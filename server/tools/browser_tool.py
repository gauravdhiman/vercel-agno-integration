import asyncio
import base64
import json
import os
import time
import traceback
from typing import Any, Dict, List, Optional, Tuple, Union

import httpx

from agno.tools import Toolkit
from agno.utils.log import log_debug, log_info, log_error, log_warning

# Try to import docker, but make it optional
try:
    import docker
    from docker.errors import DockerException, NotFound
except ImportError:
    docker = None
    DockerException = None
    NotFound = None
    log_warning(
        "`docker` package not installed. Sandbox container management will be skipped. "
        "Ensure the sandbox container is running manually. Install with `pip install docker`."
    )


# --- Pydantic Models for API communication (mirroring Suna's browser_api.py expectations) ---
# These are used to structure data sent to the internal API, not for Agno's direct tool inputs.

class Position:
    x: int
    y: int

class ClickElementAction:
    index: int

class ClickCoordinatesAction:
    x: int
    y: int

class GoToUrlAction:
    url: str

class InputTextAction:
    index: int
    text: str

class ScrollAction:
    amount: Optional[int] = None

class SendKeysAction:
    keys: str

class SwitchTabAction:
    page_id: int

class OpenTabAction:
    url: str

class CloseTabAction:
    page_id: int

class ExtractContentAction:
    goal: str # Goal for content extraction

class DragDropAction:
    element_source: Optional[str] = None
    element_target: Optional[str] = None
    coord_source_x: Optional[int] = None
    coord_source_y: Optional[int] = None
    coord_target_x: Optional[int] = None
    coord_target_y: Optional[int] = None

# --- Model for representing the result from the browser API ---
# This is what the internal browser_api.py server returns.
class BrowserActionResult:
    success: bool = True
    message: str = ""
    error: Optional[str] = None
    url: Optional[str] = None
    title: Optional[str] = None
    elements: Optional[str] = None
    screenshot_base64: Optional[str] = None # The API might return this
    image_url: Optional[str] = None # If API uploads screenshot to S3
    pixels_above: int = 0
    pixels_below: int = 0
    content: Optional[str] = None # For extracted content
    ocr_text: Optional[str] = None
    element_count: int = 0
    interactive_elements: Optional[List[Dict[str, Any]]] = None
    viewport_width: Optional[int] = None
    viewport_height: Optional[int] = None

    def __init__(self, **data: Any):
        for field, value in data.items():
            setattr(self, field, value)

    def to_json_string(self) -> str:
        data_dict = self.__dict__
        # Remove base64 screenshot if present for brevity in logs/output string
        if "screenshot_base64" in data_dict and data_dict["screenshot_base64"]:
            data_dict_summary = data_dict.copy()
            data_dict_summary["screenshot_base64"] = "[Screenshot data removed for brevity]"
            return json.dumps(data_dict_summary, indent=2)
        return json.dumps(data_dict, indent=2)

class AgnoBrowserToolkit(Toolkit):
    def __init__(
        self,
        container_name: str = "agno_browser_sandbox",
        image_name: str = "kortix/suna:0.1.2.8",
        host_port: int = 8004,  # Using a different default port for Agno
        sandbox_api_internal_port: int = 8003,
        vnc_password: str = "agnopass",
        wait_after_action: float = 0.5, # seconds
        default_timeout: float = 60.0, # seconds for HTTP requests
        manage_docker: bool = True, # Whether the toolkit should try to manage the Docker container
        **kwargs,
    ):
        super().__init__(name="agno_browser_toolkit", **kwargs)
        self.container_name = container_name
        self.image_name = image_name
        self.host_port = host_port
        self.sandbox_api_internal_port = sandbox_api_internal_port
        self.vnc_password = vnc_password
        self.base_url = f"http://localhost:{self.host_port}/api/automation"
        self._client = httpx.AsyncClient(timeout=default_timeout)
        self.wait_after_action = wait_after_action
        self.manage_docker = manage_docker

        self.docker_client = None
        if self.manage_docker and docker:
            try:
                self.docker_client = docker.from_env()
                log_info("Docker SDK initialized. Toolkit will attempt to manage the sandbox container.")
            except DockerException:
                log_warning(
                    "Docker SDK found but failed to connect to Docker daemon. "
                    "Sandbox container management will be skipped. Ensure the sandbox container is running manually."
                )
                self.docker_client = None
                self.manage_docker = False # Disable docker management if client fails
        elif self.manage_docker and not docker:
            log_warning(
                "`docker` package not installed, but `manage_docker` is True. "
                "Disabling Docker management. Please install `docker` or manage the container manually."
            )
            self.manage_docker = False


        # Register tool methods
        if self.manage_docker:
            self.register(self.ensure_sandbox_running)
            self.register(self.stop_sandbox)

        self.register(self.browser_navigate_to)
        self.register(self.browser_get_current_state)
        self.register(self.browser_click_element)
        self.register(self.browser_click_coordinates)
        self.register(self.browser_input_text)
        self.register(self.browser_send_keys)
        self.register(self.browser_scroll_down)
        self.register(self.browser_scroll_up)
        self.register(self.browser_scroll_to_text)
        self.register(self.browser_extract_content)
        # More advanced/less common actions can be added later if needed
        # self.register(self.search_google) # This is an internal API, agent should use search tool
        self.register(self.browser_go_back)
        self.register(self.browser_wait_seconds)
        # self.register(self.switch_tab) # Tab management can be complex
        # self.register(self.open_tab)
        # self.register(self.close_tab)
        # self.register(self.save_pdf)
        # self.register(self.get_dropdown_options)
        # self.register(self.select_dropdown_option)
        # self.register(self.drag_drop)

    async def _ensure_container_is_ready(self) -> bool:
        """Checks if the API inside the container is responsive."""
        try:
            response = await self._client.get(f"http://localhost:{self.host_port}/api", timeout=5.0)
            return response.status_code == 200
        except httpx.RequestError:
            return False

    def ensure_sandbox_running(self, start_timeout: int = 120) -> str:
        """
        Ensures the browser sandbox container is running.
        Starts it if it's stopped, or creates it if it doesn't exist.
        This method is synchronous because Docker SDK operations are typically synchronous.

        :param start_timeout: Max time in seconds to wait for the sandbox API to become responsive.
        :return: Status message.
        """
        if not self.manage_docker or not self.docker_client:
            return "Docker management is disabled for this toolkit. Ensure the sandbox is running manually."

        try:
            container = self.docker_client.containers.get(self.container_name)
            if container.status == "running":
                log_info(f"Sandbox container '{self.container_name}' is already running.")
                # Check if API is responsive
                if asyncio.run(self._ensure_container_is_ready()):
                    return f"Sandbox container '{self.container_name}' is running and API is responsive."
                else:
                    log_warning(f"Sandbox container '{self.container_name}' is running but API is not responsive. Attempting restart.")
                    container.restart()
            else:
                log_info(f"Sandbox container '{self.container_name}' found but status is '{container.status}'. Starting...")
                container.start()
        except NotFound:
            log_info(f"Sandbox container '{self.container_name}' not found. Creating and starting...")
            try:
                # These env vars are used by Suna's browser_api.py and supervisord.conf
                env_vars = {
                    "VNC_PASSWORD": self.vnc_password,
                    "RESOLUTION": "1024x768x24",
                    "CHROME_PERSISTENT_SESSION": "true", # Or false, depending on desired behavior
                    "ANONYMIZED_TELEMETRY": "false", # Important for Suna image
                    "CHROME_DEBUGGING_PORT": "9222", # Consistent with Suna
                }
                # Ports: host_port for API, host_port+1 for VNC Web, host_port+2 for VNC raw
                # This is a simple mapping, might need adjustment if ports conflict.
                # Suna's internal ports: 8003 (API), 6080 (noVNC), 5901 (VNC)
                ports_map = {
                    f"{self.sandbox_api_internal_port}/tcp": self.host_port,
                    "6080/tcp": self.host_port + 1, # Map noVNC
                    "5901/tcp": self.host_port + 2, # Map VNC
                }
                container = self.docker_client.containers.run(
                    self.image_name,
                    detach=True,
                    name=self.container_name,
                    ports=ports_map,
                    environment=env_vars,
                    shm_size="2g", # Recommended for browsers
                    restart_policy={"Name": "unless-stopped"},
                )
                log_info(f"Sandbox container '{self.container_name}' created and started with ID: {container.id}")
            except DockerException as e:
                log_error(f"Failed to create/start sandbox container: {e}")
                return f"Error: Failed to create/start sandbox container: {e}"
        except DockerException as e:
            log_error(f"Docker error while ensuring sandbox is running: {e}")
            return f"Error: Docker error: {e}"

        # Wait for the API to become responsive
        log_info(f"Waiting up to {start_timeout}s for sandbox API to become responsive...")
        start_wait_time = time.time()
        while time.time() - start_wait_time < start_timeout:
            if asyncio.run(self._ensure_container_is_ready()):
                log_info("Sandbox API is responsive.")
                return (f"Sandbox container '{self.container_name}' is running. API: {self.base_url}. "
                        f"VNC Web: http://localhost:{self.host_port + 1}/vnc.html?password={self.vnc_password}")
            time.sleep(2)
        log_error("Sandbox API did not become responsive within timeout.")
        return f"Error: Sandbox API at {self.base_url} did not become responsive after {start_timeout}s."

    def stop_sandbox(self) -> str:
        """
        Stops the browser sandbox container if it's managed by this toolkit.
        This method is synchronous.

        :return: Status message.
        """
        if not self.manage_docker or not self.docker_client:
            return "Docker management is disabled. Cannot stop sandbox."

        try:
            container = self.docker_client.containers.get(self.container_name)
            if container.status == "running":
                log_info(f"Stopping sandbox container '{self.container_name}'...")
                container.stop()
                return f"Sandbox container '{self.container_name}' stopped."
            else:
                return f"Sandbox container '{self.container_name}' is not running (status: {container.status})."
        except NotFound:
            return f"Sandbox container '{self.container_name}' not found. Cannot stop."
        except DockerException as e:
            log_error(f"Docker error while stopping sandbox: {e}")
            return f"Error: Docker error while stopping sandbox: {e}"

    async def _api_request(
        self, method: str, endpoint: str, data: Optional[Dict] = None, params: Optional[Dict] = None
    ) -> BrowserActionResult:
        """Internal helper to make HTTP requests to the sandbox browser API."""
        url = f"{self.base_url}{endpoint}"
        log_debug(f"Browser API Request: {method} {url} | Params: {params} | Data: {data}")

        try:
            if method.upper() == "GET":
                response = await self._client.get(url, params=params)
            elif method.upper() == "POST":
                response = await self._client.post(url, json=data)
            else:
                return BrowserActionResult(success=False, error=f"Unsupported HTTP method: {method}")

            response.raise_for_status()  # Will raise an exception for 4xx/5xx status
            response_data = response.json()
            log_debug(f"Browser API Response: {response_data}")
            return BrowserActionResult(**response_data)
        except httpx.HTTPStatusError as e:
            error_content = e.response.text
            try:
                error_json = e.response.json()
                error_content = error_json.get("detail", error_content)
            except ValueError:
                pass # Keep error_content as text
            log_error(f"Browser API HTTP Error: {e.request.method} {e.request.url} - Status {e.response.status_code} - {error_content}")
            return BrowserActionResult(success=False, error=f"API Error {e.response.status_code}: {error_content}", url=str(e.request.url))
        except httpx.RequestError as e:
            log_error(f"Browser API Request Error: {e.request.method} {e.request.url} - {e}")
            return BrowserActionResult(success=False, error=f"Request Error: {e}", url=str(e.request.url))
        except Exception as e:
            log_error(f"Unexpected error in _api_request: {e} for {url}")
            traceback.print_exc()
            return BrowserActionResult(success=False, error=f"Unexpected error: {e}", url=url)

    async def _process_action_and_get_state(self, action_name: str, endpoint: str, payload: Optional[Dict] = None, method: str = "POST") -> str:
        """Helper to execute an action and return the formatted BrowserActionResult."""
        if self.wait_after_action > 0:
            await asyncio.sleep(self.wait_after_action)
        
        action_result = await self._api_request(method, endpoint, data=payload)
        return action_result.to_json_string()

    async def browser_get_current_state(self) -> str:
        """
        Retrieves the current state of the browser, including URL, title, interactive elements, and a screenshot.

        :return: A JSON string representing the current browser state.
        """
        log_info("Getting current browser state.")
        # The browser_api.py doesn't have a dedicated "get_state" endpoint that just returns state.
        # It returns state *after* an action. A common way to get state is to perform a benign action, like wait(0).
        # Or, we can assume the state is returned by the *last* action.
        # For a dedicated state retrieval, we'd need to add an endpoint to browser_api.py.
        # For now, let's use a short wait as a pseudo "get_state" action.
        return await self._process_action_and_get_state("get_current_browser_state", "/wait", {"seconds": 0})

    async def browser_navigate_to(self, url: str) -> str:
        """
        Navigates the browser to the specified URL.

        :param url: The URL to navigate to.
        :return: A JSON string representing the browser state after navigation.
        """
        log_info(f"Navigating to URL: {url}")
        return await self._process_action_and_get_state("navigate_to", "/navigate_to", {"url": url})

    async def browser_click_element(self, index: int) -> str:
        """
        Clicks on an interactive element on the page, identified by its index.
        The index is based on the list of interactive elements returned by `get_current_browser_state`.

        :param index: The 1-based index of the element to click.
        :return: A JSON string representing the browser state after the click.
        """
        log_info(f"Clicking element at index: {index}")
        return await self._process_action_and_get_state("click_element", "/click_element", {"index": index})

    async def browser_click_coordinates(self, x: int, y: int) -> str:
        """
        Clicks at the specified X, Y coordinates on the page.

        :param x: The X coordinate.
        :param y: The Y coordinate.
        :return: A JSON string representing the browser state after the click.
        """
        log_info(f"Clicking at coordinates: x={x}, y={y}")
        return await self._process_action_and_get_state("click_coordinates", "/click_coordinates", {"x": x, "y": y})

    async def browser_input_text(self, index: int, text: str) -> str:
        """
        Inputs the given text into an interactive element (e.g., input field, textarea)
        identified by its index.

        :param index: The 1-based index of the element.
        :param text: The text to input.
        :return: A JSON string representing the browser state after inputting text.
        """
        log_info(f"Inputting text '{text}' into element at index: {index}")
        return await self._process_action_and_get_state("input_text", "/input_text", {"index": index, "text": text})

    async def browser_send_keys(self, keys: str) -> str:
        """
        Sends keyboard keystrokes to the browser.
        Can be special keys like 'Enter', 'Escape', or combinations like 'Control+a'.

        :param keys: The key(s) to send.
        :return: A JSON string representing the browser state after sending keys.
        """
        log_info(f"Sending keys: {keys}")
        return await self._process_action_and_get_state("send_keys", "/send_keys", {"keys": keys})

    async def browser_scroll_down(self, amount: Optional[int] = None) -> str:
        """
        Scrolls the page down.

        :param amount: Optional pixel amount to scroll. If None, scrolls by one viewport height.
        :return: A JSON string representing the browser state after scrolling.
        """
        log_info(f"Scrolling down by {amount or 'one page'}.")
        return await self._process_action_and_get_state("scroll_down", "/scroll_down", {"amount": amount} if amount else {})

    async def browser_scroll_up(self, amount: Optional[int] = None) -> str:
        """
        Scrolls the page up.

        :param amount: Optional pixel amount to scroll. If None, scrolls by one viewport height.
        :return: A JSON string representing the browser state after scrolling.
        """
        log_info(f"Scrolling up by {amount or 'one page'}.")
        return await self._process_action_and_get_state("scroll_up", "/scroll_up", {"amount": amount} if amount else {})

    async def browser_scroll_to_text(self, text: str) -> str:
        """
        Scrolls the page to find the first visible occurrence of the specified text.

        :param text: The text to scroll to.
        :return: A JSON string representing the browser state after scrolling.
        """
        log_info(f"Scrolling to text: '{text}'")
        return await self._process_action_and_get_state("scroll_to_text", "/scroll_to_text", {"text": text})

    async def browser_extract_content(self, goal: str) -> str:
        """
        Extracts content from the current page based on a specified goal.
        The internal API uses an LLM for intelligent extraction if configured, otherwise falls back to simpler text extraction.

        :param goal: A description of what content to extract (e.g., "all headings", "product price").
        :return: A JSON string representing the browser state, with extracted content in the 'content' field.
        """
        log_info(f"Extracting content with goal: '{goal}'")
        return await self._process_action_and_get_state("extract_content", "/extract_content", {"goal": goal})

    async def browser_go_back(self) -> str:
        """
        Navigates to the previous page in the browser's history.

        :return: A JSON string representing the browser state after navigating back.
        """
        log_info("Navigating back in browser history.")
        return await self._process_action_and_get_state("go_back", "/go_back", method="POST") # browser_api has it as POST

    async def browser_wait_seconds(self, seconds: int = 3) -> str:
        """
        Pauses execution for a specified number of seconds.
        The browser state is refreshed after the wait.

        :param seconds: Number of seconds to wait.
        :return: A JSON string representing the browser state after waiting.
        """
        log_info(f"Waiting for {seconds} seconds.")
        # The API endpoint is /wait and payload should be {"seconds": ...}
        return await self._process_action_and_get_state("wait_seconds", "/wait", {"seconds": seconds})

    async def close(self):
        """Closes the HTTP client."""
        if self._client:
            await self._client.aclose()
            log_info("AgnoBrowserToolkit HTTP client closed.")


async def main_test():
    """Test function for AgnoBrowserToolkit."""
    print("Initializing AgnoBrowserToolkit...")
    # Set manage_docker=True if you have Docker running and want the toolkit to handle it.
    # If manage_docker=False, ensure the kortix/suna container is running and port 8004 is mapped to 8003.
    # Example: docker run -d --name agno_browser_sandbox -p 8004:8003 -p 8005:6080 -p 8006:5901 --shm-size=2g kortix/suna:0.1.2.8
    browser_toolkit = AgnoBrowserToolkit(manage_docker=True, host_port=8004)

    try:
        if browser_toolkit.manage_docker:
            print("\nEnsuring sandbox container is running...")
            status_msg = browser_toolkit.ensure_sandbox_running()
            print(status_msg)
            if "Error" in status_msg:
                return

        print("\nTesting navigate_to google.com...")
        result_str = await browser_toolkit.navigate_to("https://www.google.com")
        print("Navigation Result (JSON string):")
        print(result_str)
        result_data = json.loads(result_str)
        if not result_data.get("success"):
             print(f"Navigation failed: {result_data.get('error')}")
             return

        print(f"\nNavigated to: {result_data.get('url')}")
        print(f"Page title: {result_data.get('title')}")
        print(f"Found {result_data.get('element_count')} interactive elements.")
        if result_data.get("image_url"):
            print(f"Screenshot uploaded to: {result_data.get('image_url')}")


        print("\nTesting input_text (searching for 'Agno AI')...")
        # Assuming the search bar is one of the first interactive elements
        # Find the search input element from the interactive_elements list (heuristic)
        search_input_index = None
        for el in result_data.get("interactive_elements", []):
            if el.get("tag_name") == "textarea" or (el.get("tag_name") == "input" and el.get("type") in [None, "text", "search"]):
                # A simple heuristic, might need adjustment
                search_input_index = el.get("index")
                break
        
        if search_input_index is not None:
            result_str = await browser_toolkit.input_text(index=search_input_index, text="Agno AI")
            print("Input Text Result (JSON string):")
            print(result_str)
            result_data = json.loads(result_str)
            if not result_data.get("success"):
                 print(f"Input text failed: {result_data.get('error')}")
                 return
            if result_data.get("image_url"):
                print(f"Screenshot after input: {result_data.get('image_url')}")

            print("\nTesting send_keys (Enter)...")
            result_str = await browser_toolkit.send_keys(keys="Enter")
            print("Send Keys Result (JSON string):")
            print(result_str)
            result_data = json.loads(result_str)
            if not result_data.get("success"):
                 print(f"Send keys failed: {result_data.get('error')}")
                 return

            print(f"\nAfter search, URL: {result_data.get('url')}")
            print(f"Page title: {result_data.get('title')}")
            if result_data.get("image_url"):
                print(f"Screenshot after search: {result_data.get('image_url')}")
            log_info("Detailed elements after search:\n" + result_data.get("elements", "No elements string provided."))

        else:
            print("Could not find a suitable search input field.")

        print("\nGetting current browser state...")
        state_str = await browser_toolkit.get_current_browser_state()
        print("Current State (JSON string):")
        print(state_str)


    except Exception as e:
        print(f"An error occurred during testing: {e}")
        traceback.print_exc()
    finally:
        await browser_toolkit.close()
        if browser_toolkit.manage_docker:
            print("\nStopping sandbox container (if managed)...")
            # Uncomment if you want the test to stop the container
            # print(browser_toolkit.stop_sandbox())
            pass


if __name__ == "__main__":
    # This is for standalone testing of the toolkit.
    # In a real Agno environment, the toolkit would be imported and used by an agent.
    print("Running AgnoBrowserToolkit test script...")
    asyncio.run(main_test())
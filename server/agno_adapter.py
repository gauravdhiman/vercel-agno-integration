# agno_adapter.py
import asyncio
import json
import logging
from typing import AsyncGenerator, Any, Dict, List, Optional, Union
from uuid import uuid4

# --- Pydantic ---
from pydantic import BaseModel, Field as PydanticField # Alias to avoid conflict with Agno's File

# --- Agno Imports ---
from agno.agent import Agent # Assuming Agent is the primary class, not Team for this example
from agno.models.message import Message as AgnoMessage
from agno.run.response import RunEvent, RunResponse
from agno.tools.function import Function
from agno.utils.log import log_debug, log_error, log_info, logger # Use the configured logger

# --- Frontend Tool Imports ---
import sys
import os
# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from common.frontend_tools import FrontendToolName

# --- Vercel AI SDK Data Stream Protocol Type IDs ---
TEXT_PART = "0"
DATA_PART = "2"
ERROR_PART = "3"
ANNOTATION_PART = "8"
TOOL_CALL_PART = "9"
TOOL_RESULT_PART = "a" # Primarily for frontend -> backend, but good to have
FINISH_MESSAGE_PART = "d"
REASONING_PART = "g"
SOURCE_PART = "h"
# ... add other type IDs as needed ...


class FrontendToolSchema(BaseModel):
    name: str
    description: str
    parameters: Dict[str, Any] = PydanticField(default_factory=lambda: {"type": "object", "properties": {}})


class AgnoVercelAdapter:
    """
    Adapts the output stream of an Agno Agent to the
    Vercel AI SDK Data Stream Protocol. It uses a proxy tool pattern
    for the Agno agent to request actions on the frontend.
    """
    PROXY_TOOL_NAME = "call_frontend_action"
    # This is used when a BACKEND tool call needs to be displayed/handled on the frontend.
    # It's different from the agent requesting a specific frontend UI action.
    BACKEND_TOOL_DISPLAY_NAME = FrontendToolName.DISPLAY_TOOL_INFO.value

    def __init__(self,
                 agent: Agent,
                 frontend_tool_schemas: Optional[List[FrontendToolSchema]] = None):
        if not isinstance(agent, Agent):
            raise TypeError("Input must be an instance of agno.Agent")
        self.agent = agent
        self.frontend_tool_schemas: List[FrontendToolSchema] = frontend_tool_schemas or []
        self._agent_instructions_updated = False

        self._ensure_proxy_tool_registered()
        self._update_agent_instructions_with_frontend_tools()


    def _ensure_proxy_tool_registered(self):
        """Ensures the proxy tool is part of the agent's tools."""
        proxy_tool_func_def = self._get_proxy_tool_definition()
        if self.agent.tools is None:
            self.agent.tools = []

        if not any(getattr(t, 'name', None) == self.PROXY_TOOL_NAME for t in self.agent.tools):
            self.agent.tools.append(proxy_tool_func_def)
            log_info(f"[Agno-Vercel Adapter][{self.agent.name}]: Registered proxy tool '{self.PROXY_TOOL_NAME}'.")
            # Agno might require a re-initialization or model update if tools change dynamically
            # This depends on Agno's internal workings. For now, we assume it's handled
            # or that tools are set before the agent is first used significantly.
            # Example: if hasattr(self.agent, 'update_model'): self.agent.update_model(session_id="proxy_tool_init")
        else:
            log_debug(f"[Agno-Vercel Adapter][{self.agent.name}]: Proxy tool '{self.PROXY_TOOL_NAME}' already registered.")


    def _update_agent_instructions_with_frontend_tools(self):
        """
        Updates the agent's instructions to include information about
        available frontend tools and how to call them using the proxy tool.
        """
        if self._agent_instructions_updated or not self.frontend_tool_schemas:
            return

        instruction_header = "\n\n## Interacting with the User Interface (Frontend Actions)\n\n"
        instruction_body = (
            f"To request actions or display specific UI components on the frontend, "
            f"you MUST use the '{self.PROXY_TOOL_NAME}' tool. "
            "This tool acts as a bridge to the frontend.\n\n"
            f"The '{self.PROXY_TOOL_NAME}' tool requires the following arguments:\n"
            f"- `frontend_tool_name` (string, required): The specific name of the action the frontend should perform.\n"
            f"- `frontend_tool_args` (object, required): A JSON object containing the arguments for that frontend action.\n\n"
            "Available frontend actions and their argument schemas:\n"
        )

        for schema in self.frontend_tool_schemas:
            instruction_body += f"\n### Frontend Action: `{schema.name}`\n"
            instruction_body += f"Description: {schema.description}\n"
            instruction_body += f"Arguments (`frontend_tool_args` for this action):\n```json\n"
            instruction_body += json.dumps(schema.parameters, indent=2)
            instruction_body += "\n```\n"

        instruction_body += (
            f"\nExample of how to call '{self.PROXY_TOOL_NAME}' to trigger the '{self.frontend_tool_schemas[0].name}' frontend action:\n"
            f"Tool Name: {self.PROXY_TOOL_NAME}\n"
            f"Tool Arguments: {{\n"
            f'  "frontend_tool_name": "{self.frontend_tool_schemas[0].name}",\n'
            f'  "frontend_tool_args": {{ ...args matching {self.frontend_tool_schemas[0].name} schema... }}\n'
            f"}}\n"
        )

        full_instructions = instruction_header + instruction_body

        if not self.agent.instructions:
            self.agent.instructions = []

        if self.agent.instructions:
            if isinstance(self.agent.instructions, str):
                self.agent.instructions += full_instructions
            elif isinstance(self.agent.instructions, list):
                self.agent.instructions.append(full_instructions)

        self._agent_instructions_updated = True
        log_info(f"[Agno-Vercel Adapter][{self.agent.name}]: Updated agent instructions with frontend tool schemas.")


    @staticmethod
    def _format_vercel_data_stream(type_id: str, data: Any) -> str:
        """Formats data according to the Vercel AI SDK Data Stream Protocol."""
        try:
            if type_id in [TEXT_PART, ERROR_PART, REASONING_PART]:
                 payload = json.dumps(str(data))
            else:
                 payload = json.dumps(data, default=str) # default=str for complex objects
        except TypeError as e:
            log_error(f"[Agno-Vercel Adapter]: Serialization error for type {type_id}: {data}. Error: {e}")
            payload = json.dumps({"error": "Serialization failed", "details": str(e)})
            type_id = ERROR_PART

        # Format according to Vercel AI SDK Data Stream Protocol
        formatted = f"{type_id}:{payload}\n"
        return formatted

    def _get_proxy_tool_definition(self) -> Function:
        """Creates the definition for the proxy tool Agno agent will call."""
        return Function(
            name=self.PROXY_TOOL_NAME,
            description="A proxy function to request an action or UI update on the frontend application. You MUST specify the exact `frontend_tool_name` and the `frontend_tool_args` according to the available frontend actions documented in your instructions.",
            parameters={
                "type": "object",
                "properties": {
                    "frontend_tool_name": {
                        "type": "string",
                        "description": "The specific name of the action the frontend application should perform (e.g., 'ask_user_confirmation', 'display_product_card'). Refer to agent instructions for available frontend_tool_names and their argument schemas."
                    },
                    "frontend_tool_args": {
                        "type": "object",
                        "description": "A JSON object containing the arguments required by the specified `frontend_tool_name`. The structure of this object depends on the `frontend_tool_name` chosen."
                    }
                },
                "required": ["frontend_tool_name", "frontend_tool_args"]
            },
            entrypoint=self._handle_proxy_tool_call, # This is called by Agno
            show_result=False, # The Agno agent doesn't need to see "Frontend action requested."
            stop_after_tool_call=False # Agent should usually continue after requesting UI action
        )

    async def _handle_proxy_tool_call(self, frontend_tool_name: str, frontend_tool_args: Dict[str, Any]) -> str:
        """
        This method is executed by Agno's agent when it calls the PROXY_TOOL_NAME.
        It simply returns a confirmation string to the Agno agent.
        The actual triggering of the frontend UI update happens in the
        `_agno_to_vercel_stream` method when it processes the `tool_call_started`
        event for this proxy tool.
        """
        log_info(f"[Agno-Vercel Adapter][{self.agent.name}]: Proxy tool '{self.PROXY_TOOL_NAME}' called by agent. Frontend action '{frontend_tool_name}' with args {frontend_tool_args} will be requested from UI.")
        # This result goes back to the Agno agent's internal state.
        # It does NOT go directly to the frontend from here.
        return f"Request to trigger frontend action '{frontend_tool_name}' has been queued. The result of frontend tool may be passed back in subsequent call and accordingly you can respond further and take any other action."

    async def _agno_to_vercel_stream(
        self,
        agno_response_stream: AsyncGenerator[RunResponse, None]
    ) -> AsyncGenerator[bytes, None]:
        # Use instance variables for tracking tool calls
        # (these are initialized in __init__ and reset in _reset_tool_tracking)

        try:
            async for agno_response in agno_response_stream:
                event = agno_response.event
                content = agno_response.content
                tools = agno_response.tools # This will contain the call to PROXY_TOOL_NAME
                metrics = agno_response.metrics
                thinking = agno_response.thinking

                if event == RunEvent.tool_call_started and tools:
                    is_proxy_call_handled = False
                    for tool_call_data in tools: # Agno's tool_call structure
                        agno_tool_name = tool_call_data.get("tool_name", tool_call_data.get("function", {}).get("name"))
                        agno_tool_args_raw = tool_call_data.get("tool_args", tool_call_data.get("function", {}).get("arguments"))
                        agno_tool_call_id = tool_call_data.get("tool_call_id", tool_call_data.get("id"))

                        if agno_tool_name == self.PROXY_TOOL_NAME:
                            is_proxy_call_handled = True
                            log_debug(f"[Agno-Vercel Adapter][{self.agent.name}]: Intercepted proxy tool call ID '{agno_tool_call_id}' to trigger frontend.")

                            # Arguments for PROXY_TOOL_NAME were set by the LLM
                            # These arguments *contain* the actual frontend tool name and its args
                            proxy_call_args = {}
                            if isinstance(agno_tool_args_raw, str):
                                try:
                                    proxy_call_args = json.loads(agno_tool_args_raw)
                                except json.JSONDecodeError:
                                    log_error(f"[Agno-Vercel Adapter] Failed to parse proxy tool args: {agno_tool_args_raw}")
                                    proxy_call_args = {"error": "Invalid proxy arguments"}
                            elif isinstance(agno_tool_args_raw, dict):
                                proxy_call_args = agno_tool_args_raw

                            frontend_tool_name_to_call = proxy_call_args.get("frontend_tool_name", "unknown_frontend_action")
                            frontend_tool_args_for_call = proxy_call_args.get("frontend_tool_args", {})

                            vercel_tool_request = {
                                "toolCallId": agno_tool_call_id, # Use Agno's ID for the proxy call
                                "toolName": frontend_tool_name_to_call,
                                "args": frontend_tool_args_for_call,
                            }
                            formatted_data = self._format_vercel_data_stream(TOOL_CALL_PART, vercel_tool_request).encode("utf-8")
                            log_debug(f"[Agno-Vercel Adapter][{self.agent.name}]: Sending tool call event: {formatted_data}")
                            yield formatted_data
                            log_debug(f"[Agno-Vercel Adapter][{self.agent.name}]: Sleeping for 0.01 seconds before next event...")
                            await asyncio.sleep(0.01)
                            # Since this specific tool_call_data was for the proxy, we've handled it.
                            # If there were other non-proxy tools in the same 'tools' list, they'd be handled by the 'else' below.
                            break # Processed the proxy tool, move to next agno_response

                    if is_proxy_call_handled:
                        continue # Move to the next event from Agno stream

                    # If not a proxy call, handle backend tools (if any) as before
                    # This allows backend tools and frontend proxy tools to coexist
                    for tool_call_data in tools:
                        tool_call_id = tool_call_data.get("tool_call_id", tool_call_data.get("id", f"backend_tool_{uuid4()}"))

                        # Skip if we've already processed this tool call start
                        if tool_call_id in self._processed_tool_call_starts:
                            log_debug(f"[Agno-Vercel Adapter][{self.agent.name}]: Skipping already processed tool call start: {tool_call_id}")
                            continue

                        # Mark this tool call as processed
                        self._processed_tool_call_starts.add(tool_call_id)

                        args_obj = {}
                        tool_args_raw = tool_call_data.get("tool_args", tool_call_data.get("function", {}).get("arguments"))
                        if tool_args_raw:
                            if isinstance(tool_args_raw, str):
                                try:
                                    args_obj = json.loads(tool_args_raw)
                                except json.JSONDecodeError:
                                    args_obj = {"raw_args": tool_args_raw}
                            elif isinstance(tool_args_raw, dict):
                                args_obj = tool_args_raw

                        vercel_backend_tool_display = {
                            "toolCallId": tool_call_id,
                            "toolName": self.BACKEND_TOOL_DISPLAY_NAME, # Generic name for UI to display
                            "args": { # Frontend receives details about the backend tool
                                "actual_tool_name": tool_call_data.get("tool_name", tool_call_data.get("function", {}).get("name")),
                                "actual_tool_args": args_obj
                            }
                        }
                        formatted_data = self._format_vercel_data_stream(TOOL_CALL_PART, vercel_backend_tool_display).encode("utf-8")
                        log_debug(f"[Agno-Vercel Adapter][{self.agent.name}]: Sending tool call event: {formatted_data}")
                        yield formatted_data
                        log_debug(f"[Agno-Vercel Adapter][{self.agent.name}]: Sleeping for 0.01 seconds before next event...")
                        await asyncio.sleep(0.01)

                elif event == RunEvent.run_response and content:
                    # Format and send the text response
                    formatted_data = self._format_vercel_data_stream(TEXT_PART, content).encode("utf-8")
                    log_debug(f"[Agno-Vercel Adapter][{self.agent.name}]: Sending text response event: {formatted_data}")
                    yield formatted_data
                    log_debug(f"[Agno-Vercel Adapter][{self.agent.name}]: Sleeping for 0.01 seconds before next event...")
                    await asyncio.sleep(0.01)

                # Handle tool call completion events
                elif event == RunEvent.tool_call_completed and tools:
                    # Ignore the completion of the proxy tool call itself for Vercel stream
                    # as the proxy tool's "result" ("Frontend action requested.") is internal to Agno.
                    if not any(tool_call.get("tool_name") == self.PROXY_TOOL_NAME for tool_call in tools):
                        # Send tool completion events to the frontend
                        for tool_call_data in tools:
                            tool_call_id = tool_call_data.get("tool_call_id", tool_call_data.get("id"))

                            # Skip if we've already processed this tool call completion
                            if tool_call_id in self._processed_tool_call_completions:
                                log_debug(f"[Agno-Vercel Adapter][{self.agent.name}]: Skipping already processed tool call completion: {tool_call_id}")
                                continue

                            print("Tool Details When Completed >>>>>> ", tool_call_data)
                            tool_result = tool_call_data.get("content")
                            if not tool_result:
                                # if there is no content / response from tool, tool is still executing, so dont process.
                                # In case of parallel tool calling, Agno send the list of all tools whenever any of those tools complete
                                # so we just need to process the tool call for which we received content, not other as they are still in call.
                                continue

                            # Mark this tool call completion as processed
                            self._processed_tool_call_completions.add(tool_call_id)

                            # Get the original tool args if available
                            tool_args = {}
                            for start_tool in self._processed_tool_call_starts:
                                if start_tool == tool_call_id:
                                    # We found the matching start tool call
                                    tool_args = {
                                        "actual_tool_name": tool_call_data.get("tool_name", "unknown_tool"),
                                        "actual_tool_args": tool_call_data.get("tool_args", {}),
                                        "actual_tool_results": tool_result
                                    }
                                    break

                            # Create a tool call result to send to the frontend
                            # Use display_tool_info as the tool name to match what was sent in the tool call started event
                            vercel_tool_result = {
                                "toolCallId": tool_call_id,
                                "toolName": self.BACKEND_TOOL_DISPLAY_NAME,  # Use display_tool_info instead of the actual tool name
                                "args": tool_args,  # Include args as required by Vercel AI SDK
                                "state": "result",
                                "result": "Actual tool result is in `args.actual_tool_results`"
                            }

                            # Format the tool completion event as a tool call part
                            formatted_data = self._format_vercel_data_stream(TOOL_CALL_PART, vercel_tool_result).encode("utf-8")
                            log_debug(f"[Agno-Vercel Adapter][{self.agent.name}]: Sending tool completion event: {formatted_data}")
                            yield formatted_data
                            log_debug(f"[Agno-Vercel Adapter][{self.agent.name}]: Sleeping for 0.01 seconds before next event...")
                            await asyncio.sleep(0.01)

                elif event == RunEvent.run_error and content:
                    formatted_data = self._format_vercel_data_stream(ERROR_PART, str(content)).encode("utf-8")
                    log_error(f"[Agno-Vercel Adapter][{self.agent.name}]: Error in run: {formatted_data}")
                    yield formatted_data
                    log_debug(f"[Agno-Vercel Adapter][{self.agent.name}]: Sleeping for 0.01 seconds before next event...")
                    await asyncio.sleep(0.01)

                elif event == RunEvent.run_completed:
                    finish_data: Dict[str, Any] = {"finishReason": "stop"}
                    if metrics:
                        finish_data["usage"] = {
                            "promptTokens": int(metrics.get("input_tokens", metrics.get("prompt_tokens", 0))),
                            "completionTokens": int(metrics.get("output_tokens", metrics.get("completion_tokens", 0))),
                            "totalTokens": int(metrics.get("total_tokens", 0)),
                        }
                        if finish_data["usage"]["totalTokens"] == 0:
                            finish_data["usage"]["totalTokens"] = finish_data["usage"]["promptTokens"] + finish_data["usage"]["completionTokens"]
                    formatted_data = self._format_vercel_data_stream(FINISH_MESSAGE_PART, finish_data).encode("utf-8")
                    log_debug(f"[Agno-Vercel Adapter][{self.agent.name}]: Sending finish message: {formatted_data}")
                    yield formatted_data
                    log_debug(f"[Agno-Vercel Adapter][{self.agent.name}]: Sleeping for 0.01 seconds before next event...")
                    await asyncio.sleep(0.01)

                elif event == RunEvent.reasoning_step and content: # Example
                    if isinstance(content, str):
                        formatted_data = self._format_vercel_data_stream(REASONING_PART, content).encode("utf-8")
                        log_debug(f"[Agno-Vercel Adapter][{self.agent.name}]: Sending reasoning step: {formatted_data}")
                        yield formatted_data
                        log_debug(f"[Agno-Vercel Adapter][{self.agent.name}]: Sleeping for 0.01 seconds before next event...")
                        await asyncio.sleep(0.01)

                elif thinking:
                    formatted_data = self._format_vercel_data_stream(REASONING_PART, thinking).encode("utf-8")
                    log_debug(f"[Agno-Vercel Adapter][{self.agent.name}]: Sending thinking: {formatted_data}")
                    yield formatted_data
                    log_debug(f"[Agno-Vercel Adapter][{self.agent.name}]: Sleeping for 0.01 seconds before next event...")
                    await asyncio.sleep(0.01)
        except Exception as e:
            # Handle ModelProviderError and other exceptions
            import traceback
            error_message = str(e)
            error_type = e.__class__.__name__
            stack_trace = traceback.format_exc()
            log_error(f"[Agno-Vercel Adapter][{self.agent.name}]: Error in stream: {error_type} - {error_message}\nStack trace:\n{stack_trace}")
            
            # Send a user-friendly message first
            user_message = "I encountered an issue processing your request. Please feel free to continue our conversation or try rephrasing your question."
            formatted_message = self._format_vercel_data_stream(TEXT_PART, user_message).encode("utf-8")
            yield formatted_message
                        
            # Send a finish message to properly close the stream
            finish_data = {"finishReason": "stop"}
            formatted_finish = self._format_vercel_data_stream(FINISH_MESSAGE_PART, finish_data).encode("utf-8")
            yield formatted_finish

            # ... map other events as needed ...


    def _prepare_agno_messages_from_vercel_history(self, messages: List[Dict[str, Any]]):
        # Convert Vercel message history to Agno's expected format
        agno_messages: List[AgnoMessage] = []

        # Process all messages including the last one's original content
        for msg_data in messages:

            # Create AgnoMessage, handling potential missing fields gracefully
            agno_msg_content = msg_data.get("content")
            agno_role = msg_data.get("role")

            if agno_msg_content:
                agno_msg = AgnoMessage(
                    role=agno_role,
                    content=str(agno_msg_content),
                )
                agno_messages.append(agno_msg)

            if "toolInvocations" in msg_data:
                # Collect all tool results
                for tool_invocation in msg_data.get("toolInvocations", []):
                    if tool_invocation.get("state") == "result":
                        tool_id = tool_invocation.get('toolCallId')
                        tool_name = tool_invocation.get('toolName')
                        tool_result = tool_invocation.get("result", {})
                        if tool_name == self.BACKEND_TOOL_DISPLAY_NAME:
                            # we dont want to show agent the response from BACKEND_TOOL_DISPLAY_NAME, as that is irrelevant (being internal tool) and should be transparent to agent.
                            continue
                        tool_result_message = AgnoMessage(
                            role="user",
                            content=f"I am providing you the result of frontend tools:\nTool '{tool_name}' with id '{tool_id}' returned: '{json.dumps(tool_result)}'",
                        )
                        agno_messages.append(tool_result_message)

        return agno_messages


    def _reset_tool_tracking(self):
        """Reset the tool tracking sets to avoid issues between conversations."""
        self._processed_tool_call_starts = set()
        self._processed_tool_call_completions = set()
        log_debug(f"[Agno-Vercel Adapter][{self.agent.name}]: Reset tool tracking sets")

    async def stream_response(
        self,
        messages: List[Dict[str, Any]], # Full history from useChat
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        **kwargs: Any # For other potential args to agent.arun
    ) -> AsyncGenerator[bytes, None]:
        """
        Runs the Agno agent and yields the response stream formatted for Vercel AI SDK.
        """
        # Reset tool tracking for new user messages
        if messages and messages[-1].get("role") == "user":
            self._reset_tool_tracking()

        self._ensure_proxy_tool_registered() # Ensure proxy tool is there
        self._update_agent_instructions_with_frontend_tools() # Ensure instructions are updated

        agno_messages = self._prepare_agno_messages_from_vercel_history(messages=messages)
        if agno_messages:
            user_or_fe_tool_input = agno_messages[-1]
            self.agent.add_messages = agno_messages[:-1]

        # Start the Agno agent stream
        agno_stream_generator = await self.agent.arun(
            message=user_or_fe_tool_input, # Latest user input
            session_id=session_id,
            user_id=user_id,
            stream=True, # Explicitly ensure Agno streams
            stream_intermediate_steps=True, # Important for tool calls
            **kwargs
        )

        async for chunk in self._agno_to_vercel_stream(agno_stream_generator):
            yield chunk
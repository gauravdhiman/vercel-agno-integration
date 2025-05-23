import uvicorn
from fastapi import FastAPI, APIRouter, HTTPException, Body
from playwright.async_api import async_playwright, Browser, Page
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import asyncio
import json
import logging
import base64
from dataclasses import dataclass, field
from datetime import datetime
import os
import random
from functools import cached_property
import traceback
import pytesseract
from PIL import Image
import io

#######################################################
# Action model definitions
#######################################################

class Position(BaseModel):
    x: int
    y: int

class ClickElementAction(BaseModel):
    index: int

class ClickCoordinatesAction(BaseModel):
    x: int
    y: int

class GoToUrlAction(BaseModel):
    url: str

class InputTextAction(BaseModel):
    index: int
    text: str

class ScrollAction(BaseModel):
    amount: Optional[int] = None

class SendKeysAction(BaseModel):
    keys: str

class SearchGoogleAction(BaseModel):
    query: str

class SwitchTabAction(BaseModel):
    page_id: int

class OpenTabAction(BaseModel):
    url: str

class CloseTabAction(BaseModel):
    page_id: int

class NoParamsAction(BaseModel):
    pass

class ExtractContentAction(BaseModel):
    goal: str

class DragDropAction(BaseModel):
    element_source: Optional[str] = None
    element_target: Optional[str] = None
    element_source_offset: Optional[Position] = None
    element_target_offset: Optional[Position] = None
    coord_source_x: Optional[int] = None
    coord_source_y: Optional[int] = None
    coord_target_x: Optional[int] = None
    coord_target_y: Optional[int] = None
    steps: Optional[int] = 10
    delay_ms: Optional[int] = 5

class DoneAction(BaseModel):
    success: bool = True
    text: str = ""

#######################################################
# DOM Structure Models
#######################################################

@dataclass
class CoordinateSet:
    x: int = 0
    y: int = 0
    width: int = 0
    height: int = 0

@dataclass
class ViewportInfo:
    width: int = 0
    height: int = 0
    scroll_x: int = 0
    scroll_y: int = 0

@dataclass
class HashedDomElement:
    tag_name: str
    attributes: Dict[str, str]
    is_visible: bool
    page_coordinates: Optional[CoordinateSet] = None

@dataclass
class DOMBaseNode:
    is_visible: bool
    parent: Optional['DOMElementNode'] = None

@dataclass
class DOMTextNode(DOMBaseNode):
    text: str = field(default="")
    type: str = 'TEXT_NODE'
    
    def has_parent_with_highlight_index(self) -> bool:
        current = self.parent
        while current is not None:
            if current.highlight_index is not None:
                return True
            current = current.parent
        return False

@dataclass
class DOMElementNode(DOMBaseNode):
    tag_name: str = field(default="")
    xpath: str = field(default="")
    attributes: Dict[str, str] = field(default_factory=dict)
    children: List['DOMBaseNode'] = field(default_factory=list)
    
    is_interactive: bool = False
    is_top_element: bool = False
    is_in_viewport: bool = False
    shadow_root: bool = False
    highlight_index: Optional[int] = None
    viewport_coordinates: Optional[CoordinateSet] = None
    page_coordinates: Optional[CoordinateSet] = None
    viewport_info: Optional[ViewportInfo] = None
    
    def __repr__(self) -> str:
        tag_str = f'<{self.tag_name}'
        for key, value in self.attributes.items():
            tag_str += f' {key}="{value}"'
        tag_str += '>'
        
        extras = []
        if self.is_interactive:
            extras.append('interactive')
        if self.is_top_element:
            extras.append('top')
        if self.highlight_index is not None:
            extras.append(f'highlight:{self.highlight_index}')
        
        if extras:
            tag_str += f' [{", ".join(extras)}]'
            
        return tag_str
    
    @cached_property
    def hash(self) -> HashedDomElement:
        return HashedDomElement(
            tag_name=self.tag_name,
            attributes=self.attributes,
            is_visible=self.is_visible,
            page_coordinates=self.page_coordinates
        )
    
    def get_all_text_till_next_clickable_element(self, max_depth: int = -1) -> str:
        text_parts = []
        
        def collect_text(node: DOMBaseNode, current_depth: int) -> None:
            if max_depth != -1 and current_depth > max_depth:
                return
                
            if isinstance(node, DOMElementNode) and node != self and node.highlight_index is not None:
                return
                
            if isinstance(node, DOMTextNode):
                text_parts.append(node.text)
            elif isinstance(node, DOMElementNode):
                for child in node.children:
                    collect_text(child, current_depth + 1)
                    
        collect_text(self, 0)
        return '\n'.join(text_parts).strip()
    
    def clickable_elements_to_string(self, include_attributes: list[str] | None = None) -> str:
        """Convert the processed DOM content to HTML."""
        formatted_text = []
        
        def process_node(node: DOMBaseNode, depth: int) -> None:
            if isinstance(node, DOMElementNode):
                # Add element with highlight_index
                if node.highlight_index is not None:
                    attributes_str = ''
                    text = node.get_all_text_till_next_clickable_element()
                    
                    # Process attributes for display
                    display_attributes = []
                    if include_attributes:
                        for key, value in node.attributes.items():
                            if key in include_attributes and value and value != node.tag_name:
                                if text and value in text:
                                    continue  # Skip if attribute value is already in the text
                                display_attributes.append(str(value))
                    
                    attributes_str = ';'.join(display_attributes)
                    
                    # Build the element string
                    line = f'[{node.highlight_index}]<{node.tag_name}'
                    
                    # Add important attributes for identification
                    for attr_name in ['id', 'href', 'name', 'value', 'type']:
                        if attr_name in node.attributes and node.attributes[attr_name]:
                            line += f' {attr_name}="{node.attributes[attr_name]}"'
                    
                    # Add the text content if available
                    if text:
                        line += f'> {text}'
                    elif attributes_str:
                        line += f'> {attributes_str}'
                    else:
                        # If no text and no attributes, use the tag name
                        line += f'> {node.tag_name.upper()}'
                    
                    line += ' </>'
                    formatted_text.append(line)
                
                # Process children regardless
                for child in node.children:
                    process_node(child, depth + 1)
                    
            elif isinstance(node, DOMTextNode):
                # Add text only if it doesn't have a highlighted parent
                if not node.has_parent_with_highlight_index() and node.is_visible:
                    if node.text and node.text.strip():
                        formatted_text.append(node.text)
                    
        process_node(self, 0)
        result = '\n'.join(formatted_text)
        return result if result.strip() else "No interactive elements found"

@dataclass
class DOMState:
    element_tree: DOMElementNode
    selector_map: Dict[int, DOMElementNode]
    url: str = ""
    title: str = ""
    pixels_above: int = 0
    pixels_below: int = 0

#######################################################
# Browser Action Result Model
#######################################################

class BrowserActionResult(BaseModel):
    success: bool = True
    message: str = ""
    error: str = ""
    
    # Extended state information
    url: Optional[str] = None
    title: Optional[str] = None
    elements: Optional[str] = None  # Formatted string of clickable elements
    screenshot_base64: Optional[str] = None
    pixels_above: int = 0
    pixels_below: int = 0
    content: Optional[str] = None
    ocr_text: Optional[str] = None  # Added field for OCR text
    
    # Additional metadata
    element_count: int = 0  # Number of interactive elements found
    interactive_elements: Optional[List[Dict[str, Any]]] = None  # Simplified list of interactive elements
    viewport_width: Optional[int] = None
    viewport_height: Optional[int] = None
    
    class Config:
        arbitrary_types_allowed = True

#######################################################
# Browser Automation Implementation 
#######################################################

class BrowserAutomation:
    def __init__(self):
        self.router = APIRouter()
        self.browser: Browser = None
        self.pages: List[Page] = []
        self.current_page_index: int = 0
        self.logger = logging.getLogger("browser_automation")
        self.include_attributes = ["id", "href", "src", "alt", "aria-label", "placeholder", "name", "role", "title", "value"]
        self.screenshot_dir = os.path.join(os.getcwd(), "screenshots")
        os.makedirs(self.screenshot_dir, exist_ok=True)
        
        # Register routes
        self.router.on_startup.append(self.startup)
        self.router.on_shutdown.append(self.shutdown)
        
        # Basic navigation
        self.router.post("/automation/navigate_to")(self.navigate_to)
        self.router.post("/automation/search_google")(self.search_google)
        self.router.post("/automation/go_back")(self.go_back)
        self.router.post("/automation/wait")(self.wait)
        
        # Element interaction
        self.router.post("/automation/click_element")(self.click_element)
        self.router.post("/automation/click_coordinates")(self.click_coordinates)
        self.router.post("/automation/input_text")(self.input_text)
        self.router.post("/automation/send_keys")(self.send_keys)
        
        # Tab management
        self.router.post("/automation/switch_tab")(self.switch_tab)
        self.router.post("/automation/open_tab")(self.open_tab)
        self.router.post("/automation/close_tab")(self.close_tab)
        
        # Content actions
        self.router.post("/automation/extract_content")(self.extract_content)
        self.router.post("/automation/save_pdf")(self.save_pdf)
        
        # Scroll actions
        self.router.post("/automation/scroll_down")(self.scroll_down)
        self.router.post("/automation/scroll_up")(self.scroll_up)
        self.router.post("/automation/scroll_to_text")(self.scroll_to_text)
        
        # Dropdown actions
        self.router.post("/automation/get_dropdown_options")(self.get_dropdown_options)
        self.router.post("/automation/select_dropdown_option")(self.select_dropdown_option)
        
        # Drag and drop
        self.router.post("/automation/drag_drop")(self.drag_drop)

    async def startup(self):
        """Initialize the browser instance on startup"""
        try:
            print("Starting browser initialization...")
            playwright = await async_playwright().start()
            print("Playwright started, launching browser...")
            
            launch_options = {
                "headless": False, # User wants to see the browser
                "timeout": 60000
            }
            # Removed CI/GITHUB_ACTIONS check to force headless: False based on user request
            
            try:
                self.browser = await playwright.chromium.launch(**launch_options)
                print("Browser launched successfully (headful mode).")
            except Exception as browser_error:
                print(f"Failed to launch browser initially: {browser_error}")
                print("Retrying with minimal options (still headful)...")
                launch_options = {"timeout": 90000, "headless": False} 
                self.browser = await playwright.chromium.launch(**launch_options)
                print("Browser launched with minimal options (headful mode).")

            try:
                # Check if there are any existing pages/contexts, use the first one if available
                # This is common if Playwright reuses an existing browser instance from a previous run
                if self.browser.contexts and self.browser.contexts[0].pages:
                    self.pages = self.browser.contexts[0].pages
                    self.current_page_index = 0
                    await self.pages[0].bring_to_front() # Ensure it's active
                    print(f"Reattached to existing browser page: {self.pages[0].url}")
                else: # Create a new page if none exist
                    raise Exception("No existing pages found in browser context.")
            except Exception as page_error:
                print(f"No suitable existing page found or error: {page_error}. Creating new page.")
                page = await self.browser.new_page(viewport={'width': 1024, 'height': 768})
                print("New page created successfully.")
                self.pages.append(page)
                self.current_page_index = 0
                await page.goto("https://www.google.com", wait_until="domcontentloaded", timeout=30000)
                print("Navigated new page to google.com")
                
            print("Browser initialization completed successfully.")
        except Exception as e:
            print(f"Browser startup error: {str(e)}")
            traceback.print_exc()
            raise RuntimeError(f"Browser initialization failed: {str(e)}")
            
    async def shutdown(self):
        """Clean up browser instance on shutdown"""
        if self.browser:
            await self.browser.close()
    
    async def get_current_page(self) -> Page:
        """Get the current active page"""
        if not self.pages:
            if self.browser and not self.browser.is_connected():
                raise HTTPException(status_code=503, detail="Browser is not connected.")
            if self.browser and not self.pages:
                 print("No pages found, creating a new one.")
                 page = await self.browser.new_page(viewport={'width': 1024, 'height': 768})
                 await page.goto("about:blank", wait_until="domcontentloaded", timeout=30000)
                 self.pages.append(page)
                 self.current_page_index = 0

            if not self.pages:
                 raise HTTPException(status_code=500, detail="No browser pages available and recovery failed.")
        return self.pages[self.current_page_index]
    
    async def get_selector_map(self) -> Dict[int, DOMElementNode]:
        page = await self.get_current_page()
        selector_map = {}
        try:
            elements_js = """
            (() => {
                function getAttributes(el) {
                    const attributes = {};
                    for (const attr of el.attributes) attributes[attr.name] = attr.value;
                    return attributes;
                }
                const interactiveElements = Array.from(document.querySelectorAll(
                    'a, button, input, select, textarea, [role="button"], [role="link"], [role="checkbox"], [role="radio"], [tabindex]:not([tabindex="-1"])'
                ));
                const visibleElements = interactiveElements.filter(el => {
                    const style = window.getComputedStyle(el);
                    const rect = el.getBoundingClientRect();
                    return style.display !== 'none' && style.visibility !== 'hidden' && style.opacity !== '0' && rect.width > 0 && rect.height > 0;
                });
                return visibleElements.map((el, index) => {
                    const rect = el.getBoundingClientRect();
                    return {
                        index: index + 1, tagName: el.tagName.toLowerCase(), text: el.innerText || el.value || '',
                        attributes: getAttributes(el), isVisible: true, isInteractive: true,
                        pageCoordinates: { x: rect.left+window.scrollX, y: rect.top+window.scrollY, width: rect.width, height: rect.height },
                        viewportCoordinates: { x: rect.left, y: rect.top, width: rect.width, height: rect.height },
                        isInViewport: rect.top>=0 && rect.left>=0 && rect.bottom<=window.innerHeight && rect.right<=window.innerWidth
                    };
                });
            })();
            """
            elements = await page.evaluate(elements_js)
            root = DOMElementNode(is_visible=True, tag_name="body", is_interactive=False, is_top_element=True)
            for idx, el_data in enumerate(elements):
                page_coords = el_data.get('pageCoordinates', {})
                vp_coords = el_data.get('viewportCoordinates', {})
                element_node = DOMElementNode(
                    is_visible=el_data.get('isVisible', True), tag_name=el_data.get('tagName', 'div'),
                    attributes=el_data.get('attributes', {}), is_interactive=el_data.get('isInteractive', True),
                    is_in_viewport=el_data.get('isInViewport', False), highlight_index=el_data.get('index', idx + 1),
                    page_coordinates=CoordinateSet(**page_coords), viewport_coordinates=CoordinateSet(**vp_coords)
                )
                if el_data.get('text'):
                    text_node = DOMTextNode(is_visible=True, text=el_data.get('text', '')); text_node.parent = element_node
                    element_node.children.append(text_node)
                selector_map[el_data.get('index', idx + 1)] = element_node
                root.children.append(element_node); element_node.parent = root
        except Exception as e:
            print(f"Error getting selector map: {e}"); traceback.print_exc()
            dummy = DOMElementNode(is_visible=True,tag_name="a",attributes={'href':'#'},is_interactive=True,highlight_index=1)
            dummy_text = DOMTextNode(is_visible=True, text="Dummy Element"); dummy_text.parent = dummy; dummy.children.append(dummy_text)
            selector_map[1] = dummy
        return selector_map
    
    async def get_current_dom_state(self) -> DOMState:
        try:
            page = await self.get_current_page()
            selector_map = await self.get_selector_map()
            root = DOMElementNode(is_visible=True, tag_name="body", is_interactive=False, is_top_element=True)
            for element in selector_map.values():
                if element.parent is None: element.parent = root; root.children.append(element)
            url = page.url; title = "Unknown Title"
            try: title = await page.title()
            except: pass
            pixels_above = 0; pixels_below = 0
            try:
                scroll_info = await page.evaluate("""
                () => {
                    const body=document.body, html=document.documentElement;
                    const totalHeight = Math.max(body.scrollHeight,body.offsetHeight,html.clientHeight,html.scrollHeight,html.offsetHeight);
                    const scrollY = window.scrollY || window.pageYOffset;
                    const windowHeight = window.innerHeight;
                    return { pixelsAbove:scrollY, pixelsBelow:Math.max(0,totalHeight-scrollY-windowHeight), totalHeight:totalHeight, viewportHeight:windowHeight };
                }""")
                pixels_above = scroll_info.get('pixelsAbove',0); pixels_below = scroll_info.get('pixelsBelow',0)
            except Exception as e: print(f"Error getting scroll info: {e}")
            return DOMState(element_tree=root, selector_map=selector_map, url=url, title=title, pixels_above=pixels_above, pixels_below=pixels_below)
        except Exception as e:
            print(f"Error getting DOM state: {e}"); traceback.print_exc()
            dummy_root = DOMElementNode(is_visible=True,tag_name="body",is_interactive=False,is_top_element=True)
            dummy_map = {1: dummy_root}; current_url = "unknown"
            try:
                if 'page' in locals() and page: current_url = page.url
            except: pass
            return DOMState(element_tree=dummy_root, selector_map=dummy_map, url=current_url, title="Error page", pixels_above=0, pixels_below=0)

    async def take_screenshot(self) -> str:
        try:
            page = await self.get_current_page()
            try: await page.wait_for_load_state("networkidle", timeout=60000)
            except Exception as e: print(f"Warning: Network idle timeout: {e}")
            screenshot_bytes = await page.screenshot(type='jpeg', quality=60, full_page=False, timeout=60000, scale='device')
            return base64.b64encode(screenshot_bytes).decode('utf-8')
        except Exception as e:
            print(f"Error taking screenshot: {e}"); traceback.print_exc()
            return ""

    async def save_screenshot_to_file(self) -> str:
        try:
            page = await self.get_current_page()
            filename = f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{random.randint(1000,9999)}.jpg"
            filepath = os.path.join(self.screenshot_dir, filename)
            await page.screenshot(path=filepath, type='jpeg', quality=60, full_page=False)
            return filepath
        except Exception as e:
            print(f"Error saving screenshot: {e}")
            return ""

    async def extract_ocr_text_from_screenshot(self, screenshot_base64: str) -> str:
        if not screenshot_base64: return ""
        try:
            image_bytes = base64.b64decode(screenshot_base64); image = Image.open(io.BytesIO(image_bytes))
            ocr_text = pytesseract.image_to_string(image); return ocr_text.strip()
        except Exception as e:
            print(f"Error performing OCR: {e}"); traceback.print_exc()
            return ""

    async def get_updated_browser_state(self, action_name: str) -> tuple:
        try:
            await asyncio.sleep(0.5)
            dom_state = await self.get_current_dom_state(); screenshot = await self.take_screenshot()
            elements = dom_state.element_tree.clickable_elements_to_string(include_attributes=self.include_attributes)
            page = await self.get_current_page(); metadata = {}
            metadata['element_count'] = len(dom_state.selector_map)
            interactive_elements = []
            for idx, element in dom_state.selector_map.items():
                el_info={'index':idx,'tag_name':element.tag_name,'text':element.get_all_text_till_next_clickable_element(),'is_in_viewport':element.is_in_viewport}
                for attr in ['id','href','src','alt','placeholder','name','role','title','type']:
                    if attr in element.attributes: el_info[attr] = element.attributes[attr]
                interactive_elements.append(el_info)
            metadata['interactive_elements'] = interactive_elements
            try:
                vp = await page.evaluate("() => {{ return {{ width: window.innerWidth, height: window.innerHeight }}; }}")
                metadata['viewport_width'] = vp.get('width',0); metadata['viewport_height'] = vp.get('height',0)
            except Exception as e: print(f"Error getting viewport: {e}"); metadata['viewport_width']=0; metadata['viewport_height']=0
            ocr_text = await self.extract_ocr_text_from_screenshot(screenshot) if screenshot else ""
            metadata['ocr_text'] = ocr_text
            print(f"Updated state after {action_name}: {len(dom_state.selector_map)} elements")
            return dom_state, screenshot, elements, metadata
        except Exception as e:
            print(f"Error getting updated state after {action_name}: {e}"); traceback.print_exc()
            return None, "", "", {}

    def build_action_result(self, success: bool, message: str, dom_state, screenshot: str, 
                              elements: str, metadata: dict, error: str = "", content: str = None,
                              fallback_url: str = None) -> BrowserActionResult:
        if elements is None: elements = ""
        return BrowserActionResult(
            success=success, message=message, error=error,
            url=dom_state.url if dom_state else fallback_url or "", title=dom_state.title if dom_state else "",
            elements=elements, screenshot_base64=screenshot,
            pixels_above=dom_state.pixels_above if dom_state else 0, pixels_below=dom_state.pixels_below if dom_state else 0,
            content=content, ocr_text=metadata.get('ocr_text',""), element_count=metadata.get('element_count',0),
            interactive_elements=metadata.get('interactive_elements',[]),
            viewport_width=metadata.get('viewport_width',0), viewport_height=metadata.get('viewport_height',0)
        )

    async def navigate_to(self, action: GoToUrlAction = Body(...)):
        try:
            page = await self.get_current_page()
            await page.goto(action.url, wait_until="domcontentloaded")
            await page.wait_for_load_state("networkidle", timeout=10000)
            dom_state, screenshot, elements, metadata = await self.get_updated_browser_state(f"navigate_to({action.url})")
            result = self.build_action_result(True, f"Navigated to {action.url}", dom_state, screenshot, elements, metadata)
            print(f"Navigation result: success={result.success}, url={result.url}")
            return result
        except Exception as e:
            print(f"Navigation error: {str(e)}"); traceback.print_exc()
            dom_state, screenshot, elements, metadata = None, "", "", {}
            try: dom_state, screenshot, elements, metadata = await self.get_updated_browser_state("navigate_error_recovery")
            except: pass
            return self.build_action_result(False, str(e), dom_state, screenshot, elements, metadata, error=str(e))

    async def search_google(self, action: SearchGoogleAction = Body(...)):
        try:
            page = await self.get_current_page()
            search_url = f"https://www.google.com/search?q={action.query}"
            await page.goto(search_url)
            await page.wait_for_load_state()
            dom_state, screenshot, elements, metadata = await self.get_updated_browser_state(f"search_google({action.query})")
            return self.build_action_result(True, f"Searched for '{action.query}' in Google", dom_state, screenshot, elements, metadata)
        except Exception as e:
            print(f"Search error: {str(e)}"); traceback.print_exc()
            dom_state, screenshot, elements, metadata = None, "", "", {}
            try: dom_state, screenshot, elements, metadata = await self.get_updated_browser_state("search_error_recovery")
            except: pass
            return self.build_action_result(False, str(e), dom_state, screenshot, elements, metadata, error=str(e))

    async def go_back(self, _: NoParamsAction = Body(...)):
        try:
            page = await self.get_current_page()
            await page.go_back()
            await page.wait_for_load_state()
            dom_state, screenshot, elements, metadata = await self.get_updated_browser_state("go_back")
            return self.build_action_result(True, "Navigated back", dom_state, screenshot, elements, metadata)
        except Exception as e:
            dom_state, screenshot, elements, metadata = None, "", "", {}
            try: dom_state, screenshot, elements, metadata = await self.get_updated_browser_state("go_back_error_recovery")
            except: pass
            return self.build_action_result(False, str(e), dom_state, screenshot, elements, metadata, error=str(e))

    async def wait(self, body: dict = Body(...)):
        seconds = body.get("seconds", 3)
        try:
            await asyncio.sleep(seconds)
            dom_state, screenshot, elements, metadata = await self.get_updated_browser_state(f"wait({seconds} seconds)")
            return self.build_action_result(True, f"Waited for {seconds} seconds", dom_state, screenshot, elements, metadata)
        except Exception as e:
            dom_state, screenshot, elements, metadata = None, "", "", {}
            try: dom_state, screenshot, elements, metadata = await self.get_updated_browser_state("wait_error_recovery")
            except: pass
            return self.build_action_result(False, str(e), dom_state, screenshot, elements, metadata, error=str(e))

    async def click_coordinates(self, action: ClickCoordinatesAction = Body(...)):
        try:
            page = await self.get_current_page()
            await page.mouse.click(action.x, action.y)
            await page.wait_for_load_state("networkidle", timeout=5000)
            dom_state, screenshot, elements, metadata = await self.get_updated_browser_state(f"click_coordinates({action.x}, {action.y})")
            return self.build_action_result(True, f"Clicked at ({action.x}, {action.y})", dom_state, screenshot, elements, metadata)
        except Exception as e:
            print(f"Error in click_coordinates: {e}"); traceback.print_exc()
            dom_state, screenshot, elements, metadata = None, "", "", {}
            try: dom_state, screenshot, elements, metadata = await self.get_updated_browser_state("click_coordinates_error_recovery")
            except: pass
            return self.build_action_result(False, str(e), dom_state, screenshot, elements, metadata, error=str(e))

    async def click_element(self, action: ClickElementAction = Body(...)):
        page = await self.get_current_page() # Define page here for fallback_url
        try:
            initial_dom_state = await self.get_current_dom_state()
            selector_map = initial_dom_state.selector_map
            if action.index not in selector_map:
                dom_state, screenshot, elements, metadata = await self.get_updated_browser_state(f"click_element_error (index {action.index} not found)")
                return self.build_action_result(False, f"Element {action.index} not found", dom_state, screenshot, elements, metadata, error=f"Element {action.index} not found")
            
            js_selector_script = f"""
            (() => {{
                const interactiveElements = Array.from(document.querySelectorAll('a, button, input, select, textarea, [role="button"], [role="link"], [role="checkbox"], [role="radio"], [tabindex]:not([tabindex="-1"])'));
                const visibleElements = interactiveElements.filter(el => {{ const style = window.getComputedStyle(el); const rect = el.getBoundingClientRect(); return style.display !== 'none' && style.visibility !== 'hidden' && style.opacity !== '0' && rect.width > 0 && rect.height > 0; }});
                if ({action.index} > 0 && {action.index} <= visibleElements.length) return visibleElements[{action.index - 1}];
                return null;
            }})();"""
            target_element_handle = await page.evaluate_handle(js_selector_script)
            click_success = False; error_message = ""
            if await target_element_handle.evaluate("node => node !== null"):
                try: await target_element_handle.click(timeout=5000); click_success = True
                except Exception as click_error: error_message = f"Error clicking: {click_error}"
            else: error_message = f"Could not locate handle for index {action.index}"
            try: await page.wait_for_load_state("networkidle", timeout=5000)
            except Exception: await asyncio.sleep(1)
            dom_state, screenshot, elements, metadata = await self.get_updated_browser_state(f"click_element({action.index})")
            return self.build_action_result(click_success, f"Clicked element {action.index}" if click_success else f"Failed click. Error: {error_message}", dom_state, screenshot, elements, metadata, error=error_message if not click_success else "")
        except Exception as e:
            print(f"Error in click_element: {e}"); traceback.print_exc()
            dom_state, screenshot, elements, metadata = None, "", "", {}; current_url = "unknown"
            try: dom_state, screenshot, elements, metadata = await self.get_updated_browser_state("click_element_error_recovery")
            except: pass
            try: current_url = page.url
            except: pass
            return self.build_action_result(False, str(e), dom_state, screenshot, elements, metadata, error=str(e), fallback_url=current_url)

    async def input_text(self, action: InputTextAction = Body(...)):
        page = await self.get_current_page()
        try:
            initial_dom_state = await self.get_current_dom_state(); selector_map = initial_dom_state.selector_map
            if action.index not in selector_map:
                dom_state, sc, el, md = await self.get_updated_browser_state(f"input_text_error (index {action.index} not found)")
                return self.build_action_result(False, f"Element {action.index} not found", dom_state, sc, el, md, error=f"Element {action.index} not found")
            js_selector_script = f"""
            (() => {{
                const interactiveElements = Array.from(document.querySelectorAll('a, button, input, select, textarea, [role="button"], [role="link"], [role="checkbox"], [role="radio"], [tabindex]:not([tabindex="-1"])'));
                const visibleElements = interactiveElements.filter(el => {{ const style = window.getComputedStyle(el); const rect = el.getBoundingClientRect(); return style.display !== 'none' && style.visibility !== 'hidden' && style.opacity !== '0' && rect.width > 0 && rect.height > 0; }});
                if ({action.index} > 0 && {action.index} <= visibleElements.length) return visibleElements[{action.index - 1}];
                return null;
            }})();"""
            target_element_handle = await page.evaluate_handle(js_selector_script)
            input_success = False; error_message = ""
            if await target_element_handle.evaluate("node => node !== null"):
                try: await target_element_handle.fill(action.text, timeout=5000); input_success = True
                except Exception as input_error: error_message = f"Error inputting: {input_error}"
            else: error_message = f"Could not locate handle for input at index {action.index}"
            dom_state, sc, el, md = await self.get_updated_browser_state(f"input_text({action.index}, '{action.text}')")
            return self.build_action_result(input_success, f"Input '{action.text}' into element {action.index}" if input_success else f"Failed input. Error: {error_message}", dom_state, sc, el, md, error=error_message if not input_success else "")
        except Exception as e:
            print(f"Error in input_text: {e}"); traceback.print_exc()
            dom_state, sc, el, md = None, "", "", {}; current_url = "unknown"
            try: dom_state, sc, el, md = await self.get_updated_browser_state("input_text_error_recovery")
            except: pass
            try: current_url = page.url
            except: pass
            return self.build_action_result(False, str(e), dom_state, sc, el, md, error=str(e), fallback_url=current_url)

    async def send_keys(self, action: SendKeysAction = Body(...)):
        page = await self.get_current_page()
        try:
            await page.keyboard.press(action.keys)
            await page.wait_for_load_state("networkidle", timeout=5000)
            dom_state, sc, el, md = await self.get_updated_browser_state(f"send_keys({action.keys})")
            return self.build_action_result(True, f"Sent keys: {action.keys}", dom_state, sc, el, md)
        except Exception as e:
            print(f"Error in send_keys: {e}"); traceback.print_exc()
            dom_state, sc, el, md = None, "", "", {}; current_url = "unknown"
            try: dom_state, sc, el, md = await self.get_updated_browser_state("send_keys_error_recovery")
            except: pass
            try: current_url = page.url
            except: pass
            return self.build_action_result(False, str(e), dom_state, sc, el, md, error=str(e), fallback_url=current_url)

    async def switch_tab(self, action: SwitchTabAction = Body(...)):
        page = await self.get_current_page() # Define page for fallback
        try:
            if 0 <= action.page_id < len(self.pages):
                self.current_page_index = action.page_id
                page = await self.get_current_page()
                await page.wait_for_load_state("domcontentloaded", timeout=5000)
                dom_state, sc, el, md = await self.get_updated_browser_state(f"switch_tab({action.page_id})")
                return self.build_action_result(True, f"Switched to tab {action.page_id}", dom_state, sc, el, md)
            else:
                csd, css, cse, csm = await self.get_updated_browser_state("switch_tab_error (invalid_index)")
                return self.build_action_result(False, f"Tab {action.page_id} not found. Valid: 0-{len(self.pages)-1}", csd, css, cse, csm, error=f"Tab {action.page_id} not found")
        except Exception as e:
            print(f"Error in switch_tab: {e}"); traceback.print_exc()
            dom_state, sc, el, md = None, "", "", {}; current_url = "unknown"
            try: dom_state, sc, el, md = await self.get_updated_browser_state("switch_tab_error_recovery")
            except: pass
            try: current_url = page.url
            except: pass
            return self.build_action_result(False, str(e), dom_state, sc, el, md, error=str(e), fallback_url=current_url)

    async def open_tab(self, action: OpenTabAction = Body(...)):
        page = await self.get_current_page() # Define page for fallback
        try:
            new_page = await self.browser.new_page(viewport={'width':1024,'height':768})
            await new_page.goto(action.url, wait_until="domcontentloaded", timeout=30000)
            await new_page.wait_for_load_state("networkidle", timeout=10000)
            self.pages.append(new_page); self.current_page_index=len(self.pages)-1
            dom_state, sc, el, md = await self.get_updated_browser_state(f"open_tab({action.url})")
            return self.build_action_result(True, f"Opened tab {action.url}. Active: {self.current_page_index}.", dom_state, sc, el, md)
        except Exception as e:
            print(f"Error opening tab: {e}"); traceback.print_exc()
            dom_state, sc, el, md = None, "", "", {}; current_url = "unknown"
            try: dom_state, sc, el, md = await self.get_updated_browser_state("open_tab_error_recovery")
            except: pass
            try: current_url = page.url
            except: pass
            return self.build_action_result(False, str(e), dom_state, sc, el, md, error=str(e), fallback_url=current_url)

    async def close_tab(self, action: CloseTabAction = Body(...)):
        page = await self.get_current_page() # Define page for fallback
        try:
            if not (0 <= action.page_id < len(self.pages)):
                csd, css, cse, csm = await self.get_updated_browser_state("close_tab_error (invalid_index)")
                return self.build_action_result(False, f"Tab {action.page_id} not found. Valid: 0-{len(self.pages)-1}", csd, css, cse, csm, error=f"Tab {action.page_id} not found")
            if len(self.pages)==1 and action.page_id==0:
                bp = await self.browser.new_page(); await bp.goto("about:blank"); self.pages.append(bp)
            page_to_close = self.pages[action.page_id]; url_closed = page_to_close.url; await page_to_close.close(); self.pages.pop(action.page_id)
            if not self.pages: bp = await self.browser.new_page(); await bp.goto("about:blank"); self.pages.append(bp); self.current_page_index=0
            elif self.current_page_index >= action.page_id: self.current_page_index=max(0,self.current_page_index-1); self.current_page_index=min(self.current_page_index,len(self.pages)-1)
            active_page = await self.get_current_page(); await active_page.bring_to_front()
            dom_state, sc, el, md = await self.get_updated_browser_state(f"close_tab({action.page_id})")
            return self.build_action_result(True, f"Closed tab {action.page_id} (URL: {url_closed}). Active: {self.current_page_index}.", dom_state, sc, el, md)
        except Exception as e:
            print(f"Error in close_tab: {e}"); traceback.print_exc()
            dom_state, sc, el, md = None, "", "", {}; current_url = "unknown"
            try: dom_state, sc, el, md = await self.get_updated_browser_state("close_tab_error_recovery")
            except: pass
            try: current_url = page.url
            except: pass
            return self.build_action_result(False, str(e), dom_state, sc, el, md, error=str(e), fallback_url=current_url)
    
    async def extract_content(self, action: ExtractContentAction = Body(...)):
        page = await self.get_current_page()
        try:
            extracted_text = await page.evaluate("""
            Array.from(document.querySelectorAll('p, h1, h2, h3, h4, h5, h6, li, span, div'))
                .filter(el => { const style = window.getComputedStyle(el); return style.display !== 'none' && style.visibility !== 'hidden' && style.opacity !== '0' && el.innerText && el.innerText.trim().length > 0 && (el.closest('main, article, section, .content, #main, #content') || document.body === el.closest('body')); })
                .map(el => el.innerText.trim()).join('\\n\\n');
            """)
            dom_state, sc, el, md = await self.get_updated_browser_state(f"extract_content({action.goal})")
            return self.build_action_result(True, f"Content extracted for goal: {action.goal}", dom_state, sc, el, md, content=extracted_text)
        except Exception as e:
            print(f"Error in extract_content: {e}"); traceback.print_exc()
            dom_state, sc, el, md = None, "", "", {}; current_url = "unknown"
            try: dom_state, sc, el, md = await self.get_updated_browser_state("extract_content_error_recovery")
            except: pass
            try: current_url = page.url
            except: pass
            return self.build_action_result(False, str(e), dom_state, sc, el, md, error=str(e), fallback_url=current_url)

    async def save_pdf(self):
        page = await self.get_current_page()
        try:
            filename=f"page_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{random.randint(1000,9999)}.pdf"; pdf_ws_path=f"/workspace/{filename}"
            await page.pdf(path=pdf_ws_path)
            dom_state, sc, el, md = await self.get_updated_browser_state("save_pdf")
            return self.build_action_result(True, f"Saved PDF: {pdf_ws_path}", dom_state, sc, el, md)
        except Exception as e:
            print(f"Error in save_pdf: {e}"); traceback.print_exc()
            dom_state, sc, el, md = None, "", "", {}; current_url = "unknown"
            try: dom_state, sc, el, md = await self.get_updated_browser_state("save_pdf_error_recovery")
            except: pass
            try: current_url = page.url
            except: pass
            return self.build_action_result(False, str(e), dom_state, sc, el, md, error=str(e), fallback_url=current_url)

    async def scroll_down(self, action: ScrollAction = Body(default_factory=ScrollAction)):
        page = await self.get_current_page()
        try:
            amount_str = "one page"
            if action.amount is not None: await page.evaluate(f"window.scrollBy(0, {action.amount});"); amount_str=f"{action.amount} pixels"
            else: await page.evaluate("window.scrollBy(0, window.innerHeight);")
            await page.wait_for_timeout(500)
            dom_state, sc, el, md = await self.get_updated_browser_state(f"scroll_down({amount_str})")
            return self.build_action_result(True, f"Scrolled down by {amount_str}", dom_state, sc, el, md)
        except Exception as e:
            print(f"Error in scroll_down: {e}"); traceback.print_exc()
            dom_state, sc, el, md = None, "", "", {}; current_url = "unknown"
            try: dom_state, sc, el, md = await self.get_updated_browser_state("scroll_down_error_recovery")
            except: pass
            try: current_url = page.url
            except: pass
            return self.build_action_result(False, str(e), dom_state, sc, el, md, error=str(e), fallback_url=current_url)

    async def scroll_up(self, action: ScrollAction = Body(default_factory=ScrollAction)):
        page = await self.get_current_page()
        try:
            amount_str = "one page"
            if action.amount is not None: await page.evaluate(f"window.scrollBy(0, -{action.amount});"); amount_str=f"{action.amount} pixels"
            else: await page.evaluate("window.scrollBy(0, -window.innerHeight);")
            await page.wait_for_timeout(500)
            dom_state, sc, el, md = await self.get_updated_browser_state(f"scroll_up({amount_str})")
            return self.build_action_result(True, f"Scrolled up by {amount_str}", dom_state, sc, el, md)
        except Exception as e:
            print(f"Error in scroll_up: {e}"); traceback.print_exc()
            dom_state, sc, el, md = None, "", "", {}; current_url = "unknown"
            try: dom_state, sc, el, md = await self.get_updated_browser_state("scroll_up_error_recovery")
            except: pass
            try: current_url = page.url
            except: pass
            return self.build_action_result(False, str(e), dom_state, sc, el, md, error=str(e), fallback_url=current_url)
            
    async def scroll_to_text(self, body: dict = Body(...)):
        text_to_find = body.get("text")
        page = await self.get_current_page() # Define page for fallback
        if not text_to_find:
            return self.build_action_result(False, "Text to find required", None, "", "", {}, error="Missing text")
        try:
            found = False
            try:
                locator = page.locator(f"text=/{text_to_find}/i")
                if await locator.count() > 0:
                    try: await locator.first.focus(timeout=1000)
                    except Exception: pass
                    await locator.first.scroll_into_view_if_needed(timeout=5000); found = True
                else:
                    js_text_to_find = json.dumps(text_to_find) # Corrected
                    await page.evaluate(f"""
                        const textToFind = {js_text_to_find};
                        const allElements = Array.from(document.querySelectorAll('*'));
                        for (const el of allElements) {{
                            if (el.innerText && el.innerText.toLowerCase().includes(textToFind.toLowerCase())) {{
                                el.scrollIntoView({{behavior: 'smooth', block: 'center'}}); break;
                            }} }}""")
                    await asyncio.sleep(0.5)
                    if await locator.count() > 0 and await locator.first.is_visible(timeout=1000): found = True
                    else: print(f"JS scroll for '{text_to_find}', not confirmed visible."); found = False 
                if found: await asyncio.sleep(0.75)
            except Exception as scroll_ex: print(f"Could not scroll to '{text_to_find}': {scroll_ex}")
            dom_state, sc, el, md = await self.get_updated_browser_state(f"scroll_to_text({text_to_find})")
            message = f"Scrolled to: '{text_to_find}'" if found else f"Text '{text_to_find}' not found/visible."
            return self.build_action_result(found, message, dom_state, sc, el, md, error="" if found else f"Text '{text_to_find}' not found")
        except Exception as e:
            print(f"Error in scroll_to_text: {e}"); traceback.print_exc()
            dom_state, sc, el, md = None, "", "", {}; current_url = "unknown"
            try: dom_state, sc, el, md = await self.get_updated_browser_state("scroll_to_text_error_recovery")
            except: pass
            try: current_url = page.url
            except: pass
            return self.build_action_result(False, str(e), dom_state, sc, el, md, error=str(e), fallback_url=current_url)

    async def get_dropdown_options(self, body: dict = Body(...)):
        index = body.get("index")
        page = await self.get_current_page()
        if index is None: return self.build_action_result(False, "Index required", None, "", "", {}, error="Missing index")
        try:
            initial_dom_state=await self.get_current_dom_state(); selector_map=initial_dom_state.selector_map
            if index not in selector_map:
                dom_state, sc, el, md = await self.get_updated_browser_state(f"get_dropdown_options_error (index {index} not found)")
                return self.build_action_result(False, f"Element {index} not found", dom_state, sc, el, md, error=f"Element {index} not found")
            element_node = selector_map[index]; options = []
            if element_node.tag_name.lower() == 'select':
                js_script_options = f"""
                (() => {{
                    const selects = Array.from(document.querySelectorAll('select')); let targetSelect = null; let visibleSelectsCount = 0;
                    for (let i=0; i<selects.length; i++) {{
                         const style=window.getComputedStyle(selects[i]); const rect=selects[i].getBoundingClientRect();
                         if (style.display!=='none'&&style.visibility!=='hidden'&&style.opacity!=='0'&&rect.width>0&&rect.height>0) {{
                             visibleSelectsCount++; if (visibleSelectsCount==={index}) {{ targetSelect=selects[i]; break; }} }} }}
                    if (targetSelect) return Array.from(targetSelect.options).map((opt, idx) => ({{index:idx,text:opt.text,value:opt.value}}));
                    return [];
                }})();"""
                options = await page.evaluate(js_script_options)
            else: options = [{"index":0,"text":"Opt A(Custom)","value":"A"},{"index":1,"text":"Opt B(Custom)","value":"B"}]
            dom_state, sc, el, md = await self.get_updated_browser_state(f"get_dropdown_options({index})")
            return self.build_action_result(True, f"Retrieved {len(options)} options", dom_state, sc, el, md, content=json.dumps(options))
        except Exception as e:
            print(f"Error in get_dropdown_options: {e}"); traceback.print_exc()
            dom_state, sc, el, md = None, "", "", {}; current_url = "unknown"
            try: dom_state, sc, el, md = await self.get_updated_browser_state("get_dropdown_options_error_recovery")
            except: pass
            try: current_url = page.url
            except: pass
            return self.build_action_result(False, str(e), dom_state, sc, el, md, error=str(e), fallback_url=current_url)

    async def select_dropdown_option(self, body: dict = Body(...)):
        index = body.get("index"); option_text = body.get("text")
        page = await self.get_current_page()
        if index is None or option_text is None: return self.build_action_result(False, "Index and option text required", None, "","","", error="Missing index or text")
        try:
            initial_dom_state = await self.get_current_dom_state(); selector_map = initial_dom_state.selector_map
            if index not in selector_map:
                dom_state, sc, el, md = await self.get_updated_browser_state(f"select_dropdown_error (index {index} not found)")
                return self.build_action_result(False, f"Element {index} not found", dom_state, sc, el, md, error=f"Element {index} not found")
            element_node = selector_map[index]; selected = False
            if element_node.tag_name.lower() == 'select':
                js_option_text = json.dumps(option_text) # Correctly escape for JS
                js_select_script = f"""
                (() => {{
                    const selects = Array.from(document.querySelectorAll('select')); let targetSelect = null; let visibleSelectsCount = 0;
                    for (let i=0; i<selects.length; i++) {{
                         const style=window.getComputedStyle(selects[i]); const rect=selects[i].getBoundingClientRect();
                         if (style.display!=='none'&&style.visibility!=='hidden'&&style.opacity!=='0'&&rect.width>0&&rect.height>0) {{
                             visibleSelectsCount++; if (visibleSelectsCount==={index}) {{ targetSelect=selects[i]; break; }} }} }}
                    if (targetSelect) {{
                        for (let i=0; i<targetSelect.options.length; i++) {{
                            if (targetSelect.options[i].text==={js_option_text}) {{ // Use the JS-escaped string
                                targetSelect.selectedIndex=i; const event=new Event('change',{{bubbles:true}}); targetSelect.dispatchEvent(event); return true;
                            }} }} }} return false;
                }})();"""
                selected = await page.evaluate(js_select_script)
            else: # Custom dropdown
                js_click_element_script = f"""
                (() => {{
                    const interactiveElements = Array.from(document.querySelectorAll('a,button,input,select,textarea,[role="button"],[role="link"],[role="checkbox"],[role="radio"],[tabindex]:not([tabindex="-1"])'));
                    const visibleElements = interactiveElements.filter(el => {{ const style=window.getComputedStyle(el); const rect=el.getBoundingClientRect(); return style.display !== 'none' && style.visibility !== 'hidden' && style.opacity !== '0' && rect.width > 0 && rect.height > 0; }});
                    if ({index} > 0 && {index} <= visibleElements.length) {{ visibleElements[{index - 1}].click(); return true; }} return false;
                }})();"""
                await page.evaluate(js_click_element_script)
                await asyncio.sleep(0.5)
                text_locator = page.locator(f"text={option_text}")
                if await text_locator.count() > 0: await text_locator.first.click(timeout=3000); selected=True
                else: print(f"Could not find option '{option_text}' in custom dropdown")
            await asyncio.sleep(0.5)
            dom_state, sc, el, md = await self.get_updated_browser_state(f"select_dropdown_option({index},'{option_text}')")
            message = f"Selected '{option_text}' from {index}" if selected else f"Failed to select '{option_text}' from {index}"
            return self.build_action_result(selected,message,dom_state,sc,el,md,error="" if selected else "Option not found/selection failed")
        except Exception as e:
            print(f"Error in select_dropdown_option: {e}"); traceback.print_exc()
            dom_state, sc, el, md = None, "", "", {}; current_url = "unknown"
            try: dom_state, sc, el, md = await self.get_updated_browser_state("select_dropdown_option_error_recovery")
            except: pass
            try: current_url = page.url
            except: pass
            return self.build_action_result(False, str(e), dom_state, sc, el, md, error=str(e), fallback_url=current_url)

    async def drag_drop(self, action: DragDropAction = Body(...)):
        page = await self.get_current_page()
        try:
            message = ""; success = False
            if action.element_source and action.element_target:
                await page.drag_and_drop(action.element_source, action.element_target, timeout=10000)
                message = f"Dragged '{action.element_source}' to '{action.element_target}'"; success = True
            elif all(coord is not None for coord in [action.coord_source_x,action.coord_source_y,action.coord_target_x,action.coord_target_y]):
                await page.mouse.move(action.coord_source_x, action.coord_source_y); await page.mouse.down()
                await page.mouse.move(action.coord_target_x, action.coord_target_y, steps=action.steps or 5); await page.mouse.up()
                message = f"Dragged from ({action.coord_source_x},{action.coord_source_y}) to ({action.coord_target_x},{action.coord_target_y})"; success = True
            else: message = "Must provide source/target selectors or full coordinates"; success = False
            await asyncio.sleep(0.5)
            dom_state, sc, el, md = await self.get_updated_browser_state(f"drag_drop")
            return self.build_action_result(success, message, dom_state, sc, el, md, error="" if success else message)
        except Exception as e:
            print(f"Error in drag_drop: {e}"); traceback.print_exc()
            dom_state, sc, el, md = None, "", "", {}; current_url = "unknown"
            try: dom_state, sc, el, md = await self.get_updated_browser_state("drag_drop_error_recovery")
            except: pass
            try: current_url = page.url
            except: pass
            return self.build_action_result(False, str(e), dom_state, sc, el, md, error=str(e), fallback_url=current_url)

# Create singleton instance
automation_service = BrowserAutomation()

# Create API app
api_app = FastAPI()

@api_app.get("/api")
async def health_check():
    return {"status": "ok", "message": "Browser API server is running"}

# Include automation service router with /api prefix
api_app.include_router(automation_service.router, prefix="/api")

# Main entry point for Uvicorn
if __name__ == '__main__':
    uvicorn.run("browser_api:api_app", host="0.0.0.0", port=8003, workers=1)
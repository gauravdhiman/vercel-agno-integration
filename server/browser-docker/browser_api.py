import uvicorn
from fastapi import FastAPI, APIRouter, HTTPException, Body
from playwright.async_api import async_playwright, Browser, Page, BrowserContext
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
import re 
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
        if self.is_interactive: extras.append('interactive')
        if self.is_top_element: extras.append('top')
        if self.highlight_index is not None: extras.append(f'highlight:{self.highlight_index}')
        if extras: tag_str += f' [{", ".join(extras)}]'
            
        return tag_str
    
    @cached_property
    def hash(self) -> HashedDomElement:
        return HashedDomElement(
            tag_name=self.tag_name, attributes=self.attributes,
            is_visible=self.is_visible, page_coordinates=self.page_coordinates
        )
    
    def get_all_text_till_next_clickable_element(self, max_depth: int = -1) -> str:
        text_parts = []
        def collect_text(node: DOMBaseNode, current_depth: int) -> None:
            if max_depth != -1 and current_depth > max_depth: return
            if isinstance(node, DOMElementNode) and node != self and node.highlight_index is not None: return
            if isinstance(node, DOMTextNode): text_parts.append(node.text)
            elif isinstance(node, DOMElementNode):
                for child in node.children: collect_text(child, current_depth + 1)
        collect_text(self, 0)
        return '\n'.join(text_parts).strip()
    
    def clickable_elements_to_string(self, include_attributes: list[str] | None = None) -> str:
        formatted_text = []
        def process_node(node: DOMBaseNode, depth: int) -> None:
            if isinstance(node, DOMElementNode):
                if node.highlight_index is not None:
                    text = node.get_all_text_till_next_clickable_element()
                    display_attributes = []
                    if include_attributes:
                        for key, value in node.attributes.items():
                            if key in include_attributes and value and value != node.tag_name and not (text and value in text):
                                display_attributes.append(str(value))
                    attributes_str = ';'.join(display_attributes)
                    line = f'[{node.highlight_index}]<{node.tag_name}'
                    for attr_name in ['id', 'href', 'name', 'value', 'type']:
                        if attr_name in node.attributes and node.attributes[attr_name]:
                            line += f' {attr_name}="{node.attributes[attr_name]}"'
                    if text: line += f'> {text}'
                    elif attributes_str: line += f'> {attributes_str}'
                    else: line += f'> {node.tag_name.upper()}'
                    line += ' </>'
                    formatted_text.append(line)
                for child in node.children: process_node(child, depth + 1)
            elif isinstance(node, DOMTextNode):
                if not node.has_parent_with_highlight_index() and node.is_visible and node.text and node.text.strip():
                    formatted_text.append(node.text)
        process_node(self, 0)
        result_str = '\n'.join(formatted_text)
        return result_str if result_str.strip() else "No interactive elements found"

@dataclass
class DOMState:
    element_tree: DOMElementNode
    selector_map: Dict[int, DOMElementNode]
    url: str = ""
    title: str = ""
    pixels_above: int = 0
    pixels_below: int = 0

class BrowserActionResult(BaseModel):
    success: bool = True
    message: str = ""
    error: str = ""
    url: Optional[str] = None
    title: Optional[str] = None
    elements: Optional[str] = None
    screenshot_base64: Optional[str] = None
    pixels_above: int = 0
    pixels_below: int = 0
    content: Optional[str] = None
    ocr_text: Optional[str] = None
    element_count: int = 0
    interactive_elements: Optional[List[Dict[str, Any]]] = None
    viewport_width: Optional[int] = None
    viewport_height: Optional[int] = None
    class Config: arbitrary_types_allowed = True

class BrowserAutomation:
    def __init__(self):
        self.router = APIRouter()
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.pages: List[Page] = []
        self.current_page_index: int = 0
        self.logger = logging.getLogger("browser_automation_agno")
        if not self.logger.hasHandlers():
            logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        self.include_attributes = ["id", "href", "src", "alt", "aria-label", "placeholder", "name", "role", "title", "value"]
        self.screenshot_dir = os.path.join(os.getcwd(), "agno_screenshots")
        os.makedirs(self.screenshot_dir, exist_ok=True)
        
        self._register_routes()

    def _register_routes(self):
        self.router.on_startup.append(self.startup)
        self.router.on_shutdown.append(self.shutdown)
        
        self.router.add_api_route("/automation/navigate_to", self.navigate_to, methods=["POST"], response_model=BrowserActionResult)
        self.router.add_api_route("/automation/search_google", self.search_google, methods=["POST"], response_model=BrowserActionResult)
        self.router.add_api_route("/automation/go_back", self.go_back, methods=["POST"], response_model=BrowserActionResult)
        self.router.add_api_route("/automation/wait", self.wait, methods=["POST"], response_model=BrowserActionResult)
        self.router.add_api_route("/automation/click_element", self.click_element, methods=["POST"], response_model=BrowserActionResult)
        self.router.add_api_route("/automation/click_coordinates", self.click_coordinates, methods=["POST"], response_model=BrowserActionResult)
        self.router.add_api_route("/automation/input_text", self.input_text, methods=["POST"], response_model=BrowserActionResult)
        self.router.add_api_route("/automation/send_keys", self.send_keys, methods=["POST"], response_model=BrowserActionResult)
        self.router.add_api_route("/automation/switch_tab", self.switch_tab, methods=["POST"], response_model=BrowserActionResult)
        self.router.add_api_route("/automation/open_tab", self.open_tab, methods=["POST"], response_model=BrowserActionResult)
        self.router.add_api_route("/automation/close_tab", self.close_tab, methods=["POST"], response_model=BrowserActionResult)
        self.router.add_api_route("/automation/extract_content", self.extract_content, methods=["POST"], response_model=BrowserActionResult)
        self.router.add_api_route("/automation/save_pdf", self.save_pdf, methods=["POST"], response_model=BrowserActionResult)
        self.router.add_api_route("/automation/scroll_down", self.scroll_down, methods=["POST"], response_model=BrowserActionResult)
        self.router.add_api_route("/automation/scroll_up", self.scroll_up, methods=["POST"], response_model=BrowserActionResult)
        self.router.add_api_route("/automation/scroll_to_text", self.scroll_to_text, methods=["POST"], response_model=BrowserActionResult)
        self.router.add_api_route("/automation/get_dropdown_options", self.get_dropdown_options, methods=["POST"], response_model=BrowserActionResult)
        self.router.add_api_route("/automation/select_dropdown_option", self.select_dropdown_option, methods=["POST"], response_model=BrowserActionResult)
        self.router.add_api_route("/automation/drag_drop", self.drag_drop, methods=["POST"], response_model=BrowserActionResult)

    async def startup(self):
        try:
            self.logger.info("Starting Agno browser initialization...")
            current_display = os.environ.get("DISPLAY")
            if not current_display:
                self.logger.warning("DISPLAY environment variable not set. Defaulting to :99 for Playwright.")
                os.environ["DISPLAY"] = ":99" 
            else:
                self.logger.info(f"Using existing DISPLAY environment variable: {current_display}")

            playwright = await async_playwright().start()
            self.logger.info("Playwright started, launching browser...")
            
            default_args = [
                '--no-sandbox', '--disable-setuid-sandbox', '--disable-infobars',
                '--disable-blink-features=AutomationControlled',
                f'--window-size={os.getenv("RESOLUTION_WIDTH", "1024")},{os.getenv("RESOLUTION_HEIGHT", "768")}',
                '--disable-dev-shm-usage',
                '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36',
                '--disable-features=IsolateOrigins,site-per-process,TranslateUI',
                '--disable-web-security', '--ignore-certificate-errors', '--allow-running-insecure-content',
                '--autoplay-policy=no-user-gesture-required', '--disable-gpu', '--disable-software-rasterizer',
                '--disable-background-networking', '--disable-background-timer-throttling', '--disable-breakpad',
                '--disable-client-side-phishing-detection', '--disable-default-apps', '--disable-hang-monitor',
                '--disable-popup-blocking', '--disable-prompt-on-repost', '--disable-sync',
                '--force-color-profile=srgb', '--metrics-recording-only', '--no-first-run',
                '--password-store=basic', '--use-mock-keychain',
            ]

            launch_options = {
                "headless": False, "timeout": 120000, 
                "args": default_args, 
                "env": {**os.environ} # Ensure DISPLAY is passed
            }
            
            try:
                self.browser = await playwright.chromium.launch(**launch_options)
                self.logger.info("Browser launched successfully (headful mode with anti-detection args).")
            except Exception as browser_error:
                self.logger.error(f"Failed to launch browser with anti-detection args: {browser_error}", exc_info=True)
                self.logger.info("Retrying with minimal headful options (still passing DISPLAY)...")
                minimal_launch_options = {"timeout": 120000, "headless": False, "env": {**os.environ}} 
                self.browser = await playwright.chromium.launch(**minimal_launch_options)
                self.logger.info("Browser launched with minimal options (headful mode).")

            if self.browser.contexts:
                 self.context = self.browser.contexts[0]
                 self.logger.info(f"Reusing existing browser context.")
            else:
                self.context = await self.browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
                    viewport={'width': int(os.getenv("RESOLUTION_WIDTH", "1024")), 'height': int(os.getenv("RESOLUTION_HEIGHT", "768"))},
                    locale='en-US', timezone_id='America/New_York',
                    java_script_enabled=True, accept_downloads=True,
                )
                self.logger.info("New browser context created.")
            
            if self.context.pages:
                self.pages = self.context.pages
                self.current_page_index = 0
                if self.pages: 
                    await self.pages[0].bring_to_front() 
                    self.logger.info(f"Using existing page from context: {self.pages[0].url}")
                else: 
                    page = await self.context.new_page()
                    self.pages.append(page)
                    await page.goto("https://www.google.com", wait_until="domcontentloaded", timeout=60000)
                    self.logger.info("No pages in context, created new one and navigated to google.com")
            else:
                page = await self.context.new_page()
                self.logger.info("New page created in context.")
                self.pages.append(page)
                self.current_page_index = 0
                await page.goto("https://www.google.com", wait_until="domcontentloaded", timeout=60000)
                self.logger.info("Navigated new page to google.com")
                
            self.logger.info("Browser initialization completed successfully.")
        except Exception as e:
            self.logger.error(f"Browser startup error: {str(e)}", exc_info=True)
            raise RuntimeError(f"Browser initialization failed: {str(e)}")
            
    async def shutdown(self):
        if self.browser:
            await self.browser.close()
            self.logger.info("Browser closed successfully.")
        self.browser = None
        self.context = None
        self.pages = []
        self.current_page_index = 0
    
    async def get_current_page(self) -> Page:
        if not self.browser or not self.browser.is_connected():
            self.logger.error("Browser is not connected or not initialized. Attempting to restart.")
            await self.startup() 
            if not self.pages:
                 self.logger.error("Failed to recover browser pages after restart attempt.")
                 raise HTTPException(status_code=503, detail="Browser service unavailable after restart attempt.")

        if not self.pages or self.current_page_index >= len(self.pages) or self.pages[self.current_page_index].is_closed():
            self.logger.warning(f"Current page (index {self.current_page_index}, total {len(self.pages)}) is invalid or closed. Opening/activating new page.")
            if self.context:
                open_pages = [p for p in self.context.pages if not p.is_closed()]
                if open_pages:
                    self.pages = open_pages
                    self.current_page_index = 0 
                    await self.pages[self.current_page_index].bring_to_front()
                    self.logger.info(f"Switched to existing open page at index {self.current_page_index}, URL: {self.pages[self.current_page_index].url}")
                else:
                    page = await self.context.new_page()
                    await page.goto("about:blank", wait_until="domcontentloaded", timeout=30000)
                    self.pages = [page] 
                    self.current_page_index = 0
                    self.logger.info(f"All pages were closed. New page created and set as current (index {self.current_page_index}).")
            else: 
                self.logger.error("Browser context is missing unexpectedly during get_current_page.")
                raise HTTPException(status_code=500, detail="Browser context lost.")
        
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
                    'a, button, input:not([type="hidden"]), select, textarea, [role="button"], [role="link"], [role="checkbox"], [role="radio"], [tabindex]:not([tabindex="-1"])'
                ));
                const visibleElements = interactiveElements.filter(el => {
                    const style = window.getComputedStyle(el);
                    const rect = el.getBoundingClientRect();
                    return style.display !== 'none' && style.visibility !== 'hidden' && style.opacity !== '0' && rect.width > 0 && rect.height > 0 && el.offsetParent !== null;
                });
                return visibleElements.map((el, index) => {
                    const rect = el.getBoundingClientRect();
                    return {
                        index: index + 1, tagName: el.tagName.toLowerCase(), text: el.innerText || el.value || el.getAttribute('aria-label') || '',
                        attributes: getAttributes(el), isVisible: true, isInteractive: true,
                        pageCoordinates: { x: Math.round(rect.left+window.scrollX), y: Math.round(rect.top+window.scrollY), width: Math.round(rect.width), height: Math.round(rect.height) },
                        viewportCoordinates: { x: Math.round(rect.left), y: Math.round(rect.top), width: Math.round(rect.width), height: Math.round(rect.height) },
                        isInViewport: rect.top>=0 && rect.left>=0 && rect.bottom<=window.innerHeight && rect.right<=window.innerWidth
                    };
                });
            })();
            """
            elements_data = await page.evaluate(elements_js)
            root = DOMElementNode(is_visible=True, tag_name="body", is_interactive=False, is_top_element=True)
            for idx, el_data in enumerate(elements_data):
                page_coords = el_data.get('pageCoordinates', {})
                vp_coords = el_data.get('viewportCoordinates', {})
                element_node = DOMElementNode(
                    is_visible=el_data.get('isVisible', True), tag_name=el_data.get('tagName', 'div'),
                    attributes=el_data.get('attributes', {}), is_interactive=el_data.get('isInteractive', True),
                    is_in_viewport=el_data.get('isInViewport', False), highlight_index=el_data.get('index', idx + 1),
                    page_coordinates=CoordinateSet(**page_coords), viewport_coordinates=CoordinateSet(**vp_coords)
                )
                element_text = el_data.get('text', '').strip()
                if element_text:
                    text_node = DOMTextNode(is_visible=True, text=element_text); text_node.parent = element_node
                    element_node.children.append(text_node)
                selector_map[el_data.get('index', idx + 1)] = element_node
                root.children.append(element_node); element_node.parent = root
        except Exception as e:
            self.logger.error(f"Error getting selector map: {e}", exc_info=True);
            dummy = DOMElementNode(is_visible=True,tag_name="a",attributes={'href':'#'},is_interactive=True,highlight_index=1)
            dummy_text = DOMTextNode(is_visible=True, text="Fallback Element"); dummy_text.parent = dummy; dummy.children.append(dummy_text)
            selector_map[1] = dummy
        return selector_map
    
    async def get_current_dom_state(self) -> DOMState:
        page = await self.get_current_page() 
        try:
            selector_map = await self.get_selector_map()
            root = DOMElementNode(is_visible=True, tag_name="body", is_interactive=False, is_top_element=True)
            for element in selector_map.values():
                if element.parent is None: element.parent = root; root.children.append(element)
            url = page.url; title = "Unknown Title"
            try: title = await page.title() or "No Title"
            except Exception as title_err: self.logger.warning(f"Could not get page title: {title_err}")
            pixels_above = 0; pixels_below = 0
            try:
                scroll_info = await page.evaluate("""
                () => {
                    const body=document.body, html=document.documentElement;
                    const totalHeight = Math.max(body.scrollHeight,body.offsetHeight,html.clientHeight,html.scrollHeight,html.offsetHeight);
                    const scrollY = window.scrollY || window.pageYOffset;
                    const windowHeight = window.innerHeight;
                    return { pixelsAbove:Math.round(scrollY), pixelsBelow:Math.round(Math.max(0,totalHeight-scrollY-windowHeight)), totalHeight:Math.round(totalHeight), viewportHeight:Math.round(windowHeight) };
                }""")
                pixels_above = scroll_info.get('pixelsAbove',0); pixels_below = scroll_info.get('pixelsBelow',0)
            except Exception as e: self.logger.warning(f"Error getting scroll info: {e}")
            return DOMState(element_tree=root, selector_map=selector_map, url=url, title=title, pixels_above=pixels_above, pixels_below=pixels_below)
        except Exception as e:
            self.logger.error(f"Error getting DOM state: {e}", exc_info=True);
            dummy_root = DOMElementNode(is_visible=True,tag_name="body",is_interactive=False,is_top_element=True)
            dummy_map = {1: dummy_root}; current_url = "unknown"
            try:
                if page: current_url = page.url
            except: pass
            return DOMState(element_tree=dummy_root, selector_map=dummy_map, url=current_url, title="Error page", pixels_above=0, pixels_below=0)

    async def take_screenshot(self) -> str:
        try:
            page = await self.get_current_page()
            await page.wait_for_timeout(250) 
            screenshot_bytes = await page.screenshot(type='jpeg', quality=75, full_page=False, timeout=30000, scale='device') 
            return base64.b64encode(screenshot_bytes).decode('utf-8')
        except Exception as e:
            self.logger.error(f"Error taking screenshot: {e}", exc_info=True);
            return ""

    async def save_screenshot_to_file(self) -> str:
        try:
            page = await self.get_current_page()
            filename = f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{random.randint(1000,9999)}.jpg"
            filepath = os.path.join(self.screenshot_dir, filename)
            await page.screenshot(path=filepath, type='jpeg', quality=75, full_page=False)
            self.logger.info(f"Screenshot saved to {filepath}")
            return filepath
        except Exception as e:
            self.logger.error(f"Error saving screenshot: {e}", exc_info=True)
            return ""

    async def extract_ocr_text_from_screenshot(self, screenshot_base64: str) -> str:
        if not screenshot_base64: return ""
        try:
            image_bytes = base64.b64decode(screenshot_base64); image = Image.open(io.BytesIO(image_bytes))
            ocr_text = pytesseract.image_to_string(image); 
            self.logger.info(f"OCR extracted {len(ocr_text)} chars.")
            return ocr_text.strip()
        except Exception as e:
            self.logger.error(f"Error performing OCR: {e}", exc_info=True);
            return ""

    async def get_updated_browser_state(self, action_name: str) -> tuple:
        try:
            await asyncio.sleep(0.35) 
            dom_state = await self.get_current_dom_state(); screenshot = await self.take_screenshot()
            elements = dom_state.element_tree.clickable_elements_to_string(include_attributes=self.include_attributes)
            page = await self.get_current_page(); metadata = {}
            metadata['element_count'] = len(dom_state.selector_map)
            interactive_elements = []
            for idx, element in dom_state.selector_map.items():
                el_info={'index':idx,'tag_name':element.tag_name,'text':element.get_all_text_till_next_clickable_element(max_depth=2)[:100],'is_in_viewport':element.is_in_viewport} 
                for attr in ['id','href','src','alt','placeholder','name','role','title','type','aria-label']: 
                    if attr in element.attributes and element.attributes[attr]: el_info[attr] = str(element.attributes[attr])[:50] 
                interactive_elements.append(el_info)
            metadata['interactive_elements'] = interactive_elements
            try:
                vp = await page.evaluate("() => {{ return {{ width: window.innerWidth, height: window.innerHeight }}; }}")
                metadata['viewport_width'] = vp.get('width',0); metadata['viewport_height'] = vp.get('height',0)
            except Exception as e: self.logger.warning(f"Error getting viewport: {e}"); metadata['viewport_width']=0; metadata['viewport_height']=0
            ocr_text = await self.extract_ocr_text_from_screenshot(screenshot) if screenshot else ""
            metadata['ocr_text'] = ocr_text[:1000] 
            self.logger.info(f"Updated state after {action_name}: {len(dom_state.selector_map)} elements, URL: {dom_state.url if dom_state else 'N/A'}")
            return dom_state, screenshot, elements, metadata
        except Exception as e:
            self.logger.error(f"Error getting updated state after {action_name}: {e}", exc_info=True);
            return None, "", "", {}

    def build_action_result(self, success: bool, message: str, dom_state: Optional[DOMState], screenshot: str, 
                              elements: str, metadata: dict, error: str = "", content: str = None,
                              fallback_url: Optional[str] = None) -> BrowserActionResult:
        if elements is None: elements = ""
        return BrowserActionResult(
            success=success, message=message, error=error,
            url=dom_state.url if dom_state else fallback_url or "unknown_url", 
            title=dom_state.title if dom_state else "Unknown Title",
            elements=elements, screenshot_base64=screenshot,
            pixels_above=dom_state.pixels_above if dom_state else 0, 
            pixels_below=dom_state.pixels_below if dom_state else 0,
            content=content, ocr_text=metadata.get('ocr_text',""), 
            element_count=metadata.get('element_count',0),
            interactive_elements=metadata.get('interactive_elements',[]),
            viewport_width=metadata.get('viewport_width',0), 
            viewport_height=metadata.get('viewport_height',0)
        )

    async def navigate_to(self, action: GoToUrlAction = Body(...)):
        page = await self.get_current_page() 
        try:
            self.logger.info(f"Navigating to URL: {action.url}")
            response = await page.goto(action.url, wait_until="load", timeout=30000) 
            if response and not response.ok:
                 self.logger.warning(f"Navigation to {action.url} resulted in HTTP status {response.status}")
            await asyncio.sleep(2) 
            dom_state, screenshot, elements, metadata = await self.get_updated_browser_state(f"navigate_to({action.url})")
            result = self.build_action_result(True, f"Navigated to {action.url}", dom_state, screenshot, elements, metadata)
            self.logger.info(f"Navigation result: success={result.success}, url={result.url}, title='{result.title}'")
            return result
        except Exception as e:
            self.logger.error(f"Navigation error to {action.url}: {str(e)}", exc_info=True);
            dom_state, screenshot, elements, metadata = None, "", "", {}; current_url = "unknown"
            try: 
                dom_state, screenshot, elements, metadata = await self.get_updated_browser_state("navigate_error_recovery")
                if page: current_url = page.url 
            except: pass
            return self.build_action_result(False, str(e), dom_state, screenshot, elements, metadata, error=str(e), fallback_url=current_url)

    async def search_google(self, action: SearchGoogleAction = Body(...)):
        page = await self.get_current_page()
        try:
            search_url = f"https://www.google.com/search?q={action.query.replace(' ', '+')}" 
            self.logger.info(f"Searching Google for: {action.query} (URL: {search_url})")
            await page.goto(search_url, wait_until="load", timeout=30000)
            await asyncio.sleep(1.5) 
            dom_state, screenshot, elements, metadata = await self.get_updated_browser_state(f"search_google({action.query})")
            return self.build_action_result(True, f"Searched for '{action.query}'", dom_state, screenshot, elements, metadata)
        except Exception as e:
            self.logger.error(f"Search error for '{action.query}': {str(e)}", exc_info=True);
            dom_state, screenshot, elements, metadata = None, "", "", {}; current_url = "unknown"
            try: 
                dom_state, screenshot, elements, metadata = await self.get_updated_browser_state("search_error_recovery")
                if page: current_url = page.url
            except: pass
            return self.build_action_result(False, str(e), dom_state, screenshot, elements, metadata, error=str(e), fallback_url=current_url)

    async def go_back(self, _: NoParamsAction = Body(...)): 
        page = await self.get_current_page()
        try:
            self.logger.info("Navigating back in browser history.")
            await page.go_back(wait_until="load", timeout=15000)
            await asyncio.sleep(1) 
            dom_state, screenshot, elements, metadata = await self.get_updated_browser_state("go_back")
            return self.build_action_result(True, "Navigated back", dom_state, screenshot, elements, metadata)
        except Exception as e:
            self.logger.error(f"Go back error: {str(e)}", exc_info=True);
            dom_state, screenshot, elements, metadata = None, "", "", {}; current_url = "unknown"
            try: 
                dom_state, screenshot, elements, metadata = await self.get_updated_browser_state("go_back_error_recovery")
                if page: current_url = page.url
            except: pass
            return self.build_action_result(False, str(e), dom_state, screenshot, elements, metadata, error=str(e), fallback_url=current_url)

    async def wait(self, body: dict = Body(...)): 
        seconds = body.get("seconds", 3) 
        page = await self.get_current_page()
        try:
            self.logger.info(f"Waiting for {seconds} seconds.")
            await asyncio.sleep(seconds)
            dom_state, screenshot, elements, metadata = await self.get_updated_browser_state(f"wait({seconds} seconds)")
            return self.build_action_result(True, f"Waited for {seconds} seconds", dom_state, screenshot, elements, metadata)
        except Exception as e:
            self.logger.error(f"Wait error: {str(e)}", exc_info=True);
            dom_state, screenshot, elements, metadata = None, "", "", {}; current_url = "unknown"
            try: 
                dom_state, screenshot, elements, metadata = await self.get_updated_browser_state("wait_error_recovery")
                if page: current_url = page.url
            except: pass
            return self.build_action_result(False, str(e), dom_state, screenshot, elements, metadata, error=str(e), fallback_url=current_url)
    
    async def click_coordinates(self, action: ClickCoordinatesAction = Body(...)):
        page = await self.get_current_page()
        try:
            self.logger.info(f"Clicking at coordinates: ({action.x}, {action.y})")
            await page.mouse.click(action.x, action.y, delay=random.uniform(50, 150)) 
            await page.wait_for_load_state("load", timeout=15000) 
            await asyncio.sleep(random.uniform(0.5, 1.0)) 
            dom_state, screenshot, elements, metadata = await self.get_updated_browser_state(f"click_coordinates({action.x}, {action.y})")
            return self.build_action_result(True, f"Clicked at ({action.x}, {action.y})", dom_state, screenshot, elements, metadata)
        except Exception as e:
            self.logger.error(f"Error in click_coordinates ({action.x}, {action.y}): {e}", exc_info=True);
            dom_state, screenshot, elements, metadata = None, "", "", {}; current_url = "unknown"
            try: 
                dom_state, screenshot, elements, metadata = await self.get_updated_browser_state("click_coordinates_error_recovery")
                if page: current_url = page.url
            except: pass
            return self.build_action_result(False, str(e), dom_state, screenshot, elements, metadata, error=str(e), fallback_url=current_url)

    async def click_element(self, action: ClickElementAction = Body(...)):
        page = await self.get_current_page()
        self.logger.info(f"Attempting to click element with index: {action.index}")
        try:
            initial_dom_state = await self.get_current_dom_state()
            selector_map = initial_dom_state.selector_map
            if action.index not in selector_map:
                self.logger.warning(f"Element with index {action.index} not found in selector_map.")
                dom_state, sc, el, md = await self.get_updated_browser_state(f"click_element_error (index {action.index} not found)")
                return self.build_action_result(False, f"Element with index {action.index} not found in current view.", dom_state, sc, el, md, error=f"Element {action.index} not found")
            
            js_selector_script = f"""
            (() => {{
                const interactiveElements = Array.from(document.querySelectorAll('a, button, input:not([type="hidden"]), select, textarea, [role="button"], [role="link"], [role="checkbox"], [role="radio"], [tabindex]:not([tabindex="-1"])'));
                const visibleElements = interactiveElements.filter(el => {{ const style = window.getComputedStyle(el); const rect = el.getBoundingClientRect(); return style.display !== 'none' && style.visibility !== 'hidden' && style.opacity !== '0' && rect.width > 0 && rect.height > 0 && el.offsetParent !== null; }});
                if ({action.index} > 0 && {action.index} <= visibleElements.length) return visibleElements[{action.index - 1}];
                return null;
            }})();"""
            target_element_handle = await page.evaluate_handle(js_selector_script)
            
            click_success = False; error_message = ""
            if await target_element_handle.evaluate("node => node !== null"):
                try: 
                    self.logger.info(f"Element handle found for index {action.index}. Attempting click.")
                    await target_element_handle.scroll_into_view_if_needed(timeout=5000) 
                    await asyncio.sleep(random.uniform(0.1, 0.3)) 
                    await target_element_handle.click(timeout=15000, force=True, delay=random.uniform(50,150), trial=True) 
                    click_success = True
                    self.logger.info(f"Successfully clicked element at index {action.index}")
                except Exception as click_error: 
                    error_message = f"Error clicking element at index {action.index}: {str(click_error)}"
                    self.logger.error(error_message, exc_info=True)
            else: 
                error_message = f"Could not locate live element handle for index {action.index} to click."
                self.logger.warning(error_message)

            try: await page.wait_for_load_state("networkidle", timeout=15000) 
            except Exception as e: self.logger.warning(f"Timeout/Error waiting for network idle after click: {e}"); await asyncio.sleep(2) 
            
            dom_state, sc, el, md = await self.get_updated_browser_state(f"click_element({action.index})")
            final_message = f"Clicked element {action.index}" if click_success else f"Failed to click element {action.index}. Error: {error_message}"
            return self.build_action_result(click_success, final_message, dom_state, sc, el, md, error=error_message if not click_success else "")
        except Exception as e:
            self.logger.error(f"Overall error in click_element for index {action.index}: {str(e)}", exc_info=True);
            dom_state, sc, el, md = None, "", "", {}; current_url = "unknown"
            try: 
                dom_state, sc, el, md = await self.get_updated_browser_state("click_element_error_recovery")
                if page: current_url = page.url
            except: pass
            return self.build_action_result(False, str(e), dom_state, sc, el, md, error=str(e), fallback_url=current_url)
            
    async def input_text(self, action: InputTextAction = Body(...)):
        page = await self.get_current_page()
        self.logger.info(f"Inputting text into element {action.index}: '{action.text[:50]}...'")
        try:
            initial_dom_state = await self.get_current_dom_state(); selector_map = initial_dom_state.selector_map
            if action.index not in selector_map:
                dom_state, sc, el, md = await self.get_updated_browser_state(f"input_text_error (index {action.index} not found)")
                return self.build_action_result(False, f"Element {action.index} not found", dom_state, sc, el, md, error=f"Element {action.index} not found")
            
            js_selector_script = f"""
            (() => {{
                const interactiveElements = Array.from(document.querySelectorAll('a, button, input:not([type="hidden"]), select, textarea, [role="button"], [role="link"], [role="checkbox"], [role="radio"], [tabindex]:not([tabindex="-1"])'));
                const visibleElements = interactiveElements.filter(el => {{ const style = window.getComputedStyle(el); const rect = el.getBoundingClientRect(); return style.display !== 'none' && style.visibility !== 'hidden' && style.opacity !== '0' && rect.width > 0 && rect.height > 0 && el.offsetParent !== null; }});
                if ({action.index} > 0 && {action.index} <= visibleElements.length) return visibleElements[{action.index - 1}];
                return null;
            }})();"""
            target_element_handle = await page.evaluate_handle(js_selector_script)
            input_success = False; error_message = ""

            if await target_element_handle.evaluate("node => node !== null"):
                try: 
                    await target_element_handle.scroll_into_view_if_needed(timeout=5000)
                    await target_element_handle.fill(action.text, timeout=10000) 
                    input_success = True
                    self.logger.info(f"Successfully input text into element {action.index}")
                except Exception as input_error: 
                    error_message = f"Error inputting text: {str(input_error)}"
                    self.logger.error(error_message, exc_info=True)
            else: 
                error_message = f"Could not locate live element handle for input at index {action.index}."
                self.logger.warning(error_message)
            
            await asyncio.sleep(0.5) 
            dom_state, sc, el, md = await self.get_updated_browser_state(f"input_text({action.index}, '{action.text}')")
            final_message = f"Input '{action.text}' into element {action.index}" if input_success else f"Failed input into element {action.index}. Error: {error_message}"
            return self.build_action_result(input_success, final_message, dom_state, sc, el, md, error=error_message if not input_success else "")
        except Exception as e:
            self.logger.error(f"Overall error in input_text for index {action.index}: {str(e)}", exc_info=True);
            dom_state, sc, el, md = None, "", "", {}; current_url = "unknown"
            try: 
                dom_state, sc, el, md = await self.get_updated_browser_state("input_text_error_recovery")
                if page: current_url = page.url
            except: pass
            return self.build_action_result(False, str(e), dom_state, sc, el, md, error=str(e), fallback_url=current_url)

    async def send_keys(self, action: SendKeysAction = Body(...)):
        page = await self.get_current_page()
        try:
            self.logger.info(f"Sending keys: {action.keys}")
            # Split keys by '+' for combinations like 'Control+A', but also handle single keys
            # Use page.keyboard.press for more control over individual key events if needed.
            # For simplicity, if '+' is in keys, assume it's a sequence Playwright handles directly.
            # Otherwise, type character by character.
            if '+' in action.keys and any(mod in action.keys.lower() for mod in ['control', 'alt', 'shift', 'meta']):
                 await page.keyboard.press(action.keys, delay=random.uniform(30,100))
            else:
                for char_or_key in action.keys: # Type character by character for simple text
                    await page.keyboard.type(char_or_key, delay=random.uniform(50,150))
            
            await page.wait_for_load_state("networkidle", timeout=10000) 
            dom_state, sc, el, md = await self.get_updated_browser_state(f"send_keys({action.keys})")
            return self.build_action_result(True, f"Sent keys: {action.keys}", dom_state, sc, el, md)
        except Exception as e:
            self.logger.error(f"Error in send_keys '{action.keys}': {str(e)}", exc_info=True);
            dom_state, sc, el, md = None, "", "", {}; current_url = "unknown"
            try: 
                dom_state, sc, el, md = await self.get_updated_browser_state("send_keys_error_recovery")
                if page: current_url = page.url
            except: pass
            return self.build_action_result(False, str(e), dom_state, sc, el, md, error=str(e), fallback_url=current_url)

    async def switch_tab(self, action: SwitchTabAction = Body(...)):
        page = await self.get_current_page() 
        try:
            self.logger.info(f"Switching to tab: {action.page_id}")
            if 0 <= action.page_id < len(self.pages):
                self.current_page_index = action.page_id
                current_page = await self.get_current_page() 
                await current_page.bring_to_front()
                await current_page.wait_for_load_state("domcontentloaded", timeout=15000)
                dom_state, sc, el, md = await self.get_updated_browser_state(f"switch_tab({action.page_id})")
                return self.build_action_result(True, f"Switched to tab {action.page_id}", dom_state, sc, el, md)
            else:
                err_msg = f"Tab {action.page_id} not found. Valid: 0-{len(self.pages)-1 if self.pages else 'None'}"
                self.logger.warning(err_msg)
                csd, css, cse, csm = await self.get_updated_browser_state("switch_tab_error (invalid_index)")
                return self.build_action_result(False, err_msg, csd, css, cse, csm, error=err_msg)
        except Exception as e:
            self.logger.error(f"Error in switch_tab to {action.page_id}: {str(e)}", exc_info=True);
            dom_state, sc, el, md = None, "", "", {}; current_url = "unknown"
            try: 
                dom_state, sc, el, md = await self.get_updated_browser_state("switch_tab_error_recovery")
                if page: current_url = page.url
            except: pass
            return self.build_action_result(False, str(e), dom_state, sc, el, md, error=str(e), fallback_url=current_url)

    async def open_tab(self, action: OpenTabAction = Body(...)):
        page = await self.get_current_page() 
        try:
            self.logger.info(f"Opening new tab with URL: {action.url}")
            if not self.context:
                 self.logger.error("Browser context not available for opening new tab.")
                 raise Exception("Browser context unavailable")
            new_page = await self.context.new_page() 
            await new_page.goto(action.url, wait_until="load", timeout=30000) 
            await asyncio.sleep(1.5) 
            self.pages.append(new_page); self.current_page_index=len(self.pages)-1
            await new_page.bring_to_front()
            dom_state, sc, el, md = await self.get_updated_browser_state(f"open_tab({action.url})")
            return self.build_action_result(True, f"Opened tab {action.url}. Active tab index: {self.current_page_index}.", dom_state, sc, el, md)
        except Exception as e:
            self.logger.error(f"Error opening tab for URL {action.url}: {str(e)}", exc_info=True);
            dom_state, sc, el, md = None, "", "", {}; current_url = "unknown"
            try: 
                dom_state, sc, el, md = await self.get_updated_browser_state("open_tab_error_recovery")
                if page: current_url = page.url
            except: pass
            return self.build_action_result(False, str(e), dom_state, sc, el, md, error=str(e), fallback_url=current_url)

    async def close_tab(self, action: CloseTabAction = Body(...)):
        page = await self.get_current_page()
        try:
            self.logger.info(f"Closing tab with page_id: {action.page_id}")
            if not (0 <= action.page_id < len(self.pages)):
                err_msg = f"Tab {action.page_id} not found. Valid indices: 0-{len(self.pages)-1 if self.pages else 'None'}"
                self.logger.warning(err_msg)
                csd, css, cse, csm = await self.get_updated_browser_state("close_tab_error (invalid_index)")
                return self.build_action_result(False, err_msg, csd, css, cse, csm, error=err_msg)
            
            if len(self.pages) == 1 and action.page_id == 0:
                self.logger.info("Attempting to close the last tab. Creating a new blank tab first.")
                if not self.context: raise Exception("Browser context unavailable to create new tab.")
                bp = await self.context.new_page(); await bp.goto("about:blank"); self.pages.append(bp)
            
            page_to_close = self.pages[action.page_id]; url_closed = page_to_close.url
            if not page_to_close.is_closed(): 
                await page_to_close.close(timeout=5000) 
                self.logger.info(f"Closed page at index {action.page_id}, URL: {url_closed}")
            else:
                self.logger.info(f"Page at index {action.page_id} (URL: {url_closed}) was already closed.")

            self.pages.pop(action.page_id)

            if not self.pages: 
                self.logger.info("All tabs were closed. Creating a new blank tab.")
                if not self.context: raise Exception("Browser context unavailable to create new tab after closing all.")
                bp = await self.context.new_page(); await bp.goto("about:blank"); self.pages.append(bp); self.current_page_index=0
            elif self.current_page_index >= action.page_id: 
                self.current_page_index=max(0,self.current_page_index-1)
                self.current_page_index=min(self.current_page_index,len(self.pages)-1 if self.pages else 0) 
            
            active_page = await self.get_current_page(); await active_page.bring_to_front()
            dom_state, sc, el, md = await self.get_updated_browser_state(f"close_tab({action.page_id})")
            return self.build_action_result(True, f"Closed tab {action.page_id} (URL: {url_closed}). Active tab index: {self.current_page_index}.", dom_state, sc, el, md)
        except Exception as e:
            self.logger.error(f"Error in close_tab for page_id {action.page_id}: {str(e)}", exc_info=True);
            dom_state, sc, el, md = None, "", "", {}; current_url = "unknown"
            try: 
                dom_state, sc, el, md = await self.get_updated_browser_state("close_tab_error_recovery")
                if page: current_url = page.url
            except: pass
            return self.build_action_result(False, str(e), dom_state, sc, el, md, error=str(e), fallback_url=current_url)
    
    async def extract_content(self, action: ExtractContentAction = Body(...)):
        page = await self.get_current_page()
        try:
            self.logger.info(f"Extracting content for goal: {action.goal}")
            extracted_text = await page.evaluate("""
            (() => {
                const mainContentSelectors = ['article', 'main', '[role="main"]', '.content', '#content', '.post-content', '.entry-content', 'body']; 
                let mainElement = null;
                for (const selector of mainContentSelectors) {
                    mainElement = document.querySelector(selector);
                    if (mainElement) break;
                }
                if (!mainElement) mainElement = document.body;
                const selectorsToRemove = ['script', 'style', 'nav', 'header', 'footer', 'aside', 'form', 'noscript', '.advertisement', '.ad', '.sidebar', 'iframe', 'figure > figcaption', 'figure > img', 'img']; 
                selectorsToRemove.forEach(selector => { mainElement.querySelectorAll(selector).forEach(el => el.remove()); });
                let text = ""; const walker = document.createTreeWalker(mainElement, NodeFilter.SHOW_TEXT, null, false); let node;
                while(node = walker.nextNode()) {
                    const parent = node.parentElement;
                    if (parent && ['P', 'H1', 'H2', 'H3', 'H4', 'H5', 'H6', 'LI', 'BLOCKQUOTE', 'PRE', 'DIV', 'TD', 'TH'].includes(parent.tagName)) { 
                         text += node.nodeValue.trim() + '\\n';
                    } else { text += node.nodeValue.trim() + ' '; }
                }
                return text.replace(/\\n\\s*\\n/g, '\\n').trim();
            })();
            """)
            dom_state, sc, el, md = await self.get_updated_browser_state(f"extract_content({action.goal})")
            return self.build_action_result(True, f"Content extracted for: {action.goal}", dom_state, sc, el, md, content=extracted_text)
        except Exception as e:
            self.logger.error(f"Error in extract_content for goal '{action.goal}': {str(e)}", exc_info=True);
            dom_state, sc, el, md = None, "", "", {}; current_url = "unknown"
            try: 
                dom_state, sc, el, md = await self.get_updated_browser_state("extract_content_error_recovery")
                if page: current_url = page.url
            except: pass
            return self.build_action_result(False, str(e), dom_state, sc, el, md, error=str(e), fallback_url=current_url)

    async def save_pdf(self, _: NoParamsAction = Body(...)): 
        page = await self.get_current_page()
        try:
            self.logger.info("Saving current page as PDF.")
            filename=f"page_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{random.randint(1000,9999)}.pdf"; pdf_ws_path=f"/workspace/{filename}"
            await page.pdf(path=pdf_ws_path, format='A4', print_background=True, timeout=60000) 
            dom_state, sc, el, md = await self.get_updated_browser_state("save_pdf")
            return self.build_action_result(True, f"Saved PDF: {filename} (in /workspace)", dom_state, sc, el, md) 
        except Exception as e:
            self.logger.error(f"Error in save_pdf: {str(e)}", exc_info=True);
            dom_state, sc, el, md = None, "", "", {}; current_url = "unknown"
            try: 
                dom_state, sc, el, md = await self.get_updated_browser_state("save_pdf_error_recovery")
                if page: current_url = page.url
            except: pass
            return self.build_action_result(False, str(e), dom_state, sc, el, md, error=str(e), fallback_url=current_url)

    async def scroll_down(self, action: ScrollAction = Body(default_factory=ScrollAction)):
        page = await self.get_current_page()
        try:
            amount_str = "one page"
            if action.amount is not None: 
                await page.mouse.wheel(0, action.amount); amount_str=f"{action.amount} units"
            else: 
                await page.evaluate("window.scrollBy(0, window.innerHeight);")
            self.logger.info(f"Scrolled down by {amount_str}")
            await page.wait_for_timeout(500)
            dom_state, sc, el, md = await self.get_updated_browser_state(f"scroll_down({amount_str})")
            return self.build_action_result(True, f"Scrolled down by {amount_str}", dom_state, sc, el, md)
        except Exception as e:
            self.logger.error(f"Error in scroll_down: {str(e)}", exc_info=True);
            dom_state, sc, el, md = None, "", "", {}; current_url = "unknown"
            try: 
                dom_state, sc, el, md = await self.get_updated_browser_state("scroll_down_error_recovery")
                if page: current_url = page.url
            except: pass
            return self.build_action_result(False, str(e), dom_state, sc, el, md, error=str(e), fallback_url=current_url)

    async def scroll_up(self, action: ScrollAction = Body(default_factory=ScrollAction)):
        page = await self.get_current_page()
        try:
            amount_str = "one page"
            if action.amount is not None: 
                await page.mouse.wheel(0, -action.amount); amount_str=f"{action.amount} units"
            else: 
                await page.evaluate("window.scrollBy(0, -window.innerHeight);")
            self.logger.info(f"Scrolled up by {amount_str}")
            await page.wait_for_timeout(500)
            dom_state, sc, el, md = await self.get_updated_browser_state(f"scroll_up({amount_str})")
            return self.build_action_result(True, f"Scrolled up by {amount_str}", dom_state, sc, el, md)
        except Exception as e:
            self.logger.error(f"Error in scroll_up: {str(e)}", exc_info=True);
            dom_state, sc, el, md = None, "", "", {}; current_url = "unknown"
            try: 
                dom_state, sc, el, md = await self.get_updated_browser_state("scroll_up_error_recovery")
                if page: current_url = page.url
            except: pass
            return self.build_action_result(False, str(e), dom_state, sc, el, md, error=str(e), fallback_url=current_url)
            
    async def scroll_to_text(self, body: dict = Body(...)): 
        text_to_find = body.get("text")
        page = await self.get_current_page() 
        if not text_to_find:
            return self.build_action_result(False, "Text to find required", None, "", "", {}, error="Missing text")
        try:
            self.logger.info(f"Scrolling to text: '{text_to_find}'")
            found = False
            try:
                locator = page.locator(f"text=/{re.escape(text_to_find)}/i").first 
                if await locator.count() > 0:
                    await locator.scroll_into_view_if_needed(timeout=10000) 
                    found = True
                if found: await asyncio.sleep(0.75) 
            except Exception as scroll_ex: self.logger.warning(f"Playwright locator scroll for '{text_to_find}' failed: {scroll_ex}")
            
            if not found: 
                self.logger.info(f"Fallback: Trying JS scroll for '{text_to_find}'")
                js_text_to_find = json.dumps(text_to_find)
                scroll_script = f"""
                (() => {{
                    const textToFind = {js_text_to_find};
                    const allElements = Array.from(document.querySelectorAll('*'));
                    for (const el of allElements) {{
                        if (el.innerText && el.innerText.toLowerCase().includes(textToFind.toLowerCase())) {{
                            el.scrollIntoView({{behavior: 'smooth', block: 'center'}}); return true;
                        }} }} return false;
                }})();"""
                found = await page.evaluate(scroll_script)
                if found: await asyncio.sleep(1.0) 

            dom_state, sc, el, md = await self.get_updated_browser_state(f"scroll_to_text({text_to_find})")
            message = f"Scrolled to text: '{text_to_find}'" if found else f"Text '{text_to_find}' not found or not visible."
            return self.build_action_result(found, message, dom_state, sc, el, md, error="" if found else f"Text '{text_to_find}' not found")
        except Exception as e:
            self.logger.error(f"Error in scroll_to_text for '{text_to_find}': {str(e)}", exc_info=True);
            dom_state, sc, el, md = None, "", "", {}; current_url = "unknown"
            try: 
                dom_state, sc, el, md = await self.get_updated_browser_state("scroll_to_text_error_recovery")
                if page: current_url = page.url
            except: pass
            return self.build_action_result(False, str(e), dom_state, sc, el, md, error=str(e), fallback_url=current_url)

    async def get_dropdown_options(self, body: dict = Body(...)): 
        index = body.get("index")
        page = await self.get_current_page()
        if index is None: return self.build_action_result(False, "Index required", None, "", "", {}, error="Missing index")
        try:
            self.logger.info(f"Getting dropdown options for element at index: {index}")
            initial_dom_state=await self.get_current_dom_state(); selector_map=initial_dom_state.selector_map
            if index not in selector_map:
                dom_state, sc, el, md = await self.get_updated_browser_state(f"get_dropdown_options_error (index {index} not found)")
                return self.build_action_result(False, f"Element {index} not found", dom_state, sc, el, md, error=f"Element {index} not found")
            
            element_node = selector_map[index]; options = []
            js_selector_script = f"""
            (() => {{
                const interactiveElements = Array.from(document.querySelectorAll('a, button, input:not([type="hidden"]), select, textarea, [role="button"], [role="link"], [role="checkbox"], [role="radio"], [tabindex]:not([tabindex="-1"])'));
                const visibleElements = interactiveElements.filter(el => {{ const style = window.getComputedStyle(el); const rect = el.getBoundingClientRect(); return style.display !== 'none' && style.visibility !== 'hidden' && style.opacity !== '0' && rect.width > 0 && rect.height > 0 && el.offsetParent !== null; }});
                if ({index} > 0 && {index} <= visibleElements.length) return visibleElements[{index - 1}];
                return null;
            }})();"""
            target_element_handle = await page.evaluate_handle(js_selector_script)

            if await target_element_handle.evaluate("node => node !== null"):
                if element_node.tag_name.lower() == 'select':
                    options = await target_element_handle.evaluate("selectElement => Array.from(selectElement.options).map((opt, idx) => ({index:idx,text:opt.text,value:opt.value}))")
                else: 
                    self.logger.info(f"Element {index} is not a <select>, attempting generic option discovery.")
                    options = [{"index":0,"text":"Option A (Custom Placeholder)","value":"A"},{"index":1,"text":"Option B (Custom Placeholder)","value":"B"}] 
            else:
                 self.logger.warning(f"Could not get handle for dropdown element at index {index}.")
            
            dom_state, sc, el, md = await self.get_updated_browser_state(f"get_dropdown_options({index})")
            return self.build_action_result(True, f"Retrieved {len(options)} options for dropdown at index {index}", dom_state, sc, el, md, content=json.dumps(options))
        except Exception as e:
            self.logger.error(f"Error in get_dropdown_options for index {index}: {str(e)}", exc_info=True);
            dom_state, sc, el, md = None, "", "", {}; current_url = "unknown"
            try: 
                dom_state, sc, el, md = await self.get_updated_browser_state("get_dropdown_options_error_recovery")
                if page: current_url = page.url
            except: pass
            return self.build_action_result(False, str(e), dom_state, sc, el, md, error=str(e), fallback_url=current_url)

    async def select_dropdown_option(self, body: dict = Body(...)): 
        index = body.get("index"); option_text = body.get("text")
        page = await self.get_current_page()
        if index is None or option_text is None: return self.build_action_result(False, "Index and option text required", None, "","","", error="Missing index or text")
        try:
            self.logger.info(f"Selecting option '{option_text}' from dropdown at index {index}")
            initial_dom_state = await self.get_current_dom_state(); selector_map = initial_dom_state.selector_map
            if index not in selector_map:
                dom_state, sc, el, md = await self.get_updated_browser_state(f"select_dropdown_error (index {index} not found)")
                return self.build_action_result(False, f"Element {index} not found", dom_state, sc, el, md, error=f"Element {index} not found")
            
            js_selector_script = f"""
            (() => {{
                const interactiveElements = Array.from(document.querySelectorAll('a, button, input:not([type="hidden"]), select, textarea, [role="button"], [role="link"], [role="checkbox"], [role="radio"], [tabindex]:not([tabindex="-1"])'));
                const visibleElements = interactiveElements.filter(el => {{ const style = window.getComputedStyle(el); const rect = el.getBoundingClientRect(); return style.display !== 'none' && style.visibility !== 'hidden' && style.opacity !== '0' && rect.width > 0 && rect.height > 0 && el.offsetParent !== null; }});
                if ({index} > 0 && {index} <= visibleElements.length) return visibleElements[{index - 1}];
                return null;
            }})();"""
            target_element_handle = await page.evaluate_handle(js_selector_script)
            selected = False

            if await target_element_handle.evaluate("node => node !== null"):
                if await target_element_handle.evaluate("node => node.tagName.toLowerCase() === 'select'"):
                    await target_element_handle.select_option(label=option_text, timeout=10000) 
                    selected = True
                else: 
                    await target_element_handle.click(timeout=5000)
                    await asyncio.sleep(0.75) 
                    option_locator = page.locator(f"text=/{re.escape(option_text)}/i").first 
                    if await option_locator.count() > 0:
                        await option_locator.click(timeout=5000)
                        selected = True
                    else: self.logger.warning(f"Could not find option '{option_text}' in custom dropdown after click.")
            else: self.logger.warning(f"Could not get handle for dropdown element at index {index}.")

            await asyncio.sleep(0.75) 
            dom_state, sc, el, md = await self.get_updated_browser_state(f"select_dropdown_option({index},'{option_text}')")
            message = f"Selected '{option_text}' from dropdown {index}" if selected else f"Failed to select '{option_text}' from dropdown {index}"
            return self.build_action_result(selected,message,dom_state,sc,el,md,error="" if selected else "Option not found/selection failed")
        except Exception as e:
            self.logger.error(f"Error in select_dropdown_option for index {index}, text '{option_text}': {str(e)}", exc_info=True);
            dom_state, sc, el, md = None, "", "", {}; current_url = "unknown"
            try: 
                dom_state, sc, el, md = await self.get_updated_browser_state("select_dropdown_option_error_recovery")
                if page: current_url = page.url
            except: pass
            return self.build_action_result(False, str(e), dom_state, sc, el, md, error=str(e), fallback_url=current_url)

    async def drag_drop(self, action: DragDropAction = Body(...)):
        page = await self.get_current_page()
        try:
            self.logger.info(f"Performing drag and drop action: {action.model_dump_json(exclude_none=True)}")
            message = ""; success = False
            if action.element_source and action.element_target:
                await page.drag_and_drop(action.element_source, action.element_target, timeout=15000) 
                message = f"Dragged element '{action.element_source}' to '{action.element_target}'"; success = True
            elif all(coord is not None for coord in [action.coord_source_x,action.coord_source_y,action.coord_target_x,action.coord_target_y]):
                await page.mouse.move(action.coord_source_x, action.coord_source_y, steps=5) 
                await page.mouse.down()
                await asyncio.sleep(random.uniform(0.1, 0.3)) 
                await page.mouse.move(action.coord_target_x, action.coord_target_y, steps=action.steps or 10)
                await asyncio.sleep(random.uniform(0.1, 0.3)) 
                await page.mouse.up()
                message = f"Dragged from ({action.coord_source_x},{action.coord_source_y}) to ({action.coord_target_x},{action.coord_target_y})"; success = True
            else: message = "Must provide source/target element selectors or full coordinates for drag and drop"; success = False
            await asyncio.sleep(0.75) 
            dom_state, sc, el, md = await self.get_updated_browser_state(f"drag_drop")
            return self.build_action_result(success, message, dom_state, sc, el, md, error="" if success else message)
        except Exception as e:
            self.logger.error(f"Error in drag_drop: {str(e)}", exc_info=True);
            dom_state, sc, el, md = None, "", "", {}; current_url = "unknown"
            try: 
                dom_state, sc, el, md = await self.get_updated_browser_state("drag_drop_error_recovery")
                if page: current_url = page.url
            except: pass
            return self.build_action_result(False, str(e), dom_state, sc, el, md, error=str(e), fallback_url=current_url)

automation_service = BrowserAutomation()
api_app = FastAPI()

@api_app.get("/api")
async def health_check(): return {"status": "ok", "message": "Browser API server is running"}
api_app.include_router(automation_service.router, prefix="/api")

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO) 
    uvicorn.run("browser_api:api_app", host="0.0.0.0", port=8003, workers=1)
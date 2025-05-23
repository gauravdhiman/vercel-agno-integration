# frontend_tool_schemas.py
from agno_adapter import FrontendToolSchema
import sys
import os
# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from common.frontend_tools import (
    FrontendToolName,
    get_all_frontend_tool_schemas
)

# Convert the Python dictionaries to FrontendToolSchema objects
frontend_tools = [
    FrontendToolSchema(
        name=schema["name"],
        description=schema["description"],
        parameters=schema["parameters"]
    )
    for schema in get_all_frontend_tool_schemas()
]

# Constants for easy reference in other parts of the backend code
ASK_USER_CONFIRMATION = FrontendToolName.ASK_USER_CONFIRMATION.value
DISPLAY_PRODUCT_CARD = FrontendToolName.DISPLAY_PRODUCT_CARD.value
DISPLAY_TOOL_INFO = FrontendToolName.DISPLAY_TOOL_INFO.value
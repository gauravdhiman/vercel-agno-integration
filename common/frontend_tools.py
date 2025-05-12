# frontend_tools.py
# GENERATED FILE - DO NOT EDIT DIRECTLY
# This file is auto-generated from frontend_tools.ts
# To make changes, edit the TypeScript file and run the generator

from enum import Enum
from typing import Dict, List, Any, Optional, Union

# -----------------------------------------------------------------------------
# Tool Name Enum
# -----------------------------------------------------------------------------

class FrontendToolName(str, Enum):
    """Enum for all available frontend tool names"""
    ASK_USER_CONFIRMATION = "ask_user_confirmation"
    DISPLAY_PRODUCT_CARD = "display_product_card"
    DISPLAY_TOOL_INFO = "display_tool_info"
    CHANGE_BACKGROUND_COLOR = "change_background_color"

# -----------------------------------------------------------------------------
# Schema Definitions
# -----------------------------------------------------------------------------

def get_ask_user_confirmation_schema() -> Dict[str, Any]:
    """Generate schema for the ask_user_confirmation tool"""
    return {
        "name": FrontendToolName.ASK_USER_CONFIRMATION,
        "description": "Use this tool for questions, confirmation or approval kind of interaction with user in UI. The UI will shows a modal with customizable buttons for user to select. If asking question, always have 'Others' option in addition to applicable ones.",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Title / header of the confirmation modal."
                },
                "question_text": {
                    "type": "string",
                    "description": "The question to present to the user for confirmation."
                },
                "confirmation_context": {
                    "type": "string",
                    "description": "Optional additional context or details to display with the confirmation question."
                },
                "buttons": {
                    "type": "array",
                    "description": "Array of button configurations to display in the modal. If not provided, default \'Confirm\' and \'Cancel\' buttons will be shown.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "label": {
                                "type": "string",
                                "description": "The text to display on the button."
                            },
                            "value": {
                                "type": ["string", "boolean", "number"],
                                "description": "The value to return when this button is clicked."
                            },
                            "style": {
                                "type": "string",
                                "enum": ["primary", "secondary", "danger"],
                                "description": "The visual style of the button. Primary is highlighted, secondary is less prominent, danger is for destructive actions."
                            }
                        },
                        "required": ["label", "value"]
                    }
                }
            },
            "required": ["question_text"]
        }
    }

def get_display_product_card_schema() -> Dict[str, Any]:
    """Generate schema for the display_product_card tool"""
    return {
        "name": FrontendToolName.DISPLAY_PRODUCT_CARD,
        "description": "Use this tool to show the product details in UI whenever user is asking about any product or want to see product details.",
        "parameters": {
            "type": "object",
            "properties": {
                "product_id": {"type": "string", "description": "The unique ID of the product."},
                "product_name": {"type": "string", "description": "Name of the product."},
                "price": {"type": "number", "description": "Price of the product."},
                "image_url": {"type": "string", "format": "uri", "description": "URL of the product image."}
            },
            "required": ["product_name", "price"]
        }
    }


def get_change_background_color_schema() -> Dict[str, Any]:
    """Generate schema for the change_background_color tool"""
    return {
        "name": FrontendToolName.CHANGE_BACKGROUND_COLOR,
        "description": "This will set / change the background color in frontend to the given hex color code like #FFC0CB",
        "parameters": {
            "type": "object",
            "properties": {
                "colorHexCode": {
                    "type": "string",
                    "description": "The hex code of the color to which the background will be set, like $FFC0CB"
                }
            },
            "required": ["colorHexCode"]
        }
    }

def get_all_frontend_tool_schemas() -> List[Dict[str, Any]]:
    """Get all frontend tool schemas"""
    return [
        get_ask_user_confirmation_schema(),
        get_display_product_card_schema(),
        get_change_background_color_schema()
    ]

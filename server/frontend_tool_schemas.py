# frontend_tool_schemas.py
from agno_adapter import FrontendToolSchema

frontend_tools = [
    FrontendToolSchema(
        name="ask_user_confirmation",
        description="Asks the user for confirmation on a specific question. The UI will show a modal with customizable buttons.",
        parameters={
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
                    "description": "Array of button configurations to display in the modal. If not provided, default 'Confirm' and 'Cancel' buttons will be shown.",
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
    ),
    FrontendToolSchema(
        name="display_product_card",
        description="Shows a product card in the UI with details about a specific product.",
        parameters={
            "type": "object",
            "properties": {
                "product_id": {"type": "string", "description": "The unique ID of the product."},
                "product_name": {"type": "string", "description": "Name of the product."},
                "price": {"type": "number", "description": "Price of the product."},
                "image_url": {"type": "string", "format": "uri", "description": "URL of the product image."}
            },
            "required": ["product_id", "product_name", "price"]
        }
    ),
    FrontendToolSchema(
        name="display_tool_info",
        description="Displays detailed information about a tool in the UI including execution status and results. Shows a spinner for in-progress tools and allows expanding completed tools to view details.",
        parameters={
            "type": "object",
            "properties": {
                "tool_name": {
                    "type": "string",
                    "description": "The name of the tool to display."
                },
                "tool_description": {
                    "type": "string",
                    "description": "Detailed description of the tool's functionality."
                },
                "tool_id": {
                    "type": "string",
                    "description": "Optional unique identifier for the tool call."
                },
                "tool_parameters": {
                    "type": "object",
                    "description": "Parameters passed to the tool."
                },
                "tool_status": {
                    "type": "string",
                    "enum": ["pending", "executing", "completed", "failed"],
                    "description": "Current execution status of the tool. 'pending' shows a spinner with gray badge, 'executing' shows a spinner with blue badge, 'completed' shows a green badge, 'failed' shows a red badge."
                },
                "tool_output": {
                    "type": "object",
                    "description": "Output or results from the tool execution. Only shown when the user expands the card."
                },
                "tool_error": {
                    "type": "string",
                    "description": "Error message if the tool execution failed. Only shown when the user expands the card."
                }
            },
            "required": ["tool_name", "tool_description", "tool_status"]
        }
    )
]
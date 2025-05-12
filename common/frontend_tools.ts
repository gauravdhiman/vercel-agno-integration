/**
 * Frontend Tools Schema Definitions
 *
 * This file serves as the single source of truth for frontend tool schemas
 * used by both the frontend and backend. The TypeScript definitions here
 * are used directly by the frontend and are converted to Python for the backend.
 */

// -----------------------------------------------------------------------------
// Tool Name Enums
// -----------------------------------------------------------------------------

/**
 * Enum for all available frontend tool names
 */
export enum FrontendToolName {
  ASK_USER_QUESTION_CONFIRMATION_APPROVAL_INPUT = "ask_user_question_confirmation_approval_input",
  DISPLAY_PRODUCT_CARD = "display_product_card",
  DISPLAY_TOOL_INFO = "display_tool_info",
  CHANGE_BACKGROUND_COLOR = "change_background_color"
}

// -----------------------------------------------------------------------------
// Tool Parameter Types
// -----------------------------------------------------------------------------

/**
 * Button configuration for confirmation modals
 */
export interface ButtonConfig {
  /** The text to display on the button */
  label: string;

  /** The value to return when this button is clicked */
  value: string | boolean | number;

  /** The visual style of the button */
  style?: "primary" | "secondary" | "danger";
}

/**
 * Parameters for the ask_user_question_confirmation_approval_input tool
 */
export interface AskUserConfirmationParams {
  /** Title / header of the confirmation modal */
  title?: string;

  /** The question to present to the user for confirmation */
  question_text: string;

  /** Optional additional context or details to display with the confirmation question */
  confirmation_context?: string;

  /**
   * Array of button configurations to display in the modal.
   * If not provided, default 'Confirm' and 'Cancel' buttons will be shown.
   */
  buttons?: ButtonConfig[];
}

/**
 * Parameters for the display_product_card tool
 */
export interface DisplayProductCardParams {
  /** The unique ID of the product */
  product_id?: string;

  /** Name of the product */
  product_name: string;

  /** Description of the product */
  product_description: string;

  /** Price of the product */
  price: number;

  /** URL of the product image */
  image_url?: string;
}

/**
 * Parameters for the display_tool_info tool
 */
export interface DisplayToolInfoParams {
  /** The name of the tool to display */
  tool_name: string;

  /** Detailed description of the tool's functionality */
  tool_description: string;

  /** Optional unique identifier for the tool call */
  tool_id?: string;

  /** Parameters passed to the tool */
  tool_parameters?: any;

  /**
   * Current execution status of the tool.
   * 'pending' shows a spinner with gray badge
   * 'executing' shows a spinner with blue badge
   * 'completed' shows a green badge
   * 'failed' shows a red badge
   */
  tool_status: "pending" | "executing" | "completed" | "failed";

  /** Output or results from the tool execution. Only shown when the user expands the card. */
  tool_output?: any;

  /** Error message if the tool execution failed. Only shown when the user expands the card. */
  tool_error?: string;
}

/**
 * Union type of all frontend tool parameter types
 */
/**
 * Parameters for the change_background_color tool
 */
export interface Change_background_colorParams {
  /** The hex code of the color to which the background will be set, like $FFC0CB */
  colorHexCode: string;

}


export type FrontendToolParams =
  | AskUserConfirmationParams
  | DisplayProductCardParams
  | DisplayToolInfoParams;

// -----------------------------------------------------------------------------
// Schema Definitions (for JSON Schema generation)
// -----------------------------------------------------------------------------

/**
 * Generic interface for a JSON Schema property
 */
interface JsonSchemaProperty {
  type: string | string[];
  description: string;
  enum?: string[];
  format?: string;
  items?: JsonSchemaObject;
  properties?: Record<string, JsonSchemaProperty>;
  required?: string[];
}

/**
 * Generic interface for a JSON Schema object
 */
interface JsonSchemaObject {
  type: string;
  properties?: Record<string, JsonSchemaProperty>;
  items?: JsonSchemaObject;
  required?: string[];
  description?: string;
}

/**
 * Interface for a frontend tool schema
 */
export interface FrontendToolSchema {
  name: string;
  description: string;
  parameters: JsonSchemaObject;
}

/**
 * Generate JSON Schema for the ask_user_question_confirmation_approval_input tool
 */
function getAskUserConfirmationSchema(): FrontendToolSchema {
  return {
    name: FrontendToolName.ASK_USER_QUESTION_CONFIRMATION_APPROVAL_INPUT,
    description: "Use this tool for questions, confirmation or approval kind of interaction with user in UI. The UI will shows a modal with customizable buttons for user to select. If asking question, always have 'Others' option in addition to applicable ones.",
    parameters: {
      type: "object",
      properties: {
        title: {
          type: "string",
          description: "Title / header of the confirmation modal."
        },
        question_text: {
          type: "string",
          description: "The question to present to the user for confirmation."
        },
        confirmation_context: {
          type: "string",
          description: "Optional additional context or details to display with the confirmation question."
        },
        buttons: {
          type: "array",
          description: "Array of button configurations to display in the modal. If not provided, default 'Confirm' and 'Cancel' buttons will be shown.",
          items: {
            type: "object",
            properties: {
              label: {
                type: "string",
                description: "The text to display on the button."
              },
              value: {
                type: ["string", "boolean", "number"],
                description: "The value to return when this button is clicked."
              },
              style: {
                type: "string",
                enum: ["primary", "secondary", "danger"],
                description: "The visual style of the button. Primary is highlighted, secondary is less prominent, danger is for destructive actions."
              }
            },
            required: ["label", "value"]
          }
        }
      },
      required: ["question_text"]
    }
  };
}

/**
 * Generate JSON Schema for the display_product_card tool
 */
function getDisplayProductCardSchema(): FrontendToolSchema {
  return {
    name: FrontendToolName.DISPLAY_PRODUCT_CARD,
    description: "Use this tool to show the product details in UI whenever user is asking about any product or want to see product details.",
    parameters: {
      type: "object",
      properties: {
        product_id: {
          type: "string",
          description: "The unique ID of the product."
        },
        product_name: {
          type: "string",
          description: "Name of the product."
        },
        product_description: {
          type: "string",
          description: "Description of the product."
        },
        price: {
          type: "number",
          description: "Price of the product."
        },
        image_url: {
          type: "string",
          format: "uri",
          description: "URL of the product image."
        }
      },
      required: ["product_name", "price"]
    }
  };
}

/**
 * Generate JSON Schema for the display_tool_info tool
 */
function getDisplayToolInfoSchema(): FrontendToolSchema {
  return {
    name: FrontendToolName.DISPLAY_TOOL_INFO,
    description: "Displays detailed information about backend tool calls in the UI, including execution status and results. Shows a spinner for in-progress tools and allows expanding completed tools to view details.",
    parameters: {
      type: "object",
      properties: {
        tool_name: {
          type: "string",
          description: "The name of the tool to display."
        },
        tool_description: {
          type: "string",
          description: "Detailed description of the tool's functionality."
        },
        tool_id: {
          type: "string",
          description: "Optional unique identifier for the tool call."
        },
        tool_parameters: {
          type: "object",
          description: "Parameters passed to the tool."
        },
        tool_status: {
          type: "string",
          enum: ["pending", "executing", "completed", "failed"],
          description: "Current execution status of the tool. 'pending' shows a spinner with gray badge, 'executing' shows a spinner with blue badge, 'completed' shows a green badge, 'failed' shows a red badge."
        },
        tool_output: {
          type: "object",
          description: "Output or results from the tool execution. Only shown when the user expands the card."
        },
        tool_error: {
          type: "string",
          description: "Error message if the tool execution failed. Only shown when the user expands the card."
        }
      },
      required: ["tool_name", "tool_description", "tool_status"]
    }
  };
}

/**
 * Get all frontend tool schemas
 */
/**
 * Generate JSON Schema for the change_background_color tool
 */
function getCHANGE_BACKGROUND_COLORSchema(): FrontendToolSchema {
  return {
    name: FrontendToolName.CHANGE_BACKGROUND_COLOR,
    description: "This will set / change the background color in frontend to the given hex color code like #FFC0CB",
    parameters: {
        "type": "object",
        "properties": {
            "colorHexCode": {
                "type": "string",
                "description": "The hex code of the color to which the background will be set, like $FFC0CB"
            }
        },
        "required": [
            "colorHexCode"
        ]
    }
  };
}


export function getAllFrontendToolSchemas(): FrontendToolSchema[] {
  return [
    getAskUserConfirmationSchema(),
    getDisplayProductCardSchema(),
    getDisplayToolInfoSchema(),
    getCHANGE_BACKGROUND_COLORSchema()
  ];
}

// Export a default object with all schemas for easier importing
export default {
  toolNames: FrontendToolName,
  schemas: getAllFrontendToolSchemas()
};

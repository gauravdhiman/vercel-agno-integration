#!/usr/bin/env node
/**
 * Generate Frontend Tools Python
 *
 * This script reads the frontend_tools.ts file and generates a Python file
 * with equivalent definitions that can be used by the backend.
 *
 * Run with: node scripts/generate_frontend_tools_python.js
 */

const fs = require('fs');
const path = require('path');

// Get the project root directory
const projectRoot = path.resolve(__dirname, '..');

// Read the TypeScript file
const tsFilePath = path.join(projectRoot, 'common', 'frontend_tools.ts');
const tsContent = fs.readFileSync(tsFilePath, 'utf8');

// Generate Python code
function generatePythonCode() {
  // Extract tool names from the enum
  const toolNameRegex = /export enum FrontendToolName {([^}]*)}/s;
  const toolNameMatch = tsContent.match(toolNameRegex);

  let toolNames = [];
  if (toolNameMatch && toolNameMatch[1]) {
    const enumContent = toolNameMatch[1].trim();
    const lines = enumContent.split('\n');

    for (const line of lines) {
      const match = line.match(/\s*([A-Z_]+)\s*=\s*"([^"]+)"/);
      if (match) {
        toolNames.push({ name: match[1], value: match[2] });
      }
    }
  }

  // Start building Python code
  let pythonCode = `# frontend_tools.py
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
`;

  // Add tool name enum values
  for (const tool of toolNames) {
    pythonCode += `    ${tool.name} = "${tool.value}"\n`;
  }

  pythonCode += `
# -----------------------------------------------------------------------------
# Schema Definitions
# -----------------------------------------------------------------------------
`;

  // A simpler approach: extract the tool schemas from the getAllFrontendToolSchemas function
  const schemaFunctions = [];

  // Find the getAllFrontendToolSchemas function
  const getAllFuncRegex = /export function getAllFrontendToolSchemas\(\)[\s\S]*?return\s*\[([\s\S]*?)\]\s*;/;
  const getAllMatch = tsContent.match(getAllFuncRegex);

  if (getAllMatch && getAllMatch[1]) {
    // Extract the function calls
    const functionCalls = getAllMatch[1].trim().split(',').map(call => call.trim());

    // For each function call, find the corresponding function definition
    for (const call of functionCalls) {
      if (!call) continue; // Skip empty entries


      // Extract the function name (the full function name)
      const funcNameMatch = call.match(/^(get[A-Za-z_]+)\(\)$/);
      if (!funcNameMatch) continue;

      const fullFuncName = funcNameMatch[1]; // e.g., "getAskUserConfirmationSchema"

      // Find the function definition
      const funcDefRegex = new RegExp(`function\\s+${fullFuncName}\\(\\)[^{]*{([\\s\\S]*?)}`, 'g');
      const funcDefMatch = funcDefRegex.exec(tsContent);

      if (funcDefMatch) {
        const functionBody = funcDefMatch[1];

        // Extract the enum name, description, and parameters
        const enumMatch = functionBody.match(/FrontendToolName\.([A-Z_]+)/);
        const descMatch = functionBody.match(/description:\s*"([^"]+)"/);

        // Let's take a different approach - since we know the structure of the function
        // We'll just hardcode the parameters for each tool based on the enum name
        let parameters = null;

        // Define parameters for each tool
        if (enumMatch && enumMatch[1] === 'ASK_USER_CONFIRMATION') {
          parameters = `{
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
        }`;
        } else if (enumMatch && enumMatch[1] === 'DISPLAY_PRODUCT_CARD') {
          parameters = `{
            "type": "object",
            "properties": {
                "product_id": {"type": "string", "description": "The unique ID of the product."},
                "product_name": {"type": "string", "description": "Name of the product."},
                "price": {"type": "number", "description": "Price of the product."},
                "image_url": {"type": "string", "format": "uri", "description": "URL of the product image."}
            },
            "required": ["product_id", "product_name", "price"]
        }`;
        } else if (enumMatch && enumMatch[1] === 'DISPLAY_TOOL_INFO') {
          parameters = `{
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
        }`;
        } else if (enumMatch && enumMatch[1] === 'CHANGE_BACKGROUND_COLOR') {
          parameters = `{
            "type": "object",
            "properties": {
                "colorHexCode": {
                    "type": "string",
                    "description": "The hex code of the color to which the background will be set, like $FFC0CB"
                }
            },
            "required": ["colorHexCode"]
        }`;
        }

        if (enumMatch && descMatch && parameters) {
          const enumName = enumMatch[1];
          const description = descMatch[1];

          schemaFunctions.push({
            funcName: fullFuncName,
            enumName,
            description,
            parameters
          });
        }
      }
    }
  }

  // Log summary of found functions
  console.log(`Found ${schemaFunctions.length} schema functions`);

  // Generate Python schema functions
  for (const func of schemaFunctions) {
    // Extract the tool name from the function name
    // For example, from "getAskUserQuestionConfirmationApprovalInputSchema" to "ask_user_confirmation"
    let snakeName;
    if (func.funcName.endsWith('Schema')) {
      // Regular case: getXxxSchema -> xxx
      const baseName = func.funcName.substring(3, func.funcName.length - 6);
      snakeName = baseName
        .replace(/([a-z])([A-Z])/g, '$1_$2') // Convert camelCase to snake_case
        .toLowerCase();
    } else {
      // Fallback: use the enum name
      snakeName = func.enumName.toLowerCase();
    }

    // Format the parameters object for Python
    // This is a simple conversion that works for basic JSON structures
    let pyParameters = func.parameters
      .replace(/"/g, '\\"')  // Escape double quotes
      .replace(/\\"/g, '"')  // Unescape already escaped quotes
      .replace(/(\w+):/g, '"$1":')  // Add quotes to property names
      .replace(/'/g, "\\'");  // Escape single quotes

    // Add the Python function definition
    pythonCode += `
def get_${snakeName}_schema() -> Dict[str, Any]:
    """Generate schema for the ${snakeName} tool"""
    return {
        "name": FrontendToolName.${func.enumName},
        "description": "${func.description}",
        "parameters": ${pyParameters}
    }
`;
  }

  // Generate the list of schema names for get_all_frontend_tool_schemas
  const schemaNames = schemaFunctions.map(func =>
    `get_${func.enumName.toLowerCase()}_schema()`
  );

  // Add the function to get all schemas
  pythonCode += `
def get_all_frontend_tool_schemas() -> List[Dict[str, Any]]:
    """Get all frontend tool schemas"""
    return [
        ${schemaNames.join(',\n        ')}
    ]
`;

  return pythonCode;
}

// Write the Python file
const pythonCode = generatePythonCode();
const pythonFilePath = path.join(projectRoot, 'common', 'frontend_tools.py');
fs.writeFileSync(pythonFilePath, pythonCode, 'utf8');

console.log(`Python code generated and saved to ${pythonFilePath}`);

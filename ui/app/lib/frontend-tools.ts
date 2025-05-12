/**
 * Frontend Tools for UI Components
 *
 * This file imports the common frontend tool definitions from the common directory
 * and re-exports them for use in the UI components.
 *
 * Note: In a real-world scenario, you might want to use a more sophisticated
 * approach to share code between frontend and backend, such as a monorepo setup
 * with a shared package.
 */

// Import the types from the common directory
// In a real project, this would be imported from a shared package
import {
  FrontendToolName,
  AskUserConfirmationParams,
  DisplayProductCardParams,
  DisplayToolInfoParams,
  ButtonConfig
} from '@common/frontend_tools';

// Define the ChangeBackgroundColorParams interface
export interface ChangeBackgroundColorParams {
  /** The hex code of the color to which the background will be set */
  colorHexCode: string;
}

// Re-export the types for use in UI components
export {
  FrontendToolName,
  type AskUserConfirmationParams,
  type DisplayProductCardParams,
  type DisplayToolInfoParams,
  type ButtonConfig
};

/**
 * Type for the tool invocation state
 */
export type ToolInvocationState = 'call' | 'result' | 'partial-call';

/**
 * Interface for a tool invocation in the UI
 */
export interface ToolInvocation {
  toolCallId: string;
  toolName: string;
  state: ToolInvocationState;
  step?: number;
  args?: any;
  result?: any;
}

/**
 * Type guard to check if a tool invocation is for a specific tool
 */
export function isToolOfType<T>(
  invocation: ToolInvocation,
  toolName: FrontendToolName
): invocation is ToolInvocation & { args: T } {
  return invocation.toolName === toolName;
}

/**
 * Type guard for ask_user_question_confirmation_approval_input tool
 */
export function isAskUserConfirmation(
  invocation: ToolInvocation
): invocation is ToolInvocation & { args: AskUserConfirmationParams } {
  return isToolOfType<AskUserConfirmationParams>(invocation, FrontendToolName.ASK_USER_QUESTION_CONFIRMATION_APPROVAL_INPUT);
}

/**
 * Type guard for display_product_card tool
 */
export function isDisplayProductCard(
  invocation: ToolInvocation
): invocation is ToolInvocation & { args: DisplayProductCardParams } {
  return isToolOfType<DisplayProductCardParams>(invocation, FrontendToolName.DISPLAY_PRODUCT_CARD);
}

/**
 * Type guard for display_tool_info tool
 */
export function isDisplayToolInfo(
  invocation: ToolInvocation
): invocation is ToolInvocation & { args: DisplayToolInfoParams } {
  return isToolOfType<DisplayToolInfoParams>(invocation, FrontendToolName.DISPLAY_TOOL_INFO);
}

/**
 * Type guard for change_background_color tool
 */
export function isChangeBackgroundColor(
  invocation: ToolInvocation
): invocation is ToolInvocation & { args: ChangeBackgroundColorParams } {
  return isToolOfType<ChangeBackgroundColorParams>(invocation, FrontendToolName.CHANGE_BACKGROUND_COLOR);
}

/**
 * Get default buttons for confirmation modal
 */
export function getDefaultConfirmationButtons(): ButtonConfig[] {
  return [
    { label: "Confirm", value: true, style: "primary" },
    { label: "Cancel", value: false, style: "secondary" }
  ];
}

/**
 * Format tool name for display
 */
export function formatToolName(name: string): string {
  if (!name) return '';

  // Replace underscores and hyphens with spaces
  let formatted = name.replace(/[_-]/g, ' ');

  // Handle camelCase by adding spaces before capital letters
  formatted = formatted.replace(/([a-z])([A-Z])/g, '$1 $2');

  // Capitalize first letter of each word
  formatted = formatted.split(' ')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(' ');

  return formatted;
}

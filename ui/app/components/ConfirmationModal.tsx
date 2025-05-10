import { type ToolInvocation } from '@ai-sdk/ui-utils';
import React from 'react';

interface ButtonConfig {
  label: string;
  value: string | boolean | number;
  style?: 'primary' | 'secondary' | 'danger';
}

interface ConfirmationModalProps {
  toolInvocation: ToolInvocation;
  onConfirm: (toolCallId: string, result: any) => void;
  onCancel: (toolCallId: string, result: any) => void;
}

export function ConfirmationModal({ toolInvocation, onConfirm, onCancel }: ConfirmationModalProps) {
  const args = toolInvocation.args as {
    title?: string;
    question_text?: string;
    confirmation_context?: string;
    buttons?: ButtonConfig[];
  };

  const title = args?.title || "Please confirm";
  const question = args?.question_text || "Are you sure?";
  const confirmation_context = args?.confirmation_context || "";

  // Default buttons if none provided
  const buttons = args?.buttons || [
    { label: "Confirm", value: true, style: "primary" },
    { label: "Cancel", value: false, style: "secondary" }
  ];

  // Handle button click
  const handleButtonClick = (value: string | boolean | number) => {
    if (value === false) {
      onCancel(toolInvocation.toolCallId, value);
    } else {
      onConfirm(toolInvocation.toolCallId, value);
    }
  };

  // Get button style class based on style property
  const getButtonClass = (style?: string) => {
    switch (style) {
      case 'primary':
        return "px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors";
      case 'secondary':
        return "px-4 py-2 bg-gray-200 text-gray-700 rounded hover:bg-gray-300 transition-colors";
      case 'danger':
        return "px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700 transition-colors";
      default:
        return "px-4 py-2 bg-gray-200 text-gray-700 rounded hover:bg-gray-300 transition-colors";
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-lg p-6 border border-gray-200 my-4">
      <h4 className="text-lg font-semibold text-gray-800 mb-3">{title}</h4>
      <p className="text-gray-600 mb-4">{question}</p>
      {confirmation_context && <p className="text-gray-600 mb-4">{confirmation_context}</p>}
      <div className="flex flex-wrap gap-3">
        {buttons.map((button, index) => (
          <button
            key={index}
            onClick={() => handleButtonClick(button.value)}
            className={getButtonClass(button.style)}
          >
            {button.label}
          </button>
        ))}
      </div>
    </div>
  );
}
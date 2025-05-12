import React, { useState, useRef, useEffect } from 'react';
import {
  type ToolInvocation,
  type AskUserConfirmationParams,
  getDefaultConfirmationButtons
} from '../lib/frontend-tools';

interface ConfirmationModalProps {
  toolInvocation: ToolInvocation;
  onConfirm: (toolCallId: string, result: any) => void;
  onCancel: (toolCallId: string, result: any) => void;
}

export function ConfirmationModal({ toolInvocation, onConfirm, onCancel }: ConfirmationModalProps) {
  const args = toolInvocation.args as AskUserConfirmationParams;

  const title = args?.title || "Please confirm";
  const question = args?.question_text || "Are you sure?";
  const confirmation_context = args?.confirmation_context || "";

  // Default buttons if none provided
  const buttons = args?.buttons || getDefaultConfirmationButtons();

  const [selectedValue, setSelectedValue] = useState<string | boolean | number | null>(null);
  const [otherText, setOtherText] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (selectedValue === 'others' && inputRef.current) {
      inputRef.current.focus();
    }
  }, [selectedValue]);

  // Handle button click
  const handleButtonClick = (value: string | boolean | number) => {
    const str_val = value.toString().toLowerCase();
    if (str_val === 'other' || str_val === 'others') {
      setSelectedValue('others');
    } else if (value === false) {
      onCancel(toolInvocation.toolCallId, value);
    } else {
      onConfirm(toolInvocation.toolCallId, value);
    }
  };

  // Handle other text submission
  const handleOtherSubmit = () => {
    if (otherText.trim()) {
      onConfirm(toolInvocation.toolCallId, otherText);
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
      <div className="flex flex-col gap-4">
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
        
        {selectedValue === 'others' && (
          <div className="flex gap-2">
            <input
              ref={inputRef}
              type="text"
              value={otherText}
              onChange={(e) => setOtherText(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleOtherSubmit();
                }
              }}
              placeholder="Please specify..."
              className="flex-1 px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <button
              onClick={handleOtherSubmit}
              disabled={!otherText.trim()}
              className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors disabled:bg-gray-400"
            >
              Submit
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
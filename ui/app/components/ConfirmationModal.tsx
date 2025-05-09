import { type ToolInvocation } from '@ai-sdk/ui-utils';
import React from 'react';

interface ConfirmationModalProps {
  toolInvocation: ToolInvocation;
  onConfirm: (toolCallId: string, result: any) => void;
  onCancel: (toolCallId: string, result: any) => void;
}

export function ConfirmationModal({ toolInvocation, onConfirm, onCancel }: ConfirmationModalProps) {
  const args = toolInvocation.args as { question?: string };
  const question = args?.question || "Are you sure?";

  return (
    <div className="bg-white rounded-lg shadow-lg p-6 border border-gray-200 my-4">
      <h4 className="text-lg font-semibold text-gray-800 mb-3">{toolInvocation.toolName}</h4>
      <p className="text-gray-600 mb-4">{question}</p>
      <div className="flex gap-3">
        <button
          onClick={() => onConfirm(toolInvocation.toolCallId, true)}
          className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors"
        >
          Confirm
        </button>
        <button
          onClick={() => onCancel(toolInvocation.toolCallId, false)}
          className="px-4 py-2 bg-gray-200 text-gray-700 rounded hover:bg-gray-300 transition-colors"
        >
          Cancel
        </button>
      </div>
    </div>
  );
}
'use client';

import { useChat, type Message } from '@ai-sdk/react';
import { type ToolInvocation } from '@ai-sdk/ui-utils'; 
import React, { useState, useRef, useEffect } from 'react';
import ReactMarkdown, { type Options } from 'react-markdown';

// --- Confirmation Modal Component ---
interface ConfirmationModalProps {
  toolInvocation: ToolInvocation;
  onConfirm: (toolCallId: string, result: any) => void;
  onCancel: (toolCallId: string, result: any) => void;
}

function ConfirmationModal({ toolInvocation, onConfirm, onCancel }: ConfirmationModalProps) {
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

// --- Message Component ---
function ChatMessage({ message }: { message: Message }) {
  const isUser = message.role === 'user';
  
  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4`}>
      <div
        className={`max-w-[80%] rounded-2xl px-5 py-3 shadow-sm ${
          isUser ? 'bg-blue-400 text-white font-medium' : 'bg-gray-100 text-gray-800'
        }`}
      >
        <div className="whitespace-pre-wrap prose dark:prose-invert max-w-none">
          <ReactMarkdown
            components={{
              p: ({ children, ...props }) => <p {...props}>{children}</p>
            }}
          >
            {message.content}
          </ReactMarkdown>
        </div>
        
        {message.toolInvocations?.filter(inv => inv.state === 'result').map(inv => (
          <div
            key={inv.toolCallId}
            className="mt-2 text-sm italic opacity-75"
          >
            Tool Result ({inv.toolName}): {JSON.stringify(inv.result)}
          </div>
        ))}
      </div>
    </div>
  );
}

// --- Main Chat Component ---
export default function Page() {
  const inputRef = useRef<HTMLInputElement>(null);
  const { messages, input, handleInputChange, handleSubmit, addToolResult, status } = useChat({
    api: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1/agent/run',
  });

  const lastMessage = messages[messages.length - 1];
  const lastAssistantMessage = (lastMessage?.role === 'assistant') ? lastMessage : undefined;

  const pendingToolInvocations = lastAssistantMessage?.toolInvocations?.filter(
    inv => inv.state === 'call' && inv.toolName === 'ask_user_confirmation'
  ) || [];

  const handleConfirm = (toolCallId: string, result: any) => {
    addToolResult({ toolCallId, result: { confirmed: result } });
  };

  const handleCancel = (toolCallId: string, result: any) => {
    addToolResult({ toolCallId, result: { confirmed: result } });
  };

  const isInputDisabled = status !== 'ready' || pendingToolInvocations.length > 0;

  useEffect(() => {
    if (inputRef.current && !isInputDisabled) {
      inputRef.current.focus();
    }
  }, [messages, isInputDisabled]);

  return (
    <div className="flex flex-col h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white shadow-sm py-4 px-6 border-b border-gray-200">
        <h1 className="text-xl font-semibold text-gray-800">AI Chat Assistant</h1>
      </div>

      {/* Chat Container */}
      <div className="flex-1 overflow-y-auto px-4 py-6">
        <div className="max-w-3xl mx-auto space-y-4">
          {messages.map((m: Message) => (
            <ChatMessage key={m.id} message={m} />
          ))}

          {/* Pending Tool Invocations */}
          {pendingToolInvocations.map(invocation => (
            <ConfirmationModal
              key={invocation.toolCallId}
              toolInvocation={invocation}
              onConfirm={handleConfirm}
              onCancel={handleCancel}
            />
          ))}
        </div>
      </div>

      {/* Input Area */}
      <div className="bg-white border-t border-gray-200 px-4 py-4">
        <div className="max-w-3xl mx-auto">
          <form onSubmit={handleSubmit} className="flex gap-3">
            <input
              value={input}
              onChange={handleInputChange}
              placeholder="Ask the agent..."
              disabled={isInputDisabled}
              ref={inputRef}
              className="flex-1 px-4 py-2 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed"
            />
            <button
              type="submit"
              disabled={isInputDisabled}
              className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:bg-gray-400 disabled:cursor-not-allowed"
            >
              Send
            </button>
          </form>
          
          {/* Status Indicator */}
          <div className="mt-2 text-sm text-gray-500 flex items-center gap-2">
            <div className={`w-2 h-2 rounded-full ${status === 'ready' ? 'bg-green-500' : 'bg-yellow-500'}`} />
            Status: {status}
          </div>
        </div>
      </div>
    </div>
  );
}
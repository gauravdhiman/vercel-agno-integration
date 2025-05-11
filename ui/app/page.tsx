'use client';

import { useChat, type Message } from '@ai-sdk/react';
import React, { useRef, useEffect, useState } from 'react';
import { ChatMessage } from './components/ChatMessage';
import { ConfirmationModal } from './components/ConfirmationModal';
import { InputArea } from './components/InputArea';
import { FrontendToolName } from './lib/frontend-tools';

// --- Main Chat Component ---
export default function Page() {
  const inputRef = useRef<HTMLInputElement>(null);

  const [error, setError] = useState<Error | null>(null);
  const [showDebug, setShowDebug] = useState(false);

  const { messages, input, handleInputChange, handleSubmit, addToolResult, status } = useChat({
    api: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1/agent/run',
    onError: (error) => {
      console.error("Chat error:", error);
      setError(error);
    }
  });

  const lastMessage = messages[messages.length - 1];
  const lastAssistantMessage = (lastMessage?.role === 'assistant') ? lastMessage : undefined;

  // Get pending tool invocations from the last assistant message
  const pendingToolInvocations = lastAssistantMessage?.parts?.filter(
    inv => inv.type === 'tool-invocation' && 'toolInvocation' in inv && inv.toolInvocation.state === 'call'
  ).map(p => 'toolInvocation' in p ? p.toolInvocation : null).filter(Boolean) || [];

  const handleConfirm = (toolCallId: string, result: any) => {
    addToolResult({ toolCallId, result: { confirmed: result } });
  };

  const handleCancel = (toolCallId: string, result: any) => {
    addToolResult({ toolCallId, result: { confirmed: result } });
  };

  const isInputDisabled = status !== 'ready' || pendingToolInvocations.length > 0;

  // Focus input when ready
  useEffect(() => {
    if (inputRef.current && !isInputDisabled) {
      inputRef.current.focus();
    }
  }, [messages, isInputDisabled]);

  return (
    <div className="flex flex-col h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white shadow-sm py-4 px-6 border-b border-gray-200">
        <div className="flex justify-between items-center">
          <h1 className="text-xl font-semibold text-gray-800">AI Chat Assistant</h1>
          <div className="flex items-center space-x-2">
            <span className={`px-2 py-1 text-xs rounded-full ${
              status === 'ready' ? 'bg-green-100 text-green-800' :
              status === 'error' ? 'bg-red-100 text-red-800' :
              'bg-blue-100 text-blue-800'
            }`}>
              Status: {status}
            </span>
            <button
              onClick={() => setShowDebug(!showDebug)}
              className="px-2 py-1 text-xs bg-gray-200 hover:bg-gray-300 rounded-full"
            >
              {showDebug ? 'Hide Debug' : 'Show Debug'}
            </button>
          </div>
        </div>
      </div>

      {/* Chat Container */}
      <div className="flex-1 overflow-y-auto px-4 py-6">
        <div className="max-w-3xl mx-auto space-y-4">
          {/* Error Display */}
          {error && (
            <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative mb-4" role="alert">
              <strong className="font-bold">Error: </strong>
              <span className="block sm:inline">{error.message}</span>
              <pre className="mt-2 text-xs overflow-auto bg-red-50 p-2 rounded">
                {JSON.stringify(error, null, 2)}
              </pre>
            </div>
          )}

          {/* Debug Information */}
          {showDebug && (
            <div className="bg-gray-100 border border-gray-300 text-gray-700 px-4 py-3 rounded relative mb-4">
              <div className="flex justify-between items-center">
                <strong className="font-bold">Debug Information</strong>
                <button
                  onClick={() => setShowDebug(false)}
                  className="text-gray-500 hover:text-gray-700"
                >
                  ✕
                </button>
              </div>
              <div className="mt-2">
                <h3 className="text-sm font-semibold">Status: {status}</h3>
                <h3 className="text-sm font-semibold mt-2">Messages ({messages.length}):</h3>
                <pre className="mt-1 text-xs overflow-auto bg-gray-50 p-2 rounded h-64">
                  {JSON.stringify(messages, null, 2)}
                </pre>
              </div>
            </div>
          )}

          {messages.map((m: Message) => (
            <ChatMessage key={m.id} message={m} />
          ))}



          {/* Pending Tool Invocations */}
          {pendingToolInvocations.map((invocation, index) => {
            if (invocation && invocation.toolName === FrontendToolName.ASK_USER_CONFIRMATION) {
              return <ConfirmationModal
                key={invocation.toolCallId}
                toolInvocation={invocation}
                onConfirm={handleConfirm}
                onCancel={handleCancel}
              />
            }
            return <React.Fragment key={`empty-${index}`}></React.Fragment>
          })}
        </div>
      </div>

      {/* Input Area */}
      <InputArea
        inputRef={inputRef}
        input={input}
        handleInputChange={handleInputChange}
        handleSubmit={handleSubmit}
        isInputDisabled={isInputDisabled}
        status={status}
      />
    </div>
  );
}
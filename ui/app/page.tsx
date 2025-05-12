'use client';

import { useChat, type Message } from '@ai-sdk/react';
import React, { useRef, useEffect, useState } from 'react';
import { ChatMessage } from './components/ChatMessage';
import { ConfirmationModal } from './components/ConfirmationModal';
import { InputArea } from './components/InputArea';
import { FrontendToolName, ChangeBackgroundColorParams, DisplayProductCardParams, DisplayToolInfoParams } from './lib/frontend-tools';
import { validateImageUrl } from './lib/image-utils';

// --- Main Chat Component ---
export default function Page() {
  const inputRef = useRef<HTMLInputElement>(null);

  const [error, setError] = useState<Error | null>(null);
  const [showDebug, setShowDebug] = useState(false);
  const [backgroundColor, setBackgroundColor] = useState<string | null>(null);

  const chatContainerRef = useRef<HTMLDivElement>(null);
const [isAtBottom, setIsAtBottom] = useState(true);

const { messages, input, handleInputChange, handleSubmit, addToolResult, status, reload } = useChat({
    api: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1/agent/run',
    onError: (error) => {
      console.error("Chat error:", error);
      setError(error);
      // Clear error after 5 seconds
      setTimeout(() => setError(null), 5000);
    },
    onToolCall: async ({ toolCall }) => {
      // Handle the change_background_color tool
      if (toolCall.toolName === FrontendToolName.CHANGE_BACKGROUND_COLOR) {
        const args = toolCall.args as ChangeBackgroundColorParams;
        const colorHexCode = args.colorHexCode;

        // Validate hex color code format
        if (/^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$/.test(colorHexCode)) {
          // Set the background color
          setBackgroundColor(colorHexCode);
          // Return success result
          return { success: true, color: colorHexCode };
        } else {
          // Return error for invalid color format
          return {
            success: false,
            error: "Invalid color format. Expected hex color code like #FFC0CB"
          };
        }
      }

      // Handle the display_product_card tool
      if (toolCall.toolName === FrontendToolName.DISPLAY_PRODUCT_CARD) {
        try {
          const args = toolCall.args as DisplayProductCardParams;
          // Validate required fields
          const { product_id, product_name, price } = args;
          if (!product_id || !product_name || typeof price !== 'number') {
            return {
              success: false,
              error: "Missing required fields: product_id, product_name, and price are required"
            };
          }

          // Validate price is positive
          if (price < 0) {
            return {
              success: false,
              error: "Price must be a positive number"
            };
          }

          // Validate image URL if provided
          if (args.image_url) {
            const imageValidation = await validateImageUrl(args.image_url);
            if (!imageValidation.isValid || !imageValidation.isLoadable) {
              return {
                success: false,
                error: imageValidation.error || "Invalid or unloadable image URL"
              };
            }
          }

          // If all validations pass, return success
          return {
            success: true,
            message: "Product card rendered successfully for ", product_name,
            product_id: product_id
          };
        } catch (error) {
          return {
            success: false,
            error: `Error rendering product card: ${error instanceof Error ? error.message : 'Unknown error'}`
          };
        }
      }
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

  // Track scroll position
  const handleScroll = () => {
    if (chatContainerRef.current) {
      const { scrollTop, scrollHeight, clientHeight } = chatContainerRef.current;
      setIsAtBottom(scrollHeight - scrollTop <= clientHeight + 10);
    }
  };

  // Auto-scroll to bottom when new messages arrive and we're at bottom
  useEffect(() => {
    if (isAtBottom && chatContainerRef.current) {
      chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight;
    }
  }, [messages, isAtBottom]);

  // Focus input when ready
  useEffect(() => {
    if (inputRef.current && !isInputDisabled) {
      inputRef.current.focus();
    }
  }, [messages, isInputDisabled]);

  return (
    <div
      className="flex flex-col h-screen transition-colors duration-300"
      style={{ backgroundColor: backgroundColor || '#f9fafb' /* bg-gray-50 equivalent */ }}>
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
      <div 
  ref={chatContainerRef}
  className="flex-1 overflow-y-auto px-4 py-6"
  onScroll={handleScroll}
>
        <div className="max-w-3xl mx-auto space-y-4">
          {/* Error Display */}
          {error && (
            <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative mb-4" role="alert">
              <strong className="font-bold">Error: </strong>
              <span className="block sm:inline">{error.message}</span>
              <pre className="mt-2 text-xs overflow-auto bg-red-50 p-2 rounded">
                {JSON.stringify(error, null, 2)}
              </pre>
              <button
                onClick={() => {
                  setError(null);
                  reload();
                }}
                className="mt-2 px-4 py-2 bg-red-500 text-white rounded hover:bg-red-600 transition-colors"
              >
                Retry
              </button>
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
            if (invocation && invocation.toolName === FrontendToolName.ASK_USER_QUESTION_CONFIRMATION_APPROVAL_INPUT) {
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
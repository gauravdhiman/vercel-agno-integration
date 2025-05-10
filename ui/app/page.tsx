'use client';

import { useChat, type Message } from '@ai-sdk/react';
import { type ToolInvocation } from '@ai-sdk/ui-utils';
import React, { useRef, useEffect, useState } from 'react';
import { ChatMessage } from './components/ChatMessage';
import { ConfirmationModal } from './components/ConfirmationModal';
import { InputArea } from './components/InputArea';
import ToolInfoCard from './components/ToolInfoCard';

// Define a type for tool invocation data to avoid deprecated warnings
interface ToolInvocationData {
  state: 'call' | 'result' | 'partial-call';
  step?: number;
  toolCallId: string;
  toolName: string;
  args: any;
  result?: any;
}

// --- Main Chat Component ---
export default function Page() {
  const inputRef = useRef<HTMLInputElement>(null);
  const [toolInfoCards, setToolInfoCards] = useState<any[]>([]);

  const [error, setError] = useState<Error | null>(null);
  const [showDebug, setShowDebug] = useState(false);

  const { messages, input, handleInputChange, handleSubmit, addToolResult, status } = useChat({
    api: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1/agent/run',
    onError: (error) => {
      console.error("Chat error:", error);
      setError(error);
    }
  });
  console.log('messages', messages);

  // Log the current status
  useEffect(() => {
    console.log('Chat status:', status);
  }, [status]);

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

  // Process tool invocations from messages
  useEffect(() => {
    // Add debugging to see what's in the messages
    console.log("Processing messages for tool invocations:", JSON.stringify(messages, null, 2));

    // Check for text content in the last assistant message
    const lastAssistantMessageWithContent = messages
      .filter(m => m.role === 'assistant' && m.content)
      .pop();

    if (lastAssistantMessageWithContent) {
      console.log("Last assistant message with content:", lastAssistantMessageWithContent);
    }

    // Find all messages with tool invocations (either in toolInvocations or parts)
    const messagesWithTools = messages.filter(m => {
      if (m.role !== 'assistant') return false;

      // Check for tool invocations in parts array (preferred method)
      const hasToolInParts = m.parts && m.parts.some(p => p.type === 'tool-invocation');

      // Check for tool invocations in deprecated toolInvocations array
      const hasToolInvocations = Array.isArray((m as any).toolInvocations) && (m as any).toolInvocations.length > 0;

      return hasToolInParts || hasToolInvocations;
    });

    if (messagesWithTools.length > 0) {
      // Extract all tool invocations from messages
      const allToolInvocations = messagesWithTools.flatMap(message => {
        // First try to get tool invocations from parts (preferred method)
        if (message.parts && message.parts.some(p => p.type === 'tool-invocation')) {
          return message.parts
            .filter(p => p.type === 'tool-invocation' && 'toolInvocation' in p)
            .map(p => {
              const tool = p.toolInvocation as any; // Type assertion to avoid TS errors
              return {
                id: tool.toolCallId,
                tool_name: tool.toolName,
                tool_description: `${tool.toolName} tool call`,
                tool_parameters: tool.args,
                tool_status: tool.state === 'call' ? 'executing' :
                            tool.state === 'result' ? 'completed' :
                            tool.state === 'partial-call' ? 'pending' : 'failed',
                tool_output: tool.state === 'result' ? tool.result : undefined,
                tool_id: tool.toolCallId
              };
            });
        }

        // Fallback to toolInvocations if parts doesn't have tool invocations
        const toolInvocations = (message as any).toolInvocations;
        if (Array.isArray(toolInvocations) && toolInvocations.length > 0) {
          return toolInvocations.map((tool: ToolInvocationData) => {
            return {
              id: tool.toolCallId,
              tool_name: tool.toolName,
              tool_description: `${tool.toolName} tool call`,
              tool_parameters: tool.args,
              tool_status: tool.state === 'call' ? 'executing' :
                          tool.state === 'result' ? 'completed' :
                          tool.state === 'partial-call' ? 'pending' : 'failed',
              tool_output: tool.state === 'result' ? tool.result : undefined,
              tool_id: tool.toolCallId
            };
          });
        }

        return [];
      });

      // Log the extracted tool invocations for debugging
      console.log("Extracted tool invocations:", allToolInvocations);

      // Update tool info cards, avoiding duplicates and updating existing ones
      if (allToolInvocations.length > 0) {
        setToolInfoCards(prev => {
          const existingIds = new Set(prev.map(card => card.id));
          const uniqueNewTools = allToolInvocations.filter(tool => !existingIds.has(tool.id));

          // Update existing cards with new status/output
          const updatedExisting = prev.map(card => {
            const update = allToolInvocations.find(tool => tool.id === card.id);
            if (update && update.tool_status !== card.tool_status) {
              console.log(`Tool status changed for ${card.tool_name}: ${card.tool_status} -> ${update.tool_status}`);
            }
            return update || card;
          });

          const result = [...updatedExisting, ...uniqueNewTools];
          console.log("Updated tool info cards:", result);
          return result;
        });
      }
    }
  }, [messages]);

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

          {/* Tool Info Cards */}
          {toolInfoCards.length > 0 && (
            <div className="mb-4">
              <h3 className="text-sm font-medium text-gray-500 mb-2">Tool Executions</h3>
              <div className="space-y-3">
                {toolInfoCards.map((toolInfo) => (
                  <ToolInfoCard key={toolInfo.id} tool={toolInfo} />
                ))}
              </div>
            </div>
          )}


          {/* Pending Tool Invocations */}
          {pendingToolInvocations.map((invocation, index) => {
            if (invocation && invocation.toolName === 'ask_user_confirmation') {
              return <ConfirmationModal
                key={invocation.toolCallId}
                toolInvocation={invocation as ToolInvocation}
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
'use client';

import { useChat, type Message } from '@ai-sdk/react';
import { type ToolInvocation } from '@ai-sdk/ui-utils';
import React, { useRef, useEffect } from 'react';
import { ChatMessage } from './components/ChatMessage';
import { ConfirmationModal } from './components/ConfirmationModal';
import { InputArea } from './components/InputArea';

// --- Main Chat Component ---
export default function Page() {
  const inputRef = useRef<HTMLInputElement>(null);
  const { messages, input, handleInputChange, handleSubmit, addToolResult, status } = useChat({
    api: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1/agent/run',
  });

  const lastMessage = messages[messages.length - 1];
  const lastAssistantMessage = (lastMessage?.role === 'assistant') ? lastMessage : undefined;

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

          {/* Tool Info Cards */}
          {/* {messages
            .filter(m => m.role === 'tool' && m.name === 'display_tool_info')
            .map((message, i) => {
              try {
                const toolInfo = typeof message.content === 'string'
                  ? JSON.parse(message.content)
                  : message.content;
                return <ToolInfoCard key={i} tool={toolInfo} />;
              } catch (e) {
                console.error('Failed to parse tool info:', e);
                return null;
              }
            })} */}


          {/* Pending Tool Invocations */}
          {pendingToolInvocations.map(invocation => {
            if (invocation && invocation.toolName === 'ask_user_confirmation') {
              return <ConfirmationModal
                key={invocation.toolCallId}
                toolInvocation={invocation as ToolInvocation}
                onConfirm={handleConfirm}
                onCancel={handleCancel}
              />
            }
            return <></>
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
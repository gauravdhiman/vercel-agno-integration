'use client';

import { useChat, type Message } from '@ai-sdk/react';
import { type ToolInvocation } from '@ai-sdk/ui-utils'; 
import React, { useState } from 'react';

// --- Confirmation Modal Component ---
interface ConfirmationModalProps {
  toolInvocation: ToolInvocation;
  onConfirm: (toolCallId: string, result: any) => void;
  onCancel: (toolCallId: string, result: any) => void;
}

function ConfirmationModal({ toolInvocation, onConfirm, onCancel }: ConfirmationModalProps) {
  const args = toolInvocation.args as { question?: string }; // Type assertion
  const question = args?.question || "Are you sure?"; // Default question

  return (
    <div style={{
      border: '2px solid blue', padding: '15px', margin: '10px 0',
      backgroundColor: '#e0e0ff'
     }}>
      <h4>Action Required: {toolInvocation.toolName}</h4>
      <p>{question}</p>
      <button onClick={() => onConfirm(toolInvocation.toolCallId, true)} style={{ marginRight: '10px' }}>
         Confirm
      </button>
      <button onClick={() => onCancel(toolInvocation.toolCallId, false)}>
         Cancel
      </button>
    </div>
  );
}

// --- Main Chat Component ---
export default function Page() {
  const { messages, input, handleInputChange, handleSubmit, addToolResult, status } = useChat({
    api: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1/agent/run',
  });

  // Find the latest assistant message
  const lastMessage = messages[messages.length - 1];
  const lastAssistantMessage = (lastMessage?.role === 'assistant') ? lastMessage : undefined;

  // Find tool invocations in the 'call' state that require user interaction
  const pendingToolInvocations = lastAssistantMessage?.toolInvocations?.filter(
    inv => inv.state === 'call' && inv.toolName === 'ask_user_confirmation' // Example tool name
  ) || [];

  const handleConfirm = (toolCallId: string, result: any) => {
    addToolResult({ toolCallId, result: { confirmed: result } });
     // Optionally clear or update local state if needed after confirmation
  };

  const handleCancel = (toolCallId: string, result: any) => {
     addToolResult({ toolCallId, result: { confirmed: result } });
     // Optionally clear or update local state if needed after cancellation
  };


  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', padding: '20px' }}>
      <div style={{ flexGrow: 1, overflowY: 'auto', marginBottom: '20px' }}>
        {messages.map((m: Message) => (
          <div key={m.id} style={{ marginBottom: '10px', whiteSpace: 'pre-wrap' }}>
            <strong>{m.role === 'user' ? 'You: ' : 'Agent: '}</strong>
            {m.content}

            {/* Render completed tool results (optional, for context) */}
            {m.toolInvocations?.filter(inv => inv.state === 'result').map(inv => (
               <div key={inv.toolCallId} style={{ fontStyle: 'italic', color: 'grey', marginLeft: '20px' }}>
                 Tool Result ({inv.toolName}): {JSON.stringify(inv.result)}
               </div>
             ))}
          </div>
        ))}

         {/* --- Render Pending Tool Invocations --- */}
         {pendingToolInvocations.map(invocation => (
           <ConfirmationModal
             key={invocation.toolCallId}
             toolInvocation={invocation}
             onConfirm={handleConfirm}
             onCancel={handleCancel}
            />
         ))}
         {/* Add rendering logic for other frontend actions here */}

      </div>

      <form onSubmit={handleSubmit}>
        <input
          value={input}
          onChange={handleInputChange}
          placeholder="Ask the agent..."
          disabled={status !== 'ready' || pendingToolInvocations.length > 0} // Disable input if waiting for user
          style={{ width: 'calc(100% - 80px)', padding: '10px', marginRight: '10px' }}
        />
        <button
           type="submit"
           disabled={status !== 'ready' || pendingToolInvocations.length > 0} // Disable submit if waiting for user
           style={{ padding: '10px' }}
         >
          Send
        </button>
      </form>
      <div style={{ marginTop: '10px', fontSize: '0.8em', color: '#555' }}>
        Status: {status}
      </div>
    </div>
  );
}
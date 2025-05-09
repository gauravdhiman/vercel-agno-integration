import React from 'react';
import ReactMarkdown, { type Options } from 'react-markdown';
import { type Message } from '@ai-sdk/react';

export function ChatMessage({ message }: { message: Message }) {
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
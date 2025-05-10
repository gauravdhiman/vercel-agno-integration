import React from 'react';
import ReactMarkdown from 'react-markdown';
import { type Message } from '@ai-sdk/react';

// Define interfaces for message parts
interface TextPart {
  type: 'text';
  text: string;
}

interface ToolInvocationPart {
  type: 'tool-invocation';
  toolInvocation: {
    toolCallId: string;
    toolName: string;
    state: string;
    result?: any;
  };
}

export function ChatMessage({ message }: { message: Message }) {
  const isUser = message.role === 'user';

  if (isUser) {
    return (
      <div className="flex justify-end mb-4">
        <div className="max-w-[80%] rounded-2xl px-5 py-3 shadow-sm bg-blue-400 text-white font-medium">
          <div className="whitespace-wrap prose dark:prose-invert max-w-none [&>*]:my-0 prose-li:my-0">
            <ReactMarkdown unwrapDisallowed={true}>{message.content}</ReactMarkdown>
          </div>
        </div>
      </div>
    );
  }

  // Type guard to check if a part is a text part
  const isTextPart = (part: any): part is TextPart =>
    part.type === 'text' && 'text' in part;

  const toolInvocationParts = (message?.parts?.filter(part =>
    part.type === 'tool-invocation' && 'toolInvocation' in part
  ) as ToolInvocationPart[]) || [];

  const toolResults = toolInvocationParts
    .filter(inv => inv.toolInvocation.state === 'result')
    .map(p => p.toolInvocation) || [];

  // Handle the case where the message has content but no parts
  // This happens with the final response from the assistant
  let messageParts: TextPart[] = [];

  if (message.parts && message.parts.length > 0) {
    // If the message has parts, extract the text parts
    messageParts = message.parts.filter(isTextPart);
  } else if (message.content) {
    // If the message has content but no parts, create a text part from the content
    messageParts = [{ type: 'text', text: message.content }];
  }

  // Log the message and parts for debugging
  console.log("Message:", message.id, "Content:", message.content, "Parts:", messageParts);

  let lastPart: TextPart | undefined;
  let remainingParts: TextPart[] = [];

  // Split message parts into first and rest
  if (messageParts.length > 1) {
    lastPart = messageParts[messageParts.length - 1];
    remainingParts = messageParts.slice(0, -1);
  } else if (messageParts.length === 1) {
    lastPart = messageParts[0];
    remainingParts = [];
  }

  return (
    <div className="flex flex-col space-y-2">
      {/* All message except last */}
      {remainingParts.map((part, index) => {
        return (
          <div key={index} className="flex justify-start">
            <div className="max-w-[80%] rounded-2xl px-5 py-3 shadow-sm bg-gray-100 text-gray-800">
              <div className="whitespace-wrap prose dark:prose-invert max-w-none [&>*]:my-0 prose-li:my-0">
                <ReactMarkdown unwrapDisallowed={true}>
                  {part.type === 'text' ? part.text : ''}
                </ReactMarkdown>
              </div>
            </div>
          </div>
        );
      })}

      {/* Tool Results */}
      {toolResults.map(inv => (
        <div key={inv.toolCallId} className="flex justify-start mb-2">
          <div className="max-w-[80%] rounded-2xl px-5 py-3 shadow-sm bg-gray-200 text-gray-700">
            <div className="text-sm">
              <span className="font-medium">Your input {inv.toolName}</span>: {JSON.stringify(inv.result)}
            </div>
          </div>
        </div>
      ))}

      {/* Last Message Part */}
      {lastPart && lastPart.type === 'text' && (
        <div className="flex justify-start">
          <div className="max-w-[80%] rounded-2xl px-5 py-3 shadow-sm bg-gray-100 text-gray-800">
            <div className="whitespace-wrap prose dark:prose-invert max-w-none [&>*]:my-0 prose-li:my-0">
              <ReactMarkdown unwrapDisallowed={true}>{lastPart.text}</ReactMarkdown>
            </div>
          </div>
        </div>
      )}
    </div>
  );

}
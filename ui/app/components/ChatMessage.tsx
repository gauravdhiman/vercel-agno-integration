import React from 'react';
import ReactMarkdown from 'react-markdown';
import { type Message } from '@ai-sdk/react';
import ToolInfoCard from './ToolInfoCard';
import {
  type ToolInvocation as FrontendToolInvocation,
  FrontendToolName,
  isChangeBackgroundColor
} from '../lib/frontend-tools';

// Define interfaces for message parts
interface TextPart {
  type: 'text';
  text: string;
}

interface ToolInvocationPart {
  type: 'tool-invocation';
  toolInvocation: FrontendToolInvocation;
}

type MessagePart = TextPart | ToolInvocationPart;

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

  // Type guards
  const isTextPart = (part: any): part is TextPart =>
    part.type === 'text' && 'text' in part;

  const isToolInvocationPart = (part: any): part is ToolInvocationPart =>
    part.type === 'tool-invocation' && 'toolInvocation' in part;

  // Process all message parts in order
  let messageParts: MessagePart[] = [];

  if (message.parts && message.parts.length > 0) {
    // If the message has parts, use them directly
    messageParts = message.parts.filter(part =>
      isTextPart(part) || isToolInvocationPart(part)
    ) as MessagePart[];
  } else if (message.content) {
    // If the message has content but no parts, create a text part from the content
    messageParts = [{ type: 'text', text: message.content }];
  }

  // Convert display_tool_info invocations to tool info cards
  const createToolInfoCard = (toolInvocation: ToolInvocationPart['toolInvocation']) => {
    const actualToolName = toolInvocation.args?.actual_tool_name;

    // Map the state to the specific enum values expected by ToolInfo
    let toolStatus: 'pending' | 'executing' | 'completed' | 'failed';

    switch (toolInvocation.state) {
      case 'call':
        toolStatus = 'executing';
        break;
      case 'result':
        toolStatus = 'completed';
        break;
      case 'partial-call':
        toolStatus = 'pending';
        break;
      default:
        toolStatus = 'failed';
    }

    return {
      id: toolInvocation.toolCallId,
      tool_name: actualToolName || toolInvocation.toolName,
      tool_description: actualToolName
        ? `Backend tool execution`
        : `${toolInvocation.toolName} tool call`,
      tool_parameters: toolInvocation.args,
      tool_status: toolStatus,
      tool_output: toolInvocation.state === 'result' ? toolInvocation.result : undefined
    };
  };

  return (
    <div className="flex flex-col space-y-2">
      {/* Render all parts in sequence */}
      {messageParts.map((part, index) => {
        // Text part
        if (isTextPart(part)) {
          return (
            <div key={`text-${index}`} className="flex justify-start">
              <div className="max-w-[80%] rounded-2xl px-5 py-3 shadow-sm bg-gray-100 text-gray-800">
                <div className="whitespace-wrap prose dark:prose-invert max-w-none [&>*]:my-0 prose-li:my-0">
                  <ReactMarkdown unwrapDisallowed={true}>{part.text}</ReactMarkdown>
                </div>
              </div>
            </div>
          );
        }

        // Tool invocation part - display_tool_info
        if (isToolInvocationPart(part) && part.toolInvocation.toolName === FrontendToolName.DISPLAY_TOOL_INFO) {
          const toolInfo = createToolInfoCard(part.toolInvocation);
          return (
            <div key={`tool-${part.toolInvocation.toolCallId}`} className="mt-2">
              <ToolInfoCard tool={toolInfo} />
            </div>
          );
        }

        // Change background color tool result
        if (isToolInvocationPart(part) && part.toolInvocation.state === 'result' &&
            isChangeBackgroundColor(part.toolInvocation)) {
          const result = part.toolInvocation.result;
          const colorHexCode = result?.color || '';

          return (
            <div key={`color-tool-${part.toolInvocation.toolCallId}`} className="flex justify-start mb-2">
              <div className="max-w-[80%] rounded-2xl px-5 py-3 shadow-sm bg-gray-200 text-gray-700">
                <div className="text-sm flex items-center">
                  <span className="font-medium mr-2">Background color changed to:</span>
                  <div
                    className="w-6 h-6 rounded border border-gray-300 inline-block mr-2"
                    style={{ backgroundColor: colorHexCode }}
                  ></div>
                  <code>{colorHexCode}</code>
                </div>
              </div>
            </div>
          );
        }

        // Other tool invocation parts (frontend tools)
        if (isToolInvocationPart(part) && part.toolInvocation.state === 'result') {
          return (
            <div key={`frontend-tool-${part.toolInvocation.toolCallId}`} className="flex justify-start mb-2">
              <div className="max-w-[80%] rounded-2xl px-5 py-3 shadow-sm bg-gray-200 text-gray-700">
                <div className="text-sm">
                  <span className="font-medium">Your input {part.toolInvocation.toolName}</span>: {JSON.stringify(part.toolInvocation.result)}
                </div>
              </div>
            </div>
          );
        }

        return null; // Skip other part types
      })}
    </div>
  );
}
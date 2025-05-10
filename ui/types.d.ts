// Custom type declarations to extend existing types

import { Message as BaseMessage } from '@ai-sdk/react';

// Extend the Message type to include toolInvocations
declare module '@ai-sdk/react' {
  interface Message extends BaseMessage {
    toolInvocations?: Array<{
      state: 'call' | 'result' | 'partial-call';
      step?: number;
      toolCallId: string;
      toolName: string;
      args: any;
      result?: any;
    }>;
  }
}

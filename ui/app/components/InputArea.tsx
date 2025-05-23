import React, { useRef, useEffect, KeyboardEvent } from 'react';
import { useChat } from '@ai-sdk/react';

export function InputArea({
  inputRef,
  input,
  handleInputChange,
  handleSubmit,
  isInputDisabled,
  status
}: {
  inputRef: React.RefObject<HTMLTextAreaElement>;
  input: string;
  handleInputChange: (e: React.ChangeEvent<HTMLTextAreaElement>) => void;
  handleSubmit: (e: React.FormEvent<HTMLFormElement>) => void;
  isInputDisabled: boolean;
  status: string;
}) {
  
  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey && !e.metaKey) {
      e.preventDefault();
      const form = e.currentTarget.form;
      if (form) {
        handleSubmit(e as unknown as React.FormEvent<HTMLFormElement>);
      }
    }
  };
  return (
    <div className="bg-white border-t border-gray-200 px-4 py-4">
      <div className="max-w-3xl mx-auto">
        <form onSubmit={handleSubmit} className="flex gap-3">
          <textarea
            value={input}
            onChange={handleInputChange}
            onKeyDown={handleKeyDown}
            placeholder="Ask the agent..."
            disabled={isInputDisabled}
            ref={inputRef}
            rows={1}
            className="flex-1 px-4 py-2 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed min-h-[44px] max-h-[400px]"
          />
          <button
            type="submit"
            disabled={isInputDisabled}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:bg-gray-400 disabled:cursor-not-allowed"
          >
            Send
          </button>
        </form>
        
        <div className="mt-2 text-sm text-gray-500 flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full ${status === 'ready' ? 'bg-green-500' : 'bg-yellow-500'}`} />
          Status: {status}
        </div>
      </div>
    </div>
  );
}
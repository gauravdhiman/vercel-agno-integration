// ToolInfoCard.tsx
/**
 * This component displays appropriate information about the backend tools called by the agent.
 */
import React, { useState, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import {
  type DisplayToolInfoParams,
  formatToolName
} from '../lib/frontend-tools';

// Alias DisplayToolInfoParams to ToolInfo for backward compatibility
type ToolInfo = DisplayToolInfoParams;

interface ToolInfoCardProps {
  tool: ToolInfo;
}

const ToolInfoCard: React.FC<ToolInfoCardProps> = ({ tool }) => {
  // Default to collapsed state
  const [expanded, setExpanded] = useState(false);

  // Extract actual tool name and args if available
  const actualToolName = tool.tool_parameters?.actual_tool_name;
  const actualToolArgs = tool.tool_parameters?.actual_tool_args;

  // For the result, check if it's in the expected format
  const actualToolResult = tool.tool_parameters?.actual_tool_results;

  // Determine if the tool has details to show
  const hasDetails = tool.tool_parameters || tool.tool_output || tool.tool_error;

  // Track if the user has manually collapsed the card
  const [userCollapsed, setUserCollapsed] = useState(false);

  // Handle expand/collapse toggle with user preference tracking
  const handleToggleExpand = () => {
    setUserCollapsed(!expanded);
    setExpanded(!expanded);
  };

  // Only auto-expand on completion if the user hasn't manually collapsed it
  useEffect(() => {
    if (tool.tool_status === 'completed' && !expanded && hasDetails && !userCollapsed) {
      setExpanded(false);
    }
  }, [tool.tool_status, expanded, hasDetails, userCollapsed]);

  // Determine if the tool is in a loading state
  const isLoading = tool.tool_status === 'pending' || tool.tool_status === 'executing';

  // Determine if the card should be expandable
  const isExpandable = hasDetails && !isLoading;

  // Intelligently format tool output based on its type and content
  const formatToolOutput = (output: any): { type: 'json' | 'markdown' | 'text', content: string } => {
    // If output is null or undefined, return empty string
    if (output === null || output === undefined) {
      return { type: 'text', content: '' };
    }

    // If output is already a string
    if (typeof output === 'string') {
      // Check if it's a stringified JSON
      try {
        const parsedJson = JSON.parse(output);
        // If we can parse it as JSON, return it as formatted JSON
        return { type: 'json', content: JSON.stringify(parsedJson, null, 2) };
      } catch (e) {
        // Check if it looks like markdown (contains # or * or `)
        if (output.match(/(?:^|\n)#{1,6}\s|[*_]{1,2}[^*_]+[*_]{1,2}|`{1,3}[^`]+`{1,3}/)) {
          return { type: 'markdown', content: output };
        }
        // Otherwise, it's just plain text
        return { type: 'text', content: output };
      }
    }

    // If output is an object or array, stringify it as JSON
    return { type: 'json', content: JSON.stringify(output, null, 2) };
  };

  // Get status badge styling
  const getStatusBadgeClass = () => {
    switch (tool.tool_status) {
      case 'completed':
        return 'bg-green-100 text-green-800';
      case 'failed':
        return 'bg-red-100 text-red-800';
      case 'executing':
        return 'bg-blue-100 text-blue-800';
      case 'pending':
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <div className={`border rounded-lg p-4 mb-4 bg-white shadow-sm transition-all duration-200 ${expanded ? 'border-blue-300' : ''}`}>
      {/* Card Header - Always visible */}
      <div
        className={`flex justify-between items-center mb-2 ${isExpandable ? 'cursor-pointer' : ''}`}
        onClick={() => isExpandable && handleToggleExpand()}
      >
        <div className="flex items-center gap-2">
          {/* Show human-readable tool name */}
          <h3 className="text-lg font-semibold">
            {formatToolName(actualToolName || tool.tool_name)}
          </h3>

          {/* Loading Spinner */}
          {isLoading && (
            <div className="animate-spin h-4 w-4 border-2 border-blue-500 border-t-transparent rounded-full"></div>
          )}
        </div>

        <div className="flex items-center gap-2">
          {/* Status Badge */}
          <span className={`px-2 py-1 text-xs rounded-full ${getStatusBadgeClass()}`}>
            {tool.tool_status}
          </span>

          {/* Expand/Collapse Icon (only if expandable) */}
          {isExpandable && (
            <button
              className="text-gray-500 hover:text-gray-700 focus:outline-none"
              aria-label={expanded ? "Collapse" : "Expand"}
              onClick={(e) => {
                e.stopPropagation(); // Prevent double triggering with the parent onClick
                handleToggleExpand();
              }}
            >
              <svg
                className={`h-5 w-5 transition-transform ${expanded ? 'rotate-180' : ''}`}
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </button>
          )}
        </div>
      </div>

      {/* Brief Description - Always visible */}
      <p className="text-sm text-gray-600 mb-2">
        {actualToolName ? `Backend tool execution` : tool.tool_description}
      </p>

      {/* Expandable Details Section */}
      {expanded && (
        <div className="mt-3 pt-3 border-t border-gray-200">
          {/* Tool ID removed as per request */}

          {/* Parameters Section */}
          {tool.tool_parameters && (() => {
            const formattedParams = formatToolOutput(actualToolArgs || tool.tool_parameters);

            return (
              <div className="mb-3">
                <h4 className="text-sm font-medium mb-1">Parameters:</h4>

                {/* Render based on detected type */}
                {formattedParams.type === 'json' && (
                  <pre className="text-xs bg-gray-50 p-2 rounded overflow-x-auto">
                    {formattedParams.content}
                  </pre>
                )}

                {formattedParams.type === 'markdown' && (
                  <div className="text-xs bg-gray-50 p-2 rounded overflow-x-auto prose prose-sm max-w-none">
                    <ReactMarkdown>{formattedParams.content}</ReactMarkdown>
                  </div>
                )}

                {formattedParams.type === 'text' && (
                  <div className="text-xs bg-gray-50 p-2 rounded overflow-x-auto whitespace-pre-wrap">
                    {formattedParams.content}
                  </div>
                )}
              </div>
            );
          })()}

          {/* Output Section */}
          {tool.tool_output && (() => {
            const formattedOutput = formatToolOutput(actualToolResult);

            return (
              <div className="mb-3">
                <h4 className="text-sm font-medium mb-1">Output:</h4>

                {/* Render based on detected type */}
                {formattedOutput.type === 'json' && (
                  <pre className="text-xs bg-gray-50 p-2 rounded overflow-x-auto">
                    {formattedOutput.content}
                  </pre>
                )}

                {formattedOutput.type === 'markdown' && (
                  <div className="text-xs bg-gray-50 p-2 rounded overflow-x-auto prose prose-sm max-w-none">
                    <ReactMarkdown>{formattedOutput.content}</ReactMarkdown>
                  </div>
                )}

                {formattedOutput.type === 'text' && (
                  <div className="text-xs bg-gray-50 p-2 rounded overflow-x-auto whitespace-pre-wrap">
                    {formattedOutput.content}
                  </div>
                )}
              </div>
            );
          })()}

          {/* Error Section */}
          {tool.tool_error && (() => {
            const formattedError = formatToolOutput(tool.tool_error);

            return (
              <div className="mb-3">
                <h4 className="text-sm font-medium text-red-600 mb-1">Error:</h4>

                {/* Render based on detected type */}
                {formattedError.type === 'json' && (
                  <pre className="text-xs bg-red-50 text-red-700 p-2 rounded overflow-x-auto">
                    {formattedError.content}
                  </pre>
                )}

                {formattedError.type === 'markdown' && (
                  <div className="text-xs bg-red-50 text-red-700 p-2 rounded overflow-x-auto prose prose-sm max-w-none">
                    <ReactMarkdown>{formattedError.content}</ReactMarkdown>
                  </div>
                )}

                {formattedError.type === 'text' && (
                  <div className="text-xs bg-red-50 text-red-700 p-2 rounded overflow-x-auto whitespace-pre-wrap">
                    {formattedError.content}
                  </div>
                )}
              </div>
            );
          })()}
        </div>
      )}

      {/* Hint for expandable cards */}
      {isExpandable && !expanded && (
        <div className="mt-1 text-xs text-gray-400 flex items-center">
          <svg className="h-3 w-3 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          Click to view details
        </div>
      )}
    </div>
  );
};

export default ToolInfoCard;
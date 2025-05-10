import React, { useState, useEffect } from 'react';

interface ToolInfo {
  tool_name: string;
  tool_description: string;
  tool_parameters?: object;
  tool_status: 'pending' | 'executing' | 'completed' | 'failed';
  tool_output?: object;
  tool_id?: string;
  tool_error?: string;
}

interface ToolInfoCardProps {
  tool: ToolInfo;
}

const ToolInfoCard: React.FC<ToolInfoCardProps> = ({ tool }) => {
  const [expanded, setExpanded] = useState(false);

  // Log tool status for debugging
  console.log(`ToolInfoCard rendering for ${tool.tool_name} with status: ${tool.tool_status}`, tool);

  // Determine if the tool has details to show
  const hasDetails = tool.tool_parameters || tool.tool_output || tool.tool_error;

  // Force expanded state to true when tool is completed
  useEffect(() => {
    if (tool.tool_status === 'completed' && !expanded && hasDetails) {
      console.log(`Auto-expanding completed tool: ${tool.tool_name}`);
      setExpanded(true);
    }
  }, [tool.tool_status, expanded, hasDetails, tool.tool_name]);

  // Determine if the tool is in a loading state
  const isLoading = tool.tool_status === 'pending' || tool.tool_status === 'executing';

  // Determine if the card should be expandable
  const isExpandable = hasDetails && !isLoading;

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
        onClick={() => isExpandable && setExpanded(!expanded)}
      >
        <div className="flex items-center gap-2">
          <h3 className="text-lg font-semibold">{tool.tool_name}</h3>

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
      <p className="text-sm text-gray-600 mb-2">{tool.tool_description}</p>

      {/* Expandable Details Section */}
      {expanded && (
        <div className="mt-3 pt-3 border-t border-gray-200">
          {/* Tool ID if available */}
          {tool.tool_id && (
            <div className="mb-3">
              <h4 className="text-sm font-medium mb-1">Tool ID:</h4>
              <p className="text-xs text-gray-600">{tool.tool_id}</p>
            </div>
          )}

          {/* Parameters Section */}
          {tool.tool_parameters && (
            <div className="mb-3">
              <h4 className="text-sm font-medium mb-1">Parameters:</h4>
              <pre className="text-xs bg-gray-50 p-2 rounded overflow-x-auto">
                {JSON.stringify(tool.tool_parameters, null, 2)}
              </pre>
            </div>
          )}

          {/* Output Section */}
          {tool.tool_output && (
            <div className="mb-3">
              <h4 className="text-sm font-medium mb-1">Output:</h4>
              <pre className="text-xs bg-gray-50 p-2 rounded overflow-x-auto">
                {JSON.stringify(tool.tool_output, null, 2)}
              </pre>
            </div>
          )}

          {/* Error Section */}
          {tool.tool_error && (
            <div className="mb-3">
              <h4 className="text-sm font-medium text-red-600 mb-1">Error:</h4>
              <pre className="text-xs bg-red-50 text-red-700 p-2 rounded overflow-x-auto">
                {tool.tool_error}
              </pre>
            </div>
          )}
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
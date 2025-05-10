import React from 'react';

interface ToolInfo {
  tool_name: string;
  tool_description: string;
  tool_parameters?: object;
  tool_status: 'pending' | 'executing' | 'completed' | 'failed';
  tool_output?: object;
}

interface ToolInfoCardProps {
  tool: ToolInfo;
}

const ToolInfoCard: React.FC<ToolInfoCardProps> = ({ tool }) => {
  return (
    <div className="border rounded-lg p-4 mb-4 bg-white shadow-sm">
      <div className="flex justify-between items-start mb-2">
        <h3 className="text-lg font-semibold">{tool.tool_name}</h3>
        <span className={`px-2 py-1 text-xs rounded-full ${
          tool.tool_status === 'completed' ? 'bg-green-100 text-green-800' :
          tool.tool_status === 'failed' ? 'bg-red-100 text-red-800' :
          tool.tool_status === 'executing' ? 'bg-blue-100 text-blue-800' :
          'bg-gray-100 text-gray-800'
        }`}>
          {tool.tool_status}
        </span>
      </div>
      
      <p className="text-sm text-gray-600 mb-3">{tool.tool_description}</p>
      
      {tool.tool_parameters && (
        <div className="mb-3">
          <h4 className="text-sm font-medium mb-1">Parameters:</h4>
          <pre className="text-xs bg-gray-50 p-2 rounded overflow-x-auto">
            {JSON.stringify(tool.tool_parameters, null, 2)}
          </pre>
        </div>
      )}
      
      {tool.tool_output && (
        <div>
          <h4 className="text-sm font-medium mb-1">Output:</h4>
          <pre className="text-xs bg-gray-50 p-2 rounded overflow-x-auto">
            {JSON.stringify(tool.tool_output, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
};

export default ToolInfoCard;
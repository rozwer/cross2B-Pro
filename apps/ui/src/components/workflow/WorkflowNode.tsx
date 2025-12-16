'use client';

import { memo } from 'react';
import { Handle, Position, type NodeProps } from 'reactflow';
import { Settings2, Play, CheckCircle2, AlertCircle, Loader2 } from 'lucide-react';
import type { WorkflowNodeData } from '@/lib/workflow-graph';
import { getProviderColor, getNodeTypeIcon } from '@/lib/workflow-graph';
import { cn } from '@/lib/utils';

interface WorkflowNodeProps extends NodeProps<WorkflowNodeData> {
  onNodeClick?: (nodeId: string, data: WorkflowNodeData) => void;
  status?: 'pending' | 'running' | 'completed' | 'failed';
}

function WorkflowNodeComponent({
  id,
  data,
  selected,
  ...props
}: WorkflowNodeProps) {
  const colors = getProviderColor(data.aiProvider);
  const typeIcon = getNodeTypeIcon(data.nodeType);
  const status = (props as unknown as { status?: string }).status;

  const getStatusIcon = () => {
    switch (status) {
      case 'running':
        return <Loader2 className="h-3.5 w-3.5 animate-spin text-blue-500" />;
      case 'completed':
        return <CheckCircle2 className="h-3.5 w-3.5 text-green-500" />;
      case 'failed':
        return <AlertCircle className="h-3.5 w-3.5 text-red-500" />;
      default:
        return null;
    }
  };

  return (
    <div
      className={cn(
        'relative rounded-xl border-2 shadow-lg transition-all duration-200',
        'min-w-[140px] max-w-[180px]',
        'hover:shadow-xl hover:-translate-y-0.5',
        colors.bg,
        colors.border,
        selected && 'ring-2 ring-offset-2 ring-blue-500'
      )}
    >
      {/* Input Handle */}
      <Handle
        type="target"
        position={Position.Left}
        className="!w-3 !h-3 !bg-gray-400 !border-2 !border-white"
      />

      {/* Node Content */}
      <div className="p-3">
        {/* Header */}
        <div className="flex items-center justify-between gap-2 mb-2">
          <div className="flex items-center gap-1.5">
            <span className="text-lg">{typeIcon}</span>
            <span className={cn('text-sm font-bold', colors.text)}>
              {data.label}
            </span>
          </div>
          <div className="flex items-center gap-1">
            {getStatusIcon()}
            {data.configurable && (
              <button
                className="p-1 rounded hover:bg-white/50 transition-colors"
                onClick={(e) => {
                  e.stopPropagation();
                  // Trigger node settings
                }}
              >
                <Settings2 className="h-3.5 w-3.5 text-gray-500" />
              </button>
            )}
          </div>
        </div>

        {/* Description */}
        <p className="text-xs text-gray-600 mb-2 line-clamp-2">
          {data.description}
        </p>

        {/* Provider Badge */}
        <div className="flex items-center justify-between">
          <span
            className={cn(
              'inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium',
              colors.bg,
              colors.text,
              'border',
              colors.border
            )}
          >
            {colors.icon}
            {data.aiProvider === 'gemini' && 'Gemini'}
            {data.aiProvider === 'claude' && 'Claude'}
            {data.aiProvider === 'manual' && '手動'}
            {data.aiProvider === 'tool' && 'ツール'}
          </span>
          {data.outputFile && (
            <span className="text-[10px] text-gray-400 truncate max-w-[60px]">
              {data.outputFile}
            </span>
          )}
        </div>
      </div>

      {/* Output Handle */}
      <Handle
        type="source"
        position={Position.Right}
        className="!w-3 !h-3 !bg-gray-400 !border-2 !border-white"
      />
    </div>
  );
}

export const WorkflowNode = memo(WorkflowNodeComponent);

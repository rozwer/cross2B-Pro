'use client';

import { memo } from 'react';
import { Handle, Position, type NodeProps } from 'reactflow';
import { Hand, CheckCircle2, XCircle, Loader2 } from 'lucide-react';
import type { WorkflowNodeData } from '@/lib/workflow-graph';
import { cn } from '@/lib/utils';

interface ApprovalNodeProps extends NodeProps<WorkflowNodeData> {
  status?: 'pending' | 'waiting' | 'approved' | 'rejected';
}

function ApprovalNodeComponent({
  id,
  data,
  selected,
  ...props
}: ApprovalNodeProps) {
  const status = (props as unknown as { status?: string }).status;

  const getStatusStyles = () => {
    switch (status) {
      case 'waiting':
        return {
          bg: 'bg-yellow-50',
          border: 'border-yellow-400',
          text: 'text-yellow-700',
          icon: <Loader2 className="h-5 w-5 animate-spin text-yellow-500" />,
        };
      case 'approved':
        return {
          bg: 'bg-green-50',
          border: 'border-green-400',
          text: 'text-green-700',
          icon: <CheckCircle2 className="h-5 w-5 text-green-500" />,
        };
      case 'rejected':
        return {
          bg: 'bg-red-50',
          border: 'border-red-400',
          text: 'text-red-700',
          icon: <XCircle className="h-5 w-5 text-red-500" />,
        };
      default:
        return {
          bg: 'bg-amber-50',
          border: 'border-amber-400',
          text: 'text-amber-700',
          icon: <Hand className="h-5 w-5 text-amber-500" />,
        };
    }
  };

  const styles = getStatusStyles();

  return (
    <div
      className={cn(
        'relative rounded-xl border-2 shadow-lg transition-all duration-200',
        'min-w-[120px]',
        'hover:shadow-xl hover:-translate-y-0.5',
        styles.bg,
        styles.border,
        selected && 'ring-2 ring-offset-2 ring-amber-500'
      )}
    >
      {/* Input Handle */}
      <Handle
        type="target"
        position={Position.Left}
        className="!w-3 !h-3 !bg-amber-400 !border-2 !border-white"
      />

      {/* Node Content */}
      <div className="p-4 text-center">
        <div className="flex flex-col items-center gap-2">
          {styles.icon}
          <span className={cn('text-sm font-bold', styles.text)}>
            {data.label}
          </span>
          <span className="text-xs text-gray-500">{data.description}</span>
        </div>
      </div>

      {/* Output Handle */}
      <Handle
        type="source"
        position={Position.Right}
        className="!w-3 !h-3 !bg-amber-400 !border-2 !border-white"
      />
    </div>
  );
}

export const ApprovalNode = memo(ApprovalNodeComponent);

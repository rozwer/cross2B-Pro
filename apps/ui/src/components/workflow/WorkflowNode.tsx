'use client';

import { memo } from 'react';
import { Handle, Position, type Node } from '@xyflow/react';
import {
  FileText,
  Search,
  Brain,
  GitBranch,
  CheckCircle,
  Pause,
  Settings,
  Sparkles,
  FileCheck,
  Package,
  FileOutput,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import type { LLMPlatform } from '@/lib/types';

export interface WorkflowNodeData extends Record<string, unknown> {
  stepId: string;
  label: string;
  description: string;
  aiModel: LLMPlatform;
  modelName: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'waiting';
  isApprovalPoint?: boolean;
  isParallel?: boolean;
  stepType: 'input' | 'analysis' | 'generation' | 'verification' | 'output' | 'approval';
  onNodeClick?: (stepId: string) => void;
}

export type WorkflowNodeType = Node<WorkflowNodeData, 'workflowNode'>;

interface WorkflowNodeProps {
  data: WorkflowNodeData;
  selected?: boolean;
}

const STEP_ICONS: Record<string, React.ElementType> = {
  'step-1': FileText,
  step0: Settings,
  step1: Search,
  step2: FileCheck,
  step3a: Brain,
  step3b: Brain,
  step3c: Brain,
  approval: Pause,
  step4: GitBranch,
  step5: Search,
  step6: Sparkles,
  'step6.5': Package,
  step7a: FileOutput,
  step7b: FileOutput,
  step8: CheckCircle,
  step9: Sparkles,
  step10: FileOutput,
};

const MODEL_COLORS: Record<LLMPlatform, { bg: string; border: string; text: string }> = {
  gemini: { bg: 'bg-blue-50', border: 'border-blue-400', text: 'text-blue-700' },
  anthropic: { bg: 'bg-orange-50', border: 'border-orange-400', text: 'text-orange-700' },
  openai: { bg: 'bg-green-50', border: 'border-green-400', text: 'text-green-700' },
};

const STATUS_STYLES: Record<string, string> = {
  pending: 'opacity-60',
  running: 'ring-2 ring-blue-400 animate-pulse',
  completed: 'ring-2 ring-green-400',
  failed: 'ring-2 ring-red-400',
  waiting: 'ring-2 ring-yellow-400',
};

function WorkflowNodeComponent({ data, selected }: WorkflowNodeProps) {
  const Icon = STEP_ICONS[data.stepId] || Brain;
  const modelColor = MODEL_COLORS[data.aiModel];

  const handleClick = () => {
    data.onNodeClick?.(data.stepId);
  };

  return (
    <div
      className={cn(
        'min-w-[180px] rounded-lg border-2 shadow-md transition-all duration-200 cursor-pointer',
        modelColor.bg,
        modelColor.border,
        STATUS_STYLES[data.status],
        selected && 'ring-2 ring-primary-500 ring-offset-2',
        data.isApprovalPoint && 'border-dashed border-yellow-500 bg-yellow-50'
      )}
      onClick={handleClick}
    >
      {/* Input handle */}
      <Handle
        type="target"
        position={Position.Top}
        className="!w-3 !h-3 !bg-gray-400 !border-2 !border-white"
      />

      {/* Header */}
      <div
        className={cn(
          'px-3 py-2 rounded-t-lg border-b flex items-center gap-2',
          modelColor.border,
          data.isApprovalPoint ? 'bg-yellow-100' : modelColor.bg
        )}
      >
        <Icon className={cn('w-4 h-4', modelColor.text)} />
        <span className={cn('text-sm font-semibold', modelColor.text)}>{data.label}</span>
        {data.isParallel && (
          <span className="text-xs bg-purple-100 text-purple-700 px-1.5 py-0.5 rounded">
            並列
          </span>
        )}
      </div>

      {/* Body */}
      <div className="px-3 py-2">
        <p className="text-xs text-gray-600 mb-2 line-clamp-2">{data.description}</p>

        {/* Model Badge */}
        {!data.isApprovalPoint && (
          <div className="flex items-center gap-1.5">
            <div
              className={cn(
                'text-xs px-2 py-0.5 rounded-full font-medium',
                modelColor.bg,
                modelColor.text,
                'border',
                modelColor.border
              )}
            >
              {data.aiModel === 'gemini' && '🔵'}
              {data.aiModel === 'anthropic' && '🟠'}
              {data.aiModel === 'openai' && '🟢'}
              {' '}
              {data.modelName}
            </div>
          </div>
        )}

        {/* Status indicator */}
        <div className="mt-2 flex items-center gap-1.5">
          <div
            className={cn(
              'w-2 h-2 rounded-full',
              data.status === 'pending' && 'bg-gray-400',
              data.status === 'running' && 'bg-blue-500 animate-pulse',
              data.status === 'completed' && 'bg-green-500',
              data.status === 'failed' && 'bg-red-500',
              data.status === 'waiting' && 'bg-yellow-500'
            )}
          />
          <span className="text-xs text-gray-500 capitalize">{data.status}</span>
        </div>
      </div>

      {/* Output handle */}
      <Handle
        type="source"
        position={Position.Bottom}
        className="!w-3 !h-3 !bg-gray-400 !border-2 !border-white"
      />
    </div>
  );
}

export const WorkflowNode = memo(WorkflowNodeComponent);

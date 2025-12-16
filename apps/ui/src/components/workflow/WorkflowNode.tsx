'use client';

import { memo, useState } from 'react';
import { Handle, Position, NodeProps } from 'reactflow';
import {
  ChevronDown,
  Cpu,
  User,
  Globe,
  CheckCircle,
  Pause,
  Settings,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import {
  StepAIProvider,
  getProviderColor,
  getProviderLabel,
} from './workflowConfig';

export interface WorkflowNodeData {
  label: string;
  description: string;
  provider: StepAIProvider;
  allowedProviders: StepAIProvider[];
  isParallel?: boolean;
  isApprovalPoint?: boolean;
  status?: 'pending' | 'running' | 'completed' | 'failed';
  onProviderChange?: (provider: StepAIProvider) => void;
}

function WorkflowNodeComponent({ data, selected }: NodeProps<WorkflowNodeData>) {
  const [showDropdown, setShowDropdown] = useState(false);

  const handleProviderSelect = (provider: StepAIProvider) => {
    data.onProviderChange?.(provider);
    setShowDropdown(false);
  };

  const getStatusStyles = () => {
    switch (data.status) {
      case 'running':
        return 'ring-2 ring-blue-400 animate-pulse';
      case 'completed':
        return 'ring-2 ring-green-400';
      case 'failed':
        return 'ring-2 ring-red-400';
      default:
        return '';
    }
  };

  const getProviderIcon = (provider: StepAIProvider) => {
    switch (provider) {
      case 'gemini':
        return <Cpu className="h-3.5 w-3.5" />;
      case 'claude':
        return <Cpu className="h-3.5 w-3.5" />;
      case 'gemini+web':
        return <Globe className="h-3.5 w-3.5" />;
      case 'manual':
        return <User className="h-3.5 w-3.5" />;
      default:
        return <Settings className="h-3.5 w-3.5" />;
    }
  };

  const isConfigurable = data.allowedProviders.length > 1;

  return (
    <div
      className={cn(
        'relative min-w-[160px] rounded-lg border bg-white shadow-md transition-all duration-200',
        selected ? 'border-primary-500 shadow-lg' : 'border-gray-200',
        data.isApprovalPoint
          ? 'border-yellow-400 bg-yellow-50'
          : data.isParallel
            ? 'border-blue-300 bg-blue-50/50'
            : '',
        getStatusStyles()
      )}
    >
      {/* Input Handle */}
      <Handle
        type="target"
        position={Position.Left}
        className="!h-3 !w-3 !border-2 !border-gray-300 !bg-white"
      />

      {/* Header with Provider Badge */}
      <div className="flex items-center justify-between border-b border-gray-100 px-3 py-2">
        <span className="text-sm font-semibold text-gray-800">{data.label}</span>
        {data.status === 'completed' && (
          <CheckCircle className="h-4 w-4 text-green-500" />
        )}
        {data.isApprovalPoint && (
          <Pause className="h-4 w-4 text-yellow-600" />
        )}
      </div>

      {/* Body */}
      <div className="px-3 py-2">
        <p className="mb-2 text-xs text-gray-500">{data.description}</p>

        {/* Provider Selector */}
        <div className="relative">
          <button
            onClick={() => isConfigurable && setShowDropdown(!showDropdown)}
            className={cn(
              'flex w-full items-center justify-between gap-2 rounded-md px-2 py-1.5 text-xs font-medium text-white transition-colors',
              getProviderColor(data.provider),
              isConfigurable
                ? 'cursor-pointer hover:opacity-90'
                : 'cursor-default'
            )}
          >
            <span className="flex items-center gap-1.5">
              {getProviderIcon(data.provider)}
              {getProviderLabel(data.provider)}
            </span>
            {isConfigurable && (
              <ChevronDown
                className={cn(
                  'h-3 w-3 transition-transform',
                  showDropdown && 'rotate-180'
                )}
              />
            )}
          </button>

          {/* Dropdown */}
          {showDropdown && isConfigurable && (
            <div className="absolute left-0 right-0 top-full z-50 mt-1 overflow-hidden rounded-md border border-gray-200 bg-white shadow-lg">
              {data.allowedProviders.map((provider) => (
                <button
                  key={provider}
                  onClick={() => handleProviderSelect(provider)}
                  className={cn(
                    'flex w-full items-center gap-2 px-2 py-1.5 text-left text-xs transition-colors hover:bg-gray-50',
                    provider === data.provider && 'bg-gray-100'
                  )}
                >
                  <span
                    className={cn(
                      'flex h-5 w-5 items-center justify-center rounded text-white',
                      getProviderColor(provider)
                    )}
                  >
                    {getProviderIcon(provider)}
                  </span>
                  <span className="text-gray-700">
                    {getProviderLabel(provider)}
                  </span>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Parallel Indicator */}
      {data.isParallel && (
        <div className="absolute -right-1 -top-1 flex h-5 w-5 items-center justify-center rounded-full bg-blue-500 text-[10px] font-bold text-white shadow">
          P
        </div>
      )}

      {/* Output Handle */}
      <Handle
        type="source"
        position={Position.Right}
        className="!h-3 !w-3 !border-2 !border-gray-300 !bg-white"
      />
    </div>
  );
}

export const WorkflowNode = memo(WorkflowNodeComponent);

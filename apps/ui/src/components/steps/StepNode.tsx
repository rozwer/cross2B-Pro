'use client';

import { CheckCircle, XCircle, Clock, Loader2, Pause, RotateCcw, Play, AlertTriangle } from 'lucide-react';
import type { Step, StepStatus } from '@/lib/types';
import { cn } from '@/lib/utils';

interface StepNodeProps {
  stepName: string;
  label: string;
  step?: Step;
  index: number;
  isCurrent: boolean;
  isWaitingApproval: boolean;
  isLast: boolean;
  onRetry?: (stepName: string) => void;
  onResume?: (stepName: string) => void;
}

const statusConfig: Record<StepStatus | 'waiting' | 'default', {
  icon: React.ComponentType<{ className?: string }>;
  iconBg: string;
  iconColor: string;
  lineColor: string;
}> = {
  completed: {
    icon: CheckCircle,
    iconBg: 'bg-success-100',
    iconColor: 'text-success-600',
    lineColor: 'bg-success-300',
  },
  failed: {
    icon: XCircle,
    iconBg: 'bg-error-100',
    iconColor: 'text-error-600',
    lineColor: 'bg-error-300',
  },
  running: {
    icon: Loader2,
    iconBg: 'bg-accent-100',
    iconColor: 'text-accent-600',
    lineColor: 'bg-accent-300',
  },
  skipped: {
    icon: Clock,
    iconBg: 'bg-gray-100',
    iconColor: 'text-gray-400',
    lineColor: 'bg-gray-200',
  },
  pending: {
    icon: Clock,
    iconBg: 'bg-gray-100',
    iconColor: 'text-gray-400',
    lineColor: 'bg-gray-200',
  },
  waiting: {
    icon: Pause,
    iconBg: 'bg-warning-100',
    iconColor: 'text-warning-600',
    lineColor: 'bg-warning-300',
  },
  default: {
    icon: Clock,
    iconBg: 'bg-gray-100',
    iconColor: 'text-gray-300',
    lineColor: 'bg-gray-200',
  },
};

export function StepNode({
  stepName,
  label,
  step,
  index,
  isCurrent,
  isWaitingApproval,
  isLast,
  onRetry,
  onResume,
}: StepNodeProps) {
  const status = step?.status;
  const attempts = step?.attempts || [];
  const lastAttempt = attempts[attempts.length - 1];

  const configKey = isWaitingApproval ? 'waiting' : (status || 'default');
  const config = statusConfig[configKey];
  const IconComponent = config.icon;
  const isRunning = status === 'running';

  return (
    <div
      className={cn(
        'relative group animate-fade-in',
      )}
      style={{ animationDelay: `${index * 30}ms` }}
    >
      {/* Connector line */}
      {!isLast && (
        <div
          className={cn(
            'absolute left-[15px] top-[32px] w-0.5 h-[calc(100%-8px)] transition-colors duration-300',
            status === 'completed' ? config.lineColor : 'bg-gray-200'
          )}
        />
      )}

      <div
        className={cn(
          'flex items-start gap-3 p-2 rounded-lg transition-all duration-200',
          isCurrent && !isWaitingApproval && 'bg-accent-50',
          isWaitingApproval && 'bg-warning-50',
          status === 'failed' && 'bg-error-50',
          !isCurrent && !status && 'opacity-60 group-hover:opacity-100'
        )}
      >
        {/* Icon */}
        <div
          className={cn(
            'flex-shrink-0 w-8 h-8 rounded-lg flex items-center justify-center transition-all',
            config.iconBg
          )}
        >
          <IconComponent
            className={cn(
              'h-4 w-4 transition-all',
              config.iconColor,
              isRunning && 'animate-spin'
            )}
          />
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0 pt-1">
          <div className="flex items-center justify-between gap-2">
            <span
              className={cn(
                'text-sm font-medium transition-colors',
                status === 'completed' && 'text-success-700',
                status === 'failed' && 'text-error-700',
                status === 'running' && 'text-accent-700',
                isWaitingApproval && 'text-warning-700',
                !status && 'text-gray-500'
              )}
            >
              {label}
            </span>

            {/* Action buttons */}
            {status === 'failed' && (
              <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                {onRetry && (
                  <button
                    onClick={() => onRetry(stepName)}
                    className="inline-flex items-center gap-1 px-2 py-1 text-xs font-medium text-error-600 hover:text-error-700 hover:bg-error-100 rounded-md transition-all"
                    title="リトライ"
                  >
                    <RotateCcw className="h-3 w-3" />
                  </button>
                )}
                {onResume && (
                  <button
                    onClick={() => onResume(stepName)}
                    className="inline-flex items-center gap-1 px-2 py-1 text-xs font-medium text-accent-600 hover:text-accent-700 hover:bg-accent-100 rounded-md transition-all"
                    title="ここから再実行"
                  >
                    <Play className="h-3 w-3" />
                  </button>
                )}
              </div>
            )}
          </div>

          {/* Additional info */}
          {attempts.length > 1 && (
            <p className="text-xs text-gray-500 mt-0.5 flex items-center gap-1">
              <AlertTriangle className="h-3 w-3" />
              {attempts.length}回目の試行
            </p>
          )}

          {lastAttempt?.error && (
            <p className="text-xs text-error-600 mt-1 line-clamp-1">
              {lastAttempt.error.message}
            </p>
          )}

          {isWaitingApproval && (
            <p className="text-xs text-warning-600 mt-1 flex items-center gap-1">
              <Pause className="h-3 w-3" />
              承認待ち
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

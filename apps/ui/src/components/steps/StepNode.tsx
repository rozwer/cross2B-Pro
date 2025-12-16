'use client';

import { CheckCircle, XCircle, Clock, Loader2, Pause, RotateCcw, Play } from 'lucide-react';
import type { Step, StepStatus } from '@/lib/types';
import { cn } from '@/lib/utils';

interface StepNodeProps {
  stepName: string;
  label: string;
  step?: Step;
  isCurrent: boolean;
  isWaitingApproval: boolean;
  isLast: boolean;
  onRetry?: (stepName: string) => void;
  onResume?: (stepName: string) => void;
}

function getStatusIcon(status: StepStatus | undefined, isCurrent: boolean, isWaitingApproval: boolean) {
  if (isWaitingApproval) {
    return <Pause className="h-4 w-4 text-yellow-500" />;
  }

  switch (status) {
    case 'completed':
      return <CheckCircle className="h-4 w-4 text-green-500" />;
    case 'failed':
      return <XCircle className="h-4 w-4 text-red-500" />;
    case 'running':
      return <Loader2 className="h-4 w-4 text-blue-500 animate-spin" />;
    case 'skipped':
      return <Clock className="h-4 w-4 text-gray-400" />;
    default:
      return <div className="h-4 w-4 rounded-full border-2 border-gray-300" />;
  }
}

export function StepNode({
  stepName,
  label,
  step,
  isCurrent,
  isWaitingApproval,
  isLast,
  onRetry,
  onResume,
}: StepNodeProps) {
  const status = step?.status;
  const attempts = step?.attempts || [];
  const lastAttempt = attempts[attempts.length - 1];

  return (
    <div className="relative">
      {/* 接続線 */}
      {!isLast && (
        <div
          className={cn(
            'absolute left-[7px] top-6 w-0.5 h-6',
            status === 'completed' ? 'bg-green-300' : 'bg-gray-200'
          )}
        />
      )}

      <div
        className={cn(
          'flex items-start gap-3 p-2 rounded-md transition-colors',
          isCurrent && 'bg-blue-50',
          status === 'failed' && 'bg-red-50'
        )}
      >
        {/* ステータスアイコン */}
        <div className="flex-shrink-0 mt-0.5">
          {getStatusIcon(status, isCurrent, isWaitingApproval)}
        </div>

        {/* コンテンツ */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between gap-2">
            <span
              className={cn(
                'text-sm font-medium',
                status === 'completed' && 'text-green-700',
                status === 'failed' && 'text-red-700',
                status === 'running' && 'text-blue-700',
                !status && 'text-gray-500'
              )}
            >
              {label}
            </span>

            {/* アクションボタン */}
            {status === 'failed' && (
              <div className="flex gap-1">
                {onRetry && (
                  <button
                    onClick={() => onRetry(stepName)}
                    className="inline-flex items-center gap-1 px-2 py-1 text-xs font-medium text-red-600 hover:text-red-700 hover:bg-red-100 rounded transition-colors"
                    title="リトライ"
                  >
                    <RotateCcw className="h-3 w-3" />
                    リトライ
                  </button>
                )}
                {onResume && (
                  <button
                    onClick={() => onResume(stepName)}
                    className="inline-flex items-center gap-1 px-2 py-1 text-xs font-medium text-blue-600 hover:text-blue-700 hover:bg-blue-100 rounded transition-colors"
                    title="ここから再実行"
                  >
                    <Play className="h-3 w-3" />
                    再実行
                  </button>
                )}
              </div>
            )}
          </div>

          {/* 追加情報 */}
          {attempts.length > 1 && (
            <p className="text-xs text-gray-500 mt-0.5">
              {attempts.length}回目の試行
            </p>
          )}

          {lastAttempt?.error && (
            <p className="text-xs text-red-600 mt-1 truncate">
              {lastAttempt.error.message}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

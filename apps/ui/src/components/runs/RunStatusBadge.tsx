'use client';

import { cn } from '@/lib/utils';
import type { RunStatus, StepStatus } from '@/lib/types';
import { getStatusColor, getStatusIcon } from '@/lib/types';

interface RunStatusBadgeProps {
  status: RunStatus | StepStatus;
  showIcon?: boolean;
  size?: 'sm' | 'md';
}

const statusLabels: Record<RunStatus | StepStatus, string> = {
  pending: '待機中',
  running: '実行中',
  waiting_approval: '承認待ち',
  completed: '完了',
  failed: '失敗',
  cancelled: 'キャンセル',
  skipped: 'スキップ',
};

export function RunStatusBadge({
  status,
  showIcon = true,
  size = 'md',
}: RunStatusBadgeProps) {
  const colorClass = getStatusColor(status);
  const icon = getStatusIcon(status);

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 rounded-full font-medium',
        colorClass,
        size === 'sm' ? 'px-2 py-0.5 text-xs' : 'px-2.5 py-1 text-sm'
      )}
    >
      {showIcon && <span className="flex-shrink-0">{icon}</span>}
      <span>{statusLabels[status]}</span>
    </span>
  );
}

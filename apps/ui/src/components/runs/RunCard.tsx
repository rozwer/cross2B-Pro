'use client';

import Link from 'next/link';
import { Clock, Cpu, Zap } from 'lucide-react';
import type { RunSummary } from '@/lib/types';
import { RunStatusBadge } from './RunStatusBadge';
import { formatRelativeTime, truncate } from '@/lib/utils';
import { STEP_LABELS } from '@/lib/types';

interface RunCardProps {
  run: RunSummary;
}

export function RunCard({ run }: RunCardProps) {
  const stepLabel = STEP_LABELS[run.current_step] || run.current_step;

  return (
    <Link href={`/runs/${run.id}`}>
      <div className="bg-white rounded-lg border border-gray-200 p-4 hover:border-primary-300 hover:shadow-md transition-all cursor-pointer">
        <div className="flex items-start justify-between mb-3">
          <div className="flex-1 min-w-0">
            <h3 className="text-sm font-semibold text-gray-900 truncate">
              {truncate(run.keyword, 50)}
            </h3>
            <p className="text-xs text-gray-500 mt-1">ID: {run.id.slice(0, 8)}</p>
          </div>
          <RunStatusBadge status={run.status} size="sm" />
        </div>

        <div className="space-y-2">
          <div className="flex items-center gap-2 text-xs text-gray-600">
            <Zap className="h-3.5 w-3.5 flex-shrink-0" />
            <span>現在: {stepLabel}</span>
          </div>

          <div className="flex items-center gap-2 text-xs text-gray-600">
            <Cpu className="h-3.5 w-3.5 flex-shrink-0" />
            <span>
              {run.model_config.platform} / {run.model_config.model}
            </span>
          </div>

          <div className="flex items-center gap-2 text-xs text-gray-500">
            <Clock className="h-3.5 w-3.5 flex-shrink-0" />
            <span>{formatRelativeTime(run.updated_at)}</span>
          </div>
        </div>

        {run.model_config.options?.grounding && (
          <div className="mt-3 pt-3 border-t border-gray-100">
            <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800">
              Grounding有効
            </span>
          </div>
        )}
      </div>
    </Link>
  );
}

'use client';

import Link from 'next/link';
import { Clock, Cpu, Zap, ArrowRight, Sparkles } from 'lucide-react';
import type { RunSummary } from '@/lib/types';
import { RunStatusBadge } from './RunStatusBadge';
import { formatRelativeTime, truncate } from '@/lib/utils';
import { STEP_LABELS } from '@/lib/types';

interface RunCardProps {
  run: RunSummary;
}

export function RunCard({ run }: RunCardProps) {
  const stepLabel = STEP_LABELS[run.current_step] || run.current_step;
  const isActive = run.status === 'running' || run.status === 'waiting_approval';

  return (
    <Link href={`/runs/${run.id}`}>
      <div className="group card card-hover p-5 cursor-pointer relative overflow-hidden">
        {/* Active indicator */}
        {isActive && (
          <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-primary-400 via-primary-500 to-primary-400 animate-shimmer" />
        )}

        {/* Header */}
        <div className="flex items-start justify-between gap-3 mb-4">
          <div className="flex-1 min-w-0">
            <h3 className="text-base font-semibold text-gray-900 group-hover:text-primary-700 transition-colors line-clamp-1">
              {truncate(run.keyword, 50)}
            </h3>
            <p className="text-xs text-gray-400 mt-1 font-mono">
              {run.id.slice(0, 8)}
            </p>
          </div>
          <RunStatusBadge status={run.status} />
        </div>

        {/* Info rows */}
        <div className="space-y-2.5">
          <div className="flex items-center gap-2.5 text-sm">
            <div className="flex items-center justify-center w-7 h-7 rounded-lg bg-primary-50 text-primary-600">
              <Zap className="h-3.5 w-3.5" />
            </div>
            <span className="text-gray-600">{stepLabel}</span>
          </div>

          <div className="flex items-center gap-2.5 text-sm">
            <div className="flex items-center justify-center w-7 h-7 rounded-lg bg-accent-50 text-accent-600">
              <Cpu className="h-3.5 w-3.5" />
            </div>
            <span className="text-gray-600">
              {run.model_config.platform} / {run.model_config.model}
            </span>
          </div>

          <div className="flex items-center gap-2.5 text-sm">
            <div className="flex items-center justify-center w-7 h-7 rounded-lg bg-gray-100 text-gray-500">
              <Clock className="h-3.5 w-3.5" />
            </div>
            <span className="text-gray-500">{formatRelativeTime(run.updated_at)}</span>
          </div>
        </div>

        {/* Grounding badge */}
        {run.model_config.options?.grounding && (
          <div className="mt-4 pt-4 border-t border-gray-100">
            <span className="badge badge-primary">
              <Sparkles className="h-3 w-3" />
              Grounding有効
            </span>
          </div>
        )}

        {/* Hover action hint */}
        <div className="absolute bottom-5 right-5 opacity-0 group-hover:opacity-100 transition-all transform group-hover:translate-x-0 translate-x-2">
          <div className="flex items-center gap-1 text-xs text-primary-600 font-medium">
            詳細を見る
            <ArrowRight className="h-3.5 w-3.5" />
          </div>
        </div>
      </div>
    </Link>
  );
}

'use client';

import { useState, useEffect } from 'react';
import { RefreshCw, Filter } from 'lucide-react';
import type { RunSummary, RunStatus } from '@/lib/types';
import { api } from '@/lib/api';
import { RunCard } from './RunCard';
import { LoadingPage } from '@/components/common/Loading';
import { ErrorMessage } from '@/components/common/ErrorBoundary';
import { cn } from '@/lib/utils';

const STATUS_FILTERS: Array<{ value: RunStatus | 'all'; label: string }> = [
  { value: 'all', label: 'すべて' },
  { value: 'running', label: '実行中' },
  { value: 'waiting_approval', label: '承認待ち' },
  { value: 'completed', label: '完了' },
  { value: 'failed', label: '失敗' },
];

export function RunList() {
  const [runs, setRuns] = useState<RunSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<RunStatus | 'all'>('all');

  const fetchRuns = async () => {
    setLoading(true);
    setError(null);
    try {
      const params = statusFilter !== 'all' ? { status: statusFilter } : {};
      const response = await api.runs.list(params);
      setRuns(response.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch runs');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRuns();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [statusFilter]);

  if (loading) {
    return <LoadingPage text="Runs を読み込み中..." />;
  }

  if (error) {
    return <ErrorMessage message={error} onRetry={fetchRuns} />;
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-2">
          <Filter className="h-4 w-4 text-gray-500" />
          <div className="flex gap-2">
            {STATUS_FILTERS.map((filter) => (
              <button
                key={filter.value}
                onClick={() => setStatusFilter(filter.value)}
                className={cn(
                  'px-3 py-1.5 text-sm font-medium rounded-md transition-colors',
                  statusFilter === filter.value
                    ? 'bg-primary-100 text-primary-700'
                    : 'text-gray-600 hover:bg-gray-100'
                )}
              >
                {filter.label}
              </button>
            ))}
          </div>
        </div>

        <button
          onClick={fetchRuns}
          className="inline-flex items-center gap-2 px-3 py-1.5 text-sm text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-md transition-colors"
        >
          <RefreshCw className="h-4 w-4" />
          更新
        </button>
      </div>

      {runs.length === 0 ? (
        <div className="text-center py-12">
          <p className="text-gray-500">Runがありません</p>
          <a
            href="/runs/new"
            className="inline-flex items-center gap-2 mt-4 px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 transition-colors"
          >
            新規Run作成
          </a>
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {runs.map((run) => (
            <RunCard key={run.id} run={run} />
          ))}
        </div>
      )}
    </div>
  );
}

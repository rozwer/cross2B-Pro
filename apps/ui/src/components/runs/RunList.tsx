'use client';

import { useState, useEffect } from 'react';
import { RefreshCw, Filter, Search, Inbox, Plus } from 'lucide-react';
import Link from 'next/link';
import type { RunSummary, RunStatus } from '@/lib/types';
import { api } from '@/lib/api';
import { RunCard } from './RunCard';
import { LoadingPage, ListSkeleton } from '@/components/common/Loading';
import { ErrorMessage } from '@/components/common/ErrorBoundary';
import { cn } from '@/lib/utils';

const STATUS_FILTERS: Array<{ value: RunStatus | 'all'; label: string; color: string }> = [
  { value: 'all', label: 'すべて', color: 'bg-gray-500' },
  { value: 'running', label: '実行中', color: 'bg-accent-500' },
  { value: 'waiting_approval', label: '承認待ち', color: 'bg-warning-500' },
  { value: 'completed', label: '完了', color: 'bg-success-500' },
  { value: 'failed', label: '失敗', color: 'bg-error-500' },
];

export function RunList() {
  const [runs, setRuns] = useState<RunSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<RunStatus | 'all'>('all');

  const fetchRuns = async (isRefresh = false) => {
    if (isRefresh) {
      setRefreshing(true);
    } else {
      setLoading(true);
    }
    setError(null);

    try {
      const params = statusFilter !== 'all' ? { status: statusFilter } : {};
      const response = await api.runs.list(params);
      setRuns(response?.items ?? []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch runs');
      setRuns([]);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchRuns();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [statusFilter]);

  if (loading) {
    return (
      <div className="animate-fade-in">
        <div className="flex items-center justify-between mb-6">
          <div className="shimmer h-10 w-80 rounded-lg" />
          <div className="shimmer h-10 w-20 rounded-lg" />
        </div>
        <ListSkeleton count={6} />
      </div>
    );
  }

  if (error) {
    return <ErrorMessage message={error} onRetry={() => fetchRuns()} />;
  }

  return (
    <div className="animate-fade-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-6">
        {/* Filter tabs */}
        <div className="flex items-center gap-2 p-1 bg-gray-100 rounded-xl">
          {STATUS_FILTERS.map((filter) => (
            <button
              key={filter.value}
              onClick={() => setStatusFilter(filter.value)}
              className={cn(
                'flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg transition-all duration-200',
                statusFilter === filter.value
                  ? 'bg-white text-gray-900 shadow-sm'
                  : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
              )}
            >
              <span
                className={cn(
                  'w-2 h-2 rounded-full transition-all',
                  statusFilter === filter.value ? filter.color : 'bg-gray-400'
                )}
              />
              {filter.label}
            </button>
          ))}
        </div>

        {/* Refresh button */}
        <button
          onClick={() => fetchRuns(true)}
          disabled={refreshing}
          className="btn btn-ghost"
        >
          <RefreshCw className={cn('h-4 w-4', refreshing && 'animate-spin')} />
          更新
        </button>
      </div>

      {/* Results */}
      {runs.length === 0 ? (
        <EmptyState statusFilter={statusFilter} />
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3 stagger-children">
          {runs.map((run) => (
            <RunCard key={run.id} run={run} />
          ))}
        </div>
      )}

      {/* Count indicator */}
      {runs.length > 0 && (
        <div className="mt-6 text-center">
          <p className="text-sm text-gray-500">
            {runs.length}件のRunを表示中
          </p>
        </div>
      )}
    </div>
  );
}

function EmptyState({ statusFilter }: { statusFilter: RunStatus | 'all' }) {
  const isFiltered = statusFilter !== 'all';

  return (
    <div className="card p-12 text-center animate-fade-in">
      <div className="flex justify-center mb-4">
        <div className="p-4 bg-gray-100 rounded-2xl">
          <Inbox className="h-8 w-8 text-gray-400" />
        </div>
      </div>
      <h3 className="text-lg font-semibold text-gray-900 mb-2">
        {isFiltered ? 'Runが見つかりません' : 'まだRunがありません'}
      </h3>
      <p className="text-gray-500 mb-6 max-w-sm mx-auto">
        {isFiltered
          ? 'フィルター条件を変更するか、新しいRunを作成してください。'
          : '最初のSEO記事を自動生成してみましょう。'}
      </p>
      <Link href="/runs/new" className="btn btn-primary">
        <Plus className="h-4 w-4" />
        新規Run作成
      </Link>
    </div>
  );
}

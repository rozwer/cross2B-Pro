'use client';

import { useState, useEffect, useCallback } from 'react';
import type { RunSummary, PaginatedResponse } from '@/lib/types';
import { api } from '@/lib/api';

interface UseRunsOptions {
  autoFetch?: boolean;
  initialStatus?: string;
  limit?: number;
}

interface UseRunsReturn {
  runs: RunSummary[];
  total: number;
  loading: boolean;
  error: string | null;
  page: number;
  hasMore: boolean;
  fetch: () => Promise<void>;
  nextPage: () => void;
  prevPage: () => void;
  setStatus: (status: string | undefined) => void;
}

export function useRuns(options: UseRunsOptions = {}): UseRunsReturn {
  const { autoFetch = true, initialStatus, limit = 20 } = options;

  const [runs, setRuns] = useState<RunSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [status, setStatusFilter] = useState<string | undefined>(initialStatus);
  const [hasMore, setHasMore] = useState(false);

  const fetch = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.runs.list({
        page,
        limit,
        status,
      });
      setRuns(response.items);
      setTotal(response.total);
      setHasMore(response.has_more);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch runs');
    } finally {
      setLoading(false);
    }
  }, [page, limit, status]);

  useEffect(() => {
    if (autoFetch) {
      fetch();
    }
  }, [autoFetch, fetch]);

  const nextPage = useCallback(() => {
    if (hasMore) {
      setPage((p) => p + 1);
    }
  }, [hasMore]);

  const prevPage = useCallback(() => {
    if (page > 1) {
      setPage((p) => p - 1);
    }
  }, [page]);

  const setStatus = useCallback((newStatus: string | undefined) => {
    setStatusFilter(newStatus);
    setPage(1);
  }, []);

  return {
    runs,
    total,
    loading,
    error,
    page,
    hasMore,
    fetch,
    nextPage,
    prevPage,
    setStatus,
  };
}

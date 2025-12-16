'use client';

import { useState, useEffect, useCallback } from 'react';
import type { Run } from '@/lib/types';
import { api } from '@/lib/api';

interface UseRunOptions {
  autoFetch?: boolean;
}

interface UseRunReturn {
  run: Run | null;
  loading: boolean;
  error: string | null;
  fetch: () => Promise<void>;
  approve: () => Promise<void>;
  reject: (reason: string) => Promise<void>;
  retry: (step: string) => Promise<{ new_attempt_id: string }>;
  resume: (step: string) => Promise<{ new_run_id: string }>;
}

export function useRun(runId: string, options: UseRunOptions = {}): UseRunReturn {
  const { autoFetch = true } = options;

  const [run, setRun] = useState<Run | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetch = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.runs.get(runId);
      setRun(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch run');
    } finally {
      setLoading(false);
    }
  }, [runId]);

  useEffect(() => {
    if (autoFetch) {
      fetch();
    }
  }, [autoFetch, fetch]);

  const approve = useCallback(async () => {
    await api.runs.approve(runId);
    await fetch();
  }, [runId, fetch]);

  const reject = useCallback(
    async (reason: string) => {
      await api.runs.reject(runId, reason);
      await fetch();
    },
    [runId, fetch]
  );

  const retry = useCallback(
    async (step: string) => {
      const result = await api.runs.retry(runId, step);
      await fetch();
      return result;
    },
    [runId, fetch]
  );

  const resume = useCallback(
    async (step: string) => {
      const result = await api.runs.resume(runId, step);
      return result;
    },
    [runId]
  );

  return {
    run,
    loading,
    error,
    fetch,
    approve,
    reject,
    retry,
    resume,
  };
}

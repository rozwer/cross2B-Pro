"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import type { RunSummary, PaginatedResponse } from "@/lib/types";
import { api } from "@/lib/api";

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
  const abortControllerRef = useRef<AbortController | null>(null);
  const isMountedRef = useRef(true);

  // Cleanup on unmount
  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
      abortControllerRef.current?.abort();
    };
  }, []);

  const fetch = useCallback(async () => {
    // Cancel any previous in-flight request to prevent race condition
    abortControllerRef.current?.abort();
    const abortController = new AbortController();
    abortControllerRef.current = abortController;

    setLoading(true);
    setError(null);
    try {
      const response = await api.runs.list({
        page,
        limit,
        status,
      });
      // Only update state if not aborted and still mounted
      if (!abortController.signal.aborted && isMountedRef.current) {
        setRuns(response.items);
        setTotal(response.total);
        setHasMore(response.has_more);
      }
    } catch (err) {
      if (!abortController.signal.aborted && isMountedRef.current) {
        setError(err instanceof Error ? err.message : "Failed to fetch runs");
      }
    } finally {
      if (!abortController.signal.aborted && isMountedRef.current) {
        setLoading(false);
      }
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

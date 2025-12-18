"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import type { Run } from "@/lib/types";
import { api } from "@/lib/api";

interface UseRunOptions {
  autoFetch?: boolean;
  /** ポーリング間隔（ミリ秒）。0 でポーリング無効。デフォルト: 5000 */
  pollingInterval?: number;
  /** 完了・失敗時にポーリングを停止するか。デフォルト: true */
  stopOnComplete?: boolean;
}

interface UseRunReturn {
  run: Run | null;
  /** 初回ローディング中（runがnullの状態でフェッチ中） */
  loading: boolean;
  /** 更新中（runが既にある状態でフェッチ中） */
  refreshing: boolean;
  error: string | null;
  fetch: () => Promise<Run | null>;
  approve: () => Promise<void>;
  reject: (reason: string) => Promise<void>;
  retry: (step: string) => Promise<{ new_attempt_id: string }>;
  resume: (step: string) => Promise<{ new_run_id: string }>;
  /** ポーリング中かどうか */
  isPolling: boolean;
  /** ポーリングを開始 */
  startPolling: () => void;
  /** ポーリングを停止 */
  stopPolling: () => void;
}

export function useRun(runId: string, options: UseRunOptions = {}): UseRunReturn {
  const { autoFetch = true, pollingInterval = 5000, stopOnComplete = true } = options;

  const [run, setRun] = useState<Run | null>(null);
  const [loading, setLoading] = useState(true); // 初回はtrue
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isPolling, setIsPolling] = useState(pollingInterval > 0);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const hasInitialLoadRef = useRef(false);

  const fetch = useCallback(async () => {
    // 初回ローディングか更新中かを判定
    if (!hasInitialLoadRef.current) {
      setLoading(true);
    } else {
      setRefreshing(true);
    }
    setError(null);
    try {
      const data = await api.runs.get(runId);
      setRun(data);
      hasInitialLoadRef.current = true;
      return data;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch run");
      return null;
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [runId]);

  const stopPolling = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    setIsPolling(false);
  }, []);

  const startPolling = useCallback(() => {
    if (pollingInterval <= 0) return;
    stopPolling();
    setIsPolling(true);
    intervalRef.current = setInterval(async () => {
      const data = await fetch();
      // 完了・失敗時にポーリング停止
      if (stopOnComplete && data && (data.status === "completed" || data.status === "failed" || data.status === "cancelled")) {
        stopPolling();
      }
    }, pollingInterval);
  }, [pollingInterval, stopOnComplete, fetch, stopPolling]);

  // 初回フェッチ
  useEffect(() => {
    if (autoFetch) {
      fetch();
    }
  }, [autoFetch, fetch]);

  // ポーリング開始・停止
  useEffect(() => {
    if (pollingInterval > 0 && autoFetch) {
      startPolling();
    }
    return () => {
      stopPolling();
    };
  }, [pollingInterval, autoFetch, startPolling, stopPolling]);

  const approve = useCallback(async () => {
    await api.runs.approve(runId);
    await fetch();
  }, [runId, fetch]);

  const reject = useCallback(
    async (reason: string) => {
      await api.runs.reject(runId, reason);
      await fetch();
    },
    [runId, fetch],
  );

  const retry = useCallback(
    async (step: string) => {
      const result = await api.runs.retry(runId, step);
      await fetch();
      return result;
    },
    [runId, fetch],
  );

  const resume = useCallback(
    async (step: string) => {
      const result = await api.runs.resume(runId, step);
      return result;
    },
    [runId],
  );

  return {
    run,
    loading,
    refreshing,
    error,
    fetch,
    approve,
    reject,
    retry,
    resume,
    isPolling,
    startPolling,
    stopPolling,
  };
}

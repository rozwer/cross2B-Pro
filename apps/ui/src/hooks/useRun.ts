"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import type { Run } from "@/lib/types";
import { api } from "@/lib/api";

/**
 * Normalize step name to API format (underscore notation)
 * UI uses dot notation (step1.5, step3.5, step6.5) but API expects underscore (step1_5, step3_5, step6_5)
 * Also handles parent step3 -> step3a normalization
 */
function normalizeStepForApi(step: string): string {
  // Convert dot notation to underscore
  const normalized = step.replace(/\./g, "_");
  // Normalize parent steps to their entry points (parallel group handling)
  // step3 has subgroups: step3a, step3b, step3c
  // step7 has subgroups: step7a, step7b
  switch (normalized) {
    case "step3":
      return "step3a";
    case "step7":
      return "step7a";
    default:
      return normalized;
  }
}

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
  /** ワークフローを一時停止（次のステップ境界で停止） */
  pause: () => Promise<void>;
  /** 停止状態のワークフローを続行 */
  continueRun: () => Promise<void>;
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
  const prevRunIdRef = useRef<string>(runId);
  const isMountedRef = useRef(true);
  const abortControllerRef = useRef<AbortController | null>(null);
  const stopOnCompleteRef = useRef(stopOnComplete);

  // Keep stopOnComplete ref updated to avoid stale closure
  useEffect(() => {
    stopOnCompleteRef.current = stopOnComplete;
  }, [stopOnComplete]);

  // Cleanup on unmount
  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
      abortControllerRef.current?.abort();
    };
  }, []);

  // Reset state when runId changes
  useEffect(() => {
    if (prevRunIdRef.current !== runId) {
      // Clear old interval before state reset
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
      // Cancel any in-flight request
      abortControllerRef.current?.abort();
      // Reset state for new run
      setRun(null);
      setLoading(true);
      setRefreshing(false);
      setError(null);
      hasInitialLoadRef.current = false;
      prevRunIdRef.current = runId;
    }
  }, [runId]);

  const fetch = useCallback(async () => {
    // Cancel any previous in-flight request
    abortControllerRef.current?.abort();
    const abortController = new AbortController();
    abortControllerRef.current = abortController;

    // 初回ローディングか更新中かを判定
    if (!hasInitialLoadRef.current) {
      setLoading(true);
    } else {
      setRefreshing(true);
    }
    setError(null);
    try {
      const data = await api.runs.get(runId);
      // Check if unmounted or request was aborted
      if (!isMountedRef.current || abortController.signal.aborted) {
        return null;
      }
      setRun(data);
      hasInitialLoadRef.current = true;
      return data;
    } catch (err) {
      // Don't update state if unmounted or aborted
      if (!isMountedRef.current || abortController.signal.aborted) {
        return null;
      }
      setError(err instanceof Error ? err.message : "Failed to fetch run");
      return null;
    } finally {
      if (isMountedRef.current && !abortController.signal.aborted) {
        setLoading(false);
        setRefreshing(false);
      }
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
    // Clear existing interval directly to avoid circular dependency
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    setIsPolling(true);
    intervalRef.current = setInterval(async () => {
      const data = await fetch();
      // 完了・失敗時にポーリング停止 (use ref to get latest value)
      if (stopOnCompleteRef.current && data && (data.status === "completed" || data.status === "failed" || data.status === "cancelled")) {
        if (intervalRef.current) {
          clearInterval(intervalRef.current);
          intervalRef.current = null;
        }
        setIsPolling(false);
      }
    }, pollingInterval);
  }, [pollingInterval, fetch]);

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
    try {
      setError(null);
      await api.runs.approve(runId);
      await fetch();
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to approve run";
      setError(message);
      throw err; // Re-throw for caller handling
    }
  }, [runId, fetch]);

  const reject = useCallback(
    async (reason: string) => {
      try {
        setError(null);
        await api.runs.reject(runId, reason);
        await fetch();
      } catch (err) {
        const message = err instanceof Error ? err.message : "Failed to reject run";
        setError(message);
        throw err; // Re-throw for caller handling
      }
    },
    [runId, fetch],
  );

  const retry = useCallback(
    async (step: string) => {
      try {
        setError(null);
        // Normalize step to API format (dot -> underscore, step3 -> step3a)
        const normalizedStep = normalizeStepForApi(step);
        const result = await api.runs.retry(runId, normalizedStep);
        await fetch();
        return result;
      } catch (err) {
        const message = err instanceof Error ? err.message : `Failed to retry step ${step}`;
        setError(message);
        throw err; // Re-throw for caller handling
      }
    },
    [runId, fetch],
  );

  const resume = useCallback(
    async (step: string) => {
      try {
        setError(null);
        // Normalize step to API format (dot -> underscore, step3 -> step3a)
        const normalizedStep = normalizeStepForApi(step);
        const result = await api.runs.resume(runId, normalizedStep);
        await fetch();
        return result;
      } catch (err) {
        const message = err instanceof Error ? err.message : `Failed to resume from step ${step}`;
        setError(message);
        throw err; // Re-throw for caller handling
      }
    },
    [runId, fetch],
  );

  const pause = useCallback(async () => {
    try {
      setError(null);
      await api.runs.pause(runId);
      await fetch();
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to pause run";
      setError(message);
      throw err; // Re-throw for caller handling
    }
  }, [runId, fetch]);

  const continueRun = useCallback(async () => {
    try {
      setError(null);
      await api.runs.continue(runId);
      await fetch();
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to continue run";
      setError(message);
      throw err; // Re-throw for caller handling
    }
  }, [runId, fetch]);

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
    pause,
    continueRun,
    isPolling,
    startPolling,
    stopPolling,
  };
}

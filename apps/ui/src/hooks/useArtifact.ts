"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import type { ArtifactRef, ArtifactContent } from "@/lib/types";
import { api } from "@/lib/api";

interface UseArtifactsOptions {
  autoFetch?: boolean;
}

interface UseArtifactsReturn {
  artifacts: ArtifactRef[];
  loading: boolean;
  error: string | null;
  fetch: () => Promise<void>;
}

export function useArtifacts(runId: string, options: UseArtifactsOptions = {}): UseArtifactsReturn {
  const { autoFetch = true } = options;

  const [artifacts, setArtifacts] = useState<ArtifactRef[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetch = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.artifacts.list(runId);
      setArtifacts(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch artifacts");
    } finally {
      setLoading(false);
    }
  }, [runId]);

  useEffect(() => {
    if (autoFetch) {
      fetch();
    }
  }, [autoFetch, fetch]);

  return {
    artifacts,
    loading,
    error,
    fetch,
  };
}

interface UseArtifactContentReturn {
  content: ArtifactContent | null;
  loading: boolean;
  error: string | null;
  fetch: () => Promise<void>;
}

export function useArtifactContent(
  runId: string,
  artifactId: string | null,
): UseArtifactContentReturn {
  const [content, setContent] = useState<ArtifactContent | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
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
    // Cancel any previous in-flight request
    abortControllerRef.current?.abort();

    if (!artifactId) {
      setContent(null);
      return;
    }

    const abortController = new AbortController();
    abortControllerRef.current = abortController;

    setLoading(true);
    setError(null);
    try {
      const data = await api.artifacts.download(runId, artifactId);
      // Only update state if not aborted and still mounted
      if (!abortController.signal.aborted && isMountedRef.current) {
        setContent(data);
      }
    } catch (err) {
      if (!abortController.signal.aborted && isMountedRef.current) {
        setError(err instanceof Error ? err.message : "Failed to fetch artifact content");
      }
    } finally {
      if (!abortController.signal.aborted && isMountedRef.current) {
        setLoading(false);
      }
    }
  }, [runId, artifactId]);

  useEffect(() => {
    fetch();
  }, [fetch]);

  return {
    content,
    loading,
    error,
    fetch,
  };
}

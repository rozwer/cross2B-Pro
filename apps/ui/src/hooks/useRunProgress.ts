"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import type { ProgressEvent, RunStatus } from "@/lib/types";
import { createRunProgressWebSocket, type WebSocketStatus } from "@/lib/websocket";

interface UseRunProgressOptions {
  autoConnect?: boolean;
  onEvent?: (event: ProgressEvent) => void;
}

interface UseRunProgressReturn {
  events: ProgressEvent[];
  status: RunStatus;
  wsStatus: WebSocketStatus;
  connect: () => void;
  disconnect: () => void;
  clearEvents: () => void;
}

export function useRunProgress(
  runId: string,
  options: UseRunProgressOptions = {},
): UseRunProgressReturn {
  const { autoConnect = true, onEvent } = options;

  const [events, setEvents] = useState<ProgressEvent[]>([]);
  const [status, setStatus] = useState<RunStatus>("pending");
  const [wsStatus, setWsStatus] = useState<WebSocketStatus>("disconnected");

  const wsRef = useRef<ReturnType<typeof createRunProgressWebSocket> | null>(null);
  const onEventRef = useRef(onEvent);
  onEventRef.current = onEvent;

  const handleMessage = useCallback((event: ProgressEvent) => {
    setEvents((prev) => [...prev, event]);

    // ステータス更新
    switch (event.type) {
      case "step_started":
        setStatus("running");
        break;
      case "approval_requested":
        setStatus("waiting_approval");
        break;
      case "run_completed":
        setStatus("completed");
        break;
      case "run_failed":
      case "error":
        setStatus("failed");
        break;
    }

    // コールバック
    onEventRef.current?.(event);
  }, []);

  const connect = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.disconnect();
    }

    wsRef.current = createRunProgressWebSocket(runId, {
      onMessage: handleMessage,
      onStatusChange: setWsStatus,
      onError: (error) => {
        console.error("WebSocket error:", error);
      },
    });

    wsRef.current.connect();
  }, [runId, handleMessage]);

  const disconnect = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.disconnect();
      wsRef.current = null;
    }
  }, []);

  const clearEvents = useCallback(() => {
    setEvents([]);
  }, []);

  // Track previous runId to detect changes
  const prevRunIdRef = useRef<string>(runId);

  useEffect(() => {
    // If runId changed, clear events from previous run
    if (prevRunIdRef.current !== runId) {
      setEvents([]);
      setStatus("pending");
      prevRunIdRef.current = runId;
    }

    if (autoConnect) {
      connect();
    }

    return () => {
      disconnect();
    };
  }, [autoConnect, connect, disconnect, runId]);

  return {
    events,
    status,
    wsStatus,
    connect,
    disconnect,
    clearEvents,
  };
}

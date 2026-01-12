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
  // Use ref to track connection state without causing re-renders or dependency issues
  const connectionStateRef = useRef<'idle' | 'connecting' | 'connected'>('idle');

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
    // Guard against multiple concurrent connection attempts
    if (connectionStateRef.current === 'connecting') {
      return;
    }

    // Clean up existing connection before creating new one
    if (wsRef.current) {
      wsRef.current.disconnect();
      wsRef.current = null;
    }

    connectionStateRef.current = 'connecting';

    wsRef.current = createRunProgressWebSocket(runId, {
      onMessage: handleMessage,
      onStatusChange: (newStatus) => {
        setWsStatus(newStatus);
        if (newStatus === 'connected') {
          connectionStateRef.current = 'connected';
        } else if (newStatus === 'disconnected' || newStatus === 'error') {
          connectionStateRef.current = 'idle';
        }
      },
      onError: (error) => {
        console.error("WebSocket error:", error);
        connectionStateRef.current = 'idle';
      },
    });

    wsRef.current.connect();
  }, [runId, handleMessage]);

  const disconnect = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.disconnect();
      wsRef.current = null;
    }
    connectionStateRef.current = 'idle';
  }, []);

  const clearEvents = useCallback(() => {
    setEvents([]);
  }, []);

  // Track previous runId to detect changes
  const prevRunIdRef = useRef<string>(runId);

  // Store connect/disconnect in refs to avoid useEffect dependency changes
  // This prevents unnecessary reconnections when the callbacks are recreated
  const connectRef = useRef(connect);
  const disconnectRef = useRef(disconnect);
  connectRef.current = connect;
  disconnectRef.current = disconnect;

  useEffect(() => {
    // If runId changed, clear events from previous run
    if (prevRunIdRef.current !== runId) {
      setEvents([]);
      setStatus("pending");
      prevRunIdRef.current = runId;
    }

    if (autoConnect) {
      connectRef.current();
    }

    return () => {
      disconnectRef.current();
    };
  }, [autoConnect, runId]);

  return {
    events,
    status,
    wsStatus,
    connect,
    disconnect,
    clearEvents,
  };
}

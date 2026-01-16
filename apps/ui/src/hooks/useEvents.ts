"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { api } from "@/lib/api";
import type { EventLogEntry, EventLogFilter, ProgressEvent } from "@/lib/types";

interface UseEventsOptions {
  /** Initial filter settings */
  initialFilter?: EventLogFilter;
  /** Auto-fetch on mount */
  autoFetch?: boolean;
  /** Polling interval in ms (0 = disabled) */
  pollingInterval?: number;
}

interface UseEventsReturn {
  /** DB-persisted events (survives page reload) */
  events: EventLogEntry[];
  /** Loading state */
  loading: boolean;
  /** Error message */
  error: string | null;
  /** Current filter */
  filter: EventLogFilter;
  /** Update filter and refetch */
  setFilter: (filter: EventLogFilter) => void;
  /** Manually fetch events */
  fetch: () => Promise<void>;
  /** Merge WebSocket events into the list */
  mergeRealtimeEvents: (wsEvents: ProgressEvent[]) => void;
  /** Clear all events */
  clear: () => void;
}

/**
 * Hook for fetching and managing event logs from the database.
 * Combines DB-persisted events with real-time WebSocket events.
 */
export function useEvents(
  runId: string,
  options: UseEventsOptions = {},
): UseEventsReturn {
  const { initialFilter = { limit: 100 }, autoFetch = true, pollingInterval = 0 } = options;

  const [events, setEvents] = useState<EventLogEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilterState] = useState<EventLogFilter>(initialFilter);

  // Track event IDs to prevent duplicates
  const eventIdsRef = useRef<Set<string>>(new Set());

  const fetchEvents = useCallback(async () => {
    if (!runId) return;

    setLoading(true);
    setError(null);

    try {
      const response = await api.events.list(runId, filter);

      // Update event IDs set
      const newIds = new Set(response.map((e) => e.id));
      eventIdsRef.current = newIds;

      // Map to EventLogEntry type
      const mappedEvents: EventLogEntry[] = response.map((e) => ({
        id: e.id,
        event_type: e.event_type,
        step: e.step,
        payload: e.payload,
        details: e.details,
        created_at: e.created_at,
      }));

      setEvents(mappedEvents);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to fetch events";
      setError(message);
      console.error("Failed to fetch events:", err);
    } finally {
      setLoading(false);
    }
  }, [runId, filter]);

  const setFilter = useCallback((newFilter: EventLogFilter) => {
    setFilterState(newFilter);
  }, []);

  const mergeRealtimeEvents = useCallback((wsEvents: ProgressEvent[]) => {
    if (wsEvents.length === 0) return;

    setEvents((prev) => {
      // Convert WebSocket events to EventLogEntry format
      const newEvents: EventLogEntry[] = wsEvents
        .filter((ws) => {
          // Create a unique ID for WebSocket events
          const wsId = `ws-${ws.timestamp}-${ws.type}`;
          if (eventIdsRef.current.has(wsId)) return false;
          eventIdsRef.current.add(wsId);
          return true;
        })
        .map((ws) => ({
          id: `ws-${ws.timestamp}-${ws.type}`,
          event_type: ws.type,
          step: ws.step,
          payload: {
            message: ws.message,
            progress: ws.progress,
            status: ws.status,
            ...ws.details,
          },
          details: {
            run_id: ws.run_id,
            step: ws.step,
            attempt: ws.attempt,
          },
          created_at: ws.timestamp,
        }));

      if (newEvents.length === 0) return prev;

      // Merge and sort by timestamp (newest first)
      const merged = [...newEvents, ...prev];
      merged.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());

      return merged;
    });
  }, []);

  const clear = useCallback(() => {
    setEvents([]);
    eventIdsRef.current.clear();
  }, []);

  // Auto-fetch on mount and when filter changes
  useEffect(() => {
    if (autoFetch) {
      fetchEvents();
    }
  }, [autoFetch, fetchEvents]);

  // Polling
  useEffect(() => {
    if (pollingInterval <= 0) return;

    const intervalId = setInterval(fetchEvents, pollingInterval);
    return () => clearInterval(intervalId);
  }, [pollingInterval, fetchEvents]);

  // Reset when runId changes
  useEffect(() => {
    clear();
    if (autoFetch) {
      fetchEvents();
    }
  }, [runId]); // eslint-disable-line react-hooks/exhaustive-deps

  return {
    events,
    loading,
    error,
    filter,
    setFilter,
    fetch: fetchEvents,
    mergeRealtimeEvents,
    clear,
  };
}

import { useEffect, useRef, useState, useCallback } from 'react';
import type { AgentEvent } from '../types';

/**
 * Enhanced SSE hook connecting to /api/events with scoped routing and replay support.
 * Pass `enabled=false` to defer connection (e.g., until auth completes).
 * Token is sent as a query param since EventSource cannot set custom headers.
 * Automatically tracks lastEventId and replays missed messages upon reconnect.
 */
export function useSSE(
  onEvent: (event: AgentEvent) => void,
  enabled: boolean = true,
  token: string | null = null,
  onReconnect?: () => void,
  convId?: string | null,
) {
  const [connected, setConnected] = useState(false);
  const reconnectCountRef = useRef(0);
  const evtSourceRef = useRef<EventSource | null>(null);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const lastEventIdRef = useRef<number | null>(null);
  const onEventRef = useRef(onEvent);
  onEventRef.current = onEvent;
  const onReconnectRef = useRef(onReconnect);
  onReconnectRef.current = onReconnect;
  const wasConnectedRef = useRef(false);

  const connect = useCallback(() => {
    if (evtSourceRef.current?.readyState === EventSource.OPEN) return;

    const url = new URL('/api/events', window.location.origin);
    if (token) {
      url.searchParams.set('token', token);
    }
    if (convId) {
      url.searchParams.set('conv_id', convId);
    }
    if (lastEventIdRef.current !== null && lastEventIdRef.current >= 0) {
      url.searchParams.set('last_event_id', String(lastEventIdRef.current));
    }

    const es = new EventSource(url.toString());
    evtSourceRef.current = es;

    es.onopen = () => {
      const wasDisconnected = wasConnectedRef.current;
      setConnected(true);
      wasConnectedRef.current = true;
      reconnectCountRef.current = 0;

      // If this is a reconnection (not initial connect), trigger catch-up
      if (wasDisconnected && onReconnectRef.current) {
        onReconnectRef.current();
      }
    };

    es.onmessage = (e) => {
      if (!e.data) return;
      try {
        const event: AgentEvent = JSON.parse(e.data);
        const rawObj = event as unknown as Record<string, unknown>;
        if (e.lastEventId && !Number.isNaN(Number(e.lastEventId))) {
          lastEventIdRef.current = Number(e.lastEventId);
        } else if (rawObj && typeof rawObj.seq === 'number') {
          lastEventIdRef.current = rawObj.seq;
        }
        onEventRef.current(event);
      } catch {
        // ignore malformed payloads
      }
    };

    es.onerror = () => {
      setConnected(false);
      es.close();
      evtSourceRef.current = null;

      const count = reconnectCountRef.current;
      const delay = Math.min(1000 * Math.pow(2, count), 10000) + Math.random() * 1000;
      reconnectCountRef.current = count + 1;

      reconnectTimerRef.current = setTimeout(connect, delay);
    };
  }, [token, convId]);

  useEffect(() => {
    if (!enabled) return;

    connect();
    return () => {
      if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current);
      if (evtSourceRef.current) {
        evtSourceRef.current.close();
        evtSourceRef.current = null;
      }
    };
  }, [enabled, connect]);

  return { connected, lastEventId: lastEventIdRef.current };
}

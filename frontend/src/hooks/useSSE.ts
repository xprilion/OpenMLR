import { useEffect, useRef, useState, useCallback } from 'react';
import type { AgentEvent } from '../types';

/**
 * SSE hook that connects to /api/events.
 * Pass `enabled=false` to defer connection (e.g., until auth completes).
 * Token is sent as a query param since EventSource cannot set headers.
 * `onReconnect` is called when SSE reconnects after a disconnect.
 */
export function useSSE(
  onEvent: (event: AgentEvent) => void,
  enabled: boolean = true,
  token: string | null = null,
  onReconnect?: () => void,
) {
  const [connected, setConnected] = useState(false);
  const reconnectCountRef = useRef(0);
  const evtSourceRef = useRef<EventSource | null>(null);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
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
        onEventRef.current(event);
      } catch {
        // ignore malformed
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
  }, [token]);

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

  return { connected };
}

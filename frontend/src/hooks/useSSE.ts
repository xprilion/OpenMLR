import { useEffect, useRef, useState, useCallback } from 'react';
import type { AgentEvent } from '../types';

/**
 * SSE hook that connects to /api/events.
 * Pass `enabled=false` to defer connection (e.g., until auth completes).
 * Token is sent as a query param since EventSource cannot set headers.
 */
export function useSSE(
  onEvent: (event: AgentEvent) => void,
  enabled: boolean = true,
  token: string | null = null,
) {
  const [connected, setConnected] = useState(false);
  const reconnectCountRef = useRef(0);
  const evtSourceRef = useRef<EventSource | null>(null);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const onEventRef = useRef(onEvent);
  onEventRef.current = onEvent;

  const connect = useCallback(() => {
    if (evtSourceRef.current?.readyState === EventSource.OPEN) return;

    const url = new URL('/api/events', window.location.origin);
    if (token) {
      url.searchParams.set('token', token);
    }

    const es = new EventSource(url.toString());
    evtSourceRef.current = es;

    es.onopen = () => {
      setConnected(true);
      reconnectCountRef.current = 0;
    };

    es.onmessage = (e) => {
      if (!e.data) return;
      try {
        const event: AgentEvent = JSON.parse(e.data);
        console.log('[SSE]', event.event_type, event.data?.chunk ? '(chunk)' : JSON.stringify(event.data)?.slice(0, 80));
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

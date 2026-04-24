import { useEffect, useRef, useState, useCallback } from 'react';
import type { AgentEvent } from '../types';

export function useSSE(onEvent: (event: AgentEvent) => void) {
  const [connected, setConnected] = useState(false);
  const [reconnectCount, setReconnectCount] = useState(0);
  const evtSourceRef = useRef<EventSource | null>(null);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const lastEventIdRef = useRef<string>('');

  const connect = useCallback(() => {
    if (evtSourceRef.current?.readyState === EventSource.OPEN) return;

    const url = new URL('/api/events', window.location.origin);
    if (lastEventIdRef.current) {
      url.searchParams.set('lastEventId', lastEventIdRef.current);
    }

    const es = new EventSource(url.toString());
    evtSourceRef.current = es;

    es.onopen = () => {
      setConnected(true);
      setReconnectCount(0);
    };

    es.onmessage = (e) => {
      if (e.data.startsWith('ping')) return;
      try {
        const event: AgentEvent = JSON.parse(e.data);
        onEvent(event);
      } catch {
        // ignore malformed events
      }
    };

    es.onerror = () => {
      setConnected(false);
      es.close();
      evtSourceRef.current = null;

      // Exponential backoff with jitter, capped at 10s
      const baseDelay = Math.min(1000 * Math.pow(2, reconnectCount), 10000);
      const jitter = Math.random() * 1000;
      const delay = baseDelay + jitter;

      setReconnectCount((c) => c + 1);

      reconnectTimerRef.current = setTimeout(() => {
        connect();
      }, delay);
    };
  }, [onEvent, reconnectCount]);

  useEffect(() => {
    connect();
    return () => {
      if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current);
      evtSourceRef.current?.close();
      evtSourceRef.current = null;
    };
  }, []);

  return { connected, reconnectCount };
}

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useSSE } from '../hooks/useSSE';
import type { AgentEvent } from '../types';

const instances: any[] = [];

vi.stubGlobal('EventSource', vi.fn(function (this: any, url: string) {
  this.url = url;
  this.readyState = 0;
  this.onopen = null;
  this.onmessage = null;
  this.onerror = null;
  this.close = function () {
    this.readyState = 2;
  };
  instances.push(this);
  return this;
}));

(globalThis as any).EventSource.CONNECTING = 0;
(globalThis as any).EventSource.OPEN = 1;
(globalThis as any).EventSource.CLOSED = 2;

function newest() {
  return instances[instances.length - 1];
}

describe('useSSE', () => {
  beforeEach(() => {
    instances.length = 0;
  });

  it('creates EventSource when enabled is true', () => {
    const onEvent = vi.fn();
    renderHook(() => useSSE(onEvent, true));

    expect((globalThis as any).EventSource).toHaveBeenCalled();
    expect(instances.length).toBe(1);
    expect(instances[0].url).toContain('/api/events');
  });

  it('does not create EventSource when enabled is false', () => {
    const onEvent = vi.fn();
    renderHook(() => useSSE(onEvent, false));

    expect(instances.length).toBe(0);
  });

  it('appends token as query parameter', () => {
    const onEvent = vi.fn();
    renderHook(() => useSSE(onEvent, true, 'test-token'));

    expect(instances.length).toBe(1);
    expect(instances[0].url).toContain('token=test-token');
  });

  it('sets connected to true on open', () => {
    const onEvent = vi.fn();
    const { result } = renderHook(() => useSSE(onEvent, true));

    act(() => {
      newest().onopen(new Event('open'));
    });

    expect(result.current.connected).toBe(true);
  });

  it('calls onEvent when message received', () => {
    const onEvent = vi.fn();
    renderHook(() => useSSE(onEvent, true));

    const event: AgentEvent = { event_type: 'text_delta', data: { text: 'hello' } };
    act(() => {
      newest().onmessage(new MessageEvent('message', { data: JSON.stringify(event) }));
    });

    expect(onEvent).toHaveBeenCalledWith(event);
  });

  it('does not call onEvent for messages without data', () => {
    const onEvent = vi.fn();
    renderHook(() => useSSE(onEvent, true));

    act(() => {
      newest().onmessage(new MessageEvent('message', { data: '' }));
    });

    expect(onEvent).not.toHaveBeenCalled();
  });

  it('handles malformed JSON gracefully', () => {
    const onEvent = vi.fn();
    renderHook(() => useSSE(onEvent, true));

    act(() => {
      newest().onmessage(new MessageEvent('message', { data: 'not-json' }));
    });

    expect(onEvent).not.toHaveBeenCalled();
  });

  it('sets connected to false on error and closes connection', () => {
    vi.useFakeTimers();
    const onEvent = vi.fn();
    const { result } = renderHook(() => useSSE(onEvent, true));

    act(() => {
      newest().onopen(new Event('open'));
    });
    expect(result.current.connected).toBe(true);

    act(() => {
      newest().onerror(new Event('error'));
    });
    expect(result.current.connected).toBe(false);

    vi.useRealTimers();
  });

  it('calls onReconnect when reconnecting after disconnect', () => {
    const onEvent = vi.fn();
    const onReconnect = vi.fn();
    renderHook(() => useSSE(onEvent, true, null, onReconnect));

    act(() => {
      newest().onopen(new Event('open'));
    });
    act(() => {
      newest().onopen(new Event('open'));
    });
    expect(onReconnect).toHaveBeenCalled();
  });
});

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useJobStatus } from '../hooks/useJobStatus';
import { api } from '../api';

vi.mock('../api', () => ({
  api: {
    getConversationJobs: vi.fn(),
  },
}));

describe('useJobStatus', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.useFakeTimers({ shouldAdvanceTime: true });
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  async function flushPromises() {
    await act(async () => {
      await Promise.resolve();
    });
  }

  it('returns empty jobs when disabled', async () => {
    const { result } = renderHook(() =>
      useJobStatus({ conversationUuid: 'test-uuid', enabled: false })
    );
    expect(result.current.activeJobs).toEqual([]);
    expect(result.current.isProcessing).toBe(false);
  });

  it('returns empty jobs when conversationUuid is null', async () => {
    const { result } = renderHook(() =>
      useJobStatus({ conversationUuid: null })
    );
    expect(result.current.activeJobs).toEqual([]);
  });

  it('fetches jobs on mount', async () => {
    const mockJobs = [
      { job_id: 'job-1', status: 'queued', created_at: '2024-01-01T00:00:00Z' },
      { job_id: 'job-2', status: 'running', created_at: '2024-01-01T00:01:00Z' },
    ];
    vi.mocked(api.getConversationJobs).mockResolvedValue({ jobs: mockJobs });

    renderHook(() =>
      useJobStatus({ conversationUuid: 'test-uuid', pollInterval: 10000 })
    );

    await flushPromises();

    expect(api.getConversationJobs).toHaveBeenCalledTimes(1);
  });

  it('detects processing state for queued jobs', async () => {
    const mockJobs = [
      { job_id: 'job-1', status: 'queued', created_at: '2024-01-01T00:00:00Z' },
    ];
    vi.mocked(api.getConversationJobs).mockResolvedValue({ jobs: mockJobs });

    const { result } = renderHook(() =>
      useJobStatus({ conversationUuid: 'test-uuid', pollInterval: 10000 })
    );

    await flushPromises();

    expect(result.current.isProcessing).toBe(true);
  });

  it('detects processing state for running jobs', async () => {
    const mockJobs = [
      { job_id: 'job-1', status: 'running', created_at: '2024-01-01T00:00:00Z' },
    ];
    vi.mocked(api.getConversationJobs).mockResolvedValue({ jobs: mockJobs });

    const { result } = renderHook(() =>
      useJobStatus({ conversationUuid: 'test-uuid', pollInterval: 10000 })
    );

    await flushPromises();

    expect(result.current.isProcessing).toBe(true);
  });

  it('not processing when all jobs completed', async () => {
    const mockJobs = [
      { job_id: 'job-1', status: 'completed', created_at: '2024-01-01T00:00:00Z' },
    ];
    vi.mocked(api.getConversationJobs).mockResolvedValue({ jobs: mockJobs });

    const { result } = renderHook(() =>
      useJobStatus({ conversationUuid: 'test-uuid', pollInterval: 10000 })
    );

    await flushPromises();

    expect(result.current.isProcessing).toBe(false);
  });

  it('handles empty jobs array', async () => {
    vi.mocked(api.getConversationJobs).mockResolvedValue({ jobs: [] });

    const { result } = renderHook(() =>
      useJobStatus({ conversationUuid: 'test-uuid', pollInterval: 10000 })
    );

    await flushPromises();

    expect(result.current.activeJobs).toEqual([]);
  });

  it('handles missing jobs key', async () => {
    vi.mocked(api.getConversationJobs).mockResolvedValue({});

    const { result } = renderHook(() =>
      useJobStatus({ conversationUuid: 'test-uuid', pollInterval: 10000 })
    );

    await flushPromises();

    expect(result.current.activeJobs).toEqual([]);
  });

  it('calls onJobComplete when jobs finish', async () => {
    const onComplete = vi.fn();
    // First call: processing, Second call: completed
    vi.mocked(api.getConversationJobs)
      .mockResolvedValueOnce({ jobs: [{ job_id: 'j1', status: 'running' }] })
      .mockResolvedValueOnce({ jobs: [{ job_id: 'j1', status: 'completed' }] });

    const { result } = renderHook(() =>
      useJobStatus({ conversationUuid: 'test-uuid', pollInterval: 5000, onJobComplete: onComplete })
    );

    await flushPromises();
    expect(result.current.isProcessing).toBe(true);

    // Advance time to trigger next poll
    await act(async () => {
      vi.advanceTimersByTime(5000);
    });
    await flushPromises();

    expect(onComplete).toHaveBeenCalledWith('test-uuid');
  });

  it('tracks last job id', async () => {
    vi.mocked(api.getConversationJobs).mockResolvedValue({
      jobs: [{ job_id: 'job-last', status: 'running' }],
    });

    const { result } = renderHook(() =>
      useJobStatus({ conversationUuid: 'test-uuid', pollInterval: 10000 })
    );

    await flushPromises();

    expect(result.current.lastJobId).toBe('job-last');
  });

  it('handles fetch errors gracefully', async () => {
    vi.mocked(api.getConversationJobs).mockRejectedValue(new Error('Network error'));
    const consoleDebug = vi.spyOn(console, 'debug').mockImplementation(() => {});

    renderHook(() =>
      useJobStatus({ conversationUuid: 'test-uuid', pollInterval: 10000 })
    );

    await flushPromises();

    expect(consoleDebug).toHaveBeenCalled();
    consoleDebug.mockRestore();
  });

  it('polls at configured interval', async () => {
    vi.mocked(api.getConversationJobs).mockResolvedValue({ jobs: [] });

    renderHook(() =>
      useJobStatus({ conversationUuid: 'test-uuid', pollInterval: 5000 })
    );

    await flushPromises();
    expect(api.getConversationJobs).toHaveBeenCalledTimes(1);

    await act(async () => {
      vi.advanceTimersByTime(5000);
    });
    await flushPromises();

    expect(api.getConversationJobs).toHaveBeenCalledTimes(2);
  });

  it('refresh triggers immediate fetch', async () => {
    vi.mocked(api.getConversationJobs).mockResolvedValue({ jobs: [] });

    const { result } = renderHook(() =>
      useJobStatus({ conversationUuid: 'test-uuid', pollInterval: 10000 })
    );

    await flushPromises();
    expect(api.getConversationJobs).toHaveBeenCalledTimes(1);

    await act(async () => {
      await result.current.refresh();
    });

    expect(api.getConversationJobs).toHaveBeenCalledTimes(2);
  });
});

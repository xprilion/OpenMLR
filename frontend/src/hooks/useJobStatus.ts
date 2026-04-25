import { useState, useEffect, useCallback, useRef } from 'react';
import { api } from '../api';
import type { AgentJob } from '../types';

interface UseJobStatusOptions {
  conversationUuid: string | null;
  pollInterval?: number;  // ms
  enabled?: boolean;
}

interface UseJobStatusResult {
  activeJobs: AgentJob[];
  isProcessing: boolean;
  lastJobId: string | null;
  refresh: () => Promise<void>;
}

/**
 * Hook to track background job status for a conversation.
 * 
 * Polls the API for active jobs when enabled, providing
 * real-time status even when SSE is disconnected.
 */
export function useJobStatus({
  conversationUuid,
  pollInterval = 3000,
  enabled = true,
}: UseJobStatusOptions): UseJobStatusResult {
  const [activeJobs, setActiveJobs] = useState<AgentJob[]>([]);
  const [lastJobId, setLastJobId] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const refresh = useCallback(async () => {
    if (!conversationUuid) {
      setActiveJobs([]);
      return;
    }

    try {
      const data = await api.getConversationJobs(conversationUuid);
      setActiveJobs(data.jobs || []);
      
      // Track the most recent job
      if (data.jobs?.length > 0) {
        setLastJobId(data.jobs[0].job_id);
      }
    } catch (err) {
      // Silently fail - job status is non-critical
      console.debug('Failed to fetch job status:', err);
    }
  }, [conversationUuid]);

  useEffect(() => {
    if (!enabled || !conversationUuid) {
      if (pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
      return;
    }

    // Initial fetch
    refresh();

    // Start polling
    pollRef.current = setInterval(refresh, pollInterval);

    return () => {
      if (pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
    };
  }, [enabled, conversationUuid, pollInterval, refresh]);

  const isProcessing = activeJobs.some(
    (job) => job.status === 'queued' || job.status === 'running'
  );

  return {
    activeJobs,
    isProcessing,
    lastJobId,
    refresh,
  };
}

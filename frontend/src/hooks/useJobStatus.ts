import { useState, useEffect, useCallback, useRef } from 'react';
import { api } from '../api';
import type { AgentJob } from '../types';

interface UseJobStatusOptions {
  conversationUuid: string | null;
  pollInterval?: number;  // ms
  enabled?: boolean;
  onJobComplete?: (uuid: string) => void;  // Called when a job transitions to completed
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
 * Calls onJobComplete when a job finishes, enabling message catch-up.
 */
export function useJobStatus({
  conversationUuid,
  pollInterval = 3000,
  enabled = true,
  onJobComplete,
}: UseJobStatusOptions): UseJobStatusResult {
  const [activeJobs, setActiveJobs] = useState<AgentJob[]>([]);
  const [lastJobId, setLastJobId] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const prevProcessingRef = useRef(false);
  const onJobCompleteRef = useRef(onJobComplete);
  onJobCompleteRef.current = onJobComplete;

  const refresh = useCallback(async () => {
    if (!conversationUuid) {
      setActiveJobs([]);
      return;
    }

    try {
      const data = await api.getConversationJobs(conversationUuid);
      const jobs = data.jobs || [];
      setActiveJobs(jobs);
      
      // Track the most recent job
      if (jobs.length > 0) {
        setLastJobId(jobs[0].job_id);
      }

      // Detect job completion: was processing, now no active jobs
      const nowProcessing = jobs.some(
        (job: AgentJob) => job.status === 'queued' || job.status === 'running'
      );
      if (prevProcessingRef.current && !nowProcessing && onJobCompleteRef.current) {
        onJobCompleteRef.current(conversationUuid);
      }
      prevProcessingRef.current = nowProcessing;
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

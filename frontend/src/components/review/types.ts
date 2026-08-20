import type { PeerReviewResult, ConferenceRubric, ReviewerPersona } from '../../types';

export type ReviewTab = 'editor' | 'results' | 'rubric';

export interface PeerReviewState {
  venue: string;
  title: string;
  submissionText: string;
  isSubmitting: boolean;
  activeTab: ReviewTab;
  result: PeerReviewResult | null;
  error: string | null;
  rubrics: Record<string, ConferenceRubric>;
  personas: ReviewerPersona[];
}

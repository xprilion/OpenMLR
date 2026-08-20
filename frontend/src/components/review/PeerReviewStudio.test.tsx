import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { PeerReviewStudio } from './PeerReviewStudio';
import { api } from '../../api';

// Mock API
vi.mock('../../api', () => ({
  api: {
    getReviewRubrics: vi.fn(),
    evaluateSubmission: vi.fn(),
    reviewProjectWorkspace: vi.fn(),
  },
}));

// Mock ProjectContext
vi.mock('../../context/ProjectContext', () => ({
  useProject: () => ({
    activeProject: { id: 1, name: 'Test Research Project', slug: 'test-research' },
  }),
}));

const mockRubricsResponse = {
  rubrics: {
    iclr: {
      venue: 'iclr',
      name: 'ICLR 2026',
      description: 'International Conference on Learning Representations',
      acceptance_threshold: 6.5,
      score_range: [1, 10] as [number, number],
      criteria: [
        { name: 'novelty', weight: 0.35, description: 'Novelty of methodology' },
        { name: 'empirical_rigor', weight: 0.35, description: 'Completeness of baselines' },
      ],
    },
  },
  personas: [
    {
      id: 'reviewer_1',
      name: 'Reviewer 1 (Theory & Novelty)',
      role: 'Senior Area Chair',
      focus_areas: ['Mathematical rigor', 'Proofs'],
    },
  ],
};

const mockReviewResult = {
  submission_title: 'Adaptive Low-Rank Attention',
  venue: 'iclr',
  average_score: 8.0,
  status: 'completed',
  evaluated_at: Date.now(),
  markdown_report: '# Peer Review Evaluation\n\n**Decision: Accept**',
  meta_review: {
    decision: 'Accept (Poster)',
    decision_type: 'accept' as const,
    consensus_score: 8.2,
    confidence: 4.5,
    summary_of_consensus: 'Strong empirical validation across LLM benchmarks with sound mathematical intuition.',
    justification: 'The adaptive pruning formulation offers consistent efficiency gains.',
    key_strengths: ['Dynamic rank budget optimization', 'Comprehensive GSM8K and MMLU evaluations'],
    primary_shortcomings: ['Hardware scaling beyond 8B parameters remains unverified'],
    actionable_revision_plan: [
      'Include 70B parameter scaling experiments in appendix',
      'Add ablation on singular value pruning frequency',
    ],
  },
  reviews: [
    {
      reviewer_id: 'rev_1',
      reviewer_name: 'Reviewer 1 (Theory & Novelty)',
      role: 'Theoretical ML Specialist',
      overall_score: 8,
      confidence: 4,
      summary: 'Well-grounded formulation of low-rank gradient dynamics.',
      strengths: ['Clear mathematical formulation', 'Novel pruning metric'],
      weaknesses: ['Convergence proof assumes convex loss landscape'],
      questions_for_authors: ['How does curvature estimation behave under AdamW?'],
      detailed_comments: 'The paper is well written.',
      recommendation: 'Accept',
      criteria_scores: { novelty: 8, theoretical_rigor: 8 },
    },
    {
      reviewer_id: 'rev_2',
      reviewer_name: 'Reviewer 2 (Empirical Validation)',
      role: 'Empirical Deep Learning Specialist',
      overall_score: 8,
      confidence: 5,
      summary: 'Solid empirical results on Llama-3-8B.',
      strengths: ['Strong baseline comparisons with DoRA', 'Memory profiling included'],
      weaknesses: ['Missing FLOPs measurements during training'],
      questions_for_authors: ['What is the wall-clock overhead of SVD computations?'],
      detailed_comments: 'Empirical section is rigorous.',
      recommendation: 'Accept',
      criteria_scores: { empirical_soundness: 8 },
    },
  ],
};

describe('PeerReviewStudio', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.getReviewRubrics).mockResolvedValue(mockRubricsResponse);
  });

  it('renders initial review studio components and banner', async () => {
    render(<PeerReviewStudio />);

    expect(screen.getByText('Autonomous Peer Review Committee')).toBeInTheDocument();
    expect(screen.getByText('Venue:')).toBeInTheDocument();
    expect(screen.getByText('Run Peer Review')).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/e\.g\. Scalable FlashAttention/i)).toBeInTheDocument();
  });

  it('opens and closes rubric modal', async () => {
    render(<PeerReviewStudio />);

    const rubricBtn = screen.getByRole('button', { name: /Rubric/i });
    fireEvent.click(rubricBtn);

    await waitFor(() => {
      expect(screen.getByText(/Peer Review Rubric & Committee Specification/i)).toBeInTheDocument();
    });

    const closeBtn = screen.getByRole('button', { name: /Close/i });
    fireEvent.click(closeBtn);

    await waitFor(() => {
      expect(screen.queryByText(/Peer Review Rubric & Committee Specification/i)).not.toBeInTheDocument();
    });
  });

  it('executes peer review simulation and displays results', async () => {
    vi.mocked(api.evaluateSubmission).mockResolvedValue(mockReviewResult);

    render(<PeerReviewStudio />);

    const runBtn = screen.getByRole('button', { name: /Run Peer Review/i });
    fireEvent.click(runBtn);

    await waitFor(() => {
      expect(screen.getByText(/Final Committee Recommendation/i)).toBeInTheDocument();
      expect(screen.getByText(/ACCEPT \(Accept \(Poster\)\)/i)).toBeInTheDocument();
      expect(screen.getByText(/Strong empirical validation across LLM benchmarks/i)).toBeInTheDocument();
      expect(screen.getByText(/Reviewer 1 \(Theory & Novelty\)/i)).toBeInTheDocument();
    });
  });

  it('handles project workspace review click', async () => {
    vi.mocked(api.reviewProjectWorkspace).mockResolvedValue(mockReviewResult);

    render(<PeerReviewStudio />);

    const workspaceBtn = screen.getByRole('button', { name: /Review Workspace/i });
    fireEvent.click(workspaceBtn);

    await waitFor(() => {
      expect(api.reviewProjectWorkspace).toHaveBeenCalledWith(1, {
        venue: 'iclr',
        include_latex: true,
        include_notes: true,
      });
    });
  });
});

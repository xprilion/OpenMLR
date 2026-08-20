import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { AblationStudio } from './AblationStudio';
import { api } from '../../api';
import type { AblationStudy } from './types';

vi.mock('../../api', () => ({
  api: {
    getAblationStudies: vi.fn(),
    createAblationStudy: vi.fn(),
    recordAblationRuns: vi.fn(),
    analyzeAblationStudy: vi.fn(),
    getAblationLatex: vi.fn(),
    deleteAblationStudy: vi.fn(),
  },
}));

const mockStudy: AblationStudy = {
  id: 'study_mock_1',
  title: 'Attention & Normalization Layer Ablation',
  description: 'Testing isolated impact of RoPE and QK-norm',
  project_id: 'proj_test',
  primary_metric: 'accuracy',
  higher_is_better: true,
  baseline_variant_name: 'Full Model',
  variants: {
    'Full Model': {
      name: 'Full Model',
      variant_type: 'baseline',
      description: 'All components active',
      removed_components: [],
      added_components: [],
      metrics: {
        accuracy: {
          count: 5,
          mean: 0.948,
          std: 0.005,
          median: 0.948,
          iqr: 0.004,
          min_val: 0.942,
          max_val: 0.954,
          ci_lower: 0.944,
          ci_upper: 0.952,
        },
      },
      raw_seed_values: {
        accuracy: [0.945, 0.948, 0.952, 0.942, 0.953],
      },
      run_ids: ['run_1'],
    },
    'w/o RoPE': {
      name: 'w/o RoPE',
      variant_type: 'ablation',
      description: 'Learned absolute embeddings',
      removed_components: ['Rotary Position Embeddings'],
      added_components: [],
      metrics: {
        accuracy: {
          count: 5,
          mean: 0.881,
          std: 0.006,
          median: 0.88,
          iqr: 0.005,
          min_val: 0.875,
          max_val: 0.889,
          ci_lower: 0.876,
          ci_upper: 0.886,
        },
      },
      raw_seed_values: {
        accuracy: [0.88, 0.876, 0.885, 0.879, 0.885],
      },
      run_ids: ['run_2'],
    },
  },
  comparisons: {
    accuracy: [
      {
        variant_name: 'w/o RoPE',
        metric_name: 'accuracy',
        baseline_mean: 0.948,
        variant_mean: 0.881,
        delta_abs: -0.067,
        delta_pct: -7.07,
        t_stat: -18.85,
        p_value: 0.000012,
        p_value_adjusted: 0.000012,
        effect_size_cohen_d: -11.92,
        effect_size_hedges_g: -10.83,
        ci_diff_lower: -0.075,
        ci_diff_upper: -0.059,
        significance_symbol: '***',
        test_type: 'welch_t',
        is_statistically_significant: true,
      },
    ],
  },
  component_impacts: [
    {
      component_name: 'Rotary Position Embeddings',
      impact_score: 0.067,
      relative_drop_pct: 7.07,
      is_critical: true,
      recommendation: "Component 'Rotary Position Embeddings' is scientifically critical. Retain in final architecture.",
    },
  ],
  narrative_summary: 'Ablation Study Summary: Evaluated 2 variants against baseline Full Model.',
  created_at: '2026-08-20T12:00:00Z',
  updated_at: '2026-08-20T12:00:00Z',
};

describe('AblationStudio Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders empty state when no ablation studies exist', async () => {
    vi.mocked(api.getAblationStudies).mockResolvedValueOnce({ studies: [] });
    render(<AblationStudio projectId="proj_test" />);

    expect(screen.getByText(/Loading Ablation Studies.../i)).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByText(/No Ablation Studies Yet/i)).toBeInTheDocument();
    });
  });

  it('renders loaded ablation study with KPIs, tables, and rankings', async () => {
    vi.mocked(api.getAblationStudies).mockResolvedValueOnce({ studies: [mockStudy] });
    render(<AblationStudio projectId="proj_test" />);

    await waitFor(() => {
      expect(screen.getByText('Attention & Normalization Layer Ablation (2 variants)')).toBeInTheDocument();
      expect(screen.getAllByText('Full Model').length).toBeGreaterThanOrEqual(1);
      expect(screen.getByText('w/o RoPE')).toBeInTheDocument();
    });

    // Check significance badge
    expect(screen.getByText(/\*\*\* \(p < 0.001\)/i)).toBeInTheDocument();
    // Check component impact ranking
    expect(screen.getAllByText(/Rotary Position Embeddings/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText(/Critical \(p < 0.05\)/i)).toBeInTheDocument();
  });

  it('handles LaTeX table generation and display', async () => {
    vi.mocked(api.getAblationStudies).mockResolvedValueOnce({ studies: [mockStudy] });
    vi.mocked(api.getAblationLatex).mockResolvedValueOnce({
      latex_table: '\\begin{table}\n\\caption{Ablation Table}\n\\end{table}',
      study_id: 'study_mock_1',
    });

    render(<AblationStudio projectId="proj_test" />);
    await waitFor(() => {
      expect(screen.getByText('View LaTeX')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('View LaTeX'));
    await waitFor(() => {
      expect(screen.getByText(/Camera-Ready LaTeX Table/i)).toBeInTheDocument();
      expect(screen.getByText(/\\begin\{table\}/i)).toBeInTheDocument();
    });
  });

  it('opens and submits new ablation study modal', async () => {
    vi.mocked(api.getAblationStudies).mockResolvedValueOnce({ studies: [mockStudy] });
    vi.mocked(api.createAblationStudy).mockResolvedValueOnce({
      study: {
        ...mockStudy,
        id: 'study_new_2',
        title: 'New FeedForward Ablation',
      },
    });

    render(<AblationStudio projectId="proj_test" />);
    await waitFor(() => {
      expect(screen.getByText('New Study')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('New Study'));
    expect(screen.getByPlaceholderText(/e\.g\. Attention & Normalization Layer Ablations/i)).toBeInTheDocument();

    fireEvent.change(screen.getByPlaceholderText(/e\.g\. Attention & Normalization Layer Ablations/i), {
      target: { value: 'New FeedForward Ablation' },
    });

    fireEvent.click(screen.getByRole('button', { name: /Create Study/i }));

    await waitFor(() => {
      expect(api.createAblationStudy).toHaveBeenCalledWith(
        expect.objectContaining({
          title: 'New FeedForward Ablation',
        })
      );
    });
  });
});

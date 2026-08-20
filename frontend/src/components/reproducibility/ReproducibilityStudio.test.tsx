import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { ReproducibilityStudio } from './ReproducibilityStudio';
import { api } from '../../api';
import type { ReproducibilityAuditReport } from './types';

vi.mock('../../api', () => ({
  api: {
    listReproducibilityReports: vi.fn(),
    runReproducibilityAudit: vi.fn(),
    getDeterminismFix: vi.fn(),
    generateReproducibilityDockerfile: vi.fn(),
    generateReproducibilityAppendix: vi.fn(),
  },
}));

vi.mock('../../context/ProjectContext', () => ({
  useProject: () => ({
    activeProject: { uuid: 'proj_test_rep', name: 'OpenMLR Reproduction Test' },
  }),
}));

const mockReport: ReproducibilityAuditReport = {
  id: 'rep_12345',
  project_id: 'proj_test_rep',
  created_at: '2026-08-20T12:00:00Z',
  overall_score: 94.5,
  grade: 'A',
  venue: 'neurips',
  categories: [
    { category: 'determinism', score: 100, passed_checks: 2, total_checks: 2, status: 'pass' },
    { category: 'environment', score: 90, passed_checks: 2, total_checks: 3, status: 'pass' },
    { category: 'hardware', score: 100, passed_checks: 1, total_checks: 1, status: 'pass' },
    { category: 'dataset', score: 85, passed_checks: 1, total_checks: 1, status: 'pass' },
    { category: 'hyperparameters', score: 95, passed_checks: 1, total_checks: 1, status: 'pass' },
    { category: 'checkpoints', score: 97, passed_checks: 1, total_checks: 1, status: 'pass' },
  ],
  checklist: [
    {
      id: 'det_seed_init',
      category: 'determinism',
      title: 'Random Seed Initialization',
      description: 'RNG generator is explicitly initialized with deterministic seeds.',
      status: 'pass',
      severity: 'critical',
      details: 'Found explicit random seed calls.',
      remediation: 'set_seed(42)',
    },
    {
      id: 'env_container_recipe',
      category: 'environment',
      title: 'Containerization / Docker Recipe',
      description: 'Dockerfile is provided for isolated reproduction.',
      status: 'warn',
      severity: 'medium',
      details: 'No Dockerfile found.',
      remediation: 'Generate Dockerfile',
    },
  ],
  detected_frameworks: ['PyTorch'],
  seeds_detected: { main_seed: 42 },
  cuda_requirements: { cuda_version: '12.1' },
  dockerfile_recipe: 'FROM nvidia/cuda:12.1.0\nCMD ["python train.py"]',
  conda_recipe: 'name: openmlr-reproduce\nchannels:\n  - pytorch',
  latex_appendix: '\\section{Reproducibility Statement}\nAll experiments run on A100.',
  badge_markdown: '[![OpenMLR](https://img.shields.io/badge/reproducibility-A-green)](#)',
  badge_svg: '<svg><text>Reproducibility A</text></svg>',
};

describe('ReproducibilityStudio Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders reproducibility studio and loads audit report', async () => {
    vi.mocked(api.listReproducibilityReports).mockResolvedValue([mockReport]);

    render(<ReproducibilityStudio />);

    expect(screen.getByText('Reproducibility Studio')).toBeInTheDocument();
    await waitFor(() => {
      expect(api.listReproducibilityReports).toHaveBeenCalledWith('proj_test_rep');
      expect(screen.getByText('Random Seed Initialization')).toBeInTheDocument();
      expect(screen.getByText('Containerization / Docker Recipe')).toBeInTheDocument();
      expect(screen.getByText('95')).toBeInTheDocument();
    });
  });

  it('switches tabs to LaTeX statement, Dockerfile, and Determinism generator', async () => {
    vi.mocked(api.listReproducibilityReports).mockResolvedValue([mockReport]);
    vi.mocked(api.getDeterminismFix).mockResolvedValue({
      determinism_snippet: 'import torch\ntorch.manual_seed(42)',
    });

    render(<ReproducibilityStudio />);

    await waitFor(() => {
      expect(screen.getByText('Random Seed Initialization')).toBeInTheDocument();
    });

    // Switch to LaTeX Appendix tab
    fireEvent.click(screen.getByText('LaTeX Reproducibility Statement'));
    expect(screen.getByText(/All experiments run on A100/i)).toBeInTheDocument();

    // Switch to Dockerfile Recipe tab
    fireEvent.click(screen.getByText('Dockerfile Recipe'));
    expect(screen.getByText(/FROM nvidia\/cuda:12.1.0/i)).toBeInTheDocument();

    // Switch to environment.yml tab
    fireEvent.click(screen.getByText('environment.yml'));
    expect(screen.getByText(/name: openmlr-reproduce/i)).toBeInTheDocument();

    // Switch to Determinism Boilerplate tab
    fireEvent.click(screen.getByText('Determinism Boilerplate'));
    await waitFor(() => {
      expect(api.getDeterminismFix).toHaveBeenCalled();
    });
  });

  it('opens audit modal and runs custom audit', async () => {
    vi.mocked(api.listReproducibilityReports).mockResolvedValue([mockReport]);
    vi.mocked(api.runReproducibilityAudit).mockResolvedValue({
      ...mockReport,
      id: 'rep_custom_99',
      overall_score: 99,
      grade: 'A+',
    });

    render(<ReproducibilityStudio />);

    await waitFor(() => {
      expect(screen.getByText('Audit Codebase')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Audit Codebase'));
    expect(screen.getByText('Run Reproducibility Audit')).toBeInTheDocument();

    fireEvent.click(screen.getByText('Start Audit'));

    await waitFor(() => {
      expect(api.runReproducibilityAudit).toHaveBeenCalledWith(
        'proj_test_rep',
        expect.objectContaining({ target_path: '.', venue: 'neurips' })
      );
    });
  });
});

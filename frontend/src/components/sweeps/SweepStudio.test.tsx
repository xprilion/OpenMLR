import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { SweepStudio } from './SweepStudio';
import { api } from '../../api';
import type { SweepConfig, SweepAnalysis } from './types';

vi.mock('../../api', () => ({
  api: {
    listSweeps: vi.fn(),
    createSweep: vi.fn(),
    getSweep: vi.fn(),
    suggestTrial: vi.fn(),
    recordTrial: vi.fn(),
    checkPrune: vi.fn(),
    getSweepAnalysis: vi.fn(),
    exportSweepReport: vi.fn(),
    deleteSweep: vi.fn(),
  },
}));

const mockSweep: SweepConfig = {
  sweep_id: 'swp_test123',
  project_id: 'proj_1',
  name: 'Learning Rate & Optimizer Sweep',
  description: 'Hyperparameter tuning for NanoGPT',
  method: 'bayesian',
  objective_metric: 'val_loss',
  goal: 'minimize',
  max_trials: 10,
  parameters: {
    lr: { name: 'lr', param_type: 'loguniform', min_val: 0.0001, max_val: 0.01 },
    optimizer: { name: 'optimizer', param_type: 'choice', choices: ['adamw', 'sgd'] },
  },
  early_stopping: { enabled: true, min_steps: 3, reduction_factor: 2.0 },
  trials: [
    {
      trial_id: 'tr_001',
      sweep_id: 'swp_test123',
      trial_number: 1,
      parameters: { lr: 0.001, optimizer: 'adamw' },
      status: 'completed',
      metrics: { val_loss: 0.28 },
      objective_value: 0.28,
      started_at: 1000,
      completed_at: 1050,
      duration_seconds: 50.0,
    },
    {
      trial_id: 'tr_002',
      sweep_id: 'swp_test123',
      trial_number: 2,
      parameters: { lr: 0.005, optimizer: 'sgd' },
      status: 'completed',
      metrics: { val_loss: 0.42 },
      objective_value: 0.42,
      started_at: 1060,
      completed_at: 1110,
      duration_seconds: 50.0,
    },
  ],
  status: 'active',
  created_at: 1000,
  updated_at: 1110,
};

const mockAnalysis: SweepAnalysis = {
  sweep_id: 'swp_test123',
  status: 'active',
  total_trials: 2,
  completed_trials: 2,
  best_trial: mockSweep.trials[0],
  best_parameters: { lr: 0.001, optimizer: 'adamw' },
  best_metric_value: 0.28,
  parameter_importance: { lr: 0.75, optimizer: 0.25 },
  correlations: { lr: 0.65, optimizer: -0.2 },
  pareto_frontier: [mockSweep.trials[0]],
};

describe('SweepStudio Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (api.listSweeps as any).mockResolvedValue({ total: 1, sweeps: [mockSweep] });
    (api.getSweep as any).mockResolvedValue({ sweep: mockSweep });
    (api.getSweepAnalysis as any).mockResolvedValue({ analysis: mockAnalysis });
  });

  it('renders Sweep Studio header and loaded sweep overview', async () => {
    render(<SweepStudio projectId="proj_1" />);

    expect(screen.getByText('Hyperparameter Optimization Studio')).toBeInTheDocument();

    await waitFor(() => {
      expect(api.listSweeps).toHaveBeenCalledWith('proj_1');
      expect(api.getSweep).toHaveBeenCalledWith('proj_1', 'swp_test123');
    });

    expect(screen.getByText('Learning Rate & Optimizer Sweep (BAYESIAN)')).toBeInTheDocument();
    expect(screen.getByText('2 / 10 completed')).toBeInTheDocument();
    expect(screen.getAllByText('0.2800').length).toBeGreaterThanOrEqual(1);
  });

  it('renders trials table with completed trials and metrics', async () => {
    render(<SweepStudio projectId="proj_1" />);

    await waitFor(() => {
      expect(screen.getByText('#1 (tr_001)')).toBeInTheDocument();
      expect(screen.getByText('#2 (tr_002)')).toBeInTheDocument();
    });

    // Check parameter display
    expect(screen.getAllByText('lr').length).toBeGreaterThan(0);
    expect(screen.getAllByText('optimizer').length).toBeGreaterThan(0);
  });

  it('switches to Parallel Coordinates tab', async () => {
    render(<SweepStudio projectId="proj_1" />);

    await waitFor(() => {
      expect(screen.getByText(/Parallel Coordinates/i)).toBeInTheDocument();
    });

    const parallelTab = screen.getByRole('button', { name: /Parallel Coordinates/i });
    fireEvent.click(parallelTab);

    expect(screen.getByText('Hyperparameter Parallel Coordinates')).toBeInTheDocument();
    expect(screen.getByText('2 completed trials plotted')).toBeInTheDocument();
  });

  it('switches to Sensitivity & Pareto Analysis tab', async () => {
    render(<SweepStudio projectId="proj_1" />);

    await waitFor(() => {
      expect(screen.getByText(/Sensitivity & Pareto Analysis/i)).toBeInTheDocument();
    });

    const analysisTab = screen.getByRole('button', { name: /Sensitivity & Pareto Analysis/i });
    fireEvent.click(analysisTab);

    expect(screen.getByText('Optimal Configuration')).toBeInTheDocument();
    expect(screen.getByText('Parameter Sensitivity & Importance')).toBeInTheDocument();
    expect(screen.getByText('Pareto Non-Dominated Frontier (Metric vs Runtime Trade-Offs)')).toBeInTheDocument();
  });

  it('opens and submits New Sweep Modal', async () => {
    (api.createSweep as any).mockResolvedValue({
      sweep: { ...mockSweep, sweep_id: 'swp_new456', name: 'New Vision Sweep' },
    });

    render(<SweepStudio projectId="proj_1" />);

    await waitFor(() => {
      expect(screen.getByText('New Sweep')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('New Sweep'));

    expect(screen.getByText('Create Hyperparameter Sweep')).toBeInTheDocument();

    const nameInput = screen.getByPlaceholderText('e.g. BERT Attention & LR Sweep');
    fireEvent.change(nameInput, { target: { value: 'New Vision Sweep' } });

    const submitBtn = screen.getByRole('button', { name: 'Create Sweep' });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(api.createSweep).toHaveBeenCalled();
    });
  });

  it('calls suggestTrial when clicking Suggest Next Trial', async () => {
    (api.suggestTrial as any).mockResolvedValue({
      trial: {
        trial_id: 'tr_003',
        sweep_id: 'swp_test123',
        trial_number: 3,
        parameters: { lr: 0.002, optimizer: 'adamw' },
        status: 'running',
      },
    });

    render(<SweepStudio projectId="proj_1" />);

    await waitFor(() => {
      expect(screen.getByText('Suggest Next Trial')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Suggest Next Trial'));

    await waitFor(() => {
      expect(api.suggestTrial).toHaveBeenCalledWith('proj_1', 'swp_test123');
    });
  });
});

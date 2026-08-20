import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { EvalBenchmarkDashboard } from './EvalBenchmarkDashboard';
import { api } from '../../api';

vi.mock('../../api', () => ({
  api: {
    listEvalSuites: vi.fn(),
    listEvalTasks: vi.fn(),
    runEvalSuite: vi.fn(),
    registerCustomReproductionTask: vi.fn(),
    registerCustomOptimizationTask: vi.fn(),
  },
}));

const mockSuites = {
  suites: [
    {
      id: 'full',
      name: 'Full OpenMLR Benchmark Suite',
      description: 'Comprehensive research suite',
      version: '1.0.0',
      tasks: ['repro-nano-gpt', 'opt-flash-attn', 'hypo-cifar100'],
    },
    {
      id: 'reproduction',
      name: 'Standard Reproduction Suite',
      description: 'Paper reproduction tasks',
      version: '1.0.0',
      tasks: ['repro-nano-gpt'],
    },
  ],
};

const mockTasks = {
  tasks: [
    {
      task_id: 'repro-nano-gpt',
      name: 'NanoGPT Reproduction',
      description: 'Train nanoGPT on Shakespeare and reach target loss.',
      category: 'reproduction' as const,
      difficulty: 'easy' as const,
      timeout_seconds: 300,
      paper_title: 'Attention Is All You Need',
      target_metrics: { val_loss: 1.45 },
    },
    {
      task_id: 'opt-flash-attn',
      name: 'FlashAttention Triton Kernel',
      description: 'Optimize fused attention kernel in Triton.',
      category: 'optimization' as const,
      difficulty: 'hard' as const,
      timeout_seconds: 600,
      kernel_name: 'fused_attention',
      framework: 'triton',
      baseline_latency_ms: 12.4,
      target_speedup: 1.8,
    },
    {
      task_id: 'hypo-cifar100',
      name: 'CIFAR-100 Novel Augmentation',
      description: 'Formulate and validate novel data augmentation hypothesis.',
      category: 'hypothesis' as const,
      difficulty: 'medium' as const,
      timeout_seconds: 400,
      dataset_name: 'cifar100',
    },
  ],
};

const mockRunResult = {
  suite_name: 'full',
  total_tasks: 3,
  passed_tasks: 3,
  failed_tasks: 0,
  pass_rate: 1.0,
  average_score: 0.94,
  execution_time_seconds: 4.82,
  results: [
    {
      task_id: 'repro-nano-gpt',
      task_name: 'NanoGPT Reproduction',
      category: 'reproduction',
      passed: true,
      score: 0.95,
      execution_time_seconds: 1.2,
      metrics: [
        {
          metric_name: 'val_loss',
          target_value: 1.45,
          achieved_value: 1.42,
          passed: true,
          relative_error: 0.02,
          tolerance: 0.05,
        },
      ],
    },
    {
      task_id: 'opt-flash-attn',
      task_name: 'FlashAttention Triton Kernel',
      category: 'optimization',
      passed: true,
      score: 0.93,
      execution_time_seconds: 2.1,
      metrics: [
        {
          metric_name: 'speedup',
          target_value: 1.8,
          achieved_value: 1.92,
          passed: true,
          relative_error: 0.06,
          tolerance: 0.05,
        },
      ],
    },
  ],
};

describe('EvalBenchmarkDashboard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.listEvalSuites).mockResolvedValue(mockSuites);
    vi.mocked(api.listEvalTasks).mockResolvedValue(mockTasks);
  });

  it('renders benchmark dashboard, suite selector, and tasks', async () => {
    render(<EvalBenchmarkDashboard />);

    expect(screen.getByText('ML Research Agent Evaluation Harness')).toBeInTheDocument();
    expect(screen.getByText('Execute Benchmark Suite')).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText('NanoGPT Reproduction')).toBeInTheDocument();
      expect(screen.getByText('FlashAttention Triton Kernel')).toBeInTheDocument();
      expect(screen.getByText('CIFAR-100 Novel Augmentation')).toBeInTheDocument();
    });
  });

  it('filters tasks by category tabs', async () => {
    render(<EvalBenchmarkDashboard />);

    await waitFor(() => {
      expect(screen.getByText('NanoGPT Reproduction')).toBeInTheDocument();
    });

    const optFilterBtn = screen.getByRole('button', { name: /^optimization$/i });
    fireEvent.click(optFilterBtn);

    expect(screen.getByText('FlashAttention Triton Kernel')).toBeInTheDocument();
    expect(screen.queryByText('NanoGPT Reproduction')).not.toBeInTheDocument();
    expect(screen.queryByText('CIFAR-100 Novel Augmentation')).not.toBeInTheDocument();
  });

  it('opens and closes custom task modal', async () => {
    render(<EvalBenchmarkDashboard />);

    const addBtn = screen.getByRole('button', { name: /Add Custom Task/i });
    fireEvent.click(addBtn);

    await waitFor(() => {
      expect(screen.getByText('Register Custom Benchmark Task')).toBeInTheDocument();
    });

    const cancelBtn = screen.getByRole('button', { name: /Cancel/i });
    fireEvent.click(cancelBtn);

    await waitFor(() => {
      expect(screen.queryByText('Register Custom Benchmark Task')).not.toBeInTheDocument();
    });
  });

  it('executes benchmark suite and displays summary cards', async () => {
    vi.mocked(api.runEvalSuite).mockResolvedValue(mockRunResult);

    render(<EvalBenchmarkDashboard />);

    const runBtn = screen.getByRole('button', { name: /Execute Benchmark Suite/i });
    fireEvent.click(runBtn);

    await waitFor(() => {
      expect(screen.getByText('Harness Evaluation Summary')).toBeInTheDocument();
      expect(screen.getByText('94.0%')).toBeInTheDocument();
      expect(screen.getByText('100% (3/3)')).toBeInTheDocument();
      expect(screen.getByText('Task Execution Breakdown (2)')).toBeInTheDocument();
    });
  });
});

import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { ResearchWorkflowStudio } from './ResearchWorkflowStudio';
import { api } from '../../api';

// Mock API
vi.mock('../../api', () => ({
  api: {
    getProjectResearchState: vi.fn(),
    startProjectResearch: vi.fn(),
    transitionProjectResearchPhase: vi.fn(),
    createResearchMilestone: vi.fn(),
    updateResearchMilestone: vi.fn(),
    addResearchArtifact: vi.fn(),
  },
}));

// Mock ProjectContext
vi.mock('../../context/ProjectContext', () => ({
  useProject: () => ({
    activeProject: { id: 1, name: 'FlashAttention-3 Optimization', slug: 'flashattention3-opt' },
  }),
}));

const mockResearchStateResponse = {
  project_id: 1,
  project_name: 'FlashAttention-3 Optimization',
  guidelines: 'Phase: RECONNAISSANCE. Conduct broad literature searches across arXiv and OpenAlex.',
  context_prompt: '### Research Harness State\nGoal: Profile and accelerate attention kernels',
  state: {
    goal: 'Profile and accelerate attention kernels',
    current_phase: 'reconnaissance' as const,
    created_at: 1700000000,
    updated_at: 1700001000,
    history: [
      {
        from_phase: 'idle' as const,
        to_phase: 'reconnaissance' as const,
        reason: 'Initiating research project',
        timestamp: 1700000000,
        artifacts_produced: [],
      },
    ],
    milestones: [
      {
        milestone_id: 'm_1',
        phase: 'reconnaissance' as const,
        title: 'Literature Reconnaissance',
        description: 'Survey 10 top papers on attention kernels',
        status: 'pending' as const,
        criteria: ['Identify 5 foundational papers', 'Map benchmark FLOPs'],
        output_artifacts: ['papers_survey.json'],
        created_at: 1700000000,
        completed_at: null,
      },
      {
        milestone_id: 'm_2',
        phase: 'hypothesis' as const,
        title: 'Hypothesis Formulation',
        description: 'Specify modified tile size and memory layout',
        status: 'pending' as const,
        criteria: ['Define falsifiable hypothesis'],
        output_artifacts: [],
        created_at: 1700000000,
        completed_at: null,
      },
    ],
    artifacts: {
      papers: [
        { id: '2307.08691', title: 'FlashAttention-2: Faster Attention with Better Parallelism', authors: ['Tri Dao'] },
      ],
      hypotheses: [
        { claim: 'Asynchronous tile prefetching reduces memory stalls by >15%' },
      ],
      experiments: [
        { id: 'exp_001', status: 'completed', kernel: 'flash_attn_v3_tile64' },
      ],
      metrics: {
        tflops: 340.5,
        speedup: 1.42,
      },
      manuscript_sections: {
        abstract: 'We present a tile-level prefetching strategy for attention...',
      },
      bibtex_entries: [
        '@article{dao2023flashattention2, title={FlashAttention-2}}',
      ],
    },
  },
};

describe('ResearchWorkflowStudio', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.getProjectResearchState).mockResolvedValue(mockResearchStateResponse);
  });

  it('renders research workflow studio with goal, project name, and active phase', async () => {
    render(<ResearchWorkflowStudio />);

    expect(screen.getByText(/Research Workflow Studio/i)).toBeInTheDocument();
    expect(screen.getByText('FlashAttention-3 Optimization')).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText(/Goal: Profile and accelerate attention kernels/i)).toBeInTheDocument();
    });

    expect(screen.getByText('1. Reconnaissance')).toBeInTheDocument();
    expect(screen.getByText('2. Hypothesis')).toBeInTheDocument();
    expect(screen.getByText('3. Experimentation')).toBeInTheDocument();
  });

  it('displays phase guidelines and execution objectives', async () => {
    render(<ResearchWorkflowStudio />);

    await waitFor(() => {
      expect(screen.getByText(/Phase Guidelines & Execution Objectives/i)).toBeInTheDocument();
    });

    expect(screen.getByText(/Conduct broad literature searches/i)).toBeInTheDocument();
  });

  it('renders research milestones checklist and handles milestone status update', async () => {
    vi.mocked(api.updateResearchMilestone).mockResolvedValue({ status: 'updated' });

    render(<ResearchWorkflowStudio />);

    await waitFor(() => {
      expect(screen.getByText('Literature Reconnaissance')).toBeInTheDocument();
      expect(screen.getByText('Hypothesis Formulation')).toBeInTheDocument();
    });

    expect(screen.getByText('Survey 10 top papers on attention kernels')).toBeInTheDocument();
    expect(screen.getByText('Identify 5 foundational papers')).toBeInTheDocument();

    // Click checkbox to complete milestone
    const checkButtons = screen.getAllByTitle(/Mark as completed/i);
    fireEvent.click(checkButtons[0]);

    await waitFor(() => {
      expect(api.updateResearchMilestone).toHaveBeenCalledWith(1, 'm_1', { status: 'completed' });
    });
  });

  it('renders cataloged artifacts tabs: papers, hypotheses, metrics, draft sections, bibtex', async () => {
    render(<ResearchWorkflowStudio />);

    await waitFor(() => {
      expect(screen.getByText('Cataloged Research Artifacts')).toBeInTheDocument();
    });

    // Default Papers tab
    expect(screen.getByText(/FlashAttention-2: Faster Attention with Better Parallelism/i)).toBeInTheDocument();
    expect(screen.getByText(/Tri Dao/i)).toBeInTheDocument();

    // Switch to Hypotheses tab
    const hypothesesTab = screen.getByRole('button', { name: /Hypotheses/i });
    fireEvent.click(hypothesesTab);
    expect(screen.getByText(/Asynchronous tile prefetching reduces memory stalls by >15%/i)).toBeInTheDocument();

    // Switch to Metrics tab
    const metricsTab = screen.getByRole('button', { name: /Metrics/i });
    fireEvent.click(metricsTab);
    expect(screen.getByText(/tflops/i)).toBeInTheDocument();
    expect(screen.getByText('340.5000')).toBeInTheDocument();

    // Switch to Draft Sections tab
    const draftTab = screen.getByRole('button', { name: /Draft Sections/i });
    fireEvent.click(draftTab);
    expect(screen.getByText('Section: abstract')).toBeInTheDocument();
    expect(screen.getByText(/We present a tile-level prefetching strategy/i)).toBeInTheDocument();

    // Switch to BibTeX tab
    const bibtexTab = screen.getByRole('button', { name: /BibTeX/i });
    fireEvent.click(bibtexTab);
    expect(screen.getByText(/@article{dao2023flashattention2/i)).toBeInTheDocument();
  });

  it('opens advance phase modal and submits transition', async () => {
    vi.mocked(api.transitionProjectResearchPhase).mockResolvedValue({ status: 'transitioned' });

    render(<ResearchWorkflowStudio />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Advance to hypothesis/i })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: /Advance to hypothesis/i }));

    expect(screen.getByText(/Advance to hypothesis Phase/i)).toBeInTheDocument();
    const reasonInput = screen.getByPlaceholderText(/Completed literature survey with 10 benchmarked papers/i);
    fireEvent.change(reasonInput, { target: { value: 'Discovered core memory bottleneck in baseline' } });

    fireEvent.click(screen.getByRole('button', { name: /Confirm Transition/i }));

    await waitFor(() => {
      expect(api.transitionProjectResearchPhase).toHaveBeenCalledWith(1, {
        next_phase: 'hypothesis',
        reason: 'Discovered core memory bottleneck in baseline',
      });
    });
  });

  it('opens add milestone modal and submits new milestone', async () => {
    vi.mocked(api.createResearchMilestone).mockResolvedValue({ status: 'created' });

    render(<ResearchWorkflowStudio />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Add Milestone/i })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: /Add Milestone/i }));

    const titleInput = screen.getByPlaceholderText(/Profile kernel FLOPs vs baseline/i);
    const descInput = screen.getByPlaceholderText(/Measure latency under batch size 32/i);

    fireEvent.change(titleInput, { target: { value: 'Implement PyTorch Triton benchmark' } });
    fireEvent.change(descInput, { target: { value: 'Benchmark forward + backward pass on H100' } });

    fireEvent.click(screen.getByRole('button', { name: /Save Milestone/i }));

    await waitFor(() => {
      expect(api.createResearchMilestone).toHaveBeenCalledWith(1, {
        title: 'Implement PyTorch Triton benchmark',
        description: 'Benchmark forward + backward pass on H100',
        phase: 'reconnaissance',
      });
    });
  });
});

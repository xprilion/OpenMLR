import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { ModelStudio } from './ModelStudio';
import { api } from '../../api';
import type { ModelArtifact } from './types';

vi.mock('../../api', () => ({
  api: {
    listRegisteredModels: vi.fn(),
    registerModel: vi.fn(),
    getRegisteredModel: vi.fn(),
    updateRegisteredModel: vi.fn(),
    deleteRegisteredModel: vi.fn(),
    generateModelCard: vi.fn(),
    planModelQuantization: vi.fn(),
    inspectCheckpoint: vi.fn(),
    compareRegisteredModels: vi.fn(),
  },
}));

vi.mock('../../context/ProjectContext', () => ({
  useProject: () => ({
    activeProject: { uuid: 'proj_test', name: 'Test Research Project' },
  }),
}));

const mockModel: ModelArtifact = {
  id: 'model_abc123',
  project_id: 'proj_test',
  name: 'LLaMA-3-8B-OpenMLR',
  version: '1.0.0',
  architecture: 'Transformer',
  framework: 'safetensors',
  task_type: 'causal_lm',
  status: 'evaluated',
  created_at: '2026-08-20T12:00:00Z',
  updated_at: '2026-08-20T12:00:00Z',
  description: 'Ablation fine-tuned model checkpoint',
  parameters_count: 8_000_000_000,
  model_size_mb: 16000.0,
  checkpoint_path: '/checkpoints/llama3.safetensors',
  tags: ['research', 'nlp'],
  metrics: { val_loss: 1.12, accuracy: 0.88 },
  hyperparameters: { lr: 0.0002 },
  lineage: {},
  metadata: {},
};

describe('ModelStudio Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders studio title and loads models', async () => {
    vi.mocked(api.listRegisteredModels).mockResolvedValue({ models: [mockModel], total_count: 1 });

    render(<ModelStudio />);

    expect(screen.getByText('Model Registry & Governance Studio')).toBeInTheDocument();
    await waitFor(() => {
      expect(api.listRegisteredModels).toHaveBeenCalled();
      const elements = screen.getAllByText('LLaMA-3-8B-OpenMLR');
      expect(elements.length).toBeGreaterThan(0);
    });
  });

  it('opens register model modal and submits', async () => {
    vi.mocked(api.listRegisteredModels).mockResolvedValue({ models: [], total_count: 0 });
    vi.mocked(api.registerModel).mockResolvedValue({ model: mockModel });

    render(<ModelStudio />);

    const regBtns = screen.getAllByRole('button', { name: /Register Model/i });
    fireEvent.click(regBtns[0]);

    expect(screen.getByText('Register Model Artifact')).toBeInTheDocument();

    const nameInput = screen.getByPlaceholderText(/e\.g\. LLaMA-3-8B-LoRA-Ablation/i);
    fireEvent.change(nameInput, { target: { value: 'New-BERT-Model' } });

    const submitBtns = screen.getAllByRole('button', { name: /Register Model/i });
    fireEvent.click(submitBtns[submitBtns.length - 1]);

    await waitFor(() => {
      expect(api.registerModel).toHaveBeenCalled();
    });
  });

  it('triggers model card generation modal', async () => {
    vi.mocked(api.listRegisteredModels).mockResolvedValue({ models: [mockModel], total_count: 1 });
    vi.mocked(api.generateModelCard).mockResolvedValue({
      model_name: 'LLaMA-3-8B-OpenMLR',
      version: '1.0.0',
      markdown: '# Model Card LLaMA-3',
      latex: '\\begin{table}',
      bibtex: '@misc{llama3}',
      co2_emissions_kg: 1.45,
      summary: { parameters: 8000000000, size_mb: 16000, architecture: 'Transformer', framework: 'safetensors', co2_kg: 1.45 },
    });

    render(<ModelStudio />);

    await waitFor(() => {
      const elements = screen.getAllByText('LLaMA-3-8B-OpenMLR');
      expect(elements.length).toBeGreaterThan(0);
    });

    const cardBtn = screen.getByRole('button', { name: /Model Card/i });
    fireEvent.click(cardBtn);

    await waitFor(() => {
      expect(api.generateModelCard).toHaveBeenCalledWith('proj_test', 'model_abc123', expect.any(Object));
      expect(screen.getByText(/Model Card & Documentation/i)).toBeInTheDocument();
    });
  });

  it('triggers checkpoint inspection', async () => {
    vi.mocked(api.listRegisteredModels).mockResolvedValue({ models: [mockModel], total_count: 1 });
    vi.mocked(api.inspectCheckpoint).mockResolvedValue({
      file_format: 'safetensors',
      total_parameters: 8000000000,
      trainable_parameters: 8000000000,
      total_size_mb: 16000,
      estimated_vram_fp32_mb: 36000,
      estimated_vram_fp16_mb: 18000,
      estimated_vram_int8_mb: 9000,
      estimated_vram_int4_mb: 4500,
      dtype_breakdown: {},
      layers_count: 32,
      top_layers: [],
      has_optimizer_state: false,
      metadata: {},
    });

    render(<ModelStudio />);

    await waitFor(() => {
      const elements = screen.getAllByText('LLaMA-3-8B-OpenMLR');
      expect(elements.length).toBeGreaterThan(0);
    });

    const inspectBtn = screen.getByRole('button', { name: /Inspect/i });
    fireEvent.click(inspectBtn);

    await waitFor(() => {
      expect(api.inspectCheckpoint).toHaveBeenCalled();
      expect(screen.getByText('Checkpoint Architecture & VRAM Inspection')).toBeInTheDocument();
    });
  });

  it('triggers quantization planning', async () => {
    vi.mocked(api.listRegisteredModels).mockResolvedValue({ models: [mockModel], total_count: 1 });
    vi.mocked(api.planModelQuantization).mockResolvedValue({
      model_id: 'model_abc123',
      estimates: [
        {
          target_precision: 'INT4',
          estimated_size_mb: 2200,
          estimated_vram_mb: 2600,
          compression_ratio: 7.3,
          expected_latency_speedup: 3.2,
          suggested_engine: 'AutoAWQ',
          loss_tolerance_level: 'Low',
        },
      ],
    });

    render(<ModelStudio />);

    await waitFor(() => {
      const elements = screen.getAllByText('LLaMA-3-8B-OpenMLR');
      expect(elements.length).toBeGreaterThan(0);
    });

    const quantBtn = screen.getByRole('button', { name: /Quantize/i });
    fireEvent.click(quantBtn);

    await waitFor(() => {
      expect(api.planModelQuantization).toHaveBeenCalled();
      expect(screen.getByText(/Quantization & Compression Matrix/i)).toBeInTheDocument();
    });
  });
});

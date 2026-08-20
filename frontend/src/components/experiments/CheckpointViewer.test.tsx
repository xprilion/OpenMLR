import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { CheckpointViewer } from './CheckpointViewer';
import { INITIAL_MOCK_RUNS } from './mockData';

describe('CheckpointViewer', () => {
  const sampleRun = INITIAL_MOCK_RUNS[0];

  it('renders checkpoints list and counts', () => {
    render(<CheckpointViewer run={sampleRun} />);
    expect(screen.getByText('Saved Checkpoints & Weights')).toBeInTheDocument();
    expect(screen.getByText('2 saved')).toBeInTheDocument();
    expect(screen.getByText('step_200.safetensors')).toBeInTheDocument();
    expect(screen.getByText('best_val_loss_step_400.safetensors')).toBeInTheDocument();
    expect(screen.getByText('BEST')).toBeInTheDocument();
  });

  it('filters checkpoints via search input', () => {
    render(<CheckpointViewer run={sampleRun} />);
    const searchInput = screen.getByPlaceholderText('Search checkpoints...');
    fireEvent.change(searchInput, { target: { value: 'step_200' } });
    expect(screen.getByText('step_200.safetensors')).toBeInTheDocument();
    expect(screen.queryByText('best_val_loss_step_400.safetensors')).not.toBeInTheDocument();
  });

  it('toggles inspection view and model card', () => {
    render(<CheckpointViewer run={sampleRun} />);
    const inspectBtns = screen.getAllByRole('button', { name: /Inspect/i });
    fireEvent.click(inspectBtns[0]);

    expect(screen.getByText(/Checkpoint Tensor Structure & Metadata:/i)).toBeInTheDocument();
    expect(screen.getByText('Simulated Parameter Hierarchy')).toBeInTheDocument();
    expect(screen.getByText('124.4M')).toBeInTheDocument();

    // Toggle Model Card
    const modelCardBtn = screen.getByRole('button', { name: /View Model Card/i });
    fireEvent.click(modelCardBtn);
    expect(screen.getByRole('button', { name: /Hide Model Card/i })).toBeInTheDocument();
  });

  it('calls onSetBest and onDeploy callbacks', () => {
    const onSetBest = vi.fn();
    const onDeploy = vi.fn();
    render(<CheckpointViewer run={sampleRun} onSetBest={onSetBest} onDeploy={onDeploy} />);

    // Click set as best
    const setBestBtn = screen.getByTitle('Set as Best Checkpoint');
    fireEvent.click(setBestBtn);
    expect(onSetBest).toHaveBeenCalledWith('ckpt-01');

    // Click deploy
    const deployBtns = screen.getAllByTitle('Deploy Checkpoint to Inference Engine');
    fireEvent.click(deployBtns[0]);
    expect(onDeploy).toHaveBeenCalled();
  });
});

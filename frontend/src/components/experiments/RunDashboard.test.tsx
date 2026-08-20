import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { RunDashboard } from './RunDashboard';

describe('RunDashboard', () => {
  it('renders experiment runs sidebar and default selected run', () => {
    render(<RunDashboard />);
    expect(screen.getByText('Experiment Runs')).toBeInTheDocument();
    expect(screen.getAllByText('nanoGPT-124M + FlashAttention-2').length).toBeGreaterThan(0);
    expect(screen.getByText('nanoGPT-124M Standard Baseline')).toBeInTheDocument();
  });

  it('switches between tab views: Metrics, Hardware, Checkpoints, Hyperparameters, Logs', () => {
    render(<RunDashboard />);
    // Default metrics tab
    expect(screen.getByText('Training & Validation Loss')).toBeInTheDocument();

    // Hardware telemetry tab
    fireEvent.click(screen.getByRole('button', { name: /GPU & Hardware Telemetry/i }));
    expect(screen.getByText('GPU Utilization')).toBeInTheDocument();
    expect(screen.getByText('VRAM Usage')).toBeInTheDocument();
    expect(screen.getByText('GPU Temp')).toBeInTheDocument();

    // Checkpoints tab
    fireEvent.click(screen.getByRole('button', { name: /Checkpoints & Weights/i }));
    expect(screen.getByText('Saved Checkpoints & Weights')).toBeInTheDocument();

    // Config / Hyperparameters tab
    fireEvent.click(screen.getByRole('button', { name: /Hyperparameters/i }));
    expect(screen.getByText('Experiment Configuration & Environment')).toBeInTheDocument();

    // Console logs tab
    fireEvent.click(screen.getByRole('button', { name: /Console Logs/i }));
    expect(screen.getByText(/Initializing distributed training/i)).toBeInTheDocument();
  });

  it('launches a new experiment trial', () => {
    render(<RunDashboard />);
    const newRunBtn = screen.getByRole('button', { name: /New Run/i });
    fireEvent.click(newRunBtn);

    expect(screen.getAllByText('Experiment Trial #3').length).toBeGreaterThan(0);
  });

  it('filters runs by search query and status', () => {
    render(<RunDashboard />);
    const searchInput = screen.getByPlaceholderText('Filter runs & tags...');
    fireEvent.change(searchInput, { target: { value: 'Baseline' } });

    // The baseline appears in sidebar and still selectable
    expect(screen.getByText('nanoGPT-124M Standard Baseline')).toBeInTheDocument();

    fireEvent.change(searchInput, { target: { value: '' } });
    const completedFilter = screen.getByRole('button', { name: 'completed' });
    fireEvent.click(completedFilter);

    expect(screen.getByText('nanoGPT-124M Standard Baseline')).toBeInTheDocument();
  });

  it('supports multi-run comparison mode', () => {
    render(<RunDashboard />);
    const checkboxes = screen.getAllByRole('checkbox');
    // Check both runs
    fireEvent.click(checkboxes[0]);
    fireEvent.click(checkboxes[1]);

    const compareBtn = screen.getByRole('button', { name: /Compare \(2\)/i });
    expect(compareBtn).toBeInTheDocument();
    fireEvent.click(compareBtn);

    expect(screen.getByText(/Comparing 2 Experiment Runs/i)).toBeInTheDocument();
    expect(screen.getByText('Hyperparameters & Scores Matrix')).toBeInTheDocument();
    expect(screen.getByText('Multi-Run Training Loss Comparison')).toBeInTheDocument();

    // Back to single run
    fireEvent.click(screen.getByRole('button', { name: /Back to Single Run/i }));
    expect(screen.queryByText(/Comparing 2 Experiment Runs/i)).not.toBeInTheDocument();
  });

  it('allows pausing and resuming runs', () => {
    render(<RunDashboard />);
    const pauseBtn = screen.getByRole('button', { name: /Pause/i });
    fireEvent.click(pauseBtn);

    expect(screen.getByRole('button', { name: /Resume/i })).toBeInTheDocument();
  });
});

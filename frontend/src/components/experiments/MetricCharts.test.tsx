import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MetricCharts } from './MetricCharts';
import type { MetricSeries } from './types';

describe('MetricCharts', () => {
  const sampleSeries: MetricSeries[] = [
    {
      id: 'train_loss',
      name: 'Train Loss',
      color: '#1288ff',
      data: [
        { step: 1, epoch: 1, timestamp: 100000, value: 4.5 },
        { step: 2, epoch: 1, timestamp: 200000, value: 3.8 },
        { step: 3, epoch: 1, timestamp: 300000, value: 3.2 },
        { step: 4, epoch: 1, timestamp: 400000, value: 2.9 },
      ],
    },
    {
      id: 'val_loss',
      name: 'Val Loss',
      color: '#10b981',
      data: [
        { step: 2, epoch: 1, timestamp: 200000, value: 3.9 },
        { step: 4, epoch: 1, timestamp: 400000, value: 3.1 },
      ],
    },
  ];

  it('renders chart title and point count', () => {
    render(<MetricCharts title="Loss Curves" series={sampleSeries} />);
    expect(screen.getByText('Loss Curves')).toBeInTheDocument();
    expect(screen.getByText('6 pts')).toBeInTheDocument();
  });

  it('renders series legend buttons and toggles visibility', () => {
    render(<MetricCharts title="Loss Curves" series={sampleSeries} />);
    const trainBtn = screen.getByText('Train Loss');
    expect(trainBtn).toBeInTheDocument();

    fireEvent.click(trainBtn);
    // Series visibility toggled
    expect(screen.getByText('Train Loss')).toBeInTheDocument();
  });

  it('toggles X-axis mode between step, epoch, and time', () => {
    render(<MetricCharts title="Loss Curves" series={sampleSeries} />);
    const epochBtn = screen.getByRole('button', { name: 'Epoch' });
    fireEvent.click(epochBtn);
    expect(epochBtn).toHaveClass('text-primary');

    const timeBtn = screen.getByRole('button', { name: 'Time' });
    fireEvent.click(timeBtn);
    expect(timeBtn).toHaveClass('text-primary');
  });

  it('toggles scale mode to LOG and LINEAR', () => {
    render(<MetricCharts title="Loss Curves" series={sampleSeries} />);
    const scaleBtn = screen.getByRole('button', { name: 'LINEAR' });
    fireEvent.click(scaleBtn);
    expect(screen.getByRole('button', { name: 'LOG' })).toBeInTheDocument();
  });

  it('handles range filtering', () => {
    render(<MetricCharts title="Loss Curves" series={sampleSeries} />);
    const range100 = screen.getByRole('button', { name: '100' });
    fireEvent.click(range100);
    expect(range100).toHaveClass('bg-primary');
  });

  it('adjusts smoothing slider', () => {
    render(<MetricCharts title="Loss Curves" series={sampleSeries} />);
    const slider = screen.getByLabelText('Exponential Moving Average Smoothing');
    fireEvent.change(slider, { target: { value: '0.6' } });
    expect(screen.getByText('EMA: 60%')).toBeInTheDocument();
  });
});

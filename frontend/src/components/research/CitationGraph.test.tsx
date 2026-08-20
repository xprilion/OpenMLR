import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { CitationGraph } from './CitationGraph';

describe('CitationGraph', () => {
  it('renders graph header, controls, and initial nodes', () => {
    render(<CitationGraph />);

    expect(screen.getByText('Research Citation Graph')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Graph View/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Literature Matrix/i })).toBeInTheDocument();
    expect(screen.getByText(/Attention Is All You Need/i)).toBeInTheDocument();
  });

  it('switches between Graph View and Literature Matrix view', () => {
    render(<CitationGraph />);

    const matrixBtn = screen.getByRole('button', { name: /Literature Matrix/i });
    fireEvent.click(matrixBtn);

    expect(screen.getByText('Benchmark Dataset')).toBeInTheDocument();
    expect(screen.getByText('Research Gap')).toBeInTheDocument();

    const graphBtn = screen.getByRole('button', { name: /Graph View/i });
    fireEvent.click(graphBtn);

    expect(screen.getByText('Research Citation Graph')).toBeInTheDocument();
  });

  it('filters graph by cluster selection', () => {
    render(<CitationGraph />);

    const select = screen.getByRole('combobox');
    fireEvent.change(select, { target: { value: 'Optimization' } });

    expect(screen.getByText(/FlashAttention/i)).toBeInTheDocument();
  });

  it('handles zoom controls', () => {
    render(<CitationGraph />);

    const zoomInBtn = screen.getByTitle('Zoom In');
    const zoomOutBtn = screen.getByTitle('Zoom Out');
    const resetZoomBtn = screen.getByTitle('Reset Zoom');

    fireEvent.click(zoomInBtn);
    fireEvent.click(zoomOutBtn);
    fireEvent.click(resetZoomBtn);

    expect(screen.getByText('Research Citation Graph')).toBeInTheDocument();
  });
});

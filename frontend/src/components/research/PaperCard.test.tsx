import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { PaperCard } from './PaperCard';
import type { PaperNode } from './types';

const MOCK_PAPER: PaperNode = {
  id: 'paper-1',
  title: 'Transformers in Machine Learning',
  authors: ['Alice Smith', 'Bob Jones'],
  year: 2024,
  venue: 'ICLR 2024',
  citations: 450,
  cluster: 'Architecture',
  abstract: 'An extensive survey and empirical benchmark of transformer architectures.',
  claims: ['Self-attention scales with high throughput.', 'FlashAttention reduces memory footprint.'],
  methodology: 'Scaled Dot-Product Attention with Rotary Embeddings',
  dataset: 'GLUE Benchmark',
  metric: '89.2 Score',
  baseline: 'BERT-Large',
  gap: 'O(N^2) memory complexity in extreme sequence regimes.',
  pdfUrl: 'https://arxiv.org/pdf/1706.03762.pdf',
};

describe('PaperCard', () => {
  it('renders empty state when paper is null', () => {
    render(<PaperCard paper={null} />);
    expect(screen.getByText('No Paper Selected')).toBeInTheDocument();
  });

  it('renders paper details, claims, and methodology', () => {
    const handleClose = vi.fn();
    const handleAdd = vi.fn();

    render(
      <PaperCard
        paper={MOCK_PAPER}
        onClose={handleClose}
        onAddToStudio={handleAdd}
      />
    );

    expect(screen.getByText('Transformers in Machine Learning')).toBeInTheDocument();
    expect(screen.getByText('Alice Smith, Bob Jones')).toBeInTheDocument();
    expect(screen.getByText('ICLR 2024')).toBeInTheDocument();
    expect(screen.getByText('450 citations')).toBeInTheDocument();
    expect(screen.getByText(/An extensive survey/)).toBeInTheDocument();
    expect(screen.getByText('Self-attention scales with high throughput.')).toBeInTheDocument();
    expect(screen.getByText('Scaled Dot-Product Attention with Rotary Embeddings')).toBeInTheDocument();
    expect(screen.getByText(/GLUE Benchmark/)).toBeInTheDocument();
  });

  it('handles copy BibTeX action', async () => {
    const writeTextMock = vi.fn().mockResolvedValue(undefined);
    Object.assign(navigator, {
      clipboard: { writeText: writeTextMock },
    });

    render(<PaperCard paper={MOCK_PAPER} />);
    const copyBtn = screen.getByRole('button', { name: /Copy BibTeX/i });
    fireEvent.click(copyBtn);

    expect(writeTextMock).toHaveBeenCalled();
  });

  it('handles cite in studio button click', () => {
    const handleAdd = vi.fn();
    render(<PaperCard paper={MOCK_PAPER} onAddToStudio={handleAdd} />);

    const citeBtn = screen.getByRole('button', { name: /Cite in Studio/i });
    fireEvent.click(citeBtn);
    expect(handleAdd).toHaveBeenCalledWith(MOCK_PAPER);
  });
});

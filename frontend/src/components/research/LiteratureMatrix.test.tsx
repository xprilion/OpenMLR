import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { LiteratureMatrix } from './LiteratureMatrix';
import type { PaperNode } from './types';

const MOCK_PAPERS: PaperNode[] = [
  {
    id: 'paper-1',
    title: 'Attention Is All You Need',
    authors: ['Ashish Vaswani', 'Noam Shazeer'],
    year: 2017,
    venue: 'NeurIPS 2017',
    citations: 120000,
    cluster: 'Architecture',
    abstract: 'Transformer model architecture.',
    claims: ['Self-attention reduces depth.'],
    methodology: 'Multi-Head Attention',
    dataset: 'WMT 2014 En-De',
    metric: '28.4 BLEU',
    baseline: 'ByteNet',
    gap: 'Quadratic memory complexity.',
  },
  {
    id: 'paper-2',
    title: 'FlashAttention IO-Awareness',
    authors: ['Tri Dao', 'Daniel Fu'],
    year: 2022,
    venue: 'NeurIPS 2022',
    citations: 5000,
    cluster: 'Optimization',
    abstract: 'Fast and memory-efficient exact attention.',
    claims: ['Exact attention with tiling.'],
    methodology: 'IO-Aware GPU Tiling',
    dataset: 'Long Range Arena',
    metric: '3.5x Speedup',
    baseline: 'PyTorch Attention',
    gap: 'Requires custom hardware kernels.',
  },
];

describe('LiteratureMatrix', () => {
  it('renders all rows and columns', () => {
    const handleSelect = vi.fn();
    render(<LiteratureMatrix papers={MOCK_PAPERS} onSelectPaper={handleSelect} />);

    expect(screen.getByText('Attention Is All You Need')).toBeInTheDocument();
    expect(screen.getByText('FlashAttention IO-Awareness')).toBeInTheDocument();
    expect(screen.getByText('Multi-Head Attention')).toBeInTheDocument();
    expect(screen.getByText('IO-Aware GPU Tiling')).toBeInTheDocument();
    expect(screen.getByText('28.4 BLEU')).toBeInTheDocument();
    expect(screen.getByText('3.5x Speedup')).toBeInTheDocument();
  });

  it('filters rows based on search query', () => {
    const handleSelect = vi.fn();
    render(<LiteratureMatrix papers={MOCK_PAPERS} onSelectPaper={handleSelect} />);

    const searchInput = screen.getByPlaceholderText(/Filter by method/i);
    fireEvent.change(searchInput, { target: { value: 'FlashAttention' } });

    expect(screen.getByText('FlashAttention IO-Awareness')).toBeInTheDocument();
    expect(screen.queryByText('Attention Is All You Need')).not.toBeInTheDocument();
  });

  it('handles row selection', () => {
    const handleSelect = vi.fn();
    render(<LiteratureMatrix papers={MOCK_PAPERS} onSelectPaper={handleSelect} />);

    const row = screen.getByText('FlashAttention IO-Awareness');
    fireEvent.click(row);

    expect(handleSelect).toHaveBeenCalledWith(MOCK_PAPERS[1]);
  });

  it('exports CSV and Markdown downloads', () => {
    const createObjectURLMock = vi.fn().mockReturnValue('blob:http://localhost/matrix-mock');
    const revokeObjectURLMock = vi.fn();
    Object.assign(URL, {
      createObjectURL: createObjectURLMock,
      revokeObjectURL: revokeObjectURLMock,
    });

    const handleSelect = vi.fn();
    render(<LiteratureMatrix papers={MOCK_PAPERS} onSelectPaper={handleSelect} />);

    const csvBtn = screen.getByRole('button', { name: /Export CSV/i });
    fireEvent.click(csvBtn);
    expect(createObjectURLMock).toHaveBeenCalled();

    const mdBtn = screen.getByRole('button', { name: /Export Markdown/i });
    fireEvent.click(mdBtn);
    expect(createObjectURLMock).toHaveBeenCalledTimes(2);
  });
});

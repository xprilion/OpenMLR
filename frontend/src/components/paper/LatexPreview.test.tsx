import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { LatexPreview } from './LatexPreview';
import type { PaperMetadata, PaperSection, BibtexEntry } from './types';

describe('LatexPreview', () => {
  const mockMetadata: PaperMetadata = {
    title: 'Test Paper Title',
    authors: ['Alice Smith', 'Bob Jones'],
    abstract: 'This is the test abstract summarizing the research.',
    keywords: ['Machine Learning', 'Autonomous Agents'],
    venue: 'ICLR 2027',
  };

  const mockSections: PaperSection[] = [
    {
      id: 'sec-1',
      title: 'Introduction',
      level: 1,
      content: 'Here is the intro citing \\cite{vaswani2017attention}.',
    },
    {
      id: 'sec-2',
      title: 'Methodology',
      level: 1,
      content: 'Here is the methodology section with equations.',
    },
  ];

  const mockBibtex: BibtexEntry[] = [
    {
      id: 'bib-1',
      citationKey: 'vaswani2017attention',
      entryType: 'article',
      title: 'Attention Is All You Need',
      author: 'Vaswani, Ashish',
      year: '2017',
      journal: 'NeurIPS',
      raw: '@article{vaswani2017attention,...}',
    },
  ];

  it('renders paper title, authors, venue and abstract', () => {
    render(
      <LatexPreview
        metadata={mockMetadata}
        sections={mockSections}
        bibtexEntries={mockBibtex}
      />
    );

    expect(screen.getByText('Test Paper Title')).toBeInTheDocument();
    expect(screen.getByText(/Alice Smith • Bob Jones/)).toBeInTheDocument();
    expect(screen.getByText('ICLR 2027')).toBeInTheDocument();
    expect(screen.getByText(/This is the test abstract/)).toBeInTheDocument();
    expect(screen.getByText('Machine Learning')).toBeInTheDocument();
  });

  it('renders section headings and content with citation links', () => {
    render(
      <LatexPreview
        metadata={mockMetadata}
        sections={mockSections}
        bibtexEntries={mockBibtex}
      />
    );

    expect(screen.getByText('Introduction')).toBeInTheDocument();
    expect(screen.getByText('Methodology')).toBeInTheDocument();
    expect(screen.getByText(/Vaswani et al\., 2017/)).toBeInTheDocument();
  });

  it('renders bibliography references section at the bottom', () => {
    render(
      <LatexPreview
        metadata={mockMetadata}
        sections={mockSections}
        bibtexEntries={mockBibtex}
      />
    );

    expect(screen.getByText('References')).toBeInTheDocument();
    expect(screen.getByText(/\[vaswani2017attention\]/)).toBeInTheDocument();
    expect(screen.getByText(/Attention Is All You Need/)).toBeInTheDocument();
  });
});

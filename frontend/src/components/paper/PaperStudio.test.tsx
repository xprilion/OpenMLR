import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { PaperStudio } from './PaperStudio';

describe('PaperStudio', () => {
  it('renders Paper Studio toolbar and initial sections', () => {
    render(<PaperStudio />);

    expect(screen.getByDisplayValue(/Autonomous Multi-Agent Machine Learning Research Harness/)).toBeInTheDocument();
    expect(screen.getByText('Introduction')).toBeInTheDocument();
    expect(screen.getByText('System Architecture & Methodology')).toBeInTheDocument();
  });

  it('switches view mode when toolbar buttons are clicked', () => {
    render(<PaperStudio />);

    const editorBtn = screen.getByTitle('Editor Only');
    fireEvent.click(editorBtn);
    expect(screen.getByPlaceholderText(/Write section body/)).toBeInTheDocument();

    const previewBtn = screen.getByTitle('Live Manuscript Preview');
    fireEvent.click(previewBtn);
    expect(screen.getByText(/Abstract/)).toBeInTheDocument();
  });

  it('adds a new section when add button is clicked', () => {
    render(<PaperStudio />);

    const addBtn = screen.getByTitle('Add section');
    fireEvent.click(addBtn);

    expect(screen.getByDisplayValue('New Section')).toBeInTheDocument();
  });

  it('triggers AI expand action and switches to diff mode', () => {
    render(<PaperStudio />);

    const expandBtn = screen.getByTitle('AI Expand Section');
    fireEvent.click(expandBtn);

    expect(screen.getByText('AI Section Revisions')).toBeInTheDocument();
    expect(screen.getByText('Accept Revision')).toBeInTheDocument();
  });

  it('toggles BibTeX manager drawer', () => {
    render(<PaperStudio />);

    const bibtexToggle = screen.getByTitle('Toggle BibTeX Manager');
    fireEvent.click(bibtexToggle);

    expect(screen.getByText('BibTeX Citations')).toBeInTheDocument();
    expect(screen.getByText('@vaswani2017attention')).toBeInTheDocument();
  });
});

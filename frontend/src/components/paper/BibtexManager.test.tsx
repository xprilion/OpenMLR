import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { BibtexManager } from './BibtexManager';
import type { BibtexEntry } from './types';

describe('BibtexManager', () => {
  const mockEntries: BibtexEntry[] = [
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
    {
      id: 'bib-2',
      citationKey: 'devlin2018bert',
      entryType: 'article',
      title: 'BERT: Pre-training of Deep Bidirectional Transformers',
      author: 'Devlin, Jacob',
      year: '2018',
      journal: 'NAACL',
      raw: '@article{devlin2018bert,...}',
    },
  ];

  it('renders citation keys and titles', () => {
    const onAdd = vi.fn();
    const onDelete = vi.fn();
    render(
      <BibtexManager
        entries={mockEntries}
        onAddEntry={onAdd}
        onDeleteEntry={onDelete}
      />
    );

    expect(screen.getByText('@vaswani2017attention')).toBeInTheDocument();
    expect(screen.getByText('@devlin2018bert')).toBeInTheDocument();
    expect(screen.getByText('Attention Is All You Need')).toBeInTheDocument();
  });

  it('filters citations by search query', () => {
    const onAdd = vi.fn();
    const onDelete = vi.fn();
    render(
      <BibtexManager
        entries={mockEntries}
        onAddEntry={onAdd}
        onDeleteEntry={onDelete}
      />
    );

    const searchInput = screen.getByPlaceholderText(/Search citation key/);
    fireEvent.change(searchInput, { target: { value: 'bert' } });

    expect(screen.queryByText('@vaswani2017attention')).not.toBeInTheDocument();
    expect(screen.getByText('@devlin2018bert')).toBeInTheDocument();
  });

  it('calls onDeleteEntry when delete button is clicked', () => {
    const onAdd = vi.fn();
    const onDelete = vi.fn();
    render(
      <BibtexManager
        entries={mockEntries}
        onAddEntry={onAdd}
        onDeleteEntry={onDelete}
      />
    );

    const deleteButtons = screen.getAllByTitle('Delete citation');
    fireEvent.click(deleteButtons[0]);
    expect(onDelete).toHaveBeenCalledWith('bib-1');
  });

  it('opens add modal and parses new BibTeX entry', () => {
    const onAdd = vi.fn();
    const onDelete = vi.fn();
    render(
      <BibtexManager
        entries={mockEntries}
        onAddEntry={onAdd}
        onDeleteEntry={onDelete}
      />
    );

    fireEvent.click(screen.getByText('Add BibTeX'));
    expect(screen.getByText('Add BibTeX Entry')).toBeInTheDocument();

    const textarea = screen.getByPlaceholderText(/@article\{vaswani2017attention/);
    fireEvent.change(textarea, {
      target: {
        value: `@article{brown2020gpt3,
  title={Language Models are Few-Shot Learners},
  author={Brown, Tom B and others},
  year={2020}
}`,
      },
    });

    fireEvent.click(screen.getByText('Save Citation'));
    expect(onAdd).toHaveBeenCalledWith(
      expect.objectContaining({
        citationKey: 'brown2020gpt3',
        title: 'Language Models are Few-Shot Learners',
        author: 'Brown, Tom B and others',
        year: '2020',
      })
    );
  });
});

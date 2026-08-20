import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { SectionDiffViewer } from './SectionDiffViewer';
import type { SectionDiff } from './types';

describe('SectionDiffViewer', () => {
  it('renders empty state when no pending diffs', () => {
    render(
      <SectionDiffViewer
        diffs={[]}
        onApplyDiff={vi.fn()}
        onRejectDiff={vi.fn()}
      />
    );

    expect(screen.getByText('No Pending AI Revisions')).toBeInTheDocument();
  });

  it('renders pending diffs with additions and removals', () => {
    const onApply = vi.fn();
    const onReject = vi.fn();
    const mockDiffs: SectionDiff[] = [
      {
        id: 'diff-1',
        sectionId: 'sec-1',
        sectionTitle: 'Methodology',
        originalText: 'Original formulation.',
        proposedText: 'Original formulation.\nNew convergence proof.',
        reason: 'Added theoretical convergence proof.',
        status: 'pending',
      },
    ];

    render(
      <SectionDiffViewer
        diffs={mockDiffs}
        onApplyDiff={onApply}
        onRejectDiff={onReject}
      />
    );

    expect(screen.getByText('Methodology')).toBeInTheDocument();
    expect(screen.getByText('Added theoretical convergence proof.')).toBeInTheDocument();
    expect(screen.getByText('New convergence proof.')).toBeInTheDocument();

    fireEvent.click(screen.getByText('Accept Revision'));
    expect(onApply).toHaveBeenCalledWith('diff-1');

    fireEvent.click(screen.getByText('Reject'));
    expect(onReject).toHaveBeenCalledWith('diff-1');
  });
});

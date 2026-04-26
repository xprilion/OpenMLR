import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import ReactMarkdown from 'react-markdown';
import { ReportDrawer } from '../components/ReportDrawer';

vi.mock('../api', () => ({
  api: {
    getReport: vi.fn(),
  },
}));

describe('ReportDrawer', () => {
  it('renders title and close button', () => {
    render(
      <ReportDrawer
        reportId="rpt-1"
        title="My Test Report"
        cachedContent="# Hello\n\nThis is content."
        onClose={vi.fn()}
      />
    );
    expect(screen.getByText('My Test Report')).toBeInTheDocument();
    expect(screen.getByText('×')).toBeInTheDocument();
  });

  it('renders cached content without loading', () => {
    render(
      <ReportDrawer
        reportId="rpt-1"
        title="Test"
        cachedContent="# Cached Content"
        onClose={vi.fn()}
      />
    );
    expect(screen.queryByText('Loading...')).not.toBeInTheDocument();
  });

  it('shows loading state without cached content', async () => {
    const { api } = await import('../api');
    vi.mocked(api.getReport).mockImplementation(() => new Promise(() => {})); // never resolves
    render(
      <ReportDrawer
        reportId="rpt-1"
        title="Test"
        cachedContent=""
        onClose={vi.fn()}
      />
    );
    expect(screen.getByText('Loading...')).toBeInTheDocument();
  });

  it('calls onClose when close button clicked', () => {
    const onClose = vi.fn();
    render(
      <ReportDrawer
        reportId="rpt-1"
        title="Test"
        cachedContent="# Content"
        onClose={onClose}
      />
    );
    screen.getByText('×').click();
    expect(onClose).toHaveBeenCalled();
  });

  it('calls onClose when overlay clicked', () => {
    const onClose = vi.fn();
    render(
      <ReportDrawer
        reportId="rpt-1"
        title="Test"
        cachedContent="# Content"
        onClose={onClose}
      />
    );
    const overlay = document.querySelector('.report-overlay');
    if (overlay) {
      (overlay as HTMLElement).click();
      expect(onClose).toHaveBeenCalled();
    }
  });
});

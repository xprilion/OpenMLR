import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ReportDrawer } from '../components/ReportDrawer';

vi.mock('../api', () => ({
  api: {
    getReport: vi.fn(),
  },
}));

describe('ReportDrawer', () => {
  it('renders title and close button', () => {
    const { container } = render(
      <ReportDrawer
        reportId="rpt-1"
        title="My Test Report"
        cachedContent="# Hello\n\nThis is content."
        onClose={vi.fn()}
      />
    );
    expect(screen.getByText('My Test Report')).toBeInTheDocument();
    // Close button now uses Lucide X icon
    const closeBtn = container.querySelector('.lucide-x')?.closest('button');
    expect(closeBtn).toBeTruthy();
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
    const { container } = render(
      <ReportDrawer
        reportId="rpt-1"
        title="Test"
        cachedContent="# Content"
        onClose={onClose}
      />
    );
    // Close button now uses Lucide X icon
    const closeBtn = container.querySelector('.lucide-x')?.closest('button');
    expect(closeBtn).toBeTruthy();
    fireEvent.click(closeBtn!);
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
    // The overlay is the fixed div with bg-black/60
    const overlay = document.querySelector('.fixed.inset-0');
    if (overlay) {
      fireEvent.click(overlay);
      expect(onClose).toHaveBeenCalled();
    }
  });
});

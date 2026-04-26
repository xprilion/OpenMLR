import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { WritingSettings } from '../components/settings/WritingSettings';
import { api } from '../api';

vi.mock('../api', () => ({
  api: {
    getSettings: vi.fn(),
    updateSetting: vi.fn(),
  },
}));

describe('WritingSettings', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.getSettings).mockResolvedValue({ settings: {} });
  });

  it('renders hint', async () => {
    render(<WritingSettings />);
    await waitFor(() => {
      expect(screen.getByText('Paper writing preferences.')).toBeInTheDocument();
    });
  });

  it('renders citation style select', async () => {
    render(<WritingSettings />);
    await waitFor(() => {
      expect(screen.getByText('Citation Style')).toBeInTheDocument();
      expect(screen.getByText('APA')).toBeInTheDocument();
      expect(screen.getByText('IEEE')).toBeInTheDocument();
    });
  });

  it('renders export format select', async () => {
    render(<WritingSettings />);
    await waitFor(() => {
      expect(screen.getByText('Export Format')).toBeInTheDocument();
      expect(screen.getByText('Markdown')).toBeInTheDocument();
      expect(screen.getByText('LaTeX')).toBeInTheDocument();
    });
  });

  it('renders save button', async () => {
    render(<WritingSettings />);
    await waitFor(() => {
      expect(screen.getByText('Save Writing Settings')).toBeInTheDocument();
    });
  });

  it('loads settings on mount', async () => {
    vi.mocked(api.getSettings).mockResolvedValue({
      settings: { writing: { citation_style: 'ieee' } },
    });
    render(<WritingSettings />);
    await waitFor(() => {
      expect(api.getSettings).toHaveBeenCalled();
    });
  });
});

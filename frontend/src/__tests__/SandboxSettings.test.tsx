import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { SandboxSettings } from '../components/settings/SandboxSettings';
import { api } from '../api';

vi.mock('../api', () => ({
  api: {
    getSettings: vi.fn(),
    updateSetting: vi.fn(),
  },
}));

describe('SandboxSettings', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.getSettings).mockResolvedValue({ settings: {} });
  });

  it('renders heading and hint', async () => {
    render(<SandboxSettings />);
    await waitFor(() => {
      expect(screen.getByText(/Execution environment/)).toBeInTheDocument();
    });
  });

  it('renders default sandbox select', async () => {
    render(<SandboxSettings />);
    await waitFor(() => {
      expect(screen.getByText('Default Sandbox')).toBeInTheDocument();
      expect(screen.getByText('Local')).toBeInTheDocument();
      expect(screen.getByText('SSH Remote')).toBeInTheDocument();
      expect(screen.getByText('Modal Cloud')).toBeInTheDocument();
    });
  });

  it('renders modal token fields', async () => {
    render(<SandboxSettings />);
    await waitFor(() => {
      expect(screen.getByPlaceholderText('MODAL_TOKEN_ID')).toBeInTheDocument();
      expect(screen.getByPlaceholderText('MODAL_TOKEN_SECRET')).toBeInTheDocument();
    });
  });

  it('renders save button', async () => {
    render(<SandboxSettings />);
    await waitFor(() => {
      expect(screen.getByText('Save Sandbox Settings')).toBeInTheDocument();
    });
  });

  it('loads settings on mount', async () => {
    vi.mocked(api.getSettings).mockResolvedValue({
      settings: { sandbox: { default_sandbox: 'ssh' } },
    });
    render(<SandboxSettings />);
    await waitFor(() => {
      expect(api.getSettings).toHaveBeenCalled();
    });
  });
});

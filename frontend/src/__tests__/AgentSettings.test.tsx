import { describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { AgentSettings } from '../components/settings/AgentSettings';
import { api } from '../api';

vi.mock('../api', () => ({
  api: {
    getSettings: vi.fn(),
    updateSetting: vi.fn(),
  },
}));

describe('AgentSettings', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.getSettings).mockResolvedValue({ settings: {} });
  });

  it('renders model hint', async () => {
    render(<AgentSettings />);
    await waitFor(() => {
      expect(screen.getByText(/Model used for new conversations/)).toBeInTheDocument();
    });
  });

  it('renders default model input', async () => {
    render(<AgentSettings />);
    await waitFor(() => {
      expect(screen.getByText('Default Model')).toBeInTheDocument();
      expect(screen.getByPlaceholderText(/anthropic\/claude-sonnet-4/)).toBeInTheDocument();
    });
  });

  it('renders research model input', async () => {
    render(<AgentSettings />);
    await waitFor(() => {
      expect(screen.getByText(/Research \/ Title Model/)).toBeInTheDocument();
    });
  });

  it('renders yolo mode checkbox', async () => {
    render(<AgentSettings />);
    await waitFor(() => {
      expect(screen.getByText(/YOLO Mode/)).toBeInTheDocument();
    });
  });

  it('renders save button', async () => {
    render(<AgentSettings />);
    await waitFor(() => {
      expect(screen.getByText('Save Agent Settings')).toBeInTheDocument();
    });
  });

  it('loads settings on mount', async () => {
    vi.mocked(api.getSettings).mockResolvedValue({
      settings: { agent: { default_model: 'claude-4', yolo_mode: true } },
    });
    render(<AgentSettings />);
    await waitFor(() => {
      expect(api.getSettings).toHaveBeenCalled();
    });
  });
});

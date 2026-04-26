import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { SettingsPanel } from '../components/SettingsPanel';
import { api } from '../api';

vi.mock('../api', () => ({
  api: {
    getProviders: vi.fn(),
    getSettings: vi.fn(),
    updateSetting: vi.fn(),
  },
}));

describe('SettingsPanel', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(api.getProviders).mockResolvedValue({
      providers: [
        { id: 'openai', name: 'OpenAI', key_env: 'OPENAI_API_KEY', configured: true },
        { id: 'anthropic', name: 'Anthropic', key_env: 'ANTHROPIC_API_KEY', configured: false },
      ],
    });
    vi.mocked(api.getSettings).mockResolvedValue({ settings: {} });
  });

  it('renders settings heading', async () => {
    render(<SettingsPanel onClose={vi.fn()} />);
    await waitFor(() => {
      expect(screen.getByText('Settings')).toBeInTheDocument();
    });
  });

  it('renders tab buttons', async () => {
    render(<SettingsPanel onClose={vi.fn()} />);
    await waitFor(() => {
      expect(screen.getByText('Providers')).toBeInTheDocument();
      expect(screen.getByText('Agent')).toBeInTheDocument();
      expect(screen.getByText('Sandbox')).toBeInTheDocument();
      expect(screen.getByText('Writing')).toBeInTheDocument();
    });
  });

  it('shows providers by default', async () => {
    render(<SettingsPanel onClose={vi.fn()} />);
    await waitFor(() => {
      expect(screen.getByText('OpenAI')).toBeInTheDocument();
      expect(screen.getByText('Anthropic')).toBeInTheDocument();
    });
  });

  it('shows configured status', async () => {
    render(<SettingsPanel onClose={vi.fn()} />);
    await waitFor(() => {
      expect(screen.getByText('Configured')).toBeInTheDocument();
      expect(screen.getByText('Not set')).toBeInTheDocument();
    });
  });

  it('switches to agent tab', async () => {
    render(<SettingsPanel onClose={vi.fn()} />);
    await waitFor(() => {
      fireEvent.click(screen.getByText('Agent'));
    });
    expect(screen.getByText('Default Model')).toBeInTheDocument();
    expect(screen.getByText(/YOLO Mode/)).toBeInTheDocument();
  });

  it('switches to sandbox tab', async () => {
    render(<SettingsPanel onClose={vi.fn()} />);
    await waitFor(() => {
      fireEvent.click(screen.getByText('Sandbox'));
    });
    expect(screen.getByText('Default Sandbox')).toBeInTheDocument();
  });

  it('switches to writing tab', async () => {
    render(<SettingsPanel onClose={vi.fn()} />);
    await waitFor(() => {
      fireEvent.click(screen.getByText('Writing'));
    });
    expect(screen.getByText('Citation Style')).toBeInTheDocument();
    expect(screen.getByText('Export Format')).toBeInTheDocument();
  });

  it('calls onClose when close clicked', async () => {
    const onClose = vi.fn();
    render(<SettingsPanel onClose={onClose} />);
    await waitFor(() => {
      const closeBtn = screen.getByText('×');
      fireEvent.click(closeBtn);
    });
    expect(onClose).toHaveBeenCalled();
  });

  it('calls onClose when overlay clicked', async () => {
    const onClose = vi.fn();
    render(<SettingsPanel onClose={onClose} />);
    await waitFor(() => {
      const overlay = document.querySelector('.modal-overlay');
      fireEvent.click(overlay!);
    });
    expect(onClose).toHaveBeenCalled();
  });
});

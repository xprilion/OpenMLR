import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ProvidersSettings } from '../components/settings/ProvidersSettings';
import { api } from '../api';

vi.mock('../api', () => ({
  api: {
    getProviders: vi.fn(),
    updateSetting: vi.fn(),
  },
}));

describe('ProvidersSettings', () => {
  const mockProviders = [
    { id: 'openai', name: 'OpenAI', key_env: 'OPENAI_API_KEY', configured: true },
    { id: 'anthropic', name: 'Anthropic', key_env: 'ANTHROPIC_API_KEY', configured: false },
  ];

  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.getProviders).mockResolvedValue({ providers: mockProviders });
  });

  it('renders hint', async () => {
    render(<ProvidersSettings />);
    await waitFor(() => {
      expect(screen.getByText(/API keys are stored/)).toBeInTheDocument();
    });
  });

  it('renders provider names', async () => {
    render(<ProvidersSettings />);
    await waitFor(() => {
      expect(screen.getByText('OpenAI')).toBeInTheDocument();
      expect(screen.getByText('Anthropic')).toBeInTheDocument();
    });
  });

  it('shows configured/not set status', async () => {
    render(<ProvidersSettings />);
    await waitFor(() => {
      expect(screen.getByText('Configured')).toBeInTheDocument();
      expect(screen.getByText('Not set')).toBeInTheDocument();
    });
  });

  it('renders key input placeholders', async () => {
    render(<ProvidersSettings />);
    await waitFor(() => {
      expect(screen.getByPlaceholderText('OPENAI_API_KEY')).toBeInTheDocument();
      expect(screen.getByPlaceholderText('ANTHROPIC_API_KEY')).toBeInTheDocument();
    });
  });

  it('renders save button', async () => {
    render(<ProvidersSettings />);
    await waitFor(() => {
      expect(screen.getByText('Save Keys')).toBeInTheDocument();
    });
  });

  it('disables save when no keys entered', async () => {
    render(<ProvidersSettings />);
    await waitFor(() => {
      const btn = screen.getByText('Save Keys');
      expect(btn).toBeDisabled();
    });
  });

  it('enables save when key entered', async () => {
    render(<ProvidersSettings />);
    await waitFor(() => {
      const input = screen.getByPlaceholderText('ANTHROPIC_API_KEY');
      fireEvent.change(input, { target: { value: 'sk-ant-test' } });
    });
    const btn = screen.getByText('Save Keys');
    expect(btn).not.toBeDisabled();
  });

  it('loads providers on mount', async () => {
    render(<ProvidersSettings />);
    await waitFor(() => {
      expect(api.getProviders).toHaveBeenCalled();
    });
  });
});

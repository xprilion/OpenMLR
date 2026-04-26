import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { OnboardingModal } from '../components/OnboardingModal';
import { api } from '../api';

vi.mock('../api', () => ({
  api: {
    getProviders: vi.fn(),
    getModels: vi.fn(),
    saveConfig: vi.fn(),
    setModel: vi.fn(),
  },
}));

const defaultProviders = [
  { id: 'openai', name: 'OpenAI', key_env: 'OPENAI_API_KEY', configured: false },
  { id: 'anthropic', name: 'Anthropic', key_env: 'ANTHROPIC_API_KEY', configured: false },
  { id: 'openrouter', name: 'OpenRouter', key_env: 'OPENROUTER_API_KEY', configured: false },
  { id: 'opencode-go', name: 'OpenCode Go', key_env: 'OPENCODE_GO_API_KEY', configured: false },
  { id: 'ollama', name: 'Ollama', key_env: 'OLLAMA_API_BASE', configured: false },
  { id: 'brave', name: 'Brave Search', key_env: 'BRAVE_API_KEY', configured: false },
];

const defaultModels = [
  { id: 'openai/gpt-4o', name: 'GPT-4o', provider: 'openai' },
  { id: 'anthropic/claude-4', name: 'Claude 4', provider: 'anthropic' },
];

describe('OnboardingModal', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(api.getProviders).mockResolvedValue({ providers: defaultProviders });
    vi.mocked(api.getModels).mockResolvedValue({ models: defaultModels });
  });

  it('renders welcome heading', async () => {
    render(<OnboardingModal onComplete={vi.fn()} />);
    await waitFor(() => {
      expect(screen.getByText('Welcome to OpenMLR')).toBeInTheDocument();
    });
  });

  it('shows loading state initially', () => {
    vi.mocked(api.getProviders).mockImplementation(() => new Promise(() => {}));
    render(<OnboardingModal onComplete={vi.fn()} />);
    expect(screen.getByText('Loading...')).toBeInTheDocument();
  });

  it('shows providers step by default', async () => {
    render(<OnboardingModal onComplete={vi.fn()} />);
    await waitFor(() => {
      expect(screen.getByText(/Configure at least one LLM provider/)).toBeInTheDocument();
    });
  });

  it('renders LLM providers', async () => {
    render(<OnboardingModal onComplete={vi.fn()} />);
    await waitFor(() => {
      expect(screen.getByText('OpenAI')).toBeInTheDocument();
      expect(screen.getByText('Anthropic')).toBeInTheDocument();
    });
  });

  it('shows key inputs for unconfigured providers', async () => {
    render(<OnboardingModal onComplete={vi.fn()} />);
    await waitFor(() => {
      expect(screen.getByPlaceholderText(/OPENAI_API_KEY/)).toBeInTheDocument();
    });
  });

  it('shows "configured" for configured providers', async () => {
    vi.mocked(api.getProviders).mockResolvedValue({
      providers: [
        { id: 'openai', name: 'OpenAI', key_env: 'OPENAI_API_KEY', configured: true },
        { id: 'anthropic', name: 'Anthropic', key_env: 'ANTHROPIC_API_KEY', configured: false },
        { id: 'openrouter', name: 'OpenRouter', key_env: 'OPENROUTER_API_KEY', configured: false },
        { id: 'opencode-go', name: 'OpenCode Go', key_env: 'OPENCODE_GO_API_KEY', configured: false },
        { id: 'ollama', name: 'Ollama', key_env: 'OLLAMA_API_BASE', configured: false },
      ],
    });
    render(<OnboardingModal onComplete={vi.fn()} />);
    // When at least one provider is configured, step auto-skips to model selection
    await waitFor(() => {
      expect(screen.getByText(/Pick a model/)).toBeInTheDocument();
    });
  });

  it('skips to model selection when providers are configured', async () => {
    vi.mocked(api.getProviders).mockResolvedValue({
      providers: [
        { id: 'openai', name: 'OpenAI', key_env: 'OPENAI_API_KEY', configured: true },
      ],
    });
    render(<OnboardingModal onComplete={vi.fn()} />);
    await waitFor(() => {
      expect(screen.getByText(/Pick a model/)).toBeInTheDocument();
    });
  });

  it('disables save button when no keys entered', async () => {
    render(<OnboardingModal onComplete={vi.fn()} />);
    await waitFor(() => {
      const btn = screen.getByText('Save & Continue');
      expect(btn).toBeDisabled();
    });
  });

  it('saves keys and moves to model step', async () => {
    vi.mocked(api.saveConfig).mockResolvedValue({ ok: true });
    vi.mocked(api.getProviders)
      .mockResolvedValueOnce({ providers: defaultProviders })
      .mockResolvedValueOnce({
        providers: [{ ...defaultProviders[0], configured: true }, ...defaultProviders.slice(1)],
      });

    render(<OnboardingModal onComplete={vi.fn()} />);
    await waitFor(() => {
      expect(screen.getByPlaceholderText(/OPENAI_API_KEY/)).toBeInTheDocument();
    });

    // Type a key
    const input = screen.getByPlaceholderText(/OPENAI_API_KEY/);
    fireEvent.change(input, { target: { value: 'sk-test-key' } });

    fireEvent.click(screen.getByText('Save & Continue'));

    await waitFor(() => {
      expect(api.saveConfig).toHaveBeenCalled();
      expect(screen.getByText(/Pick a model/)).toBeInTheDocument();
    });
  });

  it('shows models in model step', async () => {
    vi.mocked(api.getProviders).mockResolvedValue({
      providers: [{ ...defaultProviders[0], configured: true }],
    });
    render(<OnboardingModal onComplete={vi.fn()} />);
    await waitFor(() => {
      expect(screen.getByText('GPT-4o')).toBeInTheDocument();
      expect(screen.getByText('Claude 4')).toBeInTheDocument();
    });
  });

  it('filters models by provider', async () => {
    vi.mocked(api.getProviders).mockResolvedValue({
      providers: [
        { id: 'openai', name: 'OpenAI', key_env: 'OPENAI_API_KEY', configured: true },
        { id: 'anthropic', name: 'Anthropic', key_env: 'ANTHROPIC_API_KEY', configured: true },
      ],
    });
    render(<OnboardingModal onComplete={vi.fn()} />);
    await waitFor(() => {
      expect(screen.getByText(/Pick a model/)).toBeInTheDocument();
    });

    // Select OpenAI from provider filter
    const select = document.querySelector('select')!;
    fireEvent.change(select, { target: { value: 'openai' } });

    await waitFor(() => {
      expect(screen.getByText('GPT-4o')).toBeInTheDocument();
      expect(screen.queryByText('Claude 4')).not.toBeInTheDocument();
    });
  });

  it('selects model and completes', async () => {
    const onComplete = vi.fn();
    vi.mocked(api.setModel).mockResolvedValue({ ok: true });
    vi.mocked(api.getProviders).mockResolvedValue({
      providers: [{ ...defaultProviders[0], configured: true }],
    });

    render(<OnboardingModal onComplete={onComplete} />);
    await waitFor(() => {
      expect(screen.getByText('GPT-4o')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('GPT-4o'));

    await waitFor(() => {
      expect(api.setModel).toHaveBeenCalledWith('openai/gpt-4o');
      expect(onComplete).toHaveBeenCalledWith('openai/gpt-4o');
    });
  });
});

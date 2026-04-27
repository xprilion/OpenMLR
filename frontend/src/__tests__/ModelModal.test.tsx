import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ModelModal } from '../components/ModelModal';
import { api } from '../api';

const mockNavigate = vi.fn();
vi.mock('react-router-dom', () => ({
  useNavigate: () => mockNavigate,
}));

vi.mock('../api', () => ({
  api: {
    getProviders: vi.fn(),
    getModels: vi.fn(),
    saveConfig: vi.fn(),
    setModel: vi.fn(),
  },
}));

const defaultProviders = [
  { id: 'openai', name: 'OpenAI', key_env: 'OPENAI_API_KEY', configured: true, categories: ['models'] },
  { id: 'anthropic', name: 'Anthropic', key_env: 'ANTHROPIC_API_KEY', configured: true, categories: ['models'] },
];

const defaultModels = [
  { id: 'openai/gpt-4o', name: 'GPT-4o', provider: 'openai', release_date: '2024-05-13' },
  { id: 'openai/gpt-4o-mini', name: 'GPT-4o Mini', provider: 'openai', release_date: '2024-07-18' },
  { id: 'anthropic/claude-4', name: 'Claude 4', provider: 'anthropic', release_date: '2025-01-01' },
];

const defaultRecent = [
  { id: 'openai/gpt-4o', name: 'GPT-4o', provider: 'openai', release_date: '2024-05-13' },
];

describe('ModelModal', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(api.getProviders).mockResolvedValue({ providers: defaultProviders });
    vi.mocked(api.getModels).mockResolvedValue({ models: defaultModels, recent_models: defaultRecent });
  });

  it('renders current model button', () => {
    render(<ModelModal currentModel="openai/gpt-4o" onModelChange={vi.fn()} />);
    expect(screen.getByText('openai/gpt-4o')).toBeInTheDocument();
  });

  it('opens modal on button click', () => {
    render(<ModelModal currentModel="openai/gpt-4o" onModelChange={vi.fn()} />);
    fireEvent.click(screen.getByText('openai/gpt-4o'));
    expect(screen.getByText('Models')).toBeInTheDocument();
    expect(screen.getByText('Providers')).toBeInTheDocument();
  });

  it('shows recent models section when opened', async () => {
    render(<ModelModal currentModel="openai/gpt-4o" onModelChange={vi.fn()} />);
    fireEvent.click(screen.getByText('openai/gpt-4o'));

    await waitFor(() => {
      expect(screen.getByText('Recently Used')).toBeInTheDocument();
      expect(screen.getAllByText('GPT-4o').length).toBeGreaterThanOrEqual(1);
    });
  });

  it('shows provider group headings', async () => {
    render(<ModelModal currentModel="openai/gpt-4o" onModelChange={vi.fn()} />);
    fireEvent.click(screen.getByText('openai/gpt-4o'));

    await waitFor(() => {
      // OpenAI appears as both a heading and filter option
      expect(screen.getAllByText('OpenAI').length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText('Anthropic').length).toBeGreaterThanOrEqual(1);
    });
  });

  it('shows model list when opened', async () => {
    render(<ModelModal currentModel="openai/gpt-4o" onModelChange={vi.fn()} />);
    fireEvent.click(screen.getByText('openai/gpt-4o'));

    await waitFor(() => {
      // GPT-4o appears twice (recent + provider group)
      expect(screen.getAllByText('GPT-4o').length).toBeGreaterThanOrEqual(1);
      expect(screen.getByText('GPT-4o Mini')).toBeInTheDocument();
    });
  });

  it('highlights current model with border-primary class', async () => {
    render(<ModelModal currentModel="openai/gpt-4o-mini" onModelChange={vi.fn()} />);
    fireEvent.click(screen.getByText('openai/gpt-4o-mini'));

    await waitFor(() => {
      // Find the button containing "GPT-4o Mini"
      const miniButton = screen.getAllByText('GPT-4o Mini')[0].closest('button');
      // Check that it has the active styling (border-primary)
      expect(miniButton?.className).toContain('border-primary');
    });
  });

  it('switches to providers tab', async () => {
    // Use a mix of configured and unconfigured providers for this test
    vi.mocked(api.getProviders).mockResolvedValue({
      providers: [
        { id: 'openai', name: 'OpenAI', key_env: 'OPENAI_API_KEY', configured: true, categories: ['models'] },
        { id: 'anthropic', name: 'Anthropic', key_env: 'ANTHROPIC_API_KEY', configured: false, categories: ['models'] },
      ],
    });

    render(<ModelModal currentModel="openai/gpt-4o" onModelChange={vi.fn()} />);
    fireEvent.click(screen.getByText('openai/gpt-4o'));
    fireEvent.click(screen.getByText('Providers'));

    await waitFor(() => {
      expect(screen.getByText('Configured')).toBeInTheDocument();
      expect(screen.getByText('API key missing')).toBeInTheDocument();
    });
  });

  it('filters models by search', async () => {
    render(<ModelModal currentModel="openai/gpt-4o" onModelChange={vi.fn()} />);
    fireEvent.click(screen.getByText('openai/gpt-4o'));

    await waitFor(() => {
      expect(screen.getByText('Claude 4')).toBeInTheDocument();
    });

    const input = screen.getByPlaceholderText('Search models...');
    fireEvent.change(input, { target: { value: 'gpt-4o' } });

    await waitFor(() => {
      expect(screen.getAllByText('GPT-4o').length).toBeGreaterThanOrEqual(1);
      expect(screen.queryByText('Claude 4')).not.toBeInTheDocument();
    });
  });

  it('selects model and calls onModelChange', async () => {
    vi.mocked(api.setModel).mockResolvedValue({ ok: true });
    const onChange = vi.fn();

    render(<ModelModal currentModel="openai/gpt-4o" onModelChange={onChange} />);
    fireEvent.click(screen.getByText('openai/gpt-4o'));

    await waitFor(() => {
      expect(screen.getByText('Claude 4')).toBeInTheDocument();
    });

    fireEvent.click(screen.getAllByText('Claude 4')[0]);

    await waitFor(() => {
      expect(api.setModel).toHaveBeenCalledWith('anthropic/claude-4');
      expect(onChange).toHaveBeenCalledWith('anthropic/claude-4');
    });
  });

  it('closed modal on close button', async () => {
    vi.mocked(api.setModel).mockResolvedValue({ ok: true });

    render(<ModelModal currentModel="openai/gpt-4o" onModelChange={vi.fn()} />);
    fireEvent.click(screen.getByText('openai/gpt-4o'));

    await waitFor(() => {
      expect(screen.getAllByText('GPT-4o').length).toBeGreaterThanOrEqual(1);
    });

    fireEvent.click(screen.getByText('Close'));

    await waitFor(() => {
      expect(screen.queryByText('GPT-4o Mini')).not.toBeInTheDocument();
    });
  });

  it('shows custom model input', async () => {
    render(<ModelModal currentModel="openai/gpt-4o" onModelChange={vi.fn()} />);
    fireEvent.click(screen.getByText('openai/gpt-4o'));

    await waitFor(() => {
      expect(screen.getByPlaceholderText('Custom model ID')).toBeInTheDocument();
    });
  });

  it('uses custom model on Enter', async () => {
    vi.mocked(api.setModel).mockResolvedValue({ ok: true });
    const onModelChange = vi.fn();

    render(<ModelModal currentModel="openai/gpt-4o" onModelChange={onModelChange} />);
    fireEvent.click(screen.getByText('openai/gpt-4o'));

    await waitFor(() => {
      expect(screen.getByPlaceholderText('Custom model ID')).toBeInTheDocument();
    });

    const input = screen.getByPlaceholderText('Custom model ID');
    fireEvent.change(input, { target: { value: 'my-custom-model' } });
    fireEvent.keyDown(input, { key: 'Enter' });

    await waitFor(() => {
      expect(api.setModel).toHaveBeenCalledWith('my-custom-model');
      expect(onModelChange).toHaveBeenCalledWith('my-custom-model');
    });
  });

  it('closes modal when overlay clicked', async () => {
    render(<ModelModal currentModel="openai/gpt-4o" onModelChange={vi.fn()} />);
    fireEvent.click(screen.getByText('openai/gpt-4o'));

    await waitFor(() => {
      expect(screen.getAllByText('GPT-4o').length).toBeGreaterThanOrEqual(1);
    });

    // Find the overlay (the fixed div with bg-black/60)
    const overlay = document.querySelector('.fixed.inset-0');
    fireEvent.click(overlay!);

    await waitFor(() => {
      expect(screen.queryByText('GPT-4o Mini')).not.toBeInTheDocument();
    });
  });

  it('navigates to settings when "More provider settings" clicked', async () => {
    render(<ModelModal currentModel="openai/gpt-4o" onModelChange={vi.fn()} />);
    fireEvent.click(screen.getByText('openai/gpt-4o'));

    await waitFor(() => {
      expect(screen.getByText('More provider settings')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('More provider settings'));
    expect(mockNavigate).toHaveBeenCalledWith('/settings/providers');
  });

  it('shows provider filter dropdown', async () => {
    render(<ModelModal currentModel="openai/gpt-4o" onModelChange={vi.fn()} />);
    fireEvent.click(screen.getByText('openai/gpt-4o'));

    await waitFor(() => {
      expect(screen.getByTitle('Filter by provider')).toBeInTheDocument();
    });
  });
});

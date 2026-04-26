import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ModelModal } from '../components/ModelModal';
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
  { id: 'openai', name: 'OpenAI', key_env: 'OPENAI_API_KEY', configured: true },
  { id: 'anthropic', name: 'Anthropic', key_env: 'ANTHROPIC_API_KEY', configured: false },
];

const defaultModels = [
  { id: 'openai/gpt-4o', name: 'GPT-4o', provider: 'openai' },
  { id: 'openai/gpt-4o-mini', name: 'GPT-4o Mini', provider: 'openai' },
  { id: 'anthropic/claude-4', name: 'Claude 4', provider: 'anthropic' },
];

describe('ModelModal', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(api.getProviders).mockResolvedValue({ providers: defaultProviders });
    vi.mocked(api.getModels).mockResolvedValue({ models: defaultModels });
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

  it('shows model list when opened', async () => {
    render(<ModelModal currentModel="openai/gpt-4o" onModelChange={vi.fn()} />);
    fireEvent.click(screen.getByText('openai/gpt-4o'));

    await waitFor(() => {
      expect(screen.getByText('GPT-4o')).toBeInTheDocument();
      expect(screen.getByText('GPT-4o Mini')).toBeInTheDocument();
      expect(screen.getByText('Claude 4')).toBeInTheDocument();
    });
  });

  it('highlights current model', async () => {
    render(<ModelModal currentModel="openai/gpt-4o-mini" onModelChange={vi.fn()} />);
    fireEvent.click(screen.getByText('openai/gpt-4o-mini'));

    await waitFor(() => {
      const options = document.querySelectorAll('.model-picker-option');
      const mini = Array.from(options).find(o => o.textContent?.includes('GPT-4o Mini'));
      expect(mini?.classList.contains('active')).toBe(true);
    });
  });

  it('switches to providers tab', async () => {
    render(<ModelModal currentModel="openai/gpt-4o" onModelChange={vi.fn()} />);
    fireEvent.click(screen.getByText('openai/gpt-4o'));
    fireEvent.click(screen.getByText('Providers'));

    await waitFor(() => {
      expect(screen.getByText('Configured')).toBeInTheDocument();
      expect(screen.getByText('API key missing')).toBeInTheDocument();
    });
  });

  it('filters models by provider', async () => {
    render(<ModelModal currentModel="openai/gpt-4o" onModelChange={vi.fn()} />);
    fireEvent.click(screen.getByText('openai/gpt-4o'));

    await waitFor(() => {
      expect(screen.getByText('Claude 4')).toBeInTheDocument();
    });

    const select = document.querySelector('select')!;
    fireEvent.change(select, { target: { value: 'openai' } });

    await waitFor(() => {
      expect(screen.getByText('GPT-4o')).toBeInTheDocument();
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

    fireEvent.click(screen.getByText('Claude 4'));

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
      expect(screen.getByText('GPT-4o')).toBeInTheDocument();
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
      expect(screen.getByText('GPT-4o')).toBeInTheDocument();
    });

    const overlay = document.querySelector('.modal-overlay');
    fireEvent.click(overlay!);

    await waitFor(() => {
      expect(screen.queryByText('GPT-4o Mini')).not.toBeInTheDocument();
    });
  });
});

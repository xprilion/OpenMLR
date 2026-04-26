import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { InputArea } from '../components/InputArea';
import type { Mode } from '../components/InputArea';

function defaultProps(overrides: Partial<React.ComponentProps<typeof InputArea>> = {}) {
  return {
    disabled: false,
    mode: 'plan' as Mode,
    onModeChange: vi.fn(),
    onSend: vi.fn(),
    onStop: vi.fn(),
    text: '',
    onTextChange: vi.fn(),
    ...overrides,
  };
}

describe('InputArea', () => {
  it('renders mode toggle button showing P in plan mode', () => {
    render(<InputArea {...defaultProps()} />);
    const toggle = screen.getByText('P');
    expect(toggle).toBeInTheDocument();
    expect(toggle).toHaveClass('mode-plan');
  });

  it('renders mode toggle button showing E in execute mode', () => {
    render(<InputArea {...defaultProps({ mode: 'execute' })} />);
    const toggle = screen.getByText('E');
    expect(toggle).toBeInTheDocument();
    expect(toggle).toHaveClass('mode-execute');
  });

  it('clicking toggle switches mode', () => {
    const onModeChange = vi.fn();
    render(<InputArea {...defaultProps({ mode: 'plan', onModeChange })} />);
    fireEvent.click(screen.getByText('P'));
    expect(onModeChange).toHaveBeenCalledWith('execute');
  });

  it('send button click calls onSend with text and mode', () => {
    const onSend = vi.fn();
    const onTextChange = vi.fn();
    render(
      <InputArea
        {...defaultProps({ text: 'hello', onSend, onTextChange })}
      />,
    );
    const sendBtn = screen.getByRole('button', { name: '↑' });
    fireEvent.click(sendBtn);
    expect(onSend).toHaveBeenCalledWith('hello', 'plan');
    expect(onTextChange).toHaveBeenCalledWith('');
  });

  it('enter key submits', () => {
    const onSend = vi.fn();
    render(<InputArea {...defaultProps({ text: 'msg', onSend })} />);
    const textarea = screen.getByRole('textbox');
    fireEvent.keyDown(textarea, { key: 'Enter' });
    expect(onSend).toHaveBeenCalledOnce();
  });

  it('shift+enter does not submit', () => {
    const onSend = vi.fn();
    render(<InputArea {...defaultProps({ text: 'msg', onSend })} />);
    const textarea = screen.getByRole('textbox');
    fireEvent.keyDown(textarea, { key: 'Enter', shiftKey: true });
    expect(onSend).not.toHaveBeenCalled();
  });

  it('input is disabled when disabled=true', () => {
    render(<InputArea {...defaultProps({ disabled: true })} />);
    const textarea = screen.getByRole('textbox');
    expect(textarea).toBeDisabled();
  });

  it('stop button appears when showStop is true', () => {
    const onStop = vi.fn();
    render(<InputArea {...defaultProps({ disabled: true, showStop: true, onStop })} />);
    const stopBtn = screen.getByTitle('Stop');
    expect(stopBtn).toBeInTheDocument();
    fireEvent.click(stopBtn);
    expect(onStop).toHaveBeenCalledOnce();
  });

  it('empty text disables send button', () => {
    render(<InputArea {...defaultProps({ text: '' })} />);
    const sendBtn = screen.getByRole('button', { name: '↑' });
    expect(sendBtn).toBeDisabled();
  });

  it('keyboard shortcut Cmd+B switches to plan', () => {
    const onModeChange = vi.fn();
    render(<InputArea {...defaultProps({ mode: 'execute', onModeChange })} />);
    fireEvent.keyDown(window, { key: 'b', metaKey: true });
    expect(onModeChange).toHaveBeenCalledWith('plan');
  });

  it('keyboard shortcut Cmd+E switches to execute', () => {
    const onModeChange = vi.fn();
    render(<InputArea {...defaultProps({ mode: 'plan', onModeChange })} />);
    fireEvent.keyDown(window, { key: 'e', metaKey: true });
    expect(onModeChange).toHaveBeenCalledWith('execute');
  });
});

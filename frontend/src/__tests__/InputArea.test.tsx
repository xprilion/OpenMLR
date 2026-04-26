import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { InputArea } from '../components/InputArea';
import type { Mode } from '../components/InputArea';

function defaultProps(overrides: Partial<React.ComponentProps<typeof InputArea>> = {}) {
  return {
    disabled: false,
    mode: 'general' as Mode,
    onModeChange: vi.fn(),
    onSend: vi.fn(),
    onStop: vi.fn(),
    text: '',
    onTextChange: vi.fn(),
    ...overrides,
  };
}

describe('InputArea', () => {
  it('renders mode buttons (Plan, Research, Write, General)', () => {
    render(<InputArea {...defaultProps()} />);
    expect(screen.getByText('Plan')).toBeInTheDocument();
    expect(screen.getByText('Research')).toBeInTheDocument();
    expect(screen.getByText('Write')).toBeInTheDocument();
    expect(screen.getByText('General')).toBeInTheDocument();
  });

  it('active mode button has active class', () => {
    render(<InputArea {...defaultProps({ mode: 'research' })} />);
    // The button with title="Research" should have the active class
    const researchBtn = screen.getByTitle('Research');
    expect(researchBtn).toHaveClass('active');

    // Other buttons should not have active class
    const planBtn = screen.getByTitle('Plan');
    expect(planBtn).not.toHaveClass('active');
  });

  it('clicking mode button calls onModeChange', () => {
    const onModeChange = vi.fn();
    render(<InputArea {...defaultProps({ onModeChange })} />);
    fireEvent.click(screen.getByTitle('Write'));
    expect(onModeChange).toHaveBeenCalledWith('write');
  });

  it('send button click calls onSend with text and mode', () => {
    const onSend = vi.fn();
    const onTextChange = vi.fn();
    render(
      <InputArea
        {...defaultProps({
          text: 'Hello there',
          mode: 'plan',
          onSend,
          onTextChange,
        })}
      />,
    );
    const sendBtn = screen.getByRole('button', { name: '↑' });
    fireEvent.click(sendBtn);
    expect(onSend).toHaveBeenCalledWith('Hello there', 'plan');
    expect(onTextChange).toHaveBeenCalledWith('');
  });

  it('Enter key submits (without shift)', () => {
    const onSend = vi.fn();
    const onTextChange = vi.fn();
    render(
      <InputArea
        {...defaultProps({
          text: 'Enter submit test',
          onSend,
          onTextChange,
        })}
      />,
    );
    const textarea = screen.getByRole('textbox');
    fireEvent.keyDown(textarea, { key: 'Enter', shiftKey: false });
    expect(onSend).toHaveBeenCalledWith('Enter submit test', 'general');
  });

  it('Shift+Enter does not submit', () => {
    const onSend = vi.fn();
    render(
      <InputArea
        {...defaultProps({
          text: 'Shift enter test',
          onSend,
        })}
      />,
    );
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
});

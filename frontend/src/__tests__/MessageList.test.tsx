import { describe, it, expect, vi, beforeAll } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MessageList } from '../components/MessageList';
import type { Message } from '../types';

// jsdom doesn't implement scrollIntoView
beforeAll(() => {
  Element.prototype.scrollIntoView = vi.fn();
});

// Helper to build a Message with sensible defaults
function msg(overrides: Partial<Message> & Pick<Message, 'id' | 'role' | 'content'>): Message {
  return { streaming: false, ...overrides };
}

describe('MessageList', () => {
  it('renders user message with content', () => {
    const messages: Message[] = [
      msg({ id: 'u1', role: 'user', content: 'Hello world' }),
    ];
    render(<MessageList messages={messages} />);
    expect(screen.getByText('Hello world')).toBeInTheDocument();
  });

  it('renders user message with mode badge when metadata.tool is set', () => {
    const messages: Message[] = [
      msg({
        id: 'u2',
        role: 'user',
        content: 'Plan my project',
        metadata: { tool: 'plan' },
      }),
    ];
    render(<MessageList messages={messages} />);
    expect(screen.getByText('plan')).toBeInTheDocument();
    // Check that the badge has proper styling (Tailwind uses text-[10px] for the badge)
    const badge = screen.getByText('plan');
    expect(badge.className).toContain('uppercase');
    expect(screen.getByText('Plan my project')).toBeInTheDocument();
  });

  it('renders assistant message with markdown', () => {
    const messages: Message[] = [
      msg({ id: 'a1', role: 'assistant', content: 'Some **bold** text' }),
    ];
    render(<MessageList messages={messages} />);
    expect(screen.getByText('bold')).toBeInTheDocument();
    expect(screen.getByText(/Some/)).toBeInTheDocument();
  });

  it('renders assistant streaming message with block cursor', () => {
    const messages: Message[] = [
      msg({ id: 'a2', role: 'assistant', content: 'Streaming now', streaming: true }),
    ];
    render(<MessageList messages={messages} />);
    // The block cursor character \u258C should be appended
    expect(screen.getByText(/Streaming now\u258C/)).toBeInTheDocument();
  });

  it('renders tool call row with tool name and args', () => {
    const messages: Message[] = [
      msg({
        id: 't1',
        role: 'tool',
        content: '',
        metadata: {
          tool: 'web_search',
          args: 'query="transformers"',
          output: 'Found 10 results',
          outputSuccess: true,
        },
      }),
    ];
    render(<MessageList messages={messages} />);
    expect(screen.getByText('web_search')).toBeInTheDocument();
    expect(screen.getByText('query="transformers"')).toBeInTheDocument();
  });

  it('renders sub-agent block with label and description', () => {
    const messages: Message[] = [
      msg({
        id: 'sa1',
        role: 'tool',
        content: '',
        metadata: {
          isSubAgent: true,
          agentType: 'research',
          args: 'Find related work on attention mechanisms',
          children: [],
          toolCount: 3,
          output: 'Done',
        },
      }),
    ];
    render(<MessageList messages={messages} />);
    expect(screen.getByText('Research Task')).toBeInTheDocument();
    expect(screen.getByText('Find related work on attention mechanisms')).toBeInTheDocument();
  });

  it('renders thinking indicator for ::thinking:: system message', () => {
    const messages: Message[] = [
      msg({ id: 's1', role: 'system', content: '::thinking::' }),
    ];
    render(<MessageList messages={messages} />);
    expect(screen.getByText('Thinking...')).toBeInTheDocument();
  });

  it('renders regular system message text', () => {
    const messages: Message[] = [
      msg({ id: 's2', role: 'system', content: 'Context compacted' }),
    ];
    render(<MessageList messages={messages} />);
    expect(screen.getByText('Context compacted')).toBeInTheDocument();
  });

  it('renders error message with error styling', () => {
    const messages: Message[] = [
      msg({ id: 'e1', role: 'error', content: 'Something went wrong' }),
    ];
    render(<MessageList messages={messages} />);
    const el = screen.getByText('Something went wrong');
    expect(el).toBeInTheDocument();
    // Check that the parent div has error styling (Tailwind uses bg-error-bg and text-error)
    const errorDiv = el.closest('div');
    expect(errorDiv?.className).toContain('text-error');
  });

  it('tool call row toggles output on click', () => {
    const outputText = 'search result output content';
    const messages: Message[] = [
      msg({
        id: 't2',
        role: 'tool',
        content: '',
        metadata: {
          tool: 'read_file',
          args: 'path/to/file.ts',
          output: outputText,
          outputSuccess: true,
        },
      }),
    ];
    const { container } = render(<MessageList messages={messages} />);

    // Output should NOT be visible initially (not expanded)
    expect(screen.queryByText(outputText)).not.toBeInTheDocument();

    // Click to expand - find the button with the tool name
    const button = container.querySelector('button');
    expect(button).toBeTruthy();
    fireEvent.click(button!);

    // Output should now be visible
    expect(screen.getByText(outputText)).toBeInTheDocument();

    // Click again to collapse
    fireEvent.click(button!);
    expect(screen.queryByText(outputText)).not.toBeInTheDocument();
  });
});

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ApprovalModal } from '../components/ApprovalModal';
import { api } from '../api';

vi.mock('../api', () => ({
  api: {
    sendApproval: vi.fn(),
  },
}));

describe('ApprovalModal', () => {
  it('renders header', () => {
    vi.mocked(api.sendApproval).mockResolvedValue({});
    const event = {
      data: {
        tool_calls: [{ id: 'tc1', name: 'bash', arguments: { cmd: 'ls' } }],
      },
    };
    render(<ApprovalModal event={event} onClose={vi.fn()} />);
    expect(screen.getByText('Approve Tool Calls')).toBeInTheDocument();
  });

  it('renders tool names', () => {
    vi.mocked(api.sendApproval).mockResolvedValue({});
    const event = {
      data: {
        tool_calls: [
          { id: 'tc1', name: 'bash', arguments: { cmd: 'ls' } },
          { id: 'tc2', name: 'write', arguments: { path: '/tmp/t', content: 'hi' } },
        ],
      },
    };
    render(<ApprovalModal event={event} onClose={vi.fn()} />);
    expect(screen.getByText('bash')).toBeInTheDocument();
    expect(screen.getByText('write')).toBeInTheDocument();
  });

  it('renders approve and reject buttons', () => {
    vi.mocked(api.sendApproval).mockResolvedValue({});
    const event = {
      data: {
        tool_calls: [{ id: 'tc1', name: 'test', arguments: {} }],
      },
    };
    render(<ApprovalModal event={event} onClose={vi.fn()} />);
    expect(screen.getByRole('button', { name: 'Approve' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Reject' })).toBeInTheDocument();
  });

  it('displays tool args', () => {
    vi.mocked(api.sendApproval).mockResolvedValue({});
    const event = {
      data: {
        tool_calls: [{ id: 'tc1', name: 'run', arguments: { query: 'test', count: 5 } }],
      },
    };
    render(<ApprovalModal event={event} onClose={vi.fn()} />);
    expect(screen.getByText(/query/)).toBeInTheDocument();
  });

  it('handles string arguments', () => {
    vi.mocked(api.sendApproval).mockResolvedValue({});
    const event = {
      data: {
        tool_calls: [{ id: 'tc1', name: 'echo', arguments: 'hello world' }],
      },
    };
    render(<ApprovalModal event={event} onClose={vi.fn()} />);
    expect(screen.getByText('hello world')).toBeInTheDocument();
  });

  it('handles tools field as fallback', () => {
    vi.mocked(api.sendApproval).mockResolvedValue({});
    const event = {
      data: {
        tools: [{ id: 'tc1', name: 'fallback_tool', arguments: {} }],
      },
    };
    render(<ApprovalModal event={event} onClose={vi.fn()} />);
    expect(screen.getByText('fallback_tool')).toBeInTheDocument();
  });

  it('calls sendApproval with approved', async () => {
    const mockSend = vi.mocked(api.sendApproval).mockResolvedValue({});
    const onClose = vi.fn();
    const event = {
      data: {
        tool_calls: [{ id: 'tc1', name: 'bash', arguments: {} }],
      },
    };
    render(<ApprovalModal event={event} onClose={onClose} />);

    fireEvent.click(screen.getByRole('button', { name: 'Approve' }));
    expect(mockSend).toHaveBeenCalledWith({ tc1: true });
  });

  it('calls sendApproval with rejected', () => {
    const mockSend = vi.mocked(api.sendApproval).mockResolvedValue({});
    const onClose = vi.fn();
    const event = {
      data: {
        tool_calls: [{ id: 'tc1', name: 'bash', arguments: {} }],
      },
    };
    render(<ApprovalModal event={event} onClose={onClose} />);

    fireEvent.click(screen.getByRole('button', { name: 'Reject' }));
    expect(mockSend).toHaveBeenCalledWith({ tc1: false });
  });

  it('approves multiple tool calls', () => {
    const mockSend = vi.mocked(api.sendApproval).mockResolvedValue({});
    const event = {
      data: {
        tool_calls: [
          { id: 'a', name: 'one', arguments: {} },
          { id: 'b', name: 'two', arguments: {} },
          { id: 'c', name: 'three', arguments: {} },
        ],
      },
    };
    render(<ApprovalModal event={event} onClose={vi.fn()} />);
    fireEvent.click(screen.getByText('Approve'));
    expect(mockSend).toHaveBeenCalledWith({ a: true, b: true, c: true });
  });
});

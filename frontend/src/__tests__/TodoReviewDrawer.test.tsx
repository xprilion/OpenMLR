import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { TodoReviewDrawer } from '../components/TodoReviewDrawer';

vi.mock('../api', () => ({
  api: {
    submitTodoApproval: vi.fn().mockResolvedValue({ ok: true }),
  },
}));

describe('TodoReviewDrawer', () => {
  const basePayload = {
    change_type: 'create' as const,
    proposed_tasks: [
      { title: 'Read papers', status: 'pending' },
      { title: 'Train model', status: 'pending' },
      { title: 'Write report', status: 'pending' },
    ],
    current_tasks: [] as Array<{ title: string; status: string }>,
  };

  it('renders header with correct title for create', () => {
    render(
      <TodoReviewDrawer
        payload={basePayload}
        onDone={vi.fn()}
        onClose={vi.fn()}
      />
    );
    expect(screen.getByText('Review Proposed Plan')).toBeInTheDocument();
  });

  it('renders header with correct title for add', () => {
    render(
      <TodoReviewDrawer
        payload={{ ...basePayload, change_type: 'add' }}
        onDone={vi.fn()}
        onClose={vi.fn()}
      />
    );
    expect(screen.getByText('Review Task Addition')).toBeInTheDocument();
  });

  it('renders proposed tasks', () => {
    render(
      <TodoReviewDrawer
        payload={basePayload}
        onDone={vi.fn()}
        onClose={vi.fn()}
      />
    );
    expect(screen.getByText('Read papers')).toBeInTheDocument();
    expect(screen.getByText('Train model')).toBeInTheDocument();
    expect(screen.getByText('Write report')).toBeInTheDocument();
  });

  it('shows task count', () => {
    render(
      <TodoReviewDrawer
        payload={basePayload}
        onDone={vi.fn()}
        onClose={vi.fn()}
      />
    );
    expect(screen.getByText('3 tasks')).toBeInTheDocument();
  });

  it('renders approve and reject buttons', () => {
    render(
      <TodoReviewDrawer
        payload={basePayload}
        onDone={vi.fn()}
        onClose={vi.fn()}
      />
    );
    expect(screen.getByText('Approve')).toBeInTheDocument();
    expect(screen.getByText('Reject')).toBeInTheDocument();
  });

  it('marks new tasks with "new" badge', () => {
    const payload = {
      change_type: 'add' as const,
      proposed_tasks: [
        { title: 'Existing task', status: 'completed' },
        { title: 'New task', status: 'pending' },
      ],
      current_tasks: [{ title: 'Existing task', status: 'completed' }],
    };
    render(
      <TodoReviewDrawer
        payload={payload}
        onDone={vi.fn()}
        onClose={vi.fn()}
      />
    );
    const badges = screen.getAllByText('new');
    expect(badges.length).toBe(1); // only the new task has a badge
  });

  it('renders current tasks column when they exist', () => {
    const payload = {
      ...basePayload,
      change_type: 'add' as const,
      current_tasks: [{ title: 'Old task', status: 'in_progress' }],
    };
    render(
      <TodoReviewDrawer
        payload={payload}
        onDone={vi.fn()}
        onClose={vi.fn()}
      />
    );
    expect(screen.getByText('Current Plan')).toBeInTheDocument();
    expect(screen.getByText('Old task')).toBeInTheDocument();
  });

  it('calls onClose when X button clicked', () => {
    const onClose = vi.fn();
    render(
      <TodoReviewDrawer
        payload={basePayload}
        onDone={vi.fn()}
        onClose={onClose}
      />
    );
    // Find the X button by looking for all buttons and finding one with the X icon
    const allButtons = screen.getAllByRole('button');
    // The X close button is in the header area and contains an SVG
    const closeButton = allButtons.find((btn) => {
      const svg = btn.querySelector('svg');
      return svg && btn.closest('.border-b') !== null;
    });
    if (closeButton) {
      fireEvent.click(closeButton);
    }
    expect(onClose).toHaveBeenCalled();
  });

  it('calls submitTodoApproval with approved on approve click', async () => {
    const { api } = await import('../api');
    const onDone = vi.fn();
    render(
      <TodoReviewDrawer
        payload={basePayload}
        onDone={onDone}
        onClose={vi.fn()}
      />
    );

    fireEvent.click(screen.getByText('Approve'));

    // Wait for async handler
    await vi.waitFor(() => {
      expect(api.submitTodoApproval).toHaveBeenCalledWith(true, expect.any(Array));
    });
  });

  it('calls submitTodoApproval with rejected on reject click', async () => {
    const { api } = await import('../api');
    const onDone = vi.fn();
    render(
      <TodoReviewDrawer
        payload={basePayload}
        onDone={onDone}
        onClose={vi.fn()}
      />
    );

    fireEvent.click(screen.getByText('Reject'));

    await vi.waitFor(() => {
      expect(api.submitTodoApproval).toHaveBeenCalledWith(false);
    });
  });

  it('has an add task input', () => {
    render(
      <TodoReviewDrawer
        payload={basePayload}
        onDone={vi.fn()}
        onClose={vi.fn()}
      />
    );
    expect(screen.getByPlaceholderText('Add a task...')).toBeInTheDocument();
  });

  it('shows edit hint text', () => {
    render(
      <TodoReviewDrawer
        payload={basePayload}
        onDone={vi.fn()}
        onClose={vi.fn()}
      />
    );
    expect(screen.getByText(/You can edit tasks before approving/)).toBeInTheDocument();
  });
});

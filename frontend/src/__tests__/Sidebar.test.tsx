import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { Sidebar } from '../components/Sidebar';
import type { Conversation, User } from '../types';

vi.mock('../api', () => ({
  setToken: vi.fn(),
}));

const mockNavigate = vi.fn();
vi.mock('react-router-dom', async (importOriginal) => {
  const actual = await importOriginal() as any;
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

const mockUser: User = { id: 1, username: 'tester', display_name: 'Test User' };

const mockConversations: Conversation[] = [
  {
    id: 1,
    uuid: 'conv-1',
    title: 'First conversation',
    model: 'gpt-4o',
    mode: 'general',
    user_message_count: 3,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
  {
    id: 2,
    uuid: 'conv-2',
    title: 'Research project',
    model: 'claude-4',
    mode: 'research',
    user_message_count: 10,
    created_at: new Date(Date.now() - 86400000 * 3).toISOString(),
    updated_at: new Date(Date.now() - 86400000 * 3).toISOString(),
  },
];

describe('Sidebar', () => {
  it('renders new chat button', () => {
    render(
      <MemoryRouter>
        <Sidebar
          conversations={mockConversations}
          currentUuid={null}
          user={mockUser}
          convStatuses={{}}
          onSwitch={vi.fn()}
          onNew={vi.fn()}
          onDelete={vi.fn()}
          onAction={vi.fn()}
        />
      </MemoryRouter>
    );
    expect(screen.getByText('+ New Chat')).toBeInTheDocument();
  });

  it('renders conversation titles', () => {
    render(
      <MemoryRouter>
        <Sidebar
          conversations={mockConversations}
          currentUuid={null}
          user={mockUser}
          convStatuses={{}}
          onSwitch={vi.fn()}
          onNew={vi.fn()}
          onDelete={vi.fn()}
          onAction={vi.fn()}
        />
      </MemoryRouter>
    );
    expect(screen.getByText('First conversation')).toBeInTheDocument();
    expect(screen.getByText('Research project')).toBeInTheDocument();
  });

  it('highlights current conversation', () => {
    render(
      <MemoryRouter>
        <Sidebar
          conversations={mockConversations}
          currentUuid="conv-1"
          user={mockUser}
          convStatuses={{}}
          onSwitch={vi.fn()}
          onNew={vi.fn()}
          onDelete={vi.fn()}
          onAction={vi.fn()}
        />
      </MemoryRouter>
    );
    const items = document.querySelectorAll('.conversation-item');
    expect(items[0].classList.contains('active')).toBe(true);
  });

  it('calls onSwitch when conversation clicked', () => {
    const onSwitch = vi.fn();
    render(
      <MemoryRouter>
        <Sidebar
          conversations={mockConversations}
          currentUuid={null}
          user={mockUser}
          convStatuses={{}}
          onSwitch={onSwitch}
          onNew={vi.fn()}
          onDelete={vi.fn()}
          onAction={vi.fn()}
        />
      </MemoryRouter>
    );
    fireEvent.click(screen.getByText('First conversation'));
    expect(onSwitch).toHaveBeenCalledWith('conv-1');
  });

  it('shows empty state when no conversations', () => {
    render(
      <MemoryRouter>
        <Sidebar
          conversations={[]}
          currentUuid={null}
          user={mockUser}
          convStatuses={{}}
          onSwitch={vi.fn()}
          onNew={vi.fn()}
          onDelete={vi.fn()}
          onAction={vi.fn()}
        />
      </MemoryRouter>
    );
    expect(screen.getByText('No conversations yet')).toBeInTheDocument();
  });

  it('shows user display name', () => {
    render(
      <MemoryRouter>
        <Sidebar
          conversations={[]}
          currentUuid={null}
          user={mockUser}
          convStatuses={{}}
          onSwitch={vi.fn()}
          onNew={vi.fn()}
          onDelete={vi.fn()}
          onAction={vi.fn()}
        />
      </MemoryRouter>
    );
    expect(screen.getByText('Test User')).toBeInTheDocument();
  });

  it('renders action buttons', () => {
    render(
      <MemoryRouter>
        <Sidebar
          conversations={mockConversations}
          currentUuid={null}
          user={mockUser}
          convStatuses={{}}
          onSwitch={vi.fn()}
          onNew={vi.fn()}
          onDelete={vi.fn()}
          onAction={vi.fn()}
        />
      </MemoryRouter>
    );
    expect(screen.getByText(/Undo/)).toBeInTheDocument();
    expect(screen.getByText(/Compact/)).toBeInTheDocument();
  });

  it('calls onAction for undo', () => {
    const onAction = vi.fn();
    render(
      <MemoryRouter>
        <Sidebar
          conversations={mockConversations}
          currentUuid={null}
          user={mockUser}
          convStatuses={{}}
          onSwitch={vi.fn()}
          onNew={vi.fn()}
          onDelete={vi.fn()}
          onAction={onAction}
        />
      </MemoryRouter>
    );
    fireEvent.click(screen.getByText(/Undo/));
    expect(onAction).toHaveBeenCalledWith('undo');
  });

  it('calls onAction for compact', () => {
    const onAction = vi.fn();
    render(
      <MemoryRouter>
        <Sidebar
          conversations={mockConversations}
          currentUuid={null}
          user={mockUser}
          convStatuses={{}}
          onSwitch={vi.fn()}
          onNew={vi.fn()}
          onDelete={vi.fn()}
          onAction={onAction}
        />
      </MemoryRouter>
    );
    fireEvent.click(screen.getByText(/Compact/));
    expect(onAction).toHaveBeenCalledWith('compact');
  });

  it('filters conversations by search', () => {
    render(
      <MemoryRouter>
        <Sidebar
          conversations={mockConversations}
          currentUuid={null}
          user={mockUser}
          convStatuses={{}}
          onSwitch={vi.fn()}
          onNew={vi.fn()}
          onDelete={vi.fn()}
          onAction={vi.fn()}
        />
      </MemoryRouter>
    );
    const searchInput = screen.getByPlaceholderText('Search...');
    fireEvent.change(searchInput, { target: { value: 'Research' } });
    expect(screen.getByText('Research project')).toBeInTheDocument();
    expect(screen.queryByText('First conversation')).not.toBeInTheDocument();
  });
});

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

const defaultProps = {
  conversations: mockConversations,
  currentUuid: null as string | null,
  user: mockUser,
  convStatuses: {} as Record<string, any>,
  onSwitch: vi.fn(),
  onNew: vi.fn(),
  onDelete: vi.fn(),
};

describe('Sidebar', () => {
  it('renders new chat button', () => {
    render(
      <MemoryRouter>
        <Sidebar {...defaultProps} />
      </MemoryRouter>
    );
    expect(screen.getByText('New Chat')).toBeInTheDocument();
  });

  it('renders conversation titles', () => {
    render(
      <MemoryRouter>
        <Sidebar {...defaultProps} />
      </MemoryRouter>
    );
    expect(screen.getByText('First conversation')).toBeInTheDocument();
    expect(screen.getByText('Research project')).toBeInTheDocument();
  });

  it('highlights current conversation with bg-primary/10 class', () => {
    render(
      <MemoryRouter>
        <Sidebar {...defaultProps} currentUuid="conv-1" />
      </MemoryRouter>
    );
    const convItem = screen.getByText('First conversation').closest('div');
    expect(convItem?.className).toContain('bg-primary/10');
  });

  it('calls onSwitch when conversation clicked', () => {
    const onSwitch = vi.fn();
    render(
      <MemoryRouter>
        <Sidebar {...defaultProps} onSwitch={onSwitch} />
      </MemoryRouter>
    );
    // The conversation item uses an overlay button with aria-label
    fireEvent.click(screen.getByRole('button', { name: /Switch to conversation: First conversation/i }));
    expect(onSwitch).toHaveBeenCalledWith('conv-1');
  });

  it('shows empty state when no conversations', () => {
    render(
      <MemoryRouter>
        <Sidebar {...defaultProps} conversations={[]} />
      </MemoryRouter>
    );
    expect(screen.getByText('No conversations yet')).toBeInTheDocument();
  });

  it('shows user display name', () => {
    render(
      <MemoryRouter>
        <Sidebar {...defaultProps} conversations={[]} />
      </MemoryRouter>
    );
    expect(screen.getByText('Test User')).toBeInTheDocument();
  });

  it('renders settings and sign out buttons', () => {
    render(
      <MemoryRouter>
        <Sidebar {...defaultProps} />
      </MemoryRouter>
    );
    expect(screen.getByTitle('Settings')).toBeInTheDocument();
    expect(screen.getByTitle('Sign out')).toBeInTheDocument();
  });

  it('filters conversations by search', () => {
    render(
      <MemoryRouter>
        <Sidebar {...defaultProps} />
      </MemoryRouter>
    );
    const searchInput = screen.getByPlaceholderText('Search...');
    fireEvent.change(searchInput, { target: { value: 'Research' } });
    expect(screen.getByText('Research project')).toBeInTheDocument();
    expect(screen.queryByText('First conversation')).not.toBeInTheDocument();
  });

  it('calls onNew when new chat button clicked', () => {
    const onNew = vi.fn();
    render(
      <MemoryRouter>
        <Sidebar {...defaultProps} onNew={onNew} />
      </MemoryRouter>
    );
    fireEvent.click(screen.getByText('New Chat'));
    expect(onNew).toHaveBeenCalled();
  });

});

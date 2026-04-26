import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { AuthGuard } from '../components/AuthGuard';
import { api, setToken } from '../api';

vi.mock('../api', () => ({
  api: {
    getMe: vi.fn(),
  },
  setToken: vi.fn(),
}));

const getItemMock = vi.fn();
const setItemMock = vi.fn();
const removeItemMock = vi.fn();

Object.defineProperty(window, 'localStorage', {
  value: {
    getItem: getItemMock,
    setItem: setItemMock,
    removeItem: removeItemMock,
  },
  writable: true,
});

describe('AuthGuard', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    getItemMock.mockReturnValue(null);
  });

  it('shows loading when checking token', () => {
    getItemMock.mockReturnValue('existing-token');
    vi.mocked(api.getMe).mockImplementation(() => new Promise(() => {}));

    render(
      <MemoryRouter initialEntries={['/']}>
        <AuthGuard onAuth={vi.fn()} user={null} />
      </MemoryRouter>
    );

    expect(screen.getByText('Loading...')).toBeInTheDocument();
  });

  it('redirects to /login when no user and no token', async () => {
    render(
      <MemoryRouter initialEntries={['/']}>
        <AuthGuard onAuth={vi.fn()} user={null} />
      </MemoryRouter>
    );

    await waitFor(() => {
      // Navigate should redirect to /login
      expect(screen.queryByText('Loading...')).not.toBeInTheDocument();
    });
  });

  it('authenticates with valid token', async () => {
    getItemMock.mockReturnValue('valid-token');
    const user = { id: 1, username: 'test', display_name: 'Test' };
    vi.mocked(api.getMe).mockResolvedValue(user);
    const onAuth = vi.fn();

    render(
      <MemoryRouter initialEntries={['/']}>
        <AuthGuard onAuth={onAuth} user={null} />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(onAuth).toHaveBeenCalledWith(user);
      expect(screen.queryByText('Loading...')).not.toBeInTheDocument();
    });
  });

  it('clears token on invalid token', async () => {
    getItemMock.mockReturnValue('invalid-token');
    vi.mocked(api.getMe).mockRejectedValue(new Error('Invalid'));
    const onAuth = vi.fn();

    render(
      <MemoryRouter initialEntries={['/']}>
        <AuthGuard onAuth={onAuth} user={null} />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(setToken).toHaveBeenCalledWith(null);
      expect(onAuth).not.toHaveBeenCalled();
    });
  });

  it('skips check when user already passed in', () => {
    const user = { id: 1, username: 'test', display_name: 'Test' };
    vi.mocked(api.getMe).mockResolvedValue(user);

    render(
      <MemoryRouter initialEntries={['/']}>
        <AuthGuard onAuth={vi.fn()} user={user} />
      </MemoryRouter>
    );

    expect(api.getMe).not.toHaveBeenCalled();
  });
});

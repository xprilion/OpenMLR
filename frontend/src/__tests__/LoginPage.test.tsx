import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { LoginPage } from '../components/LoginPage';
import { api, setToken } from '../api';

vi.mock('../api', () => ({
  api: {
    checkSetup: vi.fn(),
    register: vi.fn(),
    login: vi.fn(),
  },
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

function renderLoginPage(onAuth = vi.fn()) {
  return render(
    <MemoryRouter>
      <LoginPage onAuth={onAuth} />
    </MemoryRouter>
  );
}

describe('LoginPage', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(api.checkSetup).mockResolvedValue({ has_users: true });
  });

  it('renders sign in form', async () => {
    renderLoginPage();
    await waitFor(() => {
      expect(screen.getByText('OpenMLR')).toBeInTheDocument();
    });
    expect(screen.getByPlaceholderText('Username')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('Password')).toBeInTheDocument();
  });

  it('shows login and register tabs when users exist', async () => {
    renderLoginPage();
    await waitFor(() => {
      const tabs = screen.getAllByRole('button');
      const tabTexts = tabs.map(t => t.textContent);
      expect(tabTexts).toContain('Sign In');
      expect(tabTexts).toContain('Register');
    });
  });

  it('switches to register mode', async () => {
    renderLoginPage();
    await waitFor(() => {
      expect(screen.getByText('Register')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('Register'));
    const createBtn = screen.getByText('Create Account');
    expect(createBtn).toBeInTheDocument();
    expect(screen.getByPlaceholderText('Display name (optional)')).toBeInTheDocument();
  });

  it('shows first-user notice when no users exist', async () => {
    vi.mocked(api.checkSetup).mockResolvedValue({ has_users: false });
    renderLoginPage();
    await waitFor(() => {
      expect(screen.getByText(/Create your account/)).toBeInTheDocument();
    });
  });

  it('handles login submission', async () => {
    const onAuth = vi.fn();
    vi.mocked(api.login).mockResolvedValue({
      access_token: 'test-token',
      user: { id: 1, username: 'testuser', display_name: 'Test User' },
    });

    renderLoginPage(onAuth);

    await waitFor(() => {
      expect(screen.getByPlaceholderText('Username')).toBeInTheDocument();
    });

    const user = userEvent.setup();
    await user.type(screen.getByPlaceholderText('Username'), 'testuser');
    await user.type(screen.getByPlaceholderText('Password'), 'password123');

    // Find the submit button by type="submit" attribute
    const submitButton = document.querySelector('button[type="submit"]') as HTMLElement;
    await user.click(submitButton);

    await waitFor(() => {
      expect(api.login).toHaveBeenCalledWith('testuser', 'password123');
      expect(setToken).toHaveBeenCalledWith('test-token');
      expect(onAuth).toHaveBeenCalledWith({ id: 1, username: 'testuser', display_name: 'Test User' });
      expect(mockNavigate).toHaveBeenCalledWith('/', { replace: true });
    });
  });

  it('handles register submission', async () => {
    const onAuth = vi.fn();
    vi.mocked(api.register).mockResolvedValue({
      access_token: 'reg-token',
      user: { id: 2, username: 'newuser', display_name: 'New' },
    });

    renderLoginPage(onAuth);

    await waitFor(() => {
      fireEvent.click(screen.getByText('Register'));
    });

    const user = userEvent.setup();
    await user.type(screen.getByPlaceholderText('Username'), 'newuser');
    await user.type(screen.getByPlaceholderText('Display name (optional)'), 'New');
    await user.type(screen.getByPlaceholderText('Password'), 'password123');
    await user.click(screen.getByRole('button', { name: 'Create Account' }));

    await waitFor(() => {
      expect(api.register).toHaveBeenCalledWith('newuser', 'password123', 'New');
      expect(setToken).toHaveBeenCalledWith('reg-token');
    });
  });

  it('displays error on auth failure', async () => {
    vi.mocked(api.login).mockRejectedValue(new Error('Invalid credentials'));

    renderLoginPage();

    await waitFor(() => {
      expect(screen.getByPlaceholderText('Username')).toBeInTheDocument();
    });

    const user = userEvent.setup();
    await user.type(screen.getByPlaceholderText('Username'), 'wrong');
    await user.type(screen.getByPlaceholderText('Password'), 'wrong');
    
    // Find the submit button by type="submit" attribute
    const submitButton = document.querySelector('button[type="submit"]') as HTMLElement;
    await user.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText('Invalid credentials')).toBeInTheDocument();
    });
  });

  it('displays generic error for unknown failures', async () => {
    vi.mocked(api.login).mockRejectedValue(new Error());

    renderLoginPage();

    await waitFor(() => {
      expect(screen.getByPlaceholderText('Username')).toBeInTheDocument();
    });

    const user = userEvent.setup();
    await user.type(screen.getByPlaceholderText('Username'), 'test');
    await user.type(screen.getByPlaceholderText('Password'), 'pass');
    
    // Find the submit button by type="submit" attribute
    const submitButton = document.querySelector('button[type="submit"]') as HTMLElement;
    await user.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText('Authentication failed')).toBeInTheDocument();
    });
  });

  it('clears error when switching modes', async () => {
    vi.mocked(api.register).mockRejectedValue(new Error('Username taken'));

    renderLoginPage();

    await waitFor(() => {
      fireEvent.click(screen.getByText('Register'));
    });

    // Fill required fields and submit register form
    const user = userEvent.setup();
    await user.type(screen.getByPlaceholderText('Username'), 'newuser');
    await user.type(screen.getByPlaceholderText('Password'), 'password');
    await user.click(screen.getByRole('button', { name: 'Create Account' }));

    await waitFor(() => {
      expect(screen.getByText('Username taken')).toBeInTheDocument();
    });

    // Switch back to Sign In - get all buttons and find the one in the tabs (not the submit)
    const signInButtons = screen.getAllByText('Sign In');
    // The tab button doesn't have type="submit"
    const tabButton = signInButtons.find(btn => btn.getAttribute('type') !== 'submit');
    fireEvent.click(tabButton!);
    await waitFor(() => {
      expect(screen.queryByText('Username taken')).not.toBeInTheDocument();
    });
  });

  it('disables submit button while loading', async () => {
    vi.mocked(api.login).mockImplementation(() => new Promise(() => {}));

    renderLoginPage();

    await waitFor(() => {
      expect(screen.getByPlaceholderText('Username')).toBeInTheDocument();
    });

    const user = userEvent.setup();
    await user.type(screen.getByPlaceholderText('Username'), 'test');
    await user.type(screen.getByPlaceholderText('Password'), 'pass');
    
    // Find the submit button by type="submit" attribute
    const submitButton = document.querySelector('button[type="submit"]') as HTMLElement;
    await user.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText('Please wait...')).toBeInTheDocument();
    });
  });
});

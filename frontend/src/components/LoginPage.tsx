import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { api, setToken } from '../api';
import type { User } from '../types';

interface Props {
  onAuth: (user: User) => void;
}

export function LoginPage({ onAuth }: Props) {
  const [mode, setMode] = useState<'login' | 'register'>('login');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [isFirstUser, setIsFirstUser] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    api.checkSetup()
      .then((data) => {
        if (!data.has_users) {
          setIsFirstUser(true);
          setMode('register');
        }
      })
      .catch(() => {});
  }, []);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      let data;
      if (mode === 'register') {
        data = await api.register(username, password, displayName || undefined);
      } else {
        data = await api.login(username, password);
      }
      setToken(data.access_token);
      onAuth(data.user);
      navigate('/', { replace: true });
    } catch (err: any) {
      setError(err.message || 'Authentication failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-page">
      <div className="login-card">
        <h1 className="login-logo">OpenMLR</h1>
        <p className="login-subtitle">ML Research Intern</p>

        {isFirstUser && (
          <div className="login-notice">
            Welcome. Create your account to get started.
          </div>
        )}

        {!isFirstUser && (
          <div className="login-tabs">
            <button
              className={`login-tab ${mode === 'login' ? 'active' : ''}`}
              onClick={() => { setMode('login'); setError(''); }}
            >
              Sign In
            </button>
            <button
              className={`login-tab ${mode === 'register' ? 'active' : ''}`}
              onClick={() => { setMode('register'); setError(''); }}
            >
              Register
            </button>
          </div>
        )}

        <form className="login-form" onSubmit={submit}>
          <input
            type="text"
            placeholder="Username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoFocus
            required
            minLength={3}
          />
          {mode === 'register' && (
            <input
              type="text"
              placeholder="Display name (optional)"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
            />
          )}
          <input
            type="password"
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            minLength={6}
          />

          {error && <div className="login-error">{error}</div>}

          <button type="submit" className="login-submit" disabled={loading}>
            {loading
              ? 'Please wait...'
              : mode === 'register'
              ? 'Create Account'
              : 'Sign In'}
          </button>
        </form>
      </div>
    </div>
  );
}

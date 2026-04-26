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
    <div className="min-h-screen bg-bg flex items-center justify-center p-6">
      <div className="w-full max-w-sm bg-surface rounded-2xl border border-border p-8 shadow-xl">
        <h1 className="text-2xl font-bold text-primary text-center mb-1">OpenMLR</h1>
        <p className="text-text-dim text-center mb-8">ML Research Intern</p>

        {isFirstUser && (
          <div className="bg-primary/10 border border-primary/30 rounded-lg p-4 mb-6 text-sm text-text text-center">
            Welcome. Create your account to get started.
          </div>
        )}

        {!isFirstUser && (
          <div className="flex rounded-lg bg-bg p-1 mb-6">
            <button
              className={`flex-1 py-2 px-4 rounded-md text-sm font-medium transition-all ${
                mode === 'login' 
                  ? 'bg-primary text-white' 
                  : 'text-text-dim hover:text-text'
              }`}
              onClick={() => { setMode('login'); setError(''); }}
            >
              Sign In
            </button>
            <button
              className={`flex-1 py-2 px-4 rounded-md text-sm font-medium transition-all ${
                mode === 'register' 
                  ? 'bg-primary text-white' 
                  : 'text-text-dim hover:text-text'
              }`}
              onClick={() => { setMode('register'); setError(''); }}
            >
              Register
            </button>
          </div>
        )}

        <form className="flex flex-col gap-4" onSubmit={submit}>
          <input
            type="text"
            className="w-full bg-bg border border-border rounded-lg px-4 py-3 text-text placeholder-text-dim focus:border-primary focus:outline-none transition-colors"
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
              className="w-full bg-bg border border-border rounded-lg px-4 py-3 text-text placeholder-text-dim focus:border-primary focus:outline-none transition-colors"
              placeholder="Display name (optional)"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
            />
          )}
          
          <input
            type="password"
            className="w-full bg-bg border border-border rounded-lg px-4 py-3 text-text placeholder-text-dim focus:border-primary focus:outline-none transition-colors"
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            minLength={6}
          />

          {error && (
            <div className="text-error text-sm bg-error-bg rounded-lg p-3 text-center">
              {error}
            </div>
          )}

          <button 
            type="submit" 
            className="w-full py-3 bg-primary text-white rounded-lg font-semibold hover:bg-primary-hover transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            disabled={loading}
          >
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

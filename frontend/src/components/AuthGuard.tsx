import { useEffect, useState } from 'react';
import { Navigate, Outlet } from 'react-router-dom';
import { api, setToken } from '../api';
import type { User } from '../types';

interface Props {
  onAuth: (user: User) => void;
  user: User | null;
}

/**
 * Route guard: checks JWT, renders children if authed, redirects to /login otherwise.
 * Passes user to parent via onAuth callback on successful token validation.
 */
export function AuthGuard({ onAuth, user }: Props) {
  const [checking, setChecking] = useState(!user);

  useEffect(() => {
    if (user) { setChecking(false); return; }
    const token = localStorage.getItem('openmlr_token');
    if (!token) { setChecking(false); return; }

    api.getMe()
      .then((data) => { onAuth(data); setChecking(false); })
      .catch(() => { setToken(null); setChecking(false); });
  }, [user, onAuth]);

  if (checking) {
    return (
      <div className="flex flex-col h-screen bg-bg items-center justify-center">
        <div className="text-text-dim animate-pulse">Loading...</div>
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  return <Outlet />;
}

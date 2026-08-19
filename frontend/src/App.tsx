import { useState, useCallback } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { api } from './api';
import type { User, Project } from './types';
import { LoginPage } from './components/LoginPage';
import { AuthGuard } from './components/AuthGuard';
import { OnboardingModal } from './components/OnboardingModal';
import { SettingsPage } from './components/SettingsPage';
import { ProvidersSettings } from './components/settings/ProvidersSettings';
import { AgentSettings } from './components/settings/AgentSettings';
import { McpSettings } from './components/settings/McpSettings';
import { ComputeSettings } from './components/settings/ComputeSettings';
import { WritingSettings } from './components/settings/WritingSettings';
import { ProjectProvider } from './context/ProjectContext';
import { ComputeProvider } from './context/ComputeContext';
import { ChatProvider } from './context/ChatContext';
import { MainLayout } from './components/layout/MainLayout';

// ── Login wrapper ───────────────────────────────────────
function LoginRoute({ onAuth }: Readonly<{ onAuth: (u: User) => void }>) {
  return <LoginPage onAuth={onAuth} />;
}

// ── Main Authenticated Layout with Providers ────────────
function AuthenticatedApp({
  user,
  model,
  setModel,
}: Readonly<{
  user: User;
  model: string;
  setModel: (m: string) => void;
}>) {
  return (
    <ProjectProvider>
      <ComputeProvider>
        <ChatProvider setModel={setModel}>
          <MainLayout user={user} model={model} setModel={setModel} />
        </ChatProvider>
      </ComputeProvider>
    </ProjectProvider>
  );
}

// ── Root App with routing ───────────────────────────────
export default function App() {
  const [user, setUser] = useState<User | null>(null);
  const [model, setModel] = useState('');
  const [needsOnboarding, setNeedsOnboarding] = useState(false);

  const handleAuth = useCallback((u: User) => {
    setUser(u);
    api
      .getStatus()
      .then((s) => {
        if (s?.model) {
          setModel(s.model);
          setNeedsOnboarding(false);
        } else {
          setNeedsOnboarding(true);
        }
      })
      .catch(() => {});
  }, []);

  const handleOnboardingComplete = useCallback((selectedModel: string, project?: Project) => {
    setModel(selectedModel);
    setNeedsOnboarding(false);
    if (project) {
      window.location.reload();
    }
  }, []);

  return (
    <>
      {needsOnboarding && user && <OnboardingModal onComplete={handleOnboardingComplete} />}
      <Routes>
        {/* Public routes */}
        <Route path="/login" element={<LoginRoute onAuth={handleAuth} />} />

        {/* Protected routes */}
        <Route element={<AuthGuard onAuth={handleAuth} user={user} />}>
          <Route path="/:uuid?" element={<AuthenticatedApp user={user!} model={model} setModel={setModel} />} />
          <Route path="/settings" element={<SettingsPage />}>
            <Route index element={<Navigate to="providers" replace />} />
            <Route path="providers" element={<ProvidersSettings />} />
            <Route path="agent" element={<AgentSettings />} />
            <Route path="mcp" element={<McpSettings />} />
            <Route path="compute" element={<ComputeSettings />} />
            <Route path="writing" element={<WritingSettings />} />
          </Route>
        </Route>

        {/* Fallback */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </>
  );
}

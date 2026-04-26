import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { SettingsPage } from '../components/SettingsPage';

describe('SettingsPage', () => {
  function renderSettings(path = '/settings/agent') {
    return render(
      <MemoryRouter initialEntries={[path]}>
        <SettingsPage />
      </MemoryRouter>
    );
  }

  it('renders back link', () => {
    renderSettings();
    expect(screen.getByText(/Back to chat/)).toBeInTheDocument();
  });

  it('renders Settings title', () => {
    renderSettings();
    expect(screen.getByText('Settings')).toBeInTheDocument();
  });

  it('renders all nav links', () => {
    renderSettings();
    expect(screen.getByText('Providers')).toBeInTheDocument();
    expect(screen.getByText('Agent')).toBeInTheDocument();
    expect(screen.getByText('Sandbox')).toBeInTheDocument();
    expect(screen.getByText('Writing')).toBeInTheDocument();
  });

  it('highlights active nav link', () => {
    renderSettings('/settings/agent');
    const agentLink = screen.getByText('Agent');
    expect(agentLink.className).toContain('active');
  });

  it('does not highlight inactive links', () => {
    renderSettings('/settings/agent');
    const providers = screen.getByText('Providers');
    expect(providers.className).not.toContain('active');
  });
});

import { Link, Outlet, useLocation } from 'react-router-dom';

const navItems = [
  { path: '/settings/providers', label: 'Providers' },
  { path: '/settings/agent', label: 'Agent' },
  { path: '/settings/mcp', label: 'MCP Servers' },
  { path: '/settings/sandbox', label: 'Sandbox' },
  { path: '/settings/writing', label: 'Writing' },
];

export function SettingsPage() {
  const location = useLocation();

  return (
    <div className="settings-page">
      <nav className="settings-nav">
        <Link to="/" className="settings-nav-back">
          &larr; Back to chat
        </Link>
        <div className="settings-nav-title">Settings</div>
        <div className="settings-nav-links">
          {navItems.map((item) => (
            <Link
              key={item.path}
              to={item.path}
              className={`settings-nav-link${location.pathname === item.path ? ' active' : ''}`}
            >
              {item.label}
            </Link>
          ))}
        </div>
      </nav>
      <div className="settings-content">
        <Outlet />
      </div>
    </div>
  );
}

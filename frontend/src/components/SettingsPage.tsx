
import { Link, Outlet, useLocation } from 'react-router-dom';
import { ArrowLeft, Key, Bot, Server, Cpu, PenTool } from 'lucide-react';

const navItems = [
  { path: '/settings/providers', label: 'Providers', icon: Key },
  { path: '/settings/agent', label: 'Agent', icon: Bot },
  { path: '/settings/mcp', label: 'MCP Servers', icon: Server },
  { path: '/settings/compute', label: 'Compute', icon: Cpu },
  { path: '/settings/writing', label: 'Writing', icon: PenTool },
];

export function SettingsPage() {
  const location = useLocation();

  return (
    <div className="flex h-screen bg-bg">
      {/* Sidebar nav */}
      <nav className="w-60 min-w-[200px] bg-surface border-r border-border flex flex-col p-5 shrink-0">
        <Link 
          to="/" 
          className="flex items-center gap-2 text-text-dim hover:text-text mb-6 transition-colors"
        >
          <ArrowLeft size={16} />
          <span>Back to chat</span>
        </Link>
        
        <div className="text-xl font-bold text-text mb-6">Settings</div>
        
        <div className="flex flex-col gap-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <Link
                key={item.path}
                to={item.path}
                className={`flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm transition-all ${
                  location.pathname === item.path 
                    ? 'bg-primary text-white font-medium' 
                    : 'text-text-dim hover:bg-surface-hover hover:text-text'
                }`}
              >
                <Icon size={16} />
                {item.label}
              </Link>
            );
          })}
        </div>
      </nav>
      
      {/* Content */}
      <div className="flex-1 overflow-y-auto p-8">
        <div className="max-w-2xl">
          <Outlet />
        </div>
      </div>
    </div>
  );
}

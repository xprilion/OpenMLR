import { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { setToken } from '../api';
import type { Conversation, User } from '../types';
import { APP_VERSION } from '../version';
import { ConfirmDialog } from './ConfirmDialog';
import { 
  PanelLeftClose, 
  PanelLeftOpen, 
  Plus, 
  Search, 
  Settings, 
  LogOut, 
  Trash2,
  X,
} from 'lucide-react';

type ConvStatus = 'idle' | 'processing' | 'waiting_approval' | 'waiting_input';

interface Props {
  readonly conversations: readonly Conversation[];
  currentUuid: string | null;
  user: User | null;
  convStatuses: Record<string, ConvStatus>;
  mobileOpen?: boolean;
  onSwitch: (uuid: string) => void;
  onNew: (mode?: string) => void;
  onDelete: (uuid: string) => void;
  onMobileClose?: () => void;
}

function groupByDate(conversations: readonly Conversation[]) {
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const yesterday = new Date(today.getTime() - 86400000);
  const weekAgo = new Date(today.getTime() - 7 * 86400000);
  const groups: { label: string; items: Conversation[] }[] = [
    { label: 'Today', items: [] }, { label: 'Yesterday', items: [] },
    { label: 'This Week', items: [] }, { label: 'Older', items: [] },
  ];
  for (const c of conversations) {
    const d = new Date(c.updated_at || c.created_at);
    if (d >= today) groups[0].items.push(c);
    else if (d >= yesterday) groups[1].items.push(c);
    else if (d >= weekAgo) groups[2].items.push(c);
    else groups[3].items.push(c);
  }
  return groups.filter((g) => g.items.length > 0);
}

function ConvIcon({ status }: { status: ConvStatus }) {
  const base = "w-2 h-2 rounded-full shrink-0";
  if (status === 'processing') return <span className={`${base} bg-primary animate-pulse`} title="Processing" />;
  if (status === 'waiting_approval') return <span className={`${base} bg-warning`} title="Needs approval" />;
  if (status === 'waiting_input') return <span className={`${base} bg-primary-light`} title="Waiting for you" />;
  return <span className={`${base} bg-border`} />;
}

export function Sidebar({ conversations, currentUuid, user, convStatuses, mobileOpen, onSwitch, onNew, onDelete, onMobileClose }: Props) {
  const navigate = useNavigate();
  const [pendingDelete, setPendingDelete] = useState<{ uuid: string; title: string } | null>(null);
  const [search, setSearch] = useState('');
  const [collapsed, setCollapsed] = useState(false);

  const filtered = useMemo(() => {
    if (!search.trim()) return conversations;
    const q = search.toLowerCase();
    return conversations.filter((c) => c.title.toLowerCase().includes(q));
  }, [conversations, search]);

  const groups = useMemo(() => groupByDate(filtered), [filtered]);

  // Shared sidebar content (used by both inline and mobile drawer)
  const sidebarContent = (isMobile: boolean) => (
    <>
      {/* Top row */}
      <div className="flex items-center gap-2">
        {isMobile ? (
          <button
            className="w-9 h-9 rounded-lg flex items-center justify-center text-text-dim hover:bg-surface-hover hover:text-text transition-colors shrink-0"
            onClick={onMobileClose}
            title="Close"
          >
            <X size={18} />
          </button>
        ) : (
          <button 
            className="w-9 h-9 rounded-lg flex items-center justify-center text-text-dim hover:bg-surface-hover hover:text-text transition-colors shrink-0"
            onClick={() => setCollapsed(true)} 
            title="Collapse sidebar"
          >
            <PanelLeftClose size={18} />
          </button>
        )}
        <button 
          className="flex-1 flex items-center justify-center gap-2 bg-primary text-white h-9 px-4 rounded-lg font-medium text-sm hover:bg-primary-hover transition-colors"
          onClick={() => { onNew(); if (isMobile) onMobileClose?.(); }}
        >
          <Plus size={16} />
          <span>New Chat</span>
        </button>
      </div>

      {/* Search */}
      <div className="relative">
        <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-dim" />
        <input 
          type="text" 
          className="w-full bg-bg border border-border rounded-lg pl-9 pr-3 py-2 text-sm text-text placeholder-text-dim focus:border-primary focus:outline-none transition-colors"
          placeholder="Search..." 
          value={search} 
          onChange={(e) => setSearch(e.target.value)} 
        />
      </div>

      {/* Conversation list */}
      <div className="flex flex-col gap-1 flex-1 overflow-y-auto">
        {groups.map((group) => (
          <div key={group.label} className="mb-3">
            <div className="text-xs uppercase tracking-wider text-text-dim font-semibold mb-2 px-2">{group.label}</div>
            {group.items.map((conv) => (
              <div
                key={conv.uuid}
                className={`group flex items-center gap-2 px-3 py-2.5 rounded-lg text-sm transition-all relative ${
                  conv.uuid === currentUuid 
                    ? 'bg-primary/10 text-text' 
                    : 'text-text-dim hover:bg-surface-hover hover:text-text'
                }`}
              >
                <button
                  type="button"
                  className="absolute inset-0 w-full h-full cursor-pointer"
                  onClick={() => { onSwitch(conv.uuid); if (isMobile) onMobileClose?.(); }}
                  aria-label={`Switch to conversation: ${conv.title}`}
                  aria-pressed={conv.uuid === currentUuid}
                />
                <ConvIcon status={convStatuses[conv.uuid] || 'idle'} />
                <span className="flex-1 truncate" title={conv.title}>{conv.title}</span>
                <button
                  type="button"
                  className="opacity-0 group-hover:opacity-100 text-text-dim hover:text-error p-1 rounded transition-all relative z-10"
                  onClick={(e) => {
                    e.stopPropagation();
                    setPendingDelete({ uuid: conv.uuid, title: conv.title });
                  }}
                  title="Delete"
                >
                  <Trash2 size={14} />
                </button>
              </div>
            ))}
          </div>
        ))}
        {filtered.length === 0 && (
          <div className="text-center text-text-dim text-sm py-8">
            {search ? 'No matches' : 'No conversations yet'}
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="pt-3 flex flex-col gap-1.5">
        <div className="flex items-center gap-2">
          <button 
            className="w-9 h-9 rounded-lg flex items-center justify-center text-text-dim hover:bg-surface-hover hover:text-text transition-colors"
            onClick={() => { navigate('/settings'); if (isMobile) onMobileClose?.(); }} 
            title="Settings"
          >
            <Settings size={18} />
          </button>
          {user && (
            <span className="flex-1 truncate text-sm text-text-dim" title={user.username}>
              {user.display_name || user.username}
            </span>
          )}
          <button 
            className="w-9 h-9 rounded-lg flex items-center justify-center text-text-dim hover:bg-surface-hover hover:text-error transition-colors"
            onClick={() => { setToken(null); window.location.reload(); }} 
            title="Sign out"
          >
            <LogOut size={18} />
          </button>
        </div>
        <span className="text-[11px] text-text-dim px-2">v{APP_VERSION}</span>
      </div>

      {pendingDelete && (
        <ConfirmDialog
          title="Delete Conversation"
          message={`Are you sure you want to delete "${pendingDelete.title}"? This action cannot be undone.`}
          confirmLabel="Delete"
          cancelLabel="Cancel"
          danger
          onConfirm={() => {
            onDelete(pendingDelete.uuid);
            setPendingDelete(null);
          }}
          onCancel={() => setPendingDelete(null)}
        />
      )}
    </>
  );

  // Mobile drawer overlay
  if (mobileOpen) {
    return (
      <>
        {/* Backdrop */}
        <div
          className="fixed inset-0 bg-black/60 z-40 lg:hidden"
          onClick={onMobileClose}
        />
        {/* Drawer */}
        <aside className="fixed inset-y-0 left-0 w-72 bg-surface border-r border-border p-4 flex flex-col gap-4 overflow-hidden z-50 lg:hidden animate-[slide-in-left_0.2s_ease-out]">
          {sidebarContent(true)}
        </aside>
      </>
    );
  }

  if (collapsed) {
    return (
      <aside className="w-14 bg-surface border-r border-border flex flex-col items-center py-4 gap-3 shrink-0 max-md:hidden">
        <button 
          className="w-9 h-9 rounded-lg flex items-center justify-center text-text-dim hover:bg-surface-hover hover:text-text transition-colors"
          onClick={() => setCollapsed(false)} 
          title="Expand sidebar"
        >
          <PanelLeftOpen size={18} />
        </button>
        <button 
          className="w-9 h-9 rounded-lg flex items-center justify-center bg-primary text-white hover:bg-primary-hover transition-colors"
          onClick={() => onNew()} 
          title="New chat"
        >
          <Plus size={18} />
        </button>
        <div className="flex-1" />
      </aside>
    );
  }

  return (
    <aside className="w-60 min-w-[200px] bg-surface border-r border-border p-4 flex flex-col gap-4 overflow-hidden shrink-0 max-md:hidden">
      {sidebarContent(false)}
    </aside>
  );
}

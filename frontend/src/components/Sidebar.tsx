import { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { setToken } from '../api';
import type { Conversation, User } from '../types';
import { ConfirmDialog } from './ConfirmDialog';

type ConvStatus = 'idle' | 'processing' | 'waiting_approval' | 'waiting_input';

interface Props {
  conversations: Conversation[];
  currentUuid: string | null;
  user: User | null;
  convStatuses: Record<string, ConvStatus>;
  onSwitch: (uuid: string) => void;
  onNew: (mode?: string) => void;
  onDelete: (uuid: string) => void;
  onAction: (type: string) => void;
}

function groupByDate(conversations: Conversation[]) {
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
  if (status === 'processing') return <span className="conv-status-icon conv-status-processing" title="Processing" />;
  if (status === 'waiting_approval') return <span className="conv-status-icon conv-status-approval" title="Needs approval" />;
  if (status === 'waiting_input') return <span className="conv-status-icon conv-status-input" title="Waiting for you" />;
  return <span className="conv-status-icon conv-status-idle" />;
}

export function Sidebar({ conversations, currentUuid, user, convStatuses, onSwitch, onNew, onDelete, onAction }: Props) {
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

  if (collapsed) {
    return (
      <aside className="sidebar sidebar-collapsed">
        <button className="sidebar-toggle" onClick={() => setCollapsed(false)} title="Expand">&raquo;</button>
        <button className="icon-btn" onClick={() => onNew()} title="New chat">+</button>
      </aside>
    );
  }

  return (
    <aside className="sidebar">
      <div className="sidebar-top">
        <button className="sidebar-toggle" onClick={() => setCollapsed(true)} title="Collapse">&laquo;</button>
        <button className="action-btn new-conv-btn" onClick={() => onNew()}>+ New Chat</button>
      </div>

      <input type="text" className="sidebar-search" placeholder="Search..." value={search} onChange={(e) => setSearch(e.target.value)} />

      <div className="conversation-list">
        {groups.map((group) => (
          <div key={group.label} className="conv-group">
            <div className="conv-group-label">{group.label}</div>
            {group.items.map((conv) => (
              <div
                key={conv.uuid}
                className={`conversation-item ${conv.uuid === currentUuid ? 'active' : ''}`}
                onClick={() => onSwitch(conv.uuid)}
              >
                <ConvIcon status={convStatuses[conv.uuid] || 'idle'} />
                <span className="conv-title" title={conv.title}>{conv.title}</span>
                <button
                  className="conv-delete"
                  onClick={(e) => {
                    e.stopPropagation();
                    setPendingDelete({ uuid: conv.uuid, title: conv.title });
                  }}
                  title="Delete"
                >
                  {'\u2715'}
                </button>
              </div>
            ))}
          </div>
        ))}
        {filtered.length === 0 && <div className="conv-empty">{search ? 'No matches' : 'No conversations yet'}</div>}
      </div>

      <div className="sidebar-actions">
        <button className="action-btn" onClick={() => onAction('undo')} title="Undo">&#x21A9; Undo</button>
        <button className="action-btn" onClick={() => onAction('compact')} title="Compact">&#x2702; Compact</button>
      </div>

      <div className="sidebar-footer">
        <button className="settings-btn" onClick={() => navigate('/settings')} title="Settings">&#x2699;</button>
        {user && <span className="user-info" title={user.username}>{user.display_name || user.username}</span>}
        <button className="logout-btn" onClick={() => { setToken(null); window.location.reload(); }} title="Sign out">&#x2192;</button>
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
    </aside>
  );
}

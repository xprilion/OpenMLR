import { api } from '../api';

interface Props {
  onAction: (type: string, data?: any) => void;
}

export function Sidebar({ onAction }: Props) {
  return (
    <aside className="sidebar">
      <h3 className="sidebar-title">Actions</h3>

      <div className="action-group">
        <button
          className="action-btn"
          onClick={async () => {
            await api.undo();
            onAction('undo');
          }}
          title="Undo last turn"
        >
          &#x21A9; Undo
        </button>
        <button
          className="action-btn"
          onClick={async () => {
            await api.compact();
            onAction('compact');
          }}
          title="Compact conversation context"
        >
          &#x1F4A9; Compact
        </button>
      </div>

      <div className="sidebar-section">
        <h4>Shortcuts</h4>
        <div className="shortcut-list">
          <div><kbd>Enter</kbd> Send</div>
          <div><kbd>Shift</kbd>+<kbd>Enter</kbd> New line</div>
        </div>
      </div>
    </aside>
  );
}

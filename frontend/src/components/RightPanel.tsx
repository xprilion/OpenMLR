import { useState, useRef, useCallback } from 'react';
import type { PlanTask, Resource, ContextUsage, SearchBudget } from '../types';

interface Props {
  tasks: PlanTask[];
  resources: Resource[];
  contextUsage: ContextUsage | null;
  searchBudget: SearchBudget | null;
  visible: boolean;
  onToggle: () => void;
  onViewReport: (resource: Resource) => void;
}

const STATUS_ICON: Record<string, string> = { pending: '○', in_progress: '◉', completed: '✓', cancelled: '✗' };
const STATUS_CLASS: Record<string, string> = { pending: 'task-pending', in_progress: 'task-progress', completed: 'task-done', cancelled: 'task-cancelled' };
const RES_ICON: Record<string, string> = { paper: '📄', code: '💻', dataset: '📊', doc: '📝', report: '📋' };

export function RightPanel({ tasks, resources, contextUsage, searchBudget, visible, onToggle, onViewReport }: Props) {
  const hasContent = tasks.length > 0 || resources.length > 0;
  const [splitY, setSplitY] = useState(50); // percentage for tasks section
  const dragging = useRef(false);
  const panelRef = useRef<HTMLElement>(null);

  const onMouseDown = useCallback(() => { dragging.current = true; }, []);

  const onMouseMove = useCallback((e: React.MouseEvent) => {
    if (!dragging.current || !panelRef.current) return;
    const rect = panelRef.current.getBoundingClientRect();
    // Subtract header height (~42px) and gauge area (~60px)
    const contentTop = rect.top + 102;
    const contentHeight = rect.height - 102;
    const y = ((e.clientY - contentTop) / contentHeight) * 100;
    setSplitY(Math.max(15, Math.min(85, y)));
  }, []);

  const onMouseUp = useCallback(() => { dragging.current = false; }, []);

  if (!visible) {
    if (!hasContent && !contextUsage) return null;
    return (
      <button className="right-panel-toggle" onClick={onToggle} title="Tasks & resources">
        {tasks.length > 0 && <span className="toggle-badge">{tasks.length}</span>}
        ☰
      </button>
    );
  }

  const done = tasks.filter((t) => t.status === 'completed').length;
  const ctxPct = contextUsage ? Math.round(contextUsage.ratio * 100) : 0;
  const ctxColor = ctxPct > 80 ? 'var(--error)' : ctxPct > 60 ? 'var(--accent)' : 'var(--success)';

  return (
    <aside
      className="right-panel"
      ref={panelRef}
      onMouseMove={onMouseMove}
      onMouseUp={onMouseUp}
      onMouseLeave={onMouseUp}
    >
      <div className="right-panel-header">
        <span className="right-panel-title">Tasks & Resources</span>
        <button className="right-panel-close" onClick={onToggle}>&times;</button>
      </div>

      {/* Context gauge */}
      {contextUsage && (
        <div className="context-gauge">
          <div className="gauge-label">
            Context: {(contextUsage.used / 1000).toFixed(0)}k / {(contextUsage.max / 1000).toFixed(0)}k tokens
          </div>
          <div className="gauge-bar">
            <div className="gauge-fill" style={{ width: `${ctxPct}%`, background: ctxColor }} />
          </div>
        </div>
      )}

      {/* Search budget */}
      {searchBudget && (
        <div className="context-gauge">
          <div className="gauge-label">
            Searches: {searchBudget.used} / {searchBudget.max}
          </div>
          <div className="gauge-bar">
            <div className="gauge-fill" style={{
              width: `${Math.round((searchBudget.used / searchBudget.max) * 100)}%`,
              background: searchBudget.used >= searchBudget.max ? 'var(--error)' : 'var(--accent)',
            }} />
          </div>
        </div>
      )}

      {/* Tasks section */}
      <div className="right-section" style={{ flex: `0 0 ${splitY}%`, overflow: 'auto' }}>
        <div className="right-section-label">Tasks ({done}/{tasks.length})</div>
        <div className="task-list">
          {tasks.map((t, i) => (
            <div key={i} className={`task-item ${STATUS_CLASS[t.status]}`}>
              <span className="task-icon">{STATUS_ICON[t.status]}</span>
              <span className="task-title">{t.title}</span>
            </div>
          ))}
          {tasks.length === 0 && <div className="right-empty-inline">No tasks yet</div>}
        </div>
      </div>

      {/* Draggable separator */}
      <div className="panel-separator" onMouseDown={onMouseDown} />

      {/* Resources section */}
      <div className="right-section" style={{ flex: `0 0 ${100 - splitY}%`, overflow: 'auto' }}>
        <div className="right-section-label">Resources ({resources.length})</div>
        <div className="resource-list">
          {resources.map((r, i) => (
            <div key={i} className={`resource-item ${r.type === 'report' ? 'resource-report' : ''}`}>
              <span className="resource-icon">{RES_ICON[r.type] || '📄'}</span>
              <div className="resource-info">
                {r.type === 'report' && r.id ? (
                  <button className="resource-title-btn" onClick={() => onViewReport(r)}>
                    {r.title}
                  </button>
                ) : (
                  <span className="resource-title">{r.title}</span>
                )}
                {r.url && (
                  <a className="resource-url" href={r.url} target="_blank" rel="noopener noreferrer">
                    {r.url.length > 40 ? r.url.slice(0, 40) + '...' : r.url}
                  </a>
                )}
              </div>
            </div>
          ))}
          {resources.length === 0 && <div className="right-empty-inline">No resources yet</div>}
        </div>
      </div>
    </aside>
  );
}

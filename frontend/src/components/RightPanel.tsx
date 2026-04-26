import { useState, useRef, useCallback } from 'react';
import { api } from '../api';
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
const RES_ICON: Record<string, string> = { plan: '📌', paper: '📄', code: '💻', dataset: '📊', doc: '📝', report: '📋' };

/** Convert markdown to a basic LaTeX document. */
function markdownToLatex(md: string, title: string): string {
  const lines: string[] = [
    '\\documentclass{article}',
    '\\usepackage[utf8]{inputenc}',
    '\\usepackage{amsmath,amssymb}',
    '\\usepackage{hyperref}',
    '',
    `\\title{${title}}`,
    '\\author{}',
    '\\date{\\today}',
    '',
    '\\begin{document}',
    '\\maketitle',
    '',
  ];
  for (const line of md.split('\n')) {
    if (line.startsWith('### ')) {
      lines.push(`\\subsubsection{${line.slice(4)}}`);
    } else if (line.startsWith('## ')) {
      lines.push(`\\subsection{${line.slice(3)}}`);
    } else if (line.startsWith('# ')) {
      // Skip title heading — already in \maketitle
      continue;
    } else {
      lines.push(line);
    }
  }
  lines.push('\\end{document}');
  return lines.join('\n');
}

/** Trigger a file download from a string. */
function downloadFile(content: string, filename: string, mime: string) {
  const blob = new Blob([content], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

export function RightPanel({ tasks, resources, contextUsage, searchBudget, visible, onToggle, onViewReport }: Props) {
  const hasContent = tasks.length > 0 || resources.length > 0;
  const [splitY, setSplitY] = useState(50); // percentage for tasks section
  const [exporting, setExporting] = useState(false);
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

  // Find the paper resource (if any)
  const paperResource = resources.find((r) => r.type === 'paper');
  // Non-paper resources for the general list
  const otherResources = resources.filter((r) => r.type !== 'paper');

  /** Fetch paper content and download in the given format. */
  const handleExport = useCallback(async (format: 'markdown' | 'latex') => {
    if (!paperResource?.id) return;
    setExporting(true);
    try {
      const data = await api.getReport(paperResource.id);
      const content: string = data.content || '';
      if (format === 'latex') {
        const latex = markdownToLatex(content, paperResource.title);
        downloadFile(latex, 'paper.tex', 'application/x-tex');
      } else {
        downloadFile(content, 'paper.md', 'text/markdown');
      }
    } catch {
      // silently fail — could add a toast here
    } finally {
      setExporting(false);
    }
  }, [paperResource]);

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

      {/* Paper section — only shown when a paper resource exists */}
      {paperResource && (
        <div className="right-section paper-section">
          <div className="right-section-label">Paper</div>
          <div className="paper-card">
            <button className="paper-title-btn" onClick={() => onViewReport(paperResource)}>
              <span className="resource-icon">📄</span>
              <span className="paper-title-text">{paperResource.title}</span>
            </button>
            <div className="paper-actions">
              <button
                className="paper-export-btn"
                disabled={exporting}
                onClick={() => handleExport('markdown')}
                title="Download as Markdown"
              >
                .md
              </button>
              <button
                className="paper-export-btn"
                disabled={exporting}
                onClick={() => handleExport('latex')}
                title="Download as LaTeX"
              >
                .tex
              </button>
            </div>
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
        <div className="right-section-label">Resources ({otherResources.length})</div>
        <div className="resource-list">
          {[...otherResources].sort((a, b) => (a.type === 'plan' ? -1 : b.type === 'plan' ? 1 : 0)).map((r, i) => (
            <div key={i} className={`resource-item ${r.type === 'report' ? 'resource-report' : ''} ${r.type === 'plan' ? 'resource-plan' : ''}`}>
              <span className="resource-icon">{RES_ICON[r.type] || '📄'}</span>
              <div className="resource-info">
                {(r.type === 'report' || r.type === 'plan') && r.id ? (
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
          {otherResources.length === 0 && <div className="right-empty-inline">No resources yet</div>}
        </div>
      </div>
    </aside>
  );
}

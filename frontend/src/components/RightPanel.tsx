import { useState, useRef, useCallback } from 'react';
import { 
  X, 
  Menu, 
  Circle, 
  CircleDot, 
  CheckCircle2, 
  XCircle,
  FileText,
  Pin,
  Code,
  Database,
  FileEdit,
  ClipboardList,
  Download,
  ExternalLink
} from 'lucide-react';
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

const STATUS_ICONS: Record<string, React.ReactNode> = {
  pending: <Circle size={14} />,
  in_progress: <CircleDot size={14} />,
  completed: <CheckCircle2 size={14} />,
  cancelled: <XCircle size={14} />,
};

const RES_ICONS: Record<string, React.ReactNode> = {
  plan: <Pin size={14} />,
  paper: <FileText size={14} />,
  code: <Code size={14} />,
  dataset: <Database size={14} />,
  doc: <FileEdit size={14} />,
  report: <ClipboardList size={14} />,
};

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
      <button 
        className="fixed right-4 top-20 z-20 w-10 h-10 rounded-lg bg-surface border border-border flex items-center justify-center text-text-dim hover:text-text hover:border-primary transition-all shadow-md"
        onClick={onToggle} 
        title="Tasks & resources"
      >
        {tasks.length > 0 && (
          <span className="absolute -top-1 -right-1 w-5 h-5 bg-primary text-white text-xs rounded-full flex items-center justify-center font-medium">
            {tasks.length}
          </span>
        )}
        <Menu size={18} />
      </button>
    );
  }

  const done = tasks.filter((t) => t.status === 'completed').length;
  const ctxPct = contextUsage ? Math.round(contextUsage.ratio * 100) : 0;
  const ctxColor = ctxPct > 80 ? 'bg-error' : ctxPct > 60 ? 'bg-warning' : 'bg-success';

  return (
    <aside
      className="w-72 min-w-[240px] bg-surface border-l border-border flex flex-col shrink-0 max-lg:hidden"
      ref={panelRef}
      onMouseMove={onMouseMove}
      onMouseUp={onMouseUp}
      onMouseLeave={onMouseUp}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-border">
        <span className="font-semibold text-text">Tasks & Resources</span>
        <button 
          className="w-7 h-7 rounded-lg flex items-center justify-center text-text-dim hover:bg-surface-hover hover:text-text transition-colors"
          onClick={onToggle}
        >
          <X size={16} />
        </button>
      </div>

      {/* Context gauge */}
      {contextUsage && (
        <div className="px-4 py-3 border-b border-border">
          <div className="text-xs text-text-dim mb-2">
            Context: {(contextUsage.used / 1000).toFixed(0)}k / {(contextUsage.max / 1000).toFixed(0)}k tokens
          </div>
          <div className="h-2 bg-bg rounded-full overflow-hidden">
            <div className={`h-full ${ctxColor} transition-all`} style={{ width: `${ctxPct}%` }} />
          </div>
        </div>
      )}

      {/* Search budget */}
      {searchBudget && (
        <div className="px-4 py-3 border-b border-border">
          <div className="text-xs text-text-dim mb-2">
            Searches: {searchBudget.used} / {searchBudget.max}
          </div>
          <div className="h-2 bg-bg rounded-full overflow-hidden">
            <div 
              className={`h-full transition-all ${searchBudget.used >= searchBudget.max ? 'bg-error' : 'bg-warning'}`}
              style={{ width: `${Math.round((searchBudget.used / searchBudget.max) * 100)}%` }} 
            />
          </div>
        </div>
      )}

      {/* Paper section — only shown when a paper resource exists */}
      {paperResource && (
        <div className="px-4 py-3 border-b border-border">
          <div className="text-xs uppercase tracking-wider text-text-dim font-semibold mb-2">Paper</div>
          <div className="bg-bg rounded-lg p-3 border border-border">
            <button 
              className="flex items-center gap-2 text-left w-full text-text hover:text-primary transition-colors"
              onClick={() => onViewReport(paperResource)}
            >
              <FileText size={16} />
              <span className="truncate font-medium">{paperResource.title}</span>
            </button>
            <div className="flex gap-2 mt-3">
              <button
                className="flex-1 py-1.5 text-xs font-medium bg-surface-hover rounded-md text-text-dim hover:text-text transition-colors disabled:opacity-50 flex items-center justify-center gap-1"
                disabled={exporting}
                onClick={() => handleExport('markdown')}
                title="Download as Markdown"
              >
                <Download size={12} />
                .md
              </button>
              <button
                className="flex-1 py-1.5 text-xs font-medium bg-surface-hover rounded-md text-text-dim hover:text-text transition-colors disabled:opacity-50 flex items-center justify-center gap-1"
                disabled={exporting}
                onClick={() => handleExport('latex')}
                title="Download as LaTeX"
              >
                <Download size={12} />
                .tex
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Tasks section */}
      <div className="px-4 py-3 overflow-auto" style={{ flex: `0 0 ${splitY}%` }}>
        <div className="text-xs uppercase tracking-wider text-text-dim font-semibold mb-2">
          Tasks ({done}/{tasks.length})
        </div>
        <div className="flex flex-col gap-1.5">
          {tasks.map((t, i) => (
            <div 
              key={i} 
              className={`flex items-center gap-2 px-2.5 py-2 rounded-lg text-sm ${
                t.status === 'completed' ? 'text-text-dim' : 
                t.status === 'in_progress' ? 'text-primary bg-primary/10' : 
                t.status === 'cancelled' ? 'text-error line-through' : 'text-text'
              }`}
            >
              <span className={`shrink-0 ${
                t.status === 'completed' ? 'text-success' : 
                t.status === 'in_progress' ? 'text-primary' : 
                t.status === 'cancelled' ? 'text-error' : 'text-text-dim'
              }`}>
                {STATUS_ICONS[t.status] || <Circle size={14} />}
              </span>
              <span className="truncate">{t.title}</span>
            </div>
          ))}
          {tasks.length === 0 && (
            <div className="text-sm text-text-dim py-2">No tasks yet</div>
          )}
        </div>
      </div>

      {/* Draggable separator */}
      <div 
        className="h-1 bg-border hover:bg-primary cursor-ns-resize transition-colors"
        onMouseDown={onMouseDown} 
      />

      {/* Resources section */}
      <div className="px-4 py-3 overflow-auto" style={{ flex: `0 0 ${100 - splitY}%` }}>
        <div className="text-xs uppercase tracking-wider text-text-dim font-semibold mb-2">
          Resources ({otherResources.length})
        </div>
        <div className="flex flex-col gap-1.5">
          {[...otherResources].sort((a, b) => (a.type === 'plan' ? -1 : b.type === 'plan' ? 1 : 0)).map((r, i) => (
            <div 
              key={i} 
              className={`flex items-start gap-2 px-2.5 py-2 rounded-lg text-sm ${
                r.type === 'report' || r.type === 'plan' ? 'bg-primary/5 border border-primary/20' : ''
              }`}
            >
              <span className="shrink-0 text-text-dim mt-0.5">
                {RES_ICONS[r.type] || <FileText size={14} />}
              </span>
              <div className="flex-1 min-w-0">
                {(r.type === 'report' || r.type === 'plan') && r.id ? (
                  <button 
                    className="text-left font-medium text-text hover:text-primary transition-colors truncate block w-full"
                    onClick={() => onViewReport(r)}
                  >
                    {r.title}
                  </button>
                ) : (
                  <span className="font-medium text-text truncate block">{r.title}</span>
                )}
                {r.url && (
                  <a 
                    className="text-xs text-text-dim hover:text-primary truncate flex items-center gap-1 mt-0.5"
                    href={r.url} 
                    target="_blank" 
                    rel="noopener noreferrer"
                  >
                    <ExternalLink size={10} />
                    {r.url.length > 35 ? r.url.slice(0, 35) + '...' : r.url}
                  </a>
                )}
              </div>
            </div>
          ))}
          {otherResources.length === 0 && (
            <div className="text-sm text-text-dim py-2">No resources yet</div>
          )}
        </div>
      </div>
    </aside>
  );
}

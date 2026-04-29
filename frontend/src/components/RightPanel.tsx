import { useState } from 'react';
import { 
  Circle, 
  CircleDot, 
  CheckCircle2, 
  XCircle,
  ListTodo,
  Files,
  Settings,
  PanelRightClose,
  PanelRightOpen,
} from 'lucide-react';
import { api } from '../api';
import { FileTree } from './FileTree';
import { CollapsiblePanel } from './CollapsiblePanel';
import type { PlanTask, Resource, ContextUsage, SearchBudget } from '../types';

interface Props {
  tasks: PlanTask[];
  resources: Resource[];
  contextUsage: ContextUsage | null;
  searchBudget: SearchBudget | null;
  visible: boolean;
  projectUuid: string | null;
  fileTreeRefreshKey?: number;
  onToggle: () => void;
  onViewReport: (resource: Resource) => void;
  onSearchBudgetChange?: (newMax: number) => void;
}

const STATUS_ICONS: Record<string, React.ReactNode> = {
  pending: <Circle size={14} />,
  in_progress: <CircleDot size={14} />,
  completed: <CheckCircle2 size={14} />,
  cancelled: <XCircle size={14} />,
};

/* ── Search Budget Settings Dialog ── */
function SearchBudgetDialog({ currentMax, onSave, onClose }: { currentMax: number; onSave: (v: number) => void; onClose: () => void }) {
  const [value, setValue] = useState(String(currentMax));
  const [saving, setSaving] = useState(false);

  const handleSave = async () => {
    const num = parseInt(value, 10);
    if (isNaN(num) || num < 1) return;
    setSaving(true);
    try {
      await api.updateSetting('agent', 'paper_search_budget', num);
      onSave(num);
    } catch {
      // ignore
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={onClose}>
      <div className="bg-surface border border-border rounded-xl shadow-2xl p-6 w-80" onClick={(e) => e.stopPropagation()}>
        <h3 className="text-sm font-semibold text-text mb-4">Search Budget</h3>
        <p className="text-xs text-text-dim mb-3">
          Set the maximum number of paper searches allowed per session.
        </p>
        <input
          type="number"
          min={1}
          max={200}
          className="w-full bg-bg border border-border rounded-lg px-3 py-2 text-sm text-text focus:border-primary focus:outline-none transition-colors mb-4"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter') handleSave(); }}
          autoFocus
        />
        <div className="flex gap-2 justify-end">
          <button
            className="px-4 py-1.5 text-xs font-medium rounded-lg text-text-dim hover:text-text hover:bg-surface-hover transition-colors"
            onClick={onClose}
          >
            Cancel
          </button>
          <button
            className="px-4 py-1.5 text-xs font-medium rounded-lg bg-primary text-white hover:bg-primary-hover transition-colors disabled:opacity-50"
            disabled={saving || !value || parseInt(value, 10) < 1}
            onClick={handleSave}
          >
            {saving ? 'Saving...' : 'Save'}
          </button>
        </div>
      </div>
    </div>
  );
}

export function RightPanel({ tasks, resources: _resources, contextUsage, searchBudget, visible, projectUuid, fileTreeRefreshKey, onToggle, onViewReport: _onViewReport, onSearchBudgetChange }: Props) {
  const [showBudgetDialog, setShowBudgetDialog] = useState(false);

  const done = tasks.filter((t) => t.status === 'completed').length;
  const ctxPct = contextUsage ? Math.round(contextUsage.ratio * 100) : 0;
  const ctxColor = ctxPct > 80 ? 'bg-error' : ctxPct > 60 ? 'bg-warning' : 'bg-success';
  const budgetUsed = searchBudget?.used ?? 0;
  const budgetMax = searchBudget?.max ?? 25;
  const budgetPct = budgetMax > 0 ? Math.round((budgetUsed / budgetMax) * 100) : 0;

  // Collapsed state: show narrow icon rail
  if (!visible) {
    return (
      <aside className="fixed right-0 top-14 bottom-0 w-12 bg-surface border-l border-border flex flex-col items-center py-3 gap-2 z-10 max-lg:hidden">
        <button
          className="w-9 h-9 rounded-lg flex items-center justify-center text-text-dim hover:bg-surface-hover hover:text-text transition-colors"
          onClick={onToggle}
          title="Expand panel"
        >
          <PanelRightOpen size={18} />
        </button>
        {tasks.length > 0 && (
          <button
            className="relative w-9 h-9 rounded-lg flex items-center justify-center text-text-dim hover:bg-surface-hover hover:text-text transition-colors"
            onClick={onToggle}
            title="Todos"
          >
            <ListTodo size={18} />
            <span className="absolute -top-1 -right-1 w-4 h-4 bg-primary text-white text-[9px] rounded-full flex items-center justify-center font-medium">
              {tasks.length}
            </span>
          </button>
        )}
      </aside>
    );
  }

  // Expanded state — no tabs, everything stacked
  return (
    <aside
      className="fixed right-0 top-14 bottom-0 w-72 bg-surface border-l border-border flex flex-col z-10 max-lg:hidden"
    >
      {/* Header — just the collapse button */}
      <div className="flex items-center justify-end px-3 py-2 border-b border-border shrink-0">
        <button 
          className="w-7 h-7 rounded-lg flex items-center justify-center text-text-dim hover:bg-surface-hover hover:text-text transition-colors"
          onClick={onToggle}
          title="Collapse panel"
        >
          <PanelRightClose size={16} />
        </button>
      </div>

      {/* Context gauge */}
      <div className="px-4 py-3 border-b border-border shrink-0">
        <div className="text-xs text-text-dim mb-2">
          {contextUsage
            ? `Context: ${(contextUsage.used / 1000).toFixed(0)}k / ${(contextUsage.max / 1000).toFixed(0)}k tokens`
            : 'Context: --'}
        </div>
        <div className="h-2 bg-bg rounded-full overflow-hidden">
          {contextUsage && (
            <div className={`h-full ${ctxColor} transition-all`} style={{ width: `${ctxPct}%` }} />
          )}
        </div>
      </div>

      {/* Search budget */}
      <div className="px-4 py-3 border-b border-border shrink-0">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs text-text-dim">
            Searches: {budgetUsed} / {budgetMax}
          </span>
          <button
            className="w-5 h-5 rounded flex items-center justify-center text-text-dim hover:text-text hover:bg-surface-hover transition-colors"
            onClick={() => setShowBudgetDialog(true)}
            title="Change search budget"
          >
            <Settings size={12} />
          </button>
        </div>
        <div className="h-2 bg-bg rounded-full overflow-hidden">
          {budgetUsed > 0 && (
            <div 
              className={`h-full transition-all ${budgetUsed >= budgetMax ? 'bg-error' : 'bg-warning'}`}
              style={{ width: `${budgetPct}%` }} 
            />
          )}
        </div>
      </div>

      {/* Scrollable content: Todos + Files stacked */}
      <div className="flex-1 overflow-y-auto">
        {/* Todos */}
        <CollapsiblePanel title="Todos" icon={<ListTodo size={12} />} badge={`${done}/${tasks.length}`}>
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
        </CollapsiblePanel>

        {/* Files */}
        {projectUuid && (
          <CollapsiblePanel title="Files" icon={<Files size={12} />}>
            <div className="-mx-4 -mb-3">
              <FileTree projectUuid={projectUuid} refreshKey={fileTreeRefreshKey} />
            </div>
          </CollapsiblePanel>
        )}
      </div>

      {/* Search Budget Settings Dialog */}
      {showBudgetDialog && (
        <SearchBudgetDialog
          currentMax={budgetMax}
          onSave={(newMax) => {
            setShowBudgetDialog(false);
            onSearchBudgetChange?.(newMax);
          }}
          onClose={() => setShowBudgetDialog(false)}
        />
      )}
    </aside>
  );
}

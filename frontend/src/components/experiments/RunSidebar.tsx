import { 
  Activity, 
  Plus, 
  Search, 
  GitCompare, 
  CheckCircle2, 
  AlertCircle, 
  Clock, 
  RotateCw,
  Pause
} from 'lucide-react';
import type { ExperimentRun, RunStatus } from './types';

interface RunSidebarProps {
  readonly runs: readonly ExperimentRun[];
  readonly selectedRunId: string;
  readonly compareRunIds: readonly string[];
  readonly isComparing: boolean;
  readonly searchQuery: string;
  readonly statusFilter: 'all' | RunStatus;
  readonly onSelectRun: (id: string) => void;
  readonly onToggleCompare: (id: string) => void;
  readonly onToggleCompareMode: () => void;
  readonly onSearchChange: (q: string) => void;
  readonly onStatusFilterChange: (st: 'all' | RunStatus) => void;
  readonly onNewRun: () => void;
}

function statusColor(status: RunStatus): string {
  switch (status) {
    case 'running': return 'text-primary bg-primary/10 border-primary/30';
    case 'completed': return 'text-success bg-success/10 border-success/30';
    case 'failed': return 'text-error bg-error/10 border-error/30';
    case 'paused': return 'text-warning bg-warning/10 border-warning/30';
    default: return 'text-text-dim bg-surface border-border';
  }
}

function statusIcon(status: RunStatus) {
  switch (status) {
    case 'running': return <RotateCw size={12} className="animate-spin text-primary" />;
    case 'completed': return <CheckCircle2 size={12} className="text-success" />;
    case 'failed': return <AlertCircle size={12} className="text-error" />;
    case 'paused': return <Pause size={12} className="text-warning" />;
    default: return <Clock size={12} className="text-text-dim" />;
  }
}

export function RunSidebar({
  runs,
  selectedRunId,
  compareRunIds,
  isComparing,
  searchQuery,
  statusFilter,
  onSelectRun,
  onToggleCompare,
  onToggleCompareMode,
  onSearchChange,
  onStatusFilterChange,
  onNewRun,
}: Readonly<RunSidebarProps>) {
  const filteredRuns = runs.filter((r) => {
    const matchSearch = r.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      r.tags.some((t) => t.toLowerCase().includes(searchQuery.toLowerCase()));
    const matchStatus = statusFilter === 'all' || r.status === statusFilter;
    return matchSearch && matchStatus;
  });

  return (
    <div className="w-80 border-r border-border flex flex-col shrink-0 bg-surface/40">
      {/* Header */}
      <div className="p-3.5 border-b border-border flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <Activity size={18} className="text-primary" />
          <h2 className="font-bold text-sm tracking-tight">Experiment Runs</h2>
        </div>
        <button
          type="button"
          className="flex items-center gap-1 px-2.5 py-1 rounded-lg bg-primary text-white text-xs font-medium hover:bg-primary-hover transition-colors"
          onClick={onNewRun}
          title="Launch Mock / New Experiment Run"
        >
          <Plus size={13} />
          <span>New Run</span>
        </button>
      </div>

      {/* Search & Filter */}
      <div className="p-2.5 border-b border-border/60 flex flex-col gap-2">
        <div className="relative">
          <Search size={13} className="absolute left-2.5 top-2 text-text-dim" />
          <input
            type="text"
            placeholder="Filter runs & tags..."
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            className="w-full bg-bg border border-border rounded-lg pl-7 pr-2.5 py-1 text-xs text-text focus:border-primary focus:outline-none"
          />
        </div>

        <div className="flex items-center justify-between text-xs">
          <div className="flex items-center gap-1">
            {(['all', 'running', 'completed'] as const).map((st) => (
              <button
                key={st}
                type="button"
                className={`px-2 py-0.5 rounded capitalize ${statusFilter === st ? 'bg-primary/20 text-primary font-medium' : 'text-text-dim hover:text-text'}`}
                onClick={() => onStatusFilterChange(st)}
              >
                {st}
              </button>
            ))}
          </div>

          {compareRunIds.length > 0 && (
            <button
              type="button"
              className={`flex items-center gap-1 px-2 py-0.5 rounded border text-[11px] ${
                isComparing ? 'bg-primary text-white border-primary' : 'bg-bg border-border text-primary'
              }`}
              onClick={onToggleCompareMode}
            >
              <GitCompare size={11} />
              <span>Compare ({compareRunIds.length})</span>
            </button>
          )}
        </div>
      </div>

      {/* Runs List */}
      <div className="flex-1 overflow-y-auto p-2 flex flex-col gap-1.5">
        {filteredRuns.map((r) => {
          const isSelected = selectedRunId === r.id && !isComparing;
          const isChecked = compareRunIds.includes(r.id);
          const progress = Math.round((r.current_step / r.total_steps) * 100);

          return (
            <div
              key={r.id}
              className={`p-3 rounded-xl border transition-all cursor-pointer flex flex-col gap-2 ${
                isSelected
                  ? 'bg-surface border-primary ring-1 ring-primary/40 shadow-sm'
                  : 'bg-surface/50 border-border hover:bg-surface hover:border-border/80'
              }`}
              onClick={() => onSelectRun(r.id)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  onSelectRun(r.id);
                }
              }}
              role="button"
              tabIndex={0}
            >
              <div className="flex items-start justify-between gap-1.5">
                <div className="flex items-center gap-1.5 min-w-0">
                  <input
                    type="checkbox"
                    checked={isChecked}
                    onChange={(e) => {
                      e.stopPropagation();
                      onToggleCompare(r.id);
                    }}
                    className="rounded border-border accent-primary cursor-pointer"
                    aria-label={`Compare ${r.name}`}
                  />
                  <span className="font-semibold text-xs text-text truncate">{r.name}</span>
                </div>
                <span className={`text-[10px] px-1.5 py-0.5 rounded border font-mono flex items-center gap-1 shrink-0 ${statusColor(r.status)}`}>
                  {statusIcon(r.status)}
                  {r.status}
                </span>
              </div>

              {/* Progress bar */}
              <div className="flex flex-col gap-1">
                <div className="flex justify-between text-[10px] text-text-dim font-mono">
                  <span>Step {r.current_step}/{r.total_steps}</span>
                  <span>{progress}%</span>
                </div>
                <div className="w-full h-1 bg-bg rounded-full overflow-hidden">
                  <div
                    className="h-full bg-primary transition-all duration-300"
                    style={{ width: `${progress}%` }}
                  />
                </div>
              </div>

              <div className="flex items-center justify-between text-[11px] text-text-dim">
                <span>Val Loss: <strong className="text-text font-mono">{r.best_val_loss.toFixed(3)}</strong></span>
                <span>{r.hyperparameters.model_architecture}</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

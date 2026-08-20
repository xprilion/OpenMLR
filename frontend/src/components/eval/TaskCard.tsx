import { useState } from 'react';
import { 
  FileCheck, 
  Zap, 
  Lightbulb, 
  ChevronDown, 
  ChevronUp, 
  Clock, 
  Target, 
  Cpu
} from 'lucide-react';
import type { EvalTaskInfo } from '../../types';

interface Props {
  task: EvalTaskInfo;
  onEvaluate?: (taskId: string) => void;
}

export function TaskCard({ task, onEvaluate }: Readonly<Props>) {
  const [expanded, setExpanded] = useState(false);

  const getCategoryIcon = () => {
    switch (task.category) {
      case 'reproduction':
        return <FileCheck size={16} className="text-primary" />;
      case 'optimization':
        return <Zap size={16} className="text-amber-400" />;
      case 'hypothesis':
        return <Lightbulb size={16} className="text-emerald-400" />;
      default:
        return <Target size={16} className="text-text-dim" />;
    }
  };

  const getDifficultyBadge = () => {
    switch (task.difficulty) {
      case 'easy':
        return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30';
      case 'medium':
        return 'bg-amber-500/10 text-amber-400 border-amber-500/30';
      case 'hard':
        return 'bg-rose-500/10 text-rose-400 border-rose-500/30';
      default:
        return 'bg-surface-hover text-text-dim border-border';
    }
  };

  return (
    <div className="bg-surface border border-border rounded-xl p-4 shadow-xs hover:border-border-hover transition-all">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2.5">
        <div className="flex items-start gap-3 min-w-0">
          <div className="w-8 h-8 rounded-lg bg-bg border border-border flex items-center justify-center shrink-0 mt-0.5">
            {getCategoryIcon()}
          </div>
          <div className="min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <h4 className="text-xs sm:text-sm font-semibold text-text truncate">{task.name}</h4>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-surface-hover text-text-dim border border-border">
                {task.task_id}
              </span>
              <span className={`text-[10px] uppercase font-bold px-2 py-0.5 rounded-md border ${getDifficultyBadge()}`}>
                {task.difficulty}
              </span>
            </div>
            <p className="text-xs text-text-dim mt-0.5 line-clamp-1">{task.description}</p>
          </div>
        </div>

        <div className="flex items-center gap-2 self-end sm:self-auto shrink-0">
          <div className="flex items-center gap-1 text-[11px] text-text-dim bg-bg px-2 py-1 rounded-md border border-border">
            <Clock size={12} />
            <span>{task.timeout_seconds}s</span>
          </div>

          {onEvaluate && (
            <button
              type="button"
              onClick={() => onEvaluate(task.task_id)}
              className="px-2.5 py-1 rounded-lg bg-primary/10 hover:bg-primary/20 text-primary border border-primary/30 text-xs font-semibold transition-colors"
            >
              Test
            </button>
          )}

          <button
            type="button"
            onClick={() => setExpanded(!expanded)}
            className="p-1 text-text-dim hover:text-text hover:bg-surface-hover rounded-md transition-colors"
          >
            {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
          </button>
        </div>
      </div>

      {/* Expanded details */}
      {expanded && (
        <div className="mt-3 pt-3 border-t border-border/60 text-xs space-y-3">
          <p className="text-text-dim leading-relaxed bg-bg/50 p-2.5 rounded-lg border border-border/40">
            {task.description}
          </p>

          {/* Paper reproduction specs */}
          {task.paper_title && (
            <div className="p-2.5 bg-bg/80 border border-border rounded-lg space-y-1.5">
              <div className="flex items-center justify-between">
                <span className="font-semibold text-text">Target Paper: {task.paper_title}</span>
                {task.dataset_name && (
                  <span className="text-[10px] px-1.5 py-0.5 rounded bg-surface text-text-dim border border-border">
                    Dataset: {task.dataset_name}
                  </span>
                )}
              </div>
              {task.target_metrics && (
                <div className="flex flex-wrap gap-1.5 pt-1">
                  {Object.entries(task.target_metrics).map(([k, v]) => (
                    <span key={k} className="text-[11px] px-2 py-0.5 bg-primary/10 text-primary rounded border border-primary/20 font-mono">
                      {k}: {typeof v === 'number' ? v.toFixed(3) : v}
                    </span>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Optimization specs */}
          {task.kernel_name && (
            <div className="p-2.5 bg-bg/80 border border-border rounded-lg space-y-1.5">
              <div className="flex items-center justify-between">
                <span className="font-semibold text-amber-400 flex items-center gap-1.5">
                  <Cpu size={14} />
                  Kernel: {task.kernel_name} ({task.framework || 'triton'})
                </span>
                {task.target_speedup && (
                  <span className="text-[11px] font-bold text-emerald-400">
                    Target Speedup: {task.target_speedup}x
                  </span>
                )}
              </div>
              {task.baseline_latency_ms && (
                <div className="text-[11px] text-text-dim">
                  Baseline Latency: <span className="font-mono text-text">{task.baseline_latency_ms} ms</span>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

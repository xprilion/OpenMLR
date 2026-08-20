import { 
  CheckCircle2, 
  XCircle, 
  Clock, 
  BarChart3, 
  Download, 
  Award,
  AlertTriangle 
} from 'lucide-react';
import type { EvalSuiteRunResult } from '../../types';

interface Props {
  runResult: EvalSuiteRunResult;
}

export function SuiteRunSummary({ runResult }: Readonly<Props>) {
  const isHighPass = runResult.pass_rate >= 0.8;
  const isMedPass = runResult.pass_rate >= 0.5;

  const getScoreColor = (score: number) => {
    if (score >= 0.8) return 'text-emerald-400';
    if (score >= 0.5) return 'text-amber-400';
    return 'text-rose-400';
  };

  const handleDownload = () => {
    const jsonStr = JSON.stringify(runResult, null, 2);
    const blob = new Blob([jsonStr], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `benchmark_${runResult.suite_name}_${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="bg-surface border border-primary/30 rounded-2xl p-6 shadow-lg space-y-6">
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-5 border-b border-border">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xs uppercase font-mono tracking-wider text-primary font-semibold">
              Benchmark Suite Results
            </span>
            <span className="text-xs px-2 py-0.5 rounded-full bg-surface-hover border border-border text-text font-mono capitalize">
              {runResult.suite_name}
            </span>
          </div>
          <h3 className="text-lg font-bold text-text mt-1">Harness Evaluation Summary</h3>
        </div>

        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={handleDownload}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-surface hover:bg-surface-hover border border-border text-xs font-medium text-text-dim hover:text-text transition-colors"
          >
            <Download size={14} />
            <span>Export JSON</span>
          </button>
        </div>
      </div>

      {/* Metric Cards Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="bg-bg border border-border rounded-xl p-3.5 flex flex-col">
          <span className="text-xs text-text-dim flex items-center gap-1">
            <Award size={13} className="text-primary" />
            Composite Score
          </span>
          <span className={`text-xl font-bold mt-1 ${getScoreColor(runResult.average_score)}`}>
            {(runResult.average_score * 100).toFixed(1)}%
          </span>
        </div>

        <div className="bg-bg border border-border rounded-xl p-3.5 flex flex-col">
          <span className="text-xs text-text-dim flex items-center gap-1">
            <BarChart3 size={13} className="text-emerald-400" />
            Pass Rate
          </span>
          <span className={`text-xl font-bold mt-1 ${isHighPass ? 'text-emerald-400' : isMedPass ? 'text-amber-400' : 'text-rose-400'}`}>
            {(runResult.pass_rate * 100).toFixed(0)}% ({runResult.passed_tasks}/{runResult.total_tasks})
          </span>
        </div>

        <div className="bg-bg border border-border rounded-xl p-3.5 flex flex-col">
          <span className="text-xs text-text-dim flex items-center gap-1">
            <CheckCircle2 size={13} className="text-emerald-400" />
            Passed Tasks
          </span>
          <span className="text-xl font-bold text-text mt-1">
            {runResult.passed_tasks}
          </span>
        </div>

        <div className="bg-bg border border-border rounded-xl p-3.5 flex flex-col">
          <span className="text-xs text-text-dim flex items-center gap-1">
            <Clock size={13} className="text-amber-400" />
            Total Duration
          </span>
          <span className="text-xl font-bold text-text mt-1 font-mono">
            {runResult.execution_time_seconds.toFixed(2)}s
          </span>
        </div>
      </div>

      {/* Task Breakdown */}
      <div className="space-y-3 pt-2">
        <h4 className="text-xs font-semibold text-text uppercase tracking-wider">
          Task Execution Breakdown ({runResult.results.length})
        </h4>

        <div className="space-y-2.5">
          {runResult.results.map((res) => (
            <div
              key={res.task_id}
              className={`p-3.5 rounded-xl border transition-all ${
                res.passed 
                  ? 'bg-emerald-500/5 border-emerald-500/20' 
                  : 'bg-rose-500/5 border-rose-500/20'
              }`}
            >
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                <div className="flex items-center gap-2.5">
                  {res.passed ? (
                    <CheckCircle2 size={16} className="text-emerald-400 shrink-0" />
                  ) : (
                    <XCircle size={16} className="text-rose-400 shrink-0" />
                  )}
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-semibold text-text">{res.task_name}</span>
                      <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-surface border border-border text-text-dim">
                        {res.task_id}
                      </span>
                      <span className="text-[10px] capitalize px-1.5 py-0.5 rounded bg-surface border border-border text-text-dim">
                        {res.category}
                      </span>
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-3 self-end sm:self-auto text-xs">
                  <span className={`font-bold ${getScoreColor(res.score)}`}>
                    Score: {(res.score * 100).toFixed(1)}%
                  </span>
                  <span className="text-text-dim font-mono">
                    {res.execution_time_seconds.toFixed(2)}s
                  </span>
                </div>
              </div>

              {/* Metric items */}
              {res.metrics && res.metrics.length > 0 && (
                <div className="mt-2.5 pt-2 border-t border-border/40 flex flex-wrap gap-2">
                  {res.metrics.map((m) => (
                    <div
                      key={m.metric_name}
                      className="text-[11px] px-2 py-1 rounded-md bg-bg border border-border flex items-center gap-1.5 font-mono"
                    >
                      <span className="text-text-dim">{m.metric_name}:</span>
                      <span className="font-semibold text-text">
                        {typeof m.achieved_value === 'number' ? m.achieved_value.toFixed(3) : m.achieved_value}
                      </span>
                      <span className="text-text-dim text-[10px]">
                        (target: {m.target_value})
                      </span>
                      {m.passed ? (
                        <span className="text-emerald-400 text-[10px] font-bold">✓</span>
                      ) : (
                        <span className="text-rose-400 text-[10px] font-bold">✗</span>
                      )}
                    </div>
                  ))}
                </div>
              )}

              {/* Error message */}
              {res.error && (
                <div className="mt-2 text-xs text-rose-400 flex items-center gap-1.5">
                  <AlertTriangle size={12} className="shrink-0" />
                  <span>{res.error}</span>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

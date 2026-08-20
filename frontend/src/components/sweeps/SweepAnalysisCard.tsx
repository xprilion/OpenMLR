import React from 'react';
import type { SweepAnalysis, SweepConfig } from './types';
import { Award, Zap, BarChart2, Layers } from 'lucide-react';

interface SweepAnalysisCardProps {
  sweep: SweepConfig;
  analysis: SweepAnalysis | null;
}

export const SweepAnalysisCard: React.FC<SweepAnalysisCardProps> = ({ sweep, analysis }) => {
  if (!analysis || analysis.completed_trials === 0) {
    return (
      <div className="bg-surface border border-border rounded-lg p-6 text-center text-text-dim">
        <Layers className="w-8 h-8 mx-auto mb-2 text-text-dim/60" />
        <p className="text-sm">Run trials to unlock parameter sensitivity analysis and Pareto optimization insights.</p>
      </div>
    );
  }

  const bestTrial = analysis.best_trial;
  const importanceEntries = Object.entries(analysis.parameter_importance || {});

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
      {/* Optimal Configuration Card */}
      <div className="bg-surface border border-border rounded-lg p-4 flex flex-col gap-3">
        <div className="flex items-center justify-between">
          <h4 className="text-sm font-semibold text-text flex items-center gap-2">
            <Award className="w-4 h-4 text-amber-400" />
            Optimal Configuration
          </h4>
          {bestTrial && (
            <span className="text-xs bg-primary/10 text-primary border border-primary/20 px-2 py-0.5 rounded font-mono">
              Trial #{bestTrial.trial_number} ({bestTrial.trial_id})
            </span>
          )}
        </div>

        {bestTrial ? (
          <div className="flex flex-col gap-2">
            <div className="bg-bg/60 p-3 rounded border border-border flex items-center justify-between">
              <span className="text-xs text-text-dim">Best {sweep.objective_metric}</span>
              <span className="text-base font-mono font-bold text-emerald-400">
                {bestTrial.objective_value !== undefined ? bestTrial.objective_value.toFixed(4) : '-'}
              </span>
            </div>

            <div className="text-xs font-semibold text-text-dim mt-1">Best Hyperparameters</div>
            <div className="grid grid-cols-2 gap-2">
              {Object.entries(bestTrial.parameters).map(([k, v]) => (
                <div key={k} className="bg-bg/40 border border-border/70 p-2 rounded flex flex-col">
                  <span className="text-[11px] text-text-dim font-mono">{k}</span>
                  <span className="text-xs font-semibold text-text mt-0.5 truncate">{String(v)}</span>
                </div>
              ))}
            </div>
          </div>
        ) : (
          <p className="text-xs text-text-dim">No completed trial yet.</p>
        )}
      </div>

      {/* Parameter Sensitivity & Importance */}
      <div className="bg-surface border border-border rounded-lg p-4 flex flex-col gap-3">
        <div className="flex items-center justify-between">
          <h4 className="text-sm font-semibold text-text flex items-center gap-2">
            <BarChart2 className="w-4 h-4 text-primary" />
            Parameter Sensitivity & Importance
          </h4>
          <span className="text-xs text-text-dim">Variance & Spearman Rank</span>
        </div>

        {importanceEntries.length > 0 ? (
          <div className="flex flex-col gap-3">
            {importanceEntries.map(([param, imp]) => {
              const corr = analysis.correlations[param] ?? 0;
              const pct = Math.round(imp * 100);
              return (
                <div key={param} className="flex flex-col gap-1">
                  <div className="flex items-center justify-between text-xs font-mono">
                    <span className="text-text font-medium">{param}</span>
                    <span className="text-text-dim">
                      {pct}% imp | corr: <span className={corr >= 0 ? 'text-emerald-400' : 'text-rose-400'}>{corr > 0 ? `+${corr}` : corr}</span>
                    </span>
                  </div>
                  <div className="w-full bg-border h-2 rounded-full overflow-hidden">
                    <div
                      className="bg-primary h-full rounded-full transition-all duration-300"
                      style={{ width: `${Math.max(5, Math.min(100, pct))}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <p className="text-xs text-text-dim">Insufficient trial data for sensitivity breakdown.</p>
        )}
      </div>

      {/* Pareto Frontier Summary */}
      {analysis.pareto_frontier && analysis.pareto_frontier.length > 0 && (
        <div className="bg-surface border border-border rounded-lg p-4 col-span-1 lg:col-span-2 flex flex-col gap-2">
          <div className="flex items-center justify-between">
            <h4 className="text-sm font-semibold text-text flex items-center gap-2">
              <Zap className="w-4 h-4 text-amber-400" />
              Pareto Non-Dominated Frontier (Metric vs Runtime Trade-Offs)
            </h4>
            <span className="text-xs text-text-dim">{analysis.pareto_frontier.length} optimal trade-off trials</span>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2 mt-1">
            {analysis.pareto_frontier.map((pt) => (
              <div key={pt.trial_id} className="bg-bg/40 border border-border p-2 rounded flex flex-col gap-1">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-mono text-primary font-medium">{pt.trial_id}</span>
                  <span className="text-emerald-400 font-mono font-semibold">
                    {sweep.objective_metric}: {pt.objective_value?.toFixed(4)}
                  </span>
                </div>
                <span className="text-[11px] text-text-dim">Runtime: {pt.duration_seconds.toFixed(1)}s</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

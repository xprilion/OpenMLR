import { X, Trophy, CheckCircle, Scale } from 'lucide-react';
import type { ModelComparisonResult } from './types';

interface Props {
  readonly comparison: ModelComparisonResult | null;
  readonly isLoading: boolean;
  readonly onClose: () => void;
}

export function ModelComparisonModal({ comparison, isLoading, onClose }: Readonly<Props>) {
  if (!comparison && !isLoading) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4 overflow-y-auto"
      role="dialog"
      aria-modal="true"
      aria-labelledby="model-comp-modal-title"
    >
      <div className="bg-surface border border-border rounded-xl shadow-2xl w-full max-w-4xl overflow-hidden my-8 flex flex-col max-h-[85vh]">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-border bg-surface-hover/30 shrink-0">
          <div className="flex items-center gap-2">
            <div className="p-2 rounded-lg bg-primary/10 text-primary">
              <Scale size={20} />
            </div>
            <div>
              <h2 id="model-comp-modal-title" className="text-base font-semibold text-text">
                Model Artifact Comparison Analysis
              </h2>
              <p className="text-xs text-text-dim">
                Side-by-side empirical performance, parameter capacity, and architecture trade-offs
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1 rounded-lg text-text-dim hover:text-text hover:bg-surface-hover transition-colors"
            aria-label="Close dialog"
          >
            <X size={18} />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 flex-1 overflow-y-auto space-y-6">
          {isLoading || !comparison ? (
            <div className="flex items-center justify-center py-16 text-text-dim">
              <span>Comparing model artifacts...</span>
            </div>
          ) : (
            <>
              {/* Recommendation Callout */}
              <div className="p-4 rounded-xl bg-primary/10 border border-primary/20 flex items-start gap-3">
                <div className="p-2 rounded-lg bg-primary/20 text-primary shrink-0 mt-0.5">
                  <Trophy size={20} />
                </div>
                <div>
                  <h4 className="text-sm font-semibold text-text flex items-center gap-2">
                    <span>Autonomous Recommendation</span>
                    <span className="text-[10px] px-2 py-0.5 rounded-full bg-primary text-white font-mono">
                      {comparison.recommended_model_id}
                    </span>
                  </h4>
                  <p className="text-xs text-text-dim mt-1">{comparison.recommendation_reason}</p>
                </div>
              </div>

              {/* Models Comparison Table */}
              <div className="rounded-lg border border-border overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-bg text-text-dim border-b border-border">
                    <tr>
                      <th className="px-4 py-3 font-medium">Attribute / Metric</th>
                      {comparison.compared_models.map((m) => {
                        const isRecommended = m.id === comparison.recommended_model_id;
                        return (
                          <th key={m.id} className="px-4 py-3 font-medium">
                            <div className="flex items-center gap-1.5">
                              <span className="font-bold text-text">{m.name}</span>
                              {isRecommended && <CheckCircle size={14} className="text-primary shrink-0" />}
                            </div>
                            <span className="text-[10px] text-text-dim block font-mono">v{m.version}</span>
                          </th>
                        );
                      })}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border text-text text-xs">
                    <tr>
                      <td className="px-4 py-2.5 font-medium text-text-dim bg-bg/50">Architecture</td>
                      {comparison.compared_models.map((m) => (
                        <td key={m.id} className="px-4 py-2.5 font-mono">
                          {m.architecture} ({m.framework})
                        </td>
                      ))}
                    </tr>
                    <tr>
                      <td className="px-4 py-2.5 font-medium text-text-dim bg-bg/50">Parameters</td>
                      {comparison.compared_models.map((m) => (
                        <td key={m.id} className="px-4 py-2.5 font-mono font-bold">
                          {m.parameters_count.toLocaleString()}
                        </td>
                      ))}
                    </tr>
                    <tr>
                      <td className="px-4 py-2.5 font-medium text-text-dim bg-bg/50">Artifact Size</td>
                      {comparison.compared_models.map((m) => (
                        <td key={m.id} className="px-4 py-2.5 font-mono">
                          {m.model_size_mb.toFixed(1)} MB
                        </td>
                      ))}
                    </tr>
                    <tr>
                      <td className="px-4 py-2.5 font-medium text-text-dim bg-bg/50">Status</td>
                      {comparison.compared_models.map((m) => (
                        <td key={m.id} className="px-4 py-2.5 uppercase text-[10px] font-bold text-primary">
                          {m.status}
                        </td>
                      ))}
                    </tr>

                    {/* Dynamic Metrics Rows */}
                    {Object.keys(comparison.metric_matrix).map((metricName) => (
                      <tr key={metricName}>
                        <td className="px-4 py-2.5 font-medium text-text-dim bg-bg/50">
                          Metric: <code className="text-text font-bold">{metricName}</code>
                        </td>
                        {comparison.compared_models.map((m) => {
                          const val = comparison.metric_matrix[metricName]?.[m.id];
                          return (
                            <td key={m.id} className="px-4 py-2.5 font-mono font-bold text-emerald-400">
                              {val !== undefined && val !== null ? (typeof val === 'number' ? val.toFixed(4) : val) : 'N/A'}
                            </td>
                          );
                        })}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </div>

        {/* Footer */}
        <div className="flex justify-end px-6 py-4 border-t border-border bg-surface shrink-0">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-sm rounded-lg bg-surface border border-border text-text hover:bg-surface-hover transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}

import { useMemo } from 'react';
import { GitCompare } from 'lucide-react';
import type { ExperimentRun, MetricSeries, RunStatus } from './types';
import { MetricCharts } from './MetricCharts';

interface RunComparisonViewProps {
  readonly runs: readonly ExperimentRun[];
  readonly compareRunIds: readonly string[];
  readonly onClose: () => void;
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

export function RunComparisonView({
  runs,
  compareRunIds,
  onClose,
}: Readonly<RunComparisonViewProps>) {
  const selectedRunsList = useMemo(() => {
    return runs.filter((r) => compareRunIds.includes(r.id));
  }, [runs, compareRunIds]);

  const comparisonSeries: MetricSeries[] = useMemo(() => {
    const colors = ['#1288ff', '#10b981', '#f59e0b', '#ec4899', '#8b5cf6'];
    return selectedRunsList.map((r, idx) => ({
      id: r.id,
      name: `${r.name} (Train Loss)`,
      color: colors[idx % colors.length],
      data: r.metrics.train_loss,
    }));
  }, [selectedRunsList]);

  return (
    <div className="flex-1 overflow-y-auto p-6 flex flex-col gap-6">
      <div className="flex items-center justify-between border-b border-border pb-4">
        <div className="flex items-center gap-2">
          <GitCompare size={20} className="text-primary" />
          <h3 className="text-lg font-bold text-text">
            Comparing {compareRunIds.length} Experiment Runs
          </h3>
        </div>
        <button
          type="button"
          className="px-3 py-1.5 rounded-lg border border-border bg-surface text-xs text-text-dim hover:text-text"
          onClick={onClose}
        >
          Back to Single Run
        </button>
      </div>

      <MetricCharts
        title="Multi-Run Training Loss Comparison"
        series={comparisonSeries}
        height={320}
      />

      {/* Hyperparameters Comparison Matrix */}
      <div className="bg-surface border border-border rounded-xl p-5 flex flex-col gap-3">
        <h4 className="font-semibold text-sm text-text">Hyperparameters & Scores Matrix</h4>
        <div className="overflow-x-auto">
          <table className="w-full text-xs text-left border-collapse">
            <thead>
              <tr className="border-b border-border/80 text-text-dim">
                <th className="p-2 font-medium">Metric / Param</th>
                {selectedRunsList.map((r) => (
                  <th key={r.id} className="p-2 font-semibold text-text">{r.name}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-border/40 font-mono">
              <tr>
                <td className="p-2 text-text-dim">Status</td>
                {selectedRunsList.map((r) => (
                  <td key={r.id} className="p-2">
                    <span className={`px-1.5 py-0.5 rounded text-[10px] ${statusColor(r.status)}`}>
                      {r.status}
                    </span>
                  </td>
                ))}
              </tr>
              <tr>
                <td className="p-2 text-text-dim">Best Val Loss</td>
                {selectedRunsList.map((r) => (
                  <td key={r.id} className="p-2 font-bold text-primary">
                    {r.best_val_loss.toFixed(4)}
                  </td>
                ))}
              </tr>
              <tr>
                <td className="p-2 text-text-dim">Best Val Accuracy</td>
                {selectedRunsList.map((r) => (
                  <td key={r.id} className="p-2 font-bold text-text">
                    {r.best_val_accuracy ? `${(r.best_val_accuracy * 100).toFixed(1)}%` : '—'}
                  </td>
                ))}
              </tr>
              <tr>
                <td className="p-2 text-text-dim">Model Arch</td>
                {selectedRunsList.map((r) => (
                  <td key={r.id} className="p-2">{r.hyperparameters.model_architecture}</td>
                ))}
              </tr>
              <tr>
                <td className="p-2 text-text-dim">Learning Rate</td>
                {selectedRunsList.map((r) => (
                  <td key={r.id} className="p-2">{r.hyperparameters.learning_rate}</td>
                ))}
              </tr>
              <tr>
                <td className="p-2 text-text-dim">Batch Size</td>
                {selectedRunsList.map((r) => (
                  <td key={r.id} className="p-2">{r.hyperparameters.batch_size}</td>
                ))}
              </tr>
              <tr>
                <td className="p-2 text-text-dim">Optimizer</td>
                {selectedRunsList.map((r) => (
                  <td key={r.id} className="p-2">{r.hyperparameters.optimizer}</td>
                ))}
              </tr>
              <tr>
                <td className="p-2 text-text-dim">Precision</td>
                {selectedRunsList.map((r) => (
                  <td key={r.id} className="p-2 uppercase">{r.hyperparameters.precision || 'fp32'}</td>
                ))}
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

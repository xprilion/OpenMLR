import React, { useState, useMemo } from 'react';
import type { SweepConfig, Trial } from './types';
import { Search, CheckCircle2, Clock, XCircle, AlertTriangle, Play } from 'lucide-react';

interface SweepTrialsTableProps {
  sweep: SweepConfig;
  onSuggestTrial?: () => void;
  suggesting?: boolean;
}

export const SweepTrialsTable: React.FC<SweepTrialsTableProps> = ({
  sweep,
  onSuggestTrial,
  suggesting = false,
}) => {
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [selectedTrial, setSelectedTrial] = useState<Trial | null>(null);

  const filteredTrials = useMemo(() => {
    return sweep.trials.filter((t) => {
      if (statusFilter !== 'all' && t.status !== statusFilter) return false;
      if (!search.trim()) return true;
      const s = search.toLowerCase();
      if (t.trial_id.toLowerCase().includes(s)) return true;
      return Object.entries(t.parameters).some(
        ([k, v]) => k.toLowerCase().includes(s) || String(v).toLowerCase().includes(s)
      );
    });
  }, [sweep.trials, statusFilter, search]);

  const getStatusPill = (status: Trial['status']) => {
    switch (status) {
      case 'completed':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <CheckCircle2 className="w-3 h-3" />
            completed
          </span>
        );
      case 'running':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-primary/10 text-primary border border-primary/20">
            <Clock className="w-3 h-3 animate-spin" />
            running
          </span>
        );
      case 'pruned':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-amber-500/10 text-amber-400 border border-amber-500/20">
            <AlertTriangle className="w-3 h-3" />
            pruned
          </span>
        );
      case 'failed':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-rose-500/10 text-rose-400 border border-rose-500/20">
            <XCircle className="w-3 h-3" />
            failed
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-text-dim/10 text-text-dim border border-text-dim/20">
            {status}
          </span>
        );
    }
  };

  return (
    <div className="bg-surface border border-border rounded-lg p-4 flex flex-col gap-3">
      {/* Controls Header */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2 flex-1 max-w-sm">
          <div className="relative w-full">
            <Search className="w-4 h-4 absolute left-2.5 top-2.5 text-text-dim" />
            <input
              type="text"
              placeholder="Search trials or parameters..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-8 pr-3 py-1.5 bg-bg border border-border rounded text-xs text-text placeholder-text-dim focus:outline-none focus:border-primary"
            />
          </div>
        </div>

        <div className="flex items-center gap-2">
          {['all', 'completed', 'running', 'pruned', 'failed'].map((st) => (
            <button
              key={st}
              type="button"
              onClick={() => setStatusFilter(st)}
              className={`px-2.5 py-1 rounded text-xs capitalize transition-colors ${
                statusFilter === st
                  ? 'bg-primary text-white font-medium'
                  : 'bg-bg text-text-dim hover:text-text border border-border'
              }`}
            >
              {st}
            </button>
          ))}

          {onSuggestTrial && (
            <button
              type="button"
              disabled={suggesting || sweep.trials.length >= sweep.max_trials}
              onClick={onSuggestTrial}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-primary hover:bg-primary/90 text-white rounded text-xs font-medium transition-colors disabled:opacity-50"
            >
              <Play className="w-3 h-3" />
              {suggesting ? 'Sampling...' : 'Suggest Next Trial'}
            </button>
          )}
        </div>
      </div>

      {/* Trials Table */}
      <div className="overflow-x-auto border border-border rounded-lg">
        <table className="w-full text-left text-xs">
          <thead className="bg-bg/80 border-b border-border text-text-dim">
            <tr>
              <th className="px-3 py-2 font-medium">Trial</th>
              <th className="px-3 py-2 font-medium">Status</th>
              <th className="px-3 py-2 font-medium">{sweep.objective_metric}</th>
              <th className="px-3 py-2 font-medium">Hyperparameters</th>
              <th className="px-3 py-2 font-medium">Runtime</th>
              <th className="px-3 py-2 font-medium text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {filteredTrials.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-3 py-6 text-center text-text-dim">
                  No trials matching current filter criteria.
                </td>
              </tr>
            ) : (
              filteredTrials.map((t) => (
                <tr key={t.trial_id} className="hover:bg-bg/40 transition-colors">
                  <td className="px-3 py-2.5 font-mono font-medium text-text">
                    #{t.trial_number} ({t.trial_id})
                  </td>
                  <td className="px-3 py-2.5">{getStatusPill(t.status)}</td>
                  <td className="px-3 py-2.5 font-mono font-bold text-emerald-400">
                    {t.objective_value !== undefined ? t.objective_value.toFixed(4) : '-'}
                  </td>
                  <td className="px-3 py-2.5">
                    <div className="flex flex-wrap gap-1 max-w-md">
                      {Object.entries(t.parameters).map(([k, v]) => (
                        <span
                          key={k}
                          className="bg-bg border border-border px-1.5 py-0.5 rounded font-mono text-[10px] text-text-dim"
                        >
                          <span className="text-text">{k}</span>={String(v)}
                        </span>
                      ))}
                    </div>
                  </td>
                  <td className="px-3 py-2.5 text-text-dim font-mono">{t.duration_seconds.toFixed(1)}s</td>
                  <td className="px-3 py-2.5 text-right">
                    <button
                      type="button"
                      onClick={() => setSelectedTrial(t)}
                      className="text-primary hover:underline text-xs font-medium"
                    >
                      Details
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Trial Details Modal */}
      {selectedTrial && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="bg-surface border border-border rounded-xl max-w-lg w-full p-5 flex flex-col gap-4 max-h-[85vh] overflow-y-auto">
            <div className="flex items-center justify-between border-b border-border pb-3">
              <h3 className="text-sm font-semibold text-text">
                Trial Details: {selectedTrial.trial_id} (#{selectedTrial.trial_number})
              </h3>
              <button
                type="button"
                onClick={() => setSelectedTrial(null)}
                className="text-text-dim hover:text-text text-sm"
              >
                ✕
              </button>
            </div>

            <div className="flex flex-col gap-3 text-xs">
              <div className="flex items-center justify-between">
                <span className="text-text-dim">Status:</span>
                {getStatusPill(selectedTrial.status)}
              </div>
              <div className="flex items-center justify-between">
                <span className="text-text-dim">Objective Metric ({sweep.objective_metric}):</span>
                <span className="font-mono font-bold text-emerald-400">
                  {selectedTrial.objective_value !== undefined ? selectedTrial.objective_value : 'None'}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-text-dim">Duration:</span>
                <span className="font-mono">{selectedTrial.duration_seconds} seconds</span>
              </div>

              <div className="border-t border-border pt-2 flex flex-col gap-1.5">
                <span className="font-semibold text-text">Parameters:</span>
                <pre className="bg-bg p-2.5 rounded border border-border text-[11px] font-mono overflow-x-auto text-text-dim">
                  {JSON.stringify(selectedTrial.parameters, null, 2)}
                </pre>
              </div>

              {selectedTrial.metrics && Object.keys(selectedTrial.metrics).length > 0 && (
                <div className="border-t border-border pt-2 flex flex-col gap-1.5">
                  <span className="font-semibold text-text">Recorded Metrics:</span>
                  <pre className="bg-bg p-2.5 rounded border border-border text-[11px] font-mono overflow-x-auto text-text-dim">
                    {JSON.stringify(selectedTrial.metrics, null, 2)}
                  </pre>
                </div>
              )}
            </div>

            <div className="flex justify-end pt-2">
              <button
                type="button"
                onClick={() => setSelectedTrial(null)}
                className="px-4 py-1.5 bg-border hover:bg-border/80 text-text rounded text-xs font-medium"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

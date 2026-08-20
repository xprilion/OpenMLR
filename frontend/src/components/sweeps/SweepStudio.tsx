import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../../api';
import type { SweepConfig, SweepAnalysis } from './types';
import { SweepTrialsTable } from './SweepTrialsTable';
import { SweepParallelCoordinates } from './SweepParallelCoordinates';
import { SweepAnalysisCard } from './SweepAnalysisCard';
import { NewSweepModal } from './NewSweepModal';
import {
  Sliders,
  Plus,
  RefreshCw,
  FileDown,
  Trash2,
  Activity,
  Layers,
  BarChart,
  Table,
} from 'lucide-react';

interface SweepStudioProps {
  projectId?: string;
}

export const SweepStudio: React.FC<SweepStudioProps> = ({ projectId = 'default' }) => {
  const [sweeps, setSweeps] = useState<SweepConfig[]>([]);
  const [selectedSweepId, setSelectedSweepId] = useState<string | null>(null);
  const [selectedSweep, setSelectedSweep] = useState<SweepConfig | null>(null);
  const [analysis, setAnalysis] = useState<SweepAnalysis | null>(null);
  const [activeTab, setActiveTab] = useState<'trials' | 'parallel_coords' | 'analysis'>('trials');
  const [loading, setLoading] = useState<boolean>(true);
  const [isModalOpen, setIsModalOpen] = useState<boolean>(false);
  const [suggesting, setSuggesting] = useState<boolean>(false);
  const [exporting, setExporting] = useState<boolean>(false);

  const loadSweeps = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.listSweeps(projectId);
      const list = data.sweeps || [];
      setSweeps(list);
      if (list.length > 0) {
        if (!selectedSweepId || !list.some((s: SweepConfig) => s.sweep_id === selectedSweepId)) {
          setSelectedSweepId(list[0].sweep_id);
        }
      } else {
        setSelectedSweepId(null);
        setSelectedSweep(null);
        setAnalysis(null);
      }
    } catch (e) {
      console.error('Failed to load sweeps', e);
    } finally {
      setLoading(false);
    }
  }, [projectId, selectedSweepId]);

  const loadSweepDetails = useCallback(async (sId: string) => {
    try {
      const [sweepRes, analysisRes] = await Promise.all([
        api.getSweep(projectId, sId),
        api.getSweepAnalysis(projectId, sId),
      ]);
      setSelectedSweep(sweepRes.sweep || null);
      setAnalysis(analysisRes.analysis || null);
    } catch (e) {
      console.error('Failed to load sweep details or analysis', e);
    }
  }, [projectId]);

  useEffect(() => {
    loadSweeps();
  }, [loadSweeps]);

  useEffect(() => {
    if (selectedSweepId) {
      loadSweepDetails(selectedSweepId);
    }
  }, [selectedSweepId, loadSweepDetails]);

  const handleCreateSweep = async (payload: Record<string, unknown>) => {
    const res = await api.createSweep(projectId, payload);
    if (res.sweep) {
      await loadSweeps();
      setSelectedSweepId(res.sweep.sweep_id);
    }
  };

  const handleSuggestTrial = async () => {
    if (!selectedSweepId) return;
    setSuggesting(true);
    try {
      await api.suggestTrial(projectId, selectedSweepId);
      await loadSweepDetails(selectedSweepId);
    } catch (e) {
      console.error('Failed to suggest trial', e);
    } finally {
      setSuggesting(false);
    }
  };

  const handleExportReport = async () => {
    if (!selectedSweepId) return;
    setExporting(true);
    try {
      const res = await api.exportSweepReport(projectId, selectedSweepId);
      if (res.report) {
        const blob = new Blob([res.report], { type: 'text/markdown' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `sweep_${selectedSweepId}_report.md`;
        a.click();
        URL.revokeObjectURL(url);
      }
    } catch (e) {
      console.error('Failed to export sweep report', e);
    } finally {
      setExporting(false);
    }
  };

  const handleDeleteSweep = async () => {
    if (!selectedSweepId) return;
    if (!confirm('Are you sure you want to delete this sweep?')) return;
    try {
      await api.deleteSweep(projectId, selectedSweepId);
      await loadSweeps();
    } catch (e) {
      console.error('Failed to delete sweep', e);
    }
  };

  const completedCount = selectedSweep
    ? selectedSweep.trials.filter((t) => t.status === 'completed').length
    : 0;

  return (
    <div className="flex flex-col h-full bg-bg overflow-y-auto p-4 md:p-6 gap-4">
      {/* Header Banner */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border pb-4">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-primary/10 rounded-lg border border-primary/20">
            <Sliders className="w-5 h-5 text-primary" />
          </div>
          <div>
            <h2 className="text-base font-semibold text-text flex items-center gap-2">
              Hyperparameter Optimization Studio
            </h2>
            <p className="text-xs text-text-dim">
              Explore parameter spaces, run Bayesian/Hyperband sweeps, and track optimal model configurations.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={loadSweeps}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-surface hover:bg-border text-text border border-border rounded text-xs transition-colors"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
          <button
            type="button"
            onClick={() => setIsModalOpen(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-primary hover:bg-primary/90 text-white rounded text-xs font-medium transition-colors"
          >
            <Plus className="w-3.5 h-3.5" />
            New Sweep
          </button>
        </div>
      </div>

      {sweeps.length === 0 && !loading ? (
        <div className="bg-surface border border-border rounded-xl p-10 flex flex-col items-center justify-center text-center gap-3">
          <Layers className="w-10 h-10 text-text-dim" />
          <h3 className="text-sm font-semibold text-text">No Hyperparameter Sweeps Found</h3>
          <p className="text-xs text-text-dim max-w-md">
            Create your first search space with Grid, Random, Bayesian Optimization, or ASHA Hyperband.
          </p>
          <button
            type="button"
            onClick={() => setIsModalOpen(true)}
            className="mt-2 flex items-center gap-1.5 px-4 py-2 bg-primary text-white rounded text-xs font-medium"
          >
            <Plus className="w-3.5 h-3.5" />
            Create First Sweep
          </button>
        </div>
      ) : (
        <>
          {/* Sweep Selector & Overview Bar */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
            <div className="bg-surface border border-border p-3 rounded-lg flex flex-col justify-between">
              <span className="text-[11px] text-text-dim">Target Sweep</span>
              <select
                value={selectedSweepId || ''}
                onChange={(e) => setSelectedSweepId(e.target.value)}
                className="mt-1 bg-bg border border-border rounded px-2 py-1 text-xs text-text focus:outline-none focus:border-primary font-medium"
              >
                {sweeps.map((s) => (
                  <option key={s.sweep_id} value={s.sweep_id}>
                    {s.name} ({s.method.toUpperCase()})
                  </option>
                ))}
              </select>
            </div>

            <div className="bg-surface border border-border p-3 rounded-lg flex flex-col justify-between">
              <span className="text-[11px] text-text-dim">Search Algorithm</span>
              <div className="mt-1 flex items-center gap-2">
                <span className="text-xs font-mono font-bold text-text uppercase">
                  {selectedSweep?.method || '-'}
                </span>
                <span className="text-[10px] bg-primary/10 text-primary border border-primary/20 px-1.5 py-0.5 rounded">
                  {selectedSweep?.goal} {selectedSweep?.objective_metric}
                </span>
              </div>
            </div>

            <div className="bg-surface border border-border p-3 rounded-lg flex flex-col justify-between">
              <span className="text-[11px] text-text-dim">Progress & Trials</span>
              <div className="mt-1 flex items-center justify-between">
                <span className="text-xs font-mono text-text">
                  {completedCount} / {selectedSweep?.max_trials || 0} completed
                </span>
                <span className="text-[11px] text-text-dim">
                  {selectedSweep?.trials.length || 0} sampled
                </span>
              </div>
            </div>

            <div className="bg-surface border border-border p-3 rounded-lg flex flex-col justify-between">
              <span className="text-[11px] text-text-dim">Best {selectedSweep?.objective_metric}</span>
              <div className="mt-1 flex items-center justify-between">
                <span className="text-sm font-mono font-bold text-emerald-400">
                  {analysis?.best_metric_value !== undefined ? analysis.best_metric_value.toFixed(4) : '-'}
                </span>
                <div className="flex items-center gap-1">
                  <button
                    type="button"
                    title="Export Markdown Report"
                    disabled={exporting}
                    onClick={handleExportReport}
                    className="p-1 text-text-dim hover:text-text bg-bg border border-border rounded"
                  >
                    <FileDown className="w-3.5 h-3.5" />
                  </button>
                  <button
                    type="button"
                    title="Delete Sweep"
                    onClick={handleDeleteSweep}
                    className="p-1 text-rose-400 hover:text-rose-300 bg-bg border border-border rounded"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            </div>
          </div>

          {/* Tab Navigation */}
          {selectedSweep && (
            <div className="flex items-center gap-2 border-b border-border pt-1">
              <button
                type="button"
                onClick={() => setActiveTab('trials')}
                className={`flex items-center gap-1.5 px-3 py-2 text-xs font-medium border-b-2 transition-colors ${
                  activeTab === 'trials'
                    ? 'border-primary text-primary'
                    : 'border-transparent text-text-dim hover:text-text'
                }`}
              >
                <Table className="w-3.5 h-3.5" />
                Trials History ({selectedSweep.trials.length})
              </button>

              <button
                type="button"
                onClick={() => setActiveTab('parallel_coords')}
                className={`flex items-center gap-1.5 px-3 py-2 text-xs font-medium border-b-2 transition-colors ${
                  activeTab === 'parallel_coords'
                    ? 'border-primary text-primary'
                    : 'border-transparent text-text-dim hover:text-text'
                }`}
              >
                <Activity className="w-3.5 h-3.5" />
                Parallel Coordinates
              </button>

              <button
                type="button"
                onClick={() => setActiveTab('analysis')}
                className={`flex items-center gap-1.5 px-3 py-2 text-xs font-medium border-b-2 transition-colors ${
                  activeTab === 'analysis'
                    ? 'border-primary text-primary'
                    : 'border-transparent text-text-dim hover:text-text'
                }`}
              >
                <BarChart className="w-3.5 h-3.5" />
                Sensitivity & Pareto Analysis
              </button>
            </div>
          )}

          {/* Main Tab Content */}
          {selectedSweep && (
            <div>
              {activeTab === 'trials' && (
                <SweepTrialsTable
                  sweep={selectedSweep}
                  onSuggestTrial={handleSuggestTrial}
                  suggesting={suggesting}
                />
              )}
              {activeTab === 'parallel_coords' && (
                <SweepParallelCoordinates sweep={selectedSweep} />
              )}
              {activeTab === 'analysis' && (
                <SweepAnalysisCard sweep={selectedSweep} analysis={analysis} />
              )}
            </div>
          )}
        </>
      )}

      {/* New Sweep Modal */}
      <NewSweepModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onSubmit={handleCreateSweep}
      />
    </div>
  );
};

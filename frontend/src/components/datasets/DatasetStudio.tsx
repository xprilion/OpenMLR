import { useState, useEffect, useCallback } from 'react';
import {
  Database,
  RefreshCw,
  Scissors,
  AlertTriangle,
  FileSpreadsheet,
  Table,
  CheckCircle,
  Hash,
} from 'lucide-react';
import { api } from '../../api';
import { useProject } from '../../context/ProjectContext';
import type { DatasetProfile } from './types';
import { ColumnMetricsTable } from './ColumnMetricsTable';
import { SampleDataViewer } from './SampleDataViewer';
import { DatasetValidatorCard } from './DatasetValidatorCard';
import { DatasetSplitterModal } from './DatasetSplitterModal';

export function DatasetStudio() {
  const { activeProject } = useProject();
  const [filePath, setFilePath] = useState<string>('data.csv');
  const [profile, setProfile] = useState<DatasetProfile | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'columns' | 'samples' | 'validate'>('columns');
  const [showSplitModal, setShowSplitModal] = useState(false);

  const fetchProfile = useCallback(async () => {
    if (!filePath.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const res = await api.profileDataset({ path: filePath.trim() });
      if (res && res.profile) {
        setProfile(res.profile);
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to profile dataset');
      setProfile(null);
    } finally {
      setLoading(false);
    }
  }, [filePath]);

  useEffect(() => {
    fetchProfile();
  }, [fetchProfile]);

  const columnsList = profile ? Object.keys(profile.columns) : [];

  return (
    <div className="flex flex-col flex-1 h-full overflow-hidden bg-background">
      {/* Header Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 p-4 border-b border-border bg-surface shrink-0">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-primary/10 border border-primary/20 flex items-center justify-center text-primary">
            <Database size={18} />
          </div>
          <div>
            <h1 className="text-sm font-semibold text-text flex items-center gap-2">
              Dataset Studio
              {activeProject && (
                <span className="text-xs font-normal text-text-dim px-2 py-0.5 rounded bg-surface-subtle border border-border">
                  {activeProject.name}
                </span>
              )}
            </h1>
            <p className="text-xs text-text-dim">
              Statistical profiling, missingness diagnostics, schema validation, and partition splits
            </p>
          </div>
        </div>

        {/* Path Input & Actions */}
        <div className="flex items-center gap-2 w-full sm:w-auto">
          <div className="relative flex-1 sm:w-80">
            <FileSpreadsheet size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-dim" />
            <input
              type="text"
              value={filePath}
              onChange={(e) => setFilePath(e.target.value)}
              placeholder="Dataset path (e.g. data.csv, train.jsonl)..."
              className="w-full bg-surface-subtle border border-border rounded-md pl-9 pr-3 py-1.5 font-mono text-xs text-text placeholder-text-dim focus:outline-none focus:border-primary"
            />
          </div>

          <button
            type="button"
            onClick={fetchProfile}
            disabled={loading}
            className="p-1.5 rounded bg-surface-subtle border border-border text-text-dim hover:text-text transition-colors disabled:opacity-50"
            title="Refresh Dataset Profile"
          >
            <RefreshCw size={15} className={loading ? 'animate-spin text-primary' : ''} />
          </button>

          <button
            type="button"
            onClick={() => setShowSplitModal(true)}
            disabled={!profile}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs bg-primary text-white font-medium rounded-md hover:bg-primary/90 transition-colors disabled:opacity-50 shrink-0"
          >
            <Scissors size={14} />
            Split Partitions
          </button>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {/* Error Alert */}
        {error && (
          <div className="p-3 bg-red-500/10 border border-red-500/30 rounded-lg flex items-center gap-2 text-xs text-red-400">
            <AlertTriangle size={15} className="shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Profile Overview Banner */}
        {profile && (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div className="p-3 bg-surface rounded-lg border border-border">
              <span className="text-[11px] text-text-dim uppercase tracking-wider block">Total Rows</span>
              <span className="text-lg font-bold font-mono text-text">
                {profile.total_rows.toLocaleString()}
              </span>
            </div>
            <div className="p-3 bg-surface rounded-lg border border-border">
              <span className="text-[11px] text-text-dim uppercase tracking-wider block">Columns</span>
              <span className="text-lg font-bold font-mono text-text">{profile.total_columns}</span>
            </div>
            <div className="p-3 bg-surface rounded-lg border border-border">
              <span className="text-[11px] text-text-dim uppercase tracking-wider block">File Size</span>
              <span className="text-lg font-bold font-mono text-text">
                {(profile.file_size_bytes / (1024 * 1024)).toFixed(2)} MB
              </span>
            </div>
            <div className="p-3 bg-surface rounded-lg border border-border">
              <span className="text-[11px] text-text-dim uppercase tracking-wider block">Health Score</span>
              <div className="flex items-center gap-2">
                <span
                  className={`text-lg font-bold font-mono ${
                    profile.health_score >= 80
                      ? 'text-emerald-400'
                      : profile.health_score >= 50
                        ? 'text-amber-400'
                        : 'text-red-400'
                  }`}
                >
                  {profile.health_score}/100
                </span>
              </div>
            </div>
          </div>
        )}

        {/* Warnings Banner */}
        {profile && profile.warnings.length > 0 && (
          <div className="p-3 bg-amber-500/10 border border-amber-500/30 rounded-lg text-xs text-amber-400 space-y-1">
            <div className="font-semibold flex items-center gap-1.5">
              <AlertTriangle size={14} /> Diagnostic Warnings Detected ({profile.warnings.length}):
            </div>
            <ul className="list-disc pl-5 space-y-0.5">
              {profile.warnings.map((w) => (
                <li key={w}>{w}</li>
              ))}
            </ul>
          </div>
        )}

        {/* Tab Switcher */}
        <div className="flex border-b border-border">
          <button
            type="button"
            onClick={() => setActiveTab('columns')}
            className={`px-4 py-2 text-xs font-medium border-b-2 flex items-center gap-1.5 transition-colors ${
              activeTab === 'columns'
                ? 'border-primary text-primary'
                : 'border-transparent text-text-dim hover:text-text'
            }`}
          >
            <Hash size={14} /> Columns & Distribution
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('samples')}
            className={`px-4 py-2 text-xs font-medium border-b-2 flex items-center gap-1.5 transition-colors ${
              activeTab === 'samples'
                ? 'border-primary text-primary'
                : 'border-transparent text-text-dim hover:text-text'
            }`}
          >
            <Table size={14} /> Data Samples
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('validate')}
            className={`px-4 py-2 text-xs font-medium border-b-2 flex items-center gap-1.5 transition-colors ${
              activeTab === 'validate'
                ? 'border-primary text-primary'
                : 'border-transparent text-text-dim hover:text-text'
            }`}
          >
            <CheckCircle size={14} /> Schema Validator
          </button>
        </div>

        {/* Tab Panes */}
        {profile && activeTab === 'columns' && <ColumnMetricsTable columns={profile.columns} />}

        {activeTab === 'samples' && (
          <SampleDataViewer filePath={filePath} availableColumns={columnsList} />
        )}

        {activeTab === 'validate' && (
          <DatasetValidatorCard filePath={filePath} availableColumns={columnsList} />
        )}
      </div>

      {/* Partition Splitter Modal */}
      {showSplitModal && (
        <DatasetSplitterModal
          filePath={filePath}
          availableColumns={columnsList}
          onClose={() => setShowSplitModal(false)}
        />
      )}
    </div>
  );
}

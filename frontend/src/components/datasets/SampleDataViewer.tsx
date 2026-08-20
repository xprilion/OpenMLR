import { useState, useEffect, useCallback } from 'react';
import { RefreshCw, Play, AlertCircle } from 'lucide-react';
import { api } from '../../api';

interface Props {
  readonly filePath: string;
  readonly availableColumns: string[];
}

function formatCellDisplay(val: unknown): string {
  if (val === null || val === undefined) {
    return '<null>';
  }
  if (typeof val === 'object') {
    return JSON.stringify(val);
  }
  return String(val);
}

export function SampleDataViewer({ filePath, availableColumns }: Props) {
  const [samples, setSamples] = useState<Record<string, unknown>[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [n, setN] = useState(5);
  const [strategy, setStrategy] = useState<'head' | 'random' | 'stratified'>('head');
  const [labelCol, setLabelCol] = useState<string>('');

  const fetchSamples = useCallback(async () => {
    if (!filePath) return;
    setLoading(true);
    setError(null);
    try {
      const res = await api.inspectDatasetSamples({
        path: filePath,
        n,
        strategy,
        label_column: strategy === 'stratified' ? labelCol || undefined : undefined,
      });
      if (res && Array.isArray(res.samples)) {
        setSamples(res.samples);
      } else {
        setSamples([]);
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to inspect dataset samples');
    } finally {
      setLoading(false);
    }
  }, [filePath, n, strategy, labelCol]);

  useEffect(() => {
    fetchSamples();
  }, [fetchSamples]);

  const headers = samples.length > 0 ? Object.keys(samples[0]) : availableColumns;

  return (
    <div className="space-y-4">
      {/* Sampling Controls */}
      <div className="flex flex-wrap items-center gap-3 bg-surface p-3 rounded-lg border border-border">
        <div className="flex items-center gap-2">
          <span className="text-xs text-text-dim">Rows:</span>
          <select
            value={n}
            onChange={(e) => setN(Number(e.target.value))}
            className="bg-surface-subtle border border-border rounded px-2 py-1 text-xs text-text focus:outline-none focus:border-primary"
          >
            <option value={5}>5</option>
            <option value={10}>10</option>
            <option value={25}>25</option>
            <option value={50}>50</option>
          </select>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-xs text-text-dim">Strategy:</span>
          <select
            value={strategy}
            onChange={(e) => setStrategy(e.target.value as 'head' | 'random' | 'stratified')}
            className="bg-surface-subtle border border-border rounded px-2 py-1 text-xs text-text focus:outline-none focus:border-primary capitalize"
          >
            <option value="head">First N (Head)</option>
            <option value="random">Random Sampling</option>
            <option value="stratified">Stratified Sampling</option>
          </select>
        </div>

        {strategy === 'stratified' && (
          <div className="flex items-center gap-2">
            <span className="text-xs text-text-dim">Stratify Column:</span>
            <select
              value={labelCol}
              onChange={(e) => setLabelCol(e.target.value)}
              className="bg-surface-subtle border border-border rounded px-2 py-1 text-xs text-text focus:outline-none focus:border-primary"
            >
              <option value="">Select column...</option>
              {availableColumns.map((col) => (
                <option key={col} value={col}>
                  {col}
                </option>
              ))}
            </select>
          </div>
        )}

        <button
          type="button"
          onClick={fetchSamples}
          disabled={loading}
          className="ml-auto inline-flex items-center gap-1.5 px-3 py-1 text-xs bg-primary text-white font-medium rounded hover:bg-primary/90 transition-colors disabled:opacity-50"
        >
          {loading ? <RefreshCw size={13} className="animate-spin" /> : <Play size={13} />}
          Fetch Samples
        </button>
      </div>

      {/* Error state */}
      {error && (
        <div className="p-3 bg-red-500/10 border border-red-500/30 rounded-lg flex items-center gap-2 text-xs text-red-400">
          <AlertCircle size={14} className="shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Samples Table */}
      <div className="border border-border rounded-lg overflow-hidden bg-surface">
        <div className="overflow-x-auto max-h-[500px]">
          <table className="w-full text-left text-xs text-text border-collapse">
            <thead className="sticky top-0 bg-surface-subtle border-b border-border z-10">
              <tr>
                <th className="py-2 px-3 w-10 text-text-dim font-mono">#</th>
                {headers.map((h) => (
                  <th key={h} className="py-2 px-3 font-mono font-medium text-text whitespace-nowrap">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-border/50 font-mono text-[11px]">
              {loading ? (
                <tr>
                  <td colSpan={headers.length + 1} className="py-8 text-center text-text-dim">
                    <RefreshCw size={18} className="animate-spin mx-auto mb-2 text-primary" />
                    Fetching dataset samples...
                  </td>
                </tr>
              ) : samples.length === 0 ? (
                <tr>
                  <td colSpan={headers.length + 1} className="py-8 text-center text-text-dim">
                    No sample records found.
                  </td>
                </tr>
              ) : (
                samples.map((row, idx) => (
                  <tr key={`sample-row-${idx + 1}`} className="hover:bg-surface-subtle/50 transition-colors">
                    <td className="py-2 px-3 text-text-dim">{idx + 1}</td>
                    {headers.map((h) => {
                      const val = row[h];
                      const displayVal = formatCellDisplay(val);
                      const isNull = val === null || val === undefined;
                      return (
                        <td
                          key={`sample-cell-${idx + 1}-${h}`}
                          className={`py-2 px-3 max-w-[280px] truncate ${
                            isNull ? 'text-text-dim/50 italic' : 'text-text'
                          }`}
                          title={displayVal}
                        >
                          {displayVal}
                        </td>
                      );
                    })}
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

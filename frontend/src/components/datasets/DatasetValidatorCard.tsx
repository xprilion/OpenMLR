import { useState } from 'react';
import { CheckCircle2, XCircle, AlertTriangle, ShieldCheck, Play, RefreshCw } from 'lucide-react';
import { api } from '../../api';
import type { ValidationResult } from './types';

interface Props {
  readonly filePath: string;
  readonly availableColumns: string[];
}

export function DatasetValidatorCard({ filePath, availableColumns }: Props) {
  const [expectedColumns, setExpectedColumns] = useState<string[]>([]);
  const [maxNullPct, setMaxNullPct] = useState<number>(20);
  const [maxTokenLen, setMaxTokenLen] = useState<string>('512');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ValidationResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleValidate = async () => {
    if (!filePath) return;
    setLoading(true);
    setError(null);
    try {
      const parsedTokens = maxTokenLen.trim() ? Number.parseInt(maxTokenLen, 10) : undefined;
      const res = await api.validateDataset({
        path: filePath,
        expected_columns: expectedColumns.length > 0 ? expectedColumns : undefined,
        max_null_pct: maxNullPct,
        max_token_length: Number.isNaN(parsedTokens) ? undefined : parsedTokens,
      });
      if (res && res.validation) {
        setResult(res.validation);
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Validation request failed');
    } finally {
      setLoading(false);
    }
  };

  const toggleColumn = (col: string) => {
    setExpectedColumns((prev) =>
      prev.includes(col) ? prev.filter((c) => c !== col) : [...prev, col]
    );
  };

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {/* Configuration */}
      <div className="p-4 bg-surface rounded-lg border border-border space-y-4">
        <div className="flex items-center gap-2 border-b border-border pb-2.5">
          <ShieldCheck size={16} className="text-primary" />
          <h3 className="text-xs font-semibold uppercase tracking-wider text-text">
            Validation Rules & Constraints
          </h3>
        </div>

        {/* Expected Columns */}
        <div>
          <label className="block text-xs font-medium text-text mb-1.5">
            Required Columns ({expectedColumns.length} selected):
          </label>
          <div className="flex flex-wrap gap-1.5 max-h-32 overflow-y-auto p-2 bg-surface-subtle rounded border border-border">
            {availableColumns.map((col) => {
              const isSelected = expectedColumns.includes(col);
              return (
                <button
                  key={col}
                  type="button"
                  onClick={() => toggleColumn(col)}
                  className={`px-2 py-0.5 text-xs rounded font-mono transition-colors ${
                    isSelected
                      ? 'bg-primary text-white font-medium'
                      : 'bg-surface text-text-dim border border-border hover:text-text'
                  }`}
                >
                  {col}
                </button>
              );
            })}
          </div>
        </div>

        {/* Max Null Pct */}
        <div>
          <div className="flex justify-between items-center text-xs mb-1">
            <span className="text-text font-medium">Max Null Percentage:</span>
            <span className="text-primary font-mono">{maxNullPct}%</span>
          </div>
          <input
            type="range"
            min="0"
            max="50"
            step="1"
            value={maxNullPct}
            onChange={(e) => setMaxNullPct(Number(e.target.value))}
            className="w-full h-1.5 bg-surface-subtle rounded-lg appearance-none cursor-pointer accent-primary"
          />
        </div>

        {/* Max Token Length */}
        <div>
          <label className="block text-xs font-medium text-text mb-1">
            Max Token Length for Text Columns:
          </label>
          <input
            type="number"
            value={maxTokenLen}
            onChange={(e) => setMaxTokenLen(e.target.value)}
            placeholder="e.g. 512"
            className="w-full bg-surface-subtle border border-border rounded px-3 py-1.5 text-xs text-text focus:outline-none focus:border-primary"
          />
        </div>

        <button
          type="button"
          onClick={handleValidate}
          disabled={loading}
          className="w-full inline-flex items-center justify-center gap-1.5 px-3 py-2 text-xs bg-primary text-white font-medium rounded hover:bg-primary/90 transition-colors disabled:opacity-50"
        >
          {loading ? <RefreshCw size={13} className="animate-spin" /> : <Play size={13} />}
          Run Validation Check
        </button>
      </div>

      {/* Results */}
      <div className="p-4 bg-surface rounded-lg border border-border flex flex-col">
        <div className="flex items-center justify-between border-b border-border pb-2.5 mb-4">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-text">
            Validation Outcome
          </h3>
          {result && (
            <span
              className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium ${
                result.valid
                  ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30'
                  : 'bg-red-500/10 text-red-400 border border-red-500/30'
              }`}
            >
              {result.valid ? <CheckCircle2 size={13} /> : <XCircle size={13} />}
              {result.valid ? 'Passed' : 'Failed'}
            </span>
          )}
        </div>

        {error && (
          <div className="p-3 bg-red-500/10 border border-red-500/30 rounded text-xs text-red-400">
            {error}
          </div>
        )}

        {!result && !error && (
          <div className="flex-1 flex flex-col items-center justify-center text-center text-text-dim text-xs py-8">
            <ShieldCheck size={28} className="mb-2 text-text-dim/40" />
            <p>Click &quot;Run Validation Check&quot; to test dataset constraints against schema rules.</p>
          </div>
        )}

        {result && (
          <div className="space-y-4 flex-1">
            <div className="flex items-center justify-between p-3 bg-surface-subtle rounded border border-border">
              <span className="text-xs text-text-dim">Calculated Health Score:</span>
              <span className="text-sm font-bold font-mono text-primary">
                {result.health_score} / 100
              </span>
            </div>

            {/* Errors */}
            {result.errors.length > 0 && (
              <div className="space-y-1.5">
                <span className="text-xs font-semibold text-red-400 flex items-center gap-1">
                  <XCircle size={13} /> Errors ({result.errors.length}):
                </span>
                <ul className="text-xs text-red-400/90 space-y-1 list-disc pl-4 bg-red-500/5 p-2.5 rounded border border-red-500/20">
                  {result.errors.map((err) => (
                    <li key={err}>{err}</li>
                  ))}
                </ul>
              </div>
            )}

            {/* Warnings */}
            {result.warnings.length > 0 && (
              <div className="space-y-1.5">
                <span className="text-xs font-semibold text-amber-400 flex items-center gap-1">
                  <AlertTriangle size={13} /> Warnings ({result.warnings.length}):
                </span>
                <ul className="text-xs text-amber-400/90 space-y-1 list-disc pl-4 bg-amber-500/5 p-2.5 rounded border border-amber-500/20">
                  {result.warnings.map((w) => (
                    <li key={w}>{w}</li>
                  ))}
                </ul>
              </div>
            )}

            {result.errors.length === 0 && result.warnings.length === 0 && (
              <div className="p-4 bg-emerald-500/10 border border-emerald-500/30 rounded text-center text-xs text-emerald-400">
                🎉 All schema checks, missingness constraints, and token length limits passed.
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

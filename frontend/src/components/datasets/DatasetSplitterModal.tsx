import { useState } from 'react';
import { X, Scissors, RefreshCw, CheckCircle2, AlertCircle } from 'lucide-react';
import { api } from '../../api';
import type { SplitManifest } from './types';

interface Props {
  readonly filePath: string;
  readonly availableColumns: string[];
  readonly onClose: () => void;
}

export function DatasetSplitterModal({ filePath, availableColumns, onClose }: Props) {
  const defaultOutDir = `${filePath.replace(/\.[^/.]+$/, '')}_splits`;
  const [outputDir, setOutputDir] = useState(defaultOutDir);
  const [trainRatio, setTrainRatio] = useState(0.8);
  const [valRatio, setValRatio] = useState(0.1);
  const [testRatio, setTestRatio] = useState(0.1);
  const [stratifyCol, setStratifyCol] = useState('');
  const [seed, setSeed] = useState(42);
  const [loading, setLoading] = useState(false);
  const [manifest, setManifest] = useState<SplitManifest | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleSplit = async () => {
    if (!filePath || !outputDir) return;
    setLoading(true);
    setError(null);
    try {
      const res = await api.splitDataset({
        path: filePath,
        output_dir: outputDir,
        train_ratio: trainRatio,
        val_ratio: valRatio,
        test_ratio: testRatio,
        stratify_column: stratifyCol || undefined,
        seed,
      });
      if (res?.manifest) {
        setManifest(res.manifest);
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Dataset partitioning failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <div className="w-full max-w-lg bg-surface border border-border rounded-xl shadow-2xl p-5 space-y-4">
        <div className="flex items-center justify-between border-b border-border pb-3">
          <div className="flex items-center gap-2">
            <Scissors size={18} className="text-primary" />
            <h2 className="text-sm font-semibold text-text">Dataset Partition Splitter</h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="text-text-dim hover:text-text p-1 rounded transition-colors"
          >
            <X size={16} />
          </button>
        </div>

        {/* Source info */}
        <div className="p-2.5 bg-surface-subtle rounded border border-border text-xs">
          <span className="text-text-dim">Source file: </span>
          <span className="font-mono text-text font-medium">{filePath}</span>
        </div>

        {/* Form */}
        <div className="space-y-3 text-xs">
          <div>
            <label htmlFor="target-output-dir" className="block text-text font-medium mb-1">
              Target Output Directory:
            </label>
            <input
              id="target-output-dir"
              type="text"
              value={outputDir}
              onChange={(e) => setOutputDir(e.target.value)}
              className="w-full bg-surface-subtle border border-border rounded px-3 py-1.5 font-mono text-xs text-text focus:outline-none focus:border-primary"
            />
          </div>

          {/* Ratio Split */}
          <div>
            <div className="flex justify-between items-center mb-1">
              <span className="text-text font-medium">Split Ratios:</span>
              <span className="font-mono text-text-dim">
                Train: {(trainRatio * 100).toFixed(0)}% | Val: {(valRatio * 100).toFixed(0)}% | Test:{' '}
                {(testRatio * 100).toFixed(0)}%
              </span>
            </div>
            <div className="grid grid-cols-3 gap-2">
              <div>
                <label htmlFor="train-ratio-input" className="text-[11px] text-text-dim block">
                  Train:
                </label>
                <input
                  id="train-ratio-input"
                  type="number"
                  step="0.05"
                  min="0.1"
                  max="0.9"
                  value={trainRatio}
                  onChange={(e) => setTrainRatio(Number(e.target.value))}
                  className="w-full bg-surface-subtle border border-border rounded px-2 py-1 text-xs text-text"
                />
              </div>
              <div>
                <label htmlFor="val-ratio-input" className="text-[11px] text-text-dim block">
                  Val:
                </label>
                <input
                  id="val-ratio-input"
                  type="number"
                  step="0.05"
                  min="0.0"
                  max="0.5"
                  value={valRatio}
                  onChange={(e) => setValRatio(Number(e.target.value))}
                  className="w-full bg-surface-subtle border border-border rounded px-2 py-1 text-xs text-text"
                />
              </div>
              <div>
                <label htmlFor="test-ratio-input" className="text-[11px] text-text-dim block">
                  Test:
                </label>
                <input
                  id="test-ratio-input"
                  type="number"
                  step="0.05"
                  min="0.0"
                  max="0.5"
                  value={testRatio}
                  onChange={(e) => setTestRatio(Number(e.target.value))}
                  className="w-full bg-surface-subtle border border-border rounded px-2 py-1 text-xs text-text"
                />
              </div>
            </div>
          </div>

          {/* Stratification */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label htmlFor="stratify-col-select" className="block text-text font-medium mb-1">
                Stratify by Column (Optional):
              </label>
              <select
                id="stratify-col-select"
                value={stratifyCol}
                onChange={(e) => setStratifyCol(e.target.value)}
                className="w-full bg-surface-subtle border border-border rounded px-2 py-1.5 text-xs text-text focus:outline-none focus:border-primary"
              >
                <option value="">None (Random Split)</option>
                {availableColumns.map((col) => (
                  <option key={col} value={col}>
                    {col}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label htmlFor="seed-input" className="block text-text font-medium mb-1">
                Random Seed:
              </label>
              <input
                id="seed-input"
                type="number"
                value={seed}
                onChange={(e) => setSeed(Number(e.target.value))}
                className="w-full bg-surface-subtle border border-border rounded px-3 py-1.5 text-xs text-text focus:outline-none focus:border-primary"
              />
            </div>
          </div>
        </div>

        {error && (
          <div className="p-3 bg-red-500/10 border border-red-500/30 rounded flex items-center gap-2 text-xs text-red-400">
            <AlertCircle size={14} className="shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {manifest && (
          <div className="p-3 bg-emerald-500/10 border border-emerald-500/30 rounded text-xs text-emerald-400 space-y-1">
            <div className="flex items-center gap-1.5 font-medium">
              <CheckCircle2 size={14} /> Partition splits generated successfully!
            </div>
            <div className="font-mono text-[11px] text-text-dim">
              Train: {manifest.train_count.toLocaleString()} | Val: {manifest.val_count.toLocaleString()} | Test:{' '}
              {manifest.test_count.toLocaleString()}
            </div>
          </div>
        )}

        <div className="flex justify-end gap-2 pt-2 border-t border-border">
          <button
            type="button"
            onClick={onClose}
            className="px-3 py-1.5 text-xs text-text-dim hover:text-text bg-surface-subtle rounded border border-border transition-colors"
          >
            Close
          </button>
          <button
            type="button"
            onClick={handleSplit}
            disabled={loading}
            className="inline-flex items-center gap-1.5 px-4 py-1.5 text-xs bg-primary text-white font-medium rounded hover:bg-primary/90 transition-colors disabled:opacity-50"
          >
            {loading ? <RefreshCw size={13} className="animate-spin" /> : <Scissors size={13} />}
            Generate Splits
          </button>
        </div>
      </div>
    </div>
  );
}

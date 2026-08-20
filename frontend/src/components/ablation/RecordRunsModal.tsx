import React, { useState } from 'react';
import { X, Plus, Database } from 'lucide-react';
import type { RecordRunsRequest, VariantType } from './types';

interface RecordRunsModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (data: RecordRunsRequest) => Promise<void>;
  existingVariantNames?: string[];
  defaultPrimaryMetric?: string;
}

export const RecordRunsModal: React.FC<RecordRunsModalProps> = ({
  isOpen,
  onClose,
  onSubmit,
  existingVariantNames = [],
  defaultPrimaryMetric = 'accuracy',
}) => {
  const [variantName, setVariantName] = useState('');
  const [variantType, setVariantType] = useState<VariantType>('ablation');
  const [description, setDescription] = useState('');
  const [removedComponentsStr, setRemovedComponentsStr] = useState('');
  const [addedComponentsStr, setAddedComponentsStr] = useState('');
  const [metricName, setMetricName] = useState(defaultPrimaryMetric);
  const [seedValuesStr, setSeedValuesStr] = useState('');
  const [loading, setLoading] = useState(false);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!variantName.trim() || !seedValuesStr.trim() || !metricName.trim()) return;

    const values = seedValuesStr
      .split(/[\s,]+/)
      .map((s) => parseFloat(s.trim()))
      .filter((n) => !isNaN(n));

    if (values.length === 0) return;

    const removed = removedComponentsStr
      .split(',')
      .map((s) => s.trim())
      .filter(Boolean);

    const added = addedComponentsStr
      .split(',')
      .map((s) => s.trim())
      .filter(Boolean);

    setLoading(true);
    try {
      await onSubmit({
        variant_name: variantName.trim(),
        variant_type: variantType,
        description: description.trim(),
        removed_components: removed,
        added_components: added,
        metrics: {
          [metricName.trim()]: values,
        },
      });
      onClose();
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4 animate-fade-in">
      <div className="w-full max-w-lg rounded-xl border border-border bg-surface shadow-2xl overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-border bg-surface">
          <div className="flex items-center gap-2 text-text font-semibold text-base">
            <Database className="w-4 h-4 text-primary" />
            Record Variant Seed Runs
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1 rounded-lg text-text-dim hover:text-text hover:bg-surface-hover transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div>
            <label className="block text-xs font-medium text-text-dim mb-1">
              Variant Name <span className="text-rose-400">*</span>
            </label>
            <input
              type="text"
              required
              value={variantName}
              onChange={(e) => setVariantName(e.target.value)}
              placeholder="e.g. w/o FlashAttention or w/ Learned Embeddings"
              list="existing-variants"
              className="w-full px-3 py-2 rounded-lg border border-border bg-background text-sm text-text focus:outline-none focus:border-primary"
            />
            {existingVariantNames.length > 0 && (
              <datalist id="existing-variants">
                {existingVariantNames.map((n) => (
                  <option key={n} value={n} />
                ))}
              </datalist>
            )}
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-text-dim mb-1">
                Variant Type
              </label>
              <select
                value={variantType}
                onChange={(e) => setVariantType(e.target.value as VariantType)}
                className="w-full px-3 py-2 rounded-lg border border-border bg-background text-sm text-text focus:outline-none focus:border-primary"
              >
                <option value="ablation">Ablation (removal)</option>
                <option value="addition">Addition (extension)</option>
                <option value="modification">Modification (swap)</option>
                <option value="baseline">Baseline</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-text-dim mb-1">
                Target Metric Name <span className="text-rose-400">*</span>
              </label>
              <input
                type="text"
                required
                value={metricName}
                onChange={(e) => setMetricName(e.target.value)}
                placeholder="e.g. accuracy"
                className="w-full px-3 py-2 rounded-lg border border-border bg-background text-sm text-text focus:outline-none focus:border-primary"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-text-dim mb-1">
              Multi-Seed Metric Values <span className="text-rose-400">*</span>
            </label>
            <input
              type="text"
              required
              value={seedValuesStr}
              onChange={(e) => setSeedValuesStr(e.target.value)}
              placeholder="e.g. 0.882, 0.879, 0.885, 0.880, 0.884"
              className="w-full px-3 py-2 rounded-lg border border-border bg-background text-sm text-text focus:outline-none focus:border-primary font-mono"
            />
            <p className="text-[11px] text-text-dim mt-1">
              Comma or space-separated list of evaluations across seeds.
            </p>
          </div>

          <div>
            <label className="block text-xs font-medium text-text-dim mb-1">
              Variant Description
            </label>
            <input
              type="text"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="e.g. Standard positional embeddings replacing RoPE"
              className="w-full px-3 py-2 rounded-lg border border-border bg-background text-sm text-text focus:outline-none focus:border-primary"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-text-dim mb-1">
              Removed Components (comma-separated)
            </label>
            <input
              type="text"
              value={removedComponentsStr}
              onChange={(e) => setRemovedComponentsStr(e.target.value)}
              placeholder="e.g. Rotary Position Embeddings, FlashAttention"
              className="w-full px-3 py-2 rounded-lg border border-border bg-background text-sm text-text focus:outline-none focus:border-primary"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-text-dim mb-1">
              Added Components (comma-separated)
            </label>
            <input
              type="text"
              value={addedComponentsStr}
              onChange={(e) => setAddedComponentsStr(e.target.value)}
              placeholder="e.g. Learned Absolute Embeddings"
              className="w-full px-3 py-2 rounded-lg border border-border bg-background text-sm text-text focus:outline-none focus:border-primary"
            />
          </div>

          <div className="flex items-center justify-end gap-2 pt-4 border-t border-border">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-lg border border-border text-sm text-text-dim hover:text-text hover:bg-surface-hover transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading || !variantName.trim() || !seedValuesStr.trim()}
              className="px-4 py-2 rounded-lg bg-primary hover:bg-primary/90 text-sm font-medium text-white transition-colors flex items-center gap-1.5 disabled:opacity-50"
            >
              <Plus className="w-4 h-4" />
              {loading ? 'Recording...' : 'Record Runs'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

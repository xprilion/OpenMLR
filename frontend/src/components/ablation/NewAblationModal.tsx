import React, { useState } from 'react';
import { X, Plus, Sparkles } from 'lucide-react';
import type { CreateStudyRequest } from './types';

interface NewAblationModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (data: CreateStudyRequest) => Promise<void>;
  projectId?: string | null;
}

export const NewAblationModal: React.FC<NewAblationModalProps> = ({
  isOpen,
  onClose,
  onSubmit,
  projectId,
}) => {
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [primaryMetric, setPrimaryMetric] = useState('accuracy');
  const [higherIsBetter, setHigherIsBetter] = useState(true);
  const [baselineName, setBaselineName] = useState('Full Model');
  const [baselineDesc, setBaselineDesc] = useState('Proposed full architecture');
  const [loading, setLoading] = useState(false);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) return;
    setLoading(true);
    try {
      await onSubmit({
        title: title.trim(),
        description: description.trim(),
        project_id: projectId,
        primary_metric: primaryMetric.trim() || 'accuracy',
        higher_is_better: higherIsBetter,
        baseline_variant_name: baselineName.trim() || 'Full Model',
        baseline_description: baselineDesc.trim(),
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
            <Sparkles className="w-4 h-4 text-primary" />
            Create Ablation Study
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
              Study Title <span className="text-rose-400">*</span>
            </label>
            <input
              type="text"
              required
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Attention & Normalization Layer Ablations"
              className="w-full px-3 py-2 rounded-lg border border-border bg-background text-sm text-text focus:outline-none focus:border-primary"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-text-dim mb-1">
              Motivation &amp; Research Goal
            </label>
            <textarea
              rows={2}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Systematic investigation into marginal contribution of rotary embeddings, QK-norm, and MLP gating."
              className="w-full px-3 py-2 rounded-lg border border-border bg-background text-sm text-text focus:outline-none focus:border-primary resize-none"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-text-dim mb-1">
                Primary Metric
              </label>
              <input
                type="text"
                value={primaryMetric}
                onChange={(e) => setPrimaryMetric(e.target.value)}
                placeholder="e.g. accuracy, perplexity, bleu"
                className="w-full px-3 py-2 rounded-lg border border-border bg-background text-sm text-text focus:outline-none focus:border-primary"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-text-dim mb-1">
                Metric Direction
              </label>
              <select
                value={higherIsBetter ? 'higher' : 'lower'}
                onChange={(e) => setHigherIsBetter(e.target.value === 'higher')}
                className="w-full px-3 py-2 rounded-lg border border-border bg-background text-sm text-text focus:outline-none focus:border-primary"
              >
                <option value="higher">Higher is better (↑)</option>
                <option value="lower">Lower is better (↓)</option>
              </select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-text-dim mb-1">
                Baseline Variant Label
              </label>
              <input
                type="text"
                value={baselineName}
                onChange={(e) => setBaselineName(e.target.value)}
                placeholder="e.g. Full Proposed Model"
                className="w-full px-3 py-2 rounded-lg border border-border bg-background text-sm text-text focus:outline-none focus:border-primary"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-text-dim mb-1">
                Baseline Description
              </label>
              <input
                type="text"
                value={baselineDesc}
                onChange={(e) => setBaselineDesc(e.target.value)}
                placeholder="All features enabled"
                className="w-full px-3 py-2 rounded-lg border border-border bg-background text-sm text-text focus:outline-none focus:border-primary"
              />
            </div>
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
              disabled={loading || !title.trim()}
              className="px-4 py-2 rounded-lg bg-primary hover:bg-primary/90 text-sm font-medium text-white transition-colors flex items-center gap-1.5 disabled:opacity-50"
            >
              <Plus className="w-4 h-4" />
              {loading ? 'Creating...' : 'Create Study'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

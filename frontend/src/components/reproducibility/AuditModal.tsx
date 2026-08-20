import { useState, useId, type FormEvent } from 'react';
import { X, Search, Terminal } from 'lucide-react';
import type { ChecklistVenue, AuditCodebaseRequest } from './types';

interface AuditModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (req: AuditCodebaseRequest) => void;
}

export function AuditModal({ isOpen, onClose, onSubmit }: Readonly<AuditModalProps>) {
  const [targetPath, setTargetPath] = useState('.');
  const [venue, setVenue] = useState<ChecklistVenue>('neurips');
  const [frameworkHint, setFrameworkHint] = useState('pytorch');
  const [customSnippet, setCustomSnippet] = useState('');

  const targetPathId = useId();
  const venueId = useId();
  const frameworkId = useId();
  const snippetId = useId();

  if (!isOpen) return null;

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    let codeSnippets: Record<string, string> | undefined;
    if (customSnippet.trim()) {
      codeSnippets = {
        'training_script.py': customSnippet.trim(),
      };
    }

    onSubmit({
      target_path: targetPath.trim() || '.',
      venue,
      framework_hint: frameworkHint,
      code_snippets: codeSnippets,
    });
  };

  return (
    <dialog
      open
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4 overflow-y-auto w-full h-full max-w-none max-h-none border-none m-0"
      aria-labelledby="audit-modal-title"
    >
      <div className="bg-surface border border-border rounded-xl shadow-2xl w-full max-w-xl overflow-hidden my-8">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-border bg-surface-hover/30">
          <div className="flex items-center gap-2">
            <Search className="w-5 h-5 text-primary" />
            <h2 id="audit-modal-title" className="text-base font-bold text-text">
              Run Reproducibility Audit
            </h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="text-text-dim hover:text-text p-1 rounded-md transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSubmit} className="p-6 flex flex-col gap-4">
          <div className="flex flex-col gap-1.5">
            <label htmlFor={targetPathId} className="text-xs font-semibold text-text">
              Target Codebase Directory
            </label>
            <input
              id={targetPathId}
              type="text"
              value={targetPath}
              onChange={(e) => setTargetPath(e.target.value)}
              placeholder="e.g. . or ./src or /workspace/exp"
              className="bg-bg border border-border rounded-lg px-3 py-2 text-sm text-text placeholder:text-text-dim focus:outline-none focus:border-primary font-mono"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="flex flex-col gap-1.5">
              <label htmlFor={venueId} className="text-xs font-semibold text-text">
                Target Conference Rubric
              </label>
              <select
                id={venueId}
                value={venue}
                onChange={(e) => setVenue(e.target.value as ChecklistVenue)}
                className="bg-bg border border-border rounded-lg px-3 py-2 text-sm text-text focus:outline-none focus:border-primary uppercase"
              >
                <option value="neurips">NeurIPS</option>
                <option value="icml">ICML</option>
                <option value="iclr">ICLR</option>
                <option value="cvpr">CVPR</option>
                <option value="general">General</option>
              </select>
            </div>

            <div className="flex flex-col gap-1.5">
              <label htmlFor={frameworkId} className="text-xs font-semibold text-text">
                Primary ML Framework
              </label>
              <select
                id={frameworkId}
                value={frameworkHint}
                onChange={(e) => setFrameworkHint(e.target.value)}
                className="bg-bg border border-border rounded-lg px-3 py-2 text-sm text-text focus:outline-none focus:border-primary capitalize"
              >
                <option value="pytorch">PyTorch</option>
                <option value="jax">JAX / Flax</option>
                <option value="tensorflow">TensorFlow</option>
                <option value="huggingface">HuggingFace</option>
              </select>
            </div>
          </div>

          <div className="flex flex-col gap-1.5">
            <div className="flex items-center justify-between">
              <label htmlFor={snippetId} className="text-xs font-semibold text-text">
                In-Memory Code Snippet (Optional)
              </label>
              <span className="text-[10px] text-text-dim">Paste script to audit directly</span>
            </div>
            <textarea
              id={snippetId}
              rows={5}
              value={customSnippet}
              onChange={(e) => setCustomSnippet(e.target.value)}
              placeholder="Paste training code with seeds, models, and dataloaders to audit instantly..."
              className="bg-bg border border-border rounded-lg p-2.5 text-xs text-text font-mono placeholder:text-text-dim focus:outline-none focus:border-primary resize-none"
            />
          </div>

          {/* Actions */}
          <div className="flex items-center justify-end gap-3 pt-3 border-t border-border">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-xs font-medium rounded-lg text-text-dim hover:text-text hover:bg-surface-hover transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-4 py-2 text-xs font-semibold rounded-lg bg-primary hover:bg-primary/90 text-white transition-colors flex items-center gap-1.5"
            >
              <Terminal className="w-3.5 h-3.5" />
              <span>Start Audit</span>
            </button>
          </div>
        </form>
      </div>
    </dialog>
  );
}

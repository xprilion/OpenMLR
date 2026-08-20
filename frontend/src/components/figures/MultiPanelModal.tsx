import { useState, useId, type FormEvent } from 'react';
import { X, Copy, Check, Grid, Sparkles } from 'lucide-react';
import type { MultiPanelResult, FigureArtifact } from './types';

interface Props {
  readonly isOpen: boolean;
  readonly isSubmitting: boolean;
  readonly selectedFigures: FigureArtifact[];
  readonly multiPanelResult: MultiPanelResult | null;
  readonly onClose: () => void;
  readonly onSubmit: (data: Record<string, unknown>) => void;
}

export function MultiPanelModal({
  isOpen,
  isSubmitting,
  selectedFigures,
  multiPanelResult,
  onClose,
  onSubmit,
}: Readonly<Props>) {
  const [title, setTitle] = useState('Comprehensive Empirical Evaluation');
  const [caption, setCaption] = useState(
    'Ablation study, scaling laws, and performance across benchmarks.'
  );
  const [columns, setColumns] = useState(2);
  const [subcaptions, setSubcaptions] = useState<Record<string, string>>({});
  const [isCopied, setIsCopied] = useState(false);

  const titleId = useId();
  const captionId = useId();
  const columnsId = useId();

  if (!isOpen) return null;

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    onSubmit({
      title: title.trim(),
      caption: caption.trim(),
      figure_ids: selectedFigures.map((f) => f.id),
      columns,
      subcaptions,
    });
  };

  const handleCopyLatex = () => {
    if (!multiPanelResult) return;
    navigator.clipboard.writeText(multiPanelResult.latex_code);
    setIsCopied(true);
    setTimeout(() => setIsCopied(false), 2000);
  };

  return (
    <dialog
      open
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4 overflow-y-auto w-full h-full max-w-none max-h-none border-none m-0"
      aria-labelledby="multipanel-modal-title"
    >
      <div className="bg-surface border border-border rounded-xl shadow-2xl w-full max-w-3xl overflow-hidden my-8">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-border bg-surface-hover/30">
          <div className="flex items-center gap-2">
            <div className="p-2 rounded-lg bg-primary/10 text-primary">
              <Grid size={20} />
            </div>
            <div>
              <h2 id="multipanel-modal-title" className="text-base font-semibold text-text">
                Multi-Panel Subfigure Grid Layout
              </h2>
              <p className="text-xs text-text-dim">
                Combine {selectedFigures.length} figures into a publication LaTeX subfigure environment
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1 rounded-lg text-text-dim hover:text-text hover:bg-surface-hover transition-colors"
            aria-label="Close dialog"
          >
            <X size={18} />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6 max-h-[75vh] overflow-y-auto">
          {multiPanelResult ? (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h4 className="text-sm font-semibold text-text">{multiPanelResult.title}</h4>
                  <p className="text-xs text-text-dim">{multiPanelResult.caption}</p>
                </div>
                <button
                  type="button"
                  onClick={handleCopyLatex}
                  className="px-3 py-1.5 rounded-lg bg-primary text-white text-xs font-medium flex items-center gap-1.5 hover:bg-primary/90 transition-colors"
                >
                  {isCopied ? <Check size={14} /> : <Copy size={14} />}
                  <span>{isCopied ? 'Copied' : 'Copy LaTeX'}</span>
                </button>
              </div>

              <pre className="p-4 rounded-lg bg-bg border border-border text-xs font-mono text-text-dim overflow-x-auto leading-relaxed">
                {multiPanelResult.latex_code}
              </pre>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div className="sm:col-span-2">
                  <label htmlFor={titleId} className="block text-xs font-medium text-text-dim mb-1">
                    Overall Title
                  </label>
                  <input
                    id={titleId}
                    type="text"
                    required
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    className="w-full px-3 py-2 text-sm bg-bg border border-border rounded-lg text-text focus:outline-none focus:border-primary"
                  />
                </div>

                <div>
                  <label htmlFor={columnsId} className="block text-xs font-medium text-text-dim mb-1">
                    Grid Columns
                  </label>
                  <select
                    id={columnsId}
                    value={columns}
                    onChange={(e) => setColumns(Number(e.target.value))}
                    className="w-full px-3 py-2 text-sm bg-bg border border-border rounded-lg text-text focus:outline-none focus:border-primary"
                  >
                    <option value={1}>1 Column</option>
                    <option value={2}>2 Columns</option>
                    <option value={3}>3 Columns</option>
                  </select>
                </div>
              </div>

              <div>
                <label htmlFor={captionId} className="block text-xs font-medium text-text-dim mb-1">
                  Overall Paper Caption
                </label>
                <input
                  id={captionId}
                  type="text"
                  required
                  value={caption}
                  onChange={(e) => setCaption(e.target.value)}
                  className="w-full px-3 py-2 text-sm bg-bg border border-border rounded-lg text-text focus:outline-none focus:border-primary"
                />
              </div>

              {/* Individual Figure Subcaptions */}
              <div className="space-y-3 pt-2">
                <h4 className="text-xs font-medium text-text-dim">Subcaptions for Included Figures</h4>
                {selectedFigures.map((f, idx) => {
                  const letters = ['(a)', '(b)', '(c)', '(d)', '(e)', '(f)'];
                  const defaultSub = `${letters[idx % letters.length]} ${f.title}`;
                  return (
                    <div key={f.id} className="flex items-center gap-3 p-2 rounded-lg bg-bg border border-border">
                      <span className="text-xs font-mono font-bold text-primary w-8">{letters[idx % letters.length]}</span>
                      <span className="text-xs text-text font-medium w-1/3 truncate">{f.title}</span>
                      <input
                        type="text"
                        placeholder={defaultSub}
                        value={subcaptions[f.id] || ''}
                        onChange={(e) => setSubcaptions({ ...subcaptions, [f.id]: e.target.value })}
                        className="flex-1 px-2.5 py-1 text-xs bg-surface border border-border rounded text-text focus:outline-none focus:border-primary"
                        aria-label={`Subcaption for ${f.title}`}
                      />
                    </div>
                  );
                })}
              </div>

              <div className="flex justify-end gap-3 pt-4 border-t border-border">
                <button
                  type="button"
                  onClick={onClose}
                  className="px-4 py-2 text-sm rounded-lg border border-border text-text-dim hover:text-text hover:bg-surface-hover transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting || selectedFigures.length < 2}
                  className="px-4 py-2 text-sm rounded-lg bg-primary hover:bg-primary/90 text-white font-medium transition-colors flex items-center gap-2 disabled:opacity-50"
                >
                  {isSubmitting ? (
                    <span>Generating Layout...</span>
                  ) : (
                    <>
                      <Sparkles size={16} />
                      <span>Create Subfigure Grid</span>
                    </>
                  )}
                </button>
              </div>
            </form>
          )}
        </div>
      </div>
    </dialog>
  );
}

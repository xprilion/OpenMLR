import { useState, useId, type FormEvent } from 'react';
import { X, Sparkles, LineChart } from 'lucide-react';
import type { PlotType, StyleTheme, ColorPalette } from './types';

interface Props {
  readonly isOpen: boolean;
  readonly isSubmitting: boolean;
  readonly onClose: () => void;
  readonly onSubmit: (data: Record<string, unknown>) => void;
}

const PLOT_TYPES: PlotType[] = [
  'loss_curve',
  'ablation_bar',
  'pareto_frontier',
  'confusion_matrix',
  'radar_benchmark',
  'heatmap',
];

const THEMES: StyleTheme[] = ['neurips', 'icml', 'iclr', 'cvpr', 'dark'];
const PALETTES: ColorPalette[] = ['colorblind', 'viridis', 'muted', 'deep', 'tableau'];

const DEFAULT_SERIES_JSON = JSON.stringify(
  {
    Baseline: [
      { x: 100, y: 2.45, y_err: 0.12 },
      { x: 500, y: 1.89, y_err: 0.08 },
      { x: 1000, y: 1.54, y_err: 0.05 },
      { x: 2000, y: 1.32, y_err: 0.04 },
    ],
    'Ours (Sparse MoE)': [
      { x: 100, y: 2.12, y_err: 0.09 },
      { x: 500, y: 1.48, y_err: 0.06 },
      { x: 1000, y: 1.15, y_err: 0.03 },
      { x: 2000, y: 0.94, y_err: 0.02 },
    ],
  },
  null,
  2
);

export function NewFigureModal({ isOpen, isSubmitting, onClose, onSubmit }: Readonly<Props>) {
  const [title, setTitle] = useState('Training Loss Convergence');
  const [caption, setCaption] = useState('Validation loss convergence comparison across 2,000 optimization steps.');
  const [plotType, setPlotType] = useState<PlotType>('loss_curve');
  const [theme, setTheme] = useState<StyleTheme>('neurips');
  const [palette, setPalette] = useState<ColorPalette>('colorblind');
  const [xLabel, setXLabel] = useState('Optimization Step');
  const [yLabel, setYLabel] = useState('Cross-Entropy Loss');
  const [seriesDataJson, setSeriesDataJson] = useState(DEFAULT_SERIES_JSON);
  const [categoriesStr, setCategoriesStr] = useState('Baseline, Ablation A, Ablation B, Ours');

  const titleId = useId();
  const captionId = useId();
  const plotTypeId = useId();
  const themeId = useId();
  const paletteId = useId();
  const xLabelId = useId();
  const yLabelId = useId();
  const seriesId = useId();
  const categoriesId = useId();

  if (!isOpen) return null;

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    let parsedSeries = {};
    try {
      parsedSeries = JSON.parse(seriesDataJson);
    } catch {
      parsedSeries = {};
    }

    const categories = categoriesStr
      .split(',')
      .map((c) => c.trim())
      .filter(Boolean);

    onSubmit({
      title: title.trim(),
      caption: caption.trim(),
      plot_type: plotType,
      style_theme: theme,
      palette,
      x_label: xLabel.trim(),
      y_label: yLabel.trim(),
      series_data: parsedSeries,
      categories,
      width_inches: 6.0,
      height_inches: 4.0,
      generate_tikz: true,
    });
  };

  return (
    <dialog
      open
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4 overflow-y-auto w-full h-full max-w-none max-h-none border-none m-0"
      aria-labelledby="new-figure-modal-title"
    >
      <div className="bg-surface border border-border rounded-xl shadow-2xl w-full max-w-2xl overflow-hidden my-8">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-border bg-surface-hover/30">
          <div className="flex items-center gap-2">
            <div className="p-2 rounded-lg bg-primary/10 text-primary">
              <LineChart size={20} />
            </div>
            <div>
              <h2 id="new-figure-modal-title" className="text-base font-semibold text-text">
                Generate Publication Figure
              </h2>
              <p className="text-xs text-text-dim">
                Create scientific plots with conference styling, Python code, and LaTeX snippets
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

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-6 space-y-4 max-h-[75vh] overflow-y-auto">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label htmlFor={titleId} className="block text-xs font-medium text-text-dim mb-1">
                Figure Title *
              </label>
              <input
                id={titleId}
                type="text"
                required
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="e.g. Training Loss Comparison"
                className="w-full px-3 py-2 text-sm bg-bg border border-border rounded-lg text-text focus:outline-none focus:border-primary"
              />
            </div>

            <div>
              <label htmlFor={plotTypeId} className="block text-xs font-medium text-text-dim mb-1">
                Plot Type
              </label>
              <select
                id={plotTypeId}
                value={plotType}
                onChange={(e) => setPlotType(e.target.value as PlotType)}
                className="w-full px-3 py-2 text-sm bg-bg border border-border rounded-lg text-text focus:outline-none focus:border-primary uppercase"
              >
                {PLOT_TYPES.map((t) => (
                  <option key={t} value={t}>
                    {t.replace('_', ' ')}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label htmlFor={themeId} className="block text-xs font-medium text-text-dim mb-1">
                Conference Theme
              </label>
              <select
                id={themeId}
                value={theme}
                onChange={(e) => setTheme(e.target.value as StyleTheme)}
                className="w-full px-3 py-2 text-sm bg-bg border border-border rounded-lg text-text focus:outline-none focus:border-primary uppercase"
              >
                {THEMES.map((th) => (
                  <option key={th} value={th}>
                    {th}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label htmlFor={paletteId} className="block text-xs font-medium text-text-dim mb-1">
                Color Palette
              </label>
              <select
                id={paletteId}
                value={palette}
                onChange={(e) => setPalette(e.target.value as ColorPalette)}
                className="w-full px-3 py-2 text-sm bg-bg border border-border rounded-lg text-text focus:outline-none focus:border-primary uppercase"
              >
                {PALETTES.map((pal) => (
                  <option key={pal} value={pal}>
                    {pal}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label htmlFor={xLabelId} className="block text-xs font-medium text-text-dim mb-1">
                X-Axis Label
              </label>
              <input
                id={xLabelId}
                type="text"
                value={xLabel}
                onChange={(e) => setXLabel(e.target.value)}
                placeholder="Step / Compute FLOPs"
                className="w-full px-3 py-2 text-sm bg-bg border border-border rounded-lg text-text focus:outline-none focus:border-primary"
              />
            </div>

            <div>
              <label htmlFor={yLabelId} className="block text-xs font-medium text-text-dim mb-1">
                Y-Axis Label
              </label>
              <input
                id={yLabelId}
                type="text"
                value={yLabel}
                onChange={(e) => setYLabel(e.target.value)}
                placeholder="Validation Loss / Accuracy (%)"
                className="w-full px-3 py-2 text-sm bg-bg border border-border rounded-lg text-text focus:outline-none focus:border-primary"
              />
            </div>
          </div>

          <div>
            <label htmlFor={captionId} className="block text-xs font-medium text-text-dim mb-1">
              LaTeX Paper Caption
            </label>
            <input
              id={captionId}
              type="text"
              value={caption}
              onChange={(e) => setCaption(e.target.value)}
              placeholder="Descriptive figure caption for academic manuscript"
              className="w-full px-3 py-2 text-sm bg-bg border border-border rounded-lg text-text focus:outline-none focus:border-primary"
            />
          </div>

          <div>
            <label htmlFor={categoriesId} className="block text-xs font-medium text-text-dim mb-1">
              Categories (comma-separated, for Bar / Radar / Heatmaps)
            </label>
            <input
              id={categoriesId}
              type="text"
              value={categoriesStr}
              onChange={(e) => setCategoriesStr(e.target.value)}
              placeholder="Category A, Category B, Category C"
              className="w-full px-3 py-2 text-sm bg-bg border border-border rounded-lg text-text focus:outline-none focus:border-primary"
            />
          </div>

          <div>
            <label htmlFor={seriesId} className="block text-xs font-medium text-text-dim mb-1">
              Series Data (JSON format)
            </label>
            <textarea
              id={seriesId}
              rows={6}
              value={seriesDataJson}
              onChange={(e) => setSeriesDataJson(e.target.value)}
              className="w-full px-3 py-2 text-xs font-mono bg-bg border border-border rounded-lg text-text focus:outline-none focus:border-primary leading-relaxed"
            />
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
              disabled={isSubmitting || !title.trim()}
              className="px-4 py-2 text-sm rounded-lg bg-primary hover:bg-primary/90 text-white font-medium transition-colors flex items-center gap-2 disabled:opacity-50"
            >
              {isSubmitting ? (
                <span>Generating...</span>
              ) : (
                <>
                  <Sparkles size={16} />
                  <span>Generate Figure</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </dialog>
  );
}

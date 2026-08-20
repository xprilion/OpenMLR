import { useState, useEffect, useCallback, useId } from 'react';
import { LineChart, Plus, Grid, RefreshCw, Search } from 'lucide-react';
import { api } from '../../api';
import { FigurePreviewCard } from './FigurePreviewCard';
import { NewFigureModal } from './NewFigureModal';
import { MultiPanelModal } from './MultiPanelModal';
import type { FigureArtifact, MultiPanelResult, PlotType } from './types';

interface Props {
  readonly projectId?: string;
}

export function FigureStudio({ projectId = 'default' }: Readonly<Props>) {
  const [figures, setFigures] = useState<FigureArtifact[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedPlotType, setSelectedPlotType] = useState<PlotType | 'all'>('all');
  const [selectedFigureId, setSelectedFigureId] = useState<string | null>(null);
  const [selectedForMultiPanel, setSelectedForMultiPanel] = useState<string[]>([]);

  const searchInputId = useId();
  const filterPlotTypeId = useId();

  // Modals
  const [isNewModalOpen, setIsNewModalOpen] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isMultiPanelOpen, setIsMultiPanelOpen] = useState(false);
  const [isCreatingMultiPanel, setIsCreatingMultiPanel] = useState(false);
  const [multiPanelResult, setMultiPanelResult] = useState<MultiPanelResult | null>(null);

  const loadFigures = useCallback(async () => {
    setIsLoading(true);
    try {
      const data = await api.listFigures(projectId);
      setFigures(data.figures || []);
    } catch {
      setFigures([]);
    } finally {
      setIsLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    loadFigures();
  }, [loadFigures]);

  const handleCreateFigure = async (data: Record<string, unknown>) => {
    setIsGenerating(true);
    try {
      await api.generateFigure(projectId, data);
      setIsNewModalOpen(false);
      await loadFigures();
    } catch {
      // Error handled gracefully
    } finally {
      setIsGenerating(false);
    }
  };

  const handleDeleteFigure = async (id: string) => {
    try {
      await api.deleteFigure(projectId, id);
      setFigures((prev) => prev.filter((f) => f.id !== id));
      setSelectedForMultiPanel((prev) => prev.filter((fid) => fid !== id));
    } catch {
      // Error handled gracefully
    }
  };

  const handleCreateMultiPanel = async (data: Record<string, unknown>) => {
    setIsCreatingMultiPanel(true);
    try {
      const res = await api.createMultiPanelLayout(projectId, data);
      setMultiPanelResult(res);
    } catch {
      // Error handled gracefully
    } finally {
      setIsCreatingMultiPanel(false);
    }
  };

  const handleToggleSelect = (id: string) => {
    setSelectedForMultiPanel((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]
    );
  };

  const filteredFigures = figures.filter((f) => {
    const matchesSearch =
      f.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      f.caption.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesType = selectedPlotType === 'all' || f.plot_type === selectedPlotType;
    return matchesSearch && matchesType;
  });

  const selectedFiguresForMulti = figures.filter((f) => selectedForMultiPanel.includes(f.id));

  return (
    <div className="h-full flex flex-col bg-bg text-text overflow-hidden">
      {/* Top Header */}
      <div className="px-6 py-4 border-b border-border bg-surface/50 flex flex-wrap items-center justify-between gap-4 shrink-0">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-primary/10 text-primary border border-primary/20">
            <LineChart size={22} />
          </div>
          <div>
            <h1 className="text-base font-semibold text-text flex items-center gap-2">
              <span>Publication Figure Studio</span>
              <span className="text-xs font-normal text-text-dim px-2 py-0.5 rounded-full bg-surface border border-border">
                {figures.length} figures
              </span>
            </h1>
            <p className="text-xs text-text-dim">
              Vector plot generation, conference styling (NeurIPS/ICML/ICLR), and LaTeX subfigure layouts
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {selectedForMultiPanel.length >= 2 && (
            <button
              type="button"
              onClick={() => {
                setMultiPanelResult(null);
                setIsMultiPanelOpen(true);
              }}
              className="px-3 py-2 text-xs rounded-lg bg-surface border border-border text-primary hover:bg-surface-hover flex items-center gap-1.5 transition-colors font-medium"
            >
              <Grid size={14} />
              <span>Multi-Panel ({selectedForMultiPanel.length})</span>
            </button>
          )}

          <button
            type="button"
            onClick={loadFigures}
            disabled={isLoading}
            className="p-2 rounded-lg border border-border text-text-dim hover:text-text hover:bg-surface-hover transition-colors"
            title="Refresh figures"
            aria-label="Refresh figures"
          >
            <RefreshCw size={14} className={isLoading ? 'animate-spin' : ''} />
          </button>

          <button
            type="button"
            onClick={() => setIsNewModalOpen(true)}
            className="px-3.5 py-2 text-xs rounded-lg bg-primary hover:bg-primary/90 text-white font-medium flex items-center gap-1.5 transition-colors shadow-sm"
          >
            <Plus size={15} />
            <span>Generate Figure</span>
          </button>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="px-6 py-3 border-b border-border bg-surface/30 flex flex-wrap items-center justify-between gap-3 shrink-0">
        <div className="relative flex-1 max-w-sm">
          <Search size={14} className="absolute left-3 top-2.5 text-text-dim" />
          <input
            id={searchInputId}
            type="text"
            placeholder="Search figures by title or caption..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-3 py-1.5 text-xs bg-bg border border-border rounded-lg text-text focus:outline-none focus:border-primary"
            aria-label="Search figures"
          />
        </div>

        <div className="flex items-center gap-2">
          <label htmlFor={filterPlotTypeId} className="text-xs text-text-dim font-medium">
            Type:
          </label>
          <select
            id={filterPlotTypeId}
            value={selectedPlotType}
            onChange={(e) => setSelectedPlotType(e.target.value as PlotType | 'all')}
            className="px-2.5 py-1.5 text-xs bg-bg border border-border rounded-lg text-text focus:outline-none focus:border-primary uppercase"
            aria-label="Filter by plot type"
          >
            <option value="all">ALL PLOTS</option>
            <option value="loss_curve">LOSS CURVE</option>
            <option value="ablation_bar">ABLATION BAR</option>
            <option value="pareto_frontier">PARETO FRONTIER</option>
            <option value="confusion_matrix">CONFUSION MATRIX</option>
            <option value="radar_benchmark">RADAR BENCHMARK</option>
            <option value="heatmap">HEATMAP</option>
          </select>
        </div>
      </div>

      {/* Figures Grid */}
      <div className="flex-1 overflow-y-auto p-6">
        {filteredFigures.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center p-8">
            <div className="p-4 rounded-2xl bg-surface border border-border mb-3 text-text-dim">
              <LineChart size={32} />
            </div>
            <h3 className="text-sm font-semibold text-text">No Publication Figures Yet</h3>
            <p className="text-xs text-text-dim max-w-sm mt-1 mb-4">
              Generate training loss curves, ablation bar charts, or Pareto frontiers with publication styling.
            </p>
            <button
              type="button"
              onClick={() => setIsNewModalOpen(true)}
              className="px-4 py-2 text-xs rounded-lg bg-primary hover:bg-primary/90 text-white font-medium flex items-center gap-1.5 transition-colors"
            >
              <Plus size={14} />
              <span>Generate First Figure</span>
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-2 xl:grid-cols-3 gap-6">
            {filteredFigures.map((fig) => (
              <FigurePreviewCard
                key={fig.id}
                figure={fig}
                isSelected={fig.id === selectedFigureId}
                isChecked={selectedForMultiPanel.includes(fig.id)}
                onSelect={(id) => setSelectedFigureId(id)}
                onToggleSelect={handleToggleSelect}
                onDelete={handleDeleteFigure}
              />
            ))}
          </div>
        )}
      </div>

      {/* Modals */}
      <NewFigureModal
        isOpen={isNewModalOpen}
        isSubmitting={isGenerating}
        onClose={() => setIsNewModalOpen(false)}
        onSubmit={handleCreateFigure}
      />

      <MultiPanelModal
        isOpen={isMultiPanelOpen}
        isSubmitting={isCreatingMultiPanel}
        selectedFigures={selectedFiguresForMulti}
        multiPanelResult={multiPanelResult}
        onClose={() => setIsMultiPanelOpen(false)}
        onSubmit={handleCreateMultiPanel}
      />
    </div>
  );
}

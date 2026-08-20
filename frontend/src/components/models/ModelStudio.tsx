import { useState, useEffect, useCallback } from 'react';
import {
  Cpu,
  Plus,
  RefreshCw,
  Search,
  Scale,
  Trash2,
  FileText,
  Zap,
  HardDrive,
  CheckCircle2,
  Tag,
} from 'lucide-react';
import { api } from '../../api';
import { useProject } from '../../context/ProjectContext';
import type {
  ModelArtifact,
  ModelCardData,
  CheckpointInspection,
  QuantizationEstimate,
  ModelComparisonResult,
} from './types';
import { NewModelModal } from './NewModelModal';
import { ModelCardModal } from './ModelCardModal';
import { CheckpointInspectorCard } from './CheckpointInspectorCard';
import { QuantizationMatrixCard } from './QuantizationMatrixCard';
import { ModelComparisonModal } from './ModelComparisonModal';

export function ModelStudio() {
  const { activeProject } = useProject();
  const [models, setModels] = useState<ModelArtifact[]>([]);
  const [selectedModelId, setSelectedModelId] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedTag, setSelectedTag] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isRegisterOpen, setIsRegisterOpen] = useState(false);
  const [isRegistering, setIsRegistering] = useState(false);

  // Model Card Modal State
  const [cardModalData, setCardModalData] = useState<ModelCardData | null>(null);
  const [isCardLoading, setIsCardLoading] = useState(false);

  // Checkpoint Inspection State
  const [inspection, setInspection] = useState<CheckpointInspection | null>(null);
  const [isInspecting, setIsInspecting] = useState(false);

  // Quantization State
  const [quantEstimates, setQuantEstimates] = useState<QuantizationEstimate[]>([]);
  const [isQuantLoading, setIsQuantLoading] = useState(false);

  // Comparison State
  const [comparisonResult, setComparisonResult] = useState<ModelComparisonResult | null>(null);
  const [isComparing, setIsComparing] = useState(false);
  const [selectedForComparison, setSelectedForComparison] = useState<string[]>([]);

  const loadModels = useCallback(async () => {
    setIsLoading(true);
    try {
      const res = await api.listRegisteredModels(activeProject?.uuid);
      const list = res.models || [];
      setModels(list);
      if (list.length > 0 && !selectedModelId) {
        setSelectedModelId(list[0].id);
      }
    } catch {
      setModels([]);
    } finally {
      setIsLoading(false);
    }
  }, [activeProject?.uuid, selectedModelId]);

  useEffect(() => {
    loadModels();
  }, [loadModels]);

  const handleRegisterModel = async (formData: Record<string, unknown>) => {
    setIsRegistering(true);
    try {
      await api.registerModel(activeProject?.uuid, formData);
      setIsRegisterOpen(false);
      await loadModels();
    } catch (e) {
      console.error('Failed to register model:', e);
    } finally {
      setIsRegistering(false);
    }
  };

  const handleDeleteModel = async (id: string) => {
    if (!confirm('Are you sure you want to delete this model artifact from the registry?')) return;
    try {
      await api.deleteRegisteredModel(activeProject?.uuid, id);
      if (selectedModelId === id) setSelectedModelId(null);
      await loadModels();
    } catch (e) {
      console.error('Failed to delete model:', e);
    }
  };

  const handleGenerateCard = async (modelId: string) => {
    setIsCardLoading(true);
    setCardModalData(null);
    try {
      const data = await api.generateModelCard(activeProject?.uuid, modelId, {
        author: 'OpenMLR Autonomous Research Agent',
        license: 'Apache-2.0',
        gpu_type: 'NVIDIA A100-SXM4-80GB',
        gpu_hours: 24.0,
      });
      setCardModalData(data);
    } catch (e) {
      console.error('Failed to generate model card:', e);
    } finally {
      setIsCardLoading(false);
    }
  };

  const handleInspectModel = async (model: ModelArtifact) => {
    setSelectedModelId(model.id);
    setIsInspecting(true);
    try {
      const res = await api.inspectCheckpoint({
        checkpoint_path: model.checkpoint_path || `${model.name.toLowerCase().replace(/\s+/g, '_')}.safetensors`,
        parameters_count: model.parameters_count,
        model_size_mb: model.model_size_mb,
        framework: model.framework,
      });
      setInspection(res);
    } catch (e) {
      console.error('Failed to inspect checkpoint:', e);
    } finally {
      setIsInspecting(false);
    }
  };

  const handlePlanQuantization = async (model: ModelArtifact) => {
    setSelectedModelId(model.id);
    setIsQuantLoading(true);
    try {
      const res = await api.planModelQuantization(activeProject?.uuid, model.id, [
        'fp16',
        'bf16',
        'fp8',
        'int8',
        'int4',
      ]);
      setQuantEstimates(res.estimates || []);
    } catch (e) {
      console.error('Failed to plan quantization:', e);
    } finally {
      setIsQuantLoading(false);
    }
  };

  const handleToggleComparisonSelect = (id: string) => {
    setSelectedForComparison((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]
    );
  };

  const handleRunComparison = async () => {
    if (selectedForComparison.length < 2) return;
    setIsComparing(true);
    try {
      const res = await api.compareRegisteredModels(activeProject?.uuid, selectedForComparison);
      setComparisonResult(res);
    } catch (e) {
      console.error('Failed to compare models:', e);
    } finally {
      setIsComparing(false);
    }
  };

  const filteredModels = models.filter((m) => {
    const matchesSearch =
      m.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      m.architecture.toLowerCase().includes(searchTerm.toLowerCase()) ||
      m.framework.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesTag = !selectedTag || m.tags.includes(selectedTag);
    return matchesSearch && matchesTag;
  });

  const selectedModel = models.find((m) => m.id === selectedModelId);

  return (
    <div className="flex-1 flex flex-col h-full bg-bg overflow-hidden">
      {/* Header Bar */}
      <div className="flex flex-wrap items-center justify-between gap-4 p-4 border-b border-border bg-surface shrink-0">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-primary/10 text-primary">
            <Cpu size={20} />
          </div>
          <div>
            <h1 className="text-base font-semibold text-text flex items-center gap-2">
              <span>Model Registry & Governance Studio</span>
              <span className="text-xs px-2 py-0.5 rounded-full bg-primary/20 text-primary font-mono">
                {models.length} artifacts
              </span>
            </h1>
            <p className="text-xs text-text-dim">
              Track checkpoints, generate NeurIPS model cards, and compute precision quantization trade-offs
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {selectedForComparison.length >= 2 && (
            <button
              type="button"
              onClick={handleRunComparison}
              className="px-3 py-1.5 text-xs rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-medium flex items-center gap-1.5 transition-colors"
            >
              <Scale size={14} />
              <span>Compare ({selectedForComparison.length})</span>
            </button>
          )}

          <button
            type="button"
            onClick={loadModels}
            disabled={isLoading}
            className="p-2 rounded-lg border border-border text-text-dim hover:text-text hover:bg-surface-hover transition-colors"
            title="Refresh"
            aria-label="Refresh models"
          >
            <RefreshCw size={16} className={isLoading ? 'animate-spin' : ''} />
          </button>

          <button
            type="button"
            onClick={() => setIsRegisterOpen(true)}
            className="px-3 py-1.5 text-xs rounded-lg bg-primary hover:bg-primary/90 text-white font-medium flex items-center gap-1.5 transition-colors"
          >
            <Plus size={14} />
            <span>Register Model</span>
          </button>
        </div>
      </div>

      {/* Main Content Split View */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left List Pane */}
        <div className="w-full md:w-96 border-r border-border bg-surface/50 flex flex-col shrink-0">
          <div className="p-3 border-b border-border space-y-2">
            <div className="relative">
              <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-dim" />
              <input
                type="text"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="Search models, architectures..."
                className="w-full pl-9 pr-3 py-1.5 text-xs bg-bg border border-border rounded-lg text-text focus:outline-none focus:border-primary"
              />
            </div>

            {selectedTag && (
              <div className="flex items-center gap-1 text-[11px] text-primary">
                <Tag size={12} />
                <span>Tag: {selectedTag}</span>
                <button
                  type="button"
                  onClick={() => setSelectedTag(null)}
                  className="ml-auto text-text-dim hover:text-text"
                >
                  Clear
                </button>
              </div>
            )}
          </div>

          <div className="flex-1 overflow-y-auto divide-y divide-border">
            {filteredModels.length === 0 ? (
              <div className="p-8 text-center text-text-dim text-xs">
                {isLoading ? 'Loading model registry...' : 'No model artifacts registered.'}
              </div>
            ) : (
              filteredModels.map((m) => {
                const isSelected = m.id === selectedModelId;
                const isChecked = selectedForComparison.includes(m.id);
                return (
                  <div
                    key={m.id}
                    className={`p-3.5 cursor-pointer transition-colors ${
                      isSelected ? 'bg-primary/10 border-l-2 border-primary' : 'hover:bg-surface-hover/60'
                    }`}
                    onClick={() => setSelectedModelId(m.id)}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <input
                          type="checkbox"
                          checked={isChecked}
                          onChange={(e) => {
                            e.stopPropagation();
                            handleToggleComparisonSelect(m.id);
                          }}
                          className="rounded border-border bg-bg text-primary focus:ring-0 cursor-pointer"
                          aria-label={`Select ${m.name} for comparison`}
                        />
                        <span className="font-semibold text-xs text-text">{m.name}</span>
                      </div>
                      <span className="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-surface border border-border text-text-dim">
                        {m.framework}
                      </span>
                    </div>

                    <p className="text-[11px] text-text-dim mt-1 line-clamp-1">{m.description || m.architecture}</p>

                    <div className="flex items-center gap-3 mt-2 text-[10px] text-text-dim">
                      <span>{(m.parameters_count / 1_000_000).toFixed(1)}M params</span>
                      <span>{m.model_size_mb.toFixed(1)} MB</span>
                      <span className="text-primary font-mono">{m.status}</span>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Right Detail & Analysis Pane */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6 bg-bg">
          {selectedModel ? (
            <>
              {/* Selected Model Top Card */}
              <div className="p-6 rounded-xl bg-surface border border-border">
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div>
                    <div className="flex items-center gap-2">
                      <h2 className="text-lg font-bold text-text">{selectedModel.name}</h2>
                      <span className="text-xs px-2 py-0.5 rounded-full bg-primary/20 text-primary font-mono">
                        v{selectedModel.version}
                      </span>
                      <span className="text-xs px-2 py-0.5 rounded-full bg-surface border border-border text-emerald-400 font-mono uppercase">
                        {selectedModel.status}
                      </span>
                    </div>
                    <p className="text-xs text-text-dim mt-1">{selectedModel.description || 'No description provided.'}</p>
                  </div>

                  {/* Actions */}
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={() => handleGenerateCard(selectedModel.id)}
                      className="px-3 py-1.5 text-xs rounded-lg bg-surface border border-border hover:bg-surface-hover text-text flex items-center gap-1.5 transition-colors"
                    >
                      <FileText size={14} />
                      <span>Model Card</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => handleInspectModel(selectedModel)}
                      className="px-3 py-1.5 text-xs rounded-lg bg-surface border border-border hover:bg-surface-hover text-text flex items-center gap-1.5 transition-colors"
                    >
                      <HardDrive size={14} />
                      <span>Inspect</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => handlePlanQuantization(selectedModel)}
                      className="px-3 py-1.5 text-xs rounded-lg bg-surface border border-border hover:bg-surface-hover text-text flex items-center gap-1.5 transition-colors"
                    >
                      <Zap size={14} />
                      <span>Quantize</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => handleDeleteModel(selectedModel.id)}
                      className="p-1.5 rounded-lg border border-border text-text-dim hover:text-red-400 hover:bg-red-500/10 transition-colors"
                      title="Delete model"
                      aria-label="Delete model"
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                </div>

                {/* Metrics Pill Grid */}
                {selectedModel.metrics && Object.keys(selectedModel.metrics).length > 0 && (
                  <div className="mt-4 pt-4 border-t border-border flex flex-wrap gap-2">
                    {Object.entries(selectedModel.metrics).map(([k, v]) => (
                      <div
                        key={k}
                        className="px-2.5 py-1 rounded-lg bg-bg border border-border text-xs flex items-center gap-1.5 font-mono"
                      >
                        <CheckCircle2 size={12} className="text-emerald-400" />
                        <span className="text-text-dim">{k}:</span>
                        <span className="font-bold text-text">{typeof v === 'number' ? v.toFixed(4) : v}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Checkpoint Inspection Card */}
              <CheckpointInspectorCard inspection={inspection} isLoading={isInspecting} />

              {/* Quantization Matrix Card */}
              <QuantizationMatrixCard
                estimates={quantEstimates}
                isLoading={isQuantLoading}
                modelName={selectedModel.name}
              />
            </>
          ) : (
            <div className="flex flex-col items-center justify-center py-24 text-center">
              <Cpu size={48} className="text-text-dim opacity-30 mb-3" />
              <h3 className="text-sm font-semibold text-text">No Model Artifact Selected</h3>
              <p className="text-xs text-text-dim max-w-sm mt-1">
                Select a model artifact from the left list or register a new one to inspect its checkpoint and generate model cards.
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Modals */}
      <NewModelModal
        isOpen={isRegisterOpen}
        isSubmitting={isRegistering}
        onClose={() => setIsRegisterOpen(false)}
        onSubmit={handleRegisterModel}
      />

      <ModelCardModal
        cardData={cardModalData}
        isLoading={isCardLoading}
        onClose={() => setCardModalData(null)}
      />

      <ModelComparisonModal
        comparison={comparisonResult}
        isLoading={isComparing}
        onClose={() => setComparisonResult(null)}
      />
    </div>
  );
}

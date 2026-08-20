import { useState, useId } from 'react';
import { X, Cpu, Sparkles } from 'lucide-react';
import type { FrameworkType, TaskType, ModelStatus } from './types';

interface Props {
  readonly isOpen: boolean;
  readonly isSubmitting: boolean;
  readonly onClose: () => void;
  readonly onSubmit: (data: Record<string, unknown>) => void;
}

const FRAMEWORKS: FrameworkType[] = ['pytorch', 'safetensors', 'jax', 'onnx', 'gguf', 'huggingface', 'tensorrt'];
const TASK_TYPES: TaskType[] = [
  'causal_lm',
  'seq2seq',
  'classification',
  'object_detection',
  'segmentation',
  'diffusion',
  'embedding',
  'reinforcement_learning',
  'custom',
];
const STATUSES: ModelStatus[] = ['draft', 'training', 'evaluated', 'production', 'archived'];

export function NewModelModal({ isOpen, isSubmitting, onClose, onSubmit }: Readonly<Props>) {
  const [name, setName] = useState('');
  const [version, setVersion] = useState('1.0.0');
  const [architecture, setArchitecture] = useState('Transformer');
  const [framework, setFramework] = useState<FrameworkType>('safetensors');
  const [taskType, setTaskType] = useState<TaskType>('causal_lm');
  const [status, setStatus] = useState<ModelStatus>('evaluated');
  const [description, setDescription] = useState('');
  const [parametersCount, setParametersCount] = useState('125000000');
  const [modelSizeMb, setModelSizeMb] = useState('500');
  const [checkpointPath, setCheckpointPath] = useState('');
  const [baseModel, setBaseModel] = useState('');
  const [tagsStr, setTagsStr] = useState('research, baseline');
  const [metricsJson, setMetricsJson] = useState('{\n  "val_loss": 1.42,\n  "accuracy": 0.88\n}');
  const [hparamsJson, setHparamsJson] = useState('{\n  "lr": 0.0003,\n  "batch_size": 32\n}');

  const nameId = useId();
  const versionId = useId();
  const archId = useId();
  const frameworkId = useId();
  const taskTypeId = useId();
  const statusId = useId();
  const paramsId = useId();
  const sizeId = useId();
  const pathId = useId();
  const baseModelId = useId();
  const tagsId = useId();
  const descId = useId();
  const metricsId = useId();
  const hparamsId = useId();

  if (!isOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;

    let parsedMetrics = {};
    let parsedHparams = {};
    try {
      if (metricsJson.trim()) parsedMetrics = JSON.parse(metricsJson);
    } catch {
      // ignore
    }
    try {
      if (hparamsJson.trim()) parsedHparams = JSON.parse(hparamsJson);
    } catch {
      // ignore
    }

    const tags = tagsStr
      .split(',')
      .map((t) => t.trim())
      .filter(Boolean);

    onSubmit({
      name: name.trim(),
      version: version.trim() || '1.0.0',
      architecture: architecture.trim() || 'Transformer',
      framework,
      task_type: taskType,
      status,
      description: description.trim(),
      parameters_count: Number.parseInt(parametersCount, 10) || 0,
      model_size_mb: Number.parseFloat(modelSizeMb) || 0,
      checkpoint_path: checkpointPath.trim(),
      base_model: baseModel.trim(),
      tags,
      metrics: parsedMetrics,
      hyperparameters: parsedHparams,
    });
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4 overflow-y-auto"
      role="dialog"
      aria-modal="true"
      aria-labelledby="new-model-modal-title"
    >
      <div className="bg-surface border border-border rounded-xl shadow-2xl w-full max-w-2xl overflow-hidden my-8">
        <div className="flex items-center justify-between px-6 py-4 border-b border-border bg-surface-hover/30">
          <div className="flex items-center gap-2">
            <div className="p-2 rounded-lg bg-primary/10 text-primary">
              <Cpu size={20} />
            </div>
            <div>
              <h2 id="new-model-modal-title" className="text-base font-semibold text-text">
                Register Model Artifact
              </h2>
              <p className="text-xs text-text-dim">Add a trained model checkpoint and metadata to the registry</p>
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

        <form onSubmit={handleSubmit} className="p-6 space-y-4 max-h-[75vh] overflow-y-auto">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label htmlFor={nameId} className="block text-xs font-medium text-text-dim mb-1">
                Model Name *
              </label>
              <input
                id={nameId}
                type="text"
                required
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. LLaMA-3-8B-LoRA-Ablation"
                className="w-full px-3 py-2 text-sm bg-bg border border-border rounded-lg text-text focus:outline-none focus:border-primary"
              />
            </div>

            <div>
              <label htmlFor={versionId} className="block text-xs font-medium text-text-dim mb-1">
                Version
              </label>
              <input
                id={versionId}
                type="text"
                value={version}
                onChange={(e) => setVersion(e.target.value)}
                placeholder="1.0.0"
                className="w-full px-3 py-2 text-sm bg-bg border border-border rounded-lg text-text focus:outline-none focus:border-primary"
              />
            </div>

            <div>
              <label htmlFor={archId} className="block text-xs font-medium text-text-dim mb-1">
                Architecture
              </label>
              <input
                id={archId}
                type="text"
                value={architecture}
                onChange={(e) => setArchitecture(e.target.value)}
                placeholder="e.g. Transformer, DiT, ResNet"
                className="w-full px-3 py-2 text-sm bg-bg border border-border rounded-lg text-text focus:outline-none focus:border-primary"
              />
            </div>

            <div>
              <label htmlFor={frameworkId} className="block text-xs font-medium text-text-dim mb-1">
                Framework
              </label>
              <select
                id={frameworkId}
                value={framework}
                onChange={(e) => setFramework(e.target.value as FrameworkType)}
                className="w-full px-3 py-2 text-sm bg-bg border border-border rounded-lg text-text focus:outline-none focus:border-primary"
              >
                {FRAMEWORKS.map((f) => (
                  <option key={f} value={f}>
                    {f.toUpperCase()}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label htmlFor={taskTypeId} className="block text-xs font-medium text-text-dim mb-1">
                Task Type
              </label>
              <select
                id={taskTypeId}
                value={taskType}
                onChange={(e) => setTaskType(e.target.value as TaskType)}
                className="w-full px-3 py-2 text-sm bg-bg border border-border rounded-lg text-text focus:outline-none focus:border-primary"
              >
                {TASK_TYPES.map((t) => (
                  <option key={t} value={t}>
                    {t.replace('_', ' ').toUpperCase()}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label htmlFor={statusId} className="block text-xs font-medium text-text-dim mb-1">
                Status
              </label>
              <select
                id={statusId}
                value={status}
                onChange={(e) => setStatus(e.target.value as ModelStatus)}
                className="w-full px-3 py-2 text-sm bg-bg border border-border rounded-lg text-text focus:outline-none focus:border-primary"
              >
                {STATUSES.map((s) => (
                  <option key={s} value={s}>
                    {s.toUpperCase()}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label htmlFor={paramsId} className="block text-xs font-medium text-text-dim mb-1">
                Parameter Count
              </label>
              <input
                id={paramsId}
                type="number"
                value={parametersCount}
                onChange={(e) => setParametersCount(e.target.value)}
                placeholder="125000000"
                className="w-full px-3 py-2 text-sm bg-bg border border-border rounded-lg text-text focus:outline-none focus:border-primary"
              />
            </div>

            <div>
              <label htmlFor={sizeId} className="block text-xs font-medium text-text-dim mb-1">
                Model Artifact Size (MB)
              </label>
              <input
                id={sizeId}
                type="number"
                step="0.1"
                value={modelSizeMb}
                onChange={(e) => setModelSizeMb(e.target.value)}
                placeholder="500"
                className="w-full px-3 py-2 text-sm bg-bg border border-border rounded-lg text-text focus:outline-none focus:border-primary"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label htmlFor={pathId} className="block text-xs font-medium text-text-dim mb-1">
                Checkpoint Path / URI
              </label>
              <input
                id={pathId}
                type="text"
                value={checkpointPath}
                onChange={(e) => setCheckpointPath(e.target.value)}
                placeholder="/checkpoints/model.safetensors"
                className="w-full px-3 py-2 text-sm bg-bg border border-border rounded-lg text-text focus:outline-none focus:border-primary"
              />
            </div>

            <div>
              <label htmlFor={baseModelId} className="block text-xs font-medium text-text-dim mb-1">
                Base Foundation Model
              </label>
              <input
                id={baseModelId}
                type="text"
                value={baseModel}
                onChange={(e) => setBaseModel(e.target.value)}
                placeholder="e.g. meta-llama/Meta-Llama-3-8B"
                className="w-full px-3 py-2 text-sm bg-bg border border-border rounded-lg text-text focus:outline-none focus:border-primary"
              />
            </div>
          </div>

          <div>
            <label htmlFor={tagsId} className="block text-xs font-medium text-text-dim mb-1">
              Tags (comma separated)
            </label>
            <input
              id={tagsId}
              type="text"
              value={tagsStr}
              onChange={(e) => setTagsStr(e.target.value)}
              placeholder="nlp, lora, fine-tune, arxiv-repro"
              className="w-full px-3 py-2 text-sm bg-bg border border-border rounded-lg text-text focus:outline-none focus:border-primary"
            />
          </div>

          <div>
            <label htmlFor={descId} className="block text-xs font-medium text-text-dim mb-1">
              Description & Scientific Hypothesis
            </label>
            <textarea
              id={descId}
              rows={2}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Summary of novel architecture, fine-tuning technique, or ablation findings."
              className="w-full px-3 py-2 text-sm bg-bg border border-border rounded-lg text-text focus:outline-none focus:border-primary"
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label htmlFor={metricsId} className="block text-xs font-medium text-text-dim mb-1">
                Metrics (JSON format)
              </label>
              <textarea
                id={metricsId}
                rows={3}
                value={metricsJson}
                onChange={(e) => setMetricsJson(e.target.value)}
                className="w-full px-3 py-2 text-xs font-mono bg-bg border border-border rounded-lg text-text focus:outline-none focus:border-primary"
              />
            </div>

            <div>
              <label htmlFor={hparamsId} className="block text-xs font-medium text-text-dim mb-1">
                Hyperparameters (JSON format)
              </label>
              <textarea
                id={hparamsId}
                rows={3}
                value={hparamsJson}
                onChange={(e) => setHparamsJson(e.target.value)}
                className="w-full px-3 py-2 text-xs font-mono bg-bg border border-border rounded-lg text-text focus:outline-none focus:border-primary"
              />
            </div>
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
              disabled={isSubmitting || !name.trim()}
              className="px-4 py-2 text-sm rounded-lg bg-primary hover:bg-primary/90 text-white font-medium transition-colors flex items-center gap-2 disabled:opacity-50"
            >
              {isSubmitting ? (
                <span>Registering...</span>
              ) : (
                <>
                  <Sparkles size={16} />
                  <span>Register Model</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

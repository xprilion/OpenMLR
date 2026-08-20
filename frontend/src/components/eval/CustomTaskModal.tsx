import { useState } from 'react';
import { X, PlusCircle, FileCheck, Zap, AlertCircle } from 'lucide-react';
import { api } from '../../api';

interface Props {
  onClose: () => void;
  onCreated: () => void;
}

export function CustomTaskModal({ onClose, onCreated }: Readonly<Props>) {
  const [taskType, setTaskType] = useState<'reproduction' | 'optimization'>('reproduction');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Common
  const [taskId, setTaskId] = useState('');
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [difficulty, setDifficulty] = useState('medium');
  const [timeoutSeconds, setTimeoutSeconds] = useState(300);

  // Reproduction specific
  const [paperTitle, setPaperTitle] = useState('');
  const [arxivId, setArxivId] = useState('');
  const [datasetName, setDatasetName] = useState('custom');
  const [targetMetricsJson, setTargetMetricsJson] = useState('{"accuracy": 0.85, "loss": 0.25}');

  // Optimization specific
  const [kernelName, setKernelName] = useState('');
  const [framework, setFramework] = useState('triton');
  const [baselineLatencyMs, setBaselineLatencyMs] = useState(25.0);
  const [targetSpeedup, setTargetSpeedup] = useState(1.5);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      if (taskType === 'reproduction') {
        let metrics: Record<string, number> = {};
        try {
          metrics = JSON.parse(targetMetricsJson);
        } catch {
          throw new Error('Target metrics must be a valid JSON object of numbers (e.g. {"accuracy": 0.85})');
        }

        await api.registerCustomReproductionTask({
          task_id: taskId,
          name,
          description,
          paper_title: paperTitle,
          arxiv_id: arxivId,
          dataset_name: datasetName,
          target_metrics: metrics,
          difficulty,
          timeout_seconds: timeoutSeconds,
        });
      } else {
        await api.registerCustomOptimizationTask({
          task_id: taskId,
          name,
          description,
          kernel_name: kernelName,
          framework,
          baseline_latency_ms: baselineLatencyMs,
          target_speedup: targetSpeedup,
          difficulty,
          timeout_seconds: timeoutSeconds,
        });
      }

      onCreated();
      onClose();
    } catch (err: unknown) {
      const errMsg = err instanceof Error ? err.message : 'Failed to register benchmark task.';
      setError(errMsg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4">
      <div className="bg-surface border border-border rounded-2xl shadow-2xl max-w-xl w-full max-h-[90vh] flex flex-col overflow-hidden animate-in fade-in zoom-in-95 duration-150">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-border bg-bg/40">
          <div className="flex items-center gap-2.5">
            <PlusCircle size={18} className="text-primary" />
            <h3 className="text-sm font-bold text-text">Register Custom Benchmark Task</h3>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1 rounded-lg text-text-dim hover:text-text hover:bg-surface-hover transition-colors"
          >
            <X size={18} />
          </button>
        </div>

        {/* Form content */}
        <form onSubmit={handleSubmit} className="p-6 overflow-y-auto space-y-4 text-xs">
          {/* Type Toggle */}
          <div className="flex items-center gap-2 p-1 bg-bg border border-border rounded-xl">
            <button
              type="button"
              onClick={() => setTaskType('reproduction')}
              className={`flex-1 py-1.5 rounded-lg flex items-center justify-center gap-1.5 font-semibold transition-all ${
                taskType === 'reproduction' ? 'bg-primary text-white shadow-xs' : 'text-text-dim hover:text-text'
              }`}
            >
              <FileCheck size={14} />
              <span>Paper Reproduction</span>
            </button>
            <button
              type="button"
              onClick={() => setTaskType('optimization')}
              className={`flex-1 py-1.5 rounded-lg flex items-center justify-center gap-1.5 font-semibold transition-all ${
                taskType === 'optimization' ? 'bg-primary text-white shadow-xs' : 'text-text-dim hover:text-text'
              }`}
            >
              <Zap size={14} />
              <span>Kernel Optimization</span>
            </button>
          </div>

          {error && (
            <div className="bg-rose-500/10 border border-rose-500/30 rounded-xl p-3 flex items-center gap-2 text-rose-400">
              <AlertCircle size={14} className="shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {/* Common fields */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label htmlFor="eval-task-id" className="block text-text-dim font-medium mb-1">Task ID</label>
              <input
                id="eval-task-id"
                type="text"
                required
                value={taskId}
                onChange={(e) => setTaskId(e.target.value)}
                placeholder="e.g. repro-flashattention-3"
                className="w-full bg-bg border border-border rounded-xl px-3 py-1.5 text-text focus:border-primary focus:outline-none"
              />
            </div>
            <div>
              <label htmlFor="eval-task-name" className="block text-text-dim font-medium mb-1">Task Name</label>
              <input
                id="eval-task-name"
                type="text"
                required
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. FlashAttention-3 Hopper FP8"
                className="w-full bg-bg border border-border rounded-xl px-3 py-1.5 text-text focus:border-primary focus:outline-none"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label htmlFor="eval-task-difficulty" className="block text-text-dim font-medium mb-1">Difficulty</label>
              <select
                id="eval-task-difficulty"
                value={difficulty}
                onChange={(e) => setDifficulty(e.target.value)}
                className="w-full bg-bg border border-border rounded-xl px-3 py-1.5 text-text focus:border-primary focus:outline-none"
              >
                <option value="easy">Easy</option>
                <option value="medium">Medium</option>
                <option value="hard">Hard</option>
              </select>
            </div>
            <div>
              <label htmlFor="eval-task-timeout" className="block text-text-dim font-medium mb-1">Timeout (seconds)</label>
              <input
                id="eval-task-timeout"
                type="number"
                min="10"
                value={timeoutSeconds}
                onChange={(e) => setTimeoutSeconds(Number.parseInt(e.target.value, 10) || 300)}
                className="w-full bg-bg border border-border rounded-xl px-3 py-1.5 text-text focus:border-primary focus:outline-none"
              />
            </div>
          </div>

          <div>
            <label htmlFor="eval-task-desc" className="block text-text-dim font-medium mb-1">Description</label>
            <textarea
              id="eval-task-desc"
              required
              rows={2}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Describe research benchmark objective and verification criteria..."
              className="w-full bg-bg border border-border rounded-xl p-2.5 text-text focus:border-primary focus:outline-none"
            />
          </div>

          {/* Specific fields */}
          {taskType === 'reproduction' ? (
            <>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label htmlFor="eval-paper-title" className="block text-text-dim font-medium mb-1">Paper Title</label>
                  <input
                    id="eval-paper-title"
                    type="text"
                    required
                    value={paperTitle}
                    onChange={(e) => setPaperTitle(e.target.value)}
                    placeholder="e.g. Attention Is All You Need"
                    className="w-full bg-bg border border-border rounded-xl px-3 py-1.5 text-text focus:border-primary focus:outline-none"
                  />
                </div>
                <div>
                  <label htmlFor="eval-arxiv-id" className="block text-text-dim font-medium mb-1">arXiv ID (optional)</label>
                  <input
                    id="eval-arxiv-id"
                    type="text"
                    value={arxivId}
                    onChange={(e) => setArxivId(e.target.value)}
                    placeholder="e.g. 1706.03762"
                    className="w-full bg-bg border border-border rounded-xl px-3 py-1.5 text-text focus:border-primary focus:outline-none"
                  />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label htmlFor="eval-dataset-name" className="block text-text-dim font-medium mb-1">Dataset Name</label>
                  <input
                    id="eval-dataset-name"
                    type="text"
                    value={datasetName}
                    onChange={(e) => setDatasetName(e.target.value)}
                    placeholder="e.g. WMT14 English-German"
                    className="w-full bg-bg border border-border rounded-xl px-3 py-1.5 text-text focus:border-primary focus:outline-none"
                  />
                </div>
              </div>
              <div>
                <label htmlFor="eval-target-metrics" className="block text-text-dim font-medium mb-1">Target Metrics (JSON)</label>
                <input
                  id="eval-target-metrics"
                  type="text"
                  required
                  value={targetMetricsJson}
                  onChange={(e) => setTargetMetricsJson(e.target.value)}
                  placeholder='{"bleu": 28.4, "perplexity": 4.5}'
                  className="w-full bg-bg border border-border rounded-xl px-3 py-1.5 text-text font-mono focus:border-primary focus:outline-none"
                />
              </div>
            </>
          ) : (
            <>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label htmlFor="eval-kernel-name" className="block text-text-dim font-medium mb-1">Kernel Name</label>
                  <input
                    id="eval-kernel-name"
                    type="text"
                    required
                    value={kernelName}
                    onChange={(e) => setKernelName(e.target.value)}
                    placeholder="e.g. fused_layernorm_gelu"
                    className="w-full bg-bg border border-border rounded-xl px-3 py-1.5 text-text focus:border-primary focus:outline-none"
                  />
                </div>
                <div>
                  <label htmlFor="eval-framework" className="block text-text-dim font-medium mb-1">Framework</label>
                  <select
                    id="eval-framework"
                    value={framework}
                    onChange={(e) => setFramework(e.target.value)}
                    className="w-full bg-bg border border-border rounded-xl px-3 py-1.5 text-text focus:border-primary focus:outline-none"
                  >
                    <option value="triton">Triton</option>
                    <option value="cuda">CUDA C++</option>
                    <option value="torch">PyTorch C++/ATen</option>
                  </select>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label htmlFor="eval-baseline-latency" className="block text-text-dim font-medium mb-1">Baseline Latency (ms)</label>
                  <input
                    id="eval-baseline-latency"
                    type="number"
                    step="0.1"
                    min="0.01"
                    required
                    value={baselineLatencyMs}
                    onChange={(e) => setBaselineLatencyMs(parseFloat(e.target.value))}
                    className="w-full bg-bg border border-border rounded-xl px-3 py-1.5 text-text focus:border-primary focus:outline-none"
                  />
                </div>
                <div>
                  <label htmlFor="eval-target-speedup" className="block text-text-dim font-medium mb-1">Target Speedup (x)</label>
                  <input
                    id="eval-target-speedup"
                    type="number"
                    step="0.1"
                    min="1.1"
                    required
                    value={targetSpeedup}
                    onChange={(e) => setTargetSpeedup(parseFloat(e.target.value))}
                    className="w-full bg-bg border border-border rounded-xl px-3 py-1.5 text-text focus:border-primary focus:outline-none"
                  />
                </div>
              </div>
            </>
          )}

          <div className="pt-2 flex justify-end gap-2 border-t border-border">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-1.5 rounded-xl bg-surface hover:bg-surface-hover border border-border text-text font-medium"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="px-4 py-1.5 rounded-xl bg-primary hover:bg-primary/90 text-white font-bold disabled:opacity-50"
            >
              {loading ? 'Registering...' : 'Register Task'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

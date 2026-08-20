import React, { useState } from 'react';
import type { ParameterSpec, ParamType } from './types';
import { Plus, Trash2 } from 'lucide-react';

interface NewSweepModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (payload: Record<string, unknown>) => Promise<void>;
}

interface ParamRow {
  name: string;
  type: ParamType;
  minVal: string;
  maxVal: string;
  step: string;
  choices: string;
}

export const NewSweepModal: React.FC<NewSweepModalProps> = ({ isOpen, onClose, onSubmit }) => {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [method, setMethod] = useState<'grid' | 'random' | 'bayesian' | 'hyperband'>('random');
  const [objectiveMetric, setObjectiveMetric] = useState('val_loss');
  const [goal, setGoal] = useState<'minimize' | 'maximize'>('minimize');
  const [maxTrials, setMaxTrials] = useState(10);
  const [earlyStoppingEnabled, setEarlyStoppingEnabled] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const [paramRows, setParamRows] = useState<ParamRow[]>([
    { name: 'learning_rate', type: 'loguniform', minVal: '0.00001', maxVal: '0.01', step: '', choices: '' },
    { name: 'batch_size', type: 'choice', minVal: '', maxVal: '', step: '', choices: '16, 32, 64' },
  ]);

  if (!isOpen) return null;

  const handleAddParam = () => {
    setParamRows((rows) => [
      ...rows,
      { name: `param_${rows.length + 1}`, type: 'uniform', minVal: '0.1', maxVal: '0.9', step: '0.1', choices: '' },
    ]);
  };

  const handleRemoveParam = (index: number) => {
    setParamRows((rows) => rows.filter((_, i) => i !== index));
  };

  const handleParamChange = (index: number, field: keyof ParamRow, value: string) => {
    setParamRows((rows) =>
      rows.map((r, i) => (i === index ? { ...r, [field]: value } : r))
    );
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;

    const parameters: Record<string, ParameterSpec> = {};
    paramRows.forEach((row) => {
      if (!row.name.trim()) return;
      const spec: ParameterSpec = {
        name: row.name.trim(),
        param_type: row.type,
      };
      if (row.type === 'choice' || row.type === 'categorical') {
        spec.choices = row.choices
          .split(',')
          .map((c) => {
            const trimmed = c.trim();
            return !isNaN(Number(trimmed)) ? Number(trimmed) : trimmed;
          })
          .filter(Boolean);
      } else {
        if (row.minVal) spec.min_val = Number(row.minVal);
        if (row.maxVal) spec.max_val = Number(row.maxVal);
        if (row.step) spec.step = Number(row.step);
      }
      parameters[row.name.trim()] = spec;
    });

    const payload = {
      name: name.trim(),
      description: description.trim(),
      method,
      objective_metric: objectiveMetric.trim() || 'val_loss',
      goal,
      max_trials: maxTrials,
      parameters,
      early_stopping: {
        enabled: earlyStoppingEnabled,
        min_steps: 5,
        reduction_factor: 3.0,
      },
    };

    setSubmitting(true);
    try {
      await onSubmit(payload);
      onClose();
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
      <div className="bg-surface border border-border rounded-xl max-w-xl w-full p-5 flex flex-col gap-4 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between border-b border-border pb-3">
          <h3 className="text-sm font-semibold text-text">Create Hyperparameter Sweep</h3>
          <button type="button" onClick={onClose} className="text-text-dim hover:text-text text-sm">
            ✕
          </button>
        </div>

        <form onSubmit={handleSubmit} className="flex flex-col gap-4 text-xs">
          <div className="grid grid-cols-2 gap-3">
            <div className="flex flex-col gap-1 col-span-2">
              <label className="text-text-dim font-medium">Sweep Name *</label>
              <input
                type="text"
                required
                placeholder="e.g. BERT Attention & LR Sweep"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="px-3 py-1.5 bg-bg border border-border rounded text-text text-xs focus:outline-none focus:border-primary"
              />
            </div>

            <div className="flex flex-col gap-1 col-span-2">
              <label className="text-text-dim font-medium">Description</label>
              <input
                type="text"
                placeholder="Hypothesis or optimization goal..."
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                className="px-3 py-1.5 bg-bg border border-border rounded text-text text-xs focus:outline-none focus:border-primary"
              />
            </div>

            <div className="flex flex-col gap-1">
              <label className="text-text-dim font-medium">Search Method</label>
              <select
                value={method}
                onChange={(e) => setMethod(e.target.value as 'grid' | 'random' | 'bayesian' | 'hyperband')}
                className="px-3 py-1.5 bg-bg border border-border rounded text-text text-xs focus:outline-none focus:border-primary"
              >
                <option value="random">Random Search</option>
                <option value="grid">Grid Search</option>
                <option value="bayesian">Bayesian Optimization</option>
                <option value="hyperband">Hyperband / ASHA</option>
              </select>
            </div>

            <div className="flex flex-col gap-1">
              <label className="text-text-dim font-medium">Max Trials</label>
              <input
                type="number"
                min={1}
                max={200}
                value={maxTrials}
                onChange={(e) => setMaxTrials(Number(e.target.value))}
                className="px-3 py-1.5 bg-bg border border-border rounded text-text text-xs focus:outline-none focus:border-primary"
              />
            </div>

            <div className="flex flex-col gap-1">
              <label className="text-text-dim font-medium">Objective Metric</label>
              <input
                type="text"
                value={objectiveMetric}
                onChange={(e) => setObjectiveMetric(e.target.value)}
                placeholder="val_loss, accuracy..."
                className="px-3 py-1.5 bg-bg border border-border rounded text-text text-xs focus:outline-none focus:border-primary"
              />
            </div>

            <div className="flex flex-col gap-1">
              <label className="text-text-dim font-medium">Goal</label>
              <select
                value={goal}
                onChange={(e) => setGoal(e.target.value as 'minimize' | 'maximize')}
                className="px-3 py-1.5 bg-bg border border-border rounded text-text text-xs focus:outline-none focus:border-primary"
              >
                <option value="minimize">Minimize (e.g. Loss)</option>
                <option value="maximize">Maximize (e.g. Accuracy / F1)</option>
              </select>
            </div>
          </div>

          {/* Search Space Parameters */}
          <div className="border-t border-border pt-3 flex flex-col gap-2">
            <div className="flex items-center justify-between">
              <span className="font-semibold text-text">Hyperparameter Search Space</span>
              <button
                type="button"
                onClick={handleAddParam}
                className="flex items-center gap-1 text-[11px] text-primary hover:underline"
              >
                <Plus className="w-3 h-3" /> Add Dimension
              </button>
            </div>

            <div className="flex flex-col gap-2 max-h-48 overflow-y-auto pr-1">
              {paramRows.map((row, idx) => (
                <div key={idx} className="bg-bg border border-border p-2 rounded flex flex-col gap-2">
                  <div className="flex items-center gap-2">
                    <input
                      type="text"
                      placeholder="Parameter name (e.g. lr)"
                      value={row.name}
                      onChange={(e) => handleParamChange(idx, 'name', e.target.value)}
                      className="px-2 py-1 bg-surface border border-border rounded text-text text-xs flex-1"
                    />
                    <select
                      value={row.type}
                      onChange={(e) => handleParamChange(idx, 'type', e.target.value)}
                      className="px-2 py-1 bg-surface border border-border rounded text-text text-xs w-32"
                    >
                      <option value="uniform">Uniform</option>
                      <option value="loguniform">Log-Uniform</option>
                      <option value="int_uniform">Int-Uniform</option>
                      <option value="choice">Choice/Categorical</option>
                    </select>
                    <button
                      type="button"
                      onClick={() => handleRemoveParam(idx)}
                      className="text-rose-400 hover:text-rose-300 p-1"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>

                  {row.type === 'choice' ? (
                    <input
                      type="text"
                      placeholder="Comma-separated values (e.g. 16, 32, 64, 128)"
                      value={row.choices}
                      onChange={(e) => handleParamChange(idx, 'choices', e.target.value)}
                      className="px-2 py-1 bg-surface border border-border rounded text-text text-xs w-full"
                    />
                  ) : (
                    <div className="grid grid-cols-3 gap-2">
                      <input
                        type="text"
                        placeholder="Min"
                        value={row.minVal}
                        onChange={(e) => handleParamChange(idx, 'minVal', e.target.value)}
                        className="px-2 py-1 bg-surface border border-border rounded text-text text-xs"
                      />
                      <input
                        type="text"
                        placeholder="Max"
                        value={row.maxVal}
                        onChange={(e) => handleParamChange(idx, 'maxVal', e.target.value)}
                        className="px-2 py-1 bg-surface border border-border rounded text-text text-xs"
                      />
                      <input
                        type="text"
                        placeholder="Step (optional)"
                        value={row.step}
                        onChange={(e) => handleParamChange(idx, 'step', e.target.value)}
                        className="px-2 py-1 bg-surface border border-border rounded text-text text-xs"
                      />
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Early Stopping Toggle */}
          <div className="border-t border-border pt-3 flex items-center justify-between">
            <div className="flex flex-col">
              <span className="text-text font-medium">Enable Early Stopping / Pruning</span>
              <span className="text-text-dim text-[11px]">Automatically halt unpromising trials via ASHA median comparison.</span>
            </div>
            <input
              type="checkbox"
              checked={earlyStoppingEnabled}
              onChange={(e) => setEarlyStoppingEnabled(e.target.checked)}
              className="accent-primary w-4 h-4 cursor-pointer"
            />
          </div>

          {/* Submit */}
          <div className="flex justify-end gap-2 border-t border-border pt-3">
            <button
              type="button"
              onClick={onClose}
              className="px-3 py-1.5 bg-border hover:bg-border/80 text-text rounded text-xs"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting || !name.trim()}
              className="px-4 py-1.5 bg-primary hover:bg-primary/90 text-white rounded text-xs font-medium transition-colors disabled:opacity-50"
            >
              {submitting ? 'Creating...' : 'Create Sweep'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

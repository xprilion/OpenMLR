import React from 'react';
import { Play, ArrowRight, Plus } from 'lucide-react';
import type { ResearchPhaseType } from './types';

export interface StartGoalModalProps {
  show: boolean;
  onClose: () => void;
  onSubmit: (goal: string) => Promise<void>;
  loading: boolean;
}

export function StartGoalModal({ show, onClose, onSubmit, loading }: Readonly<StartGoalModalProps>) {
  const [goal, setGoal] = React.useState('');

  if (!show) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!goal.trim()) return;
    await onSubmit(goal.trim());
    setGoal('');
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4 animate-in fade-in duration-200">
      <div className="bg-surface border border-border rounded-2xl p-6 max-w-md w-full shadow-2xl space-y-4">
        <h3 className="text-base font-bold text-text flex items-center gap-2">
          <Play className="w-4 h-4 text-primary fill-current" />
          Initiate Research Workflow
        </h3>
        <p className="text-xs text-text-dim">
          Set the overarching scientific objective or hypothesis to explore.
        </p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <textarea
            value={goal}
            onChange={(e) => setGoal(e.target.value)}
            placeholder="e.g. Investigate FlashAttention-3 memory efficiency and propose a modified attention kernel for sparse inputs..."
            rows={4}
            required
            className="w-full text-xs bg-surface-hover border border-border rounded-xl p-3 text-text placeholder:text-text-dim focus:outline-none focus:border-primary resize-none"
          />

          <div className="flex items-center justify-end gap-2">
            <button
              type="button"
              onClick={onClose}
              className="px-3 py-1.5 text-xs text-text-dim hover:text-text"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading || !goal.trim()}
              className="px-4 py-2 rounded-lg bg-primary text-white text-xs font-medium hover:bg-primary/90 disabled:opacity-50"
            >
              Start Workflow
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export interface TransitionPhaseModalProps {
  show: boolean;
  nextPhase: ResearchPhaseType | null;
  onClose: () => void;
  onSubmit: (reason: string) => Promise<void>;
  loading: boolean;
}

export function TransitionPhaseModal({
  show,
  nextPhase,
  onClose,
  onSubmit,
  loading,
}: Readonly<TransitionPhaseModalProps>) {
  const [reason, setReason] = React.useState('');

  if (!show || !nextPhase) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await onSubmit(reason.trim());
    setReason('');
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4 animate-in fade-in duration-200">
      <div className="bg-surface border border-border rounded-2xl p-6 max-w-md w-full shadow-2xl space-y-4">
        <h3 className="text-base font-bold text-text flex items-center gap-2">
          <ArrowRight className="w-4 h-4 text-primary" />
          Advance to {nextPhase.replace('_', ' ')} Phase
        </h3>
        <p className="text-xs text-text-dim">
          Record the rationale or findings that justify advancing to the next research phase.
        </p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <textarea
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder="e.g. Completed literature survey with 10 benchmarked papers and synthesized baseline metrics..."
            rows={3}
            className="w-full text-xs bg-surface-hover border border-border rounded-xl p-3 text-text placeholder:text-text-dim focus:outline-none focus:border-primary resize-none"
          />

          <div className="flex items-center justify-end gap-2">
            <button
              type="button"
              onClick={onClose}
              className="px-3 py-1.5 text-xs text-text-dim hover:text-text"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="px-4 py-2 rounded-lg bg-primary text-white text-xs font-medium hover:bg-primary/90"
            >
              Confirm Transition
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export interface AddMilestoneModalProps {
  show: boolean;
  onClose: () => void;
  onSubmit: (title: string, description: string) => Promise<void>;
  loading: boolean;
}

export function AddMilestoneModal({
  show,
  onClose,
  onSubmit,
  loading,
}: Readonly<AddMilestoneModalProps>) {
  const [title, setTitle] = React.useState('');
  const [description, setDescription] = React.useState('');

  if (!show) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) return;
    await onSubmit(title.trim(), description.trim());
    setTitle('');
    setDescription('');
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4 animate-in fade-in duration-200">
      <div className="bg-surface border border-border rounded-2xl p-6 max-w-md w-full shadow-2xl space-y-4">
        <h3 className="text-base font-bold text-text flex items-center gap-2">
          <Plus className="w-4 h-4 text-primary" />
          Add Research Milestone
        </h3>

        <form onSubmit={handleSubmit} className="space-y-3">
          <div>
            <label htmlFor="milestone-title-input" className="text-[11px] font-semibold text-text-dim uppercase tracking-wider block mb-1">
              Milestone Title
            </label>
            <input
              id="milestone-title-input"
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Profile kernel FLOPs vs baseline"
              required
              className="w-full text-xs bg-surface-hover border border-border rounded-lg p-2.5 text-text focus:outline-none focus:border-primary"
            />
          </div>

          <div>
            <label htmlFor="milestone-desc-input" className="text-[11px] font-semibold text-text-dim uppercase tracking-wider block mb-1">
              Description & Criteria
            </label>
            <textarea
              id="milestone-desc-input"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="e.g. Measure latency under batch size 32, seq len 2048 on A100 GPU."
              rows={3}
              className="w-full text-xs bg-surface-hover border border-border rounded-lg p-2.5 text-text focus:outline-none focus:border-primary resize-none"
            />
          </div>

          <div className="flex items-center justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-3 py-1.5 text-xs text-text-dim hover:text-text"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading || !title.trim()}
              className="px-4 py-2 rounded-lg bg-primary text-white text-xs font-medium hover:bg-primary/90 disabled:opacity-50"
            >
              Save Milestone
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

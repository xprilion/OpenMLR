import { useState, useEffect, useCallback } from 'react';
import {
  Compass,
  Play,
  ArrowRight,
  Plus,
  Info,
  CheckCircle,
  Clock,
  ChevronDown,
  ChevronUp,
  RefreshCw,
} from 'lucide-react';
import { api } from '../../api';
import { useProject } from '../../context/ProjectContext';
import { PhaseStepBar } from './PhaseStepBar';
import { ResearchMilestoneCard } from './ResearchMilestoneCard';
import { ResearchArtifactsViewer } from './ResearchArtifactsViewer';
import { StartGoalModal, TransitionPhaseModal, AddMilestoneModal } from './ResearchModals';
import type {
  ResearchStateData,
  ResearchPhaseType,
  MilestoneStatusType,
} from './types';

const NEXT_PHASE_MAP: Record<ResearchPhaseType, ResearchPhaseType | null> = {
  idle: 'reconnaissance',
  reconnaissance: 'hypothesis',
  hypothesis: 'experimentation',
  experimentation: 'analysis',
  analysis: 'paper_drafting',
  paper_drafting: 'completed',
  completed: null,
};

export function ResearchWorkflowStudio() {
  const { activeProject } = useProject();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [researchState, setResearchState] = useState<ResearchStateData | null>(null);
  const [guidelines, setGuidelines] = useState<string>('');
  const [showGuidelines, setShowGuidelines] = useState(true);

  // Modals state
  const [showStartModal, setShowStartModal] = useState(false);
  const [showTransitionModal, setShowTransitionModal] = useState(false);
  const [showAddMilestoneModal, setShowAddMilestoneModal] = useState(false);
  const [milestoneFilter, setMilestoneFilter] = useState<'all' | 'active' | 'completed'>('all');

  const fetchState = useCallback(async () => {
    if (!activeProject?.id) return;
    setLoading(true);
    setError(null);
    try {
      const res = await api.getProjectResearchState(activeProject.id);
      setResearchState(res.state);
      setGuidelines(res.guidelines || '');
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to fetch research state';
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, [activeProject?.id]);

  useEffect(() => {
    fetchState();
  }, [fetchState]);

  const handleStartResearch = async (goal: string) => {
    if (!activeProject?.id) return;
    try {
      setLoading(true);
      await api.startProjectResearch(activeProject.id, {
        goal,
        initial_phase: 'reconnaissance',
        generate_default_milestones: true,
      });
      setShowStartModal(false);
      await fetchState();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to start research');
    } finally {
      setLoading(false);
    }
  };

  const handleTransition = async (reason: string) => {
    if (!activeProject?.id || !researchState) return;
    const nextPhase = NEXT_PHASE_MAP[researchState.current_phase];
    if (!nextPhase) return;

    try {
      setLoading(true);
      await api.transitionProjectResearchPhase(activeProject.id, {
        next_phase: nextPhase,
        reason: reason || `Advancing to ${nextPhase} phase`,
      });
      setShowTransitionModal(false);
      await fetchState();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to transition phase');
    } finally {
      setLoading(false);
    }
  };

  const handleUpdateMilestone = async (milestoneId: string, status: MilestoneStatusType) => {
    if (!activeProject?.id) return;
    try {
      await api.updateResearchMilestone(activeProject.id, milestoneId, { status });
      await fetchState();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to update milestone');
    }
  };

  const handleCreateMilestone = async (title: string, description: string) => {
    if (!activeProject?.id) return;
    try {
      setLoading(true);
      await api.createResearchMilestone(activeProject.id, {
        title,
        description,
        phase: researchState?.current_phase || 'reconnaissance',
      });
      setShowAddMilestoneModal(false);
      await fetchState();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to create milestone');
    } finally {
      setLoading(false);
    }
  };

  const currentPhase = researchState?.current_phase || 'idle';
  const nextPhase = NEXT_PHASE_MAP[currentPhase];
  const allMilestones = researchState?.milestones || [];
  const completedMilestones = allMilestones.filter((m) => m.status === 'completed');
  const filteredMilestones = allMilestones.filter((m) => {
    if (milestoneFilter === 'completed') return m.status === 'completed';
    if (milestoneFilter === 'active') return m.phase === currentPhase;
    return true;
  });

  return (
    <div className="flex flex-col flex-1 h-full overflow-y-auto bg-bg p-4 sm:p-6 space-y-6 scrollbar-thin">
      {/* Top Banner & Title */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-surface border border-border p-5 rounded-2xl shadow-sm">
        <div className="flex items-center gap-3.5">
          <div className="w-10 h-10 rounded-xl bg-primary/10 border border-primary/20 flex items-center justify-center text-primary shadow-[0_0_15px_rgba(18,136,255,0.15)]">
            <Compass className="w-5 h-5" />
          </div>
          <div>
            <h1 className="text-base sm:text-lg font-bold text-text flex items-center gap-2">
              Research Workflow Studio
              <span className="text-xs font-normal text-text-dim px-2 py-0.5 rounded-full bg-surface-hover border border-border">
                {activeProject?.name || 'No Project Selected'}
              </span>
            </h1>
            <p className="text-xs text-text-dim mt-0.5">
              {researchState?.goal
                ? `Goal: ${researchState.goal}`
                : 'Systematic 5-phase scientific inquiry, experimentation, and paper drafting.'}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <button
            type="button"
            onClick={fetchState}
            disabled={loading}
            className="p-2 rounded-lg bg-surface border border-border text-text-dim hover:text-text hover:bg-surface-hover transition-colors"
            title="Refresh State"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>

          {!researchState?.goal || currentPhase === 'idle' ? (
            <button
              type="button"
              onClick={() => setShowStartModal(true)}
              className="flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-primary text-white text-xs font-medium hover:bg-primary/90 transition-colors shadow-sm"
            >
              <Play className="w-3.5 h-3.5 fill-current" />
              Start Research Goal
            </button>
          ) : (
            nextPhase && (
              <button
                type="button"
                onClick={() => setShowTransitionModal(true)}
                className="flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-primary text-white text-xs font-medium hover:bg-primary/90 transition-colors shadow-[0_0_15px_rgba(18,136,255,0.2)]"
              >
                <span>Advance to {nextPhase.replace('_', ' ')}</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            )
          )}
        </div>
      </div>

      {error && (
        <div className="p-3 bg-error/10 border border-error/20 rounded-xl text-xs text-error">
          {error}
        </div>
      )}

      {/* Phase Progression Stepper */}
      <PhaseStepBar currentPhase={currentPhase} />

      {/* Phase Instructions & Guidelines Accordion */}
      {guidelines && (
        <div className="bg-surface border border-border rounded-xl p-4 shadow-sm">
          <button
            type="button"
            onClick={() => setShowGuidelines(!showGuidelines)}
            className="flex items-center justify-between w-full text-left"
          >
            <div className="flex items-center gap-2">
              <Info className="w-4 h-4 text-primary" />
              <span className="text-xs font-bold uppercase tracking-wider text-text">
                Phase Guidelines & Execution Objectives
              </span>
            </div>
            {showGuidelines ? (
              <ChevronUp className="w-4 h-4 text-text-dim" />
            ) : (
              <ChevronDown className="w-4 h-4 text-text-dim" />
            )}
          </button>

          {showGuidelines && (
            <div className="mt-3 text-xs text-text-dim whitespace-pre-wrap leading-relaxed bg-surface-hover/50 p-3 rounded-lg border border-border/50 font-sans">
              {guidelines}
            </div>
          )}
        </div>
      )}

      {/* Main Grid: Milestones & Artifacts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left Column: Research Milestones Checklist */}
        <div className="bg-surface border border-border rounded-2xl p-5 flex flex-col space-y-4 shadow-sm">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <CheckCircle className="w-4 h-4 text-primary" />
              <h2 className="text-sm font-bold text-text">Research Milestones</h2>
              <span className="text-xs text-text-dim">
                ({completedMilestones.length}/{allMilestones.length} completed)
              </span>
            </div>

            <button
              type="button"
              onClick={() => setShowAddMilestoneModal(true)}
              className="flex items-center gap-1 text-xs text-primary hover:text-primary/80 font-medium"
            >
              <Plus className="w-3.5 h-3.5" />
              Add Milestone
            </button>
          </div>

          {/* Progress bar */}
          <div className="w-full bg-surface-hover h-2 rounded-full overflow-hidden border border-border/50">
            <div
              className="bg-primary h-full transition-all duration-300 rounded-full"
              style={{
                width: `${
                  allMilestones.length > 0
                    ? (completedMilestones.length / allMilestones.length) * 100
                    : 0
                }%`,
              }}
            />
          </div>

          {/* Filter Pills */}
          <div className="flex items-center gap-1.5">
            <button
              type="button"
              onClick={() => setMilestoneFilter('all')}
              className={`px-2.5 py-1 rounded-md text-[11px] font-medium transition-colors ${
                milestoneFilter === 'all'
                  ? 'bg-primary/20 text-primary border border-primary/30'
                  : 'text-text-dim hover:text-text bg-surface-hover'
              }`}
            >
              All ({allMilestones.length})
            </button>
            <button
              type="button"
              onClick={() => setMilestoneFilter('active')}
              className={`px-2.5 py-1 rounded-md text-[11px] font-medium transition-colors ${
                milestoneFilter === 'active'
                  ? 'bg-primary/20 text-primary border border-primary/30'
                  : 'text-text-dim hover:text-text bg-surface-hover'
              }`}
            >
              Active Phase
            </button>
            <button
              type="button"
              onClick={() => setMilestoneFilter('completed')}
              className={`px-2.5 py-1 rounded-md text-[11px] font-medium transition-colors ${
                milestoneFilter === 'completed'
                  ? 'bg-primary/20 text-primary border border-primary/30'
                  : 'text-text-dim hover:text-text bg-surface-hover'
              }`}
            >
              Completed ({completedMilestones.length})
            </button>
          </div>

          {/* Milestones List */}
          <div className="space-y-3 max-h-[480px] overflow-y-auto scrollbar-thin pr-1">
            {filteredMilestones.length === 0 ? (
              <div className="text-center py-8 text-xs text-text-dim">
                No milestones in this view.
              </div>
            ) : (
              filteredMilestones.map((m) => (
                <ResearchMilestoneCard
                  key={m.milestone_id}
                  milestone={m}
                  onUpdateStatus={handleUpdateMilestone}
                />
              ))
            )}
          </div>
        </div>

        {/* Right Column: Research Artifacts Viewer */}
        <div className="flex flex-col space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-bold text-text flex items-center gap-2">
              <Clock className="w-4 h-4 text-primary" />
              Cataloged Research Artifacts
            </h2>
          </div>

          <ResearchArtifactsViewer
            artifacts={
              researchState?.artifacts || {
                papers: [],
                hypotheses: [],
                experiments: [],
                metrics: {},
                manuscript_sections: {},
                bibtex_entries: [],
              }
            }
          />
        </div>
      </div>

      {/* Start Research Modal */}
      <StartGoalModal
        show={showStartModal}
        onClose={() => setShowStartModal(false)}
        onSubmit={handleStartResearch}
        loading={loading}
      />

      {/* Transition Modal */}
      <TransitionPhaseModal
        show={showTransitionModal}
        nextPhase={nextPhase}
        onClose={() => setShowTransitionModal(false)}
        onSubmit={handleTransition}
        loading={loading}
      />

      {/* Add Milestone Modal */}
      <AddMilestoneModal
        show={showAddMilestoneModal}
        onClose={() => setShowAddMilestoneModal(false)}
        onSubmit={handleCreateMilestone}
        loading={loading}
      />
    </div>
  );
}

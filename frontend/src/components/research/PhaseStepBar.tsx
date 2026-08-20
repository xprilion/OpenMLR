import { CheckCircle2, Clock, Search, Lightbulb, FlaskConical, BarChart3, FileText, ArrowRight } from 'lucide-react';
import type { ResearchPhaseType } from './types';

export interface PhaseStepBarProps {
  currentPhase: ResearchPhaseType;
  onSelectPhase?: (phase: ResearchPhaseType) => void;
}

const PHASES: Array<{
  id: ResearchPhaseType;
  label: string;
  short: string;
  icon: typeof Search;
}> = [
  { id: 'reconnaissance', label: '1. Reconnaissance', short: 'Recon', icon: Search },
  { id: 'hypothesis', label: '2. Hypothesis', short: 'Hypothesis', icon: Lightbulb },
  { id: 'experimentation', label: '3. Experimentation', short: 'Experiment', icon: FlaskConical },
  { id: 'analysis', label: '4. Analysis', short: 'Analysis', icon: BarChart3 },
  { id: 'paper_drafting', label: '5. Paper Drafting', short: 'Drafting', icon: FileText },
];

const PHASE_ORDER: ResearchPhaseType[] = [
  'idle',
  'reconnaissance',
  'hypothesis',
  'experimentation',
  'analysis',
  'paper_drafting',
  'completed',
];

export function PhaseStepBar({ currentPhase, onSelectPhase }: Readonly<PhaseStepBarProps>) {
  const currentIndex = PHASE_ORDER.indexOf(currentPhase);

  return (
    <div className="w-full bg-surface/80 border border-border rounded-xl p-4 sm:p-5 backdrop-blur-sm shadow-sm">
      <div className="flex items-center justify-between gap-1 sm:gap-2 overflow-x-auto pb-1 scrollbar-thin">
        {PHASES.map((phase, idx) => {
          const phaseIndex = PHASE_ORDER.indexOf(phase.id);
          const isCompleted = currentIndex > phaseIndex;
          const isCurrent = currentPhase === phase.id;
          const isUpcoming = currentIndex < phaseIndex;
          const Icon = phase.icon;

          return (
            <div key={phase.id} className="flex items-center flex-1 min-w-[130px] last:flex-none">
              <button
                type="button"
                onClick={() => onSelectPhase?.(phase.id)}
                disabled={!onSelectPhase}
                className={`flex items-center gap-2.5 p-2 rounded-lg w-full text-left transition-all group ${
                  isCurrent
                    ? 'bg-primary/10 border border-primary/40 shadow-[0_0_12px_rgba(18,136,255,0.2)]'
                    : isCompleted
                      ? 'hover:bg-surface-hover/80 text-text-dim hover:text-text'
                      : 'opacity-60 text-text-dim hover:opacity-90'
                }`}
              >
                <div
                  className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 text-sm font-semibold transition-colors ${
                    isCurrent
                      ? 'bg-primary text-white ring-2 ring-primary/30'
                      : isCompleted
                        ? 'bg-success/20 text-success border border-success/30'
                        : 'bg-surface-hover border border-border text-text-dim'
                  }`}
                >
                  {isCompleted ? (
                    <CheckCircle2 className="w-4 h-4" />
                  ) : isCurrent ? (
                    <Icon className="w-4 h-4 animate-pulse" />
                  ) : (
                    <span className="text-xs">{idx + 1}</span>
                  )}
                </div>

                <div className="flex flex-col min-w-0">
                  <span
                    className={`text-xs font-semibold truncate ${
                      isCurrent ? 'text-primary' : isCompleted ? 'text-text' : 'text-text-dim'
                    }`}
                  >
                    {phase.label}
                  </span>
                  <span className="text-[10px] text-text-dim flex items-center gap-1">
                    {isCurrent && (
                      <>
                        <Clock className="w-2.5 h-2.5 text-primary animate-spin" />
                        <span className="text-primary font-medium">In Progress</span>
                      </>
                    )}
                    {isCompleted && <span className="text-success font-medium">Completed</span>}
                    {isUpcoming && <span>Pending</span>}
                  </span>
                </div>
              </button>

              {idx < PHASES.length - 1 && (
                <div className="mx-1 sm:mx-2 shrink-0 hidden md:block">
                  <ArrowRight
                    className={`w-3.5 h-3.5 ${
                      isCompleted ? 'text-success/50' : 'text-border'
                    }`}
                  />
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

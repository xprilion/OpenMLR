import { CheckCircle2, Circle, Clock, Check } from 'lucide-react';
import type { ResearchMilestoneItem, MilestoneStatusType } from './types';

export interface ResearchMilestoneCardProps {
  milestone: ResearchMilestoneItem;
  onUpdateStatus?: (milestoneId: string, status: MilestoneStatusType) => void;
  onAddArtifact?: (milestoneId: string, artifactName: string) => void;
}

export function ResearchMilestoneCard({
  milestone,
  onUpdateStatus,
}: Readonly<ResearchMilestoneCardProps>) {
  const isCompleted = milestone.status === 'completed';
  const isInProgress = milestone.status === 'in_progress';

  return (
    <div
      className={`border rounded-xl p-4 transition-all duration-200 ${
        isCompleted
          ? 'bg-surface/50 border-border/60 opacity-80'
          : isInProgress
            ? 'bg-surface border-primary/50 shadow-[0_0_15px_rgba(18,136,255,0.08)]'
            : 'bg-surface border-border hover:border-border/80'
      }`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-3 flex-1 min-w-0">
          <button
            type="button"
            onClick={() =>
              onUpdateStatus?.(
                milestone.milestone_id,
                isCompleted ? 'pending' : 'completed'
              )
            }
            className={`mt-0.5 w-5 h-5 rounded-md flex items-center justify-center transition-colors shrink-0 ${
              isCompleted
                ? 'bg-success text-white'
                : 'border border-border hover:border-primary text-text-dim hover:text-primary'
            }`}
            title={isCompleted ? 'Mark as pending' : 'Mark as completed'}
          >
            {isCompleted ? <Check className="w-3.5 h-3.5" /> : <Circle className="w-3 h-3" />}
          </button>

          <div className="flex flex-col gap-1 min-w-0 flex-1">
            <div className="flex items-center gap-2 flex-wrap">
              <span
                className={`text-sm font-medium ${
                  isCompleted ? 'line-through text-text-dim' : 'text-text'
                }`}
              >
                {milestone.title}
              </span>
              <span className="text-[10px] px-2 py-0.5 rounded-full uppercase font-bold tracking-wide bg-surface-hover text-text-dim border border-border">
                {milestone.phase}
              </span>
            </div>

            {milestone.description && (
              <p className="text-xs text-text-dim leading-relaxed">
                {milestone.description}
              </p>
            )}

            {/* Criteria Checklist */}
            {milestone.criteria && milestone.criteria.length > 0 && (
              <div className="mt-2 space-y-1 bg-surface-hover/50 p-2 rounded-lg border border-border/40">
                <span className="text-[10px] font-semibold text-text-dim uppercase tracking-wider block mb-1">
                  Acceptance Criteria:
                </span>
                {milestone.criteria.map((criterion, idx) => (
                  <div key={idx} className="flex items-center gap-1.5 text-xs text-text">
                    <div className="w-1.5 h-1.5 rounded-full bg-primary shrink-0" />
                    <span>{criterion}</span>
                  </div>
                ))}
              </div>
            )}

            {/* Output Artifacts */}
            {milestone.output_artifacts && milestone.output_artifacts.length > 0 && (
              <div className="mt-2 flex items-center gap-1.5 flex-wrap">
                <span className="text-[10px] font-semibold text-text-dim">Artifacts:</span>
                {milestone.output_artifacts.map((art, idx) => (
                  <span
                    key={idx}
                    className="text-[10px] bg-primary/10 text-primary border border-primary/20 px-2 py-0.5 rounded-md font-mono"
                  >
                    {art}
                  </span>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Status indicator */}
        <div className="shrink-0">
          {isCompleted && (
            <span className="flex items-center gap-1 text-[11px] font-medium text-success bg-success/10 px-2.5 py-1 rounded-full border border-success/20">
              <CheckCircle2 className="w-3.5 h-3.5" />
              Done
            </span>
          )}
          {isInProgress && (
            <span className="flex items-center gap-1 text-[11px] font-medium text-primary bg-primary/10 px-2.5 py-1 rounded-full border border-primary/20">
              <Clock className="w-3.5 h-3.5 animate-spin" />
              Active
            </span>
          )}
          {milestone.status === 'pending' && (
            <span className="text-[11px] font-medium text-text-dim bg-surface-hover px-2.5 py-1 rounded-full border border-border">
              Pending
            </span>
          )}
        </div>
      </div>
    </div>
  );
}

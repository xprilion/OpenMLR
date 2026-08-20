import { 
  CheckCircle2, 
  XCircle, 
  AlertCircle, 
  Sparkles, 
  Target, 
  ListChecks 
} from 'lucide-react';
import type { MetaReview } from '../../types';

interface Props {
  metaReview: MetaReview;
  averageScore: number;
  venue: string;
}

export function MetaReviewSummary({ metaReview, averageScore, venue }: Readonly<Props>) {
  const isAccept = metaReview.decision_type === 'accept' || metaReview.decision.toLowerCase().includes('accept');
  const isReject = metaReview.decision_type === 'reject' || metaReview.decision.toLowerCase().includes('reject');

  const getDecisionBadge = () => {
    if (isAccept) {
      return (
        <div className="flex items-center gap-2 px-3.5 py-1.5 rounded-xl bg-emerald-500/15 border border-emerald-500/30 text-emerald-400 font-bold text-sm">
          <CheckCircle2 size={18} />
          <span>ACCEPT ({metaReview.decision})</span>
        </div>
      );
    }
    if (isReject) {
      return (
        <div className="flex items-center gap-2 px-3.5 py-1.5 rounded-xl bg-rose-500/15 border border-rose-500/30 text-rose-400 font-bold text-sm">
          <XCircle size={18} />
          <span>REJECT ({metaReview.decision})</span>
        </div>
      );
    }
    return (
      <div className="flex items-center gap-2 px-3.5 py-1.5 rounded-xl bg-amber-500/15 border border-amber-500/30 text-amber-400 font-bold text-sm">
        <AlertCircle size={18} />
        <span>BORDERLINE ({metaReview.decision})</span>
      </div>
    );
  };

  return (
    <div className="bg-surface border border-primary/30 rounded-2xl p-6 shadow-lg relative overflow-hidden">
      {/* Glow backdrop */}
      <div className="absolute top-0 right-0 w-64 h-64 bg-primary/5 rounded-full blur-3xl pointer-events-none" />

      {/* Header bar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-5 border-b border-border">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs uppercase font-mono tracking-wider text-primary font-semibold">
              Meta-Reviewer Committee Consensus
            </span>
            <span className="text-xs px-2 py-0.5 rounded-full bg-surface-hover border border-border text-text-dim uppercase font-mono">
              {venue}
            </span>
          </div>
          <h3 className="text-lg font-bold text-text">Final Committee Recommendation</h3>
        </div>

        <div className="flex items-center gap-3 flex-wrap">
          {getDecisionBadge()}
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-bg border border-border text-xs">
            <span className="text-text-dim">Committee Avg:</span>
            <span className="font-bold text-primary">{averageScore.toFixed(1)}/10</span>
          </div>
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-bg border border-border text-xs">
            <span className="text-text-dim">Consensus:</span>
            <span className="font-bold text-text">{metaReview.consensus_score.toFixed(1)}/10</span>
          </div>
        </div>
      </div>

      {/* Consensus & Justification */}
      <div className="mt-5 space-y-4 text-xs">
        {metaReview.summary_of_consensus && (
          <div>
            <h4 className="font-semibold text-text mb-1 flex items-center gap-1.5">
              <Sparkles size={14} className="text-primary" />
              Summary of Committee Consensus
            </h4>
            <p className="text-text-dim leading-relaxed bg-bg/60 p-3.5 rounded-xl border border-border">
              {metaReview.summary_of_consensus}
            </p>
          </div>
        )}

        {metaReview.justification && (
          <div>
            <h4 className="font-semibold text-text mb-1 flex items-center gap-1.5">
              <Target size={14} className="text-amber-400" />
              Decision Justification
            </h4>
            <p className="text-text-dim leading-relaxed bg-bg/60 p-3.5 rounded-xl border border-border">
              {metaReview.justification}
            </p>
          </div>
        )}

        {/* Key Strengths & Shortcomings */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-1">
          {metaReview.key_strengths && metaReview.key_strengths.length > 0 && (
            <div className="bg-emerald-500/5 border border-emerald-500/20 rounded-xl p-3.5">
              <h5 className="font-semibold text-emerald-400 mb-2">Key Strengths Recognized</h5>
              <ul className="space-y-1 pl-1">
                {metaReview.key_strengths.map((str, idx) => (
                  <li key={`ms-${idx}`} className="text-text-dim flex items-start gap-2">
                    <span className="text-emerald-400 font-bold">•</span>
                    <span>{str}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {metaReview.primary_shortcomings && metaReview.primary_shortcomings.length > 0 && (
            <div className="bg-rose-500/5 border border-rose-500/20 rounded-xl p-3.5">
              <h5 className="font-semibold text-rose-400 mb-2">Primary Shortcomings</h5>
              <ul className="space-y-1 pl-1">
                {metaReview.primary_shortcomings.map((short, idx) => (
                  <li key={`msc-${idx}`} className="text-text-dim flex items-start gap-2">
                    <span className="text-rose-400 font-bold">•</span>
                    <span>{short}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>

        {/* Actionable Revision Plan */}
        {metaReview.actionable_revision_plan && metaReview.actionable_revision_plan.length > 0 && (
          <div className="bg-primary/5 border border-primary/20 rounded-xl p-4 mt-2">
            <h4 className="font-semibold text-primary mb-2.5 flex items-center gap-1.5">
              <ListChecks size={15} />
              Actionable Revision Plan for Camera-Ready / Resubmission
            </h4>
            <div className="space-y-2">
              {metaReview.actionable_revision_plan.map((step, idx) => (
                <div key={`rev-${idx}`} className="flex items-start gap-2.5 bg-bg/80 p-2.5 rounded-lg border border-border/50">
                  <div className="w-5 h-5 rounded-full bg-primary/20 text-primary flex items-center justify-center font-bold text-[10px] shrink-0 mt-0.5">
                    {idx + 1}
                  </div>
                  <span className="text-text-dim leading-relaxed">{step}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

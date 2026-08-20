import { useState } from 'react';
import { 
  CheckCircle, 
  AlertTriangle, 
  HelpCircle, 
  ChevronDown, 
  ChevronUp, 
  UserCheck,
  Award
} from 'lucide-react';
import type { SingleReview } from '../../types';

interface Props {
  review: SingleReview;
  index: number;
}

export function ReviewerCard({ review, index }: Readonly<Props>) {
  const [expanded, setExpanded] = useState(true);

  const getScoreBadgeColor = (score: number) => {
    if (score >= 7) return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30';
    if (score >= 5) return 'bg-amber-500/10 text-amber-400 border-amber-500/30';
    return 'bg-rose-500/10 text-rose-400 border-rose-500/30';
  };

  return (
    <div className="bg-surface border border-border rounded-xl p-5 shadow-sm hover:border-border-hover transition-all">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-border/60">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-primary/10 border border-primary/20 flex items-center justify-center text-primary font-semibold">
            R{index + 1}
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h4 className="text-sm font-semibold text-text">{review.reviewer_name}</h4>
              <span className="text-[11px] px-2 py-0.5 rounded-full bg-surface-hover text-text-dim border border-border">
                {review.role}
              </span>
            </div>
            <p className="text-xs text-text-dim mt-0.5">{review.recommendation}</p>
          </div>
        </div>

        {/* Score and confidence */}
        <div className="flex items-center gap-2 self-start sm:self-auto">
          <div className={`flex items-center gap-1 px-2.5 py-1 rounded-lg border text-xs font-semibold ${getScoreBadgeColor(review.overall_score)}`}>
            <Award size={14} />
            <span>Score: {review.overall_score}/10</span>
          </div>
          <div className="flex items-center gap-1 px-2.5 py-1 rounded-lg bg-surface-hover border border-border text-xs text-text-dim">
            <UserCheck size={14} />
            <span>Conf: {review.confidence}/5</span>
          </div>
          <button
            type="button"
            onClick={() => setExpanded(!expanded)}
            className="p-1 text-text-dim hover:text-text hover:bg-surface-hover rounded-md transition-colors"
            title={expanded ? 'Collapse review' : 'Expand review'}
          >
            {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
          </button>
        </div>
      </div>

      {/* Criteria Breakdown if available */}
      {review.criteria_scores && Object.keys(review.criteria_scores).length > 0 && (
        <div className="flex flex-wrap gap-2 pt-3 pb-1">
          {Object.entries(review.criteria_scores).map(([criterion, score]) => (
            <div
              key={criterion}
              className="text-[11px] px-2.5 py-1 rounded-md bg-bg border border-border flex items-center gap-1.5"
            >
              <span className="text-text-dim capitalize">{criterion.replace(/_/g, ' ')}:</span>
              <span className="font-medium text-text">{score}/10</span>
            </div>
          ))}
        </div>
      )}

      {/* Body content */}
      {expanded && (
        <div className="mt-4 space-y-4 text-xs">
          {/* Summary */}
          {review.summary && (
            <div>
              <h5 className="font-semibold text-text mb-1.5 flex items-center gap-1.5">
                Summary & Novelty Assessment
              </h5>
              <p className="text-text-dim leading-relaxed bg-bg/50 p-3 rounded-lg border border-border/40">
                {review.summary}
              </p>
            </div>
          )}

          {/* Strengths & Weaknesses Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {/* Strengths */}
            <div className="bg-emerald-500/5 border border-emerald-500/20 rounded-lg p-3">
              <h5 className="font-semibold text-emerald-400 mb-2 flex items-center gap-1.5">
                <CheckCircle size={14} />
                Strengths ({review.strengths?.length || 0})
              </h5>
              <ul className="space-y-1.5 pl-1">
                {review.strengths?.map((strength, i) => (
                  <li key={`str-${i}`} className="text-text-dim leading-relaxed flex items-start gap-2">
                    <span className="text-emerald-400 font-bold">•</span>
                    <span>{strength}</span>
                  </li>
                ))}
              </ul>
            </div>

            {/* Weaknesses */}
            <div className="bg-rose-500/5 border border-rose-500/20 rounded-lg p-3">
              <h5 className="font-semibold text-rose-400 mb-2 flex items-center gap-1.5">
                <AlertTriangle size={14} />
                Weaknesses ({review.weaknesses?.length || 0})
              </h5>
              <ul className="space-y-1.5 pl-1">
                {review.weaknesses?.map((weakness, i) => (
                  <li key={`weak-${i}`} className="text-text-dim leading-relaxed flex items-start gap-2">
                    <span className="text-rose-400 font-bold">•</span>
                    <span>{weakness}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>

          {/* Questions for Authors */}
          {review.questions_for_authors && review.questions_for_authors.length > 0 && (
            <div className="bg-primary/5 border border-primary/20 rounded-lg p-3">
              <h5 className="font-semibold text-primary mb-2 flex items-center gap-1.5">
                <HelpCircle size={14} />
                Questions for Authors ({review.questions_for_authors.length})
              </h5>
              <ol className="space-y-1.5 list-decimal list-inside text-text-dim leading-relaxed">
                {review.questions_for_authors.map((q, i) => (
                  <li key={`q-${i}`} className="pl-1">
                    <span>{q}</span>
                  </li>
                ))}
              </ol>
            </div>
          )}

          {/* Detailed Comments */}
          {review.detailed_comments && (
            <div>
              <h5 className="font-semibold text-text mb-1.5">Detailed Constructive Comments</h5>
              <div className="text-text-dim whitespace-pre-wrap leading-relaxed bg-bg/50 p-3 rounded-lg border border-border/40 font-mono text-[11px]">
                {review.detailed_comments}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

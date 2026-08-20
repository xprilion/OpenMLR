import { X, BookOpen, Scale, Award } from 'lucide-react';
import type { ConferenceRubric, ReviewerPersona } from '../../types';

interface Props {
  venue: string;
  rubrics: Record<string, ConferenceRubric>;
  personas: ReviewerPersona[];
  onClose: () => void;
}

export function RubricViewerModal({ venue, rubrics, personas, onClose }: Readonly<Props>) {
  const currentRubric = rubrics[venue] || Object.values(rubrics)[0];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4">
      <div className="bg-surface border border-border rounded-2xl shadow-2xl max-w-2xl w-full max-h-[85vh] flex flex-col overflow-hidden animate-in fade-in zoom-in-95 duration-150">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-border bg-bg/40">
          <div className="flex items-center gap-2.5">
            <BookOpen size={18} className="text-primary" />
            <h3 className="text-base font-bold text-text">
              Peer Review Rubric & Committee Specification
            </h3>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1 rounded-lg text-text-dim hover:text-text hover:bg-surface-hover transition-colors"
          >
            <X size={18} />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto space-y-6 text-xs">
          {currentRubric ? (
            <div>
              <div className="flex items-center justify-between pb-3 border-b border-border">
                <div>
                  <h4 className="text-sm font-bold text-text uppercase tracking-wide">
                    {currentRubric.name || venue.toUpperCase()} Review Rubric
                  </h4>
                  <p className="text-text-dim mt-0.5">{currentRubric.description}</p>
                </div>
                <div className="flex items-center gap-2">
                  <span className="px-2.5 py-1 rounded-lg bg-primary/10 border border-primary/20 text-primary font-mono font-bold">
                    Threshold: {currentRubric.acceptance_threshold || 6.0}+
                  </span>
                </div>
              </div>

              {/* Criteria List */}
              <div className="mt-4 space-y-3">
                <h5 className="font-semibold text-text flex items-center gap-1.5">
                  <Scale size={14} className="text-primary" />
                  Evaluation Criteria & Weights
                </h5>
                <div className="space-y-2">
                  {currentRubric.criteria?.map((c, i) => (
                    <div key={`crit-${i}`} className="p-3 bg-bg border border-border rounded-xl">
                      <div className="flex items-center justify-between mb-1">
                        <span className="font-semibold text-text capitalize">
                          {c.name.replace(/_/g, ' ')}
                        </span>
                        <span className="px-2 py-0.5 rounded-md bg-surface-hover text-text-dim font-mono font-medium">
                          Weight: {(c.weight * 100).toFixed(0)}%
                        </span>
                      </div>
                      <p className="text-text-dim leading-relaxed">{c.description}</p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <p className="text-text-dim">No rubric details available for {venue}.</p>
          )}

          {/* Committee Personas */}
          {personas && personas.length > 0 && (
            <div className="pt-2 border-t border-border">
              <h5 className="font-semibold text-text mb-3 flex items-center gap-1.5">
                <Award size={14} className="text-primary" />
                Reviewer Committee Personas
              </h5>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {personas.map((p) => (
                  <div key={p.id} className="p-3 bg-bg border border-border rounded-xl">
                    <div className="font-semibold text-text">{p.name}</div>
                    <div className="text-primary font-mono text-[11px] mt-0.5">{p.role}</div>
                    <div className="mt-2 flex flex-wrap gap-1">
                      {p.focus_areas?.map((fa) => (
                        <span key={fa} className="px-1.5 py-0.5 rounded bg-surface-hover text-text-dim text-[10px]">
                          {fa}
                        </span>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t border-border bg-bg/40 flex justify-end">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-1.5 rounded-lg bg-surface hover:bg-surface-hover border border-border text-text font-medium text-xs transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}

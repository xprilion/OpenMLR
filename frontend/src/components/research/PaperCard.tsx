import { useState, useCallback } from 'react';
import {
  FileText,
  ExternalLink,
  BookOpen,
  Copy,
  Check,
  Award,
  Calendar,
  Layers,
  X,
} from 'lucide-react';
import type { PaperNode } from './types';

export interface PaperCardProps {
  paper: PaperNode | null;
  onClose?: () => void;
  onAddToStudio?: (paper: PaperNode) => void;
}

export function PaperCard({
  paper,
  onClose,
  onAddToStudio,
}: Readonly<PaperCardProps>) {
  const [copiedBib, setCopiedBib] = useState(false);

  const handleCopyBibtex = useCallback(async () => {
    if (!paper) return;
    const authorStr = paper.authors.join(' and ');
    const citeKey = `${paper.authors[0]?.split(' ').pop()?.toLowerCase() || 'paper'}${paper.year}${paper.title.slice(0, 10).replace(/[^a-zA-Z0-9]/g, '').toLowerCase()}`;
    const bib = `@article{${citeKey},\n  title={${paper.title}},\n  author={${authorStr}},\n  year={${paper.year}},\n  journal={${paper.venue || 'arXiv'}}\n}`;

    try {
      if (typeof navigator !== 'undefined' && navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(bib);
      }
      setCopiedBib(true);
      setTimeout(() => setCopiedBib(false), 2000);
    } catch {
      /* ignore */
    }
  }, [paper]);

  if (!paper) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-8 text-center text-text-dim">
        <BookOpen size={36} className="text-text-dim/40 mb-3" />
        <h4 className="text-sm font-semibold text-text mb-1">No Paper Selected</h4>
        <p className="text-xs max-w-xs">
          Click any paper node in the citation graph or literature table to view extracted claims and methodology.
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full bg-surface border-l border-border select-text">
      {/* Header */}
      <div className="p-4 border-b border-border flex items-center justify-between gap-3 shrink-0">
        <span className="text-xs font-semibold text-primary uppercase tracking-wider flex items-center gap-1.5">
          <Layers size={14} />
          <span>{paper.cluster}</span>
        </span>
        <div className="flex items-center gap-1.5">
          {onClose && (
            <button
              type="button"
              className="p-1 rounded-lg text-text-dim hover:text-text hover:bg-surface-hover transition-colors"
              onClick={onClose}
              title="Close paper details"
            >
              <X size={16} />
            </button>
          )}
        </div>
      </div>

      {/* Body Content */}
      <div className="flex-1 overflow-y-auto p-5 flex flex-col gap-5">
        {/* Title & Authors */}
        <div>
          <h2 className="text-base font-bold text-text leading-snug mb-2">
            {paper.title}
          </h2>
          <p className="text-xs text-text-dim leading-relaxed">
            {paper.authors.join(', ')}
          </p>
          <div className="mt-3 flex flex-wrap items-center gap-2 text-xs">
            <span className="flex items-center gap-1 bg-bg px-2.5 py-1 rounded-md border border-border text-text-dim">
              <Calendar size={13} />
              <span>{paper.year}</span>
            </span>
            <span className="flex items-center gap-1 bg-bg px-2.5 py-1 rounded-md border border-border text-text-dim">
              <Award size={13} />
              <span>{paper.citations} citations</span>
            </span>
            {paper.venue && (
              <span className="bg-primary/10 text-primary font-medium px-2.5 py-1 rounded-md border border-primary/20">
                {paper.venue}
              </span>
            )}
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-2 pt-2 border-t border-border">
          <button
            type="button"
            className="flex-1 flex items-center justify-center gap-1.5 py-1.5 px-3 bg-bg border border-border hover:bg-surface-hover rounded-lg text-xs font-medium text-text transition-colors"
            onClick={handleCopyBibtex}
          >
            {copiedBib ? <Check size={14} className="text-success" /> : <Copy size={14} />}
            <span>{copiedBib ? 'BibTeX Copied' : 'Copy BibTeX'}</span>
          </button>
          {paper.pdfUrl && (
            <a
              href={paper.pdfUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center justify-center gap-1.5 py-1.5 px-3 bg-bg border border-border hover:bg-surface-hover rounded-lg text-xs font-medium text-text transition-colors"
            >
              <ExternalLink size={14} />
              <span>View PDF</span>
            </a>
          )}
          {onAddToStudio && (
            <button
              type="button"
              className="flex items-center justify-center gap-1.5 py-1.5 px-3 bg-primary hover:bg-primary-hover rounded-lg text-xs font-medium text-white transition-colors"
              onClick={() => onAddToStudio(paper)}
            >
              <FileText size={14} />
              <span>Cite in Studio</span>
            </button>
          )}
        </div>

        {/* Abstract */}
        <div className="flex flex-col gap-2">
          <h3 className="text-xs font-bold uppercase tracking-wider text-text-dim">Abstract</h3>
          <p className="text-xs text-text/90 leading-relaxed bg-bg p-3.5 rounded-lg border border-border">
            {paper.abstract}
          </p>
        </div>

        {/* Extracted Claims */}
        {paper.claims.length > 0 && (
          <div className="flex flex-col gap-2">
            <h3 className="text-xs font-bold uppercase tracking-wider text-text-dim">Key Claims</h3>
            <ul className="flex flex-col gap-2">
              {paper.claims.map((claim, idx) => (
                <li
                  key={`claim-${paper.id}-${idx}`}
                  className="text-xs text-text/90 bg-bg p-2.5 rounded-lg border border-border flex items-start gap-2"
                >
                  <span className="text-primary font-mono font-bold mt-0.5">•</span>
                  <span>{claim}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Methodology & Gaps Grid */}
        <div className="grid grid-cols-1 gap-2.5 pt-2 border-t border-border">
          <div className="bg-bg p-3 rounded-lg border border-border">
            <span className="text-[11px] font-semibold text-text-dim uppercase tracking-wider block mb-1">
              Methodology
            </span>
            <p className="text-xs text-text">{paper.methodology}</p>
          </div>
          <div className="bg-bg p-3 rounded-lg border border-border">
            <span className="text-[11px] font-semibold text-text-dim uppercase tracking-wider block mb-1">
              Benchmark & Metric
            </span>
            <p className="text-xs text-text font-mono">
              {paper.dataset} ({paper.metric})
            </p>
          </div>
          <div className="bg-bg p-3 rounded-lg border border-border">
            <span className="text-[11px] font-semibold text-text-dim uppercase tracking-wider block mb-1">
              Baseline Compared
            </span>
            <p className="text-xs text-text">{paper.baseline}</p>
          </div>
          <div className="bg-bg p-3 rounded-lg border border-border">
            <span className="text-[11px] font-semibold text-error/90 uppercase tracking-wider block mb-1">
              Identified Research Gap
            </span>
            <p className="text-xs text-text">{paper.gap}</p>
          </div>
        </div>
      </div>
    </div>
  );
}

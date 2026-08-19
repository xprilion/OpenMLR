import { useMemo } from 'react';
import { Check, X, GitCompare } from 'lucide-react';
import type { SectionDiff } from './types';

export interface SectionDiffViewerProps {
  diffs: SectionDiff[];
  onApplyDiff: (diffId: string) => void;
  onRejectDiff: (diffId: string) => void;
}

interface DiffLine {
  type: 'add' | 'remove' | 'same';
  text: string;
}

function computeSimpleDiff(original: string, proposed: string): DiffLine[] {
  const origLines = original.split('\n');
  const propLines = proposed.split('\n');
  const lines: DiffLine[] = [];

  const maxLen = Math.max(origLines.length, propLines.length);
  for (let i = 0; i < maxLen; i++) {
    const o = origLines[i];
    const p = propLines[i];

    if (o === p) {
      if (o !== undefined) lines.push({ type: 'same', text: o });
    } else {
      if (o !== undefined) lines.push({ type: 'remove', text: o });
      if (p !== undefined) lines.push({ type: 'add', text: p });
    }
  }
  return lines;
}

function getLineClasses(type: DiffLine['type']): string {
  if (type === 'add') return 'bg-success/15 text-success';
  if (type === 'remove') return 'bg-error/15 text-error line-through';
  return 'text-text/80';
}

function getLinePrefix(type: DiffLine['type']): string {
  if (type === 'add') return '+';
  if (type === 'remove') return '-';
  return ' ';
}

export function SectionDiffViewer({
  diffs,
  onApplyDiff,
  onRejectDiff,
}: Readonly<SectionDiffViewerProps>) {
  const pendingDiffs = useMemo(() => diffs.filter((d) => d.status === 'pending'), [diffs]);

  if (pendingDiffs.length === 0) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-8 text-center text-text-dim">
        <GitCompare size={36} className="text-text-dim/40 mb-3" />
        <h4 className="text-sm font-semibold text-text mb-1">No Pending AI Revisions</h4>
        <p className="text-xs max-w-sm">
          Select an AI action like "Expand Section" or "Polish Academic Style" to generate proposals.
        </p>
      </div>
    );
  }

  return (
    <div className="flex-1 h-full overflow-y-auto p-6 flex flex-col gap-6 bg-surface">
      <div className="flex items-center justify-between border-b border-border pb-4">
        <div>
          <h3 className="text-base font-bold text-text">AI Section Revisions</h3>
          <p className="text-xs text-text-dim">Review line-by-line proposals before applying to manuscript.</p>
        </div>
        <span className="text-xs bg-primary/20 text-primary font-medium px-2.5 py-1 rounded-full">
          {pendingDiffs.length} pending
        </span>
      </div>

      {pendingDiffs.map((diff) => {
        const diffLines = computeSimpleDiff(diff.originalText, diff.proposedText);

        return (
          <div
            key={diff.id}
            className="bg-bg border border-border rounded-xl overflow-hidden shadow-sm flex flex-col"
          >
            {/* Diff Header */}
            <div className="px-5 py-3.5 bg-surface border-b border-border flex items-center justify-between gap-4">
              <div>
                <span className="text-xs font-bold text-primary tracking-wide uppercase">
                  {diff.sectionTitle}
                </span>
                <p className="text-xs text-text-dim mt-0.5">{diff.reason}</p>
              </div>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-text-dim hover:text-error hover:bg-surface-hover rounded-lg transition-colors"
                  onClick={() => onRejectDiff(diff.id)}
                >
                  <X size={14} />
                  <span>Reject</span>
                </button>
                <button
                  type="button"
                  className="flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-medium bg-primary text-white hover:bg-primary-hover rounded-lg transition-colors shadow-sm"
                  onClick={() => onApplyDiff(diff.id)}
                >
                  <Check size={14} />
                  <span>Accept Revision</span>
                </button>
              </div>
            </div>

            {/* Diff Body */}
            <div className="p-4 font-mono text-xs overflow-x-auto flex flex-col gap-1 leading-relaxed select-text">
              {diffLines.map((line, idx) => (
                <div
                  key={`${diff.id}-line-${idx}`}
                  className={`px-2 py-0.5 rounded flex items-start gap-2 ${getLineClasses(line.type)}`}
                >
                  <span className="select-none text-text-dim w-4 shrink-0">
                    {getLinePrefix(line.type)}
                  </span>
                  <span className="whitespace-pre-wrap break-words">{line.text || ' '}</span>
                </div>
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}

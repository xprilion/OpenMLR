import React, { useState } from 'react';
import { Copy, Check, Download, Code, FileText, Trash2 } from 'lucide-react';
import type { FigureArtifact } from './types';

interface Props {
  readonly figure: FigureArtifact;
  readonly isSelected: boolean;
  readonly isChecked: boolean;
  readonly onSelect: (id: string) => void;
  readonly onToggleSelect: (id: string) => void;
  readonly onDelete: (id: string) => void;
}

export function FigurePreviewCard({
  figure,
  isSelected,
  isChecked,
  onSelect,
  onToggleSelect,
  onDelete,
}: Readonly<Props>) {
  const [activeCodeTab, setActiveCodeTab] = useState<'latex' | 'python' | 'tikz'>('latex');
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

  const handleCopy = (text: string, key: string, e: React.MouseEvent) => {
    e.stopPropagation();
    navigator.clipboard.writeText(text);
    setCopiedKey(key);
    setTimeout(() => setCopiedKey(null), 2000);
  };

  const handleDownloadSvg = (e: React.MouseEvent) => {
    e.stopPropagation();
    const blob = new Blob([figure.svg_preview], { type: 'image/svg+xml' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${figure.id}_plot.svg`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const codeContent =
    activeCodeTab === 'latex'
      ? figure.latex_snippet
      : activeCodeTab === 'python'
      ? figure.python_script
      : figure.tikz_code || '% TikZ code not available for this plot.';

  return (
    <div
      className={`rounded-xl border transition-all ${
        isSelected ? 'border-primary bg-primary/5 shadow-md' : 'border-border bg-surface hover:border-border-hover'
      }`}
      onClick={() => onSelect(figure.id)}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          onSelect(figure.id);
        }
      }}
      role="button"
      tabIndex={0}
    >
      {/* Header */}
      <div className="p-4 border-b border-border flex items-start justify-between gap-3">
        <div className="flex items-start gap-2.5">
          <input
            type="checkbox"
            checked={isChecked}
            onChange={(e) => {
              e.stopPropagation();
              onToggleSelect(figure.id);
            }}
            className="mt-1 rounded border-border accent-primary cursor-pointer"
            aria-label={`Select ${figure.title} for multi-panel`}
          />
          <div>
            <h3 className="text-sm font-semibold text-text">{figure.title}</h3>
            <p className="text-xs text-text-dim mt-0.5 line-clamp-1">{figure.caption || 'No caption'}</p>
            <div className="flex items-center gap-2 mt-2">
              <span className="text-[10px] px-2 py-0.5 rounded font-mono bg-bg border border-border text-primary uppercase">
                {figure.plot_type.replace('_', ' ')}
              </span>
              <span className="text-[10px] px-2 py-0.5 rounded font-mono bg-bg border border-border text-text-dim uppercase">
                {figure.style_theme}
              </span>
              <span className="text-[10px] text-text-dim font-mono">{figure.palette}</span>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-1.5 shrink-0">
          <button
            type="button"
            onClick={handleDownloadSvg}
            className="p-1.5 rounded-lg border border-border text-text-dim hover:text-text hover:bg-surface-hover transition-colors"
            title="Download SVG vector file"
            aria-label="Download SVG vector file"
          >
            <Download size={14} />
          </button>
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              onDelete(figure.id);
            }}
            className="p-1.5 rounded-lg border border-border text-text-dim hover:text-red-400 hover:bg-surface-hover transition-colors"
            title="Delete figure"
            aria-label="Delete figure"
          >
            <Trash2 size={14} />
          </button>
        </div>
      </div>

      {/* SVG Preview Section */}
      <div
        className="p-4 bg-bg/40 flex items-center justify-center overflow-hidden"
        dangerouslySetInnerHTML={{ __html: figure.svg_preview }}
      />

      {/* Code / Snippet Section */}
      <div className="p-4 border-t border-border bg-surface-hover/20">
        <div className="flex items-center justify-between gap-2 mb-2">
          <div className="flex items-center gap-1">
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                setActiveCodeTab('latex');
              }}
              className={`px-2.5 py-1 rounded text-[11px] font-medium flex items-center gap-1 transition-colors ${
                activeCodeTab === 'latex' ? 'bg-primary/20 text-primary' : 'text-text-dim hover:text-text'
              }`}
            >
              <FileText size={12} />
              LaTeX Figure
            </button>
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                setActiveCodeTab('python');
              }}
              className={`px-2.5 py-1 rounded text-[11px] font-medium flex items-center gap-1 transition-colors ${
                activeCodeTab === 'python' ? 'bg-primary/20 text-primary' : 'text-text-dim hover:text-text'
              }`}
            >
              <Code size={12} />
              Python Script
            </button>
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                setActiveCodeTab('tikz');
              }}
              className={`px-2.5 py-1 rounded text-[11px] font-medium flex items-center gap-1 transition-colors ${
                activeCodeTab === 'tikz' ? 'bg-primary/20 text-primary' : 'text-text-dim hover:text-text'
              }`}
            >
              TikZ Code
            </button>
          </div>

          <button
            type="button"
            onClick={(e) => handleCopy(codeContent, `${figure.id}_${activeCodeTab}`, e)}
            className="px-2 py-1 rounded text-[11px] border border-border bg-surface text-text hover:bg-surface-hover flex items-center gap-1 transition-colors"
          >
            {copiedKey === `${figure.id}_${activeCodeTab}` ? (
              <>
                <Check size={12} className="text-emerald-400" />
                <span className="text-emerald-400">Copied</span>
              </>
            ) : (
              <>
                <Copy size={12} />
                <span>Copy</span>
              </>
            )}
          </button>
        </div>

        <pre className="p-2.5 rounded bg-bg border border-border text-[10px] font-mono text-text-dim overflow-x-auto max-h-32 leading-relaxed">
          {codeContent}
        </pre>
      </div>
    </div>
  );
}

import { useState } from 'react';
import { X, Copy, Check, FileText, Code2, Quote, Leaf } from 'lucide-react';
import type { ModelCardData } from './types';

interface Props {
  readonly cardData: ModelCardData | null;
  readonly isLoading: boolean;
  readonly onClose: () => void;
}

type CardTab = 'markdown' | 'latex' | 'bibtex' | 'environmental';

interface CodeSnippetViewProps {
  readonly content: string;
  readonly copyKey: string;
  readonly copiedKey: string | null;
  readonly onCopy: (text: string, key: string) => void;
  readonly copyLabel: string;
}

function CodeSnippetView({ content, copyKey, copiedKey, onCopy, copyLabel }: CodeSnippetViewProps) {
  const isCopied = copiedKey === copyKey;
  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => onCopy(content, copyKey)}
        className="absolute top-2 right-2 px-3 py-1.5 rounded-lg bg-surface border border-border text-text hover:bg-surface-hover flex items-center gap-1.5 transition-colors z-10"
      >
        {isCopied ? <Check size={14} className="text-success" /> : <Copy size={14} />}
        <span>{isCopied ? 'Copied' : copyLabel}</span>
      </button>
      <pre className="p-4 rounded-lg bg-surface border border-border text-text-dim whitespace-pre-wrap leading-relaxed">
        {content}
      </pre>
    </div>
  );
}

function EnvironmentalTabContent({ cardData }: { readonly cardData: ModelCardData }) {
  return (
    <div className="space-y-4">
      <div className="p-4 rounded-lg bg-surface border border-border">
        <div className="flex items-center gap-3 mb-3">
          <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400">
            <Leaf size={24} />
          </div>
          <div>
            <h4 className="text-sm font-semibold text-text">Estimated Carbon Footprint</h4>
            <p className="text-xs text-text-dim">
              Estimated according to ML emissions standard guidelines (TDP × Hours × PUE × Grid)
            </p>
          </div>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-3 border-t border-border/50">
          <div className="p-3 bg-bg/80 rounded-lg">
            <span className="text-[10px] text-text-dim uppercase tracking-wider block mb-1">
              CO2 Equivalent
            </span>
            <span className="text-lg font-bold text-emerald-400">
              {cardData.co2_emissions_kg.toFixed(2)} kg
            </span>
          </div>
          <div className="p-3 bg-bg/80 rounded-lg">
            <span className="text-[10px] text-text-dim uppercase tracking-wider block mb-1">
              Total Parameters
            </span>
            <span className="text-lg font-bold text-text">
              {(cardData.summary.parameters / 1_000_000).toFixed(1)}M
            </span>
          </div>
          <div className="p-3 bg-bg/80 rounded-lg">
            <span className="text-[10px] text-text-dim uppercase tracking-wider block mb-1">
              Artifact Size
            </span>
            <span className="text-lg font-bold text-text">
              {cardData.summary.size_mb.toFixed(1)} MB
            </span>
          </div>
          <div className="p-3 bg-bg/80 rounded-lg">
            <span className="text-[10px] text-text-dim uppercase tracking-wider block mb-1">
              Framework
            </span>
            <span className="text-lg font-bold text-primary uppercase">
              {cardData.summary.framework}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}

export function ModelCardModal({ cardData, isLoading, onClose }: Readonly<Props>) {
  const [activeTab, setActiveTab] = useState<CardTab>('markdown');
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

  if (!cardData && !isLoading) return null;

  const handleCopy = (text: string, key: string) => {
    navigator.clipboard.writeText(text);
    setCopiedKey(key);
    setTimeout(() => setCopiedKey(null), 2000);
  };

  return (
    <dialog
      open
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4 overflow-y-auto w-full h-full max-w-none max-h-none border-none m-0"
      aria-labelledby="model-card-modal-title"
    >
      <div className="bg-surface border border-border rounded-xl shadow-2xl w-full max-w-3xl overflow-hidden my-8 flex flex-col max-h-[85vh]">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-border bg-surface-hover/30 shrink-0">
          <div className="flex items-center gap-2">
            <div className="p-2 rounded-lg bg-primary/10 text-primary">
              <FileText size={20} />
            </div>
            <div>
              <h2 id="model-card-modal-title" className="text-base font-semibold text-text">
                Model Card & Documentation: {cardData?.model_name || 'Loading...'}
              </h2>
              <p className="text-xs text-text-dim">
                v{cardData?.version || '1.0.0'} • NeurIPS / HuggingFace Model Card Standard
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1 rounded-lg text-text-dim hover:text-text hover:bg-surface-hover transition-colors"
            aria-label="Close dialog"
          >
            <X size={18} />
          </button>
        </div>

        {/* Tab Selection */}
        <div className="flex border-b border-border bg-surface px-6 shrink-0">
          <button
            type="button"
            onClick={() => setActiveTab('markdown')}
            className={`flex items-center gap-2 px-4 py-2.5 text-xs font-medium border-b-2 transition-colors ${
              activeTab === 'markdown'
                ? 'border-primary text-primary'
                : 'border-transparent text-text-dim hover:text-text'
            }`}
          >
            <FileText size={14} />
            Markdown
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('latex')}
            className={`flex items-center gap-2 px-4 py-2.5 text-xs font-medium border-b-2 transition-colors ${
              activeTab === 'latex'
                ? 'border-primary text-primary'
                : 'border-transparent text-text-dim hover:text-text'
            }`}
          >
            <Code2 size={14} />
            LaTeX Snippet
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('bibtex')}
            className={`flex items-center gap-2 px-4 py-2.5 text-xs font-medium border-b-2 transition-colors ${
              activeTab === 'bibtex'
                ? 'border-primary text-primary'
                : 'border-transparent text-text-dim hover:text-text'
            }`}
          >
            <Quote size={14} />
            BibTeX Citation
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('environmental')}
            className={`flex items-center gap-2 px-4 py-2.5 text-xs font-medium border-b-2 transition-colors ${
              activeTab === 'environmental'
                ? 'border-primary text-primary'
                : 'border-transparent text-text-dim hover:text-text'
            }`}
          >
            <Leaf size={14} />
            Environmental Impact
          </button>
        </div>

        {/* Body Content */}
        <div className="p-6 flex-1 overflow-y-auto bg-bg/50 font-mono text-xs">
          {isLoading || !cardData ? (
            <div className="flex items-center justify-center py-16 text-text-dim">
              <span>Generating multi-format model documentation...</span>
            </div>
          ) : (
            <>
              {activeTab === 'markdown' && (
                <CodeSnippetView
                  content={cardData.markdown}
                  copyKey="md"
                  copiedKey={copiedKey}
                  onCopy={handleCopy}
                  copyLabel="Copy Markdown"
                />
              )}
              {activeTab === 'latex' && (
                <CodeSnippetView
                  content={cardData.latex}
                  copyKey="latex"
                  copiedKey={copiedKey}
                  onCopy={handleCopy}
                  copyLabel="Copy LaTeX"
                />
              )}
              {activeTab === 'bibtex' && (
                <CodeSnippetView
                  content={cardData.bibtex}
                  copyKey="bibtex"
                  copiedKey={copiedKey}
                  onCopy={handleCopy}
                  copyLabel="Copy BibTeX"
                />
              )}
              {activeTab === 'environmental' && <EnvironmentalTabContent cardData={cardData} />}
            </>
          )}
        </div>

        {/* Footer */}
        <div className="flex justify-end px-6 py-4 border-t border-border bg-surface shrink-0">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-sm rounded-lg bg-surface border border-border text-text hover:bg-surface-hover transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </dialog>
  );
}

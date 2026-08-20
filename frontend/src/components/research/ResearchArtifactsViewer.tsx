import { useState } from 'react';
import { BookOpen, Lightbulb, FlaskConical, BarChart2, FileText, Bookmark } from 'lucide-react';
import type { ResearchArtifactsSummary } from './types';

export interface ResearchArtifactsViewerProps {
  artifacts: ResearchArtifactsSummary;
}

type ArtifactTab = 'papers' | 'hypotheses' | 'experiments' | 'metrics' | 'manuscript' | 'bibtex';

export function ResearchArtifactsViewer({ artifacts }: Readonly<ResearchArtifactsViewerProps>) {
  const [activeTab, setActiveTab] = useState<ArtifactTab>('papers');

  const paperCount = artifacts?.papers?.length || 0;
  const hypothesisCount = artifacts?.hypotheses?.length || 0;
  const experimentCount = artifacts?.experiments?.length || 0;
  const metricsCount = Object.keys(artifacts?.metrics || {}).length;
  const sectionCount = Object.keys(artifacts?.manuscript_sections || {}).length;
  const bibtexCount = artifacts?.bibtex_entries?.length || 0;

  return (
    <div className="bg-surface border border-border rounded-xl flex flex-col overflow-hidden shadow-sm">
      {/* Header Tabs */}
      <div className="flex items-center gap-1 p-2 bg-surface-hover/40 border-b border-border overflow-x-auto scrollbar-thin">
        <button
          type="button"
          onClick={() => setActiveTab('papers')}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors shrink-0 ${
            activeTab === 'papers'
              ? 'bg-primary text-white shadow-sm'
              : 'text-text-dim hover:text-text hover:bg-surface-hover'
          }`}
        >
          <BookOpen className="w-3.5 h-3.5" />
          Papers
          <span
            className={`text-[10px] px-1.5 py-0.2 rounded-full ${
              activeTab === 'papers' ? 'bg-white/20 text-white' : 'bg-surface text-text-dim'
            }`}
          >
            {paperCount}
          </span>
        </button>

        <button
          type="button"
          onClick={() => setActiveTab('hypotheses')}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors shrink-0 ${
            activeTab === 'hypotheses'
              ? 'bg-primary text-white shadow-sm'
              : 'text-text-dim hover:text-text hover:bg-surface-hover'
          }`}
        >
          <Lightbulb className="w-3.5 h-3.5" />
          Hypotheses
          <span
            className={`text-[10px] px-1.5 py-0.2 rounded-full ${
              activeTab === 'hypotheses' ? 'bg-white/20 text-white' : 'bg-surface text-text-dim'
            }`}
          >
            {hypothesisCount}
          </span>
        </button>

        <button
          type="button"
          onClick={() => setActiveTab('experiments')}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors shrink-0 ${
            activeTab === 'experiments'
              ? 'bg-primary text-white shadow-sm'
              : 'text-text-dim hover:text-text hover:bg-surface-hover'
          }`}
        >
          <FlaskConical className="w-3.5 h-3.5" />
          Experiments
          <span
            className={`text-[10px] px-1.5 py-0.2 rounded-full ${
              activeTab === 'experiments' ? 'bg-white/20 text-white' : 'bg-surface text-text-dim'
            }`}
          >
            {experimentCount}
          </span>
        </button>

        <button
          type="button"
          onClick={() => setActiveTab('metrics')}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors shrink-0 ${
            activeTab === 'metrics'
              ? 'bg-primary text-white shadow-sm'
              : 'text-text-dim hover:text-text hover:bg-surface-hover'
          }`}
        >
          <BarChart2 className="w-3.5 h-3.5" />
          Metrics
          <span
            className={`text-[10px] px-1.5 py-0.2 rounded-full ${
              activeTab === 'metrics' ? 'bg-white/20 text-white' : 'bg-surface text-text-dim'
            }`}
          >
            {metricsCount}
          </span>
        </button>

        <button
          type="button"
          onClick={() => setActiveTab('manuscript')}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors shrink-0 ${
            activeTab === 'manuscript'
              ? 'bg-primary text-white shadow-sm'
              : 'text-text-dim hover:text-text hover:bg-surface-hover'
          }`}
        >
          <FileText className="w-3.5 h-3.5" />
          Draft Sections
          <span
            className={`text-[10px] px-1.5 py-0.2 rounded-full ${
              activeTab === 'manuscript' ? 'bg-white/20 text-white' : 'bg-surface text-text-dim'
            }`}
          >
            {sectionCount}
          </span>
        </button>

        <button
          type="button"
          onClick={() => setActiveTab('bibtex')}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors shrink-0 ${
            activeTab === 'bibtex'
              ? 'bg-primary text-white shadow-sm'
              : 'text-text-dim hover:text-text hover:bg-surface-hover'
          }`}
        >
          <Bookmark className="w-3.5 h-3.5" />
          BibTeX
          <span
            className={`text-[10px] px-1.5 py-0.2 rounded-full ${
              activeTab === 'bibtex' ? 'bg-white/20 text-white' : 'bg-surface text-text-dim'
            }`}
          >
            {bibtexCount}
          </span>
        </button>
      </div>

      {/* Content Area */}
      <div className="p-4 max-h-[360px] overflow-y-auto scrollbar-thin">
        {activeTab === 'papers' && (
          <div className="space-y-2.5">
            {paperCount === 0 ? (
              <p className="text-xs text-text-dim text-center py-6">
                No papers cataloged yet. During literature reconnaissance, papers will appear here.
              </p>
            ) : (
              artifacts.papers.map((p, idx) => (
                <div key={idx} className="bg-surface-hover/40 border border-border/60 p-3 rounded-lg flex flex-col gap-1">
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-xs font-semibold text-text">
                      {String(p.title || p.name || 'Untitled Paper')}
                    </span>
                    {Boolean(p.arxiv_id || p.id) && (
                      <span className="text-[10px] font-mono bg-primary/10 text-primary px-1.5 py-0.5 rounded">
                        arXiv:{String(p.arxiv_id || p.id)}
                      </span>
                    )}
                  </div>
                  {Boolean(p.authors) && (
                    <span className="text-[11px] text-text-dim truncate">
                      {Array.isArray(p.authors) ? p.authors.join(', ') : String(p.authors)}
                    </span>
                  )}
                  {Boolean(p.summary || p.abstract) && (
                    <p className="text-[11px] text-text-dim/90 line-clamp-2 mt-1">
                      {String(p.summary || p.abstract)}
                    </p>
                  )}
                </div>
              ))
            )}
          </div>
        )}

        {activeTab === 'hypotheses' && (
          <div className="space-y-2.5">
            {hypothesisCount === 0 ? (
              <p className="text-xs text-text-dim text-center py-6">
                No hypotheses formulated yet. Formulate testable claims during the hypothesis phase.
              </p>
            ) : (
              artifacts.hypotheses.map((h, idx) => (
                <div key={idx} className="bg-surface-hover/40 border border-border/60 p-3 rounded-lg flex flex-col gap-1.5">
                  <div className="flex items-center gap-2">
                    <Lightbulb className="w-3.5 h-3.5 text-primary shrink-0" />
                    <span className="text-xs font-medium text-text">
                      {String(h.claim || h.statement || h.title || 'Hypothesis Claim')}
                    </span>
                  </div>
                  {Boolean(h.baseline || h.evaluation_criteria) && (
                    <p className="text-[11px] text-text-dim">
                      Baseline: {String(h.baseline || h.evaluation_criteria)}
                    </p>
                  )}
                </div>
              ))
            )}
          </div>
        )}

        {activeTab === 'experiments' && (
          <div className="space-y-2.5">
            {experimentCount === 0 ? (
              <p className="text-xs text-text-dim text-center py-6">
                No experiments logged. Executed training and ablation runs will be tracked here.
              </p>
            ) : (
              artifacts.experiments.map((exp, idx) => (
                <div key={idx} className="bg-surface-hover/40 border border-border/60 p-3 rounded-lg flex flex-col gap-1 font-mono text-xs">
                  <div className="flex items-center justify-between text-text font-semibold">
                    <span>{String(exp.id || exp.run_id || `Experiment #${idx + 1}`)}</span>
                    <span className="text-[10px] text-primary">{String(exp.status || 'logged')}</span>
                  </div>
                  <pre className="text-[11px] text-text-dim overflow-x-auto whitespace-pre-wrap">
                    {JSON.stringify(exp, null, 2)}
                  </pre>
                </div>
              ))
            )}
          </div>
        )}

        {activeTab === 'metrics' && (
          <div>
            {metricsCount === 0 ? (
              <p className="text-xs text-text-dim text-center py-6">
                No metrics updated yet. Training loss, evaluation scores, and FLOPs will appear here.
              </p>
            ) : (
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5">
                {Object.entries(artifacts.metrics).map(([key, val]) => (
                  <div key={key} className="bg-surface-hover/50 border border-border/60 p-2.5 rounded-lg flex flex-col">
                    <span className="text-[10px] uppercase font-bold tracking-wider text-text-dim truncate">
                      {key}
                    </span>
                    <span className="text-sm font-semibold text-primary font-mono mt-0.5">
                      {typeof val === 'number' ? val.toFixed(4) : String(val)}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {activeTab === 'manuscript' && (
          <div className="space-y-3">
            {sectionCount === 0 ? (
              <p className="text-xs text-text-dim text-center py-6">
                No manuscript sections drafted yet. Generated LaTeX paper sections will appear here.
              </p>
            ) : (
              Object.entries(artifacts.manuscript_sections).map(([secName, content]) => (
                <div key={secName} className="bg-surface-hover/40 border border-border/60 p-3 rounded-lg flex flex-col gap-1.5">
                  <span className="text-xs font-semibold text-primary capitalize flex items-center gap-1.5">
                    <FileText className="w-3.5 h-3.5" />
                    Section: {secName}
                  </span>
                  <pre className="text-[11px] text-text-dim bg-surface p-2.5 rounded-md border border-border/50 font-mono whitespace-pre-wrap max-h-40 overflow-y-auto scrollbar-thin">
                    {content}
                  </pre>
                </div>
              ))
            )}
          </div>
        )}

        {activeTab === 'bibtex' && (
          <div className="space-y-2">
            {bibtexCount === 0 ? (
              <p className="text-xs text-text-dim text-center py-6">
                No BibTeX entries registered yet. Referenced bibliographies will be recorded here.
              </p>
            ) : (
              artifacts.bibtex_entries.map((entry, idx) => (
                <pre
                  key={idx}
                  className="bg-surface-hover/40 border border-border/60 p-2.5 rounded-lg text-[11px] font-mono text-text-dim whitespace-pre-wrap overflow-x-auto"
                >
                  {entry}
                </pre>
              ))
            )}
          </div>
        )}
      </div>
    </div>
  );
}

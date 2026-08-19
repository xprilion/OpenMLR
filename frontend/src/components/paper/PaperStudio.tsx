import { useState, useCallback, useMemo } from 'react';
import {
  FileText,
  Columns,
  Eye,
  Edit3,
  GitCompare,
  Sparkles,
  Download,
  Copy,
  Check,
  BookOpen,
  Plus,
  Trash2,
} from 'lucide-react';
import { LatexPreview } from './LatexPreview';
import { BibtexManager } from './BibtexManager';
import { SectionDiffViewer } from './SectionDiffViewer';
import type { PaperMetadata, PaperSection, BibtexEntry, SectionDiff, PaperViewMode } from './types';

const INITIAL_METADATA: PaperMetadata = {
  title: 'Autonomous Multi-Agent Machine Learning Research Harness',
  authors: ['OpenMLR Research Team', 'Autonomous Agent Silas'],
  abstract:
    'We present OpenMLR, a unified autonomous machine learning research platform that orchestrates literature discovery, hypothesis formulation, distributed experiment execution, and automated LaTeX manuscript generation. Empirical evaluations demonstrate accelerated research velocity and reproducible experimental pipelines.',
  keywords: ['Autonomous Agents', 'Automated ML', 'Literature Reconnaissance', 'LaTeX Generation'],
  venue: 'ICLR 2027 Submission',
};

const INITIAL_SECTIONS: PaperSection[] = [
  {
    id: 'sec-intro',
    title: 'Introduction',
    level: 1,
    content:
      String.raw`Autonomous research agents hold great promise for democratizing scientific discovery. Traditional workflows require manual literature surveys, script debugging, and paper typesetting. In this paper, we propose a modular architecture utilizing reactive SSE streaming, asynchronous compute execution, and multi-agent peer review simulation \cite{vaswani2017attention}.`,
  },
  {
    id: 'sec-method',
    title: 'System Architecture & Methodology',
    level: 1,
    content:
      'The architecture comprises three primary sub-systems:\n\n1. **Reconnaissance Engine**: Graph-based citation crawling and vector search across arXiv and Semantic Scholar.\n2. **Execution Sandbox**: High-concurrency async compute nodes supporting Singularity and Modal containers.\n3. **LaTeX Studio**: Real-time split-pane authoring with automated BibTeX resolution.',
  },
  {
    id: 'sec-results',
    title: 'Experimental Evaluation',
    level: 1,
    content:
      'We evaluate our system across standard ML benchmarks. Table 1 summarizes throughput and reproduction accuracy.\n\n$$\\mathcal{L}_{total} = \\alpha \\mathcal{L}_{recon} + \\beta \\mathcal{L}_{exec} + \\gamma \\mathcal{L}_{draft}$$\n\nOur method achieves a 3.4x speedup in hypothesis validation while maintaining rigorous reproducibility.',
  },
  {
    id: 'sec-conclusion',
    title: 'Conclusion & Future Work',
    level: 1,
    content:
      'We demonstrated an end-to-end autonomous research harness. Future directions include reinforcement learning from AI peer review feedback and hardware-accelerated kernel search.',
  },
];

const INITIAL_BIBTEX: BibtexEntry[] = [
  {
    id: 'bib-1',
    citationKey: 'vaswani2017attention',
    entryType: 'article',
    title: 'Attention is All You Need',
    author: 'Vaswani, Ashish and Shazeer, Noam and Parmar, Niki and others',
    year: '2017',
    journal: 'Advances in Neural Information Processing Systems (NeurIPS)',
    raw: '@article{vaswani2017attention,\n  title={Attention is All You Need},\n  author={Vaswani, Ashish and others},\n  journal={NeurIPS},\n  year={2017}\n}',
  },
];

export function PaperStudio() {
  const [metadata, setMetadata] = useState<PaperMetadata>(INITIAL_METADATA);
  const [sections, setSections] = useState<PaperSection[]>(INITIAL_SECTIONS);
  const [bibtexEntries, setBibtexEntries] = useState<BibtexEntry[]>(INITIAL_BIBTEX);
  const [diffs, setDiffs] = useState<SectionDiff[]>([]);
  const [viewMode, setViewMode] = useState<PaperViewMode>('split');
  const [activeSectionId, setActiveSectionId] = useState<string>(INITIAL_SECTIONS[0].id);
  const [showBibtexDrawer, setShowBibtexDrawer] = useState(false);
  const [copiedTex, setCopiedTex] = useState(false);

  const activeSection = useMemo(
    () => sections.find((s) => s.id === activeSectionId) || sections[0],
    [sections, activeSectionId]
  );

  const handleUpdateSectionContent = useCallback((id: string, content: string) => {
    setSections((prev) => prev.map((s) => (s.id === id ? { ...s, content } : s)));
  }, []);

  const handleUpdateSectionTitle = useCallback((id: string, title: string) => {
    setSections((prev) => prev.map((s) => (s.id === id ? { ...s, title } : s)));
  }, []);

  const handleAddSection = useCallback(() => {
    const newSec: PaperSection = {
      id: `sec-${Date.now()}`,
      title: 'New Section',
      level: 1,
      content: 'Write your section content here in LaTeX or Markdown format.',
    };
    setSections((prev) => [...prev, newSec]);
    setActiveSectionId(newSec.id);
  }, []);

  const handleDeleteSection = useCallback((id: string) => {
    setSections((prev) => {
      if (prev.length <= 1) return prev;
      const next = prev.filter((s) => s.id !== id);
      setActiveSectionId(next[0].id);
      return next;
    });
  }, []);

  // AI Actions Mock Proposer
  const handleAiAction = useCallback(
    (actionType: 'expand' | 'polish' | 'cite' | 'abstract') => {
      if (!activeSection) return;

      if (actionType === 'expand') {
        const proposed = `${activeSection.content}\n\nFurthermore, theoretical convergence guarantees can be derived under standard Lipschitz continuity assumptions. Let $f: \\mathcal{X} \\to \\mathbb{R}$ represent the objective landscape.`;
        const newDiff: SectionDiff = {
          id: `diff-${Date.now()}`,
          sectionId: activeSection.id,
          sectionTitle: activeSection.title,
          originalText: activeSection.content,
          proposedText: proposed,
          reason: 'Expanded section with formal mathematical formulations and convergence details.',
          status: 'pending',
        };
        setDiffs((prev) => [newDiff, ...prev]);
        setViewMode('diff');
      } else if (actionType === 'polish') {
        const proposed = activeSection.content
          .replace(/We evaluate our system/g, 'We rigorously benchmark the proposed harness')
          .replace(/comprises three primary/g, 'is hierarchically partitioned into three core');
        const newDiff: SectionDiff = {
          id: `diff-${Date.now()}`,
          sectionId: activeSection.id,
          sectionTitle: activeSection.title,
          originalText: activeSection.content,
          proposedText: proposed,
          reason: 'Polished phrasing for high-impact academic publication standards.',
          status: 'pending',
        };
        setDiffs((prev) => [newDiff, ...prev]);
        setViewMode('diff');
      } else if (actionType === 'abstract') {
        setMetadata((prev) => ({
          ...prev,
          abstract: `Synthesized Overview: ${sections.map((s) => s.title).join(' -> ')}. This manuscript develops scalable autonomous methods for ML discovery.`,
        }));
      }
    },
    [activeSection, sections]
  );

  const handleApplyDiff = useCallback(
    (diffId: string) => {
      const diff = diffs.find((d) => d.id === diffId);
      if (diff) {
        setSections((prev) =>
          prev.map((s) => (s.id === diff.sectionId ? { ...s, content: diff.proposedText } : s))
        );
        setDiffs((prev) => prev.map((d) => (d.id === diffId ? { ...d, status: 'applied' } : d)));
        setViewMode('split');
      }
    },
    [diffs]
  );

  const handleRejectDiff = useCallback((diffId: string) => {
    setDiffs((prev) => prev.map((d) => (d.id === diffId ? { ...d, status: 'rejected' } : d)));
  }, []);

  const generateFullLatex = useCallback(() => {
    const docHeader = String.raw`\documentclass[11pt,a4paper]{article}
\usepackage{amsmath,amssymb,amsfonts}
\usepackage{graphicx}
\usepackage{hyperref}`;

    const andSep = String.raw`\and`;
    const titleBlock = String.raw`\title{` + metadata.title + String.raw`}
\author{` + metadata.authors.join(` ${andSep} `) + String.raw`}
\date{\today}`;

    const bodySections = sections
      .map((s) => String.raw`\section{` + s.title + '}\n' + s.content)
      .join('\n\n');

    return `${docHeader}

${titleBlock}

` + String.raw`\begin{document}
\maketitle

\begin{abstract}
` + metadata.abstract + String.raw`
\end{abstract}

` + `${bodySections}

` + String.raw`\bibliographystyle{plain}
\bibliography{references}

\end{document}`;
  }, [metadata, sections]);

  const handleCopyLatex = useCallback(async () => {
    const tex = generateFullLatex();
    try {
      if (typeof navigator !== 'undefined' && navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(tex);
      }
      setCopiedTex(true);
      setTimeout(() => setCopiedTex(false), 2000);
    } catch {
      /* ignore */
    }
  }, [generateFullLatex]);

  const handleDownloadTex = useCallback(() => {
    const tex = generateFullLatex();
    const blob = new Blob([tex], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'paper.tex';
    link.click();
    URL.revokeObjectURL(url);
  }, [generateFullLatex]);

  return (
    <div className="flex flex-col flex-1 h-full overflow-hidden bg-bg">
      {/* Top Studio Toolbar */}
      <header className="flex items-center justify-between px-4 sm:px-6 h-13 bg-surface border-b border-border shrink-0 gap-3">
        <div className="flex items-center gap-2 min-w-0">
          <FileText size={18} className="text-primary shrink-0" />
          <input
            type="text"
            className="bg-transparent text-sm font-semibold text-text border-none focus:outline-none focus:ring-1 focus:ring-primary/40 rounded px-1.5 py-0.5 truncate max-w-xs sm:max-w-md"
            value={metadata.title}
            onChange={(e) => setMetadata((m) => ({ ...m, title: e.target.value }))}
            placeholder="Paper Title"
          />
        </div>

        {/* View Mode Controls */}
        <div className="flex items-center gap-1 bg-bg border border-border rounded-lg p-0.5">
          <button
            type="button"
            className={`flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium rounded-md transition-colors ${
              viewMode === 'split' ? 'bg-surface text-primary shadow-xs' : 'text-text-dim hover:text-text'
            }`}
            onClick={() => setViewMode('split')}
            title="Split Editor & Preview"
          >
            <Columns size={14} />
            <span className="hidden sm:inline">Split</span>
          </button>
          <button
            type="button"
            className={`flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium rounded-md transition-colors ${
              viewMode === 'editor' ? 'bg-surface text-primary shadow-xs' : 'text-text-dim hover:text-text'
            }`}
            onClick={() => setViewMode('editor')}
            title="Editor Only"
          >
            <Edit3 size={14} />
            <span className="hidden sm:inline">Editor</span>
          </button>
          <button
            type="button"
            className={`flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium rounded-md transition-colors ${
              viewMode === 'preview' ? 'bg-surface text-primary shadow-xs' : 'text-text-dim hover:text-text'
            }`}
            onClick={() => setViewMode('preview')}
            title="Live Manuscript Preview"
          >
            <Eye size={14} />
            <span className="hidden sm:inline">Preview</span>
          </button>
          <button
            type="button"
            className={`flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium rounded-md transition-colors ${
              viewMode === 'diff' ? 'bg-surface text-primary shadow-xs' : 'text-text-dim hover:text-text'
            }`}
            onClick={() => setViewMode('diff')}
            title="Review AI Proposals"
          >
            <GitCompare size={14} />
            <span className="hidden sm:inline">Diff</span>
            {diffs.some((d) => d.status === 'pending') && (
              <span className="w-1.5 h-1.5 rounded-full bg-primary" />
            )}
          </button>
        </div>

        {/* AI & Export Actions */}
        <div className="flex items-center gap-1.5">
          <button
            type="button"
            className="flex items-center gap-1 text-xs bg-surface border border-border text-text-dim hover:text-text hover:bg-surface-hover px-2.5 py-1.5 rounded-lg transition-colors"
            onClick={() => handleAiAction('expand')}
            title="AI Expand Section"
          >
            <Sparkles size={14} className="text-primary" />
            <span className="hidden md:inline">AI Expand</span>
          </button>
          <button
            type="button"
            className={`flex items-center gap-1 text-xs px-2.5 py-1.5 rounded-lg border transition-colors ${
              showBibtexDrawer
                ? 'bg-primary/10 border-primary text-primary'
                : 'bg-surface border-border text-text-dim hover:text-text hover:bg-surface-hover'
            }`}
            onClick={() => setShowBibtexDrawer((v) => !v)}
            title="Toggle BibTeX Manager"
          >
            <BookOpen size={14} />
            <span className="hidden md:inline">BibTeX</span>
          </button>
          <button
            type="button"
            className="p-1.5 text-text-dim hover:text-text hover:bg-surface-hover rounded-lg transition-colors border border-border"
            onClick={handleCopyLatex}
            title="Copy LaTeX source"
          >
            {copiedTex ? <Check size={16} className="text-success" /> : <Copy size={16} />}
          </button>
          <button
            type="button"
            className="flex items-center gap-1 text-xs bg-primary text-white font-medium px-2.5 py-1.5 rounded-lg hover:bg-primary-hover transition-colors"
            onClick={handleDownloadTex}
            title="Export .tex source"
          >
            <Download size={14} />
            <span className="hidden sm:inline">Export</span>
          </button>
        </div>
      </header>

      {/* Main Workspace Layout */}
      <div className="flex flex-1 overflow-hidden relative">
        {/* Section Navigation Sidebar */}
        <aside className="w-52 bg-surface border-r border-border flex flex-col shrink-0 hidden md:flex">
          <div className="p-3 border-b border-border flex items-center justify-between">
            <span className="text-xs font-semibold text-text-dim uppercase tracking-wider">Sections</span>
            <button
              type="button"
              className="p-1 rounded text-text-dim hover:text-text hover:bg-surface-hover transition-colors"
              onClick={handleAddSection}
              title="Add section"
            >
              <Plus size={14} />
            </button>
          </div>
          <nav className="flex-1 overflow-y-auto p-2 flex flex-col gap-1">
            {sections.map((sec, idx) => (
              <button
                type="button"
                key={sec.id}
                className={`flex items-center justify-between px-2.5 py-1.5 rounded-lg text-xs font-medium text-left transition-colors group ${
                  activeSectionId === sec.id
                    ? 'bg-primary/10 text-primary'
                    : 'text-text-dim hover:text-text hover:bg-surface-hover'
                }`}
                onClick={() => setActiveSectionId(sec.id)}
              >
                <span className="truncate">
                  {idx + 1}. {sec.title}
                </span>
                {sections.length > 1 && (
                  <button
                    type="button"
                    className="opacity-0 group-hover:opacity-100 p-0.5 text-text-dim hover:text-error transition-opacity"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDeleteSection(sec.id);
                    }}
                    title="Delete section"
                  >
                    <Trash2 size={12} />
                  </button>
                )}
              </button>
            ))}
          </nav>
        </aside>

        {/* Center Workspace */}
        <div className="flex flex-1 overflow-hidden">
          {viewMode === 'diff' ? (
            <SectionDiffViewer
              diffs={diffs}
              onApplyDiff={handleApplyDiff}
              onRejectDiff={handleRejectDiff}
            />
          ) : (
            <>
              {/* Left: Editor Pane */}
              {(viewMode === 'split' || viewMode === 'editor') && activeSection && (
                <div className="flex-1 flex flex-col border-r border-border bg-bg min-w-[320px]">
                  <div className="p-3 border-b border-border bg-surface flex items-center gap-2 shrink-0">
                    <span className="text-xs font-mono text-primary font-semibold">Section:</span>
                    <input
                      type="text"
                      className="bg-transparent text-xs font-semibold text-text border-none focus:outline-none focus:ring-1 focus:ring-primary/40 rounded px-1 py-0.5 flex-1"
                      value={activeSection.title}
                      onChange={(e) => handleUpdateSectionTitle(activeSection.id, e.target.value)}
                    />
                  </div>
                  <textarea
                    className="flex-1 p-4 bg-bg text-text font-mono text-xs leading-relaxed focus:outline-none resize-none border-none"
                    value={activeSection.content}
                    onChange={(e) => handleUpdateSectionContent(activeSection.id, e.target.value)}
                    placeholder="Write section body in LaTeX / Markdown..."
                  />
                </div>
              )}

              {/* Right: Live Manuscript Preview */}
              {(viewMode === 'split' || viewMode === 'preview') && (
                <div className="flex-1 flex flex-col bg-surface min-w-[340px]">
                  <LatexPreview
                    metadata={metadata}
                    sections={sections}
                    bibtexEntries={bibtexEntries}
                  />
                </div>
              )}
            </>
          )}
        </div>

        {/* Right Drawer: BibTeX Manager */}
        {showBibtexDrawer && (
          <div className="w-80 border-l border-border bg-surface shrink-0 animate-in slide-in-from-right duration-200">
            <BibtexManager
              entries={bibtexEntries}
              onAddEntry={(newEntry) => setBibtexEntries((prev) => [newEntry, ...prev])}
              onDeleteEntry={(id) => setBibtexEntries((prev) => prev.filter((b) => b.id !== id))}
              onInsertCite={(key) => {
                if (activeSection) {
                  const citeCode = String.raw`\cite{${key}}`;
                  handleUpdateSectionContent(activeSection.id, `${activeSection.content} ${citeCode}`);
                }
              }}
            />
          </div>
        )}
      </div>
    </div>
  );
}

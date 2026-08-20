import { useState, useEffect, useCallback } from 'react';
import { 
  Award, 
  Play, 
  FileText, 
  Download, 
  RotateCcw, 
  Sliders, 
  Sparkles,
  AlertCircle,
  FolderOpen
} from 'lucide-react';
import { api } from '../../api';
import { useProject } from '../../context/ProjectContext';
import type { PeerReviewResult, ConferenceRubric, ReviewerPersona } from '../../types';
import { ReviewerCard } from './ReviewerCard';
import { MetaReviewSummary } from './MetaReviewSummary';
import { RubricViewerModal } from './RubricViewerModal';

const SAMPLE_PAPER = `\\documentclass{article}
\\title{Adaptive Low-Rank Attention for Large Language Model Fine-Tuning}
\\begin{document}
\\maketitle

\\begin{abstract}
Parameter-efficient fine-tuning (PEFT) methods such as LoRA significantly reduce memory overhead during large model adaptation. However, uniform rank allocation across attention heads leads to suboptimal representation capacity. We propose AdaLoRA-Dynamo, an adaptive singular value pruning approach that dynamically allocates rank budgets based on gradient magnitude and curvature. Extensive experiments on Llama-3-8B demonstrate 1.4x faster convergence and a 2.3% accuracy improvement on GSM8K and MMLU benchmarks with 40% fewer trainable parameters.
\\end{abstract}

\\section{Introduction}
As foundational models grow in scale, adapting them to specialized domains requires efficient parameter updates. Standard LoRA decomposes weight matrices into low-rank representations. However, empirical analyses reveal that earlier transformer layers require significantly lower rank capacity than mid-to-deep reasoning layers.

\\section{Methodology}
We formulate rank allocation as a dynamic budget optimization problem. Given weight matrix $W \\in \\mathbb{R}^{d \\times k}$, we decompose updates into $W = W_0 + \\Delta W$, where $\\Delta W = P \\Lambda Q^T$. The diagonal matrix $\\Lambda$ is pruned at regular intervals during training according to importance metric $S_i$:
$$S_i = |\\Lambda_i| \\cdot \\|\\nabla_{\\Lambda_i} \\mathcal{L}\\|_2$$

\\section{Empirical Results}
We evaluate on GSM8K, ARC-Challenge, and HumanEval using Llama-3-8B. Table 1 shows that our dynamic allocation achieves 78.4% on GSM8K compared to 76.1% for standard LoRA and 76.8% for DoRA, while reducing parameter memory from 160MB to 96MB.

\\section{Conclusion}
Dynamic low-rank adaptation resolves parameter imbalance in PEFT workflows. Future work includes extending to multi-modal vision-language architectures.
\\end{document}`;

const VENUES = [
  { id: 'iclr', name: 'ICLR', desc: 'International Conference on Learning Representations' },
  { id: 'neurips', name: 'NeurIPS', desc: 'Neural Information Processing Systems' },
  { id: 'icml', name: 'ICML', desc: 'International Conference on Machine Learning' },
  { id: 'cvpr', name: 'CVPR', desc: 'Computer Vision and Pattern Recognition' },
  { id: 'acl', name: 'ACL', desc: 'Association for Computational Linguistics' },
  { id: 'general', name: 'General ML', desc: 'Standard Machine Learning Rigor Rubric' },
];

export function PeerReviewStudio() {
  const { activeProject } = useProject();
  const [venue, setVenue] = useState('iclr');
  const [title, setTitle] = useState('Adaptive Low-Rank Attention for Large Language Model Fine-Tuning');
  const [submissionText, setSubmissionText] = useState(SAMPLE_PAPER);
  const [loading, setLoading] = useState(false);
  const [deliberationStep, setDeliberationStep] = useState<string | null>(null);
  const [result, setResult] = useState<PeerReviewResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [rubrics, setRubrics] = useState<Record<string, ConferenceRubric>>({});
  const [personas, setPersonas] = useState<ReviewerPersona[]>([]);
  const [showRubricModal, setShowRubricModal] = useState(false);

  useEffect(() => {
    api.getReviewRubrics()
      .then((data) => {
        if (data?.rubrics) setRubrics(data.rubrics);
        if (data?.personas) setPersonas(data.personas);
      })
      .catch(() => {});
  }, []);

  const handleRunReview = async () => {
    if (!submissionText.trim()) {
      setError('Please provide manuscript text or LaTeX code to review.');
      return;
    }
    setError(null);
    setLoading(true);
    setDeliberationStep('Convening Reviewer 1 (Theory & Novelty)...');

    const stepTimers = [
      setTimeout(() => setDeliberationStep('Reviewer 2 evaluating Empirical Validation & Baselines...'), 1200),
      setTimeout(() => setDeliberationStep('Reviewer 3 checking Clarity, Reproducibility & Code...'), 2400),
      setTimeout(() => setDeliberationStep('Meta-Reviewer consolidating committee consensus...'), 3600),
    ];

    try {
      const data = await api.evaluateSubmission({
        submission_text: submissionText,
        venue,
        title: title || 'Autonomous Submission',
      });
      setResult(data);
    } catch (err: unknown) {
      const errMsg = err instanceof Error ? err.message : 'Peer review simulation failed.';
      setError(errMsg);
    } finally {
      stepTimers.forEach(clearTimeout);
      setLoading(false);
      setDeliberationStep(null);
    }
  };

  const handleProjectWorkspaceReview = async () => {
    if (!activeProject) return;
    setError(null);
    setLoading(true);
    setDeliberationStep('Scanning project workspace LaTeX and research notes...');

    try {
      const data = await api.reviewProjectWorkspace(activeProject.id, {
        venue,
        include_latex: true,
        include_notes: true,
      });
      setResult(data);
      if (data.submission_title) setTitle(data.submission_title);
    } catch (err: unknown) {
      const errMsg = err instanceof Error ? err.message : 'Project review failed.';
      setError(errMsg);
    } finally {
      setLoading(false);
      setDeliberationStep(null);
    }
  };

  const handleExportMarkdown = useCallback(() => {
    if (!result) return;
    const content = result.markdown_report || JSON.stringify(result, null, 2);
    const blob = new Blob([content], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `peer_review_${venue}_${Date.now()}.md`;
    a.click();
    URL.revokeObjectURL(url);
  }, [result, venue]);

  return (
    <div className="flex flex-col flex-1 h-full overflow-y-auto bg-bg text-text p-4 sm:p-6 space-y-6">
      {/* Top Banner & Venue Bar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-surface border border-border rounded-2xl p-5 shadow-sm">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-primary/10 border border-primary/20 flex items-center justify-center text-primary">
            <Award size={22} />
          </div>
          <div>
            <h2 className="text-base sm:text-lg font-bold text-text flex items-center gap-2">
              Autonomous Peer Review Committee
            </h2>
            <p className="text-xs text-text-dim">
              Simulate 3 independent reviewer subagents & 1 meta-reviewer with conference scoring rubrics
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2.5 flex-wrap">
          {/* Venue select */}
          <div className="flex items-center gap-2 bg-bg border border-border rounded-xl px-3 py-1.5">
            <span className="text-xs text-text-dim font-medium">Venue:</span>
            <select
              value={venue}
              onChange={(e) => setVenue(e.target.value)}
              className="bg-transparent text-xs font-semibold text-text focus:outline-none cursor-pointer"
            >
              {VENUES.map((v) => (
                <option key={v.id} value={v.id} className="bg-surface text-text">
                  {v.name} ({v.desc})
                </option>
              ))}
            </select>
          </div>

          <button
            type="button"
            onClick={() => setShowRubricModal(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-surface-hover hover:bg-border border border-border text-xs font-medium text-text-dim hover:text-text transition-colors"
          >
            <Sliders size={14} />
            <span>Rubric</span>
          </button>
        </div>
      </div>

      {/* Editor & Control Section */}
      <div className="bg-surface border border-border rounded-2xl p-5 shadow-sm space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex-1 min-w-0">
            <label className="block text-xs font-semibold text-text-dim mb-1">Submission Title</label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Scalable FlashAttention with Adaptive Sparse Masking"
              className="w-full bg-bg border border-border rounded-xl px-3.5 py-2 text-xs text-text focus:border-primary focus:outline-none transition-colors"
            />
          </div>

          <div className="flex items-center gap-2 self-end sm:self-auto pt-4 sm:pt-0">
            {activeProject && (
              <button
                type="button"
                onClick={handleProjectWorkspaceReview}
                disabled={loading}
                className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-surface-hover hover:bg-border border border-border text-xs font-medium text-text-dim hover:text-text transition-colors disabled:opacity-50"
                title="Review current active project workspace drafts"
              >
                <FolderOpen size={14} />
                <span>Review Workspace</span>
              </button>
            )}

            <button
              type="button"
              onClick={handleRunReview}
              disabled={loading || !submissionText.trim()}
              className="flex items-center gap-2 px-4 py-2 rounded-xl bg-primary hover:bg-primary/90 text-white text-xs font-bold shadow-md hover:shadow-primary/20 transition-all disabled:opacity-50"
            >
              {loading ? (
                <>
                  <RotateCcw size={14} className="animate-spin" />
                  <span>Reviewing...</span>
                </>
              ) : (
                <>
                  <Play size={14} />
                  <span>Run Peer Review</span>
                </>
              )}
            </button>
          </div>
        </div>

        {/* Text Area */}
        <div>
          <div className="flex items-center justify-between mb-1">
            <label className="text-xs font-semibold text-text-dim flex items-center gap-1.5">
              <FileText size={14} />
              Manuscript Draft / LaTeX Source / Abstract
            </label>
            <span className="text-[11px] text-text-dim font-mono">
              {submissionText.length.toLocaleString()} characters
            </span>
          </div>
          <textarea
            rows={8}
            value={submissionText}
            onChange={(e) => setSubmissionText(e.target.value)}
            placeholder="Paste your full paper LaTeX source, Markdown draft, or research proposal here..."
            className="w-full bg-bg border border-border rounded-xl p-3.5 text-xs text-text font-mono focus:border-primary focus:outline-none leading-relaxed transition-colors resize-y"
          />
        </div>
      </div>

      {/* Loading Deliberations Status */}
      {loading && (
        <div className="bg-surface/80 border border-primary/30 rounded-2xl p-6 shadow-md flex flex-col items-center justify-center text-center space-y-3 animate-pulse">
          <div className="w-10 h-10 rounded-full border-2 border-primary border-t-transparent animate-spin" />
          <div className="text-sm font-semibold text-text">{deliberationStep || 'Simulating Peer Review Committee...'}</div>
          <p className="text-xs text-text-dim max-w-md">
            The subagents are reviewing your submission against {venue.toUpperCase()} conference standards for theoretical rigor, empirical baselines, and reproducibility.
          </p>
        </div>
      )}

      {/* Error Message */}
      {error && (
        <div className="bg-rose-500/10 border border-rose-500/30 rounded-xl p-4 flex items-center gap-3 text-xs text-rose-400">
          <AlertCircle size={18} className="shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Review Results Section */}
      {result && (
        <div className="space-y-6 animate-in fade-in duration-300">
          {/* Action bar for results */}
          <div className="flex items-center justify-between">
            <h3 className="text-base font-bold text-text flex items-center gap-2">
              <Sparkles size={16} className="text-primary" />
              Committee Evaluation Report ({result.venue.toUpperCase()})
            </h3>
            <button
              type="button"
              onClick={handleExportMarkdown}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-surface hover:bg-surface-hover border border-border text-xs font-medium text-text-dim hover:text-text transition-colors"
            >
              <Download size={14} />
              <span>Export Report (MD)</span>
            </button>
          </div>

          {/* Meta Review Consensus Summary */}
          {result.meta_review && (
            <MetaReviewSummary
              metaReview={result.meta_review}
              averageScore={result.average_score}
              venue={result.venue}
            />
          )}

          {/* Individual Reviewer Cards */}
          <div className="space-y-4">
            <h4 className="text-sm font-bold text-text flex items-center gap-2">
              Individual Subagent Reviews ({result.reviews.length})
            </h4>
            <div className="space-y-4">
              {result.reviews.map((rev, idx) => (
                <ReviewerCard key={rev.reviewer_id || `rev-${idx}`} review={rev} index={idx} />
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Rubric Details Modal */}
      {showRubricModal && (
        <RubricViewerModal
          venue={venue}
          rubrics={rubrics}
          personas={personas}
          onClose={() => setShowRubricModal(false)}
        />
      )}
    </div>
  );
}

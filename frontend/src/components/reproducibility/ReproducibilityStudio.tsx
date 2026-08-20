import { useState, useEffect, useCallback } from 'react';
import {
  ShieldCheck,
  Search,
  FileCode,
  Layers,
  Copy,
  Check,
  Download,
  Terminal,
  FileText,
  Sparkles,
  Loader2,
} from 'lucide-react';
import { api } from '../../api';
import { useProject } from '../../context/ProjectContext';
import { ScoreGauge } from './ScoreGauge';
import { ChecklistTable } from './ChecklistTable';
import { AuditModal } from './AuditModal';
import type { ReproducibilityAuditReport, AuditCodebaseRequest } from './types';

type StudioTab = 'checklist' | 'appendix' | 'dockerfile' | 'conda' | 'determinism';

export function ReproducibilityStudio() {
  const { activeProject } = useProject();
  const [reports, setReports] = useState<ReproducibilityAuditReport[]>([]);
  const [activeReport, setActiveReport] = useState<ReproducibilityAuditReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [auditing, setAuditing] = useState(false);
  const [activeTab, setActiveTab] = useState<StudioTab>('checklist');
  const [showAuditModal, setShowAuditModal] = useState(false);
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

  // Determinism snippet generator state
  const [targetFramework, setTargetFramework] = useState('pytorch');
  const [targetSeed, setTargetSeed] = useState(42);
  const [determinismSnippet, setDeterminismSnippet] = useState('');

  const loadReports = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.listReproducibilityReports(activeProject?.uuid);
      if (Array.isArray(res) && res.length > 0) {
        setReports(res);
        setActiveReport(res[0]);
      } else {
        // If no reports exist yet, run a default baseline audit
        const defaultReport = await api.runReproducibilityAudit(activeProject?.uuid, {
          target_path: '.',
          venue: 'neurips',
        });
        if (defaultReport && typeof defaultReport === 'object' && 'id' in defaultReport) {
          setReports([defaultReport as ReproducibilityAuditReport]);
          setActiveReport(defaultReport as ReproducibilityAuditReport);
        }
      }
    } catch {
      // Fallback
    } finally {
      setLoading(false);
    }
  }, [activeProject?.uuid]);

  useEffect(() => {
    loadReports();
  }, [loadReports]);

  const loadDeterminismSnippet = useCallback(async () => {
    try {
      const res = (await api.getDeterminismFix({
        framework: targetFramework,
        seed: targetSeed,
        strict_mode: true,
      })) as { determinism_snippet?: string };
      if (res?.determinism_snippet) {
        setDeterminismSnippet(res.determinism_snippet);
      }
    } catch {
      // ignore
    }
  }, [targetFramework, targetSeed]);

  useEffect(() => {
    if (activeTab === 'determinism') {
      loadDeterminismSnippet();
    }
  }, [activeTab, loadDeterminismSnippet]);

  const handleRunAudit = async (req: AuditCodebaseRequest) => {
    setAuditing(true);
    setShowAuditModal(false);
    try {
      const res = (await api.runReproducibilityAudit(
        activeProject?.uuid,
        req
      )) as ReproducibilityAuditReport;
      if (res && res.id) {
        setReports((prev) => [res, ...prev]);
        setActiveReport(res);
      }
    } catch {
      // error handled
    } finally {
      setAuditing(false);
    }
  };

  const handleCopy = (key: string, text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedKey(key);
    setTimeout(() => setCopiedKey(null), 2000);
  };

  const handleDownloadFile = (filename: string, content: string) => {
    const blob = new Blob([content], { type: 'text/plain;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    link.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="flex flex-col h-full bg-bg overflow-hidden select-text">
      {/* Header Bar */}
      <div className="p-4 bg-surface border-b border-border flex flex-wrap items-center justify-between gap-3 shrink-0">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-primary/10 border border-primary/20 text-primary">
            <ShieldCheck className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-base font-bold text-text">Reproducibility Studio</h1>
              <span className="text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                Conference Certified
              </span>
            </div>
            <p className="text-xs text-text-dim">
              Automated scientific artifact verification, determinism auditing, and NeurIPS / ICML checklist generator
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {reports.length > 1 && (
            <select
              aria-label="Select reproducibility report"
              value={activeReport?.id || ''}
              onChange={(e) => {
                const found = reports.find((r) => r.id === e.target.value);
                if (found) setActiveReport(found);
              }}
              className="bg-bg border border-border rounded-lg px-2.5 py-1.5 text-xs text-text focus:outline-none focus:border-primary"
            >
              {reports.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.venue.toUpperCase()} — Grade {r.grade} ({r.overall_score}%)
                </option>
              ))}
            </select>
          )}
          <button
            type="button"
            onClick={() => setShowAuditModal(true)}
            disabled={auditing}
            className="px-3.5 py-1.5 text-xs font-semibold rounded-lg bg-primary hover:bg-primary/90 text-white transition-colors flex items-center gap-1.5 disabled:opacity-50"
          >
            {auditing ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <Search className="w-3.5 h-3.5" />
            )}
            <span>{auditing ? 'Auditing Codebase...' : 'Audit Codebase'}</span>
          </button>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 overflow-y-auto p-4 md:p-6 flex flex-col gap-6 max-w-7xl mx-auto w-full">
        {loading ? (
          <div className="py-20 flex flex-col items-center justify-center gap-3 text-text-dim">
            <Loader2 className="w-8 h-8 animate-spin text-primary" />
            <span className="text-xs">Analyzing codebase artifacts...</span>
          </div>
        ) : !activeReport ? (
          <div className="py-20 text-center text-xs text-text-dim">
            No reproducibility reports found. Click &quot;Audit Codebase&quot; to run your first evaluation.
          </div>
        ) : (
          <>
            {/* Top Score Gauge & Overview */}
            <ScoreGauge
              score={activeReport.overall_score}
              grade={activeReport.grade}
              venue={activeReport.venue}
              categories={activeReport.categories}
            />

            {/* Studio Navigation Tabs */}
            <div className="flex items-center gap-2 border-b border-border pb-1">
              <button
                type="button"
                onClick={() => setActiveTab('checklist')}
                className={`px-3 py-1.5 text-xs font-medium rounded-t-lg transition-colors flex items-center gap-1.5 ${
                  activeTab === 'checklist'
                    ? 'text-primary border-b-2 border-primary font-semibold'
                    : 'text-text-dim hover:text-text'
                }`}
              >
                <ShieldCheck className="w-3.5 h-3.5" />
                <span>Conference Checklist</span>
                <span className="text-[10px] px-1.5 rounded-full bg-surface border border-border">
                  {activeReport.checklist.length}
                </span>
              </button>

              <button
                type="button"
                onClick={() => setActiveTab('appendix')}
                className={`px-3 py-1.5 text-xs font-medium rounded-t-lg transition-colors flex items-center gap-1.5 ${
                  activeTab === 'appendix'
                    ? 'text-primary border-b-2 border-primary font-semibold'
                    : 'text-text-dim hover:text-text'
                }`}
              >
                <FileText className="w-3.5 h-3.5" />
                <span>LaTeX Reproducibility Statement</span>
              </button>

              <button
                type="button"
                onClick={() => setActiveTab('dockerfile')}
                className={`px-3 py-1.5 text-xs font-medium rounded-t-lg transition-colors flex items-center gap-1.5 ${
                  activeTab === 'dockerfile'
                    ? 'text-primary border-b-2 border-primary font-semibold'
                    : 'text-text-dim hover:text-text'
                }`}
              >
                <Layers className="w-3.5 h-3.5" />
                <span>Dockerfile Recipe</span>
              </button>

              <button
                type="button"
                onClick={() => setActiveTab('conda')}
                className={`px-3 py-1.5 text-xs font-medium rounded-t-lg transition-colors flex items-center gap-1.5 ${
                  activeTab === 'conda'
                    ? 'text-primary border-b-2 border-primary font-semibold'
                    : 'text-text-dim hover:text-text'
                }`}
              >
                <FileCode className="w-3.5 h-3.5" />
                <span>environment.yml</span>
              </button>

              <button
                type="button"
                onClick={() => setActiveTab('determinism')}
                className={`px-3 py-1.5 text-xs font-medium rounded-t-lg transition-colors flex items-center gap-1.5 ${
                  activeTab === 'determinism'
                    ? 'text-primary border-b-2 border-primary font-semibold'
                    : 'text-text-dim hover:text-text'
                }`}
              >
                <Terminal className="w-3.5 h-3.5" />
                <span>Determinism Boilerplate</span>
              </button>
            </div>

            {/* Tab Views */}
            {activeTab === 'checklist' && (
              <ChecklistTable items={activeReport.checklist} />
            )}

            {activeTab === 'appendix' && (
              <div className="bg-surface border border-border rounded-xl p-4 flex flex-col gap-3 shadow-sm">
                <div className="flex items-center justify-between border-b border-border pb-2">
                  <div>
                    <h3 className="text-sm font-semibold text-text">LaTeX Reproducibility Appendix Section</h3>
                    <p className="text-xs text-text-dim">
                      Ready to insert directly into your Overleaf or LaTeX submission manuscript
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={() => handleCopy('appendix', activeReport.latex_appendix)}
                      className="px-3 py-1.5 text-xs font-medium rounded-md bg-surface-hover hover:bg-border text-text transition-colors flex items-center gap-1.5"
                    >
                      {copiedKey === 'appendix' ? (
                        <>
                          <Check className="w-3.5 h-3.5 text-emerald-400" />
                          <span className="text-emerald-400">Copied</span>
                        </>
                      ) : (
                        <>
                          <Copy className="w-3.5 h-3.5" />
                          <span>Copy LaTeX</span>
                        </>
                      )}
                    </button>
                  </div>
                </div>
                <pre className="p-4 bg-bg border border-border rounded-lg text-xs font-mono text-text overflow-x-auto whitespace-pre-wrap leading-relaxed">
                  {activeReport.latex_appendix}
                </pre>
              </div>
            )}

            {activeTab === 'dockerfile' && (
              <div className="bg-surface border border-border rounded-xl p-4 flex flex-col gap-3 shadow-sm">
                <div className="flex items-center justify-between border-b border-border pb-2">
                  <div>
                    <h3 className="text-sm font-semibold text-text">Standalone Reproducible Dockerfile</h3>
                    <p className="text-xs text-text-dim">
                      CUDA-accelerated container image with pinned Python environment and deterministic variables
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={() => handleCopy('dockerfile', activeReport.dockerfile_recipe)}
                      className="px-3 py-1.5 text-xs font-medium rounded-md bg-surface-hover hover:bg-border text-text transition-colors flex items-center gap-1.5"
                    >
                      {copiedKey === 'dockerfile' ? (
                        <>
                          <Check className="w-3.5 h-3.5 text-emerald-400" />
                          <span className="text-emerald-400">Copied</span>
                        </>
                      ) : (
                        <>
                          <Copy className="w-3.5 h-3.5" />
                          <span>Copy</span>
                        </>
                      )}
                    </button>
                    <button
                      type="button"
                      onClick={() => handleDownloadFile('Dockerfile', activeReport.dockerfile_recipe)}
                      className="px-3 py-1.5 text-xs font-medium rounded-md bg-primary hover:bg-primary/90 text-white transition-colors flex items-center gap-1.5"
                    >
                      <Download className="w-3.5 h-3.5" />
                      <span>Download Dockerfile</span>
                    </button>
                  </div>
                </div>
                <pre className="p-4 bg-bg border border-border rounded-lg text-xs font-mono text-text overflow-x-auto whitespace-pre-wrap leading-relaxed">
                  {activeReport.dockerfile_recipe}
                </pre>
              </div>
            )}

            {activeTab === 'conda' && (
              <div className="bg-surface border border-border rounded-xl p-4 flex flex-col gap-3 shadow-sm">
                <div className="flex items-center justify-between border-b border-border pb-2">
                  <div>
                    <h3 className="text-sm font-semibold text-text">Conda Environment Definition</h3>
                    <p className="text-xs text-text-dim">
                      Reproduce local Conda or Mamba environments with exact CUDA toolkit channels
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={() => handleCopy('conda', activeReport.conda_recipe)}
                      className="px-3 py-1.5 text-xs font-medium rounded-md bg-surface-hover hover:bg-border text-text transition-colors flex items-center gap-1.5"
                    >
                      {copiedKey === 'conda' ? (
                        <>
                          <Check className="w-3.5 h-3.5 text-emerald-400" />
                          <span className="text-emerald-400">Copied</span>
                        </>
                      ) : (
                        <>
                          <Copy className="w-3.5 h-3.5" />
                          <span>Copy</span>
                        </>
                      )}
                    </button>
                    <button
                      type="button"
                      onClick={() => handleDownloadFile('environment.yml', activeReport.conda_recipe)}
                      className="px-3 py-1.5 text-xs font-medium rounded-md bg-primary hover:bg-primary/90 text-white transition-colors flex items-center gap-1.5"
                    >
                      <Download className="w-3.5 h-3.5" />
                      <span>Download YAML</span>
                    </button>
                  </div>
                </div>
                <pre className="p-4 bg-bg border border-border rounded-lg text-xs font-mono text-text overflow-x-auto whitespace-pre-wrap leading-relaxed">
                  {activeReport.conda_recipe}
                </pre>
              </div>
            )}

            {activeTab === 'determinism' && (
              <div className="bg-surface border border-border rounded-xl p-4 flex flex-col gap-4 shadow-sm">
                <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border pb-3">
                  <div>
                    <h3 className="text-sm font-semibold text-text">Deterministic Execution Generator</h3>
                    <p className="text-xs text-text-dim">
                      Inject deterministic RNG seeds, cuDNN flags, and CUDA workspace settings into training loops
                    </p>
                  </div>
                  <div className="flex items-center gap-3">
                    <div className="flex items-center gap-2">
                      <label htmlFor="det-framework-select" className="text-xs text-text-dim font-medium">Framework:</label>
                      <select
                        id="det-framework-select"
                        value={targetFramework}
                        onChange={(e) => setTargetFramework(e.target.value)}
                        className="bg-bg border border-border rounded-md px-2.5 py-1 text-xs text-text focus:outline-none focus:border-primary"
                      >
                        <option value="pytorch">PyTorch</option>
                        <option value="jax">JAX</option>
                        <option value="tensorflow">TensorFlow</option>
                      </select>
                    </div>

                    <div className="flex items-center gap-2">
                      <label htmlFor="det-seed-input" className="text-xs text-text-dim font-medium">Seed:</label>
                      <input
                        id="det-seed-input"
                        type="number"
                        value={targetSeed}
                        onChange={(e) => setTargetSeed(Number(e.target.value))}
                        className="w-20 bg-bg border border-border rounded-md px-2.5 py-1 text-xs text-text focus:outline-none focus:border-primary font-mono"
                      />
                    </div>

                    <button
                      type="button"
                      onClick={() => handleCopy('determinism', determinismSnippet)}
                      className="px-3 py-1 text-xs font-medium rounded-md bg-primary hover:bg-primary/90 text-white transition-colors flex items-center gap-1.5"
                    >
                      {copiedKey === 'determinism' ? (
                        <>
                          <Check className="w-3.5 h-3.5" />
                          <span>Copied</span>
                        </>
                      ) : (
                        <>
                          <Sparkles className="w-3.5 h-3.5" />
                          <span>Copy Snippet</span>
                        </>
                      )}
                    </button>
                  </div>
                </div>

                <pre className="p-4 bg-bg border border-border rounded-lg text-xs font-mono text-text overflow-x-auto whitespace-pre-wrap leading-relaxed">
                  {determinismSnippet}
                </pre>
              </div>
            )}
          </>
        )}
      </div>

      {/* Audit Codebase Modal */}
      <AuditModal
        isOpen={showAuditModal}
        onClose={() => setShowAuditModal(false)}
        onSubmit={handleRunAudit}
      />
    </div>
  );
}

import React, { useState, useEffect, useCallback } from 'react';
import {
  Sparkles,
  Plus,
  Copy,
  Check,
  RefreshCw,
  FileCode,
  Layers,
  Database,
  Trash2,
  Cpu,
} from 'lucide-react';
import { api } from '../../api';
import { SignificanceTable } from './SignificanceTable';
import { ComponentImpactWaterfall } from './ComponentImpactWaterfall';
import { NewAblationModal } from './NewAblationModal';
import { RecordRunsModal } from './RecordRunsModal';
import type {
  AblationStudy,
  CreateStudyRequest,
  RecordRunsRequest,
} from './types';

interface AblationStudioProps {
  projectId?: string | null;
}

export const AblationStudio: React.FC<AblationStudioProps> = ({ projectId }) => {
  const [studies, setStudies] = useState<AblationStudy[]>([]);
  const [selectedStudyId, setSelectedStudyId] = useState<string | null>(null);
  const [selectedMetric, setSelectedMetric] = useState<string>('accuracy');
  const [loading, setLoading] = useState<boolean>(true);
  const [analyzing, setAnalyzing] = useState<boolean>(false);
  const [copiedLatex, setCopiedLatex] = useState<boolean>(false);
  const [latexCode, setLatexCode] = useState<string>('');

  const [isNewStudyOpen, setIsNewStudyOpen] = useState(false);
  const [isRecordRunsOpen, setIsRecordRunsOpen] = useState(false);

  const activeStudy = studies.find((s) => s.id === selectedStudyId) || studies[0] || null;

  const loadStudies = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.getAblationStudies(projectId);
      const studyList: AblationStudy[] = res.studies || [];
      setStudies(studyList);
      if (studyList.length > 0) {
        if (!selectedStudyId || !studyList.some((s) => s.id === selectedStudyId)) {
          setSelectedStudyId(studyList[0].id);
        }
      } else {
        setSelectedStudyId(null);
      }
    } catch {
      // Fallback
    } finally {
      setLoading(false);
    }
  }, [projectId, selectedStudyId]);

  useEffect(() => {
    loadStudies();
  }, [loadStudies]);

  // Update selectedMetric when activeStudy changes
  useEffect(() => {
    if (activeStudy) {
      if (!selectedMetric || (!activeStudy.comparisons[selectedMetric] && activeStudy.primary_metric)) {
        setSelectedMetric(activeStudy.primary_metric);
      }
    }
  }, [activeStudy, selectedMetric]);

  const handleCreateStudy = async (data: CreateStudyRequest) => {
    const res = await api.createAblationStudy(data);
    if (res.study) {
      setStudies((prev) => [res.study, ...prev]);
      setSelectedStudyId(res.study.id);
      setSelectedMetric(res.study.primary_metric);
    }
  };

  const handleRecordRuns = async (data: RecordRunsRequest) => {
    if (!activeStudy) return;
    const res = await api.recordAblationRuns(activeStudy.id, data);
    if (res.study) {
      setStudies((prev) => prev.map((s) => (s.id === res.study.id ? res.study : s)));
    }
  };

  const handleAnalyze = async () => {
    if (!activeStudy) return;
    setAnalyzing(true);
    try {
      const res = await api.analyzeAblationStudy(activeStudy.id);
      if (res.study) {
        setStudies((prev) => prev.map((s) => (s.id === res.study.id ? res.study : s)));
      }
    } finally {
      setAnalyzing(false);
    }
  };

  const handleFetchLatex = async () => {
    if (!activeStudy) return;
    try {
      const res = await api.getAblationLatex(activeStudy.id);
      if (res.latex_table) {
        setLatexCode(res.latex_table);
      }
    } catch {
      // Ignore
    }
  };

  const handleDeleteStudy = async () => {
    if (!activeStudy || !confirm(`Delete ablation study "${activeStudy.title}"?`)) return;
    await api.deleteAblationStudy(activeStudy.id);
    setStudies((prev) => prev.filter((s) => s.id !== activeStudy.id));
    setSelectedStudyId(null);
  };

  const handleCopyLatex = () => {
    if (!latexCode) return;
    navigator.clipboard.writeText(latexCode);
    setCopiedLatex(true);
    setTimeout(() => setCopiedLatex(false), 2000);
  };

  const availableMetrics = activeStudy
    ? Array.from(
        new Set([
          activeStudy.primary_metric,
          ...Object.keys(activeStudy.comparisons),
          ...Object.values(activeStudy.variants).flatMap((v) => Object.keys(v.metrics)),
        ])
      )
    : [];

  const criticalCount = activeStudy ? activeStudy.component_impacts.filter((i) => i.is_critical).length : 0;
  const topImpact = activeStudy && activeStudy.component_impacts.length > 0 ? activeStudy.component_impacts[0] : null;

  return (
    <div className="flex flex-col h-full bg-background overflow-hidden">
      {/* Top action header */}
      <div className="flex flex-wrap items-center justify-between gap-3 px-6 py-4 border-b border-border bg-surface shrink-0">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-primary/10 text-primary border border-primary/20">
            <Sparkles className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-base font-bold text-text flex items-center gap-2">
              Ablation &amp; Significance Studio
              <span className="text-xs font-normal text-text-dim px-2 py-0.5 rounded bg-zinc-800 border border-border">
                Holm-Bonferroni Corrected
              </span>
            </h2>
            <p className="text-xs text-text-dim">
              Systematic component isolations, multi-seed statistical testing &amp; publication table generator
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {studies.length > 0 && (
            <select
              value={selectedStudyId || ''}
              onChange={(e) => setSelectedStudyId(e.target.value)}
              aria-label="Select Ablation Study"
              className="px-3 py-1.5 rounded-lg border border-border bg-background text-sm text-text focus:outline-none focus:border-primary"
            >
              {studies.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.title} ({Object.keys(s.variants).length} variants)
                </option>
              ))}
            </select>
          )}

          <button
            type="button"
            onClick={() => setIsNewStudyOpen(true)}
            className="px-3 py-1.5 rounded-lg bg-primary hover:bg-primary/90 text-sm font-medium text-white transition-colors flex items-center gap-1.5"
          >
            <Plus className="w-4 h-4" />
            New Study
          </button>
        </div>
      </div>

      {/* Main Content Body */}
      {loading ? (
        <div className="flex flex-1 items-center justify-center text-text-dim gap-2">
          <RefreshCw className="w-5 h-5 animate-spin" />
          Loading Ablation Studies...
        </div>
      ) : !activeStudy ? (
        <div className="flex flex-1 flex-col items-center justify-center text-center p-8">
          <Layers className="w-12 h-12 text-text-dim mb-3 opacity-30" />
          <h3 className="text-base font-semibold text-text mb-1">No Ablation Studies Yet</h3>
          <p className="text-sm text-text-dim max-w-md mb-4">
            Create an ablation study to systematically evaluate architectural variants, component drops, and compute statistical significance for your paper.
          </p>
          <button
            type="button"
            onClick={() => setIsNewStudyOpen(true)}
            className="px-4 py-2 rounded-lg bg-primary hover:bg-primary/90 text-sm font-medium text-white transition-colors flex items-center gap-2"
          >
            <Plus className="w-4 h-4" />
            Create First Study
          </button>
        </div>
      ) : (
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Summary KPIs */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="p-4 rounded-xl border border-border bg-surface/50">
              <div className="text-xs text-text-dim mb-1 flex items-center gap-1.5">
                <Layers className="w-3.5 h-3.5 text-primary" />
                Evaluated Variants
              </div>
              <div className="text-2xl font-bold text-text">
                {Object.keys(activeStudy.variants).length}
              </div>
              <div className="text-[11px] text-text-dim mt-1">
                Baseline: <span className="text-primary font-medium">{activeStudy.baseline_variant_name}</span>
              </div>
            </div>

            <div className="p-4 rounded-xl border border-border bg-surface/50">
              <div className="text-xs text-text-dim mb-1 flex items-center gap-1.5">
                <Cpu className="w-3.5 h-3.5 text-emerald-400" />
                Primary Metric
              </div>
              <div className="text-xl font-bold text-emerald-400 capitalize truncate">
                {activeStudy.primary_metric}
              </div>
              <div className="text-[11px] text-text-dim mt-1">
                Direction: {activeStudy.higher_is_better ? 'Higher is better (↑)' : 'Lower is better (↓)'}
              </div>
            </div>

            <div className="p-4 rounded-xl border border-border bg-surface/50">
              <div className="text-xs text-text-dim mb-1 flex items-center gap-1.5">
                <Sparkles className="w-3.5 h-3.5 text-rose-400" />
                Critical Components
              </div>
              <div className="text-2xl font-bold text-rose-400">{criticalCount}</div>
              <div className="text-[11px] text-text-dim mt-1">
                p &lt; 0.05 vs baseline (statistically vital)
              </div>
            </div>

            <div className="p-4 rounded-xl border border-border bg-surface/50">
              <div className="text-xs text-text-dim mb-1 flex items-center gap-1.5">
                <FileCode className="w-3.5 h-3.5 text-cyan-400" />
                Top Isolated Factor
              </div>
              <div className="text-sm font-bold text-text truncate">
                {topImpact ? topImpact.component_name : '--'}
              </div>
              <div className="text-[11px] text-rose-400 mt-1">
                {topImpact ? `-${topImpact.impact_score.toFixed(4)} (-${topImpact.relative_drop_pct.toFixed(1)}%) drop` : 'No ranking yet'}
              </div>
            </div>
          </div>

          {/* Action toolbar & metric tabs */}
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border pb-3">
            <div className="flex items-center gap-1.5 overflow-x-auto">
              <span className="text-xs font-semibold text-text-dim uppercase mr-2">Metric:</span>
              {availableMetrics.map((m) => (
                <button
                  key={m}
                  type="button"
                  onClick={() => setSelectedMetric(m)}
                  className={`px-3 py-1 rounded-lg text-xs font-medium transition-colors ${
                    selectedMetric === m
                      ? 'bg-primary text-white'
                      : 'bg-surface text-text-dim hover:text-text hover:bg-surface-hover'
                  }`}
                >
                  {m}
                </button>
              ))}
            </div>

            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => setIsRecordRunsOpen(true)}
                className="px-3 py-1.5 rounded-lg border border-border text-xs font-medium text-text hover:bg-surface-hover transition-colors flex items-center gap-1.5"
              >
                <Database className="w-3.5 h-3.5 text-primary" />
                Record Runs
              </button>

              <button
                type="button"
                disabled={analyzing}
                onClick={handleAnalyze}
                className="px-3 py-1.5 rounded-lg border border-border text-xs font-medium text-text hover:bg-surface-hover transition-colors flex items-center gap-1.5 disabled:opacity-50"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${analyzing ? 'animate-spin' : ''}`} />
                Re-Analyze
              </button>

              <button
                type="button"
                onClick={handleFetchLatex}
                className="px-3 py-1.5 rounded-lg border border-border text-xs font-medium text-text hover:bg-surface-hover transition-colors flex items-center gap-1.5"
              >
                <FileCode className="w-3.5 h-3.5 text-cyan-400" />
                View LaTeX
              </button>

              <button
                type="button"
                onClick={handleDeleteStudy}
                className="p-1.5 rounded-lg text-text-dim hover:text-rose-400 hover:bg-surface-hover transition-colors"
                title="Delete Study"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Significance Matrix Table */}
          <div className="space-y-2">
            <h3 className="text-sm font-semibold text-text">
              Multi-Seed Significance &amp; Effect Size Table ({selectedMetric})
            </h3>
            <SignificanceTable
              study={activeStudy}
              selectedMetric={selectedMetric}
            />
          </div>

          {/* Component Impact Waterfall Breakdown */}
          <div className="pt-2">
            <ComponentImpactWaterfall
              impacts={activeStudy.component_impacts}
              primaryMetric={activeStudy.primary_metric}
            />
          </div>

          {/* Academic Prose Narrative Summary */}
          {activeStudy.narrative_summary && (
            <div className="p-4 rounded-xl border border-border bg-surface/40 space-y-2">
              <h4 className="text-xs font-semibold text-text uppercase tracking-wider">
                Automated Scientific Narrative Report
              </h4>
              <div className="text-xs text-text-dim leading-relaxed whitespace-pre-line font-sans">
                {activeStudy.narrative_summary}
              </div>
            </div>
          )}

          {/* Live LaTeX Code Viewer */}
          {latexCode && (
            <div className="p-4 rounded-xl border border-border bg-black/60 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-mono font-medium text-cyan-400 flex items-center gap-1.5">
                  <FileCode className="w-3.5 h-3.5" />
                  Camera-Ready LaTeX Table (Booktabs)
                </span>
                <button
                  type="button"
                  onClick={handleCopyLatex}
                  className="px-2.5 py-1 rounded bg-zinc-800 hover:bg-zinc-700 text-xs font-medium text-text transition-colors flex items-center gap-1.5"
                >
                  {copiedLatex ? (
                    <>
                      <Check className="w-3.5 h-3.5 text-emerald-400" />
                      Copied!
                    </>
                  ) : (
                    <>
                      <Copy className="w-3.5 h-3.5" />
                      Copy LaTeX
                    </>
                  )}
                </button>
              </div>
              <pre className="p-3 rounded bg-zinc-950 border border-zinc-800 text-xs font-mono text-zinc-300 overflow-x-auto select-all">
                {latexCode}
              </pre>
            </div>
          )}
        </div>
      )}

      {/* Modals */}
      <NewAblationModal
        isOpen={isNewStudyOpen}
        onClose={() => setIsNewStudyOpen(false)}
        onSubmit={handleCreateStudy}
        projectId={projectId}
      />

      <RecordRunsModal
        isOpen={isRecordRunsOpen}
        onClose={() => setIsRecordRunsOpen(false)}
        onSubmit={handleRecordRuns}
        existingVariantNames={activeStudy ? Object.keys(activeStudy.variants) : []}
        defaultPrimaryMetric={activeStudy?.primary_metric || 'accuracy'}
      />
    </div>
  );
};

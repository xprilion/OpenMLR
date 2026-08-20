# OpenMLR: Full-Scale UI, Performance & Stronger AI Harness Improvement Plan

> **For Hermes / Subagents:** Use the `subagent-driven-development` and `test-driven-development` skills to execute this implementation plan task-by-task.

**Goal:** Transform OpenMLR into the premier open-source autonomous machine learning research platform with a fluid modern dark UI, high-throughput asynchronous backend performance, and an industrial-strength AI research harness capable of autonomous literature reconnaissance, experiment execution, LaTeX paper drafting, and peer review simulation.

**Architecture:**
- **Frontend:** React 19 + TypeScript + Vite + Tailwind CSS / shadcn dark palette (`#000000` / `#09090b` / `#1288ff` electric blue accents). Virtualized chat lists, live split-pane LaTeX/Markdown editor, interactive D3/Canvas citation graph, and real-time experiment metric dashboards.
- **Backend:** Python 3.12 + FastAPI + AsyncPG SQLAlchemy 2.0 + Redis + Celery worker pool + LiteLLM / Custom Multi-Provider Gateway.
- **AI Harness:** Multi-phase autonomous ML research engine (Reconnaissance → Hypothesis → Experimentation → Self-Correction → LaTeX Compilation → Peer Review).

---

## High-Level Improvement Pillars

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          OpenMLR Next-Gen Platform                          │
├─────────────────────────┬─────────────────────────┬─────────────────────────┤
│   1. UI / UX Overhaul   │   2. Performance Engine │ 3. Stronger AI Harness  │
├─────────────────────────┼─────────────────────────┼─────────────────────────┤
│ • Zero layout shift     │ • AsyncPG connection    │ • Graph citation crawl  │
│ • Pure dark (#000000)   │   pooling & Redis cache │ • Experiment runner     │
│ • Split LaTeX editor    │ • SSE channel multiplex │ • CUDA/NaN self-heal    │
│ • D3 Citation Graph     │ • Parallel paper ingest │ • LaTeX auto-compiler   │
│ • Metric charts (Loss)  │ • Hybrid BM25+Dense search│ • Multi-agent reviewer│
│ • Lucide vector icons   │ • Virtualized message UI│ • Eval benchmark harness│
└─────────────────────────┴─────────────────────────┴─────────────────────────┘
```

---

## Phase 1: UI & UX Modernization (Zero-Shift, Dark Theme, Research Artifacts)

### Task 1.1: Design System & Theme Stabilization
- **Objective:** Establish authentic shadcn/ui dark aesthetic (`#000000` pure black, `#09090b` surface, `#1288ff` accent), zero layout shift transitions, and Lucide SVG icon system.
- **Files:**
  - Modify: `frontend/src/index.css`
  - Modify: `frontend/tailwind.config.js` (or Vite CSS config)
  - Create: `frontend/src/components/ui/Icon.tsx` (central Lucide icon mapper)
- **Key Actions:**
  1. Define CSS variables for tokens (`--background: 0 0% 0%`, `--card: 240 10% 3.9%`, `--primary: 212 100% 53.7%`).
  2. Remove layout jump animations; restrict motion strictly to spinners, progress loaders, and smooth opacity transitions.
  3. Replace any legacy emoji buttons with crisp vector Lucide SVG icons.

### Task 1.2: Modularize Monolithic `App.tsx` into Context Providers & Views
- **Objective:** Break down the 1,100-line `App.tsx` into modular domain contexts and view components (< 400 lines each).
- **Files:**
  - Create: `frontend/src/context/ChatContext.tsx`
  - Create: `frontend/src/context/ProjectContext.tsx`
  - Create: `frontend/src/context/ComputeContext.tsx`
  - Create: `frontend/src/components/layout/MainLayout.tsx`
  - Create: `frontend/src/components/chat/ChatContainer.tsx`
  - Modify: `frontend/src/App.tsx` (reduced to clean router and top-level provider wrapping)

### Task 1.3: Live Split-Pane Paper & LaTeX Studio
- **Objective:** Build a dedicated, distraction-free Paper Studio supporting split Markdown/LaTeX authoring, live PDF/HTML preview, BibTeX autocomplete, and section diffing.
- **Files:**
  - Create: `frontend/src/components/paper/PaperStudio.tsx`
  - Create: `frontend/src/components/paper/LatexPreview.tsx`
  - Create: `frontend/src/components/paper/BibtexManager.tsx`
  - Create: `frontend/src/components/paper/SectionDiffViewer.tsx`
- **Features:**
  - Split-view editor with live formula rendering (KaTeX / MathJax).
  - One-click compile to Overleaf / PDF export.
  - Section-by-section AI expansion, rewriting, and citation insertion.

### Task 1.4: Interactive Research Citation Graph & Knowledge Explorer
- **Objective:** Render an interactive graph visualization of searched and referenced papers, displaying citation edges, co-authorship clusters, and methodology hierarchies.
- **Files:**
  - Create: `frontend/src/components/research/CitationGraph.tsx`
  - Create: `frontend/src/components/research/PaperCard.tsx`
  - Create: `frontend/src/components/research/LiteratureMatrix.tsx`
- **Features:**
  - Canvas / SVG force-directed citation layout.
  - Direct node click to view paper abstract, extracted claims, and PDF viewer.
  - Export literature comparison matrix (Method, Dataset, Metric, Baseline, Gap) as Markdown/CSV.

### Task 1.5: Live Experiment Metric Dashboard & Run Visualizer
- **Objective:** Provide a real-time W&B-style experiment tracking dashboard displaying training loss curves, evaluation benchmarks, GPU utilization, and output artifacts.
- **Files:**
  - Create: `frontend/src/components/experiments/RunDashboard.tsx`
  - Create: `frontend/src/components/experiments/MetricCharts.tsx`
  - Create: `frontend/src/components/experiments/CheckpointViewer.tsx`

---

## Phase 2: High-Throughput Performance & Backend Scalability

### Task 2.1: Async Database Session Pool & Query Optimization
- **Objective:** Upgrade SQLAlchemy async engine configuration with high-concurrency connection pooling, statement caching, and index tuning.
- **Files:**
  - Modify: `backend/openmlr/db/session.py`
  - Modify: `backend/openmlr/db/models.py`
  - Create: `backend/openmlr/db/migrations/env.py`
- **Optimizations:**
  - Set `pool_size=30`, `max_overflow=20`, `pool_recycle=1800`, `pool_pre_ping=True`.
  - Add compound indexes on `(project_id, created_at)` and `(conversation_id, sequence_num)`.

### Task 2.2: Parallel Multi-Source Paper Ingestion with Redis Caching
- **Objective:** Accelerate literature search by querying arXiv, OpenAlex, Semantic Scholar, and CrossRef in parallel with async connection pools and tiered Redis caching.
- **Files:**
  - Modify: `backend/openmlr/tools/papers.py`
  - Create: `backend/openmlr/services/paper_cache.py`
  - Create: `backend/openmlr/services/arxiv_client.py`
- **Optimizations:**
  - Parallel `asyncio.gather` across academic providers with per-provider bounded semaphores.
  - 24-hour Redis TTL cache for paper abstracts, metadata, and citation counts.
  - Automated fallback if Semantic Scholar rate limits hit.

### Task 2.3: Multiplexed Server-Sent Events (SSE) & WebSocket Hub
- **Objective:** Consolidate agent thinking steps, tool outputs, terminal streams, and metrics into a unified low-latency event bus.
- **Files:**
  - Modify: `backend/openmlr/services/event_bus.py`
  - Modify: `backend/openmlr/agent/loop.py`
  - Modify: `frontend/src/hooks/useSSE.ts`
- **Optimizations:**
  - Stream delta tokens with sub-20ms latency.
  - Buffer background worker events in Redis Pub/Sub channels to enable reconnect without lost messages.

### Task 2.4: Hybrid Semantic + BM25 Vector Search for Project Knowledge
- **Objective:** Implement hybrid retrieval (sparse BM25 + dense embedding vectors) over user workspaces, downloaded paper PDFs, and experiment notes.
- **Files:**
  - Create: `backend/openmlr/services/vector_index.py`
  - Create: `backend/openmlr/services/hybrid_search.py`
  - Modify: `backend/openmlr/workspace/knowledge.py`

---

## Phase 3: Stronger AI Research Harness & Autonomous Agent Capabilities

### Task 3.1: Multi-Phase Structured Research Orchestration Loop
- **Objective:** Implement a dedicated AI research state machine that guides the agent through systematic scientific exploration:
  1. *Reconnaissance Phase*: Broad literature search + citation depth analysis.
  2. *Hypothesis & Proposal Phase*: Formulation of testable ML claims and baseline comparison design.
  3. *Experiment & Code Phase*: Writing PyTorch/JAX scripts, executing on Compute, and parsing metrics.
  4. *Analysis & Self-Correction Phase*: Analyzing loss curves, ablation findings, and error recovery.
  5. *Paper Drafting Phase*: Generating full LaTeX manuscripts with figures and BibTeX.
- **Files:**
  - Create: `backend/openmlr/agent/research_orchestrator.py`
  - Create: `backend/openmlr/agent/states.py`
  - Modify: `backend/openmlr/agent/loop.py`
  - Modify: `backend/openmlr/agent/prompts.py`

### Task 3.2: Automated ML Error Diagnostic & Self-Healing Engine (Completed - PR #48)
- **Objective:** Add specialized recovery agents that catch and repair common ML failures during execution:
  - CUDA Out-of-Memory (OOM) → Automatically injects gradient accumulation, batch size reduction, or FlashAttention/FP16.
  - Loss NaN / Divergence → Diagnoses learning rate, gradient clipping, or numerical instability.
  - Tensor Shape Mismatch → Analyzes PyTorch traceback and applies tensor reshaping or dimension alignment.
  - Missing Package / Version Conflict → Probes environment and auto-installs compatible wheel binaries.
  - Process Timeout / Hung CUDA Kernel → Diagnoses deadlocks in DDP or hanging dataloaders.
- **Files:**
  - Create: `backend/openmlr/agent/ml_debugger.py`
  - Modify: `backend/openmlr/agent/doom_loop.py`
  - Modify: `backend/openmlr/agent/loop_executor.py`
  - Create: `backend/tests/test_ml_debugger.py`

### Task 3.3: Autonomous Multi-Agent Peer Review Simulation (Completed - PR #49)
- **Objective:** Deploy a committee of 3 independent reviewer subagents + 1 Meta-Reviewer that evaluate research plans and drafted papers against standard conference rubrics (ICLR / NeurIPS / ICML):
  - Reviewer 1 (Theory & Novelty): Rigor, mathematical correctness, theoretical claims.
  - Reviewer 2 (Empirical Validation): Baselines, ablation completeness, statistical significance.
  - Reviewer 3 (Clarity & Reproducibility): Code availability, hyperparameters, writing structure.
  - Meta-Reviewer: Consolidates reviews, issues Accept/Reject decisions with actionable revision feedback.
- **Files:**
  - Create: `backend/openmlr/agent/peer_review.py`
  - Create: `backend/openmlr/agent/review_prompts.py`
  - Create: `backend/openmlr/routes/review.py`
  - Create: `backend/tests/test_peer_review.py`

### Task 3.4: Sandboxed LaTeX Compilation & BibTeX Validator (NEXT)
- **Objective:** Built-in headless LaTeX compiler (Tectonic / `pdflatex`) that validates syntax, checks for missing citations, downloads missing packages, and produces clean PDF artifacts.
- **Files:**
  - Create: `backend/openmlr/tools/latex_compiler.py`
  - Create: `backend/openmlr/services/bibtex_validator.py`
  - Modify: `backend/openmlr/tools/writing.py`

### Task 3.5: ML Agent Evaluation Benchmark Harness
- **Objective:** Implement an automated benchmark harness to evaluate OpenMLR agent performance across standard research benchmarks:
  - *Paper Reproduction Benchmark*: Ability to reproduce reported results from an arXiv paper given repository code.
  - *Kernel Optimization Benchmark*: Ability to accelerate PyTorch/Triton kernels by >1.5x.
  - *Hypothesis Discovery Benchmark*: Ability to formulate novel ablation hypotheses on standard datasets (CIFAR, ImageNet, GLUE, GSM8K).
- **Files:**
  - Create: `backend/openmlr/eval/benchmark_harness.py`
  - Create: `backend/openmlr/eval/tasks/reproduction_task.py`
  - Create: `backend/openmlr/eval/tasks/optimization_task.py`
  - Create: `backend/openmlr/eval/metrics.py`

---

## Implementation Roadmap & Milestones

| Milestone | Key Deliverables | Expected Outcome |
| :--- | :--- | :--- |
| **M1: Design & Frontend Refactor** | Split `App.tsx`, implement shadcn dark theme, Lucide SVG icons, zero layout shift. | Instant, crisp UI responsiveness; modular component architecture. |
| **M2: Paper Studio & Citation Graph** | Split LaTeX/Markdown editor, BibTeX autocomplete, interactive D3 citation graph. | Complete in-browser literature exploration & manuscript drafting. |
| **M3: Backend Performance & Caching** | AsyncPG connection pool, Redis paper caching, multiplexed SSE stream, hybrid search. | 4x faster paper ingestion, zero dropped tokens during long runs. |
| **M4: Autonomous Research Harness** | 5-phase research state machine, CUDA/ML self-correction engine, LaTeX compiler. | Fully autonomous end-to-end ML research execution on local/cloud compute. |
| **M5: Peer Review & Eval Benchmarks** | Multi-agent ICLR/NeurIPS reviewer committee, reproduction & optimization benchmark suite. | Objective evaluation of agent research quality & automated self-improvement. |

---

## Verification & Testing Strategy

1. **Unit & Integration Tests:**
   - Backend: `pytest backend/tests -v --cov=openmlr` (target: >85% coverage).
   - Frontend: `pnpm --filter frontend test` (Vitest + React Testing Library).
2. **End-to-End Autonomous Research Test:**
   - Run OpenMLR on a reference task: *"Propose and benchmark an attention mechanism modification on a nanoGPT training loop"*.
   - Verify that:
     1. Literature search returns cited papers.
     2. Experiment script executes on Docker/Modal and logs loss curves.
     3. Drafted LaTeX paper compiles to PDF without syntax errors.
     4. Simulated peer review scores the submission with detailed critiques.

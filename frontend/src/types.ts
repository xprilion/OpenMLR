export interface AgentEvent {
  event_type: string;
  data?: Record<string, any>;
}

export interface SubAgentChild {
  tool: string;
  args?: string;
  id?: string;
  output?: string;
  success?: boolean;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'tool' | 'system' | 'error';
  content: string;
  streaming?: boolean;
  timestamp?: number;
  duration?: number;
  model?: string;
  mode?: string;
  /** Accumulated thinking/reasoning content from the LLM */
  thinking?: string;
  /** Duration in seconds the model spent thinking */
  thinkingDuration?: number;
  /** Whether the thinking block is collapsed (model started replying) */
  thinkingCollapsed?: boolean;
  metadata?: {
    tool?: string;
    args?: string;
    output?: string;
    outputSuccess?: boolean;
    tool_call_id?: string;
    // Sub-agent fields
    isSubAgent?: boolean;
    agentType?: string;
    children?: SubAgentChild[];
    toolCount?: number;
    duration?: number;
  };
}

export interface Conversation {
  id: number;
  uuid: string;
  title: string;
  model: string | null;
  mode: string;
  user_message_count: number;
  created_at: string;
  updated_at: string;
}

export interface User {
  id: number;
  username: string;
  display_name: string | null;
}

export interface Provider {
  id: string;
  name: string;
  key_env: string;
  configured: boolean;
  categories: string[];
  docs_url?: string;
  is_custom?: boolean;
  sdk_type?: string;
  api_base?: string;
}

// ── Structured Questions ────────────────────────────────

export interface QuestionOption {
  label: string;
  description?: string;
}

export interface Question {
  id: string;
  question: string;
  options: QuestionOption[];
  allow_text?: boolean; // default true
}

export interface QuestionsPayload {
  questions: Question[];
  context?: string;
  suggest_mode?: string | null;
}

// ── Projects ────────────────────────────────────────────

export interface Project {
  id: number;
  uuid: string;
  name: string;
  slug: string;
  description: string | null;
  workspace_path: string | null;
  status: 'active' | 'archived';
  settings: Record<string, any>;
  is_default?: boolean;
  conversation_count?: number;
  created_at: string;
  updated_at: string;
}

export interface FileNode {
  name: string;
  path: string;
  is_dir: boolean;
  size: number | null;
  modified: number;
}

export interface OpenFile {
  path: string;
  content: string;
  language: string;
}

// ── Task Plan & Resources ───────────────────────────────

export interface PlanTask {
  title: string;
  status: 'pending' | 'in_progress' | 'completed' | 'cancelled';
}

export interface Resource {
  title: string;
  url: string;
  type: 'paper' | 'code' | 'dataset' | 'doc' | 'report' | 'plan';
  id?: string;    // for reports — used to fetch content
  content?: string;
}

// ── TODO Approval ───────────────────────────────────────

export interface TodoApprovalPayload {
  change_type: 'create' | 'add';
  proposed_tasks: Array<{ title: string; status: string; priority?: string }>;
  current_tasks: Array<{ title: string; status: string; priority?: string }>;
}

// ── Context & Budget ────────────────────────────────────

export interface ContextUsage {
  used: number;
  max: number;
  ratio: number;
}

export interface SearchBudget {
  used: number;
  max: number;
}

// ── MCP Servers ─────────────────────────────────────────

export interface McpServerStatus {
  name: string;
  url: string;
  enabled: boolean;
  connected: boolean;
  modes?: string[];
}

// ── @ Mentions ──────────────────────────────────────────

export interface Mention {
  type: 'server' | 'file';
  value: string; // server name or workspace-relative path
}

// ── Background Jobs ─────────────────────────────────────

export interface AgentJob {
  job_id: string;
  status: 'queued' | 'running' | 'completed' | 'failed' | 'cancelled';
  created_at: string;
  started_at?: string;
  completed_at?: string;
  error?: string;
}

// ── Peer Review Simulation ──────────────────────────────

export interface ReviewCriteria {
  name: string;
  weight: number;
  description: string;
  scale?: string;
}

export interface ConferenceRubric {
  venue: string;
  name: string;
  description: string;
  criteria: ReviewCriteria[];
  acceptance_threshold: number;
  score_range: [number, number];
}

export interface ReviewerPersona {
  id: string;
  name: string;
  role: string;
  focus_areas: string[];
}

export interface ReviewRubricsResponse {
  rubrics: Record<string, ConferenceRubric>;
  personas: ReviewerPersona[];
}

export interface SingleReview {
  reviewer_id: string;
  reviewer_name: string;
  role: string;
  overall_score: number;
  confidence: number;
  summary: string;
  strengths: string[];
  weaknesses: string[];
  questions_for_authors: string[];
  detailed_comments: string;
  recommendation: string;
  criteria_scores?: Record<string, number>;
}

export interface MetaReview {
  decision: string;
  decision_type: 'accept' | 'reject' | 'borderline';
  consensus_score: number;
  confidence: number;
  summary_of_consensus: string;
  justification: string;
  key_strengths: string[];
  primary_shortcomings: string[];
  actionable_revision_plan: string[];
}

export interface PeerReviewResult {
  submission_title: string;
  venue: string;
  average_score: number;
  reviews: SingleReview[];
  meta_review: MetaReview | null;
  evaluated_at: number;
  status: string;
  markdown_report?: string;
}

// ── Evaluation & Benchmark Suite ─────────────────────────

export interface EvalTaskInfo {
  task_id: string;
  name: string;
  description: string;
  category: 'reproduction' | 'optimization' | 'hypothesis';
  difficulty: 'easy' | 'medium' | 'hard';
  timeout_seconds: number;
  paper_title?: string;
  dataset_name?: string;
  target_metrics?: Record<string, number>;
  kernel_name?: string;
  framework?: string;
  baseline_latency_ms?: number;
  target_speedup?: number;
}

export interface EvalSuiteInfo {
  id: string;
  name: string;
  description: string;
  version: string;
  tasks: string[];
}

export interface EvalMetricResult {
  metric_name: string;
  target_value: number;
  achieved_value: number;
  passed: boolean;
  relative_error: number;
  tolerance: number;
}

export interface EvalTaskResult {
  task_id: string;
  task_name: string;
  category: string;
  passed: boolean;
  score: number;
  metrics: EvalMetricResult[];
  execution_time_seconds: number;
  error?: string | null;
}

export interface EvalSuiteRunResult {
  suite_name: string;
  total_tasks: number;
  passed_tasks: number;
  failed_tasks: number;
  pass_rate: number;
  average_score: number;
  execution_time_seconds: number;
  results: EvalTaskResult[];
}

// ── Autonomous Research Workflow ─────────────────────────

export type ResearchPhaseType =
  | 'idle'
  | 'reconnaissance'
  | 'hypothesis'
  | 'experimentation'
  | 'analysis'
  | 'paper_drafting'
  | 'completed';

export type MilestoneStatusType =
  | 'pending'
  | 'in_progress'
  | 'completed'
  | 'failed'
  | 'skipped';

export interface PhaseTransitionItem {
  from_phase: ResearchPhaseType;
  to_phase: ResearchPhaseType;
  reason: string;
  timestamp: number;
  artifacts_produced: string[];
  milestone_id?: string | null;
}

export interface ResearchMilestoneItem {
  milestone_id: string;
  phase: ResearchPhaseType;
  title: string;
  description: string;
  status: MilestoneStatusType;
  criteria: string[];
  output_artifacts: string[];
  created_at: number;
  completed_at?: number | null;
}

export interface ResearchArtifactsSummary {
  papers: Array<Record<string, unknown>>;
  hypotheses: Array<Record<string, unknown>>;
  experiments: Array<Record<string, unknown>>;
  metrics: Record<string, unknown>;
  manuscript_sections: Record<string, string>;
  bibtex_entries: string[];
}

export interface ResearchStateData {
  goal: string;
  current_phase: ResearchPhaseType;
  milestones: ResearchMilestoneItem[];
  artifacts: ResearchArtifactsSummary;
  history: PhaseTransitionItem[];
  created_at: number;
  updated_at: number;
}

export interface ProjectResearchStateResponse {
  project_id: number;
  project_name: string;
  state: ResearchStateData;
  guidelines: string;
  context_prompt: string;
}

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

// ── Background Jobs ─────────────────────────────────────

export interface AgentJob {
  job_id: string;
  status: 'queued' | 'running' | 'completed' | 'failed' | 'cancelled';
  created_at: string;
  started_at?: string;
  completed_at?: string;
  error?: string;
}

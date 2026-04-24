export interface AgentEvent {
  event_type: string;
  data?: Record<string, any>;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'tool' | 'tool-output' | 'system' | 'error';
  content: string;
  metadata?: {
    tool?: string;
    args?: string;
    success?: boolean;
  };
}

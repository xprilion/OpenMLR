export interface AgentEvent {
  event_type: string;
  data?: Record<string, any>;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'tool' | 'system' | 'error';
  content: string;
  streaming?: boolean;
  metadata?: {
    tool?: string;
    args?: string;
    output?: string;
    outputSuccess?: boolean;
  };
}

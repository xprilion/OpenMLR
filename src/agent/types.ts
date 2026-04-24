export interface AgentEvent {
  event_type: string;
  data?: Record<string, any>;
}

export interface ToolSpec {
  name: string;
  description: string;
  parameters: Record<string, any>;
  handler: (args: Record<string, any>) => Promise<[string, boolean]>;
}

export interface Message {
  role: "system" | "user" | "assistant" | "tool";
  content: string;
  tool_calls?: ToolCall[];
  tool_call_id?: string;
  name?: string;
}

export interface ToolCall {
  id: string;
  type: "function";
  function: {
    name: string;
    arguments: string;
  };
}

export type EventHandler = (event: AgentEvent) => void;

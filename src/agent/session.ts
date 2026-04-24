import type { AgentEvent, Message, ToolCall } from "./types.js";
import type { AgentConfig } from "./config.js";
import { ContextManager } from "./context.js";
import { getAllTools } from "./tools/index.js";

export class Session {
  sessionId: string;
  config: AgentConfig;
  contextManager: ContextManager;
  isRunning = true;
  stream: boolean;
  pendingApproval: { tool_calls: ToolCall[] } | null = null;
  private cancelled = false;
  private eventHandlers: Set<(event: AgentEvent) => void> = new Set();
  turnCount = 0;

  constructor(config: AgentConfig) {
    this.sessionId = Math.random().toString(36).slice(2, 10);
    this.config = { ...config };
    this.contextManager = new ContextManager(config);
    this.stream = config.stream;
  }

  onEvent(handler: (event: AgentEvent) => void) {
    this.eventHandlers.add(handler);
    return () => this.eventHandlers.delete(handler);
  }

  sendEvent(event: AgentEvent) {
    for (const h of this.eventHandlers) {
      try { h(event); } catch { /* ignore */ }
    }
  }

  cancel() {
    this.cancelled = true;
  }

  resetCancel() {
    this.cancelled = false;
  }

  get isCancelled() {
    return this.cancelled;
  }

  updateModel(modelName: string) {
    this.config.model_name = modelName;
  }

  incrementTurn() {
    this.turnCount++;
  }
}

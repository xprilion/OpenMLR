import type { Message } from "./types.js";
import type { AgentConfig } from "./config.js";
import { buildSystemPrompt, COMPACT_PROMPT } from "./prompts.js";
import { getAllTools } from "./tools/index.js";
import { summarizeMessages } from "./llm.js";

export class ContextManager {
  items: Message[] = [];
  modelMaxTokens: number;
  compactThreshold: number;
  untouchedMessages: number;
  runningContextUsage = 0;

  constructor(config: AgentConfig) {
    this.modelMaxTokens = config.default_max_tokens;
    this.compactThreshold = Math.floor(this.modelMaxTokens * config.compact_threshold_ratio);
    this.untouchedMessages = config.untouched_messages;
    const toolSpecs = getAllTools().map((t) => ({
      type: "function",
      function: {
        name: t.name,
        description: t.description,
        parameters: t.parameters,
      },
    }));
    this.items = [
      { role: "system", content: buildSystemPrompt(getAllTools()) },
    ];
  }

  get needsCompaction(): boolean {
    return this.runningContextUsage > this.compactThreshold;
  }

  addMessage(message: Message, tokenCount?: number) {
    if (tokenCount) {
      this.runningContextUsage = tokenCount;
    } else {
      // Estimate: ~5 chars per token
      this.runningContextUsage += Math.ceil((message.content?.length || 0) / 5);
    }
    this.items.push(message);
  }

  getMessages(): Message[] {
    this.patchDanglingToolCalls();
    return [...this.items];
  }

  private patchDanglingToolCalls() {
    let assistantIdx = -1;
    for (let i = this.items.length - 1; i >= 0; i--) {
      if (this.items[i].role === "assistant" && this.items[i].tool_calls) {
        assistantIdx = i;
        break;
      }
    }
    if (assistantIdx === -1) return;

    const assistantMsg = this.items[assistantIdx];
    const toolCalls = assistantMsg.tool_calls || [];
    const existingResults = new Set<string>();

    for (let i = assistantIdx + 1; i < this.items.length; i++) {
      if (this.items[i].role === "tool" && this.items[i].tool_call_id) {
        existingResults.add(this.items[i].tool_call_id);
      }
    }

    for (const tc of toolCalls) {
      if (!existingResults.has(tc.id)) {
        this.items.push({
          role: "tool",
          content: "Task abandoned — no result was provided.",
          tool_call_id: tc.id,
          name: tc.function.name,
        });
      }
    }
  }

  async compact(config: AgentConfig) {
    if (!this.needsCompaction) return;

    const systemMsg = this.items[0];
    let firstUserIdx = 1;
    for (let i = 1; i < this.items.length; i++) {
      if (this.items[i].role === "user") {
        firstUserIdx = i;
        break;
      }
    }

    // Find cutoff point: preserve last untouched_messages
    let idx = Math.max(1, this.items.length - this.untouchedMessages);
    while (idx > 1 && this.items[idx].role !== "user") {
      idx--;
    }

    const recentMessages = this.items.slice(idx);
    const messagesToSummarize = this.items.slice(firstUserIdx + 1, idx);

    if (messagesToSummarize.length === 0) return;

    const summary = await summarizeMessages(messagesToSummarize, config);

    this.items = [
      systemMsg,
      this.items[firstUserIdx],
      {
        role: "user",
        content: `[SYSTEM: Previous conversation summarized]: ${summary}`,
      },
      ...recentMessages,
    ];

    this.runningContextUsage = Math.ceil(
      this.items.reduce((sum, m) => sum + (m.content?.length || 0), 0) / 5,
    );
  }

  undoLastTurn(): boolean {
    // Find last user message and remove everything after the one before it
    let lastUserIdx = -1;
    for (let i = this.items.length - 1; i >= 0; i--) {
      if (this.items[i].role === "user" && !this.items[i].content?.startsWith("[SYSTEM:")) {
        lastUserIdx = i;
        break;
      }
    }
    if (lastUserIdx <= 1) return false;

    this.items = this.items.slice(0, lastUserIdx);
    this.runningContextUsage = Math.ceil(
      this.items.reduce((sum, m) => sum + (m.content?.length || 0), 0) / 5,
    );
    return true;
  }
}

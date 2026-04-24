import type { Session } from "./session.js";
import type { AgentEvent, Message, ToolCall } from "./types.js";
import { callLLM } from "./llm.js";
import { getAllTools } from "./tools/index.js";

const MAX_LLM_RETRIES = 3;
const LLM_RETRY_DELAYS = [5000, 15000, 30000];

function isTransientError(error: any): boolean {
  const err = String(error).toLowerCase();
  const patterns = [
    "timeout", "timed out", "429", "rate limit", "rate_limit",
    "503", "service unavailable", "502", "bad gateway", "500",
    "internal server error", "overloaded", "capacity",
    "connection reset", "connection refused", "connection error",
    "eof", "broken pipe",
  ];
  return patterns.some((p) => err.includes(p));
}

function friendlyErrorMessage(error: any): string {
  const err = String(error).toLowerCase();
  if (err.includes("authentication") || err.includes("unauthorized") || err.includes("api key")) {
    return (
      "Authentication failed — your API key is missing or invalid.\n\n" +
      "To fix this, set the API key for your model provider:\n" +
      "  • Anthropic:   export ANTHROPIC_API_KEY=sk-...\n" +
      "  • OpenAI:      export OPENAI_API_KEY=sk-...\n" +
      "  • OpenRouter:  export OPENROUTER_API_KEY=sk-or-...\n\n" +
      "You can also add it to a .env file in the project root.\n" +
      "To switch models, use the /model command."
    );
  }
  if (err.includes("insufficient") && err.includes("credit")) {
    return "Insufficient API credits. Please check your account balance.";
  }
  if (err.includes("model") && (err.includes("not found") || err.includes("does not exist"))) {
    return "Model not found. Use '/model' to switch to a valid model ID.";
  }
  return String(error);
}

function needsApproval(toolName: string, _toolArgs: Record<string, any>, config: any): boolean {
  if (config.yolo_mode) return false;
  // For MVP: no tools require approval. Can add later.
  return false;
}

async function delay(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export async function runAgentTurn(session: Session, text: string) {
  session.resetCancel();

  // Abandon pending approval if user sends new message
  if (text && session.pendingApproval) {
    const toolCalls = session.pendingApproval.tool_calls;
    for (const tc of toolCalls) {
      session.contextManager.addMessage({
        role: "tool",
        content: "Task abandoned — user continued the conversation without approving.",
        tool_call_id: tc.id,
        name: tc.function.name,
      });
      session.sendEvent({
        event_type: "tool_state_change",
        data: { tool_call_id: tc.id, tool: tc.function.name, state: "abandoned" },
      });
    }
    session.pendingApproval = null;
  }

  if (text) {
    session.contextManager.addMessage({ role: "user", content: text });
  }

  session.sendEvent({ event_type: "processing", data: { message: "Processing user input" } });

  let iteration = 0;
  let finalResponse: string | null = null;
  let errored = false;
  const maxIterations = session.config.max_iterations;

  while (maxIterations === -1 || iteration < maxIterations) {
    if (session.isCancelled) break;

    // Compact if needed
    if (session.contextManager.needsCompaction) {
      await session.contextManager.compact(session.config);
      session.sendEvent({
        event_type: "compacted",
        data: {
          old_tokens: session.contextManager.runningContextUsage,
          new_tokens: session.contextManager.runningContextUsage,
        },
      });
    }

    const messages = session.contextManager.getMessages();
    const toolSpecs = getAllTools().map((t) => ({
      type: "function" as const,
      function: {
        name: t.name,
        description: t.description,
        parameters: t.parameters,
      },
    }));

    try {
      let llmResult: any;
      let attempt = 0;

      while (true) {
        try {
          llmResult = await callLLM(
            messages,
            toolSpecs,
            session.config,
            session.stream
              ? (chunk: string) => {
                  session.sendEvent({ event_type: "assistant_chunk", data: { content: chunk } });
                }
              : undefined,
          );
          break;
        } catch (e: any) {
          if (attempt < MAX_LLM_RETRIES - 1 && isTransientError(e)) {
            const delayMs = LLM_RETRY_DELAYS[attempt];
            session.sendEvent({
              event_type: "tool_log",
              data: { tool: "system", log: `LLM connection error, retrying in ${delayMs / 1000}s...` },
            });
            await delay(delayMs);
            attempt++;
            continue;
          }
          throw e;
        }
      }

      const content = llmResult.content;
      const toolCalls = llmResult.toolCalls as ToolCall[];

      if (session.stream) {
        session.sendEvent({ event_type: "assistant_stream_end", data: {} });
      }

      // If no tool calls, add assistant message and done
      if (!toolCalls || toolCalls.length === 0) {
        if (content) {
          session.contextManager.addMessage({
            role: "assistant",
            content: content,
          }, llmResult.tokenCount);
          finalResponse = content;
        } else {
          session.sendEvent({
            event_type: "error",
            data: { error: "Model returned an empty response. Try again or switch models." },
          });
          errored = true;
        }
        break;
      }

      // Validate tool args
      const goodTools: Array<[ToolCall, string, Record<string, any>]> = [];
      const badTools: ToolCall[] = [];

      for (const tc of toolCalls) {
        try {
          const args = JSON.parse(tc.function.arguments);
          goodTools.push([tc, tc.function.name, args]);
        } catch {
          badTools.push(tc);
        }
      }

      // Add assistant message with tool calls
      session.contextManager.addMessage({
        role: "assistant",
        content: content || "",
        tool_calls: toolCalls,
      }, llmResult.tokenCount);

      // Handle bad tool calls
      for (const tc of badTools) {
        const errorMsg =
          `ERROR: Tool call to '${tc.function.name}' had malformed JSON arguments and was NOT executed. ` +
          `Retry with smaller content.`;
        session.contextManager.addMessage({
          role: "tool",
          content: errorMsg,
          tool_call_id: tc.id,
          name: tc.function.name,
        });
        session.sendEvent({
          event_type: "tool_call",
          data: { tool: tc.function.name, arguments: {}, tool_call_id: tc.id },
        });
        session.sendEvent({
          event_type: "tool_output",
          data: { tool: tc.function.name, tool_call_id: tc.id, output: errorMsg, success: false },
        });
      }

      if (session.isCancelled) break;

      // Separate approval vs non-approval
      const approvalTools: Array<[ToolCall, string, Record<string, any>]> = [];
      const autoTools: Array<[ToolCall, string, Record<string, any>]> = [];

      for (const [tc, name, args] of goodTools) {
        if (needsApproval(name, args, session.config)) {
          approvalTools.push([tc, name, args]);
        } else {
          autoTools.push([tc, name, args]);
        }
      }

      // Execute auto tools
      if (autoTools.length > 0) {
        // Send tool_call events
        for (const [tc, name, args] of autoTools) {
          session.sendEvent({
            event_type: "tool_call",
            data: { tool: name, arguments: args, tool_call_id: tc.id },
          });
        }

        // Execute in parallel
        const toolMap = new Map(getAllTools().map((t) => [t.name, t]));
        const promises = autoTools.map(async ([tc, name, args]) => {
          const spec = toolMap.get(name);
          if (!spec) {
            return [tc, name, args, `Unknown tool: ${name}`, false] as const;
          }
          try {
            const [output, success] = await spec.handler(args);
            return [tc, name, args, output, success] as const;
          } catch (e: any) {
            return [tc, name, args, `Tool error: ${e.message}`, false] as const;
          }
        });

        const results = await Promise.all(promises);

        for (const [tc, name, _args, output, success] of results) {
          session.contextManager.addMessage({
            role: "tool",
            content: output,
            tool_call_id: tc.id,
            name,
          });
          session.sendEvent({
            event_type: "tool_output",
            data: { tool: name, tool_call_id: tc.id, output, success },
          });
        }
      }

      // If approval needed, stop and ask user
      if (approvalTools.length > 0) {
        const toolsData = approvalTools.map(([tc, name, args]) => ({
          tool: name,
          arguments: args,
          tool_call_id: tc.id,
        }));
        session.sendEvent({
          event_type: "approval_required",
          data: { tools: toolsData, count: toolsData.length },
        });
        session.pendingApproval = { tool_calls: approvalTools.map(([tc]) => tc) };
        return;
      }

      iteration++;
    } catch (e: any) {
      const msg = friendlyErrorMessage(e);
      session.sendEvent({ event_type: "error", data: { error: msg } });
      errored = true;
      break;
    }
  }

  if (session.isCancelled) {
    session.sendEvent({ event_type: "interrupted" });
  } else if (!errored) {
    session.sendEvent({
      event_type: "turn_complete",
      data: { history_size: session.contextManager.items.length },
    });
  }

  session.incrementTurn();
}

export async function handleApproval(session: Session, approvals: Array<{ tool_call_id: string; approved: boolean; feedback?: string }>) {
  if (!session.pendingApproval) {
    session.sendEvent({ event_type: "error", data: { error: "No pending approval to process" } });
    return;
  }

  const toolCalls = session.pendingApproval.tool_calls;
  const approvalMap = new Map(approvals.map((a) => [a.tool_call_id, a]));
  session.pendingApproval = null;

  const approvedTasks: Array<[ToolCall, string, Record<string, any>]> = [];
  const rejectedTasks: Array<[ToolCall, string, string]> = [];

  for (const tc of toolCalls) {
    const name = tc.function.name;
    let args: Record<string, any>;
    try {
      args = JSON.parse(tc.function.arguments);
    } catch {
      session.contextManager.addMessage({
        role: "tool",
        content: "Malformed arguments",
        tool_call_id: tc.id,
        name,
      });
      session.sendEvent({
        event_type: "tool_output",
        data: { tool: name, tool_call_id: tc.id, output: "Malformed arguments", success: false },
      });
      continue;
    }

    const decision = approvalMap.get(tc.id);
    if (decision?.approved) {
      approvedTasks.push([tc, name, args]);
      session.sendEvent({
        event_type: "tool_state_change",
        data: { tool_call_id: tc.id, tool: name, state: "approved" },
      });
    } else {
      const feedback = decision?.feedback || "Job execution cancelled by user";
      rejectedTasks.push([tc, name, feedback]);
      session.sendEvent({
        event_type: "tool_state_change",
        data: { tool_call_id: tc.id, tool: name, state: "rejected" },
      });
    }
  }

  // Execute approved tools
  if (approvedTasks.length > 0) {
    const toolMap = new Map(getAllTools().map((t) => [t.name, t]));
    const promises = approvedTasks.map(async ([tc, name, args]) => {
      session.sendEvent({
        event_type: "tool_state_change",
        data: { tool_call_id: tc.id, tool: name, state: "running" },
      });
      const spec = toolMap.get(name);
      if (!spec) return [tc, name, `Unknown tool: ${name}`, false] as const;
      try {
        const [output, success] = await spec.handler(args);
        return [tc, name, output, success] as const;
      } catch (e: any) {
        return [tc, name, `Tool error: ${e.message}`, false] as const;
      }
    });

    const results = await Promise.all(promises);
    for (const [tc, name, output, success] of results) {
      session.contextManager.addMessage({
        role: "tool",
        content: output,
        tool_call_id: tc.id,
        name,
      });
      session.sendEvent({
        event_type: "tool_output",
        data: { tool: name, tool_call_id: tc.id, output, success },
      });
    }
  }

  // Handle rejected tools
  for (const [tc, name, feedback] of rejectedTasks) {
    const msg = `Job execution cancelled by user. User feedback: ${feedback}`;
    session.contextManager.addMessage({
      role: "tool",
      content: msg,
      tool_call_id: tc.id,
      name,
    });
    session.sendEvent({
      event_type: "tool_output",
      data: { tool: name, tool_call_id: tc.id, output: msg, success: false },
    });
  }

  // Continue agent loop
  await runAgentTurn(session, "");
}

export function undoSession(session: Session) {
  const removed = session.contextManager.undoLastTurn();
  session.sendEvent({ event_type: "undo_complete", data: { removed } });
}

export async function compactSession(session: Session) {
  await session.contextManager.compact(session.config);
  session.sendEvent({
    event_type: "compacted",
    data: {
      old_tokens: session.contextManager.runningContextUsage,
      new_tokens: session.contextManager.runningContextUsage,
    },
  });
}

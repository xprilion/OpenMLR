import OpenAI from "openai";
import { createAnthropic } from "@ai-sdk/anthropic";
import { generateText, streamText, type CoreMessage, type ToolSet } from "ai";
import type { AgentConfig } from "./config.js";
import type { Message, ToolCall } from "./types.js";

export interface LLMResult {
  content: string | null;
  toolCalls: ToolCall[];
  tokenCount: number;
  finishReason: string | null;
}

// ---- OpenAI-compatible (OpenAI + OpenRouter) ----
function getOpenAIClient(modelName: string): { client: OpenAI; modelId: string } {
  if (modelName.startsWith("openrouter/")) {
    const apiKey = process.env.OPENROUTER_API_KEY;
    if (!apiKey) throw new Error("OPENROUTER_API_KEY not set");
    return {
      client: new OpenAI({ apiKey, baseURL: "https://openrouter.ai/api/v1" }),
      modelId: modelName.replace("openrouter/", ""),
    };
  }

  const apiKey = process.env.OPENAI_API_KEY;
  if (!apiKey) throw new Error("OPENAI_API_KEY not set");
  const modelId = modelName.startsWith("openai/")
    ? modelName.replace("openai/", "")
    : modelName;
  return { client: new OpenAI({ apiKey }), modelId };
}

function toOpenAIMessages(messages: Message[]): any[] {
  return messages.map((m) => {
    if (m.role === "tool") {
      return {
        role: "tool",
        tool_call_id: m.tool_call_id || "",
        content: m.content,
      };
    }
    if (m.role === "assistant" && m.tool_calls) {
      return {
        role: "assistant",
        content: m.content || "",
        tool_calls: m.tool_calls.map((tc) => ({
          id: tc.id,
          type: "function",
          function: {
            name: tc.function.name,
            arguments: tc.function.arguments,
          },
        })),
      };
    }
    return { role: m.role, content: m.content };
  });
}

function toOpenAITools(toolSpecs: any[]): any[] {
  return toolSpecs.map((spec) => {
    const fn = spec.function || spec;
    return {
      type: "function",
      function: {
        name: fn.name,
        description: fn.description,
        parameters: fn.parameters,
      },
    };
  });
}

async function callOpenRouterOrOpenAI(
  messages: Message[],
  toolSpecs: any[],
  config: AgentConfig,
  onChunk?: (chunk: string) => void,
): Promise<LLMResult> {
  const { client, modelId } = getOpenAIClient(config.model_name);
  const openaiMessages = toOpenAIMessages(messages);
  const tools = toolSpecs.length > 0 ? toOpenAITools(toolSpecs) : undefined;

  if (config.stream && onChunk) {
    const stream = await client.chat.completions.create({
      model: modelId,
      messages: openaiMessages,
      tools,
      tool_choice: tools ? "auto" : undefined,
      stream: true,
    });

    let content = "";
    const toolCallsAcc = new Map<number, any>();

    for await (const chunk of stream) {
      const delta = chunk.choices[0]?.delta;
      if (delta?.content) {
        content += delta.content;
        onChunk(delta.content);
      }
      if (delta?.tool_calls) {
        for (const tc of delta.tool_calls) {
          const idx = tc.index || 0;
          if (!toolCallsAcc.has(idx)) {
            toolCallsAcc.set(idx, {
              id: tc.id || `call_${idx}`,
              type: "function",
              function: { name: tc.function?.name || "", arguments: "" },
            });
          }
          const existing = toolCallsAcc.get(idx);
          if (tc.function?.name) existing.function.name = tc.function.name;
          if (tc.function?.arguments) existing.function.arguments += tc.function.arguments;
        }
      }
    }

    const tokenCount = Math.ceil(
      messages.reduce((sum, m) => sum + (m.content?.length || 0), 0) / 5 +
      content.length / 5,
    );

    const toolCalls: ToolCall[] = [];
    for (const [idx] of [...toolCallsAcc.entries()].sort((a, b) => a[0] - b[0])) {
      const tc = toolCallsAcc.get(idx);
      if (tc && tc.function.name) toolCalls.push(tc);
    }

    return { content: content || null, toolCalls, tokenCount, finishReason: "stop" };
  } else {
    const response = await client.chat.completions.create({
      model: modelId,
      messages: openaiMessages,
      tools,
      tool_choice: tools ? "auto" : undefined,
    });

    const choice = response.choices[0];
    const content = choice?.message?.content || null;
    const toolCalls: ToolCall[] =
      choice?.message?.tool_calls?.map((tc: any) => ({
        id: tc.id,
        type: "function",
        function: {
          name: tc.function.name,
          arguments: tc.function.arguments,
        },
      })) || [];

    const tokenCount = Math.ceil(
      messages.reduce((sum, m) => sum + (m.content?.length || 0), 0) / 5 +
      (content?.length || 0) / 5,
    );

    return { content, toolCalls, tokenCount, finishReason: choice?.finish_reason || null };
  }
}

// ---- Anthropic via ai SDK ----
function toCoreMessages(messages: Message[]): CoreMessage[] {
  return messages.map((m) => {
    if (m.role === "tool") {
      return {
        role: "tool" as const,
        content: [
          {
            type: "tool-result" as const,
            toolCallId: m.tool_call_id || "",
            toolName: m.name || "",
            result: m.content,
            isError: false,
          },
        ],
      };
    }
    if (m.role === "assistant" && m.tool_calls) {
      return {
        role: "assistant" as const,
        content: m.tool_calls.map((tc) => ({
          type: "tool-call" as const,
          toolCallId: tc.id,
          toolName: tc.function.name,
          args: JSON.parse(tc.function.arguments || "{}"),
        })),
      };
    }
    return {
      role: m.role as "system" | "user" | "assistant",
      content: m.content,
    };
  });
}

function toAIToolSet(toolSpecs: any[]): ToolSet {
  const tools: ToolSet = {};
  for (const spec of toolSpecs) {
    const fn = spec.function || spec;
    tools[fn.name] = {
      description: fn.description,
      parameters: fn.parameters,
    };
  }
  return tools;
}

async function callAnthropic(
  messages: Message[],
  toolSpecs: any[],
  config: AgentConfig,
  onChunk?: (chunk: string) => void,
): Promise<LLMResult> {
  const apiKey = process.env.ANTHROPIC_API_KEY;
  if (!apiKey) throw new Error("ANTHROPIC_API_KEY not set");
  const anthropic = createAnthropic({ apiKey });
  const modelId = config.model_name.replace("anthropic/", "");
  const coreMessages = toCoreMessages(messages);
  const tools = toolSpecs.length > 0 ? toAIToolSet(toolSpecs) : undefined;

  if (config.stream && onChunk) {
    const result = await streamText({
      model: anthropic(modelId),
      messages: coreMessages,
      tools,
      maxSteps: 1,
    });

    let content = "";
    const toolCallsAcc = new Map<number, any>();

    for await (const part of result.fullStream) {
      if (part.type === "text-delta") {
        content += part.textDelta;
        onChunk(part.textDelta);
      } else if (part.type === "tool-call-delta") {
        const idx = parseInt(part.toolCallId.replace(/\D/g, ""), 10) || 0;
        if (!toolCallsAcc.has(idx)) {
          toolCallsAcc.set(idx, {
            id: part.toolCallId,
            type: "function",
            function: { name: part.toolName, arguments: "" },
          });
        }
        const tc = toolCallsAcc.get(idx);
        if (part.argsTextDelta) tc.function.arguments += part.argsTextDelta;
      } else if (part.type === "tool-call") {
        const idx = parseInt(part.toolCallId.replace(/\D/g, ""), 10) || 0;
        toolCallsAcc.set(idx, {
          id: part.toolCallId,
          type: "function",
          function: { name: part.toolName, arguments: JSON.stringify(part.args) },
        });
      }
    }

    const tokenCount = Math.ceil(
      messages.reduce((sum, m) => sum + (m.content?.length || 0), 0) / 5 +
      content.length / 5,
    );

    const toolCalls: ToolCall[] = [];
    for (const [idx] of [...toolCallsAcc.entries()].sort((a, b) => a[0] - b[0])) {
      const tc = toolCallsAcc.get(idx);
      if (tc) toolCalls.push(tc);
    }

    return { content: content || null, toolCalls, tokenCount, finishReason: "stop" };
  } else {
    const result = await generateText({
      model: anthropic(modelId),
      messages: coreMessages,
      tools,
      maxSteps: 1,
    });

    const toolCalls: ToolCall[] = result.toolCalls.map((tc) => ({
      id: tc.toolCallId,
      type: "function",
      function: { name: tc.toolName, arguments: JSON.stringify(tc.args) },
    }));

    const tokenCount = Math.ceil(
      messages.reduce((sum, m) => sum + (m.content?.length || 0), 0) / 5 +
      (result.text?.length || 0) / 5,
    );

    return { content: result.text || null, toolCalls, tokenCount, finishReason: result.finishReason };
  }
}

// ---- Public API ----
export async function callLLM(
  messages: Message[],
  toolSpecs: any[],
  config: AgentConfig,
  onChunk?: (chunk: string) => void,
): Promise<LLMResult> {
  if (config.model_name.startsWith("anthropic/")) {
    return callAnthropic(messages, toolSpecs, config, onChunk);
  }
  return callOpenRouterOrOpenAI(messages, toolSpecs, config, onChunk);
}

export async function summarizeMessages(
  messages: Message[],
  config: AgentConfig,
): Promise<string> {
  if (config.model_name.startsWith("anthropic/")) {
    return callAnthropic(messages, [], { ...config, stream: false }).then(
      (r) => r.content || "[Summary unavailable]"
    );
  }

  const { client, modelId } = getOpenAIClient(config.model_name);
  const prompt =
    messages.map((m) => `${m.role}: ${m.content}`).join("\n\n") +
    "\n\n" +
    "Please provide a concise summary of the conversation above, focusing on key decisions, the 'why' behind the decisions, problems solved, and important context needed for developing further.";

  const response = await client.chat.completions.create({
    model: modelId,
    messages: [{ role: "user", content: prompt }],
  });

  return response.choices[0]?.message?.content || "[Summary unavailable]";
}

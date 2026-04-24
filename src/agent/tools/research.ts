import { generateText } from "ai";
import { createOpenAI } from "@ai-sdk/openai";
import type { ToolSpec } from "../types.js";

async function braveSearch(query: string, limit: number): Promise<Array<{ title: string; url: string; snippet: string }>> {
  const apiKey = process.env.BRAVE_API_KEY;
  if (!apiKey) return [];

  const url = new URL("https://api.search.brave.com/res/v1/web/search");
  url.searchParams.set("q", query);
  url.searchParams.set("count", String(limit));
  url.searchParams.set("offset", "0");
  url.searchParams.set("safesearch", "off");

  const res = await fetch(url.toString(), {
    headers: {
      Accept: "application/json",
      "X-Subscription-Token": apiKey,
    },
  });

  if (!res.ok) return [];

  const data = await res.json();
  const out: Array<{ title: string; url: string; snippet: string }> = [];
  const webResults = data.web?.results || [];
  for (const r of webResults) {
    out.push({
      title: r.title || "",
      url: r.url || "",
      snippet: r.description || "",
    });
  }
  return out;
}

async function researchHandler(args: Record<string, any>): Promise<[string, boolean]> {
  const task = args.task || "";
  const context = args.context || "";
  if (!task) return ["No research task provided.", false];

  try {
    const links = await braveSearch(task, 8);

    if (links.length === 0) {
      return ["No research results found for this task.", false];
    }

    const apiKey = process.env.OPENAI_API_KEY;
    if (!apiKey) {
      const formatted = links.map((l, i) => `${i + 1}. ${l.title}\n   ${l.url}\n   ${l.snippet}`).join("\n\n");
      return [formatted, true];
    }

    const openai = createOpenAI({ apiKey });
    const searchContext = links.map((l) => `Title: ${l.title}\nURL: ${l.url}\nSnippet: ${l.snippet}`).join("\n\n");

    const prompt = `You are a research sub-agent. The main agent needs concise, actionable findings on this task:\n\nTASK: ${task}\n${context ? `CONTEXT: ${context}\n` : ""}\n\nHere are web search results:\n\n${searchContext}\n\nPlease summarize the key findings in 3-5 bullet points. Focus on:\n- Working code examples or patterns found\n- Key APIs or libraries to use\n- Important gotchas or version issues\n- Direct links to the most relevant resources\n\nBe concise and specific.`;

    const result = await generateText({
      model: openai("gpt-4o-mini"),
      messages: [{ role: "user", content: prompt }],
    });

    return [result.text || "Research completed but no summary generated.", true];
  } catch (e: any) {
    return [`Research error: ${e.message}`, false];
  }
}

export const researchToolSpec: ToolSpec = {
  name: "research",
  description:
    "Spawn a research sub-agent to explore documentation, codebases, or repos WITHOUT polluting the main conversation context. " +
    "The sub-agent gets its own independent context and returns a concise summary of findings.\n\n" +
    "Use this for:\n" +
    "- Researching current API usage before implementing ML tasks\n" +
    "- Exploring docs, reading papers, analyzing GitHub repos\n" +
    "- Any research where raw tool outputs would be too verbose",
  parameters: {
    type: "object",
    required: ["task"],
    additionalProperties: false,
    properties: {
      task: {
        type: "string",
        description:
          "Detailed description of what to research. Be specific: include library names, trainer types, dataset names, repo names.",
      },
      context: {
        type: "string",
        description: "Optional context from the current conversation that the research agent needs.",
      },
    },
  },
  handler: researchHandler,
};

import { generateText } from "ai";
import { createOpenAI } from "@ai-sdk/openai";
import type { ToolSpec } from "../types.js";

async function researchHandler(args: Record<string, any>): Promise<[string, boolean]> {
  const task = args.task || "";
  const context = args.context || "";
  if (!task) return ["No research task provided.", false];

  try {
    // Step 1: Web search for the task
    const searchQuery = `${task} site:github.com OR site:huggingface.co documentation example`;
    const searchUrl = `https://html.duckduckgo.com/html/?q=${encodeURIComponent(searchQuery)}`;
    const res = await fetch(searchUrl, {
      headers: { "User-Agent": "Mozilla/5.0 (compatible; Bot/0.1)" },
    });
    const html = await res.text();

    const links: Array<{ title: string; url: string; snippet: string }> = [];
    const linkRegex = /<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)<\/a>/g;
    const snippetRegex = /<a[^>]+class="result__snippet"[^>]*>(.*?)<\/a>/g;

    let linkMatch;
    const rawLinks: Array<{ title: string; url: string }> = [];
    while ((linkMatch = linkRegex.exec(html)) !== null) {
      let title = linkMatch[2].replace(/<[^>]+>/g, "").trim();
      let url = linkMatch[1];
      const uMatch = url.match(/uddg=([^&]+)/);
      if (uMatch) {
        try { url = decodeURIComponent(uMatch[1]); } catch { /* keep */ }
      }
      rawLinks.push({ title, url });
    }

    let snippetMatch;
    const rawSnippets: string[] = [];
    while ((snippetMatch = snippetRegex.exec(html)) !== null) {
      rawSnippets.push(snippetMatch[1].replace(/<[^>]+>/g, "").trim());
    }

    for (let i = 0; i < Math.min(rawLinks.length, rawSnippets.length, 8); i++) {
      links.push({ ...rawLinks[i], snippet: rawSnippets[i] });
    }

    if (links.length === 0) {
      return ["No research results found for this task.", false];
    }

    // Step 2: Summarize with a cheap LLM call
    const apiKey = process.env.OPENAI_API_KEY;
    if (!apiKey) {
      // Fallback: just return raw links
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

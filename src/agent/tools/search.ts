import type { ToolSpec } from "../types.js";

async function webSearchHandler(args: Record<string, any>): Promise<[string, boolean]> {
  const query = args.query || "";
  if (!query) return ["No query provided.", false];

  const apiKey = process.env.BRAVE_API_KEY;
  if (!apiKey) {
    return ["BRAVE_API_KEY is not set in the environment.", false];
  }

  try {
    const limit = Math.min(Math.max(args.limit || 10, 1), 20);
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

    if (!res.ok) {
      const body = await res.text();
      return [`Brave Search API error (${res.status}): ${body}`, false];
    }

    const data = await res.json();
    const results: string[] = [];

    const webResults = data.web?.results || [];
    for (let i = 0; i < webResults.length; i++) {
      const r = webResults[i];
      results.push(`${i + 1}. ${r.title}\n   ${r.url}\n   ${r.description || ""}`);
    }

    if (results.length === 0) {
      return ["No search results found.", false];
    }

    return [results.join("\n\n"), true];
  } catch (e: any) {
    return [`Web search error: ${e.message}`, false];
  }
}

export const webSearchToolSpec: ToolSpec = {
  name: "web_search",
  description:
    "Search the web using Brave Search. Returns title, URL, and snippet for each result. " +
    "Use for finding documentation, examples, papers, or current information.",
  parameters: {
    type: "object",
    required: ["query"],
    additionalProperties: false,
    properties: {
      query: { type: "string", description: "Search query." },
      limit: { type: "integer", description: "Max results (default: 10, max: 20)." },
    },
  },
  handler: webSearchHandler,
};

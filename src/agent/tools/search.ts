import type { ToolSpec } from "../types.js";

async function webSearchHandler(args: Record<string, any>): Promise<[string, boolean]> {
  const query = args.query || "";
  if (!query) return ["No query provided.", false];

  try {
    // Use DuckDuckGo HTML lite
    const url = `https://html.duckduckgo.com/html/?q=${encodeURIComponent(query)}`;
    const res = await fetch(url, {
      headers: {
        "User-Agent": "Mozilla/5.0 (compatible; Bot/0.1)",
      },
    });
    const html = await res.text();

    // Extract results using regex
    const results: string[] = [];
    const linkRegex = /<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)<\/a>/g;
 const snippetRegex = /<a[^>]+class="result__snippet"[^>]*>(.*?)<\/a>/g;

    let linkMatch;
    let snippetMatch;
    const links: Array<{ title: string; url: string }> = [];
    const snippets: string[] = [];

    while ((linkMatch = linkRegex.exec(html)) !== null) {
      let title = linkMatch[2].replace(/<[^>]+>/g, "").trim();
      let url = linkMatch[1];
      // DuckDuckGo redirects through their server
      const uMatch = url.match(/uddg=([^&]+)/);
      if (uMatch) {
        try {
          url = decodeURIComponent(uMatch[1]);
        } catch {
          // keep original
        }
      }
      links.push({ title, url });
    }

    while ((snippetMatch = snippetRegex.exec(html)) !== null) {
      snippets.push(snippetMatch[1].replace(/<[^>]+>/g, "").trim());
    }

    const limit = args.limit || 10;
    for (let i = 0; i < Math.min(links.length, snippets.length, limit); i++) {
      results.push(`${i + 1}. ${links[i].title}\n   ${links[i].url}\n   ${snippets[i]}`);
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
    "Search the web using DuckDuckGo. Returns title, URL, and snippet for each result. " +
    "Use for finding documentation, examples, papers, or current information.",
  parameters: {
    type: "object",
    required: ["query"],
    additionalProperties: false,
    properties: {
      query: { type: "string", description: "Search query." },
      limit: { type: "integer", description: "Max results (default: 10)." },
    },
  },
  handler: webSearchHandler,
};

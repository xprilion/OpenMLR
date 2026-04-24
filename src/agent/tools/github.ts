import type { ToolSpec } from "../types.js";

const GITHUB_TOKEN = process.env.GITHUB_TOKEN;

async function githubFetch(url: string): Promise<any> {
  const headers: Record<string, string> = {
    Accept: "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
  };
  if (GITHUB_TOKEN) {
    headers.Authorization = `Bearer ${GITHUB_TOKEN}`;
  }
  const res = await fetch(url, { headers });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`GitHub API ${res.status}: ${text}`);
  }
  return res.json();
}

async function githubReadFileHandler(args: Record<string, any>): Promise<[string, boolean]> {
  const repo = args.repo;
  const path = args.path;
  const ref = args.ref || "HEAD";
  if (!repo || !path) return ["Missing required arguments: repo, path", false];

  try {
    const data = await githubFetch(
      `https://api.github.com/repos/${repo}/contents/${path}?ref=${ref}`,
    );
    if (data.type !== "file") return [`Not a file: ${path}`, false];

    const content = Buffer.from(data.content, "base64").toString("utf-8");
    const lines = content.split("\n");
    const lineStart = args.line_start ? Math.max(args.line_start - 1, 0) : 0;
    const lineEnd = args.line_end ? Math.min(args.line_end, lines.length) : Math.min(300, lines.length);
    const selected = lines.slice(lineStart, lineEnd);

    const header = `// ${repo}/${path}${ref !== "HEAD" ? ` @ ${ref}` : ""} (${selected.length}/${lines.length} lines)\n`;
    return [header + selected.join("\n"), true];
  } catch (e: any) {
    return [`GitHub error: ${e.message}`, false];
  }
}

async function githubListReposHandler(args: Record<string, any>): Promise<[string, boolean]> {
  const owner = args.owner;
  const ownerType = args.owner_type || "org";
  const sort = args.sort || "stars";
  const order = args.order || "desc";
  const limit = args.limit || 30;
  if (!owner) return ["Missing required argument: owner", false];

  try {
    const endpoint = ownerType === "org"
      ? `https://api.github.com/orgs/${owner}/repos`
      : `https://api.github.com/users/${owner}/repos`;

    let allRepos: any[] = [];
    let page = 1;
    while (allRepos.length < limit && page <= 10) {
      const data = await githubFetch(`${endpoint}?per_page=100&page=${page}`);
      if (!Array.isArray(data) || data.length === 0) break;
      allRepos = allRepos.concat(data);
      page++;
    }

    allRepos = allRepos.slice(0, limit);

    if (sort === "stars" || sort === "forks") {
      allRepos.sort((a, b) => {
        const diff = (b[sort] || 0) - (a[sort] || 0);
        return order === "asc" ? -diff : diff;
      });
    }

    const lines = allRepos.map((r) => {
      const stars = (r.stargazers_count || 0).toLocaleString();
      const forks = (r.forks_count || 0).toLocaleString();
      const lang = r.language || "N/A";
      return `${r.full_name} | ⭐ ${stars} | 🍴 ${forks} | ${lang} | ${r.description || ""}`;
    });

    return [lines.join("\n"), true];
  } catch (e: any) {
    return [`GitHub error: ${e.message}`, false];
  }
}

async function githubFindExamplesHandler(args: Record<string, any>): Promise<[string, boolean]> {
  const repo = args.repo;
  const org = args.org || "huggingface";
  const keyword = args.keyword || "";
  const maxResults = args.max_results || 50;
  const minScore = args.min_score || 60;
  if (!repo) return ["Missing required argument: repo", false];

  try {
    const treeData = await githubFetch(
      `https://api.github.com/repos/${org}/${repo}/git/trees/HEAD?recursive=1`,
    );
    if (!treeData.tree) return ["Could not fetch repository tree", false];

    const patterns = [
      "scripts", "examples", "example", "notebooks", "notebook",
      "tutorials", "tutorial", "quickstart", "cookbook", "recipes",
      "demos", "demo", "samples", "sample", "guides", "guide",
    ];

    const scored = treeData.tree
      .filter((f: any) => f.type === "blob")
      .map((f: any) => {
        const path = f.path.toLowerCase();
        let score = 0;
        for (const p of patterns) {
          if (path.includes(p)) score += 30;
        }
        if (keyword) {
          if (path.includes(keyword.toLowerCase())) score += 50;
          // Fuzzy-ish: check if keyword chars appear in order
          let ki = 0;
          for (const ch of path) {
            if (ch === keyword[ki]?.toLowerCase()) ki++;
          }
          if (ki >= keyword.length) score += 20;
        }
        return { path: f.path, score };
      })
      .filter((f: any) => f.score >= minScore)
      .sort((a: any, b: any) => b.score - a.score)
      .slice(0, maxResults);

    if (scored.length === 0) {
      return [`No example files found matching '${keyword}' in ${org}/${repo}`, false];
    }

    const lines = scored.map((f: any) => `${f.path} (score: ${f.score})`);
    return [lines.join("\n"), true];
  } catch (e: any) {
    return [`GitHub error: ${e.message}`, false];
  }
}

export const githubToolSpecs: ToolSpec[] = [
  {
    name: "github_read_file",
    description:
      "Read file contents from GitHub repositories. Returns first 300 lines by default. " +
      "Use AFTER github_find_examples to study the working implementation. " +
      "Use line_start/line_end for large files.",
    parameters: {
      type: "object",
      required: ["repo", "path"],
      additionalProperties: false,
      properties: {
        repo: { type: "string", description: "Repository in format 'owner/repo'." },
        path: { type: "string", description: "Path to file in repository." },
        ref: { type: "string", description: "Git reference (branch/tag/SHA). Default: HEAD." },
        line_start: { type: "integer", description: "Starting line (1-indexed)." },
        line_end: { type: "integer", description: "Ending line (1-indexed)." },
      },
    },
    handler: githubReadFileHandler,
  },
  {
    name: "github_list_repos",
    description:
      "List and discover repositories for GitHub organizations or users. " +
      "Use when exploring what libraries exist for a task or finding popular projects.",
    parameters: {
      type: "object",
      required: ["owner"],
      additionalProperties: false,
      properties: {
        owner: { type: "string", description: "GitHub username or organization name." },
        owner_type: { type: "string", enum: ["user", "org"], description: "Owner type." },
        sort: { type: "string", enum: ["stars", "forks", "updated", "created"], description: "Sort field." },
        order: { type: "string", enum: ["asc", "desc"], description: "Sort order." },
        limit: { type: "integer", description: "Max results." },
      },
    },
    handler: githubListReposHandler,
  },
  {
    name: "github_find_examples",
    description:
      "Find working example scripts in GitHub repositories. " +
      "MANDATORY before writing any ML training, fine-tuning, or inference code. " +
      "Sequence: github_find_examples → github_read_file → implement.",
    parameters: {
      type: "object",
      required: ["repo"],
      additionalProperties: false,
      properties: {
        repo: { type: "string", description: "Repository name (e.g., 'trl')." },
        org: { type: "string", description: "GitHub organization. Default: 'huggingface'." },
        keyword: { type: "string", description: "Keyword to fuzzy match against file paths." },
        max_results: { type: "integer", description: "Max results. Default: 50." },
        min_score: { type: "integer", description: "Minimum match score. Default: 60." },
      },
    },
    handler: githubFindExamplesHandler,
  },
];

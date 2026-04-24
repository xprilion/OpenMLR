import { execSync } from "child_process";
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "fs";
import { tmpdir } from "os";
import { dirname, resolve } from "path";
import type { ToolSpec } from "../types.js";

const MAX_OUTPUT_CHARS = 25_000;
const DEFAULT_READ_LINES = 2000;
const MAX_LINE_LENGTH = 4000;
const DEFAULT_TIMEOUT = 120;
const MAX_TIMEOUT = 36000;

const ANSI_RE = /\x1b\[[0-9;]*[a-zA-Z]|\x1b\].*?\x07/g;

const filesRead = new Set<string>();

function resolvePath(p: string): string {
  try {
    return resolve(p);
  } catch {
    return p;
  }
}

function stripAnsi(text: string): string {
  return text.replace(ANSI_RE, "");
}

function truncateOutput(output: string, maxChars = MAX_OUTPUT_CHARS): string {
  if (output.length <= maxChars) return output;
  const headBudget = Math.floor(maxChars * 0.25);
  const tailBudget = maxChars - headBudget;
  const head = output.slice(0, headBudget);
  const tail = output.slice(-tailBudget);
  const omitted = output.length - maxChars;
  return (
    head +
    `\n\n... (${omitted.toLocaleString()} of ${output.length.toLocaleString()} chars omitted) ...\n` +
    tail
  );
}

async function bashHandler(args: Record<string, any>): Promise<[string, boolean]> {
  const command = args.command || "";
  if (!command) return ["No command provided.", false];
  const workDir = args.work_dir || ".";
  const timeout = Math.min(args.timeout || DEFAULT_TIMEOUT, MAX_TIMEOUT);

  try {
    const result = execSync(command, {
      cwd: workDir,
      encoding: "utf-8",
      timeout: timeout * 1000,
      maxBuffer: 10 * 1024 * 1024,
    });
    const output = stripAnsi(result);
    const truncated = truncateOutput(output);
    return [truncated || "(no output)", true];
  } catch (e: any) {
    if (e.signal === "SIGTERM") {
      return [
        `Command timed out after ${timeout}s and was killed.\n\n` +
          `For long-running commands, run in the background and poll:\n` +
          `  nohup <command> > /tmp/output.log 2>&1 & echo $!`,
        false,
      ];
    }
    const stderr = stripAnsi(e.stderr || "");
    const stdout = stripAnsi(e.stdout || "");
    const output = truncateOutput(stdout + stderr);
    return [output || e.message || "Command failed", false];
  }
}

async function readHandler(args: Record<string, any>): Promise<[string, boolean]> {
  const filePath = args.path || "";
  if (!filePath) return ["No path provided.", false];
  const p = resolvePath(filePath);
  if (!existsSync(p)) return [`File not found: ${filePath}`, false];

  try {
    const stat = require("fs").statSync(p);
    if (stat.isDirectory()) return ["Cannot read a directory. Use bash with 'ls' instead.", false];
  } catch {
    return [`read error: could not stat ${filePath}`, false];
  }

  try {
    const rawContent = readFileSync(p, "utf-8");
    filesRead.add(p);

    const lines = rawContent.split("\n");
    const offset = Math.max((args.offset || 1) - 1, 0);
    const limit = args.limit || DEFAULT_READ_LINES;
    const selected = lines.slice(offset, offset + limit);
    const numbered = selected.map((line, i) => {
      const num = offset + i + 1;
      const truncated =
        line.length > MAX_LINE_LENGTH ? line.slice(0, MAX_LINE_LENGTH) + "..." : line;
      return `${num.toString().padStart(6)}\t${truncated}`;
    });

    return [numbered.join("\n"), true];
  } catch (e: any) {
    return [`read error: ${e.message}`, false];
  }
}

async function writeHandler(args: Record<string, any>): Promise<[string, boolean]> {
  const filePath = args.path || "";
  const content = args.content || "";
  if (!filePath) return ["No path provided.", false];
  const p = resolvePath(filePath);

  if (existsSync(p) && !filesRead.has(p)) {
    return [
      `You must read ${filePath} before overwriting it. Use the read tool first to see current contents.`,
      false,
    ];
  }

  try {
    mkdirSync(dirname(p), { recursive: true });
    writeFileSync(p, content, "utf-8");
    filesRead.add(p);
    return [`Wrote ${content.length} bytes to ${filePath}`, true];
  } catch (e: any) {
    return [`write error: ${e.message}`, false];
  }
}

async function editHandler(args: Record<string, any>): Promise<[string, boolean]> {
  const filePath = args.path || "";
  const oldStr = args.old_str || "";
  const newStr = args.new_str ?? "";
  const replaceAll = args.replace_all || false;

  if (!filePath) return ["No path provided.", false];
  if (oldStr === newStr) return ["old_str and new_str must differ.", false];

  const p = resolvePath(filePath);
  if (!existsSync(p)) return [`File not found: ${filePath}`, false];
  if (!filesRead.has(p)) {
    return [
      `You must read ${filePath} before editing it. Use the read tool first to see current contents.`,
      false,
    ];
  }

  try {
    let text = readFileSync(p, "utf-8");
    let count = 0;

    if (replaceAll) {
      const regex = new RegExp(oldStr.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"), "g");
      const matches = text.match(regex);
      count = matches ? matches.length : 0;
      text = text.replace(regex, newStr);
    } else {
      const idx = text.indexOf(oldStr);
      if (idx === -1) {
        return [
          `Could not find the text to replace in ${filePath}. The edit will FAIL if old_str is not unique. Provide a larger string with more surrounding context to make it unique, or set replace_all to true.`,
          false,
        ];
      }
      const secondIdx = text.indexOf(oldStr, idx + 1);
      if (secondIdx !== -1) {
        return [
          `old_str appears multiple times in ${filePath}. Provide a larger string with more surrounding context to make it unique, or set replace_all to true.`,
          false,
        ];
      }
      text = text.slice(0, idx) + newStr + text.slice(idx + oldStr.length);
      count = 1;
    }

    writeFileSync(p, text, "utf-8");
    return [`Edited ${filePath} (${count} replacement${count > 1 ? "s" : ""})`, true];
  } catch (e: any) {
    return [`edit error: ${e.message}`, false];
  }
}

export const localToolSpecs: ToolSpec[] = [
  {
    name: "bash",
    description:
      "Run a shell command on the local machine and return stdout/stderr.\n\n" +
      "IMPORTANT: Do NOT use bash for file operations — use the dedicated tools instead:\n" +
      "- To read files: use read (not cat/head/tail)\n" +
      "- To edit files: use edit (not sed/awk)\n" +
      "- To write files: use write (not echo/cat <<EOF)\n\n" +
      "Commands run in a shell at the working directory. Each invocation is independent. " +
      "Chain dependent commands with &&. Independent commands should be separate bash calls.\n\n" +
      "For long-running commands (training, evaluation), run in the background and poll:\n" +
      "  nohup <command> > /tmp/output.log 2>&1 & echo $!",
    parameters: {
      type: "object",
      required: ["command"],
      additionalProperties: false,
      properties: {
        command: { type: "string", description: "The shell command to execute." },
        description: { type: "string", description: "Short description (5-10 words, active voice)." },
        work_dir: { type: "string", description: "Working directory (default: current directory)." },
        timeout: { type: "integer", description: "Optional timeout in seconds (default: 120, max: 36000)." },
      },
    },
    handler: bashHandler,
  },
  {
    name: "read",
    description:
      "Reads a file from the local filesystem. Returns contents with line numbers.\n\n" +
      "Usage:\n" +
      "- By default, reads up to 2000 lines from the beginning of the file.\n" +
      "- You can optionally specify offset and limit for large files.\n" +
      "- Lines longer than 4000 chars are truncated.\n" +
      "- Cannot read directories — use bash with 'ls' instead.\n" +
      "- IMPORTANT: Always read a file before editing or overwriting it.",
    parameters: {
      type: "object",
      required: ["path"],
      additionalProperties: false,
      properties: {
        path: { type: "string", description: "Absolute path to the file to read." },
        offset: { type: "integer", description: "The line number to start reading from (1-based)." },
        limit: { type: "integer", description: "The number of lines to read." },
      },
    },
    handler: readHandler,
  },
  {
    name: "write",
    description:
      "Writes a file to the local filesystem. Overwrites the existing file if one exists.\n\n" +
      "- If this is an existing file, you MUST use the read tool first.\n" +
      "- ALWAYS prefer editing existing files with the edit tool over overwriting.\n" +
      "- Creates parent directories as needed.",
    parameters: {
      type: "object",
      required: ["path", "content"],
      additionalProperties: false,
      properties: {
        path: { type: "string", description: "Absolute path to the file to write." },
        content: { type: "string", description: "The complete file content to write." },
      },
    },
    handler: writeHandler,
  },
  {
    name: "edit",
    description:
      "Performs string replacements in files.\n\n" +
      "Usage:\n" +
      "- You must read the file at least once before editing.\n" +
      "- The edit will FAIL if old_str is not unique. Provide a larger string or set replace_all.\n" +
      "- old_str and new_str must differ.\n" +
      "- Preserve indentation exactly.\n" +
      "- Do NOT include line number prefixes from read output in old_str or new_str.",
    parameters: {
      type: "object",
      required: ["path", "old_str", "new_str"],
      additionalProperties: false,
      properties: {
        path: { type: "string", description: "Absolute path to the file to edit." },
        old_str: { type: "string", description: "The text to find." },
        new_str: { type: "string", description: "The replacement text." },
        replace_all: { type: "boolean", description: "Replace all occurrences (default: false).", default: false },
      },
    },
    handler: editHandler,
  },
];

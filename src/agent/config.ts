import { existsSync, readFileSync } from "fs";
import { join } from "path";
import { loadProjectConfig } from "../project-config.js";

export interface AgentConfig {
  model_name: string;
  max_iterations: number;
  stream: boolean;
  yolo_mode: boolean;
  compact_threshold_ratio: number;
  untouched_messages: number;
  default_max_tokens: number;
}

const DEFAULT_CONFIG: AgentConfig = {
  model_name: process.env.OPEN_MLR_MODEL || process.env.ML_INTERN_MODEL || "openai/gpt-4o",
  max_iterations: -1,
  stream: true,
  yolo_mode: false,
  compact_threshold_ratio: 0.75,
  untouched_messages: 5,
  default_max_tokens: 200_000,
};

export function loadConfig(path?: string): AgentConfig {
  // 1. Start with defaults
  let config: AgentConfig = { ...DEFAULT_CONFIG };

  // 2. Apply legacy global config if present
  const globalPath = join(process.cwd(), "configs", "main_agent_config.json");
  if (existsSync(globalPath)) {
    try {
      const raw = readFileSync(globalPath, "utf-8");
      const parsed = JSON.parse(raw);
      config = { ...config, ...parsed };
    } catch {
      // fall through
    }
  }

  // 3. Apply project-local config (overrides global)
  const projectConfig = loadProjectConfig();
  if (projectConfig.model_name) {
    config.model_name = projectConfig.model_name;
  }

  // 4. Apply explicit path if provided (highest priority)
  if (path && existsSync(path)) {
    try {
      const raw = readFileSync(path, "utf-8");
      const parsed = JSON.parse(raw);
      config = { ...config, ...parsed };
    } catch {
      // fall through
    }
  }

  return config;
}

export function getModelMaxTokens(modelName: string): number {
  // Rough mapping for common models
  const known: Record<string, number> = {
    "gpt-4o": 128_000,
    "gpt-4o-mini": 128_000,
    "gpt-4-turbo": 128_000,
    "gpt-4": 8_192,
    "claude-sonnet-4": 200_000,
    "claude-opus-4": 200_000,
    "claude-sonnet-4-5": 200_000,
    "claude-3-5-sonnet": 200_000,
    "claude-3-opus": 200_000,
  };
  const bare = modelName.replace(/^\w+\//, "").toLowerCase();
  for (const [k, v] of Object.entries(known)) {
    if (bare.includes(k)) return v;
  }
  return DEFAULT_CONFIG.default_max_tokens;
}

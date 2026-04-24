import { existsSync, readFileSync, writeFileSync } from "fs";
import { join } from "path";

export interface ProjectConfig {
  model_name?: string;
  [key: string]: any;
}

const CONFIG_FILENAME = ".open-mlr.config.json";

function getConfigPath(): string {
  return join(process.cwd(), CONFIG_FILENAME);
}

export function loadProjectConfig(): ProjectConfig {
  const path = getConfigPath();
  if (existsSync(path)) {
    try {
      const raw = readFileSync(path, "utf-8");
      return JSON.parse(raw) as ProjectConfig;
    } catch {
      return {};
    }
  }
  return {};
}

export function saveProjectConfig(updates: Partial<ProjectConfig>): void {
  const path = getConfigPath();
  const current = loadProjectConfig();
  const next = { ...current, ...updates };
  writeFileSync(path, JSON.stringify(next, null, 2) + "\n", "utf-8");
}

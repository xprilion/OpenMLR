import { localToolSpecs } from "./local.js";
import { githubToolSpecs } from "./github.js";
import { webSearchToolSpec } from "./search.js";
import { researchToolSpec } from "./research.js";
import { planToolSpec } from "./plan.js";
import type { ToolSpec } from "../types.js";

export function getAllTools(): ToolSpec[] {
  return [
    researchToolSpec,
    planToolSpec,
    ...githubToolSpecs,
    ...localToolSpecs,
    webSearchToolSpec,
  ];
}

export * from "./local.js";
export * from "./github.js";
export * from "./search.js";
export * from "./research.js";
export * from "./plan.js";

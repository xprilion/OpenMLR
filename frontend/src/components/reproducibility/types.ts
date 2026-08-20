export type ChecklistVenue = 'neurips' | 'icml' | 'iclr' | 'cvpr' | 'general';
export type CheckStatus = 'pass' | 'warn' | 'fail' | 'skip';
export type CheckSeverity = 'critical' | 'high' | 'medium' | 'low';
export type CheckCategory = 'determinism' | 'environment' | 'hardware' | 'dataset' | 'hyperparameters' | 'checkpoints';

export interface CheckItem {
  id: string;
  category: CheckCategory;
  title: string;
  description: string;
  status: CheckStatus;
  severity: CheckSeverity;
  details: string;
  remediation?: string;
}

export interface CategoryScore {
  category: CheckCategory;
  score: number;
  passed_checks: number;
  total_checks: number;
  status: CheckStatus;
}

export interface ReproducibilityAuditReport {
  id: string;
  project_id?: string;
  created_at: string;
  overall_score: number;
  grade: string;
  venue: ChecklistVenue;
  categories: CategoryScore[];
  checklist: CheckItem[];
  detected_frameworks: string[];
  seeds_detected: Record<string, number | string>;
  cuda_requirements: Record<string, unknown>;
  dockerfile_recipe: string;
  conda_recipe: string;
  latex_appendix: string;
  badge_markdown: string;
  badge_svg: string;
}

export interface AuditCodebaseRequest {
  target_path: string;
  venue: ChecklistVenue;
  framework_hint?: string;
  code_snippets?: Record<string, string>;
}

export type SignificanceLevel = '***' | '**' | '*' | '.' | 'ns';
export type HypothesisTestType = 'student_t' | 'welch_t' | 'mann_whitney' | 'bootstrap';
export type CorrectionMethod = 'holm_bonferroni' | 'benjamini_hochberg' | 'none';
export type VariantType = 'baseline' | 'ablation' | 'addition' | 'modification';

export interface MetricAggregate {
  count: number;
  mean: number;
  std: number;
  median: number;
  iqr: number;
  min_val: number;
  max_val: number;
  ci_lower: number;
  ci_upper: number;
}

export interface VariantResult {
  name: string;
  variant_type: VariantType;
  description: string;
  removed_components: string[];
  added_components: string[];
  metrics: Record<string, MetricAggregate>;
  raw_seed_values: Record<string, number[]>;
  run_ids: string[];
}

export interface SignificanceComparison {
  variant_name: string;
  metric_name: string;
  baseline_mean: number;
  variant_mean: number;
  delta_abs: number;
  delta_pct: number;
  t_stat: number;
  p_value: number;
  p_value_adjusted: number;
  effect_size_cohen_d: number;
  effect_size_hedges_g: number;
  ci_diff_lower: number;
  ci_diff_upper: number;
  significance_symbol: SignificanceLevel;
  test_type: HypothesisTestType;
  is_statistically_significant: boolean;
}

export interface ComponentImpact {
  component_name: string;
  impact_score: number;
  relative_drop_pct: number;
  is_critical: boolean;
  recommendation: string;
}

export interface AblationStudy {
  id: string;
  title: string;
  description: string;
  project_id?: string | null;
  primary_metric: string;
  higher_is_better: boolean;
  baseline_variant_name: string;
  variants: Record<string, VariantResult>;
  comparisons: Record<string, SignificanceComparison[]>;
  component_impacts: ComponentImpact[];
  narrative_summary: string;
  created_at: string;
  updated_at: string;
}

export interface CreateStudyRequest {
  id?: string;
  title: string;
  description?: string;
  project_id?: string | null;
  primary_metric?: string;
  higher_is_better?: boolean;
  baseline_variant_name?: string;
  baseline_description?: string;
}

export interface RecordRunsRequest {
  variant_name: string;
  variant_type?: VariantType;
  description?: string;
  removed_components?: string[];
  added_components?: string[];
  metrics: Record<string, number[]>;
  run_ids?: string[];
}

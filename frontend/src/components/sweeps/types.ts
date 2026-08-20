export type ParamType = 'categorical' | 'uniform' | 'loguniform' | 'int_uniform' | 'choice';

export interface ParameterSpec {
  name: string;
  param_type: ParamType;
  min_val?: number;
  max_val?: number;
  step?: number;
  choices?: (string | number)[];
  default?: string | number;
}

export interface EarlyStoppingConfig {
  enabled: boolean;
  min_steps: number;
  reduction_factor: number;
  metric_threshold?: number;
}

export interface Trial {
  trial_id: string;
  sweep_id: string;
  trial_number: number;
  parameters: Record<string, string | number>;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'pruned';
  metrics: Record<string, number>;
  objective_value?: number;
  step_history?: { step: number; [key: string]: number }[];
  started_at: number;
  completed_at?: number;
  error_message?: string;
  duration_seconds: number;
}

export interface SweepConfig {
  sweep_id: string;
  project_id: string;
  name: string;
  description: string;
  method: 'grid' | 'random' | 'bayesian' | 'hyperband';
  objective_metric: string;
  goal: 'minimize' | 'maximize';
  max_trials: number;
  parameters: Record<string, ParameterSpec>;
  early_stopping: EarlyStoppingConfig;
  trials: Trial[];
  status: 'active' | 'completed' | 'archived';
  created_at: number;
  updated_at: number;
}

export interface SweepAnalysis {
  sweep_id: string;
  status: string;
  total_trials: number;
  completed_trials: number;
  best_trial?: Trial;
  best_parameters?: Record<string, string | number>;
  best_metric_value?: number;
  parameter_importance: Record<string, number>;
  correlations: Record<string, number>;
  pareto_frontier: Trial[];
}

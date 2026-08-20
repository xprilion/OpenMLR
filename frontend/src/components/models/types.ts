export type FrameworkType = 'pytorch' | 'safetensors' | 'jax' | 'onnx' | 'gguf' | 'huggingface' | 'tensorrt';

export type TaskType =
  | 'causal_lm'
  | 'seq2seq'
  | 'classification'
  | 'object_detection'
  | 'segmentation'
  | 'diffusion'
  | 'embedding'
  | 'reinforcement_learning'
  | 'custom';

export type ModelStatus = 'draft' | 'training' | 'evaluated' | 'production' | 'archived';

export interface ModelArtifact {
  id: string;
  project_id: string;
  name: string;
  version: string;
  architecture: string;
  framework: FrameworkType;
  task_type: TaskType;
  status: ModelStatus;
  created_at: string;
  updated_at: string;
  description?: string;
  parameters_count: number;
  model_size_mb: number;
  checkpoint_path?: string;
  base_model?: string;
  tags: string[];
  metrics: Record<string, number>;
  hyperparameters: Record<string, unknown>;
  lineage: Record<string, unknown>;
  metadata: Record<string, unknown>;
}

export interface CheckpointInspection {
  file_format: string;
  total_parameters: number;
  trainable_parameters: number;
  total_size_mb: number;
  estimated_vram_fp32_mb: number;
  estimated_vram_fp16_mb: number;
  estimated_vram_int8_mb: number;
  estimated_vram_int4_mb: number;
  dtype_breakdown: Record<string, number>;
  layers_count: number;
  top_layers: Array<{ name: string; params: number; dtype: string }>;
  has_optimizer_state: boolean;
  metadata: Record<string, unknown>;
}

export interface QuantizationEstimate {
  target_precision: string;
  estimated_size_mb: number;
  estimated_vram_mb: number;
  compression_ratio: number;
  expected_latency_speedup: number;
  suggested_engine: string;
  loss_tolerance_level: string;
}

export interface ModelCardData {
  model_name: string;
  version: string;
  markdown: string;
  latex: string;
  bibtex: string;
  co2_emissions_kg: number;
  summary: {
    parameters: number;
    size_mb: number;
    architecture: string;
    framework: string;
    co2_kg: number;
  };
}

export interface ModelComparisonResult {
  compared_models: ModelArtifact[];
  metric_matrix: Record<string, Record<string, number | null>>;
  parameter_comparison: Record<string, number>;
  size_comparison_mb: Record<string, number>;
  recommended_model_id: string;
  recommendation_reason: string;
}

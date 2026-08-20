export type RunStatus = 'running' | 'completed' | 'failed' | 'queued' | 'paused';

export interface Hyperparameters {
  learning_rate: number;
  batch_size: number;
  optimizer: string;
  weight_decay: number;
  warmup_steps: number;
  max_epochs: number;
  model_architecture: string;
  gradient_accumulation_steps?: number;
  precision?: 'fp32' | 'fp16' | 'bf16';
  seed?: number;
  [key: string]: string | number | boolean | undefined;
}

export interface MetricPoint {
  step: number;
  epoch: number;
  timestamp: number;
  value: number;
}

export interface MetricSeries {
  id: string;
  name: string;
  color: string;
  unit?: string;
  data: MetricPoint[];
}

export interface HardwareMetrics {
  gpu_utilization_pct: number;
  gpu_memory_used_mb: number;
  gpu_memory_total_mb: number;
  gpu_temperature_c: number;
  power_draw_watts: number;
  cpu_utilization_pct: number;
  ram_used_gb: number;
  ram_total_gb: number;
}

export interface HardwareMetricPoint {
  step: number;
  timestamp: number;
  gpu_util: number;
  gpu_vram_mb: number;
  gpu_temp: number;
  power_w: number;
  cpu_util: number;
}

export interface CheckpointArtifact {
  id: string;
  run_id: string;
  name: string;
  step: number;
  epoch: number;
  val_loss: number;
  accuracy?: number;
  file_size_bytes: number;
  format: 'pytorch_pt' | 'safetensors' | 'onnx' | 'gguf';
  sha256?: string;
  created_at: string;
  is_best?: boolean;
  download_url?: string;
}

export interface ExperimentRun {
  id: string;
  name: string;
  description: string;
  status: RunStatus;
  started_at: string;
  ended_at?: string;
  duration_seconds: number;
  compute_target: string;
  tags: string[];
  hyperparameters: Hyperparameters;
  current_step: number;
  total_steps: number;
  current_epoch: number;
  total_epochs: number;
  best_val_loss: number;
  best_val_accuracy?: number;
  metrics: {
    train_loss: MetricPoint[];
    val_loss: MetricPoint[];
    train_accuracy?: MetricPoint[];
    val_accuracy?: MetricPoint[];
    learning_rate: MetricPoint[];
    custom?: Record<string, MetricPoint[]>;
  };
  hardware_history: HardwareMetricPoint[];
  latest_hardware: HardwareMetrics;
  checkpoints: CheckpointArtifact[];
  logs: string[];
}

export type XAxisMode = 'step' | 'epoch' | 'time';
export type ScaleMode = 'linear' | 'log';
export type ActiveTab = 'metrics' | 'hardware' | 'checkpoints' | 'config' | 'logs' | 'compare';

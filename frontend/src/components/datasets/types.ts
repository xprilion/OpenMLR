/**
 * Types for Dataset Profiler, Table Inspector, Validation, and Partition Splitter.
 */

export interface ColumnProfile {
  name: string;
  dtype: 'numeric' | 'text' | 'categorical' | 'boolean' | 'unknown' | string;
  total_count: number;
  null_count: number;
  null_percentage: number;
  unique_count: number;
  stats: {
    min?: number;
    max?: number;
    mean?: number;
    std?: number;
    median?: number;
    q25?: number;
    q75?: number;
    outlier_count?: number;
    top_classes?: Record<string, number>;
    imbalance_ratio?: number;
    class_distribution?: Record<string, number>;
    char_len_avg?: number;
    token_est_mean?: number;
    token_est_p95?: number;
    token_est_max?: number;
    overflow_512_count?: number;
    overflow_512_pct?: number;
    true_count?: number;
    [key: string]: unknown;
  };
}

export interface DatasetProfile {
  file_path: string;
  format: string;
  total_rows: number;
  total_columns: number;
  file_size_bytes: number;
  columns: Record<string, ColumnProfile>;
  health_score: number;
  warnings: string[];
  summary: string;
}

export interface ValidationResult {
  valid: boolean;
  errors: string[];
  warnings: string[];
  health_score: number;
  total_rows: number;
  total_columns: number;
}

export interface SplitManifest {
  source_file: string;
  stratified_by: string | null;
  seed: number;
  total_records: number;
  train_count: number;
  val_count: number;
  test_count: number;
  splits: {
    train: string;
    val: string;
    test: string;
  };
}

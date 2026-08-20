import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { DatasetStudio } from './DatasetStudio';
import { api } from '../../api';

vi.mock('../../api', () => ({
  api: {
    profileDataset: vi.fn(),
    inspectDatasetSamples: vi.fn(),
    validateDataset: vi.fn(),
    splitDataset: vi.fn(),
  },
}));

vi.mock('../../context/ProjectContext', () => ({
  useProject: () => ({
    activeProject: { uuid: 'proj-123', name: 'Vision LLM Research' },
  }),
}));

const mockProfile = {
  success: true,
  profile: {
    file_path: 'data.csv',
    format: 'csv',
    total_rows: 1500,
    total_columns: 4,
    file_size_bytes: 204850,
    health_score: 92,
    warnings: ['Column text has 5% missing values'],
    summary: 'data.csv: 1500 rows, 4 cols. Health: 92/100.',
    columns: {
      id: {
        name: 'id',
        dtype: 'numeric',
        total_count: 1500,
        null_count: 0,
        null_percentage: 0.0,
        unique_count: 1500,
        stats: { min: 1, max: 1500, mean: 750.5, std: 433.0 },
      },
      label: {
        name: 'label',
        dtype: 'categorical',
        total_count: 1500,
        null_count: 0,
        null_percentage: 0.0,
        unique_count: 3,
        stats: { top_classes: { positive: 800, negative: 500, neutral: 200 }, imbalance_ratio: 4.0 },
      },
      text: {
        name: 'text',
        dtype: 'text',
        total_count: 1500,
        null_count: 75,
        null_percentage: 5.0,
        unique_count: 1420,
        stats: { char_len_avg: 120.4, token_est_mean: 32.5, token_est_max: 128 },
      },
      active: {
        name: 'active',
        dtype: 'boolean',
        total_count: 1500,
        null_count: 0,
        null_percentage: 0.0,
        unique_count: 2,
        stats: { true_count: 1200 },
      },
    },
  },
};

const mockSamples = {
  success: true,
  total_sampled: 2,
  samples: [
    { id: 1, label: 'positive', text: 'Excellent benchmark accuracy', active: true },
    { id: 2, label: 'negative', text: 'High generalization error', active: false },
  ],
};

const mockValidation = {
  success: true,
  validation: {
    valid: true,
    errors: [],
    warnings: [],
    health_score: 95,
    total_rows: 1500,
    total_columns: 4,
  },
};

const mockSplitManifest = {
  success: true,
  manifest: {
    source_file: 'data.csv',
    stratified_by: 'label',
    seed: 42,
    total_records: 1500,
    train_count: 1200,
    val_count: 150,
    test_count: 150,
    splits: {
      train: 'data_splits/train.csv',
      val: 'data_splits/val.csv',
      test: 'data_splits/test.csv',
    },
  },
};

describe('DatasetStudio Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.profileDataset).mockResolvedValue(mockProfile);
    vi.mocked(api.inspectDatasetSamples).mockResolvedValue(mockSamples);
    vi.mocked(api.validateDataset).mockResolvedValue(mockValidation);
    vi.mocked(api.splitDataset).mockResolvedValue(mockSplitManifest);
  });

  it('renders dataset header, overview metrics, and column stats table', async () => {
    render(<DatasetStudio />);

    expect(screen.getByText('Dataset Studio')).toBeDefined();
    expect(screen.getByText('Vision LLM Research')).toBeDefined();

    await waitFor(() => {
      expect(api.profileDataset).toHaveBeenCalledWith({ path: 'data.csv' });
      expect(screen.getAllByText('1,500').length).toBeGreaterThan(0);
      expect(screen.getByText('92/100')).toBeDefined();
    });

    // Column names
    expect(screen.getByText('label')).toBeDefined();
    expect(screen.getAllByText('text').length).toBeGreaterThan(0);
  });

  it('switches to Data Samples tab and renders preview rows', async () => {
    render(<DatasetStudio />);

    await waitFor(() => {
      expect(screen.getByText('92/100')).toBeDefined();
    });

    const samplesTab = screen.getByText('Data Samples');
    fireEvent.click(samplesTab);

    await waitFor(() => {
      expect(api.inspectDatasetSamples).toHaveBeenCalled();
      expect(screen.getByText('Excellent benchmark accuracy')).toBeDefined();
      expect(screen.getByText('High generalization error')).toBeDefined();
    });
  });

  it('switches to Schema Validator and executes validation check', async () => {
    render(<DatasetStudio />);

    await waitFor(() => {
      expect(screen.getByText('92/100')).toBeDefined();
    });

    const valTab = screen.getByText('Schema Validator');
    fireEvent.click(valTab);

    const runBtn = screen.getByText('Run Validation Check');
    fireEvent.click(runBtn);

    await waitFor(() => {
      expect(api.validateDataset).toHaveBeenCalled();
      expect(screen.getByText('Passed')).toBeDefined();
      expect(screen.getByText('95 / 100')).toBeDefined();
    });
  });

  it('opens Dataset Splitter modal and triggers partition generation', async () => {
    render(<DatasetStudio />);

    await waitFor(() => {
      expect(screen.getByText('92/100')).toBeDefined();
    });

    const splitBtn = screen.getByText('Split Partitions');
    fireEvent.click(splitBtn);

    expect(screen.getByText('Dataset Partition Splitter')).toBeDefined();

    const generateBtn = screen.getByText('Generate Splits');
    fireEvent.click(generateBtn);

    await waitFor(() => {
      expect(api.splitDataset).toHaveBeenCalled();
      expect(screen.getByText('Partition splits generated successfully!')).toBeDefined();
    });
  });

  it('displays error banner when dataset profiling fails', async () => {
    vi.mocked(api.profileDataset).mockRejectedValueOnce(new Error('File not found: missing.csv'));
    render(<DatasetStudio />);

    await waitFor(() => {
      expect(screen.getByText('File not found: missing.csv')).toBeDefined();
    });
  });
});

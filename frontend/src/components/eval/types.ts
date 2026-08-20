import type { EvalTaskInfo, EvalSuiteInfo, EvalSuiteRunResult } from '../../types';

export type EvalCategoryFilter = 'all' | 'reproduction' | 'optimization' | 'hypothesis';

export interface EvalDashboardState {
  selectedSuite: string;
  categoryFilter: EvalCategoryFilter;
  suites: EvalSuiteInfo[];
  tasks: EvalTaskInfo[];
  loading: boolean;
  running: boolean;
  runResult: EvalSuiteRunResult | null;
  error: string | null;
  showCustomModal: boolean;
}

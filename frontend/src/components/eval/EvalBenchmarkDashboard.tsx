import { useState, useEffect, useCallback } from 'react';
import { 
  BarChart2, 
  Play, 
  Plus, 
  RotateCcw, 
  Filter, 
  Search, 
  AlertCircle, 
  Layers
} from 'lucide-react';
import { api } from '../../api';
import type { EvalTaskInfo, EvalSuiteInfo, EvalSuiteRunResult } from '../../types';
import type { EvalCategoryFilter } from './types';
import { TaskCard } from './TaskCard';
import { CustomTaskModal } from './CustomTaskModal';
import { SuiteRunSummary } from './SuiteRunSummary';

export function EvalBenchmarkDashboard() {
  const [suites, setSuites] = useState<EvalSuiteInfo[]>([]);
  const [tasks, setTasks] = useState<EvalTaskInfo[]>([]);
  const [selectedSuite, setSelectedSuite] = useState('full');
  const [concurrency, setConcurrency] = useState(4);
  const [categoryFilter, setCategoryFilter] = useState<EvalCategoryFilter>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [running, setRunning] = useState(false);
  const [runResult, setRunResult] = useState<EvalSuiteRunResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showCustomModal, setShowCustomModal] = useState(false);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [suitesData, tasksData] = await Promise.all([
        api.listEvalSuites(),
        api.listEvalTasks(),
      ]);
      if (suitesData?.suites) setSuites(suitesData.suites);
      if (tasksData?.tasks) setTasks(tasksData.tasks);
    } catch (err: unknown) {
      const errMsg = err instanceof Error ? err.message : 'Failed to load evaluation tasks.';
      setError(errMsg);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleRunSuite = async () => {
    setError(null);
    setRunning(true);
    try {
      const data = await api.runEvalSuite(selectedSuite, concurrency);
      setRunResult(data);
    } catch (err: unknown) {
      const errMsg = err instanceof Error ? err.message : 'Failed to execute benchmark suite.';
      setError(errMsg);
    } finally {
      setRunning(false);
    }
  };

  const filteredTasks = tasks.filter((t) => {
    const matchesCategory = categoryFilter === 'all' || t.category === categoryFilter;
    const matchesSearch = 
      t.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      t.task_id.toLowerCase().includes(searchQuery.toLowerCase()) ||
      t.description.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesCategory && matchesSearch;
  });

  return (
    <div className="flex flex-col flex-1 h-full overflow-y-auto bg-bg text-text p-4 sm:p-6 space-y-6">
      {/* Top Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-surface border border-border rounded-2xl p-5 shadow-sm">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-primary/10 border border-primary/20 flex items-center justify-center text-primary">
            <BarChart2 size={22} />
          </div>
          <div>
            <h2 className="text-base sm:text-lg font-bold text-text flex items-center gap-2">
              ML Research Agent Evaluation Harness
            </h2>
            <p className="text-xs text-text-dim">
              Benchmark autonomous paper reproduction, kernel optimization, and hypothesis discovery
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2.5 flex-wrap">
          <button
            type="button"
            onClick={() => setShowCustomModal(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-surface-hover hover:bg-border border border-border text-xs font-medium text-text-dim hover:text-text transition-colors"
          >
            <Plus size={14} />
            <span>Add Custom Task</span>
          </button>
        </div>
      </div>

      {/* Runner Control Bar */}
      <div className="bg-surface border border-border rounded-2xl p-5 shadow-sm space-y-4">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div className="flex items-center gap-3 flex-wrap">
            {/* Suite dropdown */}
            <div className="flex items-center gap-2 bg-bg border border-border rounded-xl px-3 py-1.5">
              <Layers size={14} className="text-primary" />
              <span className="text-xs text-text-dim font-medium">Suite:</span>
              <select
                value={selectedSuite}
                onChange={(e) => setSelectedSuite(e.target.value)}
                className="bg-transparent text-xs font-semibold text-text focus:outline-none cursor-pointer capitalize"
              >
                {suites.length > 0 ? (
                  suites.map((s) => (
                    <option key={s.id} value={s.id} className="bg-surface text-text">
                      {s.name} ({s.tasks?.length || 0} tasks)
                    </option>
                  ))
                ) : (
                  <>
                    <option value="full">Full OpenMLR Benchmark Suite</option>
                    <option value="reproduction">Standard Reproduction Suite</option>
                    <option value="optimization">Standard Optimization Suite</option>
                    <option value="hypothesis">Standard Hypothesis Suite</option>
                  </>
                )}
              </select>
            </div>

            {/* Concurrency */}
            <div className="flex items-center gap-2 bg-bg border border-border rounded-xl px-3 py-1.5">
              <span className="text-xs text-text-dim font-medium">Concurrency:</span>
              <select
                value={concurrency}
                onChange={(e) => setConcurrency(parseInt(e.target.value))}
                className="bg-transparent text-xs font-semibold text-text focus:outline-none cursor-pointer"
              >
                <option value={1}>1 worker</option>
                <option value={2}>2 workers</option>
                <option value={4}>4 workers</option>
                <option value={8}>8 workers</option>
              </select>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={handleRunSuite}
              disabled={running}
              className="flex items-center gap-2 px-4 py-2 rounded-xl bg-primary hover:bg-primary/90 text-white text-xs font-bold shadow-md hover:shadow-primary/20 transition-all disabled:opacity-50"
            >
              {running ? (
                <>
                  <RotateCcw size={14} className="animate-spin" />
                  <span>Running Suite...</span>
                </>
              ) : (
                <>
                  <Play size={14} />
                  <span>Execute Benchmark Suite</span>
                </>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Error alert */}
      {error && (
        <div className="bg-rose-500/10 border border-rose-500/30 rounded-xl p-4 flex items-center gap-3 text-xs text-rose-400">
          <AlertCircle size={18} className="shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Run results summary if available */}
      {runResult && <SuiteRunSummary runResult={runResult} />}

      {/* Task Explorer Section */}
      <div className="space-y-4">
        {/* Filters and search */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          {/* Category Tabs */}
          <div className="flex items-center gap-1.5 p-1 bg-surface border border-border rounded-xl overflow-x-auto">
            {(['all', 'reproduction', 'optimization', 'hypothesis'] as const).map((cat) => (
              <button
                key={cat}
                type="button"
                onClick={() => setCategoryFilter(cat)}
                className={`px-3 py-1 rounded-lg text-xs font-medium capitalize transition-all ${
                  categoryFilter === cat
                    ? 'bg-primary text-white shadow-xs'
                    : 'text-text-dim hover:text-text hover:bg-surface-hover'
                }`}
              >
                {cat}
              </button>
            ))}
          </div>

          {/* Search */}
          <div className="relative">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-dim" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search benchmark tasks..."
              className="bg-surface border border-border rounded-xl pl-8 pr-3 py-1.5 text-xs text-text placeholder:text-text-dim focus:border-primary focus:outline-none w-full sm:w-64"
            />
          </div>
        </div>

        {/* Task cards list */}
        {loading ? (
          <div className="text-center py-12 text-xs text-text-dim">Loading benchmark tasks...</div>
        ) : filteredTasks.length > 0 ? (
          <div className="grid grid-cols-1 gap-3">
            {filteredTasks.map((task) => (
              <TaskCard key={task.task_id} task={task} />
            ))}
          </div>
        ) : (
          <div className="bg-surface border border-border rounded-2xl p-8 text-center text-xs text-text-dim flex flex-col items-center justify-center">
            <Filter size={24} className="mb-2 text-text-dim/60" />
            <span>No benchmark tasks match the selected criteria.</span>
          </div>
        )}
      </div>

      {/* Custom Task Registration Modal */}
      {showCustomModal && (
        <CustomTaskModal
          onClose={() => setShowCustomModal(false)}
          onCreated={loadData}
        />
      )}
    </div>
  );
}

import { useState, useMemo, useCallback } from 'react';
import { 
  Play, 
  Pause, 
  Square, 
  Cpu, 
  Sliders, 
  Terminal, 
  Download, 
  CheckCircle2, 
  AlertCircle, 
  Clock, 
  RotateCw,
  HardDrive,
  Activity
} from 'lucide-react';
import type { ExperimentRun, RunStatus, ActiveTab } from './types';
import { MetricCharts } from './MetricCharts';
import { CheckpointViewer } from './CheckpointViewer';
import { RunSidebar } from './RunSidebar';
import { RunComparisonView } from './RunComparisonView';
import { INITIAL_MOCK_RUNS } from './mockData';

function statusColor(status: RunStatus): string {
  switch (status) {
    case 'running': return 'text-primary bg-primary/10 border-primary/30';
    case 'completed': return 'text-success bg-success/10 border-success/30';
    case 'failed': return 'text-error bg-error/10 border-error/30';
    case 'paused': return 'text-warning bg-warning/10 border-warning/30';
    default: return 'text-text-dim bg-surface border-border';
  }
}

function statusIcon(status: RunStatus) {
  switch (status) {
    case 'running': return <RotateCw size={12} className="animate-spin text-primary" />;
    case 'completed': return <CheckCircle2 size={12} className="text-success" />;
    case 'failed': return <AlertCircle size={12} className="text-error" />;
    case 'paused': return <Pause size={12} className="text-warning" />;
    default: return <Clock size={12} className="text-text-dim" />;
  }
}

export function RunDashboard() {
  const [runs, setRuns] = useState<ExperimentRun[]>(INITIAL_MOCK_RUNS);
  const [selectedRunId, setSelectedRunId] = useState<string>(INITIAL_MOCK_RUNS[0].id);
  const [activeTab, setActiveTab] = useState<ActiveTab>('metrics');
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<'all' | RunStatus>('all');
  const [compareRunIds, setCompareRunIds] = useState<string[]>([]);
  const [isComparing, setIsComparing] = useState(false);

  const selectedRun = useMemo(() => {
    return runs.find((r) => r.id === selectedRunId) || runs[0];
  }, [runs, selectedRunId]);

  const toggleCompareRun = useCallback((id: string) => {
    setCompareRunIds((prev) => 
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]
    );
  }, []);

  const handleCreateNewRun = useCallback(() => {
    const newId = `run-${Date.now().toString(36)}`;
    const newRun: ExperimentRun = {
      id: newId,
      name: `Experiment Trial #${runs.length + 1}`,
      description: 'Autonomous exploration run generated from active research hypothesis.',
      status: 'running',
      started_at: new Date().toISOString().replace('T', ' ').slice(0, 19),
      duration_seconds: 120,
      compute_target: 'Local H100 GPU (80GB)',
      tags: ['auto-generated', 'hypothesis-test'],
      hyperparameters: {
        model_architecture: 'Transformer-Tiny',
        learning_rate: 0.001,
        batch_size: 32,
        optimizer: 'AdamW',
        weight_decay: 0.01,
        warmup_steps: 100,
        max_epochs: 5,
        precision: 'bf16',
      },
      current_step: 30,
      total_steps: 500,
      current_epoch: 1,
      total_epochs: 5,
      best_val_loss: 3.42,
      metrics: {
        train_loss: Array.from({ length: 6 }, (_, i) => ({
          step: (i + 1) * 5,
          epoch: 1,
          timestamp: Date.now() - (6 - i) * 20000,
          value: 4.2 - (i * 0.14),
        })),
        val_loss: [
          { step: 25, epoch: 1, timestamp: Date.now() - 10000, value: 3.42 },
        ],
        learning_rate: Array.from({ length: 6 }, (_, i) => ({
          step: (i + 1) * 5,
          epoch: 1,
          timestamp: Date.now() - (6 - i) * 20000,
          value: 0.0002 * (i + 1),
        })),
      },
      hardware_history: [],
      latest_hardware: {
        gpu_utilization_pct: 88,
        gpu_memory_used_mb: 16400,
        gpu_memory_total_mb: 81920,
        gpu_temperature_c: 58,
        power_draw_watts: 240,
        cpu_utilization_pct: 32,
        ram_used_gb: 22.0,
        ram_total_gb: 128.0,
      },
      checkpoints: [
        {
          id: `ckpt-${newId}-01`,
          run_id: newId,
          name: 'step_25.safetensors',
          step: 25,
          epoch: 1,
          val_loss: 3.42,
          file_size_bytes: 120000000,
          format: 'safetensors',
          created_at: 'Just now',
          is_best: true,
        },
      ],
      logs: ['[INFO] Initialized autonomous experiment trial...'],
    };
    setRuns((prev) => [newRun, ...prev]);
    setSelectedRunId(newId);
    setIsComparing(false);
  }, [runs.length]);

  const handleExportCSV = useCallback(() => {
    if (!selectedRun) return;
    const rows = [['Step', 'Epoch', 'Train_Loss', 'Val_Loss', 'Learning_Rate']];
    const maxSteps = Math.max(
      selectedRun.metrics.train_loss.length,
      selectedRun.metrics.val_loss.length
    );
    for (let i = 0; i < maxSteps; i++) {
      const train = selectedRun.metrics.train_loss[i];
      const val = selectedRun.metrics.val_loss[i];
      const lr = selectedRun.metrics.learning_rate[i];
      rows.push([
        String(train?.step || val?.step || i + 1),
        String(train?.epoch || val?.epoch || 1),
        String(train?.value?.toFixed(4) || ''),
        String(val?.value?.toFixed(4) || ''),
        String(lr?.value?.toExponential(2) || ''),
      ]);
    }
    const csvContent = 'data:text/csv;charset=utf-8,' + rows.map((e) => e.join(',')).join('\n');
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `${selectedRun.id}_metrics.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }, [selectedRun]);

  return (
    <div className="flex flex-1 h-full overflow-hidden bg-bg text-text">
      <RunSidebar
        runs={runs}
        selectedRunId={selectedRunId}
        compareRunIds={compareRunIds}
        isComparing={isComparing}
        searchQuery={searchQuery}
        statusFilter={statusFilter}
        onSelectRun={(id) => {
          setSelectedRunId(id);
          setIsComparing(false);
        }}
        onToggleCompare={toggleCompareRun}
        onToggleCompareMode={() => setIsComparing((v) => !v)}
        onSearchChange={setSearchQuery}
        onStatusFilterChange={setStatusFilter}
        onNewRun={handleCreateNewRun}
      />

      <div className="flex-1 flex flex-col overflow-hidden">
        {isComparing ? (
          <RunComparisonView
            runs={runs}
            compareRunIds={compareRunIds}
            onClose={() => setIsComparing(false)}
          />
        ) : (
          <div className="flex-1 flex flex-col overflow-hidden">
            {/* Run Top Banner */}
            <div className="p-4 border-b border-border bg-surface/30 flex items-center justify-between flex-wrap gap-3">
              <div className="flex flex-col gap-1 min-w-0">
                <div className="flex items-center gap-2">
                  <h3 className="font-bold text-base text-text truncate">{selectedRun.name}</h3>
                  <span className={`text-xs px-2 py-0.5 rounded-full border font-mono flex items-center gap-1 ${statusColor(selectedRun.status)}`}>
                    {statusIcon(selectedRun.status)}
                    {selectedRun.status}
                  </span>
                </div>
                <p className="text-xs text-text-dim truncate">{selectedRun.description}</p>
              </div>

              {/* Action Toolbar */}
              <div className="flex items-center gap-2">
                {selectedRun.status === 'running' ? (
                  <>
                    <button
                      type="button"
                      className="flex items-center gap-1 px-3 py-1.5 rounded-lg border border-border bg-bg text-xs text-text hover:bg-surface transition-colors"
                      onClick={() => {
                        setRuns((prev) => prev.map((r) => r.id === selectedRun.id ? { ...r, status: 'paused' } : r));
                      }}
                    >
                      <Pause size={13} />
                      <span>Pause</span>
                    </button>
                    <button
                      type="button"
                      className="flex items-center gap-1 px-3 py-1.5 rounded-lg border border-error/40 bg-error/10 text-xs text-error hover:bg-error/20 transition-colors"
                      onClick={() => {
                        setRuns((prev) => prev.map((r) => r.id === selectedRun.id ? { ...r, status: 'completed' } : r));
                      }}
                    >
                      <Square size={13} />
                      <span>Stop</span>
                    </button>
                  </>
                ) : (
                  <button
                    type="button"
                    className="flex items-center gap-1 px-3 py-1.5 rounded-lg border border-primary/40 bg-primary/10 text-xs text-primary hover:bg-primary/20 transition-colors"
                    onClick={() => {
                      setRuns((prev) => prev.map((r) => r.id === selectedRun.id ? { ...r, status: 'running' } : r));
                    }}
                  >
                    <Play size={13} />
                    <span>Resume</span>
                  </button>
                )}

                <button
                  type="button"
                  className="flex items-center gap-1 px-3 py-1.5 rounded-lg border border-border bg-bg text-xs text-text-dim hover:text-text hover:bg-surface transition-colors"
                  onClick={handleExportCSV}
                  title="Export Run Metrics CSV"
                >
                  <Download size={13} />
                  <span>CSV</span>
                </button>
              </div>
            </div>

            {/* Navigation Tabs */}
            <div className="flex items-center border-b border-border bg-surface px-4 gap-1 text-xs shrink-0">
              {[
                { id: 'metrics', label: 'Metrics & Loss Curves', icon: Activity },
                { id: 'hardware', label: 'GPU & Hardware Telemetry', icon: Cpu },
                { id: 'checkpoints', label: 'Checkpoints & Weights', icon: HardDrive },
                { id: 'config', label: 'Hyperparameters', icon: Sliders },
                { id: 'logs', label: 'Console Logs', icon: Terminal },
              ].map((tab) => {
                const Icon = tab.icon;
                const isActive = activeTab === tab.id;
                return (
                  <button
                    key={tab.id}
                    type="button"
                    className={`flex items-center gap-1.5 px-3 py-2.5 font-medium border-b-2 transition-colors ${
                      isActive ? 'border-primary text-primary' : 'border-transparent text-text-dim hover:text-text'
                    }`}
                    onClick={() => setActiveTab(tab.id as ActiveTab)}
                  >
                    <Icon size={14} />
                    <span>{tab.label}</span>
                  </button>
                );
              })}
            </div>

            {/* Tab View Container */}
            <div className="flex-1 overflow-y-auto p-5 flex flex-col gap-5">
              {activeTab === 'metrics' && (
                <div className="flex flex-col gap-5">
                  <MetricCharts
                    title="Training & Validation Loss"
                    series={[
                      { id: 'train_loss', name: 'Train Loss', color: '#1288ff', data: selectedRun.metrics.train_loss },
                      { id: 'val_loss', name: 'Val Loss', color: '#10b981', data: selectedRun.metrics.val_loss },
                    ]}
                  />

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <MetricCharts
                      title="Learning Rate Schedule"
                      series={[
                        { id: 'lr', name: 'Learning Rate', color: '#f59e0b', data: selectedRun.metrics.learning_rate },
                      ]}
                      height={220}
                    />

                    {selectedRun.metrics.val_accuracy && (
                      <MetricCharts
                        title="Validation Accuracy"
                        series={[
                          { id: 'val_acc', name: 'Val Accuracy', color: '#8b5cf6', data: selectedRun.metrics.val_accuracy },
                        ]}
                        height={220}
                      />
                    )}
                  </div>
                </div>
              )}

              {activeTab === 'hardware' && (
                <div className="flex flex-col gap-4">
                  {/* Gauge Cards */}
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                    <div className="bg-surface border border-border p-3.5 rounded-xl flex flex-col gap-1">
                      <span className="text-xs text-text-dim">GPU Utilization</span>
                      <span className="text-xl font-bold font-mono text-primary">{selectedRun.latest_hardware.gpu_utilization_pct}%</span>
                    </div>
                    <div className="bg-surface border border-border p-3.5 rounded-xl flex flex-col gap-1">
                      <span className="text-xs text-text-dim">VRAM Usage</span>
                      <span className="text-xl font-bold font-mono text-text">
                        {(selectedRun.latest_hardware.gpu_memory_used_mb / 1024).toFixed(1)} / {(selectedRun.latest_hardware.gpu_memory_total_mb / 1024).toFixed(0)} GB
                      </span>
                    </div>
                    <div className="bg-surface border border-border p-3.5 rounded-xl flex flex-col gap-1">
                      <span className="text-xs text-text-dim">GPU Temp</span>
                      <span className="text-xl font-bold font-mono text-warning">{selectedRun.latest_hardware.gpu_temperature_c}°C</span>
                    </div>
                    <div className="bg-surface border border-border p-3.5 rounded-xl flex flex-col gap-1">
                      <span className="text-xs text-text-dim">Power Draw</span>
                      <span className="text-xl font-bold font-mono text-text">{selectedRun.latest_hardware.power_draw_watts} W</span>
                    </div>
                  </div>

                  {/* GPU telemetry chart */}
                  {selectedRun.hardware_history.length > 0 && (
                    <MetricCharts
                      title="GPU Utilization & Power Over Time"
                      series={[
                        {
                          id: 'gpu_util',
                          name: 'GPU Util %',
                          color: '#1288ff',
                          data: selectedRun.hardware_history.map((h) => ({ step: h.step, epoch: 1, timestamp: h.timestamp, value: h.gpu_util })),
                        },
                        {
                          id: 'cpu_util',
                          name: 'CPU Util %',
                          color: '#10b981',
                          data: selectedRun.hardware_history.map((h) => ({ step: h.step, epoch: 1, timestamp: h.timestamp, value: h.cpu_util })),
                        },
                      ]}
                      height={240}
                    />
                  )}
                </div>
              )}

              {activeTab === 'checkpoints' && (
                <CheckpointViewer run={selectedRun} />
              )}

              {activeTab === 'config' && (
                <div className="bg-surface border border-border rounded-xl p-5 flex flex-col gap-3 font-mono text-xs">
                  <h4 className="font-semibold text-sm text-text font-sans">Experiment Configuration & Environment</h4>
                  <pre className="bg-bg border border-border p-4 rounded-lg overflow-x-auto text-text">
                    {JSON.stringify(selectedRun.hyperparameters, null, 2)}
                  </pre>
                </div>
              )}

              {activeTab === 'logs' && (
                <div className="bg-bg border border-border rounded-xl p-4 font-mono text-xs flex flex-col gap-1 overflow-y-auto max-h-[450px]">
                  {selectedRun.logs.map((log, idx) => (
                    <div key={`log-${idx}`} className="text-text-dim hover:text-text font-mono leading-relaxed">
                      {log}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

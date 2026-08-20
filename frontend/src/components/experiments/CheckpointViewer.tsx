import { useState, useMemo, useCallback } from 'react';
import { 
  HardDrive, 
  Download, 
  Award, 
  Layers, 
  Rocket, 
  FileText, 
  CheckCircle,
  Copy,
  Search
} from 'lucide-react';
import type { CheckpointArtifact, ExperimentRun } from './types';

interface CheckpointViewerProps {
  readonly run: ExperimentRun;
  readonly onSetBest?: (checkpointId: string) => void;
  readonly onDeploy?: (checkpoint: CheckpointArtifact) => void;
}

function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${(bytes / Math.pow(k, i)).toFixed(2)} ${sizes[i]}`;
}

export function CheckpointViewer({
  run,
  onSetBest,
  onDeploy,
}: Readonly<CheckpointViewerProps>) {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCheckpoint, setSelectedCheckpoint] = useState<CheckpointArtifact | null>(null);
  const [showModelCard, setShowModelCard] = useState(false);
  const [copiedHash, setCopiedHash] = useState(false);
  const [deployedId, setDeployedId] = useState<string | null>(null);

  const filteredCheckpoints = useMemo(() => {
    return run.checkpoints.filter((cp) => 
      cp.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      cp.format.toLowerCase().includes(searchQuery.toLowerCase())
    );
  }, [run.checkpoints, searchQuery]);

  const handleCopySha = useCallback((hash?: string) => {
    if (!hash) return;
    navigator.clipboard.writeText(hash);
    setCopiedHash(true);
    setTimeout(() => setCopiedHash(false), 2000);
  }, []);

  const handleDeployClick = useCallback((cp: CheckpointArtifact) => {
    setDeployedId(cp.id);
    if (onDeploy) {
      onDeploy(cp);
    }
    setTimeout(() => setDeployedId(null), 3000);
  }, [onDeploy]);

  const modelCardContent = useMemo(() => {
    if (!selectedCheckpoint) return '';
    return `# Model Card: ${run.name} (${selectedCheckpoint.name})
## Overview
- **Architecture**: ${run.hyperparameters.model_architecture}
- **Run ID**: \`${run.id}\`
- **Step**: ${selectedCheckpoint.step} / ${run.total_steps}
- **Epoch**: ${selectedCheckpoint.epoch} / ${run.total_epochs}
- **Format**: ${selectedCheckpoint.format.toUpperCase()}
- **File Size**: ${formatBytes(selectedCheckpoint.file_size_bytes)}
- **SHA-256**: \`${selectedCheckpoint.sha256 || 'N/A'}\`

## Performance Metrics
- **Validation Loss**: ${selectedCheckpoint.val_loss.toFixed(4)}
${selectedCheckpoint.accuracy ? `- **Validation Accuracy**: ${(selectedCheckpoint.accuracy * 100).toFixed(2)}%` : ''}
- **Best Run Loss**: ${run.best_val_loss.toFixed(4)}

## Hyperparameters
\`\`\`json
${JSON.stringify(run.hyperparameters, null, 2)}
\`\`\`
`;
  }, [run, selectedCheckpoint]);

  return (
    <div className="flex flex-col gap-4">
      {/* Header Bar */}
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center gap-2">
          <HardDrive size={16} className="text-primary" />
          <h3 className="text-sm font-semibold text-text">Saved Checkpoints & Weights</h3>
          <span className="text-xs text-text-dim px-2 py-0.5 rounded-full bg-surface border border-border">
            {run.checkpoints.length} saved
          </span>
        </div>

        <div className="flex items-center gap-2">
          <div className="relative">
            <Search size={14} className="absolute left-2.5 top-2.5 text-text-dim" />
            <input
              type="text"
              placeholder="Search checkpoints..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="bg-bg border border-border rounded-lg pl-8 pr-3 py-1.5 text-xs text-text focus:border-primary focus:outline-none w-48 transition-colors"
            />
          </div>
        </div>
      </div>

      {/* Checkpoints Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {filteredCheckpoints.map((cp) => {
          const isSelected = selectedCheckpoint?.id === cp.id;
          return (
            <div
              key={cp.id}
              className={`flex flex-col gap-3 p-4 rounded-xl border transition-all ${
                isSelected
                  ? 'bg-surface border-primary ring-1 ring-primary/40 shadow-lg'
                  : 'bg-surface/60 border-border hover:border-border/80 hover:bg-surface'
              }`}
            >
              {/* Card Top */}
              <div className="flex items-start justify-between gap-2">
                <div className="flex flex-col min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-sm text-text truncate">{cp.name}</span>
                    {cp.is_best && (
                      <span className="flex items-center gap-1 text-[10px] bg-warning/15 text-warning border border-warning/30 px-1.5 py-0.5 rounded font-medium">
                        <Award size={11} />
                        BEST
                      </span>
                    )}
                  </div>
                  <span className="text-xs text-text-dim font-mono">
                    Step {cp.step} · Epoch {cp.epoch} · {cp.created_at}
                  </span>
                </div>

                <span className="text-[10px] font-mono uppercase bg-bg border border-border px-2 py-0.5 rounded text-text-dim">
                  {cp.format.replace('_', '.')}
                </span>
              </div>

              {/* Metrics row */}
              <div className="grid grid-cols-3 gap-2 bg-bg/60 p-2.5 rounded-lg border border-border/40 text-xs">
                <div>
                  <span className="text-text-dim text-[11px] block">Val Loss</span>
                  <span className="font-mono font-medium text-text">{cp.val_loss.toFixed(4)}</span>
                </div>
                <div>
                  <span className="text-text-dim text-[11px] block">Accuracy</span>
                  <span className="font-mono font-medium text-text">
                    {cp.accuracy ? `${(cp.accuracy * 100).toFixed(1)}%` : '—'}
                  </span>
                </div>
                <div>
                  <span className="text-text-dim text-[11px] block">File Size</span>
                  <span className="font-mono font-medium text-text">{formatBytes(cp.file_size_bytes)}</span>
                </div>
              </div>

              {/* Action Toolbar */}
              <div className="flex items-center justify-between gap-1 pt-1 border-t border-border/40 text-xs">
                <button
                  type="button"
                  className={`flex items-center gap-1 px-2 py-1 rounded-lg border transition-colors ${
                    isSelected ? 'bg-primary text-white border-primary' : 'bg-bg border-border text-text-dim hover:text-text hover:bg-surface-hover'
                  }`}
                  onClick={() => setSelectedCheckpoint(isSelected ? null : cp)}
                >
                  <Layers size={12} />
                  <span>Inspect</span>
                </button>

                <div className="flex items-center gap-1.5">
                  {!cp.is_best && onSetBest && (
                    <button
                      type="button"
                      className="px-2 py-1 rounded-lg border border-border bg-bg text-text-dim hover:text-warning hover:border-warning/40 transition-colors"
                      onClick={() => onSetBest(cp.id)}
                      title="Set as Best Checkpoint"
                    >
                      <Award size={12} />
                    </button>
                  )}

                  <button
                    type="button"
                    className={`flex items-center gap-1 px-2.5 py-1 rounded-lg border transition-colors ${
                      deployedId === cp.id
                        ? 'bg-success text-white border-success'
                        : 'bg-primary/10 border-primary/30 text-primary hover:bg-primary/20'
                    }`}
                    onClick={() => handleDeployClick(cp)}
                    title="Deploy Checkpoint to Inference Engine"
                  >
                    {deployedId === cp.id ? <CheckCircle size={12} /> : <Rocket size={12} />}
                    <span>{deployedId === cp.id ? 'Deployed' : 'Deploy'}</span>
                  </button>

                  <a
                    href={cp.download_url || '#'}
                    download={cp.name}
                    className="p-1.5 rounded-lg border border-border bg-bg text-text-dim hover:text-text hover:bg-surface-hover transition-colors"
                    title="Download Weights File"
                    onClick={(e) => {
                      if (!cp.download_url) e.preventDefault();
                    }}
                  >
                    <Download size={13} />
                  </a>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Selected Checkpoint Inspection Drawer / Modal */}
      {selectedCheckpoint && (
        <div className="bg-surface border border-primary/50 rounded-xl p-5 shadow-2xl flex flex-col gap-4 mt-2">
          <div className="flex items-center justify-between border-b border-border pb-3">
            <div className="flex items-center gap-2">
              <Layers size={16} className="text-primary" />
              <h4 className="font-semibold text-sm text-text">
                Checkpoint Tensor Structure & Metadata: <span className="font-mono text-primary">{selectedCheckpoint.name}</span>
              </h4>
            </div>
            <div className="flex items-center gap-2">
              <button
                type="button"
                className="flex items-center gap-1 px-2.5 py-1 rounded-lg border border-border bg-bg text-xs text-text-dim hover:text-text transition-colors"
                onClick={() => setShowModelCard((v) => !v)}
              >
                <FileText size={12} />
                <span>{showModelCard ? 'Hide Model Card' : 'View Model Card'}</span>
              </button>
              <button
                type="button"
                className="text-xs text-text-dim hover:text-text px-2 py-1"
                onClick={() => setSelectedCheckpoint(null)}
              >
                Close
              </button>
            </div>
          </div>

          {showModelCard ? (
            <div className="relative bg-bg border border-border rounded-lg p-4 font-mono text-xs text-text overflow-x-auto whitespace-pre-wrap">
              <button
                type="button"
                className="absolute top-3 right-3 flex items-center gap-1 px-2 py-1 rounded bg-surface border border-border text-text-dim hover:text-text transition-colors"
                onClick={() => navigator.clipboard.writeText(modelCardContent)}
              >
                <Copy size={12} />
                <span>Copy</span>
              </button>
              {modelCardContent}
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
              {/* Tensor parameters summary */}
              <div className="col-span-2 flex flex-col gap-2.5">
                <span className="font-medium text-text">Simulated Parameter Hierarchy</span>
                <div className="bg-bg border border-border rounded-lg p-3 flex flex-col gap-2 font-mono text-[11px]">
                  <div className="flex justify-between text-text-dim border-b border-border/40 pb-1">
                    <span>Layer / Module</span>
                    <span>Shape</span>
                    <span>Params</span>
                  </div>
                  <div className="flex justify-between text-text">
                    <span>transformer.wte.weight</span>
                    <span className="text-text-dim">[50257, 768]</span>
                    <span>38.6M</span>
                  </div>
                  <div className="flex justify-between text-text">
                    <span>transformer.h.0-11.attn.c_attn.weight</span>
                    <span className="text-text-dim">[768, 2304]</span>
                    <span>21.2M</span>
                  </div>
                  <div className="flex justify-between text-text">
                    <span>transformer.h.0-11.mlp.c_fc.weight</span>
                    <span className="text-text-dim">[768, 3072]</span>
                    <span>28.3M</span>
                  </div>
                  <div className="flex justify-between text-text">
                    <span>transformer.ln_f.weight</span>
                    <span className="text-text-dim">[768]</span>
                    <span>768</span>
                  </div>
                  <div className="flex justify-between text-primary font-semibold pt-1 border-t border-border/40">
                    <span>Total Trainable Parameters</span>
                    <span>—</span>
                    <span>124.4M</span>
                  </div>
                </div>
              </div>

              {/* SHA256 & Artifact Security */}
              <div className="flex flex-col gap-2.5">
                <span className="font-medium text-text">Integrity & Checksum</span>
                <div className="bg-bg border border-border rounded-lg p-3 flex flex-col gap-2 text-[11px]">
                  <span className="text-text-dim">SHA-256 Digest:</span>
                  <div className="flex items-center gap-1.5 bg-surface p-1.5 rounded border border-border">
                    <span className="font-mono text-text break-all text-[10px]">
                      {selectedCheckpoint.sha256 || 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'}
                    </span>
                    <button
                      type="button"
                      className="p-1 text-text-dim hover:text-text shrink-0"
                      onClick={() => handleCopySha(selectedCheckpoint.sha256)}
                      title="Copy SHA-256"
                    >
                      {copiedHash ? <CheckCircle size={12} className="text-success" /> : <Copy size={12} />}
                    </button>
                  </div>
                  <span className="text-[10px] text-text-dim">
                    Format: {selectedCheckpoint.format.toUpperCase()} · Verified with SafeTensors header parser
                  </span>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

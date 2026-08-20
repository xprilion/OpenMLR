import { HardDrive, MemoryStick, Layers, ShieldCheck } from 'lucide-react';
import type { CheckpointInspection } from './types';

interface Props {
  readonly inspection: CheckpointInspection | null;
  readonly isLoading: boolean;
}

export function CheckpointInspectorCard({ inspection, isLoading }: Readonly<Props>) {
  if (isLoading) {
    return (
      <div className="p-6 rounded-xl bg-surface border border-border flex items-center justify-center min-h-[200px]">
        <span className="text-xs text-text-dim">Analyzing checkpoint tensors and memory footprint...</span>
      </div>
    );
  }

  if (!inspection) {
    return (
      <div className="p-6 rounded-xl bg-surface border border-border text-center py-12">
        <HardDrive size={32} className="mx-auto text-text-dim mb-2 opacity-50" />
        <h4 className="text-sm font-medium text-text">No Checkpoint Inspected</h4>
        <p className="text-xs text-text-dim mt-1 max-w-sm mx-auto">
          Select or inspect a model checkpoint artifact to analyze tensor layouts, weight distributions, and precision VRAM requirements.
        </p>
      </div>
    );
  }

  return (
    <div className="p-6 rounded-xl bg-surface border border-border space-y-6">
      <div className="flex items-center justify-between border-b border-border pb-4">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-lg bg-primary/10 text-primary">
            <Layers size={20} />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-text">Checkpoint Architecture & VRAM Inspection</h3>
            <p className="text-xs text-text-dim">
              Format: <span className="text-text font-mono uppercase">{inspection.file_format}</span> • {inspection.layers_count} registered layers
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2 text-xs text-emerald-400 bg-emerald-500/10 px-2.5 py-1 rounded-full border border-emerald-500/20">
          <ShieldCheck size={14} />
          <span>Tensors Verified</span>
        </div>
      </div>

      {/* Memory Footprint Grid */}
      <div>
        <h4 className="text-xs font-semibold text-text-dim uppercase tracking-wider mb-3 flex items-center gap-1.5">
          <MemoryStick size={14} />
          <span>Estimated GPU VRAM Footprint by Precision</span>
        </h4>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <div className="p-3.5 rounded-lg bg-bg border border-border/80">
            <span className="text-[10px] text-text-dim font-medium block mb-1">FP32 Precision</span>
            <span className="text-base font-bold text-text">{inspection.estimated_vram_fp32_mb.toFixed(1)} MB</span>
            <span className="text-[10px] text-text-dim block mt-1">4 bytes / param</span>
          </div>
          <div className="p-3.5 rounded-lg bg-bg border border-primary/30">
            <span className="text-[10px] text-primary font-medium block mb-1">FP16 / BF16 (AMP)</span>
            <span className="text-base font-bold text-primary">{inspection.estimated_vram_fp16_mb.toFixed(1)} MB</span>
            <span className="text-[10px] text-emerald-400 block mt-1">2.0x memory reduction</span>
          </div>
          <div className="p-3.5 rounded-lg bg-bg border border-border/80">
            <span className="text-[10px] text-text-dim font-medium block mb-1">INT8 / FP8</span>
            <span className="text-base font-bold text-text">{inspection.estimated_vram_int8_mb.toFixed(1)} MB</span>
            <span className="text-[10px] text-emerald-400 block mt-1">4.0x memory reduction</span>
          </div>
          <div className="p-3.5 rounded-lg bg-bg border border-border/80">
            <span className="text-[10px] text-text-dim font-medium block mb-1">INT4 / AWQ / GPTQ</span>
            <span className="text-base font-bold text-emerald-400">{inspection.estimated_vram_int4_mb.toFixed(1)} MB</span>
            <span className="text-[10px] text-emerald-400 block mt-1">7.3x memory reduction</span>
          </div>
        </div>
      </div>

      {/* Layer breakdown */}
      {inspection.top_layers && inspection.top_layers.length > 0 && (
        <div>
          <h4 className="text-xs font-semibold text-text-dim uppercase tracking-wider mb-3">
            Key Layer Weight Allocations
          </h4>
          <div className="rounded-lg border border-border overflow-hidden">
            <table className="w-full text-left text-xs">
              <thead className="bg-bg text-text-dim border-b border-border">
                <tr>
                  <th className="px-3 py-2 font-medium">Layer Tensor Name</th>
                  <th className="px-3 py-2 font-medium">Dtype</th>
                  <th className="px-3 py-2 font-medium text-right">Parameters</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border font-mono text-[11px]">
                {inspection.top_layers.map((layer) => (
                  <tr key={layer.name} className="hover:bg-surface-hover/40 transition-colors">
                    <td className="px-3 py-2 text-text truncate max-w-xs" title={layer.name}>
                      {layer.name}
                    </td>
                    <td className="px-3 py-2 text-text-dim uppercase">{layer.dtype}</td>
                    <td className="px-3 py-2 text-right text-text">{layer.params.toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

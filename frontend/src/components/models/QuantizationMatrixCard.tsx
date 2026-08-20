import { Gauge, Cpu, CheckCircle2, Zap } from 'lucide-react';
import type { QuantizationEstimate } from './types';

interface Props {
  readonly estimates: QuantizationEstimate[];
  readonly isLoading: boolean;
  readonly modelName?: string;
}

export function QuantizationMatrixCard({ estimates, isLoading, modelName }: Readonly<Props>) {
  if (isLoading) {
    return (
      <div className="p-6 rounded-xl bg-surface border border-border flex items-center justify-center min-h-[200px]">
        <span className="text-xs text-text-dim">Computing precision trade-offs and quantization metrics...</span>
      </div>
    );
  }

  if (!estimates || estimates.length === 0) {
    return (
      <div className="p-6 rounded-xl bg-surface border border-border text-center py-12">
        <Gauge size={32} className="mx-auto text-text-dim mb-2 opacity-50" />
        <h4 className="text-sm font-medium text-text">No Quantization Strategy Active</h4>
        <p className="text-xs text-text-dim mt-1 max-w-sm mx-auto">
          Evaluate quantization profiles for the selected model artifact to estimate compression, VRAM reduction, and execution latency.
        </p>
      </div>
    );
  }

  return (
    <div className="p-6 rounded-xl bg-surface border border-border space-y-6">
      <div className="flex items-center justify-between border-b border-border pb-4">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-lg bg-primary/10 text-primary">
            <Zap size={20} />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-text">
              Quantization & Compression Matrix: {modelName || 'Artifact'}
            </h3>
            <p className="text-xs text-text-dim">
              Precision trade-off analysis across modern inference acceleration engines
            </p>
          </div>
        </div>
      </div>

      <div className="rounded-lg border border-border overflow-hidden">
        <table className="w-full text-left text-xs">
          <thead className="bg-bg text-text-dim border-b border-border">
            <tr>
              <th className="px-4 py-3 font-medium">Target Precision</th>
              <th className="px-4 py-3 font-medium">Est. Size</th>
              <th className="px-4 py-3 font-medium">VRAM Footprint</th>
              <th className="px-4 py-3 font-medium">Compression</th>
              <th className="px-4 py-3 font-medium">Est. Speedup</th>
              <th className="px-4 py-3 font-medium">Recommended Runtime / Engine</th>
              <th className="px-4 py-3 font-medium">Accuracy Impact</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border text-text">
            {estimates.map((est) => (
              <tr key={est.target_precision} className="hover:bg-surface-hover/40 transition-colors">
                <td className="px-4 py-3 font-bold text-primary flex items-center gap-1.5">
                  <Cpu size={14} />
                  <span>{est.target_precision}</span>
                </td>
                <td className="px-4 py-3 font-mono">{est.estimated_size_mb.toFixed(1)} MB</td>
                <td className="px-4 py-3 font-mono">{est.estimated_vram_mb.toFixed(1)} MB</td>
                <td className="px-4 py-3 font-bold text-emerald-400">{est.compression_ratio.toFixed(1)}x</td>
                <td className="px-4 py-3 font-bold text-amber-400">{est.expected_latency_speedup.toFixed(1)}x</td>
                <td className="px-4 py-3 text-text-dim text-[11px] max-w-xs truncate" title={est.suggested_engine}>
                  {est.suggested_engine}
                </td>
                <td className="px-4 py-3 text-text-dim text-[11px] flex items-center gap-1">
                  <CheckCircle2 size={12} className="text-primary shrink-0" />
                  <span>{est.loss_tolerance_level}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

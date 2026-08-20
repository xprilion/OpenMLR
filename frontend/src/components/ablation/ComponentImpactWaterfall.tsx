import React from 'react';
import { Award, AlertTriangle, Lightbulb } from 'lucide-react';
import type { ComponentImpact } from './types';

interface ComponentImpactWaterfallProps {
  impacts: ComponentImpact[];
  primaryMetric: string;
}

export const ComponentImpactWaterfall: React.FC<ComponentImpactWaterfallProps> = ({
  impacts,
  primaryMetric,
}) => {
  if (!impacts || impacts.length === 0) {
    return (
      <div className="p-4 rounded-lg border border-border bg-surface/30 text-text-dim text-sm text-center">
        No component impacts computed yet. Add ablation variants with removed components to see contribution ranking.
      </div>
    );
  }

  const maxImpact = Math.max(...impacts.map((i) => i.impact_score), 0.001);

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h4 className="text-sm font-semibold text-text flex items-center gap-2">
          <Award className="w-4 h-4 text-primary" />
          Component Contribution &amp; Sensitivity Ranking ({primaryMetric})
        </h4>
        <span className="text-xs text-text-dim">
          Ranked by absolute degradation when removed
        </span>
      </div>

      <div className="space-y-2.5">
        {impacts.map((imp) => {
          const widthPct = Math.min(100, Math.max(8, (imp.impact_score / maxImpact) * 100));

          return (
            <div
              key={imp.component_name}
              className={`p-3 rounded-lg border transition-all ${
                imp.is_critical
                  ? 'border-border bg-surface hover:border-primary/50'
                  : 'border-border/60 bg-surface/40 hover:border-border'
              }`}
            >
              <div className="flex items-center justify-between gap-2 mb-1.5">
                <div className="flex items-center gap-2">
                  <span className="font-medium text-sm text-text">
                    {imp.component_name}
                  </span>
                  {imp.is_critical ? (
                    <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-rose-950/60 text-rose-400 border border-rose-800/40 flex items-center gap-1">
                      <AlertTriangle className="w-2.5 h-2.5" />
                      Critical (p &lt; 0.05)
                    </span>
                  ) : (
                    <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-zinc-800 text-zinc-400 border border-border">
                      Marginal
                    </span>
                  )}
                </div>

                <div className="text-right font-mono text-xs text-text">
                  <span className="font-semibold text-rose-400">-{imp.impact_score.toFixed(4)}</span>
                  <span className="text-text-dim ml-1">(-{imp.relative_drop_pct.toFixed(1)}%)</span>
                </div>
              </div>

              {/* Progress visual bar */}
              <div className="w-full h-1.5 rounded-full bg-zinc-800 overflow-hidden mb-2">
                <div
                  className={`h-full rounded-full transition-all ${
                    imp.is_critical ? 'bg-rose-500' : 'bg-zinc-500'
                  }`}
                  style={{ width: `${widthPct}%` }}
                />
              </div>

              <div className="text-xs text-text-dim flex items-start gap-1.5 bg-background/50 p-2 rounded border border-border/30">
                <Lightbulb className="w-3.5 h-3.5 text-primary shrink-0 mt-0.5" />
                <span>{imp.recommendation}</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

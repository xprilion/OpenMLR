import React from 'react';
import { CheckCircle2, AlertCircle, HelpCircle, ArrowDown, ArrowUp, Minus } from 'lucide-react';
import type { AblationStudy, SignificanceComparison } from './types';

interface SignificanceTableProps {
  study: AblationStudy;
  selectedMetric: string;
  onSelectVariant?: (variantName: string) => void;
}

export const SignificanceTable: React.FC<SignificanceTableProps> = ({
  study,
  selectedMetric,
  onSelectVariant,
}) => {
  const comparisons: SignificanceComparison[] = study.comparisons[selectedMetric] || [];
  const baseline = study.variants[study.baseline_variant_name];
  const baselineAgg = baseline?.metrics[selectedMetric];

  const getSignificanceBadge = (comp: SignificanceComparison) => {
    const symbol = comp.significance_symbol;
    if (symbol === '***' || symbol === '**' || symbol === '*') {
      const isPositive = study.higher_is_better ? comp.delta_abs > 0 : comp.delta_abs < 0;
      return (
        <span
          className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-semibold ${
            isPositive ? 'bg-emerald-950/60 text-emerald-400 border border-emerald-800/40' : 'bg-rose-950/60 text-rose-400 border border-rose-800/40'
          }`}
          title={`p-adj = ${comp.p_value_adjusted.toFixed(4)} (${comp.test_type})`}
        >
          <CheckCircle2 className="w-3 h-3" />
          {symbol} (p &lt; {comp.p_value_adjusted < 0.001 ? '0.001' : comp.p_value_adjusted < 0.01 ? '0.01' : '0.05'})
        </span>
      );
    }
    if (symbol === '.') {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-amber-950/60 text-amber-400 border border-amber-800/40">
          <AlertCircle className="w-3 h-3" />
          . (p &lt; 0.10)
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-zinc-800/60 text-zinc-400 border border-zinc-700/40">
        <HelpCircle className="w-3 h-3" />
        ns (p &ge; 0.10)
      </span>
    );
  };

  const getEffectSizeBadge = (cohenD: number) => {
    const absD = Math.abs(cohenD);
    let label = 'Negligible';
    let color = 'text-zinc-400';
    if (absD >= 0.8) {
      label = 'Large';
      color = 'text-purple-400 font-semibold';
    } else if (absD >= 0.5) {
      label = 'Medium';
      color = 'text-blue-400 font-medium';
    } else if (absD >= 0.2) {
      label = 'Small';
      color = 'text-cyan-400';
    }
    return (
      <span className={`text-xs ${color}`} title={`Cohen's d = ${cohenD.toFixed(3)}`}>
        {cohenD > 0 ? `+${cohenD.toFixed(2)}` : cohenD.toFixed(2)} ({label})
      </span>
    );
  };

  return (
    <div className="w-full overflow-x-auto rounded-lg border border-border bg-surface/50">
      <table className="w-full text-left text-sm text-text">
        <thead className="bg-surface text-text-dim text-xs uppercase border-b border-border">
          <tr>
            <th className="px-4 py-3 font-semibold">Variant Configuration</th>
            <th className="px-4 py-3 font-semibold text-center">Type</th>
            <th className="px-4 py-3 font-semibold text-right">Mean ± Std</th>
            <th className="px-4 py-3 font-semibold text-right">Δ from Baseline</th>
            <th className="px-4 py-3 font-semibold text-center">Effect Size (d)</th>
            <th className="px-4 py-3 font-semibold text-center">Significance (Holm)</th>
            <th className="px-4 py-3 font-semibold text-center">95% CI of Δ</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border/50">
          {/* Baseline Row */}
          {baseline && (
            <tr className="bg-primary/5 hover:bg-primary/10 transition-colors">
              <td className="px-4 py-3 font-semibold text-text flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-primary" />
                {baseline.name} <span className="text-xs text-primary font-normal">(Baseline)</span>
              </td>
              <td className="px-4 py-3 text-center">
                <span className="px-2 py-0.5 rounded text-[11px] bg-primary/20 text-primary border border-primary/30 font-medium">
                  baseline
                </span>
              </td>
              <td className="px-4 py-3 text-right font-mono font-medium text-text">
                {baselineAgg ? `${baselineAgg.mean.toFixed(4)} ± ${baselineAgg.std.toFixed(4)}` : '--'}
              </td>
              <td className="px-4 py-3 text-right text-text-dim font-mono text-xs">-- (ref)</td>
              <td className="px-4 py-3 text-center text-text-dim text-xs">--</td>
              <td className="px-4 py-3 text-center text-text-dim text-xs">--</td>
              <td className="px-4 py-3 text-center text-text-dim text-xs font-mono">
                {baselineAgg ? `[${baselineAgg.ci_lower.toFixed(3)}, ${baselineAgg.ci_upper.toFixed(3)}]` : '--'}
              </td>
            </tr>
          )}

          {/* Variants Rows */}
          {Object.entries(study.variants).map(([vName, vRes]) => {
            if (vName === study.baseline_variant_name) return null;
            const comp = comparisons.find((c) => c.variant_name === vName);
            const agg = vRes.metrics[selectedMetric];

            const isGood = study.higher_is_better ? (comp?.delta_abs ?? 0) > 0 : (comp?.delta_abs ?? 0) < 0;
            const isBad = study.higher_is_better ? (comp?.delta_abs ?? 0) < 0 : (comp?.delta_abs ?? 0) > 0;

            return (
              <tr
                key={vName}
                className="hover:bg-surface-hover/50 transition-colors cursor-pointer"
                onClick={() => onSelectVariant?.(vName)}
              >
                <td className="px-4 py-3">
                  <div className="font-medium text-text">{vName}</div>
                  {vRes.removed_components.length > 0 && (
                    <div className="text-xs text-rose-400/80 mt-0.5">
                      Removed: {vRes.removed_components.join(', ')}
                    </div>
                  )}
                  {vRes.added_components.length > 0 && (
                    <div className="text-xs text-emerald-400/80 mt-0.5">
                      Added: {vRes.added_components.join(', ')}
                    </div>
                  )}
                </td>
                <td className="px-4 py-3 text-center">
                  <span className="px-2 py-0.5 rounded text-[11px] bg-zinc-800 text-zinc-300 border border-border">
                    {vRes.variant_type}
                  </span>
                </td>
                <td className="px-4 py-3 text-right font-mono text-text">
                  {agg ? `${agg.mean.toFixed(4)} ± ${agg.std.toFixed(4)}` : '--'}
                </td>
                <td className="px-4 py-3 text-right font-mono">
                  {comp ? (
                    <div className={`flex items-center justify-end gap-1 ${isGood ? 'text-emerald-400' : isBad ? 'text-rose-400' : 'text-zinc-400'}`}>
                      {comp.delta_abs > 0 ? <ArrowUp className="w-3.5 h-3.5" /> : comp.delta_abs < 0 ? <ArrowDown className="w-3.5 h-3.5" /> : <Minus className="w-3.5 h-3.5" />}
                      <span>{comp.delta_abs > 0 ? `+${comp.delta_abs.toFixed(4)}` : comp.delta_abs.toFixed(4)}</span>
                      <span className="text-xs text-text-dim">({comp.delta_pct > 0 ? `+${comp.delta_pct.toFixed(1)}%` : `${comp.delta_pct.toFixed(1)}%`})</span>
                    </div>
                  ) : (
                    '--'
                  )}
                </td>
                <td className="px-4 py-3 text-center">
                  {comp ? getEffectSizeBadge(comp.effect_size_cohen_d) : '--'}
                </td>
                <td className="px-4 py-3 text-center">
                  {comp ? getSignificanceBadge(comp) : '--'}
                </td>
                <td className="px-4 py-3 text-center font-mono text-xs text-text-dim">
                  {comp ? `[${comp.ci_diff_lower.toFixed(3)}, ${comp.ci_diff_upper.toFixed(3)}]` : '--'}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
};

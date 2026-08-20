import React, { useMemo, useState } from 'react';
import type { SweepConfig, Trial } from './types';

interface SweepParallelCoordinatesProps {
  sweep: SweepConfig;
}

export const SweepParallelCoordinates: React.FC<SweepParallelCoordinatesProps> = ({ sweep }) => {
  const [hoveredTrial, setHoveredTrial] = useState<string | null>(null);

  const completedTrials = useMemo(() => {
    return sweep.trials.filter((t) => t.status === 'completed' && t.objective_value !== undefined);
  }, [sweep.trials]);

  // Dimension axes: all numerical/categorical parameters + objective metric
  const axes = useMemo(() => {
    const list: { key: string; label: string; min: number; max: number; isCategorical?: boolean; choices?: string[] }[] = [];

    Object.entries(sweep.parameters).forEach(([name, spec]) => {
      if (spec.choices && spec.choices.length > 0) {
        const choiceStrings = spec.choices.map(String);
        list.push({
          key: name,
          label: name,
          min: 0,
          max: choiceStrings.length - 1,
          isCategorical: true,
          choices: choiceStrings,
        });
      } else {
        const minVal = spec.min_val ?? 0;
        const maxVal = spec.max_val ?? 1;
        list.push({
          key: name,
          label: name,
          min: minVal,
          max: Math.max(minVal + 1e-4, maxVal),
        });
      }
    });

    // Objective metric axis
    const objValues = completedTrials.map((t) => t.objective_value ?? 0);
    const minObj = objValues.length > 0 ? Math.min(...objValues) : 0;
    const maxObj = objValues.length > 0 ? Math.max(...objValues) : 1;
    list.push({
      key: sweep.objective_metric,
      label: `${sweep.objective_metric} (${sweep.goal})`,
      min: minObj,
      max: Math.max(minObj + 1e-4, maxObj),
    });

    return list;
  }, [sweep, completedTrials]);

  const svgWidth = 700;
  const svgHeight = 280;
  const paddingX = 60;
  const paddingY = 40;

  const getX = (axisIndex: number) => {
    if (axes.length <= 1) return svgWidth / 2;
    return paddingX + (axisIndex / (axes.length - 1)) * (svgWidth - 2 * paddingX);
  };

  const getY = (axisIndex: number, rawVal: number | string | undefined) => {
    const axis = axes[axisIndex];
    let numeric: number;
    if (axis.isCategorical && axis.choices) {
      const idx = axis.choices.indexOf(String(rawVal));
      numeric = idx >= 0 ? idx : 0;
    } else {
      numeric = typeof rawVal === 'number' ? rawVal : Number(rawVal) || 0;
    }

    const range = Math.max(1e-6, axis.max - axis.min);
    const norm = Math.max(0, Math.min(1, (numeric - axis.min) / range));
    return svgHeight - paddingY - norm * (svgHeight - 2 * paddingY);
  };

  if (completedTrials.length === 0) {
    return (
      <div className="bg-surface/50 border border-border rounded-lg p-8 text-center text-text-dim">
        <p className="text-sm">No completed trials yet to render parallel coordinates chart.</p>
      </div>
    );
  }

  return (
    <div className="bg-surface border border-border rounded-lg p-4 flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <h4 className="text-sm font-semibold text-text flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-primary" />
          {' '}
          Hyperparameter Parallel Coordinates
        </h4>
        <span className="text-xs text-text-dim">{completedTrials.length} completed trials plotted</span>
      </div>

      <div className="w-full overflow-x-auto">
        <svg viewBox={`0 0 ${svgWidth} ${svgHeight}`} className="w-full h-auto min-w-[500px]">
          {/* Axis vertical lines */}
          {axes.map((axis, i) => {
            const x = getX(i);
            return (
              <g key={axis.key}>
                <line
                  x1={x}
                  y1={paddingY}
                  x2={x}
                  y2={svgHeight - paddingY}
                  stroke="#27272a"
                  strokeWidth="2"
                  strokeDasharray="2 2"
                />
                {/* Axis label */}
                <text
                  x={x}
                  y={paddingY - 14}
                  textAnchor="middle"
                  className="fill-text-dim text-[11px] font-mono"
                >
                  {axis.label}
                </text>
                {/* Min / Max ticks */}
                <text
                  x={x}
                  y={svgHeight - paddingY + 16}
                  textAnchor="middle"
                  className="fill-text-dim text-[10px] font-mono"
                >
                  {axis.isCategorical && axis.choices ? axis.choices[0] : axis.min.toFixed(2)}
                </text>
                <text
                  x={x}
                  y={paddingY - 2}
                  textAnchor="middle"
                  className="fill-text-dim text-[10px] font-mono"
                >
                  {axis.isCategorical && axis.choices ? axis.choices[axis.choices.length - 1] : axis.max.toFixed(2)}
                </text>
              </g>
            );
          })}

          {/* Trial Paths */}
          {completedTrials.map((trial: Trial) => {
            const isHovered = hoveredTrial === trial.trial_id;
            const points = axes.map((axis, i) => {
              const val = axis.key === sweep.objective_metric ? trial.objective_value : trial.parameters[axis.key];
              return `${getX(i)},${getY(i, val)}`;
            });
            const d = `M ${points.join(' L ')}`;

            return (
              <path
                key={trial.trial_id}
                d={d}
                fill="none"
                stroke={isHovered ? '#1288ff' : '#38bdf8'}
                strokeWidth={isHovered ? 3 : 1.5}
                strokeOpacity={isHovered ? 1 : 0.45}
                className="cursor-pointer transition-all duration-150"
                onMouseEnter={() => setHoveredTrial(trial.trial_id)}
                onMouseLeave={() => setHoveredTrial(null)}
              />
            );
          })}
        </svg>
      </div>
    </div>
  );
};

import React, { useState, useMemo, useRef, useCallback } from 'react';
import { 
  LineChart as ChartIcon, 
  Download, 
  Sliders, 
  Eye, 
  EyeOff
} from 'lucide-react';
import type { MetricSeries, XAxisMode, ScaleMode, MetricPoint } from './types';

interface MetricChartsProps {
  readonly title: string;
  readonly series: readonly MetricSeries[];
  readonly height?: number;
  readonly defaultXAxis?: XAxisMode;
  readonly defaultScale?: ScaleMode;
  readonly showControls?: boolean;
}

export function MetricCharts({
  title,
  series,
  height = 280,
  defaultXAxis = 'step',
  defaultScale = 'linear',
  showControls = true,
}: Readonly<MetricChartsProps>) {
  const [xAxisMode, setXAxisMode] = useState<XAxisMode>(defaultXAxis);
  const [scaleMode, setScaleMode] = useState<ScaleMode>(defaultScale);
  const [smoothing, setSmoothing] = useState<number>(0.0); // 0 to 0.95
  const [hiddenSeries, setHiddenSeries] = useState<Record<string, boolean>>({});
  const [hoverIndex, setHoverIndex] = useState<{ x: number; points: { name: string; color: string; val: number }[] } | null>(null);
  const [stepRange, setStepRange] = useState<'all' | '100' | '500'>('all');
  const svgRef = useRef<SVGSVGElement | null>(null);

  const toggleSeries = useCallback((id: string) => {
    setHiddenSeries((prev) => ({ ...prev, [id]: !prev[id] }));
  }, []);

  const smoothData = useCallback((points: MetricPoint[], weight: number): MetricPoint[] => {
    if (weight <= 0 || points.length <= 1) return points;
    const result: MetricPoint[] = [];
    let last = points[0].value;
    for (let i = 0; i < points.length; i++) {
      const pt = points[i];
      if (i === 0) {
        result.push(pt);
      } else {
        last = last * weight + (1 - weight) * pt.value;
        result.push({ ...pt, value: last });
      }
    }
    return result;
  }, []);

  // Filter series according to range and visibility
  const activeSeries = useMemo(() => {
    return series.filter((s) => !hiddenSeries[s.id]).map((s) => {
      let data = s.data;
      if (stepRange === '100') {
        data = data.slice(-100);
      } else if (stepRange === '500') {
        data = data.slice(-500);
      }
      return {
        ...s,
        data: smoothData(data, smoothing),
      };
    });
  }, [series, hiddenSeries, stepRange, smoothing, smoothData]);

  // Compute bounds
  const { minX, maxX, minY, maxY, allPointsCount } = useMemo(() => {
    let minXVal = Number.POSITIVE_INFINITY;
    let maxXVal = Number.NEGATIVE_INFINITY;
    let minYVal = Number.POSITIVE_INFINITY;
    let maxYVal = Number.NEGATIVE_INFINITY;
    let count = 0;

    for (const s of activeSeries) {
      count += s.data.length;
      for (const pt of s.data) {
        const x = xAxisMode === 'step' ? pt.step : (xAxisMode === 'epoch' ? pt.epoch : (pt.timestamp / 1000));
        if (x < minXVal) minXVal = x;
        if (x > maxXVal) maxXVal = x;

        let y = pt.value;
        if (scaleMode === 'log') {
          y = y > 0 ? Math.log10(y) : 0;
        }
        if (y < minYVal) minYVal = y;
        if (y > maxYVal) maxYVal = y;
      }
    }

    if (minXVal === Number.POSITIVE_INFINITY) minXVal = 0;
    if (maxXVal === Number.NEGATIVE_INFINITY || maxXVal === minXVal) maxXVal = minXVal + 1;
    if (minYVal === Number.POSITIVE_INFINITY) minYVal = 0;
    if (maxYVal === Number.NEGATIVE_INFINITY || maxYVal === minYVal) maxYVal = minYVal + 1;

    // Add 5% padding to Y
    const yPad = (maxYVal - minYVal) * 0.05 || 0.1;
    return {
      minX: minXVal,
      maxX: maxXVal,
      minY: minYVal - yPad,
      maxY: maxYVal + yPad,
      allPointsCount: count,
    };
  }, [activeSeries, xAxisMode, scaleMode]);

  // SVG viewport
  const padding = { top: 15, right: 20, bottom: 25, left: 45 };
  const width = 600;
  const plotWidth = width - padding.left - padding.right;
  const plotHeight = height - padding.top - padding.bottom;

  const getCoordinates = useCallback((pt: MetricPoint) => {
    const xVal = xAxisMode === 'step' ? pt.step : (xAxisMode === 'epoch' ? pt.epoch : (pt.timestamp / 1000));
    let yVal = pt.value;
    if (scaleMode === 'log') {
      yVal = yVal > 0 ? Math.log10(yVal) : 0;
    }
    const xRatio = (xVal - minX) / (maxX - minX || 1);
    const yRatio = (yVal - minY) / (maxY - minY || 1);
    const svgX = padding.left + xRatio * plotWidth;
    const svgY = padding.top + (1 - yRatio) * plotHeight;
    return { svgX, svgY };
  }, [xAxisMode, scaleMode, minX, maxX, minY, maxY, padding.left, padding.top, plotWidth, plotHeight]);

  // Generate SVG paths
  const seriesPaths = useMemo(() => {
    return activeSeries.map((s) => {
      if (s.data.length === 0) return { ...s, pathD: '' };
      const d = s.data.reduce((acc, pt, idx) => {
        const { svgX, svgY } = getCoordinates(pt);
        return idx === 0 ? `M ${svgX.toFixed(1)} ${svgY.toFixed(1)}` : `${acc} L ${svgX.toFixed(1)} ${svgY.toFixed(1)}`;
      }, '');
      return { ...s, pathD: d };
    });
  }, [activeSeries, getCoordinates]);

  // Mouse move over SVG for tooltip
  const handleMouseMove = useCallback((e: React.MouseEvent<SVGSVGElement>) => {
    if (!svgRef.current || activeSeries.length === 0) return;
    const rect = svgRef.current.getBoundingClientRect();
    const clickX = e.clientX - rect.left;
    const normX = ((clickX - padding.left) / plotWidth);
    if (normX < 0 || normX > 1) {
      setHoverIndex(null);
      return;
    }
    const targetXVal = minX + normX * (maxX - minX);

    // Find closest points
    const points: { name: string; color: string; val: number }[] = [];
    for (const s of activeSeries) {
      if (s.data.length === 0) continue;
      let closestPt = s.data[0];
      let minDiff = Number.POSITIVE_INFINITY;
      for (const pt of s.data) {
        const ptX = xAxisMode === 'step' ? pt.step : (xAxisMode === 'epoch' ? pt.epoch : (pt.timestamp / 1000));
        const diff = Math.abs(ptX - targetXVal);
        if (diff < minDiff) {
          minDiff = diff;
          closestPt = pt;
        }
      }
      points.push({ name: s.name, color: s.color, val: closestPt.value });
    }

    setHoverIndex({ x: clickX, points });
  }, [activeSeries, minX, maxX, xAxisMode, padding.left, plotWidth]);

  const handleMouseLeave = useCallback(() => {
    setHoverIndex(null);
  }, []);

  const handleExportSVG = useCallback(() => {
    if (!svgRef.current) return;
    const svgData = new XMLSerializer().serializeToString(svgRef.current);
    const blob = new Blob([svgData], { type: 'image/svg+xml;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${title.toLowerCase().replace(/\s+/g, '_')}_chart.svg`;
    a.click();
    URL.revokeObjectURL(url);
  }, [title]);

  // Format tick labels
  const yTicks = useMemo(() => {
    const ticks = [];
    const count = 4;
    for (let i = 0; i <= count; i++) {
      const val = minY + (i / count) * (maxY - minY);
      const displayVal = scaleMode === 'log' ? Math.pow(10, val) : val;
      const formatted = displayVal < 0.01 && displayVal > 0 ? displayVal.toExponential(1) : displayVal.toFixed(displayVal < 1 ? 3 : 1);
      const svgY = padding.top + (1 - i / count) * plotHeight;
      ticks.push({ svgY, label: formatted });
    }
    return ticks;
  }, [minY, maxY, scaleMode, padding.top, plotHeight]);

  const xTicks = useMemo(() => {
    const ticks = [];
    const count = 5;
    for (let i = 0; i <= count; i++) {
      const val = minX + (i / count) * (maxX - minX);
      const svgX = padding.left + (i / count) * plotWidth;
      const formatted = xAxisMode === 'time' ? `${val.toFixed(0)}s` : `${Math.round(val)}`;
      ticks.push({ svgX, label: formatted });
    }
    return ticks;
  }, [minX, maxX, xAxisMode, padding.left, plotWidth]);

  return (
    <div className="bg-surface/80 border border-border rounded-xl p-4 flex flex-col gap-3">
      {/* Header & Controls */}
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center gap-2">
          <ChartIcon size={16} className="text-primary" />
          <h4 className="text-sm font-semibold text-text tracking-tight">{title}</h4>
          <span className="text-xs text-text-dim px-2 py-0.5 rounded-full bg-bg border border-border">
            {allPointsCount} pts
          </span>
        </div>

        {showControls && (
          <div className="flex items-center gap-2 flex-wrap">
            {/* Range filter */}
            <div className="flex items-center bg-bg border border-border rounded-lg p-0.5 text-xs">
              <button
                type="button"
                className={`px-2 py-1 rounded transition-colors ${stepRange === 'all' ? 'bg-primary text-white font-medium' : 'text-text-dim hover:text-text'}`}
                onClick={() => setStepRange('all')}
              >
                All
              </button>
              <button
                type="button"
                className={`px-2 py-1 rounded transition-colors ${stepRange === '500' ? 'bg-primary text-white font-medium' : 'text-text-dim hover:text-text'}`}
                onClick={() => setStepRange('500')}
              >
                500
              </button>
              <button
                type="button"
                className={`px-2 py-1 rounded transition-colors ${stepRange === '100' ? 'bg-primary text-white font-medium' : 'text-text-dim hover:text-text'}`}
                onClick={() => setStepRange('100')}
              >
                100
              </button>
            </div>

            {/* X-Axis Mode */}
            <div className="flex items-center bg-bg border border-border rounded-lg p-0.5 text-xs">
              <button
                type="button"
                className={`px-2 py-1 rounded transition-colors ${xAxisMode === 'step' ? 'bg-surface-hover text-primary font-medium' : 'text-text-dim hover:text-text'}`}
                onClick={() => setXAxisMode('step')}
              >
                Step
              </button>
              <button
                type="button"
                className={`px-2 py-1 rounded transition-colors ${xAxisMode === 'epoch' ? 'bg-surface-hover text-primary font-medium' : 'text-text-dim hover:text-text'}`}
                onClick={() => setXAxisMode('epoch')}
              >
                Epoch
              </button>
              <button
                type="button"
                className={`px-2 py-1 rounded transition-colors ${xAxisMode === 'time' ? 'bg-surface-hover text-primary font-medium' : 'text-text-dim hover:text-text'}`}
                onClick={() => setXAxisMode('time')}
              >
                Time
              </button>
            </div>

            {/* Scale toggle */}
            <button
              type="button"
              className={`px-2 py-1 rounded-lg border text-xs transition-colors ${scaleMode === 'log' ? 'bg-primary/15 text-primary border-primary/40' : 'bg-bg border-border text-text-dim hover:text-text'}`}
              onClick={() => setScaleMode((m) => (m === 'linear' ? 'log' : 'linear'))}
              title="Toggle Log Scale"
            >
              {scaleMode.toUpperCase()}
            </button>

            {/* Smoothing Slider */}
            <div className="flex items-center gap-1 bg-bg border border-border rounded-lg px-2 py-1 text-xs text-text-dim">
              <Sliders size={12} />
              <span>EMA: {(smoothing * 100).toFixed(0)}%</span>
              <input
                type="range"
                min="0"
                max="0.95"
                step="0.05"
                value={smoothing}
                onChange={(e) => setSmoothing(Number.parseFloat(e.target.value))}
                className="w-14 h-1 bg-surface-hover rounded-lg appearance-none cursor-pointer accent-primary"
                aria-label="Exponential Moving Average Smoothing"
              />
            </div>

            {/* Export SVG */}
            <button
              type="button"
              className="p-1.5 rounded-lg border border-border bg-bg text-text-dim hover:text-text hover:bg-surface-hover transition-colors"
              onClick={handleExportSVG}
              title="Export SVG Chart"
            >
              <Download size={14} />
            </button>
          </div>
        )}
      </div>

      {/* SVG Canvas Area */}
      <div className="relative w-full overflow-hidden select-none bg-bg/50 rounded-lg border border-border/50">
        <svg
          ref={svgRef}
          viewBox={`0 0 ${width} ${height}`}
          className="w-full h-auto max-h-[340px]"
          onMouseMove={handleMouseMove}
          onMouseLeave={handleMouseLeave}
        >
          {/* Grid lines */}
          {yTicks.map((t, idx) => (
            <g key={`ytick-${t.label}-${idx}`}>
              <line
                x1={padding.left}
                y1={t.svgY}
                x2={width - padding.right}
                y2={t.svgY}
                stroke="currentColor"
                className="text-border/40"
                strokeDasharray="2 2"
                strokeWidth={1}
              />
              <text
                x={padding.left - 6}
                y={t.svgY + 3}
                fill="currentColor"
                className="text-[10px] text-text-dim/80 fill-current"
                textAnchor="end"
              >
                {t.label}
              </text>
            </g>
          ))}

          {xTicks.map((t, idx) => (
            <g key={`xtick-${t.label}-${idx}`}>
              <line
                x1={t.svgX}
                y1={padding.top}
                x2={t.svgX}
                y2={height - padding.bottom}
                stroke="currentColor"
                className="text-border/40"
                strokeDasharray="2 2"
                strokeWidth={1}
              />
              <text
                x={t.svgX}
                y={height - padding.bottom + 14}
                fill="currentColor"
                className="text-[10px] text-text-dim/80 fill-current"
                textAnchor="middle"
              >
                {t.label}
              </text>
            </g>
          ))}

          {/* Series lines */}
          {seriesPaths.map((s) => (
            <path
              key={s.id}
              d={s.pathD}
              fill="none"
              stroke={s.color}
              strokeWidth={2}
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          ))}

          {/* Hover Crosshair line */}
          {hoverIndex && (
            <line
              x1={hoverIndex.x}
              y1={padding.top}
              x2={hoverIndex.x}
              y2={height - padding.bottom}
              stroke="#1288ff"
              strokeWidth={1.5}
              strokeDasharray="3 3"
            />
          )}
        </svg>

        {/* Hover Tooltip Overlay */}
        {hoverIndex && (
          <div
            className="absolute top-2 pointer-events-none bg-surface/95 backdrop-blur-sm border border-border rounded-lg shadow-xl p-2 text-xs flex flex-col gap-1 z-20"
            style={{
              left: Math.min(hoverIndex.x + 10, width - 180),
            }}
          >
            {hoverIndex.points.map((p) => (
              <div key={p.name} className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full" style={{ backgroundColor: p.color }} />
                <span className="text-text-dim">{p.name}:</span>
                <span className="font-mono text-text font-medium">{p.val.toFixed(4)}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Legend & Series Toggles */}
      <div className="flex items-center flex-wrap gap-3 pt-1 border-t border-border/40 text-xs">
        {series.map((s) => {
          const isHidden = hiddenSeries[s.id];
          return (
            <button
              key={s.id}
              type="button"
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg border transition-all ${isHidden ? 'opacity-40 border-border bg-bg text-text-dim' : 'border-border/80 bg-surface text-text hover:border-primary/50'}`}
              onClick={() => toggleSeries(s.id)}
            >
              <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: s.color }} />
              <span className="font-medium">{s.name}</span>
              {isHidden ? <EyeOff size={12} className="text-text-dim" /> : <Eye size={12} className="text-primary" />}
            </button>
          );
        })}
      </div>
    </div>
  );
}

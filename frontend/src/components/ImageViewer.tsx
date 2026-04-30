
import { useState, useRef, useCallback, useEffect } from 'react';
import { ZoomIn, ZoomOut, RotateCw, Maximize2, Minimize2 } from 'lucide-react';

interface Props {
  readonly src: string;
  readonly filename: string;
}

export function ImageViewer({ src, filename }: Props) {
  const [zoom, setZoom] = useState(1);
  const [rotation, setRotation] = useState(0);
  const [dragging, setDragging] = useState(false);
  const [offset, setOffset] = useState({ x: 0, y: 0 });
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const [naturalSize, setNaturalSize] = useState<{ w: number; h: number } | null>(null);
  const [fitMode, setFitMode] = useState(true);
  const containerRef = useRef<HTMLDivElement>(null);

  const handleWheel = useCallback((e: React.WheelEvent) => {
    e.preventDefault();
    setZoom((z) => Math.min(Math.max(z + (e.deltaY > 0 ? -0.1 : 0.1), 0.1), 10));
    setFitMode(false);
  }, []);

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    if (e.button !== 0) return;
    setDragging(true);
    setDragStart({ x: e.clientX - offset.x, y: e.clientY - offset.y });
  }, [offset]);

  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    if (!dragging) return;
    setOffset({ x: e.clientX - dragStart.x, y: e.clientY - dragStart.y });
  }, [dragging, dragStart]);

  const handleMouseUp = useCallback(() => {
    setDragging(false);
  }, []);

  const resetView = useCallback(() => {
    setZoom(1);
    setRotation(0);
    setOffset({ x: 0, y: 0 });
    setFitMode(true);
  }, []);

  const handleLoad = useCallback((e: React.SyntheticEvent<HTMLImageElement>) => {
    const img = e.currentTarget;
    setNaturalSize({ w: img.naturalWidth, h: img.naturalHeight });
  }, []);

  // Reset view when src changes
  useEffect(() => {
    resetView();
  }, [src, resetView]);

  return (
    <div className="flex flex-col flex-1 h-full bg-bg overflow-hidden">
      {/* Toolbar */}
      <div className="flex items-center justify-between px-4 py-2 bg-surface border-b border-border shrink-0">
        <div className="flex items-center gap-2 min-w-0">
          <span className="text-sm font-medium text-text truncate">{filename}</span>
          {naturalSize && (
            <span className="text-xs text-text-dim shrink-0">
              {naturalSize.w} x {naturalSize.h}
            </span>
          )}
        </div>
        <div className="flex items-center gap-1">
          <button
            className="w-7 h-7 rounded flex items-center justify-center text-text-dim hover:text-text hover:bg-surface-hover transition-colors"
            onClick={() => { setZoom((z) => Math.max(z - 0.25, 0.1)); setFitMode(false); }}
            title="Zoom out"
          >
            <ZoomOut size={14} />
          </button>
          <span className="text-xs text-text-dim w-12 text-center">{Math.round(zoom * 100)}%</span>
          <button
            className="w-7 h-7 rounded flex items-center justify-center text-text-dim hover:text-text hover:bg-surface-hover transition-colors"
            onClick={() => { setZoom((z) => Math.min(z + 0.25, 10)); setFitMode(false); }}
            title="Zoom in"
          >
            <ZoomIn size={14} />
          </button>
          <button
            className="w-7 h-7 rounded flex items-center justify-center text-text-dim hover:text-text hover:bg-surface-hover transition-colors"
            onClick={() => setRotation((r) => (r + 90) % 360)}
            title="Rotate"
          >
            <RotateCw size={14} />
          </button>
          <button
            className="w-7 h-7 rounded flex items-center justify-center text-text-dim hover:text-text hover:bg-surface-hover transition-colors"
            onClick={() => { setFitMode((f) => !f); setZoom(1); setOffset({ x: 0, y: 0 }); }}
            title={fitMode ? 'Actual size' : 'Fit to view'}
          >
            {fitMode ? <Maximize2 size={14} /> : <Minimize2 size={14} />}
          </button>
          <button
            className="px-2 py-1 text-xs text-text-dim hover:text-text hover:bg-surface-hover rounded transition-colors"
            onClick={resetView}
          >
            Reset
          </button>
        </div>
      </div>

      {/* Image canvas */}
      <div
        ref={containerRef}
        role="application"
        tabIndex={0}
        aria-label={`Image viewer: ${filename}`}
        className="flex-1 overflow-hidden flex items-center justify-center cursor-grab active:cursor-grabbing focus:outline-none"
        style={{ background: 'repeating-conic-gradient(#1a1a1a 0% 25%, #0d0d0d 0% 50%) 50% / 20px 20px' }}
        onWheel={handleWheel}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        onKeyDown={(e) => {
          if (e.key === '+' || e.key === '=') { setZoom((z) => Math.min(z + 0.25, 10)); setFitMode(false); }
          if (e.key === '-') { setZoom((z) => Math.max(z - 0.25, 0.1)); setFitMode(false); }
          if (e.key === '0') resetView();
        }}
      >
        <img
          src={src}
          alt={filename}
          className="select-none pointer-events-none"
          style={{
            transform: `translate(${offset.x}px, ${offset.y}px) scale(${zoom}) rotate(${rotation}deg)`,
            transformOrigin: 'center center',
            maxWidth: fitMode ? '100%' : undefined,
            maxHeight: fitMode ? '100%' : undefined,
            transition: dragging ? 'none' : 'transform 0.15s ease-out',
          }}
          draggable={false}
          onLoad={handleLoad}
        />
      </div>
    </div>
  );
}

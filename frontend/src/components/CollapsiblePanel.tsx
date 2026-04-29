import { useState, type ReactNode } from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';

interface CollapsiblePanelProps {
  title: string;
  icon?: ReactNode;
  badge?: string | number;
  defaultExpanded?: boolean;
  children: ReactNode;
}

export function CollapsiblePanel({ title, icon, badge, defaultExpanded = true, children }: CollapsiblePanelProps) {
  const [expanded, setExpanded] = useState(defaultExpanded);

  return (
    <div className="border-b border-border">
      <button
        className="flex items-center gap-1.5 w-full px-4 py-2.5 text-left text-xs uppercase tracking-wider text-text-dim font-semibold hover:text-text transition-colors"
        onClick={() => setExpanded(!expanded)}
      >
        <span className="shrink-0 text-text-dim">
          {expanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
        </span>
        {icon && <span className="shrink-0">{icon}</span>}
        <span className="flex-1 truncate">{title}</span>
        {badge !== undefined && badge !== null && (
          <span className="text-[10px] font-medium text-text-dim bg-bg px-1.5 py-0.5 rounded-full">
            {badge}
          </span>
        )}
      </button>
      {expanded && (
        <div className="px-4 pb-3">
          {children}
        </div>
      )}
    </div>
  );
}

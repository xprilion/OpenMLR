import { useState, useEffect, useRef } from 'react';
import { Cpu, ChevronDown, Star } from 'lucide-react';

interface ComputeNode {
  id: number;
  name: string;
  type: string;
  health_status: string;
}

interface ComputeSelectorProps {
  currentNode: ComputeNode | null;
  nodes: ComputeNode[];
  onChange: (nodeId: number | null) => void;
}

export function ComputeSelector({ currentNode, nodes, onChange }: ComputeSelectorProps) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (ref.current && !ref.current.contains(event.target as Node)) {
        setOpen(false);
      }
    }
    function handleEsc(event: KeyboardEvent) {
      if (event.key === 'Escape') setOpen(false);
    }
    document.addEventListener('mousedown', handleClickOutside);
    document.addEventListener('keydown', handleEsc);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleEsc);
    };
  }, []);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'online': return 'bg-success';
      case 'offline': return 'bg-error';
      case 'degraded': return 'bg-warning';
      default: return 'bg-text-dim';
    }
  };

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-2 px-3 py-1.5 bg-surface border border-border rounded-lg text-sm text-text hover:bg-surface-hover transition-colors"
      >
        <Cpu size={14} className="text-primary" />
        <span className="max-w-[120px] truncate">
          {currentNode ? currentNode.name : 'Default'}
        </span>
        <ChevronDown size={14} className="text-text-dim" />
      </button>

      {open && (
        <div className="absolute top-full right-0 mt-1 w-64 bg-surface border border-border rounded-lg shadow-xl z-50 py-1">
          {/* Default option */}
          <button
            onClick={() => { onChange(null); setOpen(false); }}
            className={`w-full flex items-center gap-2 px-3 py-2 text-sm text-left transition-colors ${
              !currentNode ? 'bg-primary/10 text-primary' : 'text-text hover:bg-surface-hover'
            }`}
          >
            <Star size={14} className={!currentNode ? 'text-primary' : 'text-text-dim'} />
            <span>Default</span>
          </button>

          {nodes.length > 0 && <div className="border-t border-border my-1" />}

          {/* Node list */}
          {nodes.map((node) => (
            <button
              key={node.id}
              onClick={() => { onChange(node.id); setOpen(false); }}
              className={`w-full flex items-center gap-2 px-3 py-2 text-sm text-left transition-colors ${
                currentNode?.id === node.id ? 'bg-primary/10 text-primary' : 'text-text hover:bg-surface-hover'
              }`}
            >
              <span className={`w-2 h-2 rounded-full ${getStatusColor(node.health_status)}`} />
              <div className="flex-1 min-w-0">
                <div className="truncate">{node.name}</div>
                <div className="text-xs text-text-dim capitalize">{node.type}</div>
              </div>
            </button>
          ))}

          {nodes.length === 0 && (
            <div className="px-3 py-2 text-xs text-text-dim text-center">
              No compute nodes configured
            </div>
          )}
        </div>
      )}
    </div>
  );
}

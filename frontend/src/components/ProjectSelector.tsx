import { useState, useEffect, useRef } from 'react';
import { FolderOpen, ChevronDown, Plus, SlidersHorizontal } from 'lucide-react';
import type { Project } from '../types';

interface Props {
  projects: Project[];
  activeProject: Project | null;
  onSelectProject: (project: Project) => void;
  onNewProject: () => void;
  onManageProjects: () => void;
}

export function ProjectSelector({ projects, activeProject, onSelectProject, onNewProject, onManageProjects }: Props) {
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

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-1 sm:gap-2 px-2 sm:px-3 py-1.5 bg-surface border border-border rounded-lg text-sm text-text hover:bg-surface-hover transition-colors"
        title={activeProject?.name || 'Select Project'}
      >
        <FolderOpen size={14} className="text-primary shrink-0" />
        <span className="hidden sm:inline max-w-[120px] truncate">
          {activeProject?.name || 'Project'}
        </span>
        <ChevronDown size={14} className={`text-text-dim shrink-0 transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>

      {open && (
        <div className="absolute top-full left-0 mt-1 w-64 bg-surface border border-border rounded-lg shadow-xl z-50 py-1 max-h-80 overflow-auto">
          {/* User projects */}
          {projects.map((p) => (
            <button
              key={p.uuid}
              className={`w-full flex items-center gap-2 px-3 py-2 text-sm text-left transition-colors ${
                activeProject?.uuid === p.uuid ? 'bg-primary/10 text-primary' : 'text-text hover:bg-surface-hover'
              }`}
              onClick={() => { onSelectProject(p); setOpen(false); }}
            >
              <FolderOpen size={14} />
              <span className="flex-1 truncate">{p.name}</span>
              {p.conversation_count !== undefined && (
                <span className="text-xs text-text-dim">{p.conversation_count}</span>
              )}
            </button>
          ))}

          {projects.length === 0 && (
            <div className="px-3 py-2 text-sm text-text-dim">No projects yet</div>
          )}

          {/* Actions */}
          <div className="border-t border-border mt-1">
            <button
              className="w-full flex items-center gap-2 px-3 py-2 text-sm text-primary hover:bg-surface-hover transition-colors"
              onClick={() => { onNewProject(); setOpen(false); }}
            >
              <Plus size={14} />
              New Project
            </button>
            {projects.length > 0 && (
              <button
                className="w-full flex items-center gap-2 px-3 py-2 text-sm text-text-dim hover:bg-surface-hover hover:text-text transition-colors"
                onClick={() => { onManageProjects(); setOpen(false); }}
              >
                <SlidersHorizontal size={14} />
                Manage Projects
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

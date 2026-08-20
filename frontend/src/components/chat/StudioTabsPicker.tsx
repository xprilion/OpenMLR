import { useState, useRef, useEffect } from 'react';
import { Plus, X, Check, ChevronDown, Layers } from 'lucide-react';
import { useProject, type MainTab } from '../../context/ProjectContext';

export interface StudioTabOption {
  id: MainTab;
  label: string;
  category: 'Research' | 'ML Engine' | 'Publication';
  description: string;
}

export const AVAILABLE_STUDIO_TABS: StudioTabOption[] = [
  // Research & Literature
  {
    id: 'workflow',
    label: 'Workflow',
    category: 'Research',
    description: 'Phased research roadmap, hypothesis tracking & milestones',
  },
  {
    id: 'research',
    label: 'Citation Graph',
    category: 'Research',
    description: 'Interactive citation tree & literature comparison matrix',
  },

  // Experiments & ML Engine
  {
    id: 'experiments',
    label: 'Experiments',
    category: 'ML Engine',
    description: 'Real-time training loss curves, checkpoints & run logs',
  },
  {
    id: 'sweeps',
    label: 'Sweeps',
    category: 'ML Engine',
    description: 'Hyperparameter sweep parallel coordinates & trial ranking',
  },
  {
    id: 'ablation',
    label: 'Ablations',
    category: 'ML Engine',
    description: 'Component impact waterfall & statistical significance testing',
  },
  {
    id: 'datasets',
    label: 'Datasets',
    category: 'ML Engine',
    description: 'Data profiling, schema validation & sample data viewer',
  },
  {
    id: 'models',
    label: 'Models',
    category: 'ML Engine',
    description: 'Model registry, quantization matrix & model cards',
  },
  {
    id: 'eval',
    label: 'Benchmarks',
    category: 'ML Engine',
    description: 'Research task harness, accuracy & speedup matrices',
  },

  // Publication & Camera-Ready
  {
    id: 'paper',
    label: 'Paper Studio',
    category: 'Publication',
    description: 'Live LaTeX editor with real-time compiled PDF preview & BibTeX',
  },
  {
    id: 'figures',
    label: 'Figures',
    category: 'Publication',
    description: 'TikZ and matplotlib vector diagram generation & gallery',
  },
  {
    id: 'reproducibility',
    label: 'Reproducibility',
    category: 'Publication',
    description: 'Multi-category checklist auditor & badge generator',
  },
  {
    id: 'review',
    label: 'Peer Review',
    category: 'Publication',
    description: 'NeurIPS/ICLR rubric scoring, meta-review & decision summary',
  },
];

export function StudioTabsPicker() {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const { enabledTabs, enableTab, disableTab, setMainTab } = useProject();

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isOpen]);

  const categories = ['Research', 'ML Engine', 'Publication'] as const;

  return (
    <div className="relative inline-block" ref={dropdownRef}>
      <button
        type="button"
        onClick={() => setIsOpen((prev) => !prev)}
        className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-text-dim hover:text-text hover:bg-surface-hover rounded-lg transition-colors border border-dashed border-border/70 hover:border-border ml-1 my-1"
        title="Surface optional specialized studios"
        aria-label="Add Tab"
        aria-expanded={isOpen}
      >
        <Plus className="w-3.5 h-3.5 text-primary" />
        <span>Add Tab</span>
        <ChevronDown className={`w-3 h-3 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      {isOpen && (
        <div
          className="absolute left-0 sm:right-0 sm:left-auto mt-1 w-80 max-h-[80vh] overflow-y-auto bg-surface border border-border rounded-xl shadow-2xl z-50 p-2 space-y-3"
          role="dialog"
          aria-label="Available Studios"
        >
          <div className="flex items-center justify-between px-2 pt-1 pb-2 border-b border-border/60">
            <div className="flex items-center gap-1.5 text-xs font-semibold text-text">
              <Layers className="w-3.5 h-3.5 text-primary" />
              <span>Specialized Studios</span>
            </div>
            <button
              type="button"
              onClick={() => setIsOpen(false)}
              className="text-text-dim hover:text-text p-1 rounded-md hover:bg-surface-hover"
              aria-label="Close menu"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>

          {categories.map((cat) => {
            const tabsInCat = AVAILABLE_STUDIO_TABS.filter((t) => t.category === cat);
            if (tabsInCat.length === 0) return null;

            return (
              <div key={cat} className="space-y-1">
                <div className="text-[10px] font-semibold uppercase tracking-wider text-text-dim px-2">
                  {cat}
                </div>
                <div className="space-y-1">
                  {tabsInCat.map((tab) => {
                    const isEnabled = enabledTabs.includes(tab.id);
                    return (
                      <div
                        key={tab.id}
                        className="flex items-start justify-between p-2 rounded-lg hover:bg-surface-hover/70 transition-colors group"
                      >
                        <div className="flex-1 pr-2">
                          <div className="flex items-center gap-1.5">
                            <span className="text-xs font-medium text-text group-hover:text-primary transition-colors">
                              {tab.label}
                            </span>
                            {isEnabled && (
                              <span className="text-[10px] text-success flex items-center gap-0.5 font-medium">
                                <Check className="w-3 h-3" /> Active
                              </span>
                            )}
                          </div>
                          <p className="text-[11px] text-text-dim leading-tight mt-0.5">
                            {tab.description}
                          </p>
                        </div>
                        <div className="shrink-0 flex items-center gap-1 pt-0.5">
                          {isEnabled ? (
                            <>
                              <button
                                type="button"
                                onClick={() => {
                                  setMainTab(tab.id);
                                  setIsOpen(false);
                                }}
                                className="px-2 py-1 text-[11px] font-medium bg-primary/10 text-primary hover:bg-primary/20 rounded-md transition-colors"
                              >
                                Switch
                              </button>
                              <button
                                type="button"
                                onClick={() => disableTab(tab.id)}
                                className="p-1 text-text-dim hover:text-error hover:bg-error/10 rounded-md transition-colors"
                                title="Hide tab"
                              >
                                <X className="w-3.5 h-3.5" />
                              </button>
                            </>
                          ) : (
                            <button
                              type="button"
                              onClick={() => {
                                enableTab(tab.id, true);
                                setIsOpen(false);
                              }}
                              className="px-2.5 py-1 text-[11px] font-medium bg-surface-hover hover:bg-primary hover:text-white text-text border border-border/80 rounded-md transition-colors flex items-center gap-1"
                            >
                              <Plus className="w-3 h-3" />
                              <span>Enable</span>
                            </button>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

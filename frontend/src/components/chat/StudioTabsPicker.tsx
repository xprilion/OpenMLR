import { useState, useEffect } from 'react';
import {
  Plus,
  X,
  Layers,
  Search,
  BookOpen,
  GitGraph,
  LineChart,
  Sliders,
  Split,
  Database,
  Cpu,
  FileCode,
  Sparkles,
  ShieldCheck,
  Award,
  Target,
  type LucideIcon,
} from 'lucide-react';
import { useProject, type MainTab } from '../../context/ProjectContext';

export interface StudioTabOption {
  id: MainTab;
  label: string;
  category: 'Research' | 'ML Engine' | 'Publication';
  description: string;
  icon: LucideIcon;
  badge?: string;
}

export const AVAILABLE_STUDIO_TABS: StudioTabOption[] = [
  // Research & Literature
  {
    id: 'workflow',
    label: 'Research Workflow',
    category: 'Research',
    description: 'Phased roadmap from idea reconnaissance to camera-ready verification.',
    icon: GitGraph,
  },
  {
    id: 'research',
    label: 'Citation Graph',
    category: 'Research',
    description: 'Interactive citation network exploration, paper matrix & co-citation clustering.',
    icon: BookOpen,
  },

  // Experiments & ML Engine
  {
    id: 'experiments',
    label: 'Experiment Tracker',
    category: 'ML Engine',
    description: 'Live loss/validation curves, GPU metrics, checkpoints & run logs.',
    icon: LineChart,
  },
  {
    id: 'sweeps',
    label: 'Hyperparameter Sweeps',
    category: 'ML Engine',
    description: 'Bayesian/Hyperband sweep parallel coordinates & trial performance ranking.',
    icon: Sliders,
  },
  {
    id: 'ablation',
    label: 'Ablations & Significance',
    category: 'ML Engine',
    description: 'Multi-seed statistical tests, Welch t-test, Cohen d effect sizes & LaTeX tables.',
    icon: Split,
    badge: 'Statistical',
  },
  {
    id: 'datasets',
    label: 'Dataset Profiler',
    category: 'ML Engine',
    description: 'Distribution metrics, schema validator, train/val split ratios & sample viewer.',
    icon: Database,
  },
  {
    id: 'models',
    label: 'Model Registry',
    category: 'ML Engine',
    description: 'Model registry, FP8/INT4 quantization planning & automated model cards.',
    icon: Cpu,
  },
  {
    id: 'eval',
    label: 'Benchmark Harness',
    category: 'ML Engine',
    description: 'Kernel speedup & paper reproduction benchmark suites.',
    icon: Target,
  },

  // Publication & Camera-Ready
  {
    id: 'paper',
    label: 'Paper Studio',
    category: 'Publication',
    description: 'Live LaTeX authoring with real-time compiled PDF preview & BibTeX normalization.',
    icon: FileCode,
    badge: 'Camera-Ready',
  },
  {
    id: 'figures',
    label: 'Publication Figures',
    category: 'Publication',
    description: 'TikZ and matplotlib vector plots with NeurIPS/ICML formatting.',
    icon: Sparkles,
  },
  {
    id: 'reproducibility',
    label: 'Reproducibility Auditor',
    category: 'Publication',
    description: 'Multi-category reproducibility scoring, checklist verification & SVG badges.',
    icon: ShieldCheck,
  },
  {
    id: 'review',
    label: 'Peer Review Studio',
    category: 'Publication',
    description: 'Multi-persona conference rubric scoring, meta-review synthesis & rebuttal builder.',
    icon: Award,
  },
];

export function StudioTabsPicker() {
  const [isOpen, setIsOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<'All' | 'Research' | 'ML Engine' | 'Publication'>('All');
  const { enabledTabs, enableTab, disableTab, setMainTab } = useProject();

  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === 'Escape' && isOpen) {
        setIsOpen(false);
      }
    }
    if (isOpen) {
      window.addEventListener('keydown', handleKeyDown);
    }
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [isOpen]);

  const categories = ['All', 'Research', 'ML Engine', 'Publication'] as const;

  const filteredTabs = AVAILABLE_STUDIO_TABS.filter((tab) => {
    const matchesCategory = selectedCategory === 'All' || tab.category === selectedCategory;
    const matchesQuery =
      searchQuery.trim() === '' ||
      tab.label.toLowerCase().includes(searchQuery.toLowerCase()) ||
      tab.description.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesCategory && matchesQuery;
  });

  return (
    <>
      <button
        type="button"
        onClick={() => setIsOpen(true)}
        className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-text-dim hover:text-text hover:bg-surface-hover rounded-lg transition-colors border border-dashed border-border/80 hover:border-primary/50 ml-1.5 my-1 shrink-0"
        title="Discover and surface specialized studios"
        aria-label="Add Tab"
      >
        <Plus className="w-3.5 h-3.5 text-primary" />
        <span>Add Tab</span>
      </button>

      {isOpen && (
        <div
          className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-3 sm:p-6 animate-fade-in"
          onClick={() => setIsOpen(false)}
          onKeyDown={(e) => e.key === 'Escape' && setIsOpen(false)}
          role="dialog"
          aria-modal="true"
          aria-labelledby="studio-picker-title"
        >
          <div
            className="max-w-2xl w-full bg-surface border border-border rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[85vh] animate-scale-up"
            onClick={(e) => e.stopPropagation()}
            onKeyDown={(e) => e.stopPropagation()}
          >
            {/* Modal Header */}
            <div className="px-5 py-4 border-b border-border/80 flex items-center justify-between bg-surface/80">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-xl bg-primary/10 border border-primary/20 flex items-center justify-center text-primary shrink-0">
                  <Layers className="w-4 h-4" />
                </div>
                <div>
                  <h2 id="studio-picker-title" className="text-sm font-semibold text-text">
                    Specialized Research Studios
                  </h2>
                  <p className="text-xs text-text-dim">
                    Surface on-demand studios for ML experimentation, literature analysis, and publication authoring.
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setIsOpen(false)}
                className="p-1.5 text-text-dim hover:text-text hover:bg-surface-hover rounded-lg transition-colors"
                aria-label="Close modal"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Filter and Search Bar */}
            <div className="px-5 py-3 border-b border-border/60 bg-bg/40 flex flex-col sm:flex-row items-center justify-between gap-2.5 shrink-0">
              <div className="relative w-full sm:w-64">
                <Search className="w-3.5 h-3.5 absolute left-3 top-2.5 text-text-dim" />
                <input
                  type="text"
                  placeholder="Search studios..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-8 pr-3 py-1.5 text-xs bg-surface border border-border rounded-lg text-text focus:outline-none focus:border-primary transition-colors"
                  autoFocus
                />
              </div>

              <div className="flex items-center gap-1 w-full sm:w-auto overflow-x-auto">
                {categories.map((cat) => (
                  <button
                    key={cat}
                    type="button"
                    onClick={() => setSelectedCategory(cat)}
                    className={`px-2.5 py-1 text-xs rounded-lg font-medium transition-colors whitespace-nowrap ${
                      selectedCategory === cat
                        ? 'bg-primary/15 text-primary border border-primary/30'
                        : 'text-text-dim hover:text-text hover:bg-surface'
                    }`}
                  >
                    {cat}
                  </button>
                ))}
              </div>
            </div>

            {/* Studios Grid */}
            <div className="p-4 sm:p-5 overflow-y-auto space-y-2.5 flex-1">
              {filteredTabs.length === 0 ? (
                <div className="text-center py-10 text-text-dim text-xs">
                  No studios found matching "{searchQuery}".
                </div>
              ) : (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {filteredTabs.map((tab) => {
                    const isEnabled = enabledTabs.includes(tab.id);
                    const IconComponent = tab.icon;

                    return (
                      <div
                        key={tab.id}
                        className={`p-3.5 rounded-xl border transition-all flex flex-col justify-between gap-3 ${
                          isEnabled
                            ? 'bg-primary/5 border-primary/30 shadow-xs'
                            : 'bg-surface/50 border-border hover:border-border-hover hover:bg-surface'
                        }`}
                      >
                        <div className="space-y-1.5">
                          <div className="flex items-center justify-between gap-2">
                            <div className="flex items-center gap-2">
                              <div
                                className={`w-7 h-7 rounded-lg flex items-center justify-center shrink-0 ${
                                  isEnabled ? 'bg-primary/20 text-primary' : 'bg-surface-hover text-text-dim'
                                }`}
                              >
                                <IconComponent className="w-3.5 h-3.5" />
                              </div>
                              <span className="text-xs font-semibold text-text">{tab.label}</span>
                            </div>

                            {tab.badge && (
                              <span className="text-[10px] uppercase tracking-wider font-semibold px-1.5 py-0.5 rounded bg-surface border border-border text-text-dim">
                                {tab.badge}
                              </span>
                            )}
                          </div>

                          <p className="text-[11px] text-text-dim leading-relaxed">{tab.description}</p>
                        </div>

                        <div className="flex items-center justify-between gap-2 pt-2 border-t border-border/40 mt-auto">
                          <span className="text-[10px] text-text-dim font-medium uppercase tracking-wider">
                            {tab.category}
                          </span>

                          <div className="flex items-center gap-1.5">
                            {isEnabled ? (
                              <>
                                <button
                                  type="button"
                                  onClick={() => {
                                    setMainTab(tab.id);
                                    setIsOpen(false);
                                  }}
                                  className="px-2.5 py-1 text-xs font-medium rounded-lg bg-primary text-white hover:bg-primary-hover transition-colors shadow-xs"
                                >
                                  Open
                                </button>
                                <button
                                  type="button"
                                  onClick={() => disableTab(tab.id)}
                                  className="px-2 py-1 text-xs text-text-dim hover:text-error hover:bg-error/10 rounded-lg transition-colors border border-border/60"
                                  title="Hide from tab bar"
                                >
                                  Hide
                                </button>
                              </>
                            ) : (
                              <button
                                type="button"
                                onClick={() => {
                                  enableTab(tab.id, true);
                                  setIsOpen(false);
                                }}
                                className="px-3 py-1 text-xs font-medium rounded-lg bg-surface hover:bg-primary hover:text-white text-text border border-border hover:border-primary transition-all flex items-center gap-1 shadow-xs"
                              >
                                <Plus className="w-3 h-3" />
                                <span>Enable & Open</span>
                              </button>
                            )}
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>

            {/* Modal Footer */}
            <div className="px-5 py-3 border-t border-border/80 bg-surface/90 flex items-center justify-between text-xs text-text-dim shrink-0">
              <span className="truncate mr-2">
                Core tabs <strong className="text-text font-medium">Agent</strong>,{' '}
                <strong className="text-text font-medium">Editor</strong>, and{' '}
                <strong className="text-text font-medium">Terminal</strong> remain always active.
              </span>
              <button
                type="button"
                onClick={() => setIsOpen(false)}
                className="px-4 py-1.5 text-xs font-medium rounded-lg bg-surface hover:bg-surface-hover text-text border border-border transition-colors shrink-0"
              >
                Done
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

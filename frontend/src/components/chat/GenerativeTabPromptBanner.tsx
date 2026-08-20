import { Sparkles, X, ArrowRight } from 'lucide-react';
import { useProject } from '../../context/ProjectContext';

export function GenerativeTabPromptBanner() {
  const { suggestedTabPrompt, enableTab, dismissSuggestedTabPrompt } = useProject();

  if (!suggestedTabPrompt) return null;

  return (
    <div
      className="mx-4 sm:mx-6 my-2.5 p-3 sm:p-3.5 bg-primary/10 border border-primary/30 rounded-xl flex items-center justify-between gap-3 shadow-sm animate-fade-in text-xs sm:text-sm shrink-0"
      role="alert"
    >
      <div className="flex items-center gap-2.5 min-w-0">
        <div className="w-8 h-8 rounded-lg bg-primary/20 flex items-center justify-center text-primary shrink-0">
          <Sparkles className="w-4 h-4" />
        </div>
        <div className="min-w-0">
          <div className="font-semibold text-text flex items-center gap-1.5 truncate">
            <span>Suggestion: Open {suggestedTabPrompt.title}</span>
            <span className="text-[10px] uppercase tracking-wider px-1.5 py-0.5 rounded-full bg-primary/20 text-primary font-medium">
              On-Demand Studio
            </span>
          </div>
          <p className="text-text-dim text-xs truncate mt-0.5">
            {suggestedTabPrompt.description}
          </p>
        </div>
      </div>

      <div className="flex items-center gap-2 shrink-0">
        <button
          type="button"
          onClick={() => enableTab(suggestedTabPrompt.tab, true)}
          className="px-3 py-1.5 rounded-lg bg-primary hover:bg-primary-hover text-white text-xs font-medium transition-colors flex items-center gap-1 shadow-xs"
        >
          <span>Enable Tab</span>
          <ArrowRight className="w-3 h-3" />
        </button>
        <button
          type="button"
          onClick={dismissSuggestedTabPrompt}
          className="p-1.5 rounded-lg text-text-dim hover:text-text hover:bg-surface-hover transition-colors"
          title="Keep in background"
          aria-label="Dismiss suggestion"
        >
          <X className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}

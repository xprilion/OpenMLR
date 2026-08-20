import { useState } from 'react';
import { CheckCircle2, AlertTriangle, XCircle, HelpCircle, ChevronDown, ChevronUp, Copy, Check } from 'lucide-react';
import type { CheckItem, CheckStatus } from './types';

interface ChecklistTableProps {
  items: CheckItem[];
}

export function ChecklistTable({ items }: Readonly<ChecklistTableProps>) {
  const [filter, setFilter] = useState<'all' | CheckStatus>('all');
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const filteredItems = items.filter((item) => {
    if (filter === 'all') return true;
    return item.status === filter;
  });

  const counts = {
    all: items.length,
    pass: items.filter((i) => i.status === 'pass').length,
    warn: items.filter((i) => i.status === 'warn').length,
    fail: items.filter((i) => i.status === 'fail').length,
    skip: items.filter((i) => i.status === 'skip').length,
  };

  const handleCopyRemediation = (id: string, text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const getStatusIcon = (status: CheckStatus) => {
    switch (status) {
      case 'pass':
        return <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />;
      case 'warn':
        return <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0" />;
      case 'fail':
        return <XCircle className="w-4 h-4 text-rose-400 shrink-0" />;
      case 'skip':
      default:
        return <HelpCircle className="w-4 h-4 text-text-dim shrink-0" />;
    }
  };

  const getStatusBadge = (status: CheckStatus) => {
    switch (status) {
      case 'pass':
        return <span className="px-2 py-0.5 text-[11px] font-semibold rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 uppercase tracking-wider">PASS</span>;
      case 'warn':
        return <span className="px-2 py-0.5 text-[11px] font-semibold rounded bg-amber-500/10 text-amber-400 border border-amber-500/20 uppercase tracking-wider">WARN</span>;
      case 'fail':
        return <span className="px-2 py-0.5 text-[11px] font-semibold rounded bg-rose-500/10 text-rose-400 border border-rose-500/20 uppercase tracking-wider">FAIL</span>;
      case 'skip':
      default:
        return <span className="px-2 py-0.5 text-[11px] font-semibold rounded bg-surface-hover text-text-dim border border-border uppercase tracking-wider">SKIP</span>;
    }
  };

  return (
    <div className="flex flex-col gap-3 bg-surface border border-border rounded-xl p-4 shadow-sm">
      {/* Header & Filter Tabs */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border pb-3">
        <h3 className="text-sm font-semibold text-text">Conference Reproducibility Checklist</h3>
        <div className="flex items-center gap-1.5 bg-bg border border-border p-1 rounded-lg">
          {(['all', 'pass', 'warn', 'fail'] as const).map((key) => {
            const isSelected = filter === key;
            const count = counts[key];
            return (
              <button
                key={key}
                type="button"
                onClick={() => setFilter(key)}
                className={`px-2.5 py-1 text-xs font-medium rounded-md transition-colors capitalize flex items-center gap-1.5 ${
                  isSelected
                    ? 'bg-surface text-primary font-semibold shadow-xs'
                    : 'text-text-dim hover:text-text'
                }`}
              >
                <span>{key}</span>
                <span className={`px-1.5 py-0.2 rounded-full text-[10px] ${isSelected ? 'bg-primary/20 text-primary' : 'bg-surface text-text-dim'}`}>
                  {count}
                </span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Checklist Items */}
      <div className="flex flex-col gap-2">
        {filteredItems.length === 0 ? (
          <div className="py-8 text-center text-xs text-text-dim">No items match the current filter.</div>
        ) : (
          filteredItems.map((item) => {
            const isExpanded = expandedId === item.id;
            return (
              <div
                key={item.id}
                className="border border-border/80 rounded-lg bg-bg/50 overflow-hidden transition-colors"
              >
                <div
                  role="button"
                  tabIndex={0}
                  onClick={() => setExpandedId(isExpanded ? null : item.id)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault();
                      setExpandedId(isExpanded ? null : item.id);
                    }
                  }}
                  className="w-full flex items-center justify-between p-3 text-left hover:bg-surface-hover/50 cursor-pointer select-none"
                >
                  <div className="flex items-center gap-3 flex-1 min-w-0 pr-2">
                    {getStatusIcon(item.status)}
                    <div className="flex flex-col min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-semibold text-text truncate">{item.title}</span>
                        <span className="text-[10px] uppercase font-mono px-1.5 py-0.2 rounded bg-surface border border-border text-text-dim">
                          {item.category}
                        </span>
                      </div>
                      <span className="text-xs text-text-dim truncate">{item.description}</span>
                    </div>
                  </div>

                  <div className="flex items-center gap-3 shrink-0">
                    {getStatusBadge(item.status)}
                    {isExpanded ? (
                      <ChevronUp className="w-4 h-4 text-text-dim" />
                    ) : (
                      <ChevronDown className="w-4 h-4 text-text-dim" />
                    )}
                  </div>
                </div>

                {isExpanded && (
                  <div className="px-3.5 pb-3.5 pt-1 border-t border-border/60 bg-surface/30 flex flex-col gap-2.5 text-xs">
                    {item.details && (
                      <div>
                        <span className="font-semibold text-text-dim block mb-0.5">Findings:</span>
                        <p className="text-text bg-bg p-2 rounded border border-border/80 font-mono text-[11px]">
                          {item.details}
                        </p>
                      </div>
                    )}

                    {item.remediation && (
                      <div>
                        <div className="flex items-center justify-between mb-0.5">
                          <span className="font-semibold text-text-dim">Remediation / Suggested Action:</span>
                          <button
                            type="button"
                            onClick={() => handleCopyRemediation(item.id, item.remediation!)}
                            className="flex items-center gap-1 text-[11px] text-primary hover:underline"
                          >
                            {copiedId === item.id ? (
                              <>
                                <Check className="w-3 h-3 text-emerald-400" />
                                <span className="text-emerald-400">Copied</span>
                              </>
                            ) : (
                              <>
                                <Copy className="w-3 h-3" />
                                <span>Copy Code</span>
                              </>
                            )}
                          </button>
                        </div>
                        <pre className="text-text bg-bg p-2.5 rounded border border-border/80 font-mono text-[11px] overflow-x-auto whitespace-pre-wrap">
                          {item.remediation}
                        </pre>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}

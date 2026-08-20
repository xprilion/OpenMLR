import { useState, useMemo } from 'react';
import { Search, ChevronDown, ChevronRight, Hash, Type, ToggleLeft, Layers } from 'lucide-react';
import type { ColumnProfile } from './types';

interface Props {
  readonly columns: Record<string, ColumnProfile>;
}

function getProgressColor(pct: number): string {
  if (pct > 20) return 'bg-red-500';
  if (pct > 5) return 'bg-amber-500';
  return 'bg-emerald-500';
}

function getTypeIcon(dtype: string) {
  switch (dtype.toLowerCase()) {
    case 'numeric':
      return <Hash size={14} className="text-blue-400" />;
    case 'text':
      return <Type size={14} className="text-emerald-400" />;
    case 'categorical':
      return <Layers size={14} className="text-purple-400" />;
    case 'boolean':
      return <ToggleLeft size={14} className="text-amber-400" />;
    default:
      return <Hash size={14} className="text-text-dim" />;
  }
}

export function ColumnMetricsTable({ columns }: Props) {
  const [search, setSearch] = useState('');
  const [selectedType, setSelectedType] = useState<string>('all');
  const [expandedCol, setExpandedCol] = useState<string | null>(null);

  const columnList = useMemo(() => Object.values(columns), [columns]);

  const filteredColumns = useMemo(() => {
    return columnList.filter((col) => {
      const matchesSearch = col.name.toLowerCase().includes(search.toLowerCase());
      const matchesType = selectedType === 'all' || col.dtype.toLowerCase() === selectedType.toLowerCase();
      return matchesSearch && matchesType;
    });
  }, [columnList, search, selectedType]);

  return (
    <div className="space-y-4">
      {/* Controls */}
      <div className="flex flex-col sm:flex-row gap-3 items-center justify-between">
        <div className="relative w-full sm:w-72">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-dim" />
          <input
            type="text"
            placeholder="Search columns..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full bg-surface-subtle border border-border rounded-md pl-9 pr-3 py-1.5 text-xs text-text placeholder-text-dim focus:outline-none focus:border-primary"
          />
        </div>
        <div className="flex items-center gap-1.5 self-start sm:self-auto overflow-x-auto">
          {['all', 'numeric', 'text', 'categorical', 'boolean'].map((t) => (
            <button
              key={t}
              type="button"
              onClick={() => setSelectedType(t)}
              className={`px-2.5 py-1 text-xs rounded capitalize transition-colors ${
                selectedType === t
                  ? 'bg-primary/20 text-primary font-medium'
                  : 'bg-surface-subtle text-text-dim hover:text-text'
              }`}
            >
              {t}
            </button>
          ))}
        </div>
      </div>

      {/* Table */}
      <div className="border border-border rounded-lg overflow-hidden bg-surface">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-text border-collapse">
            <thead>
              <tr className="border-b border-border bg-surface-subtle text-text-dim font-medium">
                <th className="py-2.5 px-3 w-8" />
                <th className="py-2.5 px-3">Column Name</th>
                <th className="py-2.5 px-3">Type</th>
                <th className="py-2.5 px-3">Missing Values</th>
                <th className="py-2.5 px-3 text-right">Unique Values</th>
                <th className="py-2.5 px-3">Statistical Summary</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border/50">
              {filteredColumns.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-8 text-center text-text-dim">
                    No matching columns found.
                  </td>
                </tr>
              ) : (
                filteredColumns.map((col) => {
                  const isExpanded = expandedCol === col.name;
                  const stats = col.stats || {};
                  return (
                    <tr key={col.name} className="hover:bg-surface-subtle/50 transition-colors group">
                      <td className="py-2.5 px-3 text-center">
                        <button
                          type="button"
                          onClick={() => setExpandedCol(isExpanded ? null : col.name)}
                          className="text-text-dim hover:text-text p-0.5 rounded"
                          title="Toggle Details"
                        >
                          {isExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                        </button>
                      </td>
                      <td className="py-2.5 px-3 font-mono font-medium text-text">{col.name}</td>
                      <td className="py-2.5 px-3">
                        <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded bg-surface-subtle border border-border font-mono text-[11px]">
                          {getTypeIcon(col.dtype)}
                          {col.dtype}
                        </span>
                      </td>
                      <td className="py-2.5 px-3">
                        <div className="flex items-center gap-2">
                          <div className="w-16 bg-surface-subtle rounded-full h-1.5 overflow-hidden border border-border">
                            <div
                              className={`h-full ${getProgressColor(col.null_percentage)}`}
                              style={{ width: `${Math.min(100, col.null_percentage)}%` }}
                            />
                          </div>
                          <span className="text-[11px] text-text-dim">
                            {col.null_percentage}% ({col.null_count}/{col.total_count})
                          </span>
                        </div>
                      </td>
                      <td className="py-2.5 px-3 text-right font-mono text-text-dim">
                        {col.unique_count.toLocaleString()}
                      </td>
                      <td className="py-2.5 px-3 text-text-dim text-[11px]">
                        {col.dtype === 'numeric' && (
                          <span>
                            Range: [{stats.min ?? '?'}, {stats.max ?? '?'}], μ={stats.mean ?? '?'}, σ={stats.std ?? '?'}
                          </span>
                        )}
                        {col.dtype === 'categorical' && (
                          <span>
                            Imbalance: {stats.imbalance_ratio ?? 1}x | Top: {Object.keys(stats.top_classes || {}).slice(0, 3).join(', ')}
                          </span>
                        )}
                        {col.dtype === 'text' && (
                          <span>
                            Mean Tokens: {stats.token_est_mean ?? '?'}, Max: {stats.token_est_max ?? '?'}
                          </span>
                        )}
                        {col.dtype === 'boolean' && (
                          <span>True Count: {stats.true_count ?? '?'}</span>
                        )}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

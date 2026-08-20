import { useState, useMemo, useCallback } from 'react';
import { Search, Table, FileSpreadsheet, FileCode } from 'lucide-react';
import type { PaperNode, LiteratureMatrixRow } from './types';

export interface LiteratureMatrixProps {
  papers: PaperNode[];
  selectedPaperId?: string;
  onSelectPaper: (paper: PaperNode) => void;
}

export function LiteratureMatrix({
  papers,
  selectedPaperId,
  onSelectPaper,
}: Readonly<LiteratureMatrixProps>) {
  const [searchQuery, setSearchQuery] = useState('');
  const [sortField, setSortField] = useState<keyof LiteratureMatrixRow>('year');
  const [sortAsc, setSortAsc] = useState(false);

  const rows: LiteratureMatrixRow[] = useMemo(() => {
    return papers.map((p) => ({
      id: p.id,
      title: p.title,
      year: p.year,
      authors: p.authors.slice(0, 2).join(', ') + (p.authors.length > 2 ? ' et al.' : ''),
      method: p.methodology,
      dataset: p.dataset,
      metric: p.metric,
      baseline: p.baseline,
      gap: p.gap,
    }));
  }, [papers]);

  const filteredRows = useMemo(() => {
    const q = searchQuery.toLowerCase().trim();
    let result = rows;
    if (q) {
      result = result.filter(
        (r) =>
          r.title.toLowerCase().includes(q) ||
          r.authors.toLowerCase().includes(q) ||
          r.method.toLowerCase().includes(q) ||
          r.dataset.toLowerCase().includes(q) ||
          r.gap.toLowerCase().includes(q)
      );
    }
    return [...result].sort((a, b) => {
      const valA = a[sortField];
      const valB = b[sortField];
      if (typeof valA === 'number' && typeof valB === 'number') {
        return sortAsc ? valA - valB : valB - valA;
      }
      return sortAsc
        ? String(valA).localeCompare(String(valB))
        : String(valB).localeCompare(String(valA));
    });
  }, [rows, searchQuery, sortField, sortAsc]);

  const handleExportCsv = useCallback(() => {
    const headers = ['Paper Title', 'Year', 'Authors', 'Methodology', 'Dataset', 'Metric', 'Baseline', 'Research Gap'];
    const csvContent = [
      headers.join(','),
      ...filteredRows.map((r) =>
        [
          `"${r.title.replace(/"/g, '""')}"`,
          r.year,
          `"${r.authors.replace(/"/g, '""')}"`,
          `"${r.method.replace(/"/g, '""')}"`,
          `"${r.dataset.replace(/"/g, '""')}"`,
          `"${r.metric.replace(/"/g, '""')}"`,
          `"${r.baseline.replace(/"/g, '""')}"`,
          `"${r.gap.replace(/"/g, '""')}"`,
        ].join(',')
      ),
    ].join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'literature_matrix.csv';
    link.click();
    URL.revokeObjectURL(url);
  }, [filteredRows]);

  const handleExportMarkdown = useCallback(() => {
    const mdLines = [
      '# Literature Comparison Matrix',
      '',
      '| Paper Title | Year | Methodology | Dataset / Benchmark | Key Metric | Baseline | Research Gap |',
      '| :--- | :---: | :--- | :--- | :--- | :--- | :--- |',
      ...filteredRows.map(
        (r) =>
          `| **${r.title}** (${r.authors}) | ${r.year} | ${r.method} | ${r.dataset} | ${r.metric} | ${r.baseline} | ${r.gap} |`
      ),
    ];
    const blob = new Blob([mdLines.join('\n')], { type: 'text/markdown;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'literature_matrix.md';
    link.click();
    URL.revokeObjectURL(url);
  }, [filteredRows]);

  const toggleSort = (field: keyof LiteratureMatrixRow) => {
    if (sortField === field) {
      setSortAsc((prev) => !prev);
    } else {
      setSortField(field);
      setSortAsc(true);
    }
  };

  return (
    <div className="flex flex-col h-full bg-bg overflow-hidden select-text">
      {/* Controls Bar */}
      <div className="p-4 bg-surface border-b border-border flex flex-wrap items-center justify-between gap-3 shrink-0">
        <div className="flex items-center gap-3 flex-1 min-w-[240px] max-w-md">
          <div className="relative w-full">
            <Search size={14} className="absolute left-3 top-2.5 text-text-dim" />
            <input
              type="text"
              className="w-full bg-bg border border-border rounded-lg pl-8 pr-3 py-1.5 text-xs text-text placeholder-text-dim focus:outline-none focus:border-primary"
              placeholder="Filter by method, dataset, claim, author..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            className="flex items-center gap-1.5 px-3 py-1.5 bg-bg border border-border hover:bg-surface-hover rounded-lg text-xs font-medium text-text-dim hover:text-text transition-colors"
            onClick={handleExportMarkdown}
            title="Export comparison table as Markdown"
          >
            <FileCode size={14} className="text-primary" />
            <span>Export Markdown</span>
          </button>
          <button
            type="button"
            className="flex items-center gap-1.5 px-3 py-1.5 bg-bg border border-border hover:bg-surface-hover rounded-lg text-xs font-medium text-text-dim hover:text-text transition-colors"
            onClick={handleExportCsv}
            title="Export comparison table as CSV"
          >
            <FileSpreadsheet size={14} className="text-success" />
            <span>Export CSV</span>
          </button>
        </div>
      </div>

      {/* Table Content */}
      <div className="flex-1 overflow-auto">
        <table className="w-full border-collapse text-left text-xs">
          <thead className="bg-surface sticky top-0 border-b border-border text-text-dim select-none z-10">
            <tr>
              <th
                className="py-3 px-4 font-semibold cursor-pointer hover:text-text transition-colors"
                onClick={() => toggleSort('title')}
              >
                Paper Title
              </th>
              <th
                className="py-3 px-3 font-semibold cursor-pointer hover:text-text transition-colors w-20 text-center"
                onClick={() => toggleSort('year')}
              >
                Year
              </th>
              <th
                className="py-3 px-4 font-semibold cursor-pointer hover:text-text transition-colors"
                onClick={() => toggleSort('method')}
              >
                Methodology
              </th>
              <th
                className="py-3 px-4 font-semibold cursor-pointer hover:text-text transition-colors"
                onClick={() => toggleSort('dataset')}
              >
                Benchmark Dataset
              </th>
              <th
                className="py-3 px-3 font-semibold cursor-pointer hover:text-text transition-colors"
                onClick={() => toggleSort('metric')}
              >
                Metric
              </th>
              <th className="py-3 px-4 font-semibold">Baseline</th>
              <th className="py-3 px-4 font-semibold text-error/90">Research Gap</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {filteredRows.length === 0 ? (
              <tr>
                <td colSpan={7} className="py-12 text-center text-text-dim">
                  <Table size={24} className="mx-auto mb-2 opacity-50" />
                  No literature comparison entries match the filter.
                </td>
              </tr>
            ) : (
              filteredRows.map((row) => {
                const isSelected = row.id === selectedPaperId;
                const matchedPaper = papers.find((p) => p.id === row.id);

                return (
                  <tr
                    key={row.id}
                    className={`cursor-pointer transition-colors ${
                      isSelected
                        ? 'bg-primary/10 hover:bg-primary/15'
                        : 'hover:bg-surface-hover/60'
                    }`}
                    onClick={() => matchedPaper && onSelectPaper(matchedPaper)}
                  >
                    <td className="py-3 px-4 font-medium text-text">
                      <div className="font-semibold">{row.title}</div>
                      <div className="text-[11px] text-text-dim mt-0.5">{row.authors}</div>
                    </td>
                    <td className="py-3 px-3 text-center text-text-dim font-mono">{row.year}</td>
                    <td className="py-3 px-4 text-text/90">{row.method}</td>
                    <td className="py-3 px-4 text-text/90 font-mono text-[11px]">{row.dataset}</td>
                    <td className="py-3 px-3 text-primary font-mono text-[11px] font-semibold">
                      {row.metric}
                    </td>
                    <td className="py-3 px-4 text-text-dim">{row.baseline}</td>
                    <td className="py-3 px-4 text-text/90 font-medium">{row.gap}</td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

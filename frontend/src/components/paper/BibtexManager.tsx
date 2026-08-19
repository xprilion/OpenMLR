import { useState, useMemo, useCallback } from 'react';
import { BookOpen, Plus, Search, Copy, Check, Trash2, Download } from 'lucide-react';
import type { BibtexEntry } from './types';

export interface BibtexManagerProps {
  entries: BibtexEntry[];
  onAddEntry: (entry: BibtexEntry) => void;
  onDeleteEntry: (id: string) => void;
  onInsertCite?: (key: string) => void;
}

export function BibtexManager({
  entries,
  onAddEntry,
  onDeleteEntry,
  onInsertCite,
}: Readonly<BibtexManagerProps>) {
  const [searchQuery, setSearchQuery] = useState('');
  const [showAddModal, setShowAddModal] = useState(false);
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

  // Form state
  const [rawBibtex, setRawBibtex] = useState('');
  const [parseError, setParseError] = useState('');

  const filteredEntries = useMemo(() => {
    const q = searchQuery.toLowerCase().trim();
    if (!q) return entries;
    return entries.filter(
      (e) =>
        e.citationKey.toLowerCase().includes(q) ||
        e.title.toLowerCase().includes(q) ||
        e.author.toLowerCase().includes(q) ||
        e.year.includes(q)
    );
  }, [entries, searchQuery]);

  const handleCopyCite = useCallback(async (key: string) => {
    const citeCmd = `\\cite{${key}}`;
    try {
      if (typeof navigator !== 'undefined' && navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(citeCmd);
      }
      setCopiedKey(key);
      setTimeout(() => setCopiedKey(null), 2000);
    } catch {
      /* ignore */
    }
  }, []);

  const handleParseAndAdd = useCallback(() => {
    if (!rawBibtex.trim()) return;
    try {
      // Basic BibTeX regex parser
      const typeMatch = rawBibtex.match(/@(\w+)\s*\{\s*([^,]+),/);
      if (!typeMatch) {
        setParseError('Invalid BibTeX syntax: Missing @type{key, header');
        return;
      }
      const entryType = typeMatch[1].toLowerCase();
      const citationKey = typeMatch[2].trim();

      const titleMatch = rawBibtex.match(/title\s*=\s*[{"]([^"}]+)[}"]/i);
      const authorMatch = rawBibtex.match(/author\s*=\s*[{"]([^"}]+)[}"]/i);
      const yearMatch = rawBibtex.match(/year\s*=\s*[{"]?(\d{4})[}"]?/i);
      const journalMatch = rawBibtex.match(/journal\s*=\s*[{"]([^"}]+)[}"]/i);
      const booktitleMatch = rawBibtex.match(/booktitle\s*=\s*[{"]([^"}]+)[}"]/i);

      const entry: BibtexEntry = {
        id: `bib-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
        citationKey,
        entryType,
        title: titleMatch ? titleMatch[1].trim() : citationKey,
        author: authorMatch ? authorMatch[1].trim() : 'Unknown Author',
        year: yearMatch ? yearMatch[1] : new Date().getFullYear().toString(),
        journal: journalMatch ? journalMatch[1].trim() : undefined,
        booktitle: booktitleMatch ? booktitleMatch[1].trim() : undefined,
        raw: rawBibtex.trim(),
      };

      onAddEntry(entry);
      setRawBibtex('');
      setParseError('');
      setShowAddModal(false);
    } catch (err: unknown) {
      setParseError(err instanceof Error ? err.message : 'Failed to parse BibTeX entry');
    }
  }, [rawBibtex, onAddEntry]);

  const handleDownloadBib = useCallback(() => {
    const content = entries.map((e) => e.raw || `@article{${e.citationKey},\n  title={${e.title}},\n  author={${e.author}},\n  year={${e.year}}\n}`).join('\n\n');
    const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'references.bib';
    link.click();
    URL.revokeObjectURL(url);
  }, [entries]);

  return (
    <div className="flex flex-col h-full bg-surface border-l border-border select-text">
      {/* Header */}
      <div className="p-4 border-b border-border flex items-center justify-between gap-2 shrink-0">
        <div className="flex items-center gap-2">
          <BookOpen size={18} className="text-primary" />
          <h3 className="text-sm font-semibold text-text">BibTeX Citations</h3>
          <span className="text-xs bg-surface-hover px-2 py-0.5 rounded-full text-text-dim">
            {entries.length}
          </span>
        </div>
        <div className="flex items-center gap-1.5">
          <button
            type="button"
            className="p-1.5 rounded-lg text-text-dim hover:text-text hover:bg-surface-hover transition-colors"
            onClick={handleDownloadBib}
            title="Download .bib file"
          >
            <Download size={16} />
          </button>
          <button
            type="button"
            className="flex items-center gap-1 text-xs bg-primary text-white font-medium px-2.5 py-1.5 rounded-lg hover:bg-primary-hover transition-colors"
            onClick={() => setShowAddModal(true)}
          >
            <Plus size={14} />
            <span>Add BibTeX</span>
          </button>
        </div>
      </div>

      {/* Search */}
      <div className="p-3 border-b border-border shrink-0">
        <div className="relative">
          <Search size={14} className="absolute left-3 top-2.5 text-text-dim" />
          <input
            type="text"
            className="w-full bg-bg border border-border rounded-lg pl-8 pr-3 py-1.5 text-xs text-text placeholder-text-dim focus:outline-none focus:border-primary"
            placeholder="Search citation key, title, author..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>
      </div>

      {/* Entries List */}
      <div className="flex-1 overflow-y-auto p-3 flex flex-col gap-2.5">
        {filteredEntries.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-48 text-center px-4">
            <BookOpen size={24} className="text-text-dim/60 mb-2" />
            <p className="text-xs text-text-dim">No BibTeX entries found.</p>
          </div>
        ) : (
          filteredEntries.map((entry) => (
            <div
              key={entry.id}
              className="p-3 bg-bg border border-border/80 rounded-lg hover:border-primary/40 transition-colors flex flex-col gap-1.5 group"
            >
              <div className="flex items-center justify-between gap-2">
                <span className="font-mono text-xs font-semibold text-primary">
                  @{entry.citationKey}
                </span>
                <div className="flex items-center gap-1 opacity-80 group-hover:opacity-100 transition-opacity">
                  {onInsertCite && (
                    <button
                      type="button"
                      className="text-[11px] px-2 py-0.5 rounded bg-surface text-text-dim hover:text-primary hover:bg-surface-hover transition-colors"
                      onClick={() => onInsertCite(entry.citationKey)}
                      title="Insert citation at cursor"
                    >
                      Insert
                    </button>
                  )}
                  <button
                    type="button"
                    className="p-1 text-text-dim hover:text-text hover:bg-surface-hover rounded transition-colors"
                    onClick={() => handleCopyCite(entry.citationKey)}
                    title="Copy \cite command"
                  >
                    {copiedKey === entry.citationKey ? (
                      <Check size={13} className="text-success" />
                    ) : (
                      <Copy size={13} />
                    )}
                  </button>
                  <button
                    type="button"
                    className="p-1 text-text-dim hover:text-error hover:bg-surface-hover rounded transition-colors"
                    onClick={() => onDeleteEntry(entry.id)}
                    title="Delete citation"
                  >
                    <Trash2 size={13} />
                  </button>
                </div>
              </div>
              <p className="text-xs text-text font-medium line-clamp-2 leading-tight">
                {entry.title}
              </p>
              <p className="text-[11px] text-text-dim truncate">
                {entry.author} ({entry.year})
              </p>
            </div>
          ))
        )}
      </div>

      {/* Add BibTeX Dialog */}
      {showAddModal && (
        <dialog
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 open:flex m-0 w-full h-full max-w-none max-h-none border-none"
          open
          onClose={() => setShowAddModal(false)}
        >
          <div className="bg-surface border border-border rounded-xl shadow-2xl w-full max-w-lg mx-4 p-5 flex flex-col gap-4">
            <h4 className="text-sm font-semibold text-text">Add BibTeX Entry</h4>
            <textarea
              className="w-full h-48 bg-bg border border-border rounded-lg p-3 text-xs font-mono text-text focus:outline-none focus:border-primary resize-none"
              placeholder={`@article{vaswani2017attention,\n  title={Attention is all you need},\n  author={Vaswani, Ashish and others},\n  journal={NeurIPS},\n  year={2017}\n}`}
              value={rawBibtex}
              onChange={(e) => {
                setRawBibtex(e.target.value);
                setParseError('');
              }}
            />
            {parseError && <p className="text-xs text-error">{parseError}</p>}
            <div className="flex items-center justify-end gap-2">
              <button
                type="button"
                className="px-3 py-1.5 text-xs text-text-dim hover:text-text hover:bg-surface-hover rounded-lg transition-colors"
                onClick={() => setShowAddModal(false)}
              >
                Cancel
              </button>
              <button
                type="button"
                className="px-4 py-1.5 text-xs bg-primary text-white font-medium rounded-lg hover:bg-primary-hover transition-colors"
                onClick={handleParseAndAdd}
              >
                Save Citation
              </button>
            </div>
          </div>
        </dialog>
      )}
    </div>
  );
}

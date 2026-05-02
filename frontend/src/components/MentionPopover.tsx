import { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { Plug, FileText, Folder } from 'lucide-react';
import type { McpServerStatus, FileNode, Mention } from '../types';
import { api } from '../api';

interface Props {
  readonly query: string;
  readonly mcpServers: readonly McpServerStatus[];
  readonly projectUuid: string | null;
  readonly onSelect: (mention: Mention, displayText: string) => void;
  readonly onClose: () => void;
}

interface PopoverItem {
  type: 'server' | 'file';
  label: string;
  value: string;
  isDir?: boolean;
}

function itemTypeLabel(item: PopoverItem): string {
  if (item.type === 'server') return 'MCP';
  if (item.isDir) return 'dir';
  return 'file';
}

function buildServerItems(mcpServers: readonly McpServerStatus[], query: string): PopoverItem[] {
  if (query.includes('/')) return [];
  const q = query.toLowerCase();
  return mcpServers
    .filter((s) => s.enabled && (!q || s.name.toLowerCase().includes(q)))
    .map((s) => ({ type: 'server' as const, label: s.name, value: s.name }));
}

function buildFileItems(files: readonly FileNode[], dirPath: string, fileFilter: string): PopoverItem[] {
  return files
    .filter((f) => !f.name.startsWith('.') && (!fileFilter || f.name.toLowerCase().includes(fileFilter)))
    .map((f) => {
      const fullPath = dirPath ? `${dirPath}/${f.name}` : f.name;
      const suffix = f.is_dir ? '/' : '';
      return { type: 'file' as const, label: f.name + suffix, value: fullPath + suffix, isDir: f.is_dir };
    });
}

export function MentionPopover({ query, mcpServers, projectUuid, onSelect, onClose }: Props) {
  const [files, setFiles] = useState<FileNode[]>([]);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const listRef = useRef<HTMLDivElement>(null);

  // Determine directory path from query for file listing
  const lastSlash = query.lastIndexOf('/');
  const dirPath = lastSlash >= 0 ? query.slice(0, lastSlash) : '';
  const fileFilter = lastSlash >= 0 ? query.slice(lastSlash + 1).toLowerCase() : query.toLowerCase();

  // Load files from project workspace
  useEffect(() => {
    if (!projectUuid) { setFiles([]); return; }
    let cancelled = false;
    api.listFiles(projectUuid, dirPath).then((data) => {
      if (!cancelled) setFiles(data.entries || []);
    }).catch(() => { if (!cancelled) setFiles([]); });
    return () => { cancelled = true; };
  }, [projectUuid, dirPath]);

  // Build filtered items list (memoised to avoid rebuilding on every render)
  const items = useMemo<PopoverItem[]>(
    () => [...buildServerItems(mcpServers, query), ...buildFileItems(files, dirPath, fileFilter)],
    [mcpServers, query, files, dirPath, fileFilter],
  );

  // Clamp selected index
  useEffect(() => {
    setSelectedIndex((prev) => Math.min(prev, Math.max(0, items.length - 1)));
  }, [items.length]);

  // Scroll selected item into view
  useEffect(() => {
    const el = listRef.current?.querySelector('[data-selected="true"]');
    el?.scrollIntoView({ block: 'nearest' });
  }, [selectedIndex]);

  const handleSelect = useCallback((item: PopoverItem) => {
    if (item.isDir) {
      onSelect({ type: 'file', value: item.value }, item.value);
      return;
    }
    onSelect({ type: item.type, value: item.value }, item.label);
  }, [onSelect]);

  // Keyboard navigation
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      switch (e.key) {
        case 'ArrowDown':
          e.preventDefault();
          setSelectedIndex((i) => Math.min(i + 1, items.length - 1));
          break;
        case 'ArrowUp':
          e.preventDefault();
          setSelectedIndex((i) => Math.max(i - 1, 0));
          break;
        case 'Enter':
        case 'Tab':
          e.preventDefault();
          if (items[selectedIndex]) handleSelect(items[selectedIndex]);
          break;
        case 'Escape':
          e.preventDefault();
          onClose();
          break;
      }
    };
    globalThis.addEventListener('keydown', handler, true);
    return () => globalThis.removeEventListener('keydown', handler, true);
  }, [items, selectedIndex, handleSelect, onClose]);

  if (items.length === 0) return null;

  return (
    <div className="absolute bottom-full left-0 right-0 mb-1 bg-surface border border-border rounded-lg shadow-xl z-50 max-h-64 overflow-auto"
         ref={listRef}>
      <div className="py-1">
        {items.map((item, i) => (
          <button
            key={`${item.type}-${item.value}`}
            data-selected={i === selectedIndex}
            className={`w-full flex items-center gap-2 px-3 py-1.5 text-sm text-left transition-colors ${
              i === selectedIndex ? 'bg-primary/20 text-text' : 'text-text-dim hover:bg-surface-hover'
            }`}
            onMouseDown={(e) => { e.preventDefault(); handleSelect(item); }}
            onMouseEnter={() => setSelectedIndex(i)}
          >
            {item.type === 'server' && <Plug size={14} className="text-primary shrink-0" />}
            {item.type === 'file' && !item.isDir && <FileText size={14} className="text-text-dim shrink-0" />}
            {item.isDir && <Folder size={14} className="text-warning shrink-0" />}
            <span className="truncate">{item.label}</span>
            <span className="ml-auto text-xs text-text-dim shrink-0">
              {itemTypeLabel(item)}
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}

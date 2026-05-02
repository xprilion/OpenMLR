import { useState, useEffect, useRef, useCallback } from 'react';
import { Plug, FileText, Folder } from 'lucide-react';
import type { McpServerStatus, FileNode, Mention } from '../types';
import { api } from '../api';

interface Props {
  query: string;
  mcpServers: readonly McpServerStatus[];
  projectUuid: string | null;
  onSelect: (mention: Mention, displayText: string) => void;
  onClose: () => void;
}

interface PopoverItem {
  type: 'server' | 'file';
  label: string;
  value: string;
  isDir?: boolean;
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
    if (!projectUuid) {
      setFiles([]);
      return;
    }
    let cancelled = false;
    api.listFiles(projectUuid, dirPath).then((data) => {
      if (!cancelled) setFiles(data.entries || []);
    }).catch(() => {
      if (!cancelled) setFiles([]);
    });
    return () => { cancelled = true; };
  }, [projectUuid, dirPath]);

  // Build filtered items list
  const items: PopoverItem[] = [];

  // MCP servers (only when not typing a path)
  if (!query.includes('/')) {
    for (const s of mcpServers) {
      if (!s.enabled) continue;
      if (query && !s.name.toLowerCase().includes(query.toLowerCase())) continue;
      items.push({ type: 'server', label: s.name, value: s.name });
    }
  }

  // Files
  for (const f of files) {
    if (f.name.startsWith('.')) continue;
    if (fileFilter && !f.name.toLowerCase().includes(fileFilter)) continue;
    const fullPath = dirPath ? `${dirPath}/${f.name}` : f.name;
    items.push({
      type: 'file',
      label: f.name + (f.is_dir ? '/' : ''),
      value: fullPath + (f.is_dir ? '/' : ''),
      isDir: f.is_dir,
    });
  }

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
      // For directories, don't close — let the user keep browsing
      // The query will update to include the directory path
      onSelect({ type: 'file', value: item.value }, item.value);
      return;
    }
    onSelect({ type: item.type, value: item.value }, item.label);
  }, [onSelect]);

  // Keyboard navigation — called from InputArea
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setSelectedIndex((i) => Math.min(i + 1, items.length - 1));
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        setSelectedIndex((i) => Math.max(i - 1, 0));
      } else if (e.key === 'Enter' || e.key === 'Tab') {
        e.preventDefault();
        if (items[selectedIndex]) handleSelect(items[selectedIndex]);
      } else if (e.key === 'Escape') {
        e.preventDefault();
        onClose();
      }
    };
    window.addEventListener('keydown', handler, true);
    return () => window.removeEventListener('keydown', handler, true);
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
              {item.type === 'server' ? 'MCP' : (item.isDir ? 'dir' : 'file')}
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}

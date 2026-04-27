import { useState, useCallback, useEffect } from 'react';
import {
  Folder,
  FolderOpen,
  FileText,
  FileCode,
  FileJson,
  Image,
  ChevronRight,
  ChevronDown,
  RefreshCw,
  AlertCircle,
} from 'lucide-react';
import { api } from '../api';
import type { FileNode } from '../types';

interface Props {
  projectUuid: string;
  onFileSelect?: (path: string, content: string) => void;
}

interface TreeNode extends FileNode {
  children?: TreeNode[];
  loading?: boolean;
  expanded?: boolean;
}

const FILE_ICONS: Record<string, React.ReactNode> = {
  '.py': <FileCode size={14} className="text-blue-400" />,
  '.js': <FileCode size={14} className="text-yellow-400" />,
  '.ts': <FileCode size={14} className="text-blue-500" />,
  '.tsx': <FileCode size={14} className="text-blue-500" />,
  '.json': <FileJson size={14} className="text-green-400" />,
  '.md': <FileText size={14} className="text-text-dim" />,
  '.txt': <FileText size={14} className="text-text-dim" />,
  '.yaml': <FileCode size={14} className="text-red-400" />,
  '.yml': <FileCode size={14} className="text-red-400" />,
  '.png': <Image size={14} className="text-purple-400" />,
  '.jpg': <Image size={14} className="text-purple-400" />,
  '.svg': <Image size={14} className="text-purple-400" />,
};

function getFileIcon(name: string, isDir: boolean): React.ReactNode {
  if (isDir) return null; // handled by folder icons
  const ext = name.includes('.') ? '.' + name.split('.').pop() : '';
  return FILE_ICONS[ext] || <FileText size={14} className="text-text-dim" />;
}

function formatSize(bytes: number | null): string {
  if (bytes === null || bytes === undefined) return '';
  if (bytes < 1024) return `${bytes}B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)}K`;
  return `${(bytes / (1024 * 1024)).toFixed(1)}M`;
}

function TreeItem({
  node,
  depth,
  onToggle,
  onSelect,
}: {
  node: TreeNode;
  depth: number;
  onToggle: (path: string) => void;
  onSelect: (path: string) => void;
}) {
  return (
    <div>
      <button
        className={`flex items-center gap-1.5 w-full text-left px-2 py-1 text-sm rounded hover:bg-surface-hover transition-colors group ${
          node.is_dir ? 'text-text' : 'text-text-dim hover:text-text'
        }`}
        style={{ paddingLeft: `${depth * 16 + 8}px` }}
        onClick={() => node.is_dir ? onToggle(node.path) : onSelect(node.path)}
      >
        {/* Expand/collapse chevron for directories */}
        {node.is_dir ? (
          <span className="shrink-0 text-text-dim">
            {node.loading ? (
              <RefreshCw size={12} className="animate-spin" />
            ) : node.expanded ? (
              <ChevronDown size={12} />
            ) : (
              <ChevronRight size={12} />
            )}
          </span>
        ) : (
          <span className="w-3 shrink-0" /> // spacer for files
        )}

        {/* Icon */}
        <span className="shrink-0">
          {node.is_dir ? (
            node.expanded ? <FolderOpen size={14} className="text-primary" /> : <Folder size={14} className="text-primary" />
          ) : (
            getFileIcon(node.name, false)
          )}
        </span>

        {/* Name */}
        <span className="truncate flex-1">{node.name}</span>

        {/* Size (for files) */}
        {!node.is_dir && node.size !== null && (
          <span className="text-xs text-text-dim shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">
            {formatSize(node.size)}
          </span>
        )}
      </button>

      {/* Children */}
      {node.is_dir && node.expanded && node.children && (
        <div>
          {node.children.map((child) => (
            <TreeItem
              key={child.path}
              node={child}
              depth={depth + 1}
              onToggle={onToggle}
              onSelect={onSelect}
            />
          ))}
          {node.children.length === 0 && (
            <div
              className="text-xs text-text-dim italic px-2 py-1"
              style={{ paddingLeft: `${(depth + 1) * 16 + 8}px` }}
            >
              (empty)
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export function FileTree({ projectUuid, onFileSelect }: Props) {
  const [nodes, setNodes] = useState<TreeNode[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const [fileContent, setFileContent] = useState<string | null>(null);
  const [fileLoading, setFileLoading] = useState(false);

  const loadDirectory = useCallback(async (path: string = ''): Promise<TreeNode[]> => {
    try {
      const data = await api.listFiles(projectUuid, path);
      return (data.entries || []).map((entry: FileNode) => ({
        ...entry,
        expanded: false,
        children: entry.is_dir ? undefined : undefined,
      }));
    } catch (err: any) {
      setError(err.message);
      return [];
    }
  }, [projectUuid]);

  // Initial load
  useEffect(() => {
    setLoading(true);
    setError(null);
    loadDirectory('').then((entries) => {
      setNodes(entries);
      setLoading(false);
    });
  }, [projectUuid, loadDirectory]);

  const handleToggle = useCallback(async (path: string) => {
    setNodes((prev) => {
      const update = (items: TreeNode[]): TreeNode[] =>
        items.map((item) => {
          if (item.path === path) {
            if (item.expanded) {
              return { ...item, expanded: false };
            }
            return { ...item, loading: true, expanded: true };
          }
          if (item.children) {
            return { ...item, children: update(item.children) };
          }
          return item;
        });
      return update(prev);
    });

    // Load children
    const children = await loadDirectory(path);
    setNodes((prev) => {
      const update = (items: TreeNode[]): TreeNode[] =>
        items.map((item) => {
          if (item.path === path) {
            return { ...item, loading: false, children };
          }
          if (item.children) {
            return { ...item, children: update(item.children) };
          }
          return item;
        });
      return update(prev);
    });
  }, [loadDirectory]);

  const handleSelect = useCallback(async (path: string) => {
    setSelectedFile(path);
    setFileLoading(true);
    setFileContent(null);
    try {
      const data = await api.readFile(projectUuid, path);
      if (data.content !== undefined) {
        setFileContent(data.content);
        onFileSelect?.(path, data.content);
      }
    } catch {
      setFileContent(null);
    }
    setFileLoading(false);
  }, [projectUuid, onFileSelect]);

  const handleRefresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    const entries = await loadDirectory('');
    setNodes(entries);
    setLoading(false);
  }, [loadDirectory]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-8 text-text-dim text-sm">
        <RefreshCw size={14} className="animate-spin mr-2" />
        Loading files...
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center gap-2 px-3 py-4 text-error text-sm">
        <AlertCircle size={14} />
        {error}
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-border">
        <span className="text-xs uppercase tracking-wider text-text-dim font-semibold">Files</span>
        <button
          className="w-6 h-6 rounded flex items-center justify-center text-text-dim hover:text-text hover:bg-surface-hover transition-colors"
          onClick={handleRefresh}
          title="Refresh"
        >
          <RefreshCw size={12} />
        </button>
      </div>

      {/* Tree */}
      <div className="flex-1 overflow-auto py-1">
        {nodes.length === 0 ? (
          <div className="text-sm text-text-dim px-3 py-4">No files yet</div>
        ) : (
          nodes.map((node) => (
            <TreeItem
              key={node.path}
              node={node}
              depth={0}
              onToggle={handleToggle}
              onSelect={handleSelect}
            />
          ))
        )}
      </div>

      {/* Selected file preview */}
      {selectedFile && (
        <div className="border-t border-border">
          <div className="flex items-center justify-between px-3 py-1.5 bg-surface-hover">
            <span className="text-xs text-text-dim truncate">{selectedFile}</span>
            <button
              className="w-5 h-5 rounded flex items-center justify-center text-text-dim hover:text-text"
              onClick={() => { setSelectedFile(null); setFileContent(null); }}
              title="Close"
            >
              ×
            </button>
          </div>
          {fileLoading ? (
            <div className="px-3 py-4 text-xs text-text-dim">Loading...</div>
          ) : fileContent !== null ? (
            <pre className="px-3 py-2 text-xs text-text overflow-auto max-h-48 font-mono whitespace-pre-wrap">
              {fileContent.length > 5000 ? fileContent.slice(0, 5000) + '\n...' : fileContent}
            </pre>
          ) : (
            <div className="px-3 py-4 text-xs text-text-dim">Binary file</div>
          )}
        </div>
      )}
    </div>
  );
}

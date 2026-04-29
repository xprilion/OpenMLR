import { X, FileText } from 'lucide-react';
import Editor from '@monaco-editor/react';
import type { OpenFile } from '../types';

interface Props {
  readonly openFiles: readonly OpenFile[];
  readonly activeFilePath: string | null;
  readonly onActivateFile: (path: string) => void;
  readonly onCloseFile: (path: string) => void;
}

/** Extract just the filename from a full path. */
function basename(path: string): string {
  return path.split('/').pop() || path;
}

export function EditorPanel({ openFiles, activeFilePath, onActivateFile, onCloseFile }: Props) {
  const activeFile = openFiles.find((f) => f.path === activeFilePath);

  if (openFiles.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center flex-1 text-center px-6 py-12">
        <FileText size={48} className="text-text-dim mb-4" strokeWidth={1} />
        <p className="text-text-dim">Select a file from the Files panel to view it here.</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col flex-1 overflow-hidden">
      {/* File tabs */}
      <div className="flex items-center bg-surface border-b border-border shrink-0 overflow-x-auto">
        {openFiles.map((f) => (
          <div
            key={f.path}
            className={`flex items-center gap-1.5 pl-3 pr-1 py-2 text-xs border-r border-border cursor-pointer shrink-0 transition-colors ${
              f.path === activeFilePath
                ? 'bg-bg text-text'
                : 'text-text-dim hover:text-text hover:bg-surface-hover'
            }`}
          >
            <button
              className="truncate max-w-[160px]"
              onClick={() => onActivateFile(f.path)}
              title={f.path}
            >
              {basename(f.path)}
            </button>
            <button
              className="w-5 h-5 rounded flex items-center justify-center text-text-dim hover:text-text hover:bg-surface-hover transition-colors shrink-0"
              onClick={(e) => {
                e.stopPropagation();
                onCloseFile(f.path);
              }}
              title="Close"
            >
              <X size={12} />
            </button>
          </div>
        ))}
      </div>

      {/* Monaco editor */}
      {activeFile ? (
        <div className="flex-1">
          <Editor
            height="100%"
            language={activeFile.language}
            value={activeFile.content}
            theme="vs-dark"
            options={{
              readOnly: true,
              minimap: { enabled: true },
              lineNumbers: 'on',
              scrollBeyondLastLine: false,
              wordWrap: 'on',
              fontSize: 13,
              renderLineHighlight: 'line',
              bracketPairColorization: { enabled: true },
              guides: { bracketPairs: true },
              domReadOnly: true,
              contextmenu: false,
            }}
            loading={
              <div className="flex items-center justify-center h-full text-text-dim text-sm">
                Loading editor...
              </div>
            }
          />
        </div>
      ) : (
        <div className="flex-1 flex items-center justify-center text-text-dim text-sm">
          Select a tab above to view a file.
        </div>
      )}
    </div>
  );
}

import { Loader2, CheckCircle2, XCircle } from 'lucide-react';

export interface McpServer {
  name: string;
  url: string;
  headers?: Record<string, string>;
  params?: Record<string, string>;
  enabled: boolean;
  modes?: string[];
}

export interface McpServerModalProps {
  isOpen: boolean;
  editingIndex: number | null;
  form: McpServer;
  setForm: React.Dispatch<React.SetStateAction<McpServer>>;
  jsonConfig: string;
  setJsonConfig: (v: string) => void;
  jsonError: string;
  setJsonError: (v: string) => void;
  testResult: { ok: boolean; tools?: number; error?: string } | null;
  testing: boolean;
  saving: boolean;
  onClose: () => void;
  onTest: () => void;
  onSave: () => void;
}

export function McpServerModal({
  isOpen,
  editingIndex,
  form,
  setForm,
  jsonConfig,
  setJsonConfig,
  jsonError,
  setJsonError,
  testResult,
  testing,
  saving,
  onClose,
  onTest,
  onSave,
}: McpServerModalProps) {
  if (!isOpen) return null;

  return (
    <dialog
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 open:flex m-0 w-full h-full max-w-none max-h-none border-none"
      open
      onClose={onClose}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
      onKeyDown={(e) => {
        if (e.key === 'Escape') onClose();
      }}
    >
      <div
        className="bg-surface border border-border rounded-xl shadow-2xl w-full max-w-lg mx-4"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Modal header */}
        <div className="px-6 py-4 border-b border-border">
          <h3 className="text-base font-semibold text-text">
            {editingIndex !== null ? 'Edit MCP Server' : 'Add MCP Server'}
          </h3>
        </div>

        {/* Modal body */}
        <div className="px-6 py-5 flex flex-col gap-4">
          <div>
            <label className="block text-sm font-medium text-text mb-1.5" htmlFor="mcp-name">
              Server Name
            </label>
            <input
              id="mcp-name"
              type="text"
              className="w-full bg-bg border border-border rounded-lg px-4 py-2.5 text-text placeholder-text-dim focus:border-primary focus:outline-none"
              placeholder="my-mcp-server"
              value={form.name}
              onChange={(e) => setForm((f: McpServer) => ({ ...f, name: e.target.value }))}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-text mb-1.5" htmlFor="mcp-url">
              Server URL
            </label>
            <input
              id="mcp-url"
              type="text"
              className="w-full bg-bg border border-border rounded-lg px-4 py-2.5 text-text placeholder-text-dim focus:border-primary focus:outline-none font-mono text-sm"
              placeholder="https://mcp-server.example.com/sse"
              value={form.url}
              onChange={(e) => setForm((f: McpServer) => ({ ...f, url: e.target.value }))}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-text mb-1.5" htmlFor="mcp-config">
              Configuration (JSON)
            </label>
            <p className="text-xs text-text-dim mb-2">
              Optional headers and query params for authentication.
            </p>
            <textarea
              id="mcp-config"
              className={`w-full bg-bg border rounded-lg px-4 py-2.5 text-text placeholder-text-dim focus:outline-none font-mono text-xs resize-none transition-colors ${
                jsonError ? 'border-error focus:border-error' : 'border-border focus:border-primary'
              }`}
              placeholder={'{\n  "headers": {\n    "Authorization": "Bearer xxx"\n  },\n  "params": {}\n}'}
              value={jsonConfig}
              onChange={(e) => {
                setJsonConfig(e.target.value);
                setJsonError('');
              }}
              rows={6}
              spellCheck={false}
            />
            {jsonError && <p className="text-xs text-error mt-1">{jsonError}</p>}
          </div>

          {/* Mode availability */}
          <div>
            <p className="block text-sm font-medium text-text mb-1.5">Available in Modes</p>
            <div className="flex items-center gap-4">
              <label className="flex items-center gap-2 text-sm text-text cursor-pointer">
                <input
                  type="checkbox"
                  className="rounded border-border accent-primary"
                  checked={form.modes?.includes('plan') ?? true}
                  onChange={(e) => {
                    setForm((f: McpServer) => {
                      const modes = new Set(f.modes || ['plan', 'execute']);
                      if (e.target.checked) {
                        modes.add('plan');
                      } else {
                        modes.delete('plan');
                      }
                      return { ...f, modes: Array.from(modes) };
                    });
                  }}
                />
                Plan mode
              </label>
              <label className="flex items-center gap-2 text-sm text-text cursor-pointer">
                <input
                  type="checkbox"
                  className="rounded border-border accent-primary"
                  checked={form.modes?.includes('execute') ?? true}
                  onChange={(e) => {
                    setForm((f: McpServer) => {
                      const modes = new Set(f.modes || ['plan', 'execute']);
                      if (e.target.checked) {
                        modes.add('execute');
                      } else {
                        modes.delete('execute');
                      }
                      return { ...f, modes: Array.from(modes) };
                    });
                  }}
                />
                Execute mode
              </label>
            </div>
          </div>

          {/* Test result */}
          {testResult && (
            <div
              className={`flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm ${
                testResult.ok ? 'bg-success/10 text-success' : 'bg-error/10 text-error'
              }`}
            >
              {testResult.ok ? (
                <>
                  <CheckCircle2 size={16} />
                  Connected — {testResult.tools} tool{testResult.tools !== 1 ? 's' : ''} available
                </>
              ) : (
                <>
                  <XCircle size={16} />
                  {testResult.error || 'Connection failed'}
                </>
              )}
            </div>
          )}
        </div>

        {/* Modal footer */}
        <div className="px-6 py-4 border-t border-border flex items-center gap-3">
          <button
            className="px-4 py-2 text-sm font-medium text-text-dim hover:text-text hover:bg-surface-hover rounded-lg transition-colors"
            onClick={onClose}
          >
            Cancel
          </button>
          <div className="flex-1" />
          <button
            className="px-4 py-2 text-sm font-medium rounded-lg border border-border text-text hover:bg-surface-hover transition-colors flex items-center gap-2 disabled:opacity-50"
            onClick={onTest}
            disabled={testing || !form.url.trim()}
          >
            {testing ? <Loader2 size={14} className="animate-spin" /> : null}
            {testing ? 'Testing...' : 'Test Connection'}
          </button>
          <button
            className="px-5 py-2 text-sm font-medium bg-primary text-white rounded-lg hover:bg-primary-hover transition-colors disabled:opacity-50"
            onClick={onSave}
            disabled={saving || !form.name.trim() || !form.url.trim()}
          >
            {saving ? 'Saving...' : 'Save'}
          </button>
        </div>
      </div>
    </dialog>
  );
}

import { useState, useEffect, useCallback } from 'react';
import { api } from '../../api';
import {
  Plus,
  Pencil,
  Trash2,
  ExternalLink,
} from 'lucide-react';
import { McpServerModal, type McpServer } from './McpServerModal';

const EMPTY_SERVER: McpServer = { name: '', url: '', enabled: true, modes: ['plan', 'execute'] };

export type { McpServer };

export function McpSettings() {
  const [servers, setServers] = useState<McpServer[]>([]);
  const [saving, setSaving] = useState(false);
  const [saveMsg, setSaveMsg] = useState('');
  const [modalOpen, setModalOpen] = useState(false);
  const [editingIndex, setEditingIndex] = useState<number | null>(null);
  const [form, setForm] = useState<McpServer>(EMPTY_SERVER);
  const [jsonConfig, setJsonConfig] = useState('');
  const [jsonError, setJsonError] = useState('');
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<{ ok: boolean; tools?: number; error?: string } | null>(null);

  useEffect(() => {
    api
      .getSettings()
      .then((d) => {
        const s = d.settings || {};
        if (s.mcp?.servers) {
          const serverList: McpServer[] = [];
          for (const [name, config] of Object.entries(s.mcp.servers as Record<string, unknown>)) {
            const cfg = config as Record<string, unknown>;
            serverList.push({
              name,
              url: (cfg.url as string) || '',
              headers: (cfg.headers as Record<string, string>) || undefined,
              params: (cfg.params as Record<string, string>) || undefined,
              enabled: cfg.enabled !== false,
              modes: (cfg.modes as string[]) || ['plan', 'execute'],
            });
          }
          setServers(serverList);
        }
      })
      .catch(() => {});
  }, []);

  const flash = useCallback((msg: string) => {
    setSaveMsg(msg);
    setTimeout(() => setSaveMsg(''), 2500);
  }, []);

  const saveServers = async (serverList: McpServer[]) => {
    setSaving(true);
    try {
      const serversObj: Record<string, unknown> = {};
      for (const server of serverList) {
        if (!server.name) continue;
        const entry: Record<string, unknown> = {
          url: server.url,
          enabled: server.enabled,
        };
        if (server.headers && Object.keys(server.headers).length > 0) {
          entry.headers = server.headers;
        }
        if (server.params && Object.keys(server.params).length > 0) {
          entry.params = server.params;
        }
        entry.modes = server.modes || ['plan', 'execute'];
        serversObj[server.name] = entry;
      }
      await api.updateSetting('mcp', 'servers', serversObj);
      flash('Saved');
    } catch {
      flash('Error saving');
    } finally {
      setSaving(false);
    }
  };

  const openAddModal = () => {
    setForm({ ...EMPTY_SERVER });
    setJsonConfig(JSON.stringify({ headers: {}, params: {} }, null, 2));
    setJsonError('');
    setTestResult(null);
    setEditingIndex(null);
    setModalOpen(true);
  };

  const openEditModal = (index: number) => {
    const server = servers[index];
    setForm({ ...server });
    const configObj: Record<string, unknown> = {};
    if (server.headers && Object.keys(server.headers).length > 0) {
      configObj.headers = server.headers;
    }
    if (server.params && Object.keys(server.params).length > 0) {
      configObj.params = server.params;
    }
    setJsonConfig(
      Object.keys(configObj).length > 0
        ? JSON.stringify(configObj, null, 2)
        : JSON.stringify({ headers: {}, params: {} }, null, 2)
    );
    setJsonError('');
    setTestResult(null);
    setEditingIndex(index);
    setModalOpen(true);
  };

  const closeModal = () => {
    setModalOpen(false);
    setEditingIndex(null);
    setTestResult(null);
    setJsonError('');
  };

  const parseJsonConfig = (): { headers?: Record<string, string>; params?: Record<string, string> } | null => {
    const trimmed = jsonConfig.trim();
    if (!trimmed || trimmed === '{}') return {};
    try {
      const parsed = JSON.parse(trimmed);
      if (typeof parsed !== 'object' || Array.isArray(parsed)) {
        setJsonError('Config must be a JSON object');
        return null;
      }
      setJsonError('');
      return {
        headers: parsed.headers || undefined,
        params: parsed.params || undefined,
      };
    } catch (e: any) {
      setJsonError(`Invalid JSON: ${e.message}`);
      return null;
    }
  };

  const handleTest = async () => {
    if (!form.url.trim()) {
      flash('URL is required');
      return;
    }
    if (!form.url.startsWith('http://') && !form.url.startsWith('https://')) {
      flash('URL must start with http:// or https://');
      return;
    }
    const config = parseJsonConfig();
    if (config === null) return;

    setTesting(true);
    setTestResult(null);
    try {
      const result = await api.testMcpServer(form.url, config.headers, config.params);
      setTestResult(result);
    } catch (e: any) {
      setTestResult({ ok: false, error: e.message || 'Connection failed' });
    } finally {
      setTesting(false);
    }
  };

  const handleSave = async () => {
    if (!form.name.trim()) {
      flash('Server name is required');
      return;
    }
    if (!form.url.trim()) {
      flash('URL is required');
      return;
    }
    const config = parseJsonConfig();
    if (config === null) return;

    const server: McpServer = {
      name: form.name.trim(),
      url: form.url.trim(),
      headers: config.headers,
      params: config.params,
      enabled: form.enabled,
    };

    let newServers: McpServer[];
    if (editingIndex !== null) {
      newServers = servers.map((s, i) => (i === editingIndex ? server : s));
    } else {
      newServers = [...servers, server];
    }

    setServers(newServers);
    await saveServers(newServers);
    closeModal();
  };

  const deleteServer = async (index: number) => {
    const newServers = servers.filter((_, i) => i !== index);
    setServers(newServers);
    await saveServers(newServers);
  };

  const toggleServer = async (index: number) => {
    const newServers = servers.map((s, i) => (i === index ? { ...s, enabled: !s.enabled } : s));
    setServers(newServers);
    await saveServers(newServers);
  };

  return (
    <div>
      {saveMsg && <div className="mb-4 px-4 py-2 bg-success/10 text-success rounded-lg text-sm">{saveMsg}</div>}

      <p className="text-text-dim mb-6">
        Configure remote MCP (Model Context Protocol) servers to extend the agent with additional tools. Only
        HTTP/HTTPS servers are supported. Add authentication via headers or query parameters.
      </p>

      {/* Server list */}
      <div className="flex flex-col gap-3 mb-6">
        {servers.length === 0 && !modalOpen && (
          <div className="text-center py-8 bg-surface rounded-lg border border-border text-text-dim">
            No MCP servers configured. Add one to extend the agent's capabilities.
          </div>
        )}

        {servers.map((server, index) => (
          <div
            key={server.name}
            className={`flex items-center gap-4 px-5 py-3.5 rounded-lg border transition-colors ${
              !server.enabled ? 'bg-surface/50 border-border opacity-60' : 'bg-surface border-border'
            }`}
          >
            <span
              className={`w-2.5 h-2.5 rounded-full shrink-0 ${server.enabled ? 'bg-success' : 'bg-text-dim'}`}
              title={server.enabled ? 'Enabled' : 'Disabled'}
            />

            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="text-sm font-mono text-text truncate">{server.url}</span>
              </div>
              <div className="flex items-center gap-2 mt-0.5">
                <span className="text-xs text-text-dim">{server.name}</span>
                {server.headers && Object.keys(server.headers).length > 0 && (
                  <span className="text-[10px] px-1.5 py-0.5 rounded bg-primary/10 text-primary">Auth</span>
                )}
              </div>
            </div>

            <div className="flex items-center gap-1.5 shrink-0">
              <button
                className="px-2.5 py-1 text-xs text-text-dim hover:text-text hover:bg-surface-hover rounded transition-colors"
                onClick={() => toggleServer(index)}
              >
                {server.enabled ? 'Disable' : 'Enable'}
              </button>
              <button
                className="w-7 h-7 rounded flex items-center justify-center text-text-dim hover:text-text hover:bg-surface-hover transition-colors"
                onClick={() => openEditModal(index)}
                title="Edit"
              >
                <Pencil size={13} />
              </button>
              <button
                className="w-7 h-7 rounded flex items-center justify-center text-text-dim hover:text-error hover:bg-error-bg transition-colors"
                onClick={() => deleteServer(index)}
                title="Delete"
              >
                <Trash2 size={13} />
              </button>
            </div>
          </div>
        ))}
      </div>

      <button
        className="w-full py-3 bg-primary text-white rounded-lg font-medium hover:bg-primary-hover transition-colors flex items-center justify-center gap-2"
        onClick={openAddModal}
      >
        <Plus size={16} />
        Add MCP Server
      </button>

      {/* Help section */}
      <div className="mt-8 p-5 bg-surface rounded-lg border border-border">
        <h4 className="font-semibold text-text mb-3">Popular MCP Servers</h4>
        <ul className="flex flex-col gap-2 text-sm text-text-dim mb-4">
          <li>
            <strong className="text-text">Composio</strong>:{' '}
            <code className="bg-bg px-1.5 py-0.5 rounded text-xs">https://mcp.composio.dev/...</code>
          </li>
          <li>
            <strong className="text-text">Zapier MCP</strong>:{' '}
            <code className="bg-bg px-1.5 py-0.5 rounded text-xs">https://actions.zapier.com/mcp/...</code>
          </li>
          <li>
            <strong className="text-text">Browserbase</strong>:{' '}
            <code className="bg-bg px-1.5 py-0.5 rounded text-xs">https://mcp.browserbase.com</code>
          </li>
        </ul>
        <p className="text-sm text-text-dim">
          Learn more at{' '}
          <a
            href="https://modelcontextprotocol.io/docs"
            target="_blank"
            rel="noopener noreferrer"
            className="text-primary hover:underline inline-flex items-center gap-1"
          >
            modelcontextprotocol.io <ExternalLink size={11} />
          </a>
        </p>
      </div>

      <McpServerModal
        isOpen={modalOpen}
        editingIndex={editingIndex}
        form={form}
        setForm={setForm}
        jsonConfig={jsonConfig}
        setJsonConfig={setJsonConfig}
        jsonError={jsonError}
        setJsonError={setJsonError}
        testResult={testResult}
        testing={testing}
        saving={saving}
        onClose={closeModal}
        onTest={handleTest}
        onSave={handleSave}
      />
    </div>
  );
}

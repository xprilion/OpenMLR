

import { useState, useEffect, useCallback } from 'react';
import { api } from '../../api';

interface McpServer {
  name: string;
  transport: 'http' | 'stdio';
  url?: string;
  command?: string;
  args?: string[];
  env?: Record<string, string>;
  enabled: boolean;
}

const DEFAULT_SERVER: McpServer = {
  name: '',
  transport: 'http',
  url: '',
  enabled: true,
};

export function McpSettings() {
  const [servers, setServers] = useState<McpServer[]>([]);
  const [saving, setSaving] = useState(false);
  const [saveMsg, setSaveMsg] = useState('');
  const [editingIndex, setEditingIndex] = useState<number | null>(null);
  const [editForm, setEditForm] = useState<McpServer>(DEFAULT_SERVER);

  useEffect(() => {
    api.getSettings().then((d) => {
      const s = d.settings || {};
      if (s.mcp?.servers) {
        // Convert from stored format to array
        const serverList: McpServer[] = [];
        for (const [name, config] of Object.entries(s.mcp.servers as Record<string, unknown>)) {
          const cfg = config as Record<string, unknown>;
          serverList.push({
            name,
            transport: (cfg.transport as 'http' | 'stdio') || 'http',
            url: cfg.url as string || '',
            command: cfg.command as string || '',
            args: cfg.args as string[] || [],
            env: cfg.env as Record<string, string> || {},
            enabled: cfg.enabled !== false,
          });
        }
        setServers(serverList);
      }
    }).catch(() => {});
  }, []);

  const flash = useCallback((msg: string) => {
    setSaveMsg(msg);
    setTimeout(() => setSaveMsg(''), 2000);
  }, []);

  const saveServers = async (serverList: McpServer[]) => {
    setSaving(true);
    try {
      // Convert to object format for storage
      const serversObj: Record<string, unknown> = {};
      for (const server of serverList) {
        if (!server.name) continue;
        serversObj[server.name] = {
          transport: server.transport,
          ...(server.transport === 'http' ? { url: server.url } : {}),
          ...(server.transport === 'stdio' ? { command: server.command, args: server.args } : {}),
          ...(Object.keys(server.env || {}).length > 0 ? { env: server.env } : {}),
          enabled: server.enabled,
        };
      }
      await api.updateSetting('mcp', 'servers', serversObj);
      flash('Saved');
    } catch {
      flash('Error saving');
    } finally {
      setSaving(false);
    }
  };

  const startEdit = (index: number) => {
    setEditForm({ ...servers[index] });
    setEditingIndex(index);
  };

  const startAdd = () => {
    setEditForm({ ...DEFAULT_SERVER });
    setEditingIndex(-1); // -1 means adding new
  };

  const cancelEdit = () => {
    setEditingIndex(null);
    setEditForm(DEFAULT_SERVER);
  };

  const saveEdit = async () => {
    if (!editForm.name.trim()) {
      flash('Name is required');
      return;
    }
    if (editForm.transport === 'http' && !editForm.url?.trim()) {
      flash('URL is required for HTTP transport');
      return;
    }
    if (editForm.transport === 'stdio' && !editForm.command?.trim()) {
      flash('Command is required for stdio transport');
      return;
    }

    let newServers: McpServer[];
    if (editingIndex === -1) {
      // Adding new
      newServers = [...servers, { ...editForm, name: editForm.name.trim() }];
    } else {
      // Editing existing
      newServers = servers.map((s, i) => 
        i === editingIndex ? { ...editForm, name: editForm.name.trim() } : s
      );
    }
    
    setServers(newServers);
    await saveServers(newServers);
    cancelEdit();
  };

  const deleteServer = async (index: number) => {
    const newServers = servers.filter((_, i) => i !== index);
    setServers(newServers);
    await saveServers(newServers);
  };

  const toggleServer = async (index: number) => {
    const newServers = servers.map((s, i) => 
      i === index ? { ...s, enabled: !s.enabled } : s
    );
    setServers(newServers);
    await saveServers(newServers);
  };

  return (
    <div>
      {saveMsg && (
        <div className="mb-4 px-4 py-2 bg-success/10 text-success rounded-lg text-sm">
          {saveMsg}
        </div>
      )}
      
      <p className="text-text-dim mb-6">
        Configure MCP (Model Context Protocol) servers to extend the agent with additional tools.
        MCP servers can provide custom tools, data sources, and integrations.
      </p>

      {/* Server list */}
      <div className="flex flex-col gap-3 mb-6">
        {servers.length === 0 && editingIndex === null && (
          <div className="text-center py-8 bg-surface rounded-lg border border-border text-text-dim">
            No MCP servers configured. Add one to extend the agent's capabilities.
          </div>
        )}
        
        {servers.map((server, index) => (
          editingIndex === index ? null : (
            <div 
              key={server.name} 
              className={`p-4 rounded-lg border ${
                !server.enabled ? 'bg-surface/50 border-border opacity-60' : 'bg-surface border-border'
              }`}
            >
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-3">
                  <span className="font-medium text-text">{server.name}</span>
                  <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                    server.transport === 'http' ? 'bg-primary/10 text-primary' : 'bg-warning/10 text-warning'
                  }`}>
                    {server.transport.toUpperCase()}
                  </span>
                  <span className={`text-xs ${server.enabled ? 'text-success' : 'text-text-dim'}`}>
                    {server.enabled ? 'Enabled' : 'Disabled'}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <button 
                    className="px-3 py-1 text-xs text-text-dim hover:text-text hover:bg-surface-hover rounded transition-colors"
                    onClick={() => toggleServer(index)}
                  >
                    {server.enabled ? 'Disable' : 'Enable'}
                  </button>
                  <button 
                    className="px-3 py-1 text-xs text-text-dim hover:text-text hover:bg-surface-hover rounded transition-colors"
                    onClick={() => startEdit(index)}
                  >
                    Edit
                  </button>
                  <button 
                    className="px-3 py-1 text-xs text-error hover:bg-error-bg rounded transition-colors"
                    onClick={() => deleteServer(index)}
                  >
                    Delete
                  </button>
                </div>
              </div>
              <div className="text-sm text-text-dim font-mono truncate">
                {server.transport === 'http' && server.url}
                {server.transport === 'stdio' && `${server.command} ${(server.args || []).join(' ')}`}
              </div>
            </div>
          )
        ))}

        {/* Edit/Add form */}
        {editingIndex !== null && (
          <div className="p-5 bg-bg rounded-lg border border-primary">
            <h4 className="font-semibold text-text mb-4">
              {editingIndex === -1 ? 'Add MCP Server' : 'Edit MCP Server'}
            </h4>
            
            <div className="flex flex-col gap-4 mb-5">
              <div>
                <label className="block text-sm font-medium text-text mb-1.5" htmlFor="mcp-server-name">Server Name</label>
                <input
                  id="mcp-server-name"
                  type="text"
                  className="w-full bg-surface border border-border rounded-lg px-4 py-2.5 text-text placeholder-text-dim focus:border-primary focus:outline-none"
                  placeholder="my-mcp-server"
                  value={editForm.name}
                  onChange={(e) => setEditForm((f) => ({ ...f, name: e.target.value }))}
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-text mb-1.5" htmlFor="mcp-transport">Transport</label>
                <select
                  id="mcp-transport"
                  className="w-full bg-surface border border-border rounded-lg px-4 py-2.5 text-text focus:border-primary focus:outline-none"
                  value={editForm.transport}
                  onChange={(e) => setEditForm((f) => ({ 
                    ...f, 
                    transport: e.target.value as 'http' | 'stdio' 
                  }))}
                >
                  <option value="http">HTTP (SSE)</option>
                  <option value="stdio">Standard I/O (Command)</option>
                </select>
              </div>

              {editForm.transport === 'http' && (
                <div>
<label className="block text-sm font-medium text-text mb-1.5" htmlFor="mcp-server-url">Server URL</label>
                <input
                  id="mcp-server-url"
                  type="text"
                    className="w-full bg-surface border border-border rounded-lg px-4 py-2.5 text-text placeholder-text-dim focus:border-primary focus:outline-none"
                    placeholder="http://localhost:8080/sse"
                    value={editForm.url || ''}
                    onChange={(e) => setEditForm((f) => ({ ...f, url: e.target.value }))}
                  />
                </div>
              )}

              {editForm.transport === 'stdio' && (
                <>
                  <div>
                    <label className="block text-sm font-medium text-text mb-1.5" htmlFor="mcp-command">Command</label>
                    <input
                      id="mcp-command"
                      type="text"
                      className="w-full bg-surface border border-border rounded-lg px-4 py-2.5 text-text placeholder-text-dim focus:border-primary focus:outline-none"
                      placeholder="npx or uvx or path/to/binary"
                      value={editForm.command || ''}
                      onChange={(e) => setEditForm((f) => ({ ...f, command: e.target.value }))}
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-text mb-1.5" htmlFor="mcp-args">Arguments (one per line)</label>
                    <textarea
                      id="mcp-args"
                      className="w-full bg-surface border border-border rounded-lg px-4 py-2.5 text-text placeholder-text-dim focus:border-primary focus:outline-none resize-none"
                      placeholder={"-y\n@modelcontextprotocol/server-filesystem\n/path/to/dir"}
                      value={(editForm.args || []).join('\n')}
                      onChange={(e) => setEditForm((f) => ({ 
                        ...f, 
                        args: e.target.value.split('\n').filter(a => a.trim()) 
                      }))}
                      rows={4}
                    />
                  </div>
                </>
              )}
            </div>

            <div className="flex gap-3">
              <button 
                className="flex-1 py-2.5 bg-surface-hover text-text-dim rounded-lg hover:text-text transition-colors"
                onClick={cancelEdit}
              >
                Cancel
              </button>
              <button 
                className="flex-1 py-2.5 bg-primary text-white rounded-lg font-medium hover:bg-primary-hover transition-colors disabled:opacity-50"
                onClick={saveEdit}
                disabled={saving}
              >
                {saving ? 'Saving...' : 'Save'}
              </button>
            </div>
          </div>
        )}
      </div>

      {editingIndex === null && (
        <button 
          className="w-full py-3 bg-primary text-white rounded-lg font-medium hover:bg-primary-hover transition-colors"
          onClick={startAdd}
        >
          + Add MCP Server
        </button>
      )}

      {/* Help section */}
      <div className="mt-8 p-5 bg-surface rounded-lg border border-border">
        <h4 className="font-semibold text-text mb-3">Popular MCP Servers</h4>
        <ul className="flex flex-col gap-2 text-sm text-text-dim mb-4">
          <li><strong className="text-text">Filesystem</strong>: <code className="bg-bg px-1.5 py-0.5 rounded text-xs">npx -y @modelcontextprotocol/server-filesystem /path</code></li>
          <li><strong className="text-text">GitHub</strong>: <code className="bg-bg px-1.5 py-0.5 rounded text-xs">npx -y @modelcontextprotocol/server-github</code></li>
          <li><strong className="text-text">Brave Search</strong>: <code className="bg-bg px-1.5 py-0.5 rounded text-xs">npx -y @modelcontextprotocol/server-brave-search</code></li>
          <li><strong className="text-text">Postgres</strong>: <code className="bg-bg px-1.5 py-0.5 rounded text-xs">npx -y @modelcontextprotocol/server-postgres postgres://...</code></li>
        </ul>
        <p className="text-sm text-text-dim">
          Learn more at{' '}
          <a 
            href="https://modelcontextprotocol.io/docs" 
            target="_blank" 
            rel="noopener noreferrer"
            className="text-primary hover:underline"
          >
            modelcontextprotocol.io
          </a>
        </p>
      </div>
    </div>
  );
}

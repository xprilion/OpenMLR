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
    <div className="settings-section">
      {saveMsg && <span className="save-flash">{saveMsg}</span>}
      <p className="settings-hint">
        Configure MCP (Model Context Protocol) servers to extend the agent with additional tools.
        MCP servers can provide custom tools, data sources, and integrations.
      </p>

      {/* Server list */}
      <div className="mcp-server-list">
        {servers.length === 0 && editingIndex === null && (
          <p className="mcp-empty">No MCP servers configured. Add one to extend the agent's capabilities.</p>
        )}
        
        {servers.map((server, index) => (
          editingIndex === index ? null : (
            <div key={server.name} className={`mcp-server-card ${!server.enabled ? 'disabled' : ''}`}>
              <div className="mcp-server-header">
                <div className="mcp-server-info">
                  <span className="mcp-server-name">{server.name}</span>
                  <span className={`mcp-server-transport ${server.transport}`}>
                    {server.transport.toUpperCase()}
                  </span>
                  <span className={`mcp-server-status ${server.enabled ? 'enabled' : 'disabled'}`}>
                    {server.enabled ? 'Enabled' : 'Disabled'}
                  </span>
                </div>
                <div className="mcp-server-actions">
                  <button className="mcp-btn-small" onClick={() => toggleServer(index)}>
                    {server.enabled ? 'Disable' : 'Enable'}
                  </button>
                  <button className="mcp-btn-small" onClick={() => startEdit(index)}>
                    Edit
                  </button>
                  <button className="mcp-btn-small danger" onClick={() => deleteServer(index)}>
                    Delete
                  </button>
                </div>
              </div>
              <div className="mcp-server-detail">
                {server.transport === 'http' && server.url && (
                  <span className="mcp-server-url">{server.url}</span>
                )}
                {server.transport === 'stdio' && server.command && (
                  <span className="mcp-server-command">
                    {server.command} {(server.args || []).join(' ')}
                  </span>
                )}
              </div>
            </div>
          )
        ))}

        {/* Edit/Add form */}
        {editingIndex !== null && (
          <div className="mcp-edit-form">
            <h4>{editingIndex === -1 ? 'Add MCP Server' : 'Edit MCP Server'}</h4>
            
            <div className="settings-field">
              <label>Server Name</label>
              <input
                type="text"
                placeholder="my-mcp-server"
                value={editForm.name}
                onChange={(e) => setEditForm((f) => ({ ...f, name: e.target.value }))}
              />
            </div>

            <div className="settings-field">
              <label>Transport</label>
              <select
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
              <div className="settings-field">
                <label>Server URL</label>
                <input
                  type="text"
                  placeholder="http://localhost:8080/sse"
                  value={editForm.url || ''}
                  onChange={(e) => setEditForm((f) => ({ ...f, url: e.target.value }))}
                />
              </div>
            )}

            {editForm.transport === 'stdio' && (
              <>
                <div className="settings-field">
                  <label>Command</label>
                  <input
                    type="text"
                    placeholder="npx or uvx or path/to/binary"
                    value={editForm.command || ''}
                    onChange={(e) => setEditForm((f) => ({ ...f, command: e.target.value }))}
                  />
                </div>
                <div className="settings-field">
                  <label>Arguments (one per line)</label>
                  <textarea
                    placeholder="-y&#10;@modelcontextprotocol/server-filesystem&#10;/path/to/dir"
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

            <div className="mcp-form-actions">
              <button className="mcp-btn cancel" onClick={cancelEdit}>
                Cancel
              </button>
              <button 
                className="mcp-btn save" 
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
        <button className="settings-save-btn" onClick={startAdd}>
          + Add MCP Server
        </button>
      )}

      <div className="mcp-help">
        <h4>Popular MCP Servers</h4>
        <ul>
          <li><strong>Filesystem</strong>: <code>npx -y @modelcontextprotocol/server-filesystem /path</code></li>
          <li><strong>GitHub</strong>: <code>npx -y @modelcontextprotocol/server-github</code></li>
          <li><strong>Brave Search</strong>: <code>npx -y @modelcontextprotocol/server-brave-search</code></li>
          <li><strong>Postgres</strong>: <code>npx -y @modelcontextprotocol/server-postgres postgres://...</code></li>
        </ul>
        <p>
          Learn more at{' '}
          <a href="https://modelcontextprotocol.io/docs" target="_blank" rel="noopener noreferrer">
            modelcontextprotocol.io
          </a>
        </p>
      </div>
    </div>
  );
}

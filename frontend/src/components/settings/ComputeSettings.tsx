import { useState, useEffect, useCallback, useRef } from 'react';
import { api } from '../../api';
import { AddKeyModal } from './AddKeyModal';
import { AddNodeModal } from './AddNodeModal';
import { KeyRound, Server, Trash2, Plus, Star, Edit3, TestTube, Search } from 'lucide-react';

interface SSHKey {
  id: number;
  filename: string;
  fingerprint: string;
  algorithm: string;
  comment: string | null;
  created_at: string;
}

interface ComputeNode {
  id: number;
  name: string;
  type: string;
  config: Record<string, any>;
  capabilities: Record<string, any>;
  health_status: string;
  is_default: boolean;
  priority: number;
  created_at: string;
}

export function ComputeSettings() {
  const [keys, setKeys] = useState<SSHKey[]>([]);
  const [nodes, setNodes] = useState<ComputeNode[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(false);
  const [showAddKey, setShowAddKey] = useState(false);
  const [showAddNode, setShowAddNode] = useState(false);
  const [editingNode, setEditingNode] = useState<ComputeNode | null>(null);
  const [message, setMessage] = useState('');
  const [busyNodeId, setBusyNodeId] = useState<number | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const flash = useCallback((msg: string) => {
    setMessage(msg);
    setTimeout(() => setMessage(''), 3000);
  }, []);

  const loadData = useCallback(async () => {
    try {
      const [keysData, nodesData] = await Promise.all([
        api.getKeys(),
        api.getComputeNodes(),
      ]);
      setKeys(keysData.keys || []);
      setNodes(nodesData.nodes || []);
      setLoadError(false);
    } catch {
      setLoadError(true);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
    // Poll health status every 30 seconds
    pollRef.current = setInterval(() => {
      api.getComputeNodes().then((d) => setNodes(d.nodes || [])).catch(() => {});
    }, 30000);
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, [loadData]);

  const handleDeleteKey = async (filename: string) => {
    if (!confirm(`Delete key "${filename}"?`)) return;
    try {
      await api.deleteKey(filename);
      flash('Key deleted');
      loadData();
    } catch (err: any) {
      flash(err.message || 'Error deleting key');
    }
  };

  const handleDeleteNode = async (id: number, name: string) => {
    if (!confirm(`Delete node "${name}"?`)) return;
    try {
      await api.deleteComputeNode(id);
      flash('Node deleted');
      loadData();
    } catch {
      flash('Error deleting node');
    }
  };

  const handleSetDefault = async (id: number) => {
    try {
      await api.setDefaultComputeNode(id);
      flash('Default compute updated');
      loadData();
    } catch {
      flash('Error setting default');
    }
  };

  const handleTestNode = async (id: number) => {
    setBusyNodeId(id);
    try {
      const result = await api.testComputeNode(id);
      flash(result.ok ? `Connected: ${result.message || 'OK'}` : `Failed: ${result.error || 'Unknown error'}`);
    } catch {
      flash('Test failed');
    } finally {
      setBusyNodeId(null);
    }
  };

  const handleProbeNode = async (id: number) => {
    setBusyNodeId(id);
    flash('Probing node capabilities...');
    try {
      const result = await api.probeComputeNode(id);
      if (result.ok) {
        flash('Probe complete — capabilities updated');
        loadData();
      } else {
        flash(`Probe failed: ${result.error || 'Unknown error'}`);
      }
    } catch {
      flash('Probe failed');
    } finally {
      setBusyNodeId(null);
    }
  };

  const handleAddNode = async (data: any) => {
    try {
      await api.createComputeNode(data);
      setShowAddNode(false);
      setEditingNode(null);
      flash('Node created');
      loadData();
    } catch (err: any) {
      flash(err.message || 'Error creating node');
    }
  };

  const handleUpdateNode = async (id: number, data: any) => {
    try {
      await api.updateComputeNode(id, data);
      setShowAddNode(false);
      setEditingNode(null);
      flash('Node updated');
      loadData();
    } catch (err: any) {
      flash(err.message || 'Error updating node');
    }
  };

  const handleAddKey = async (data: any) => {
    try {
      await api.createKey(data);
      setShowAddKey(false);
      flash('Key added');
      loadData();
    } catch (err: any) {
      flash(err.message || 'Error adding key');
    }
  };

  const getStatusDot = (status: string) => {
    const colors: Record<string, string> = {
      online: 'bg-success',
      offline: 'bg-error',
      degraded: 'bg-warning',
      unknown: 'bg-text-dim',
    };
    return (
      <span
        className={`w-2 h-2 rounded-full ${colors[status] || colors.unknown}`}
        aria-label={`Status: ${status}`}
      />
    );
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    );
  }

  return (
    <div>
      {/* Flash message — rendered at z-[60] so it appears above modals (z-50) */}
      {message && (
        <div className="fixed top-4 left-1/2 -translate-x-1/2 z-[60] px-4 py-2 bg-surface border border-border rounded-lg shadow-xl text-sm text-text">
          {message}
        </div>
      )}

      {loadError && (
        <div className="mb-4 px-4 py-3 bg-error/10 text-error rounded-lg text-sm flex items-center justify-between">
          <span>Failed to load compute settings</span>
          <button onClick={loadData} className="underline hover:no-underline">Retry</button>
        </div>
      )}

      {/* SSH Keys Section */}
      <div className="mb-10">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-text flex items-center gap-2">
            <KeyRound size={18} />
            SSH Keys
          </h2>
          <button
            onClick={() => setShowAddKey(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-primary text-white rounded-lg text-sm hover:bg-primary-hover transition-colors"
          >
            <Plus size={14} />
            Add Key
          </button>
        </div>

        {keys.length === 0 ? (
          <p className="text-text-dim text-sm">No SSH keys configured. Add a key to connect to remote machines.</p>
        ) : (
          <div className="space-y-2">
            {keys.map((key) => (
              <div key={key.id} className="flex items-center justify-between p-3 bg-surface rounded-lg border border-border">
                <div className="min-w-0">
                  <div className="font-medium text-text text-sm">{key.filename}</div>
                  <div className="text-xs text-text-dim mt-0.5">
                    {key.algorithm} · {key.fingerprint}
                  </div>
                </div>
                <button
                  onClick={() => handleDeleteKey(key.filename)}
                  className="p-1.5 text-text-dim hover:text-error transition-colors shrink-0"
                  title="Delete key"
                  aria-label={`Delete key ${key.filename}`}
                >
                  <Trash2 size={14} />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Compute Nodes Section */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-text flex items-center gap-2">
            <Server size={18} />
            Compute Nodes
          </h2>
          <button
            onClick={() => { setEditingNode(null); setShowAddNode(true); }}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-primary text-white rounded-lg text-sm hover:bg-primary-hover transition-colors"
          >
            <Plus size={14} />
            Add Node
          </button>
        </div>

        {nodes.length === 0 ? (
          <p className="text-text-dim text-sm">No compute nodes configured. Add a local workspace or SSH remote to get started.</p>
        ) : (
          <div className="space-y-3">
            {nodes.map((node) => (
              <div key={node.id} className="p-4 bg-surface rounded-lg border border-border">
                <div className="flex items-start justify-between">
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-text">{node.name}</span>
                      {node.is_default && (
                        <span className="flex items-center gap-0.5 text-xs text-warning">
                          <Star size={10} fill="currentColor" />
                          Default
                        </span>
                      )}
                      <span className="flex items-center gap-1 text-xs text-text-dim capitalize">
                        {getStatusDot(node.health_status)}
                        {node.type}
                      </span>
                    </div>
                    {node.type === 'ssh' && (
                      <div className="text-xs text-text-dim mt-1">
                        {node.config.host}:{node.config.port || 22} · {node.config.username}
                      </div>
                    )}
                    {node.type === 'local' && (
                      <div className="text-xs text-text-dim mt-1">
                        {node.config.workdir || 'Per-conversation workspace'}
                      </div>
                    )}
                    {node.capabilities && Object.keys(node.capabilities).length > 0 && (
                      <div className="flex flex-wrap gap-1 mt-2">
                        {node.capabilities.gpu_available && (
                          <span className="px-1.5 py-0.5 bg-success/10 text-success text-xs rounded">GPU</span>
                        )}
                        {node.capabilities.available_ram_gb > 0 && (
                          <span className="px-1.5 py-0.5 bg-primary/10 text-primary text-xs rounded">
                            {Math.round(node.capabilities.available_ram_gb)} GB RAM
                          </span>
                        )}
                        {node.capabilities.cpu_cores > 0 && (
                          <span className="px-1.5 py-0.5 bg-text-dim/10 text-text-dim text-xs rounded">
                            {node.capabilities.cpu_cores} cores
                          </span>
                        )}
                      </div>
                    )}
                  </div>
                  <div className="flex items-center gap-1 shrink-0 ml-3">
                    {!node.is_default && (
                      <button
                        onClick={() => handleSetDefault(node.id)}
                        className="p-1.5 text-text-dim hover:text-warning transition-colors"
                        title="Set as default"
                        aria-label={`Set ${node.name} as default`}
                      >
                        <Star size={14} />
                      </button>
                    )}
                    <button
                      onClick={() => handleTestNode(node.id)}
                      disabled={busyNodeId === node.id}
                      className="p-1.5 text-text-dim hover:text-success transition-colors disabled:opacity-50"
                      title="Test connection"
                      aria-label={`Test connection to ${node.name}`}
                    >
                      <TestTube size={14} />
                    </button>
                    <button
                      onClick={() => handleProbeNode(node.id)}
                      disabled={busyNodeId === node.id}
                      className="p-1.5 text-text-dim hover:text-primary transition-colors disabled:opacity-50"
                      title="Probe capabilities"
                      aria-label={`Probe capabilities of ${node.name}`}
                    >
                      <Search size={14} />
                    </button>
                    <button
                      onClick={() => { setEditingNode(node); setShowAddNode(true); }}
                      className="p-1.5 text-text-dim hover:text-primary transition-colors"
                      title="Edit node"
                      aria-label={`Edit ${node.name}`}
                    >
                      <Edit3 size={14} />
                    </button>
                    <button
                      onClick={() => handleDeleteNode(node.id, node.name)}
                      className="p-1.5 text-text-dim hover:text-error transition-colors"
                      title="Delete node"
                      aria-label={`Delete ${node.name}`}
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Modals */}
      {showAddKey && (
        <AddKeyModal
          onClose={() => setShowAddKey(false)}
          onSubmit={handleAddKey}
        />
      )}
      {showAddNode && (
        <AddNodeModal
          keys={keys}
          node={editingNode}
          onClose={() => { setShowAddNode(false); setEditingNode(null); }}
          onSubmit={editingNode ? (data) => handleUpdateNode(editingNode.id, data) : handleAddNode}
        />
      )}
    </div>
  );
}

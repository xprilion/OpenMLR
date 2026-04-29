

import { useState, useEffect } from 'react';
import { X, Server, Monitor, Cloud, TestTube } from 'lucide-react';
import { api } from '../../api';

interface SSHKey {
  id: number;
  filename: string;
  fingerprint: string;
  algorithm: string;
}

interface ComputeNode {
  id: number;
  name: string;
  type: string;
  config: Record<string, any>;
  is_default: boolean;
  priority: number;
}

interface AddNodeModalProps {
  keys: SSHKey[];
  node: ComputeNode | null;
  onClose: () => void;
  onSubmit: (data: any) => void;
}

export function AddNodeModal({ keys, node, onClose, onSubmit }: AddNodeModalProps) {
  const isEditing = !!node;

  useEffect(() => {
    const handleEsc = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    document.addEventListener('keydown', handleEsc);
    return () => document.removeEventListener('keydown', handleEsc);
  }, [onClose]);
  const [type, setType] = useState<'ssh' | 'local' | 'modal'>('ssh');
  const [name, setName] = useState('');
  const [isDefault, setIsDefault] = useState(false);
  const [priority, setPriority] = useState(0);

  // SSH fields
  const [host, setHost] = useState('');
  const [port, setPort] = useState(22);
  const [username, setUsername] = useState('');
  const [keyFilename, setKeyFilename] = useState('');
  const [workdir, setWorkdir] = useState('~');

  // Local fields
  const [localWorkdir, setLocalWorkdir] = useState('');

  // Modal fields
  const [modalImage, setModalImage] = useState('python:3.12');
  const [modalGpu, setModalGpu] = useState('');
  const [modalPackages, setModalPackages] = useState('');

  const [submitting, setSubmitting] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<{ ok: boolean; message?: string; error?: string; host_key_fingerprint?: string } | null>(null);

  useEffect(() => {
    if (node) {
      setType(node.type as any);
      setName(node.name);
      setIsDefault(node.is_default);
      setPriority(node.priority);
      const c = node.config;
      if (node.type === 'ssh') {
        setHost(c.host || '');
        setPort(c.port || 22);
        setUsername(c.username || '');
        setKeyFilename(c.key_filename || '');
        setWorkdir(c.workdir || '~');
      } else if (node.type === 'local') {
        setLocalWorkdir(c.workdir || '');
      } else if (node.type === 'modal') {
        setModalImage(c.image || 'python:3.12');
        setModalGpu(c.gpu || '');
        setModalPackages((c.packages || []).join(', '));
      }
    }
  }, [node]);

  const buildConfig = (): Record<string, any> => {
    if (type === 'ssh') {
      return {
        host: host.trim(),
        port: port || 22,
        username: username.trim(),
        key_filename: keyFilename || undefined,
        workdir: workdir.trim() || '~',
      };
    } else if (type === 'local') {
      return { workdir: localWorkdir.trim() || undefined };
    } else if (type === 'modal') {
      return {
        image: modalImage.trim(),
        gpu: modalGpu.trim() || undefined,
        packages: modalPackages.split(',').map((p) => p.trim()).filter(Boolean),
      };
    }
    return {};
  };

  const handleTest = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      const result = await api.testComputeConfig(type, buildConfig());
      setTestResult(result);
    } catch {
      setTestResult({ ok: false, error: 'Connection test failed' });
    } finally {
      setTesting(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;

    setSubmitting(true);
    try {
      await onSubmit({
        name: name.trim(),
        type,
        config: buildConfig(),
        is_default: isDefault,
        priority,
      });
    } finally {
      setSubmitting(false);
    }
  };

  const typeOptions = [
    { value: 'ssh' as const, label: 'SSH Remote', icon: Server },
    { value: 'local' as const, label: 'Local Workspace', icon: Monitor },
    { value: 'modal' as const, label: 'Modal Cloud', icon: Cloud },
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={onClose} role="dialog" aria-modal="true" aria-labelledby="add-node-title">
      <div className="bg-surface rounded-xl border border-border w-full max-w-lg mx-4 shadow-xl max-h-[90vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between px-5 py-4 border-b border-border">
          <h3 id="add-node-title" className="font-semibold text-text">
            {isEditing ? 'Edit Compute Node' : 'Add Compute Node'}
          </h3>
          <button onClick={onClose} className="text-text-dim hover:text-text transition-colors">
            <X size={18} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-5 space-y-4">
          {/* Type selector (only when creating) */}
          {!isEditing && (
            <div className="flex gap-1 p-1 bg-bg rounded-lg">
              {typeOptions.map((opt) => {
                const Icon = opt.icon;
                return (
                  <button
                    key={opt.value}
                    type="button"
                    onClick={() => setType(opt.value)}
                    className={`flex-1 py-1.5 text-sm rounded-md transition-colors flex items-center justify-center gap-1.5 ${
                      type === opt.value ? 'bg-surface text-text shadow-sm' : 'text-text-dim hover:text-text'
                    }`}
                  >
                    <Icon size={14} />
                    {opt.label}
                  </button>
                );
              })}
            </div>
          )}

          {/* Name */}
          <div>
            <label className="block text-sm font-medium text-text mb-1.5">Name</label>
            <input
              type="text"
              required
              placeholder="Workstation"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full bg-bg border border-border rounded-lg px-3 py-2 text-text text-sm focus:border-primary focus:outline-none"
            />
          </div>

          {/* SSH-specific fields */}
          {type === 'ssh' && (
            <>
              <div className="grid grid-cols-3 gap-3">
                <div className="col-span-2">
                  <label className="block text-sm font-medium text-text mb-1.5">Host</label>
                  <input
                    type="text"
                    required
                    placeholder="ml-workstation.local"
                    value={host}
                    onChange={(e) => setHost(e.target.value)}
                    className="w-full bg-bg border border-border rounded-lg px-3 py-2 text-text text-sm focus:border-primary focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-text mb-1.5">Port</label>
                  <input
                    type="number"
                    value={port}
                    onChange={(e) => setPort(parseInt(e.target.value) || 22)}
                    className="w-full bg-bg border border-border rounded-lg px-3 py-2 text-text text-sm focus:border-primary focus:outline-none"
                  />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-text mb-1.5">Username</label>
                <input
                  type="text"
                  required
                  placeholder="researcher"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  className="w-full bg-bg border border-border rounded-lg px-3 py-2 text-text text-sm focus:border-primary focus:outline-none"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-text mb-1.5">SSH Key</label>
                <select
                  value={keyFilename}
                  onChange={(e) => setKeyFilename(e.target.value)}
                  className="w-full bg-bg border border-border rounded-lg px-3 py-2 text-text text-sm focus:border-primary focus:outline-none"
                >
                  <option value="">Select a key...</option>
                  {keys.map((k) => (
                    <option key={k.id} value={k.filename}>
                      {k.filename} ({k.fingerprint})
                    </option>
                  ))}
                </select>
                {keys.length === 0 && (
                  <p className="text-xs text-warning mt-1">
                    No keys available. Add an SSH key in the Keys section first.
                  </p>
                )}
              </div>
              <div>
                <label className="block text-sm font-medium text-text mb-1.5">Working Directory</label>
                <input
                  type="text"
                  placeholder="~/openmlr-workspaces"
                  value={workdir}
                  onChange={(e) => setWorkdir(e.target.value)}
                  className="w-full bg-bg border border-border rounded-lg px-3 py-2 text-text text-sm focus:border-primary focus:outline-none"
                />
              </div>
            </>
          )}

          {/* Local-specific fields */}
          {type === 'local' && (
            <div>
              <label className="block text-sm font-medium text-text mb-1.5">Working Directory</label>
              <input
                type="text"
                placeholder="Leave blank for current directory"
                value={localWorkdir}
                onChange={(e) => setLocalWorkdir(e.target.value)}
                className="w-full bg-bg border border-border rounded-lg px-3 py-2 text-text text-sm focus:border-primary focus:outline-none"
              />
              <p className="text-xs text-text-dim mt-1">
                Defaults to per-conversation workspace at ~/.openmlr/workspace-{'{uuid}'}
              </p>
            </div>
          )}

          {/* Modal-specific fields */}
          {type === 'modal' && (
            <>
              <div>
                <label className="block text-sm font-medium text-text mb-1.5">Container Image</label>
                <input
                  type="text"
                  value={modalImage}
                  onChange={(e) => setModalImage(e.target.value)}
                  className="w-full bg-bg border border-border rounded-lg px-3 py-2 text-text text-sm focus:border-primary focus:outline-none"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-text mb-1.5">GPU (optional)</label>
                <select
                  value={modalGpu}
                  onChange={(e) => setModalGpu(e.target.value)}
                  className="w-full bg-bg border border-border rounded-lg px-3 py-2 text-text text-sm focus:border-primary focus:outline-none"
                >
                  <option value="">No GPU</option>
                  <option value="T4">T4</option>
                  <option value="A10G">A10G</option>
                  <option value="A100">A100</option>
                  <option value="H100">H100</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-text mb-1.5">Packages (comma-separated)</label>
                <input
                  type="text"
                  placeholder="torch, transformers, datasets"
                  value={modalPackages}
                  onChange={(e) => setModalPackages(e.target.value)}
                  className="w-full bg-bg border border-border rounded-lg px-3 py-2 text-text text-sm focus:border-primary focus:outline-none"
                />
              </div>
            </>
          )}

          {/* Default & Priority */}
          <div className="flex items-center gap-4 pt-2">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={isDefault}
                onChange={(e) => setIsDefault(e.target.checked)}
                className="w-4 h-4 rounded border-border text-primary focus:ring-primary"
              />
              <span className="text-sm text-text">Set as default compute</span>
            </label>
          </div>

          {/* Test connection (pre-save) */}
          {type === 'ssh' && (
            <div className="pt-2">
              <button
                type="button"
                onClick={handleTest}
                disabled={testing || !host.trim() || !username.trim()}
                className="flex items-center gap-1.5 px-3 py-1.5 border border-border rounded-lg text-sm text-text-dim hover:text-text hover:border-text-dim transition-colors disabled:opacity-50"
              >
                <TestTube size={14} />
                {testing ? 'Testing...' : 'Test Connection'}
              </button>
              {testResult && (
                <div className={`mt-2 px-3 py-2 rounded-lg text-xs ${testResult.ok ? 'bg-success/10 text-success' : 'bg-error/10 text-error'}`}>
                  {testResult.ok ? testResult.message || 'Connected' : testResult.error || 'Failed'}
                  {testResult.host_key_fingerprint && (
                    <div className="mt-1 text-text-dim font-mono">
                      Host key: {testResult.host_key_fingerprint}
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm text-text-dim hover:text-text transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting || !name.trim()}
              className="px-4 py-2 bg-primary text-white rounded-lg text-sm font-medium hover:bg-primary-hover transition-colors disabled:opacity-50"
            >
              {submitting ? 'Saving...' : isEditing ? 'Update Node' : 'Add Node'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

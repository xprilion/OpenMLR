

import { useState, useEffect } from 'react';
import { X, Upload, KeyRound } from 'lucide-react';

interface AddKeyModalProps {
  onClose: () => void;
  onSubmit: (data: any) => void;
}

export function AddKeyModal({ onClose, onSubmit }: AddKeyModalProps) {
  useEffect(() => {
    const handleEsc = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    document.addEventListener('keydown', handleEsc);
    return () => document.removeEventListener('keydown', handleEsc);
  }, [onClose]);
  const [mode, setMode] = useState<'upload' | 'generate'>('upload');
  const [filename, setFilename] = useState('');
  const [privateKey, setPrivateKey] = useState('');
  const [algorithm, setAlgorithm] = useState('ed25519');
  const [comment, setComment] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!filename.trim()) return;

    setSubmitting(true);
    try {
      if (mode === 'upload') {
        await onSubmit({
          action: 'upload',
          filename: filename.trim(),
          private_key: privateKey,
          comment: comment || undefined,
        });
      } else {
        await onSubmit({
          action: 'generate',
          filename: filename.trim(),
          algorithm,
          comment: comment || `openmlr-key`,
        });
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={onClose} role="dialog" aria-modal="true" aria-labelledby="add-key-title">
      <div className="bg-surface rounded-xl border border-border w-full max-w-lg mx-4 shadow-xl" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between px-5 py-4 border-b border-border">
          <h3 id="add-key-title" className="font-semibold text-text flex items-center gap-2">
            <KeyRound size={16} />
            Add SSH Key
          </h3>
          <button onClick={onClose} className="text-text-dim hover:text-text transition-colors">
            <X size={18} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-5 space-y-4">
          {/* Mode toggle */}
          <div className="flex gap-1 p-1 bg-bg rounded-lg">
            <button
              type="button"
              onClick={() => setMode('upload')}
              className={`flex-1 py-1.5 text-sm rounded-md transition-colors ${
                mode === 'upload' ? 'bg-surface text-text shadow-sm' : 'text-text-dim hover:text-text'
              }`}
            >
              <Upload size={14} className="inline mr-1" />
              Upload
            </button>
            <button
              type="button"
              onClick={() => setMode('generate')}
              className={`flex-1 py-1.5 text-sm rounded-md transition-colors ${
                mode === 'generate' ? 'bg-surface text-text shadow-sm' : 'text-text-dim hover:text-text'
              }`}
            >
              <KeyRound size={14} className="inline mr-1" />
              Generate
            </button>
          </div>

          {/* Filename */}
          <div>
            <label className="block text-sm font-medium text-text mb-1.5">Filename</label>
            <input
              type="text"
              required
              placeholder="id_ed25519_workstation"
              value={filename}
              onChange={(e) => setFilename(e.target.value)}
              className="w-full bg-bg border border-border rounded-lg px-3 py-2 text-text text-sm focus:border-primary focus:outline-none"
            />
            <p className="text-xs text-text-dim mt-1">Stored in .keys/ directory</p>
          </div>

          {mode === 'upload' ? (
            <div>
              <label className="block text-sm font-medium text-text mb-1.5">Private Key</label>
              <textarea
                required
                rows={6}
                placeholder="-----BEGIN OPENSSH PRIVATE KEY-----..."
                value={privateKey}
                onChange={(e) => setPrivateKey(e.target.value)}
                className="w-full bg-bg border border-border rounded-lg px-3 py-2 text-text text-sm focus:border-primary focus:outline-none font-mono"
              />
            </div>
          ) : (
            <div>
              <label className="block text-sm font-medium text-text mb-1.5">Algorithm</label>
              <select
                value={algorithm}
                onChange={(e) => setAlgorithm(e.target.value)}
                className="w-full bg-bg border border-border rounded-lg px-3 py-2 text-text text-sm focus:border-primary focus:outline-none"
              >
                <option value="ed25519">ED25519 (recommended)</option>
                <option value="rsa">RSA 4096</option>
              </select>
            </div>
          )}

          {/* Comment */}
          <div>
            <label className="block text-sm font-medium text-text mb-1.5">Comment (optional)</label>
            <input
              type="text"
              placeholder="Workstation key"
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              className="w-full bg-bg border border-border rounded-lg px-3 py-2 text-text text-sm focus:border-primary focus:outline-none"
            />
          </div>

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
              disabled={submitting || !filename.trim() || (mode === 'upload' && !privateKey.trim())}
              className="px-4 py-2 bg-primary text-white rounded-lg text-sm font-medium hover:bg-primary-hover transition-colors disabled:opacity-50"
            >
              {submitting ? 'Saving...' : mode === 'upload' ? 'Upload Key' : 'Generate Key'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

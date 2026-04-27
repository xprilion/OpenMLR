import { useState } from 'react';
import { X, FolderPlus } from 'lucide-react';
import { api } from '../api';
import type { Project } from '../types';

interface Props {
  onClose: () => void;
  onCreate: (project: Project) => void;
}

export function ProjectModal({ onClose, onCreate }: Props) {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleCreate = async () => {
    if (!name.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const data = await api.createProject(name.trim(), description.trim() || undefined);
      onCreate(data.project);
      onClose();
    } catch (err: any) {
      setError(err.message || 'Failed to create project');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="bg-surface border border-border rounded-xl shadow-xl w-full max-w-md mx-4">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-border">
          <div className="flex items-center gap-2">
            <FolderPlus size={18} className="text-primary" />
            <h2 className="text-lg font-semibold text-text">New Project</h2>
          </div>
          <button
            className="w-8 h-8 rounded-lg flex items-center justify-center text-text-dim hover:bg-surface-hover hover:text-text transition-colors"
            onClick={onClose}
          >
            <X size={16} />
          </button>
        </div>

        {/* Form */}
        <div className="px-6 py-5 space-y-4">
          <div>
            <label className="block text-sm font-medium text-text mb-1.5">Project Name</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g., Attention Mechanism Survey"
              className="w-full px-3 py-2 bg-bg border border-border rounded-lg text-text placeholder-text-dim focus:border-primary focus:outline-none transition-colors"
              autoFocus
              onKeyDown={(e) => e.key === 'Enter' && handleCreate()}
            />
            <p className="text-xs text-text-dim mt-1">
              A workspace directory will be created for this project
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-text mb-1.5">
              Description <span className="text-text-dim font-normal">(optional)</span>
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Brief description of the research goal..."
              rows={3}
              className="w-full px-3 py-2 bg-bg border border-border rounded-lg text-text placeholder-text-dim focus:border-primary focus:outline-none transition-colors resize-none"
            />
          </div>

          {error && (
            <div className="text-sm text-error bg-error/10 px-3 py-2 rounded-lg">{error}</div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-border">
          <button
            className="px-4 py-2 text-sm text-text-dim hover:text-text transition-colors"
            onClick={onClose}
          >
            Cancel
          </button>
          <button
            className="px-4 py-2 text-sm font-medium bg-primary text-white rounded-lg hover:bg-primary/90 transition-colors disabled:opacity-50"
            onClick={handleCreate}
            disabled={!name.trim() || loading}
          >
            {loading ? 'Creating...' : 'Create Project'}
          </button>
        </div>
      </div>
    </div>
  );
}

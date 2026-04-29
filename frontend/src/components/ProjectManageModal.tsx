

import { useState, useRef, useEffect } from 'react';
import { X, FolderOpen, Pencil, Trash2, Check, Layers } from 'lucide-react';
import { api } from '../api';
import type { Project } from '../types';
import { ConfirmDialog } from './ConfirmDialog';

interface Props {
  projects: Project[];
  onClose: () => void;
  onChanged: () => void;
}

function ProjectRow({ project, onChanged }: { project: Project; onChanged: () => void }) {
  const [renaming, setRenaming] = useState(false);
  const [name, setName] = useState(project.name);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [saving, setSaving] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const isDefault = project.is_default;

  useEffect(() => {
    if (renaming) {
      inputRef.current?.focus();
      inputRef.current?.select();
    }
  }, [renaming]);

  const handleRename = async () => {
    const trimmed = name.trim();
    if (!trimmed || trimmed === project.name) {
      setRenaming(false);
      setName(project.name);
      return;
    }
    setSaving(true);
    try {
      await api.updateProject(project.uuid, { name: trimmed });
      onChanged();
    } catch {
      setName(project.name);
    } finally {
      setSaving(false);
      setRenaming(false);
    }
  };

  const handleDelete = async () => {
    try {
      await api.deleteProject(project.uuid);
      onChanged();
    } catch {
      // ignore
    }
    setConfirmDelete(false);
  };

  return (
    <>
      <div className="flex items-center gap-3 p-3 bg-bg rounded-lg border border-border group">
        <FolderOpen size={16} className={`shrink-0 ${isDefault ? 'text-primary' : 'text-text-dim'}`} />

        {/* Name / inline rename */}
        <div className="flex-1 min-w-0">
          {renaming ? (
            <div className="flex items-center gap-1.5">
              <input
                ref={inputRef}
                className="flex-1 bg-surface border border-primary rounded px-2 py-1 text-sm text-text focus:outline-none min-w-0"
                value={name}
                onChange={(e) => setName(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') handleRename();
                  if (e.key === 'Escape') { setRenaming(false); setName(project.name); }
                }}
                disabled={saving}
              />
              <button
                className="p-1 rounded text-success hover:bg-success/10 transition-colors"
                onClick={handleRename}
                disabled={saving}
              >
                <Check size={14} />
              </button>
              <button
                className="p-1 rounded text-text-dim hover:bg-surface-hover transition-colors"
                onClick={() => { setRenaming(false); setName(project.name); }}
              >
                <X size={14} />
              </button>
            </div>
          ) : (
            <div>
              <span className="text-sm font-medium text-text block truncate">{project.name}</span>
              {project.description && (
                <span className="text-xs text-text-dim block truncate">{project.description}</span>
              )}
              <span className="text-xs text-text-dim">
                {project.conversation_count ?? 0} conversation{(project.conversation_count ?? 0) !== 1 ? 's' : ''}
              </span>
            </div>
          )}
        </div>

        {/* Actions (not for default project, not during rename) */}
        {!isDefault && !renaming && (
          <div className="flex items-center gap-1 shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">
            <button
              className="p-1.5 rounded text-text-dim hover:text-text hover:bg-surface-hover transition-colors"
              onClick={() => setRenaming(true)}
              title="Rename"
            >
              <Pencil size={14} />
            </button>
            <button
              className="p-1.5 rounded text-text-dim hover:text-error hover:bg-error/10 transition-colors"
              onClick={() => setConfirmDelete(true)}
              title="Delete"
            >
              <Trash2 size={14} />
            </button>
          </div>
        )}

        {/* Default badge */}
        {isDefault && (
          <span className="text-[10px] px-2 py-0.5 rounded-full bg-primary/10 text-primary shrink-0">Default</span>
        )}
      </div>

      {confirmDelete && (
        <ConfirmDialog
          title="Delete Project"
          message={`Delete "${project.name}" and its workspace? All files in the workspace will be permanently removed. This cannot be undone.`}
          confirmLabel="Delete Project"
          cancelLabel="Cancel"
          danger
          onConfirm={handleDelete}
          onCancel={() => setConfirmDelete(false)}
        />
      )}
    </>
  );
}

export function ProjectManageModal({ projects, onClose, onChanged }: Props) {
  const dialogRef = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const dialog = dialogRef.current;
    if (dialog && !dialog.open) {
      dialog.showModal();
    }

    const handleCancel = (e: Event) => {
      e.preventDefault();
      onClose();
    };

    dialog?.addEventListener('cancel', handleCancel);
    return () => dialog?.removeEventListener('cancel', handleCancel);
  }, [onClose]);

  // Sort: default first, then alphabetical
  const sorted = [...projects].sort((a, b) => {
    if (a.is_default && !b.is_default) return -1;
    if (!a.is_default && b.is_default) return 1;
    return a.name.localeCompare(b.name);
  });

  const handleBackdropClick = (e: React.MouseEvent<HTMLDialogElement>) => {
    if (e.target === dialogRef.current) {
      onClose();
    }
  };

  return (
    <dialog
      ref={dialogRef}
      className="fixed bg-transparent p-4 m-0 max-w-none max-h-none w-full h-full backdrop:bg-black/60 backdrop:backdrop-blur-sm"
      onClick={handleBackdropClick}
      aria-labelledby="project-manage-title"
    >
      <div className="flex items-center justify-center min-h-full">
        <div
          className="bg-surface border border-border rounded-xl shadow-xl w-full max-w-lg max-h-[70vh] flex flex-col"
          onClick={(e) => e.stopPropagation()}
        >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-border shrink-0">
          <div className="flex items-center gap-2">
            <Layers size={18} className="text-primary" />
            <h2 id="project-manage-title" className="text-lg font-semibold text-text">Manage Projects</h2>
          </div>
          <button
            className="w-8 h-8 rounded-lg flex items-center justify-center text-text-dim hover:bg-surface-hover hover:text-text transition-colors"
            onClick={onClose}
          >
            <X size={16} />
          </button>
        </div>

        {/* Project list */}
        <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-2 min-h-0">
          {sorted.length === 0 ? (
            <p className="text-center text-text-dim py-8">No projects yet.</p>
          ) : (
            sorted.map((p) => (
              <ProjectRow key={p.uuid} project={p} onChanged={onChanged} />
            ))
          )}
        </div>

        {/* Footer hint */}
        <div className="px-6 py-3 border-t border-border text-xs text-text-dim text-center shrink-0">
          Hover a project to rename or delete. The default project cannot be modified.
        </div>
        </div>
      </div>
    </dialog>
  );
}

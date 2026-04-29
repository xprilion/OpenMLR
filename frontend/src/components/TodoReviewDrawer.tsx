import { useState } from 'react';
import { Check, X, Plus, Trash2, GripVertical } from 'lucide-react';
import { api } from '../api';

interface TodoApprovalPayload {
  change_type: 'create' | 'add';
  proposed_tasks: Array<{ title: string; status: string; priority?: string }>;
  current_tasks: Array<{ title: string; status: string; priority?: string }>;
}

interface Props {
  readonly payload: TodoApprovalPayload;
  readonly onDone: () => void;
  readonly onClose: () => void;
}

const statusIcon = (status: string) => {
  switch (status) {
    case 'completed': return '[x]';
    case 'in_progress': return '[~]';
    case 'cancelled': return '[-]';
    default: return '[ ]';
  }
};

const statusColor = (status: string) => {
  switch (status) {
    case 'completed': return 'text-success';
    case 'in_progress': return 'text-primary';
    case 'cancelled': return 'text-text-dim line-through';
    default: return 'text-text';
  }
};

export function TodoReviewDrawer({ payload, onDone, onClose }: Props) {
  const { change_type, proposed_tasks, current_tasks } = payload;
  const [editableTasks, setEditableTasks] = useState(
    proposed_tasks.map((t) => ({ ...t }))
  );
  const [submitting, setSubmitting] = useState(false);
  const [editingIdx, setEditingIdx] = useState<number | null>(null);
  const [editText, setEditText] = useState('');
  const [newTaskText, setNewTaskText] = useState('');

  // Determine which tasks are new (not in current_tasks)
  const currentTitles = new Set(current_tasks.map((t) => t.title));
  const isNewTask = (title: string) => !currentTitles.has(title);

  const handleRemoveTask = (idx: number) => {
    setEditableTasks((prev) => prev.filter((_, i) => i !== idx));
  };

  const handleEditStart = (idx: number) => {
    setEditingIdx(idx);
    setEditText(editableTasks[idx].title);
  };

  const handleEditSave = () => {
    if (editingIdx !== null && editText.trim()) {
      setEditableTasks((prev) =>
        prev.map((t, i) => (i === editingIdx ? { ...t, title: editText.trim() } : t))
      );
    }
    setEditingIdx(null);
    setEditText('');
  };

  const handleAddTask = () => {
    if (newTaskText.trim()) {
      setEditableTasks((prev) => [...prev, { title: newTaskText.trim(), status: 'pending' }]);
      setNewTaskText('');
    }
  };

  const handleApprove = async () => {
    setSubmitting(true);
    try {
      await api.submitTodoApproval(true, editableTasks);
      onDone();
    } catch { /* */ }
    finally { setSubmitting(false); }
  };

  const handleReject = async () => {
    setSubmitting(true);
    try {
      await api.submitTodoApproval(false);
      onDone();
    } catch { /* */ }
    finally { setSubmitting(false); }
  };

  const title = change_type === 'create'
    ? 'Review Proposed Plan'
    : 'Review Task Addition';

  return (
    <div className="absolute inset-x-0 bottom-0 bg-surface border-t border-border shadow-xl animate-slide-up z-30">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-border">
        <div className="font-semibold text-text">{title}</div>
        <div className="flex items-center gap-2">
          <span className="text-sm text-text-dim">
            {editableTasks.length} task{editableTasks.length !== 1 ? 's' : ''}
          </span>
          <button
            className="w-8 h-8 rounded-lg flex items-center justify-center text-text-dim hover:bg-surface-hover hover:text-text transition-colors"
            onClick={onClose}
          >
            <X size={18} />
          </button>
        </div>
      </div>

      {/* Body — two-column diff view */}
      <div className="flex gap-4 px-6 py-5 max-h-80 overflow-y-auto">
        {/* Current tasks (left side) */}
        {current_tasks.length > 0 && (
          <div className="flex-1 min-w-0">
            <div className="text-xs font-medium text-text-dim uppercase tracking-wide mb-3">
              Current Plan
            </div>
            <div className="flex flex-col gap-1.5">
              {current_tasks.map((task, i) => (
                <div
                  key={i}
                  className="flex items-center gap-2 px-3 py-2 rounded-lg bg-bg border border-border text-sm"
                >
                  <span className="font-mono text-xs text-text-dim shrink-0">
                    {statusIcon(task.status)}
                  </span>
                  <span className={statusColor(task.status)}>{task.title}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Proposed tasks (right side, editable) */}
        <div className="flex-1 min-w-0">
          <div className="text-xs font-medium text-text-dim uppercase tracking-wide mb-3">
            {current_tasks.length > 0 ? 'Proposed Changes' : 'Proposed Plan'}
          </div>
          <div className="flex flex-col gap-1.5">
            {editableTasks.map((task, i) => {
              const isNew = isNewTask(task.title);
              return (
                <div
                  key={i}
                  className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm border transition-colors ${
                    isNew
                      ? 'bg-success/5 border-success/30'
                      : 'bg-bg border-border'
                  }`}
                >
                  <GripVertical size={14} className="text-text-dim shrink-0 opacity-30" />
                  <span className="font-mono text-xs text-text-dim shrink-0">
                    {statusIcon(task.status)}
                  </span>
                  {editingIdx === i ? (
                    <input
                      type="text"
                      className="flex-1 bg-bg border border-primary rounded px-2 py-1 text-sm text-text focus:outline-none"
                      value={editText}
                      onChange={(e) => setEditText(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') handleEditSave();
                        if (e.key === 'Escape') { setEditingIdx(null); setEditText(''); }
                      }}
                      onBlur={handleEditSave}
                      autoFocus
                    />
                  ) : (
                    <button
                      className={`flex-1 cursor-pointer hover:text-primary transition-colors text-left ${
                        isNew ? 'text-success font-medium' : statusColor(task.status)
                      }`}
                      onClick={() => handleEditStart(i)}
                      onKeyDown={(e) => e.key === 'Enter' && handleEditStart(i)}
                      title="Click to edit"
                    >
                      {task.title}
                      {isNew && (
                        <span className="ml-2 text-xs bg-success/20 text-success px-1.5 py-0.5 rounded">
                          new
                        </span>
                      )}
                    </button>
                  )}
                  <button
                    className="w-6 h-6 rounded flex items-center justify-center text-text-dim hover:text-error hover:bg-error/10 transition-colors shrink-0"
                    onClick={() => handleRemoveTask(i)}
                    title="Remove task"
                  >
                    <Trash2 size={13} />
                  </button>
                </div>
              );
            })}

            {/* Add task input */}
            <div className="flex items-center gap-2 mt-1">
              <input
                type="text"
                className="flex-1 bg-bg border border-border rounded-lg px-3 py-2 text-sm text-text placeholder-text-dim focus:border-primary focus:outline-none transition-colors"
                placeholder="Add a task..."
                value={newTaskText}
                onChange={(e) => setNewTaskText(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') handleAddTask();
                }}
              />
              <button
                className="w-8 h-8 rounded-lg flex items-center justify-center text-text-dim hover:bg-surface-hover hover:text-primary transition-colors disabled:opacity-30"
                onClick={handleAddTask}
                disabled={!newTaskText.trim()}
              >
                <Plus size={16} />
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Footer */}
      <div className="flex items-center justify-between px-6 py-4 border-t border-border bg-bg">
        <div className="text-sm text-text-dim">
          You can edit tasks before approving. Click a task title to rename it.
        </div>
        <div className="flex items-center gap-3">
          <button
            className="flex items-center gap-2 px-5 py-2.5 bg-error text-white rounded-lg font-medium hover:opacity-90 transition-all disabled:opacity-50"
            onClick={handleReject}
            disabled={submitting}
          >
            <X size={16} />
            {submitting ? 'Rejecting...' : 'Reject'}
          </button>
          <button
            className="flex items-center gap-2 px-5 py-2.5 bg-success text-white rounded-lg font-medium hover:opacity-90 transition-all disabled:opacity-50"
            onClick={handleApprove}
            disabled={submitting || editableTasks.length === 0}
          >
            <Check size={16} />
            {submitting ? 'Approving...' : `Approve${editableTasks.length !== proposed_tasks.length ? ' (modified)' : ''}`}
          </button>
        </div>
      </div>
    </div>
  );
}

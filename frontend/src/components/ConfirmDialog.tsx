import { useEffect, useRef } from 'react';

interface Props {
  title: string;
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
  onConfirm: () => void;
  onCancel: () => void;
  danger?: boolean;
}

export function ConfirmDialog({
  title,
  message,
  confirmLabel = 'Confirm',
  cancelLabel = 'Cancel',
  onConfirm,
  onCancel,
  danger = false,
}: Props) {
  const cancelRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    // Focus cancel button by default for safety
    cancelRef.current?.focus();

    // Handle escape key
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onCancel();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onCancel]);

  return (
    <div 
      className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4"
      onClick={onCancel}
    >
      <div 
        className="bg-surface rounded-xl border border-border p-6 max-w-md w-full shadow-xl animate-slide-up"
        onClick={(e) => e.stopPropagation()}
      >
        <h3 className="text-lg font-semibold text-text mb-3">{title}</h3>
        <p className="text-text-dim mb-6 leading-relaxed">{message}</p>
        
        <div className="flex gap-3">
          <button
            ref={cancelRef}
            className="flex-1 py-2.5 px-4 rounded-lg border border-border text-text-dim hover:bg-surface-hover hover:text-text transition-colors"
            onClick={onCancel}
          >
            {cancelLabel}
          </button>
          <button
            className={`flex-1 py-2.5 px-4 rounded-lg font-medium text-white transition-colors ${
              danger 
                ? 'bg-error hover:opacity-90' 
                : 'bg-primary hover:bg-primary-hover'
            }`}
            onClick={onConfirm}
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}

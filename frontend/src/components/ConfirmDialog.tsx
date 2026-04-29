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
  const dialogRef = useRef<HTMLDialogElement>(null);
  const cancelRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    const dialog = dialogRef.current;
    if (dialog && !dialog.open) {
      dialog.showModal();
    }

    // Focus cancel button by default for safety
    cancelRef.current?.focus();

    // Handle escape key via dialog's native cancel event
    const handleCancel = (e: Event) => {
      e.preventDefault();
      onCancel();
    };

    dialog?.addEventListener('cancel', handleCancel);
    return () => dialog?.removeEventListener('cancel', handleCancel);
  }, [onCancel]);

  const handleBackdropClick = (e: React.MouseEvent<HTMLDialogElement>) => {
    // Close when clicking the backdrop (outside the dialog content)
    if (e.target === dialogRef.current) {
      onCancel();
    }
  };

  return (
    <dialog
      ref={dialogRef}
      className="fixed bg-transparent p-4 m-0 max-w-none max-h-none w-full h-full backdrop:bg-black/60"
      onClick={handleBackdropClick}
      aria-labelledby="confirm-dialog-title"
    >
      <div className="flex items-center justify-center min-h-full">
        <div 
          className="bg-surface rounded-xl border border-border p-6 max-w-md w-full shadow-xl animate-slide-up"
          onClick={(e) => e.stopPropagation()}
        >
          <h3 id="confirm-dialog-title" className="text-lg font-semibold text-text mb-3">{title}</h3>
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
    </dialog>
  );
}

import { useState, useEffect, useRef } from 'react';
import { X } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { api } from '../api';

interface Props {
  reportId: string;
  title: string;
  cachedContent?: string;
  onClose: () => void;
}

export function ReportDrawer({ reportId, title, cachedContent, onClose }: Props) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const [content, setContent] = useState(cachedContent || '');
  const [loading, setLoading] = useState(!cachedContent);

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

  useEffect(() => {
    if (cachedContent) return;
    setLoading(true);
    api.getReport(reportId)
      .then((data) => setContent(data.content || 'No content.'))
      .catch(() => setContent('Failed to load report.'))
      .finally(() => setLoading(false));
  }, [reportId, cachedContent]);

  const handleBackdropClick = (e: React.MouseEvent<HTMLDialogElement>) => {
    if (e.target === dialogRef.current) {
      onClose();
    }
  };

  return (
    <dialog
      ref={dialogRef}
      className="fixed bg-transparent p-0 m-0 max-w-none max-h-none w-full h-full backdrop:bg-black/60"
      onClick={handleBackdropClick}
      aria-labelledby="report-drawer-title"
    >
      <div className="flex justify-end min-h-full">
        <div 
          className="w-full max-w-2xl h-full bg-surface border-l border-border flex flex-col animate-slide-in-right"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="flex items-center justify-between px-6 py-4 border-b border-border shrink-0">
            <h3 id="report-drawer-title" className="text-lg font-semibold text-text truncate pr-4">{title}</h3>
            <button 
              className="w-8 h-8 rounded-lg flex items-center justify-center text-text-dim hover:bg-surface-hover hover:text-text transition-colors"
              onClick={onClose}
            >
              <X size={18} />
            </button>
          </div>
          
          {/* Body */}
          <div className="flex-1 overflow-y-auto px-6 py-5">
            {loading ? (
              <div className="flex items-center justify-center h-full text-text-dim">Loading...</div>
            ) : (
              <div className="prose max-w-none">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
              </div>
            )}
          </div>
        </div>
      </div>
    </dialog>
  );
}

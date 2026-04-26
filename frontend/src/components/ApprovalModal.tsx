import { Check, X } from 'lucide-react';
import { api } from '../api';

interface Props {
  event: any;
  onClose: () => void;
}

export function ApprovalModal({ event, onClose }: Props) {
  const toolCalls: Array<{
    id: string;
    name: string;
    arguments: Record<string, any> | string;
  }> = event.data?.tool_calls || event.data?.tools || [];

  const send = async (approved: boolean) => {
    const approvals: Record<string, boolean> = {};
    for (const tc of toolCalls) {
      approvals[tc.id] = approved;
    }
    await api.sendApproval(approvals);
    onClose();
  };

  return (
    <div className="absolute inset-0 bg-black/40 flex items-center justify-center p-4 z-40">
      <div className="bg-surface rounded-xl border border-border p-6 max-w-lg w-full shadow-xl animate-slide-up">
        <h4 className="text-lg font-semibold text-text mb-4">Approve Tool Calls</h4>
        
        <div className="flex flex-col gap-3 mb-6 max-h-64 overflow-y-auto">
          {toolCalls.map((t, i) => (
            <div key={t.id} className="flex items-start gap-3 p-3 bg-bg rounded-lg border border-border">
              <span className="w-6 h-6 rounded-full bg-primary text-white flex items-center justify-center text-xs font-bold shrink-0">
                {i + 1}
              </span>
              <div className="flex-1 min-w-0">
                <span className="font-medium text-text block">{t.name}</span>
                <code className="text-xs text-text-dim font-mono block truncate mt-1">
                  {typeof t.arguments === 'string'
                    ? t.arguments.slice(0, 100)
                    : JSON.stringify(t.arguments).slice(0, 100)}
                </code>
              </div>
            </div>
          ))}
        </div>
        
        <div className="flex gap-3">
          <button 
            className="flex-1 py-3 bg-success text-white rounded-lg font-medium hover:opacity-90 transition-all flex items-center justify-center gap-2"
            onClick={() => send(true)}
          >
            <Check size={18} />
            Approve
          </button>
          <button 
            className="flex-1 py-3 bg-error text-white rounded-lg font-medium hover:opacity-90 transition-all flex items-center justify-center gap-2"
            onClick={() => send(false)}
          >
            <X size={18} />
            Reject
          </button>
        </div>
      </div>
    </div>
  );
}

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
    <div className="approval-modal">
      <div className="approval-content">
        <h4>Approve Tool Calls</h4>
        <div className="approval-tools">
          {toolCalls.map((t, i) => (
            <div key={t.id} className="approval-tool">
              <span className="approval-index">{i + 1}</span>
              <span className="approval-name">{t.name}</span>
              <code className="approval-args">
                {typeof t.arguments === 'string'
                  ? t.arguments.slice(0, 100)
                  : JSON.stringify(t.arguments).slice(0, 100)}
              </code>
            </div>
          ))}
        </div>
        <div className="approval-actions">
          <button className="btn-yes" onClick={() => send(true)}>
            Approve
          </button>
          <button className="btn-no" onClick={() => send(false)}>
            Reject
          </button>
        </div>
      </div>
    </div>
  );
}

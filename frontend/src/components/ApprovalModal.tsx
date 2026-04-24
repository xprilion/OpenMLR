import { api } from '../api';

interface Props {
  event: any;
  onClose: () => void;
}

export function ApprovalModal({ event, onClose }: Props) {
  const tools = (event.data?.tools || []) as Array<{
    tool: string;
    arguments: Record<string, any>;
    tool_call_id: string;
  }>;

  const send = async (approved: boolean) => {
    const approvals = tools.map((t) => ({
      tool_call_id: t.tool_call_id,
      approved,
      feedback: approved ? undefined : 'Rejected by user',
    }));
    await api.sendApproval(approvals);
    onClose();
  };

  return (
    <div className="approval-modal">
      <div className="approval-content">
        <h4>Approve Tool Calls</h4>
        <div className="approval-tools">
          {tools.map((t, i) => (
            <div key={t.tool_call_id} className="approval-tool">
              <span className="approval-index">{i + 1}</span>
              <span className="approval-name">{t.tool}</span>
              <code className="approval-args">
                {JSON.stringify(t.arguments).slice(0, 100)}
              </code>
            </div>
          ))}
        </div>
        <div className="approval-actions">
          <button className="btn-yes" onClick={() => send(true)}>
            Yes
          </button>
          <button className="btn-no" onClick={() => send(false)}>
            No
          </button>
          <button className="btn-yolo" onClick={() => send(true)}>
            Yolo (always approve)
          </button>
        </div>
      </div>
    </div>
  );
}

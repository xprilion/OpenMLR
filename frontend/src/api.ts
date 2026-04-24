export async function post(path: string, body: unknown) {
  const res = await fetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export const api = {
  sendMessage: (message: string) => post('/api/message', { message }),
  sendApproval: (approvals: any[]) => post('/api/approval', { approvals }),
  undo: () => post('/api/undo', {}),
  compact: () => post('/api/compact', {}),
  setModel: (model: string) => post('/api/model', { model }),
};

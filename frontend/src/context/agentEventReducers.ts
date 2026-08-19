import type { Message } from '../types';

let msgId = 0;
export const nextMsgId = () => `msg-${++msgId}`;

export function findLastIndex<T>(arr: T[], predicate: (item: T) => boolean): number {
  for (let i = arr.length - 1; i >= 0; i--) {
    if (predicate(arr[i])) return i;
  }
  return -1;
}

export function handleThinkingChunk(prev: Message[], tchunk: string): Message[] {
  if (!tchunk) return prev;
  let msgs = prev;
  if (msgs.length > 0 && msgs[msgs.length - 1].content === '::thinking::') {
    msgs = msgs.slice(0, -1);
  }
  const last = msgs[msgs.length - 1];
  if (last?.role === 'system' && last.content === '::thinking_content::') {
    const updated = [...msgs];
    updated[updated.length - 1] = { ...last, thinking: (last.thinking || '') + tchunk };
    return updated;
  }
  return [...msgs, { id: nextMsgId(), role: 'system', content: '::thinking_content::', thinking: tchunk }];
}

export function handleThinkingEnd(prev: Message[], duration: number): Message[] {
  const idx = findLastIndex(prev, (m: Message) => m.role === 'system' && m.content === '::thinking_content::');
  if (idx >= 0) {
    const updated = [...prev];
    updated[idx] = { ...updated[idx], thinkingDuration: duration };
    return updated;
  }
  return prev;
}

export function handleAssistantChunk(prev: Message[], chunk: string): Message[] {
  if (!chunk) return prev;
  let msgs = prev;
  if (msgs.length > 0 && msgs[msgs.length - 1].content === '::thinking::') {
    msgs = msgs.slice(0, -1);
  }
  const thinkIdx = findLastIndex(msgs, (m: Message) => m.role === 'system' && m.content === '::thinking_content::' && !m.thinkingCollapsed);
  if (thinkIdx >= 0) {
    msgs = [...msgs];
    msgs[thinkIdx] = { ...msgs[thinkIdx], thinkingCollapsed: true };
  }
  const last = msgs[msgs.length - 1];
  if (last?.role === 'assistant' && last.streaming) {
    const updated = [...msgs];
    updated[updated.length - 1] = { ...last, content: last.content + chunk };
    return updated;
  }
  return [...msgs, { id: nextMsgId(), role: 'assistant', content: chunk, streaming: true }];
}

export function handleToolCall(prev: Message[], data?: Record<string, unknown>): Message[] {
  let msgs = prev.filter((m) => !(m.role === 'system' && m.content === '::thinking::'));
  const thinkIdx = findLastIndex(msgs, (m: Message) => m.role === 'system' && m.content === '::thinking_content::' && !m.thinkingCollapsed);
  if (thinkIdx >= 0) {
    msgs = [...msgs];
    msgs[thinkIdx] = { ...msgs[thinkIdx], thinkingCollapsed: true };
  }
  return [
    ...msgs,
    {
      id: nextMsgId(),
      role: 'tool',
      content: '',
      metadata: {
        tool: (data?.tool as string) ?? '',
        tool_call_id: data?.id as string | undefined,
        args: typeof data?.arguments === 'string' ? data.arguments.slice(0, 120) : JSON.stringify(data?.arguments ?? {}).slice(0, 120),
      },
    },
  ];
}

export function handleToolOutput(prev: Message[], data?: Record<string, unknown>): Message[] {
  const tcId = data?.tool_call_id as string | undefined;
  let idx = -1;
  if (tcId) {
    for (let i = prev.length - 1; i >= 0; i--) {
      if (prev[i].metadata?.tool_call_id === tcId) {
        idx = i;
        break;
      }
    }
  }
  if (idx === -1) {
    for (let i = prev.length - 1; i >= 0; i--) {
      if (prev[i].role === 'tool' && prev[i].metadata?.output === undefined) {
        idx = i;
        break;
      }
    }
  }
  if (idx === -1) {
    return [
      ...prev,
      {
        id: nextMsgId(),
        role: 'tool',
        content: '',
        metadata: { output: (data?.output as string) || '', outputSuccess: data?.success as boolean | undefined },
      },
    ];
  }
  const u = [...prev];
  u[idx] = {
    ...u[idx],
    metadata: { ...u[idx].metadata, output: (data?.output as string) || '', outputSuccess: data?.success as boolean | undefined },
  };
  return u;
}

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

export function handleAssistantStreamEnd(prev: Message[]): Message[] {
  const last = prev[prev.length - 1];
  if (last?.role === 'assistant' && last.streaming) {
    const u = [...prev];
    u[u.length - 1] = { ...last, streaming: false };
    return u;
  }
  return prev;
}

export function handleAssistantMessage(prev: Message[], content: string): Message[] {
  if (!content) return prev;
  const msgs = prev.filter((m) => !(m.role === 'system' && m.content === '::thinking::'));
  if (msgs[msgs.length - 1]?.role === 'assistant') return msgs;
  return [...msgs, { id: nextMsgId(), role: 'assistant', content }];
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

export function handleSubAgentStart(prev: Message[], data?: Record<string, unknown>): Message[] {
  const msgs = prev.filter((m) => !(m.role === 'system' && m.content === '::thinking::'));
  return [
    ...msgs,
    {
      id: nextMsgId(),
      role: 'tool',
      content: '',
      metadata: {
        tool: `sub_agent:${data?.agent_type || 'task'}`,
        tool_call_id: data?.parent_tool_call_id as string | undefined,
        args: (data?.description as string) || '',
        isSubAgent: true,
        agentType: data?.agent_type as string | undefined,
        children: [],
      },
    },
  ];
}

export function handleSubAgentToolCall(prev: Message[], data?: Record<string, unknown>): Message[] {
  const parentId = data?.parent_tool_call_id;
  const idx = findLastIndex(prev, (m: Message) => m.metadata?.tool_call_id === parentId && !!m.metadata?.isSubAgent);
  if (idx >= 0) {
    const u = [...prev];
    const children = [
      ...(u[idx].metadata?.children || []),
      {
        tool: (data?.tool as string) || '',
        args: (data?.args as string) || '',
        id: (data?.tool_call_id as string) || '',
      },
    ];
    u[idx] = { ...u[idx], metadata: { ...u[idx].metadata, children, toolCount: children.length } };
    return u;
  }
  return prev;
}

export function handleSubAgentToolOutput(prev: Message[], data?: Record<string, unknown>): Message[] {
  const parentId = data?.parent_tool_call_id;
  const idx = findLastIndex(prev, (m: Message) => m.metadata?.tool_call_id === parentId && !!m.metadata?.isSubAgent);
  if (idx >= 0) {
    const u = [...prev];
    const children = (u[idx].metadata?.children || []).map((c) =>
      c.id === data?.tool_call_id
        ? {
            ...c,
            output: (data?.output as string | undefined)?.slice(0, 200),
            success: data?.success as boolean | undefined,
          }
        : c
    );
    u[idx] = { ...u[idx], metadata: { ...u[idx].metadata, children } };
    return u;
  }
  return prev;
}

export function handleSubAgentEnd(prev: Message[], data?: Record<string, unknown>): Message[] {
  const parentId = data?.parent_tool_call_id;
  const idx = findLastIndex(prev, (m: Message) => m.metadata?.tool_call_id === parentId && !!m.metadata?.isSubAgent);
  if (idx >= 0) {
    const u = [...prev];
    u[idx] = {
      ...u[idx],
      metadata: {
        ...u[idx].metadata,
        output: (data?.summary as string) || 'Completed',
        outputSuccess: true,
        duration: data?.duration_seconds as number | undefined,
        toolCount: data?.tool_count as number | undefined,
      },
    };
    return u;
  }
  return prev;
}

export function mapApiMessages(
  rawMessages: Array<{ role: Message['role']; content: string; metadata?: Record<string, unknown> }>
): Message[] {
  return rawMessages.map((m) => {
    if (m.role === 'tool') {
      const meta = m.metadata || {};
      return {
        id: nextMsgId(),
        role: 'tool' as const,
        content: '',
        metadata: {
          tool: (meta.tool as string) || 'tool',
          args: '',
          output: m.content,
          outputSuccess: meta.success !== false,
        },
      };
    }
    return { id: nextMsgId(), role: m.role, content: m.content };
  });
}


import { useCallback, useRef } from 'react';
import { api } from '../api';
import type {
  AgentEvent,
  Message,
  Conversation,
  QuestionsPayload,
  PlanTask,
  Resource,
  ContextUsage,
  SearchBudget,
  TodoApprovalPayload,
  McpServerStatus,
} from '../types';
import type { ConvStatus } from './chatTypes';
import {
  nextMsgId,
  findLastIndex,
  handleThinkingChunk,
  handleThinkingEnd,
  handleAssistantChunk,
  handleToolCall,
  handleToolOutput,
} from './agentEventReducers';

export { nextMsgId, findLastIndex };

export interface UseAgentEventsParams {
  currentConvUuidRef: React.MutableRefObject<string | null>;
  setModel: (m: string) => void;
  setCurrentConvStatus: (status: ConvStatus) => void;
  setConvStatuses: React.Dispatch<React.SetStateAction<Record<string, ConvStatus>>>;
  setMessages: React.Dispatch<React.SetStateAction<Message[]>>;
  setConversations: React.Dispatch<React.SetStateAction<Conversation[]>>;
  setQuestionsPayload: (p: QuestionsPayload | null) => void;
  setTasks: React.Dispatch<React.SetStateAction<PlanTask[]>>;
  setResources: React.Dispatch<React.SetStateAction<Resource[]>>;
  setRightPanelOpen: React.Dispatch<React.SetStateAction<boolean>>;
  setContextUsage: React.Dispatch<React.SetStateAction<ContextUsage | null>>;
  setSearchBudget: React.Dispatch<React.SetStateAction<SearchBudget | null>>;
  setApprovalEvent: (event: AgentEvent | null) => void;
  setTodoApprovalPayload: (p: TodoApprovalPayload | null) => void;
  setMcpServers: React.Dispatch<React.SetStateAction<McpServerStatus[]>>;
  triggerFileTreeRefresh: () => void;
  loadConversations: () => Promise<Conversation[]>;
  reloadConversationMessages: (uuid: string) => void;
}

export function useAgentEvents({
  currentConvUuidRef,
  setModel,
  setCurrentConvStatus,
  setConvStatuses,
  setMessages,
  setConversations,
  setQuestionsPayload,
  setTasks,
  setResources,
  setRightPanelOpen,
  setContextUsage,
  setSearchBudget,
  setApprovalEvent,
  setTodoApprovalPayload,
  setMcpServers,
  triggerFileTreeRefresh,
  loadConversations,
  reloadConversationMessages,
}: UseAgentEventsParams) {
  const reloadTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const handleEvent = useCallback(
    (event: AgentEvent) => {
      const { event_type, data } = event;
      const activeUuid = currentConvUuidRef.current;
      const eventConvUuid = data?.conversation_uuid;

      if (eventConvUuid && eventConvUuid !== activeUuid) {
        if (event_type === 'job_complete') {
          setConvStatuses((prev) => ({ ...prev, [eventConvUuid as string]: 'idle' }));
          loadConversations();
        } else if (event_type === 'processing') {
          setConvStatuses((prev) => ({ ...prev, [eventConvUuid as string]: 'processing' }));
        }
        return;
      }

      switch (event_type) {
        case 'model_info':
          if (data?.model) setModel(data.model as string);
          break;
        case 'status':
          if (data?.status === 'ready') setCurrentConvStatus('idle');
          break;
        case 'processing':
          setCurrentConvStatus('processing');
          setMessages((prev) => {
            if (prev.length > 0 && prev[prev.length - 1].content === '::thinking::') return prev;
            return [...prev, { id: nextMsgId(), role: 'system', content: '::thinking::' }];
          });
          break;
        case 'thinking_chunk':
          setMessages((prev) => handleThinkingChunk(prev, (data?.chunk as string) || ''));
          break;
        case 'thinking_end':
          setMessages((prev) => handleThinkingEnd(prev, (data?.duration_seconds as number) || 0));
          break;
        case 'assistant_chunk':
          setMessages((prev) => handleAssistantChunk(prev, (data?.chunk as string) || (data?.content as string) || ''));
          break;
        case 'assistant_stream_end':
          setMessages((prev) => {
            const last = prev[prev.length - 1];
            if (last?.role === 'assistant' && last.streaming) {
              const u = [...prev];
              u[u.length - 1] = { ...last, streaming: false };
              return u;
            }
            return prev;
          });
          break;
        case 'assistant_message':
          if (data?.content) {
            setMessages((prev) => {
              const msgs = prev.filter((m) => !(m.role === 'system' && m.content === '::thinking::'));
              if (msgs[msgs.length - 1]?.role === 'assistant') return msgs;
              return [...msgs, { id: nextMsgId(), role: 'assistant', content: data.content as string }];
            });
          }
          break;
        case 'tool_call':
          setMessages((prev) => handleToolCall(prev, data));
          break;
        case 'tool_output':
          setMessages((prev) => handleToolOutput(prev, data));
          break;
        case 'tool_log':
          setMessages((prev) => [...prev, { id: nextMsgId(), role: 'system', content: (data?.message as string) || '' }]);
          break;
        case 'sub_agent_start':
          setMessages((prev) => {
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
          });
          break;
        case 'sub_agent_tool_call':
          setMessages((prev) => {
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
          });
          break;
        case 'sub_agent_tool_output':
          setMessages((prev) => {
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
          });
          break;
        case 'sub_agent_end':
          setMessages((prev) => {
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
          });
          break;
        case 'questions':
          setCurrentConvStatus('waiting_input');
          setQuestionsPayload(data as QuestionsPayload);
          break;
        case 'plan_update': {
          const incomingTasks = (data?.tasks as PlanTask[]) || [];
          setTasks(incomingTasks);
          setRightPanelOpen(true);
          const allCompleted = incomingTasks.every((t) => t.status === 'completed' || t.status === 'cancelled');
          if (allCompleted && incomingTasks.length > 0) {
            setTimeout(() => api.compact().catch(() => {}), 1000);
          }
          break;
        }
        case 'resources_update':
          setResources((data?.resources as Resource[]) || []);
          setRightPanelOpen(true);
          break;
        case 'workspace_files_changed':
          triggerFileTreeRefresh();
          break;
        case 'context_usage':
          if (data) setContextUsage(data as ContextUsage);
          break;
        case 'search_budget':
          if (data) setSearchBudget(data as SearchBudget);
          break;
        case 'approval_required':
          setApprovalEvent(event);
          setCurrentConvStatus('waiting_approval');
          break;
        case 'todo_approval_required':
          setTodoApprovalPayload(data as TodoApprovalPayload);
          setCurrentConvStatus('waiting_approval');
          break;
        case 'turn_complete':
          setApprovalEvent(null);
          setTodoApprovalPayload(null);
          if (reloadTimerRef.current) {
            clearTimeout(reloadTimerRef.current);
            reloadTimerRef.current = null;
          }
          setMessages((prev) => {
            const c = prev
              .filter((m) => !(m.role === 'system' && m.content === '::thinking::'))
              .map((m) => (m.role === 'system' && m.content === '::thinking_content::' && !m.thinkingCollapsed ? { ...m, thinkingCollapsed: true } : m));
            const last = c[c.length - 1];
            setCurrentConvStatus(last?.role === 'assistant' && last.content.trim().endsWith('?') ? 'waiting_input' : 'idle');
            return c;
          });
          loadConversations();
          break;
        case 'conversation_updated': {
          const { uuid, title } = (data || {}) as { uuid?: string; title?: string };
          if (uuid && title) setConversations((prev) => prev.map((c) => (c.uuid === uuid ? { ...c, title } : c)));
          break;
        }
        case 'mcp_status': {
          const servers = data?.servers;
          if (Array.isArray(servers)) {
            setMcpServers(servers as McpServerStatus[]);
          }
          break;
        }
        case 'interrupted':
          setCurrentConvStatus('idle');
          setMessages((prev) => [...prev.filter((m) => !(m.role === 'system' && m.content === '::thinking::')), { id: nextMsgId(), role: 'system', content: 'Interrupted.' }]);
          break;
        case 'error':
          setCurrentConvStatus('idle');
          setMessages((prev) => [...prev.filter((m) => !(m.role === 'system' && m.content === '::thinking::')), { id: nextMsgId(), role: 'error', content: (data?.error as string) || 'Unknown error' }]);
          break;
        case 'compacted':
          setMessages((prev) => [...prev, { id: nextMsgId(), role: 'system', content: 'Context compacted.' }]);
          break;
        case 'undo_complete':
          setMessages((prev) => [...prev, { id: nextMsgId(), role: 'system', content: 'Undone.' }]);
          break;
        case 'job_complete': {
          const { status, error, conversation_uuid } = (data || {}) as { status?: string; error?: string; conversation_uuid?: string };
          const uuid = conversation_uuid || activeUuid;
          if (uuid) setConvStatuses((prev) => ({ ...prev, [uuid]: 'idle' }));
          if (uuid === activeUuid) {
            if (status === 'failed' && error) {
              setMessages((prev) => [...prev, { id: nextMsgId(), role: 'error', content: `Job failed: ${error}` }]);
            }
            if (status === 'completed' && uuid) {
              reloadTimerRef.current = setTimeout(() => {
                reloadTimerRef.current = null;
                reloadConversationMessages(uuid);
              }, 500);
            }
          }
          loadConversations();
          break;
        }
      }
    },
    [
      currentConvUuidRef,
      loadConversations,
      reloadConversationMessages,
      setApprovalEvent,
      setContextUsage,
      setConvStatuses,
      setConversations,
      setMcpServers,
      setMessages,
      setModel,
      setQuestionsPayload,
      setResources,
      setRightPanelOpen,
      setSearchBudget,
      setTasks,
      setTodoApprovalPayload,
      setCurrentConvStatus,
      triggerFileTreeRefresh,
    ]
  );

  return { handleEvent, reloadTimerRef };
}

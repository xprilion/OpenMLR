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
  handleThinkingChunk,
  handleThinkingEnd,
  handleAssistantChunk,
  handleAssistantStreamEnd,
  handleAssistantMessage,
  handleToolCall,
  handleToolOutput,
  handleSubAgentStart,
  handleSubAgentToolCall,
  handleSubAgentToolOutput,
  handleSubAgentEnd,
} from './agentEventReducers';

export { nextMsgId, findLastIndex } from './agentEventReducers';

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

function processTurnComplete(
  setMessages: React.Dispatch<React.SetStateAction<Message[]>>,
  setCurrentConvStatus: (status: ConvStatus) => void,
  setApprovalEvent: (event: AgentEvent | null) => void,
  setTodoApprovalPayload: (p: TodoApprovalPayload | null) => void,
  reloadTimerRef: React.MutableRefObject<ReturnType<typeof setTimeout> | null>
) {
  setApprovalEvent(null);
  setTodoApprovalPayload(null);
  if (reloadTimerRef.current) {
    clearTimeout(reloadTimerRef.current);
    reloadTimerRef.current = null;
  }
  setMessages((prev) => {
    const c = prev
      .filter((m) => !(m.role === 'system' && m.content === '::thinking::'))
      .map((m) =>
        m.role === 'system' && m.content === '::thinking_content::' && !m.thinkingCollapsed
          ? { ...m, thinkingCollapsed: true }
          : m
      );
    const last = c[c.length - 1];
    setCurrentConvStatus(
      last?.role === 'assistant' && last.content.trim().endsWith('?')
        ? 'waiting_input'
        : 'idle'
    );
    return c;
  });
}

function processJobComplete(
  data: Record<string, unknown> | undefined,
  activeUuid: string | null | undefined,
  setConvStatuses: React.Dispatch<React.SetStateAction<Record<string, ConvStatus>>>,
  setMessages: React.Dispatch<React.SetStateAction<Message[]>>,
  reloadConversationMessages: (uuid: string) => void,
  reloadTimerRef: React.MutableRefObject<ReturnType<typeof setTimeout> | null>
) {
  const { status, error, conversation_uuid } = (data || {}) as {
    status?: string;
    error?: string;
    conversation_uuid?: string;
  };
  const uuid = conversation_uuid || activeUuid;
  if (uuid) setConvStatuses((prev) => ({ ...prev, [uuid]: 'idle' }));
  if (uuid === activeUuid) {
    if (status === 'failed' && error) {
      setMessages((prev) => [
        ...prev,
        { id: nextMsgId(), role: 'error', content: `Job failed: ${error}` },
      ]);
    }
    if (status === 'completed' && uuid) {
      reloadTimerRef.current = setTimeout(() => {
        reloadTimerRef.current = null;
        reloadConversationMessages(uuid);
      }, 500);
    }
  }
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
}: Readonly<UseAgentEventsParams>) {
  const reloadTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const dispatchStreamEvents = useCallback(
    (eventType: string, data?: Record<string, unknown>): boolean => {
      switch (eventType) {
        case 'model_info':
          if (data?.model) setModel(data.model as string);
          return true;
        case 'status':
          if (data?.status === 'ready') setCurrentConvStatus('idle');
          return true;
        case 'processing':
          setCurrentConvStatus('processing');
          setMessages((prev) => {
            if (prev.length > 0 && prev[prev.length - 1].content === '::thinking::') return prev;
            return [...prev, { id: nextMsgId(), role: 'system', content: '::thinking::' }];
          });
          return true;
        case 'thinking_chunk':
          setMessages((prev) => handleThinkingChunk(prev, (data?.chunk as string) || ''));
          return true;
        case 'thinking_end':
          setMessages((prev) => handleThinkingEnd(prev, (data?.duration_seconds as number) || 0));
          return true;
        case 'assistant_chunk':
          setMessages((prev) =>
            handleAssistantChunk(prev, (data?.chunk as string) || (data?.content as string) || '')
          );
          return true;
        case 'assistant_stream_end':
          setMessages((prev) => handleAssistantStreamEnd(prev));
          return true;
        case 'assistant_message':
          setMessages((prev) => handleAssistantMessage(prev, (data?.content as string) || ''));
          return true;
        default:
          return false;
      }
    },
    [setCurrentConvStatus, setMessages, setModel]
  );

  const dispatchToolAndSubAgentEvents = useCallback(
    (eventType: string, data?: Record<string, unknown>): boolean => {
      switch (eventType) {
        case 'tool_call':
          setMessages((prev) => handleToolCall(prev, data));
          return true;
        case 'tool_output':
          setMessages((prev) => handleToolOutput(prev, data));
          return true;
        case 'tool_log':
          setMessages((prev) => [
            ...prev,
            { id: nextMsgId(), role: 'system', content: (data?.message as string) || '' },
          ]);
          return true;
        case 'sub_agent_start':
          setMessages((prev) => handleSubAgentStart(prev, data));
          return true;
        case 'sub_agent_tool_call':
          setMessages((prev) => handleSubAgentToolCall(prev, data));
          return true;
        case 'sub_agent_tool_output':
          setMessages((prev) => handleSubAgentToolOutput(prev, data));
          return true;
        case 'sub_agent_end':
          setMessages((prev) => handleSubAgentEnd(prev, data));
          return true;
        default:
          return false;
      }
    },
    [setMessages]
  );

  const dispatchWorkflowEvents = useCallback(
    (event: AgentEvent): boolean => {
      const { event_type: eventType, data } = event;
      switch (eventType) {
        case 'questions':
          setCurrentConvStatus('waiting_input');
          setQuestionsPayload(data as QuestionsPayload);
          return true;
        case 'plan_update': {
          const incomingTasks = (data?.tasks as PlanTask[]) || [];
          setTasks(incomingTasks);
          setRightPanelOpen(true);
          const allCompleted =
            incomingTasks.length > 0 &&
            incomingTasks.every((t) => t.status === 'completed' || t.status === 'cancelled');
          if (allCompleted) {
            setTimeout(() => api.compact().catch(() => {}), 1000);
          }
          return true;
        }
        case 'resources_update':
          setResources((data?.resources as Resource[]) || []);
          setRightPanelOpen(true);
          return true;
        case 'workspace_files_changed':
          triggerFileTreeRefresh();
          return true;
        case 'context_usage':
          if (data) setContextUsage(data as ContextUsage);
          return true;
        case 'search_budget':
          if (data) setSearchBudget(data as SearchBudget);
          return true;
        case 'approval_required':
          setApprovalEvent(event);
          setCurrentConvStatus('waiting_approval');
          return true;
        case 'todo_approval_required':
          setTodoApprovalPayload(data as TodoApprovalPayload);
          setCurrentConvStatus('waiting_approval');
          return true;
        default:
          return false;
      }
    },
    [
      setApprovalEvent,
      setContextUsage,
      setCurrentConvStatus,
      setQuestionsPayload,
      setResources,
      setRightPanelOpen,
      setSearchBudget,
      setTasks,
      setTodoApprovalPayload,
      triggerFileTreeRefresh,
    ]
  );

  const dispatchSystemEvents = useCallback(
    (
      eventType: string,
      data?: Record<string, unknown>,
      activeUuid?: string | null
    ): boolean => {
      switch (eventType) {
        case 'turn_complete':
          processTurnComplete(
            setMessages,
            setCurrentConvStatus,
            setApprovalEvent,
            setTodoApprovalPayload,
            reloadTimerRef
          );
          loadConversations();
          return true;
        case 'conversation_updated': {
          const { uuid, title } = (data || {}) as { uuid?: string; title?: string };
          if (uuid && title) {
            setConversations((prev) =>
              prev.map((c) => (c.uuid === uuid ? { ...c, title } : c))
            );
          }
          return true;
        }
        case 'mcp_status': {
          const servers = data?.servers;
          if (Array.isArray(servers)) setMcpServers(servers as McpServerStatus[]);
          return true;
        }
        case 'interrupted':
          setCurrentConvStatus('idle');
          setMessages((prev) => [
            ...prev.filter((m) => !(m.role === 'system' && m.content === '::thinking::')),
            { id: nextMsgId(), role: 'system', content: 'Interrupted.' },
          ]);
          return true;
        case 'error':
          setCurrentConvStatus('idle');
          setMessages((prev) => [
            ...prev.filter((m) => !(m.role === 'system' && m.content === '::thinking::')),
            {
              id: nextMsgId(),
              role: 'error',
              content: (data?.error as string) || 'Unknown error',
            },
          ]);
          return true;
        case 'compacted':
          setMessages((prev) => [
            ...prev,
            { id: nextMsgId(), role: 'system', content: 'Context compacted.' },
          ]);
          return true;
        case 'undo_complete':
          setMessages((prev) => [
            ...prev,
            { id: nextMsgId(), role: 'system', content: 'Undone.' },
          ]);
          return true;
        case 'job_complete':
          processJobComplete(
            data,
            activeUuid,
            setConvStatuses,
            setMessages,
            reloadConversationMessages,
            reloadTimerRef
          );
          loadConversations();
          return true;
        default:
          return false;
      }
    },
    [
      loadConversations,
      reloadConversationMessages,
      setApprovalEvent,
      setConvStatuses,
      setConversations,
      setCurrentConvStatus,
      setMcpServers,
      setMessages,
      setTodoApprovalPayload,
    ]
  );

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

      if (dispatchStreamEvents(event_type, data)) return;
      if (dispatchToolAndSubAgentEvents(event_type, data)) return;
      if (dispatchWorkflowEvents(event)) return;
      dispatchSystemEvents(event_type, data, activeUuid);
    },
    [
      currentConvUuidRef,
      dispatchStreamEvents,
      dispatchSystemEvents,
      dispatchToolAndSubAgentEvents,
      dispatchWorkflowEvents,
      loadConversations,
      setConvStatuses,
    ]
  );

  return { handleEvent, reloadTimerRef };
}

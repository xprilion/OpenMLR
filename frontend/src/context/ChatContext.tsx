/* eslint-disable react-refresh/only-export-components */
import { createContext, useContext, useState, useCallback, useEffect, useRef, type ReactNode } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { api } from '../api';
import { useSSE } from '../hooks/useSSE';
import { useJobStatus } from '../hooks/useJobStatus';
import type {
  Message,
  Conversation,
  QuestionsPayload,
  PlanTask,
  Resource,
  ContextUsage,
  SearchBudget,
  Project,
  TodoApprovalPayload,
  AgentEvent,
} from '../types';
import type { Mode } from '../components/InputArea';
import { useProject } from './ProjectContext';
import { useCompute } from './ComputeContext';
import { useAgentEvents, nextMsgId } from './useAgentEvents';
import type { ChatContextType, ConvStatus } from './chatTypes';

export type { ChatContextType, ConvStatus };

const ChatContext = createContext<ChatContextType | null>(null);

export function ChatProvider({
  children,
  setModel,
}: {
  children: ReactNode;
  setModel: (m: string) => void;
}) {
  const navigate = useNavigate();
  const { uuid: routeUuid } = useParams<{ uuid: string }>();
  const { activeProject, activeProjectRef, setProjects, setActiveProject, setShowProjectModal, triggerFileTreeRefresh } = useProject();
  const { loadComputeNodes, loadActiveCompute, loadMcpServers, setMcpServers, setActiveCompute } = useCompute();

  const [messages, setMessages] = useState<Message[]>([]);
  const [approvalEvent, setApprovalEvent] = useState<AgentEvent | null>(null);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [currentConvUuid, setCurrentConvUuid] = useState<string | null>(routeUuid || null);
  const [convStatuses, setConvStatuses] = useState<Record<string, ConvStatus>>({});
  const [questionsPayload, setQuestionsPayload] = useState<QuestionsPayload | null>(null);
  const [tasks, setTasks] = useState<PlanTask[]>([]);
  const [resources, setResources] = useState<Resource[]>([]);
  const [rightPanelOpen, setRightPanelOpen] = useState(false);
  const [contextUsage, setContextUsage] = useState<ContextUsage | null>(null);
  const [searchBudget, setSearchBudget] = useState<SearchBudget | null>(null);
  const [viewingReport, setViewingReport] = useState<Resource | null>(null);
  const [inputMode, setInputMode] = useState<Mode>('plan');
  const [inputText, setInputText] = useState('');
  const [todoApprovalPayload, setTodoApprovalPayload] = useState<TodoApprovalPayload | null>(null);
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);
  const [mobileRightOpen, setMobileRightOpen] = useState(false);
  const [conversationLoading, setConversationLoading] = useState(false);

  const currentConvUuidRef = useRef<string | null>(currentConvUuid);
  currentConvUuidRef.current = currentConvUuid;

  const switchSeqRef = useRef(0);
  const sendingRef = useRef(false);
  const reloadDebounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const currentStatus = currentConvUuid ? convStatuses[currentConvUuid] || 'idle' : 'idle';
  const isProcessing = currentStatus === 'processing';
  const agentTurnActive = currentStatus !== 'idle';

  const setCurrentConvStatus = useCallback((status: ConvStatus) => {
    setCurrentConvUuid((uuid) => {
      if (uuid) setConvStatuses((p) => ({ ...p, [uuid]: status }));
      return uuid;
    });
  }, []);

  const loadConversations = useCallback(async (project?: Project | null) => {
    const proj = project !== undefined ? project : activeProjectRef.current;
    try {
      if (!proj?.uuid) return [];
      const data = await api.listProjectConversations(proj.uuid);
      setConversations(data.conversations || []);
      return data.conversations || [];
    } catch {
      return [];
    }
  }, [activeProjectRef]);

  const switchConv = useCallback(async (uuid: string) => {
    const seq = ++switchSeqRef.current;
    if (reloadTimerRef.current) {
      clearTimeout(reloadTimerRef.current);
      reloadTimerRef.current = null;
    }
    setConversationLoading(true);
    setMessages([]);
    try {
      await api.switchConversation(uuid);
      if (seq !== switchSeqRef.current) return;
      const data = await api.getConversation(uuid);
      if (seq !== switchSeqRef.current) return;
      setCurrentConvUuid(uuid);
      if (data.conversation?.model) setModel(data.conversation.model);
      setContextUsage(null);
      setSearchBudget(null);
      setApprovalEvent(null);
      setQuestionsPayload(null);
      setTodoApprovalPayload(null);

      const rawTasks = (data.tasks || []) as Array<{ title: string; status: PlanTask['status'] }>;
      setTasks(rawTasks.map((t) => ({ title: t.title, status: t.status })));
      const rawResources = (data.resources || []) as Array<{ title: string; url?: string; type: Resource['type']; id?: string }>;
      setResources(
        rawResources.map((r) => ({
          title: r.title,
          url: r.url || '',
          type: r.type,
          id: r.id,
        }))
      );

      if ((data.tasks?.length > 0) || (data.resources?.length > 0)) {
        setRightPanelOpen(true);
      }

      const rawMessages = (data.messages || []) as Array<{ role: Message['role']; content: string; metadata?: Record<string, unknown> }>;
      setMessages(
        rawMessages.map((m) => {
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
        })
      );

      if (seq === switchSeqRef.current) await loadActiveCompute(uuid);
    } catch {
      /* ignore */
    } finally {
      if (seq === switchSeqRef.current) setConversationLoading(false);
    }
  }, [loadActiveCompute, setModel]);

  const _doReloadMessages = useCallback(async (uuid: string) => {
    try {
      const data = await api.getConversation(uuid);
      if (uuid !== currentConvUuidRef.current) return;
      if (data.messages) {
        const rawMessages = data.messages as Array<{ role: Message['role']; content: string; metadata?: Record<string, unknown> }>;
        setMessages(
          rawMessages.map((m) => {
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
          })
        );
      }
      if (data.tasks?.length > 0 || data.resources?.length > 0) {
        const rawTasks = (data.tasks || []) as Array<{ title: string; status: PlanTask['status'] }>;
        setTasks(rawTasks.map((t) => ({ title: t.title, status: t.status })));
        const rawResources = (data.resources || []) as Array<{ title: string; url?: string; type: Resource['type']; id?: string }>;
        setResources(rawResources.map((r) => ({ title: r.title, url: r.url || '', type: r.type, id: r.id })));
        setRightPanelOpen(true);
      }
    } catch {
      /* ignore */
    }
  }, []);

  const reloadConversationMessages = useCallback((uuid: string) => {
    if (reloadDebounceRef.current) clearTimeout(reloadDebounceRef.current);
    reloadDebounceRef.current = setTimeout(() => {
      reloadDebounceRef.current = null;
      _doReloadMessages(uuid);
    }, 300);
  }, [_doReloadMessages]);

  const { handleEvent, reloadTimerRef } = useAgentEvents({
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
    loadConversations: () => loadConversations(),
    reloadConversationMessages,
  });

  const sseToken = localStorage.getItem('openmlr_token');
  const handleSSEReconnect = useCallback(() => {
    const uuid = currentConvUuidRef.current;
    if (uuid) {
      reloadConversationMessages(uuid);
      loadConversations();
    }
  }, [reloadConversationMessages, loadConversations]);

  const { connected } = useSSE(handleEvent, true, sseToken, handleSSEReconnect);

  const { isProcessing: jobProcessing } = useJobStatus({
    conversationUuid: currentConvUuid,
    pollInterval: 5000,
    enabled: !connected,
    onJobComplete: (uuid) => {
      reloadConversationMessages(uuid);
      loadConversations();
      setConvStatuses((prev) => ({ ...prev, [uuid]: 'idle' }));
    },
  });

  useEffect(() => {
    if (currentConvUuid && jobProcessing && !connected) {
      setConvStatuses((prev) => ({ ...prev, [currentConvUuid]: 'processing' }));
    }
  }, [currentConvUuid, jobProcessing, connected]);

  const sendMessage = useCallback(
    async (text: string, mode: string, mentions?: Array<{ type: 'server' | 'file'; value: string }>) => {
      if (sendingRef.current) return;
      sendingRef.current = true;
      setInputText('');
      setMessages((prev) => [...prev, { id: nextMsgId(), role: 'user', content: text, metadata: { tool: mode } }]);
      setCurrentConvStatus('processing');
      try {
        await api.sendMessage(text, mode, mentions);
      } catch (err: unknown) {
        const errorMsg = err instanceof Error ? err.message : 'Unknown error';
        setCurrentConvStatus('idle');
        setMessages((prev) => [...prev, { id: nextMsgId(), role: 'error', content: `Failed to send: ${errorMsg}` }]);
      } finally {
        sendingRef.current = false;
      }
    },
    [setCurrentConvStatus]
  );

  const handleSwitchConversation = useCallback(
    (uuid: string) => {
      navigate(`/${uuid}`, { replace: true });
    },
    [navigate]
  );

  const handleNewConversation = useCallback(async () => {
    if (!activeProject) {
      setShowProjectModal(true);
      return;
    }
    try {
      const data = await api.createConversation(undefined, undefined, undefined, activeProject.uuid);
      const conv = data.conversation;
      setConversations((prev) => [conv, ...prev]);
      setCurrentConvUuid(conv.uuid);
      setMessages([]);
      setTasks([]);
      setResources([]);
      setContextUsage(null);
      setSearchBudget(null);
      setApprovalEvent(null);
      setQuestionsPayload(null);
      setTodoApprovalPayload(null);
      if (conv.model) setModel(conv.model);
      await loadActiveCompute(conv.uuid);
      navigate(`/${conv.uuid}`, { replace: true });
    } catch {
      /* ignore */
    }
  }, [activeProject, navigate, loadActiveCompute, setModel, setShowProjectModal]);

  const handleDeleteConversation = useCallback(
    async (uuid: string) => {
      try {
        await api.deleteConversation(uuid);
        setConversations((prev) => prev.filter((c) => c.uuid !== uuid));
        setConvStatuses((prev) => {
          const n = { ...prev };
          delete n[uuid];
          return n;
        });
        if (currentConvUuid === uuid) {
          setCurrentConvUuid(null);
          setMessages([]);
          setTasks([]);
          setResources([]);
          setApprovalEvent(null);
          setQuestionsPayload(null);
          setTodoApprovalPayload(null);
          setActiveCompute(null);
          navigate('/', { replace: true });
        }
      } catch {
        /* ignore */
      }
    },
    [currentConvUuid, navigate, setActiveCompute]
  );

  const handleStop = useCallback(() => {
    api.interrupt().catch(() => {});
    setCurrentConvStatus('idle');
  }, [setCurrentConvStatus]);

  const handleSearchBudgetChange = useCallback((newMax: number) => {
    setSearchBudget((prev) => (prev ? { ...prev, max: newMax } : prev));
  }, []);

  // Auto-compact
  const lastCompactRef = useRef<number>(0);
  useEffect(() => {
    if (!contextUsage) return;
    const now = Date.now();
    if (contextUsage.ratio >= 0.9 && now - lastCompactRef.current > 30000) {
      lastCompactRef.current = now;
      api.compact().catch(() => {});
    }
  }, [contextUsage]);

  // Initial load
  useEffect(() => {
    const init = async () => {
      const [, projData] = await Promise.all([
        loadComputeNodes(),
        api.listProjects().catch(() => ({ projects: [] })),
        loadMcpServers(),
      ]);
      const allProjects: Project[] = projData.projects || [];
      setProjects(allProjects);

      if (allProjects.length === 0) {
        setShowProjectModal(true);
        return;
      }

      const proj = allProjects[0];
      setActiveProject(proj);

      const convs = await loadConversations(proj);
      if (routeUuid) {
        await switchConv(routeUuid);
        return;
      }

      if (convs.length === 0) {
        try {
          const data = await api.createConversation(undefined, undefined, undefined, proj.uuid);
          const conv = data.conversation;
          setConversations([conv]);
          setCurrentConvUuid(conv.uuid);
          if (conv.model) setModel(conv.model);
          navigate(`/${conv.uuid}`, { replace: true });
        } catch {
          /* ignore */
        }
      } else if (!currentConvUuid) {
        const first = convs[0];
        setCurrentConvUuid(first.uuid);
        navigate(`/${first.uuid}`, { replace: true });
        await switchConv(first.uuid);
      }
    };
    init();
  }, []);

  // Reload conversations when activeProject changes
  useEffect(() => {
    if (!activeProject) return;
    loadConversations(activeProject).then((convs) => {
      if (convs.length > 0) {
        const first = convs[0];
        setCurrentConvUuid(first.uuid);
        navigate(`/${first.uuid}`, { replace: true });
        switchConv(first.uuid);
      } else {
        setCurrentConvUuid(null);
        setMessages([]);
        setTasks([]);
        setResources([]);
      }
    });
  }, [activeProject, loadConversations, navigate, switchConv]);

  // Handle route change
  useEffect(() => {
    if (routeUuid && routeUuid !== currentConvUuid) {
      switchConv(routeUuid);
    }
  }, [routeUuid, currentConvUuid, switchConv]);

  const effectiveProcessing = isProcessing || jobProcessing;
  const effectiveTurnActive = agentTurnActive || jobProcessing;

  return (
    <ChatContext.Provider
      value={{
        messages,
        conversations,
        currentConvUuid,
        convStatuses,
        questionsPayload,
        tasks,
        resources,
        rightPanelOpen,
        contextUsage,
        searchBudget,
        viewingReport,
        inputMode,
        inputText,
        approvalEvent,
        todoApprovalPayload,
        mobileSidebarOpen,
        mobileRightOpen,
        conversationLoading,
        connected,
        effectiveProcessing,
        effectiveTurnActive,
        loadConversations,
        switchConv,
        handleSwitchConversation,
        handleNewConversation,
        handleDeleteConversation,
        sendMessage,
        handleStop,
        setInputMode,
        setInputText,
        setRightPanelOpen,
        setMobileSidebarOpen,
        setMobileRightOpen,
        setApprovalEvent,
        setQuestionsPayload,
        setTodoApprovalPayload,
        setViewingReport,
        handleSearchBudgetChange,
        reloadConversationMessages,
        setCurrentConvStatus,
        setMessages,
      }}
    >
      {children}
    </ChatContext.Provider>
  );
}

export function useChat(): ChatContextType {
  const context = useContext(ChatContext);
  if (!context) {
    throw new Error('useChat must be used within a ChatProvider');
  }
  return context;
}

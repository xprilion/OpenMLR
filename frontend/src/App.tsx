import { useState, useCallback, useEffect, useRef } from 'react';
import { Routes, Route, Navigate, useNavigate, useParams } from 'react-router-dom';
import { Copy, Check } from 'lucide-react';
import { ComputeSelector } from './components/ComputeSelector';
import { useSSE } from './hooks/useSSE';
import { useJobStatus } from './hooks/useJobStatus';
import { api } from './api';
import type { AgentEvent, Message, Conversation, User, QuestionsPayload, PlanTask, Resource, ContextUsage, SearchBudget, Project } from './types';
import { MessageList } from './components/MessageList';
import { InputArea, type Mode } from './components/InputArea';
import { Sidebar } from './components/Sidebar';
import { ModelModal } from './components/ModelModal';
import { ApprovalModal } from './components/ApprovalModal';
import { LoginPage } from './components/LoginPage';
import { QuestionDrawer } from './components/QuestionDrawer';
import { RightPanel } from './components/RightPanel';
import { ReportDrawer } from './components/ReportDrawer';
import { AuthGuard } from './components/AuthGuard';
import { OnboardingModal } from './components/OnboardingModal';
import { Terminal } from './components/Terminal';
import { ProjectModal } from './components/ProjectModal';
import { ProjectManageModal } from './components/ProjectManageModal';
import { SettingsPage } from './components/SettingsPage';
import { ProvidersSettings } from './components/settings/ProvidersSettings';
import { AgentSettings } from './components/settings/AgentSettings';
import { McpSettings } from './components/settings/McpSettings';
import { ComputeSettings } from './components/settings/ComputeSettings';
import { WritingSettings } from './components/settings/WritingSettings';

let msgId = 0;
const nextId = () => `msg-${++msgId}`;

/** ES2020-compatible findLastIndex */
function findLastIndex<T>(arr: T[], predicate: (item: T) => boolean): number {
  for (let i = arr.length - 1; i >= 0; i--) {
    if (predicate(arr[i])) return i;
  }
  return -1;
}
type ConvStatus = 'idle' | 'processing' | 'waiting_approval' | 'waiting_input';

// ── Login wrapper (reads user from parent) ──────────────
function LoginRoute({ onAuth }: { onAuth: (u: User) => void }) {
  return <LoginPage onAuth={onAuth} />;
}

// ── Copy button with feedback ───────────────────────────
function CopyModelButton({ model }: { model: string }) {
  const [copied, setCopied] = useState(false);
  
  const handleCopy = async () => {
    // Extract just the model ID (remove context info if present)
    const modelId = model.split(' ')[0];
    try {
      await navigator.clipboard.writeText(modelId);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback for older browsers
      const textArea = document.createElement('textarea');
      textArea.value = modelId;
      document.body.appendChild(textArea);
      textArea.select();
      document.execCommand('copy');
      document.body.removeChild(textArea);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <button
      onClick={handleCopy}
      className="w-8 h-8 rounded-lg flex items-center justify-center text-text-dim hover:bg-surface-hover hover:text-text transition-colors"
      title="Copy model ID"
    >
      {copied ? <Check size={16} className="text-success" /> : <Copy size={16} />}
    </button>
  );
}

// ── Main chat UI (rendered inside AuthGuard) ────────────
function ChatUI({
  user, model, setModel,
}: {
  user: User;
  model: string;
  setModel: (m: string) => void;
}) {
  const navigate = useNavigate();
  const { uuid: routeUuid } = useParams<{ uuid: string }>();

  const [messages, setMessages] = useState<Message[]>([]);
  const [approvalEvent, setApprovalEvent] = useState<any>(null);
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
  const [computeNodes, setComputeNodes] = useState<any[]>([]);
  const [activeCompute, setActiveCompute] = useState<any>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [activeProject, setActiveProject] = useState<Project | null>(null);
  const [showProjectModal, setShowProjectModal] = useState(false);
  const [showManageProjects, setShowManageProjects] = useState(false);
  const [terminalOpen, setTerminalOpen] = useState(false);

  // Ref to always have current conv UUID in SSE callback (avoids stale closure)
  const currentConvUuidRef = useRef<string | null>(currentConvUuid);
  currentConvUuidRef.current = currentConvUuid;

  // ── Derived per-conversation processing state ─────────
  const currentStatus = currentConvUuid ? (convStatuses[currentConvUuid] || 'idle') : 'idle';
  const isProcessing = currentStatus === 'processing';
  const agentTurnActive = currentStatus !== 'idle';

  const loadConversations = useCallback(async () => {
    try { 
      const data = await api.listConversations();
      setConversations(data.conversations || []); 
      return data.conversations || [];
    } catch { 
      return [];
    }
  }, []);

  const loadComputeNodes = useCallback(async () => {
    try {
      const data = await api.getComputeNodes();
      setComputeNodes(data.nodes || []);
    } catch {
      setComputeNodes([]);
    }
  }, []);

  const loadProjects = useCallback(async () => {
    try {
      const data = await api.listProjects();
      setProjects(data.projects || []);
    } catch {
      setProjects([]);
    }
  }, []);

  const loadActiveCompute = useCallback(async (uuid: string) => {
    try {
      const data = await api.getConversationCompute(uuid);
      setActiveCompute(data.node || null);
    } catch {
      setActiveCompute(null);
    }
  }, []);

  // Initial load - load conversations and activate the correct one
  useEffect(() => { 
    const init = async () => {
      await Promise.all([loadComputeNodes(), loadProjects()]);
      const convs = await loadConversations();
      
      // If URL has a conversation UUID, load it directly
      if (routeUuid) {
        await switchConv(routeUuid);
        return;
      }
      
      // If no conversations exist, create one automatically
      if (convs.length === 0) {
        try {
          const data = await api.createConversation();
          const conv = data.conversation;
          setConversations([conv]);
          setCurrentConvUuid(conv.uuid);
          if (conv.model) setModel(conv.model);
          navigate(`/${conv.uuid}`, { replace: true });
        } catch { /* */ }
      } else if (!currentConvUuid) {
        // Auto-select the first (most recent) conversation
        const first = convs[0];
        setCurrentConvUuid(first.uuid);
        navigate(`/${first.uuid}`, { replace: true });
        await switchConv(first.uuid);
      }
    };
    init();
  }, []);

  // Handle navigation to a different conversation via URL change
  useEffect(() => {
    if (routeUuid && routeUuid !== currentConvUuid) {
      switchConv(routeUuid);
    }
  }, [routeUuid]);

  const setCurrentConvStatus = useCallback((status: ConvStatus) => {
    setCurrentConvUuid((uuid) => {
      if (uuid) setConvStatuses((p) => ({ ...p, [uuid]: status }));
      return uuid;
    });
  }, []);

  const switchConv = async (uuid: string) => {
    try {
      await api.switchConversation(uuid);
      const data = await api.getConversation(uuid);
      setCurrentConvUuid(uuid);
      // Only update model if conversation has one explicitly set; don't overwrite the user's sticky model
      if (data.conversation?.model) setModel(data.conversation.model);
      setContextUsage(null); setSearchBudget(null);
      setApprovalEvent(null); setQuestionsPayload(null);
      
      // Load persisted tasks and resources from database
      setTasks(data.tasks?.map((t: any) => ({ title: t.title, status: t.status })) || []);
      setResources(data.resources?.map((r: any) => ({ 
        title: r.title, 
        url: r.url || '', 
        type: r.type,
        id: r.id,
      })) || []);
      
      // Open right panel if there are tasks or resources
      if ((data.tasks?.length > 0) || (data.resources?.length > 0)) {
        setRightPanelOpen(true);
      }
      
      setMessages(data.messages?.map((m: any) => {
        if (m.role === 'tool') {
          const meta = m.metadata || {};
          return { id: nextId(), role: 'tool' as const, content: '', metadata: { tool: meta.tool || 'tool', args: '', output: m.content, outputSuccess: meta.success !== false } };
        }
        return { id: nextId(), role: m.role, content: m.content };
      }) || []);

      // Load active compute for this conversation
      await loadActiveCompute(uuid);
    } catch { /* */ }
  };

  const handleSwitchConversation = async (uuid: string) => {
    navigate(`/${uuid}`, { replace: true });
    await switchConv(uuid);
  };

  const handleNewConversation = async () => {
    try {
      const data = await api.createConversation();
      const conv = data.conversation;
      setConversations((prev) => [conv, ...prev]);
      setCurrentConvUuid(conv.uuid);
      setMessages([]); setTasks([]); setResources([]); setContextUsage(null); setSearchBudget(null);
      setApprovalEvent(null); setQuestionsPayload(null);
      if (conv.model) setModel(conv.model);
      // Load default compute for new conversation
      await loadActiveCompute(conv.uuid);
      navigate(`/${conv.uuid}`, { replace: true });
    } catch { /* */ }
  };

  const handleDeleteConversation = async (uuid: string) => {
    try {
      await api.deleteConversation(uuid);
      setConversations((prev) => prev.filter((c) => c.uuid !== uuid));
      setConvStatuses((prev) => { const n = { ...prev }; delete n[uuid]; return n; });
      if (currentConvUuid === uuid) {
        setCurrentConvUuid(null); setMessages([]); setTasks([]); setResources([]);
        setApprovalEvent(null); setQuestionsPayload(null);
        setActiveCompute(null);
        navigate('/', { replace: true });
      }
    } catch { /* */ }
  };

  const handleComputeChange = useCallback(async (nodeId: number | null) => {
    if (!currentConvUuid) return;
    try {
      if (nodeId === null) {
        await api.clearConversationCompute(currentConvUuid);
      } else {
        await api.setConversationCompute(currentConvUuid, nodeId);
      }
      await loadActiveCompute(currentConvUuid);
    } catch { /* */ }
  }, [currentConvUuid, loadActiveCompute]);

  // Helper to reload messages from DB for a given conversation
  const reloadConversationMessages = useCallback(async (uuid: string) => {
    try {
      const data = await api.getConversation(uuid);
      if (data.messages) {
        setMessages(data.messages.map((m: any) => {
          if (m.role === 'tool') {
            const meta = m.metadata || {};
            return { id: nextId(), role: 'tool' as const, content: '', metadata: { tool: meta.tool || 'tool', args: '', output: m.content, outputSuccess: meta.success !== false } };
          }
          return { id: nextId(), role: m.role, content: m.content };
        }));
      }
      if (data.tasks?.length > 0 || data.resources?.length > 0) {
        setTasks(data.tasks?.map((t: any) => ({ title: t.title, status: t.status })) || []);
        setResources(data.resources?.map((r: any) => ({ title: r.title, url: r.url || '', type: r.type, id: r.id })) || []);
        setRightPanelOpen(true);
      }
    } catch { /* ignore */ }
  }, []);

  // ── Auto-compact when context usage > 90% ─────────────
  const lastCompactRef = useRef<number>(0);
  useEffect(() => {
    if (!contextUsage) return;
    const now = Date.now();
    // Auto-compact when context usage exceeds 90%, but not more than once per 30 seconds
    if (contextUsage.ratio >= 0.9 && now - lastCompactRef.current > 30000) {
      lastCompactRef.current = now;
      api.compact().catch(() => {});
    }
  }, [contextUsage]);

  // ── SSE ───────────────────────────────────────────────
  const handleEvent = useCallback((event: AgentEvent) => {
    const { event_type, data } = event;
    
    // Use ref for current UUID to avoid stale closure issues
    const activeUuid = currentConvUuidRef.current;
    
    // Filter events by conversation UUID when available
    const eventConvUuid = data?.conversation_uuid;
    if (eventConvUuid && eventConvUuid !== activeUuid) {
      // Event is for a different conversation - update its status in sidebar
      if (event_type === 'job_complete') {
        setConvStatuses((prev) => ({ ...prev, [eventConvUuid]: 'idle' }));
        loadConversations();
      } else if (event_type === 'processing') {
        setConvStatuses((prev) => ({ ...prev, [eventConvUuid]: 'processing' }));
      }
      return;
    }
    
    switch (event_type) {
      case 'model_info': if (data?.model) setModel(data.model); break;
      case 'status': if (data?.status === 'ready') setCurrentConvStatus('idle'); break;
      case 'processing':
        setCurrentConvStatus('processing');
        setMessages((prev) => {
          if (prev.length > 0 && prev[prev.length - 1].content === '::thinking::') return prev;
          return [...prev, { id: nextId(), role: 'system', content: '::thinking::' }];
        });
        break;
      case 'assistant_chunk': {
        const chunk = data?.chunk || data?.content || '';
        if (!chunk) break;
        setMessages((prev) => {
          let msgs = prev;
          if (msgs.length > 0 && msgs[msgs.length - 1].content === '::thinking::') msgs = msgs.slice(0, -1);
          const last = msgs[msgs.length - 1];
          if (last?.role === 'assistant' && last.streaming) {
            const updated = [...msgs]; updated[updated.length - 1] = { ...last, content: last.content + chunk }; return updated;
          }
          return [...msgs, { id: nextId(), role: 'assistant', content: chunk, streaming: true }];
        });
        break;
      }
      case 'assistant_stream_end':
        setMessages((prev) => {
          const last = prev[prev.length - 1];
          if (last?.role === 'assistant' && last.streaming) { const u = [...prev]; u[u.length - 1] = { ...last, streaming: false }; return u; }
          return prev;
        });
        break;
      case 'assistant_message':
        if (data?.content) {
          setMessages((prev) => {
            const msgs = prev.filter((m) => !(m.role === 'system' && m.content === '::thinking::'));
            if (msgs[msgs.length - 1]?.role === 'assistant') return msgs;
            return [...msgs, { id: nextId(), role: 'assistant', content: data.content }];
          });
        }
        break;
      case 'tool_call':
        setMessages((prev) => {
          const msgs = prev.filter((m) => !(m.role === 'system' && m.content === '::thinking::'));
          return [...msgs, { id: nextId(), role: 'tool', content: '', metadata: { tool: data?.tool ?? '', tool_call_id: data?.id, args: typeof data?.arguments === 'string' ? data.arguments.slice(0, 120) : JSON.stringify(data?.arguments ?? {}).slice(0, 120) } }];
        });
        break;
      case 'tool_output':
        setMessages((prev) => {
          const tcId = data?.tool_call_id;
          let idx = -1;
          if (tcId) { for (let i = prev.length - 1; i >= 0; i--) { if (prev[i].metadata?.tool_call_id === tcId) { idx = i; break; } } }
          if (idx === -1) { for (let i = prev.length - 1; i >= 0; i--) { if (prev[i].role === 'tool' && prev[i].metadata?.output === undefined) { idx = i; break; } } }
          if (idx === -1) return [...prev, { id: nextId(), role: 'tool', content: '', metadata: { output: data?.output || '', outputSuccess: data?.success } }];
          const u = [...prev]; u[idx] = { ...u[idx], metadata: { ...u[idx].metadata, output: data?.output || '', outputSuccess: data?.success } }; return u;
        });
        break;
      case 'tool_log': setMessages((prev) => [...prev, { id: nextId(), role: 'system', content: data?.message || '' }]); break;
      // Sub-agent events
      case 'sub_agent_start':
        setMessages((prev) => {
          const msgs = prev.filter((m) => !(m.role === 'system' && m.content === '::thinking::'));
          return [...msgs, { id: nextId(), role: 'tool', content: '', metadata: { 
            tool: `sub_agent:${data?.agent_type || 'task'}`, 
            tool_call_id: data?.parent_tool_call_id,
            args: data?.description || '',
            isSubAgent: true,
            agentType: data?.agent_type,
            children: [],
          }}];
        });
        break;
      case 'sub_agent_tool_call':
        setMessages((prev) => {
          const parentId = data?.parent_tool_call_id;
          const idx = findLastIndex(prev, (m: Message) => m.metadata?.tool_call_id === parentId && !!m.metadata?.isSubAgent);
          if (idx >= 0) {
            const u = [...prev];
            const children = [...(u[idx].metadata?.children || []), { tool: data?.tool, args: data?.args, id: data?.tool_call_id }];
            u[idx] = { ...u[idx], metadata: { ...u[idx].metadata, children, toolCount: children.length }};
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
            const children = (u[idx].metadata?.children || []).map((c: any) => 
              c.id === data?.tool_call_id ? { ...c, output: data?.output?.slice(0, 200), success: data?.success } : c
            );
            u[idx] = { ...u[idx], metadata: { ...u[idx].metadata, children }};
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
            u[idx] = { ...u[idx], metadata: { ...u[idx].metadata, 
              output: data?.summary || 'Completed', 
              outputSuccess: true,
              duration: data?.duration_seconds,
              toolCount: data?.tool_count,
            }};
            return u;
          }
          return prev;
        });
        break;
      case 'questions': setCurrentConvStatus('waiting_input'); setQuestionsPayload(data as QuestionsPayload); break;
      case 'plan_update': {
        setTasks(data?.tasks || []); 
        setRightPanelOpen(true); 
        // Auto-compact after all tasks are completed
        const allCompleted = (data?.tasks || []).every((t: any) => t.status === 'completed' || t.status === 'cancelled');
        if (allCompleted && (data?.tasks || []).length > 0) {
          setTimeout(() => api.compact().catch(() => {}), 1000);
        }
        break;
      }
      case 'resources_update': setResources(data?.resources || []); setRightPanelOpen(true); break;
      case 'context_usage': if (data) setContextUsage(data as ContextUsage); break;
      case 'search_budget': if (data) setSearchBudget(data as SearchBudget); break;
      case 'approval_required': setApprovalEvent(event); setCurrentConvStatus('waiting_approval'); break;
      case 'turn_complete':
        setApprovalEvent(null);
        setMessages((prev) => {
          const c = prev.filter((m) => !(m.role === 'system' && m.content === '::thinking::'));
          const last = c[c.length - 1];
          setCurrentConvStatus(last?.role === 'assistant' && last.content.trim().endsWith('?') ? 'waiting_input' : 'idle');
          return c;
        });
        loadConversations();
        break;
      case 'conversation_updated': {
        const { uuid, title } = data || {};
        if (uuid && title) setConversations((prev) => prev.map((c) => c.uuid === uuid ? { ...c, title } : c));
        break;
      }
      case 'interrupted':
        setCurrentConvStatus('idle');
        setMessages((prev) => [...prev.filter((m) => !(m.role === 'system' && m.content === '::thinking::')), { id: nextId(), role: 'system', content: 'Interrupted.' }]);
        break;
      case 'error':
        setCurrentConvStatus('idle');
        setMessages((prev) => [...prev.filter((m) => !(m.role === 'system' && m.content === '::thinking::')), { id: nextId(), role: 'error', content: data?.error || 'Unknown error' }]);
        break;
      case 'compacted': setMessages((prev) => [...prev, { id: nextId(), role: 'system', content: 'Context compacted.' }]); break;
      case 'undo_complete': setMessages((prev) => [...prev, { id: nextId(), role: 'system', content: 'Undone.' }]); break;
      // Background job events (from Redis pub/sub)
      case 'job_complete': {
        const { status, error, conversation_uuid } = data || {};
        const uuid = conversation_uuid || activeUuid;
        // Always update the conversation's status
        if (uuid) setConvStatuses((prev) => ({ ...prev, [uuid]: 'idle' }));
        // Only update messages if this is the active conversation
        if (uuid === activeUuid) {
          if (status === 'failed' && error) {
            setMessages((prev) => [...prev, { id: nextId(), role: 'error', content: `Job failed: ${error}` }]);
          }
          if (status === 'completed' && uuid) {
            setTimeout(() => reloadConversationMessages(uuid), 500);
          }
        }
        loadConversations();
        break;
      }
    }
  }, [setCurrentConvStatus, loadConversations, setModel, reloadConversationMessages]);

  const sseToken = localStorage.getItem('openmlr_token');
  
  // On SSE reconnect, reload current conversation to catch any missed events
  const handleSSEReconnect = useCallback(() => {
    const uuid = currentConvUuidRef.current;
    if (uuid) {
      reloadConversationMessages(uuid);
      loadConversations();
    }
  }, [reloadConversationMessages, loadConversations]);

  const { connected } = useSSE(handleEvent, true, sseToken, handleSSEReconnect);
  
  // Track background job status (fallback when SSE is disconnected)
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
  
  // Update conversation status when job processing status changes
  useEffect(() => {
    if (currentConvUuid && jobProcessing && !connected) {
      setConvStatuses((prev) => ({ ...prev, [currentConvUuid]: 'processing' }));
    }
  }, [currentConvUuid, jobProcessing, connected]);

  const sendMessage = useCallback(async (text: string, mode: string) => {
    setMessages((prev) => [...prev, { id: nextId(), role: 'user', content: text, metadata: { tool: mode } }]);
    setCurrentConvStatus('processing');
    try { await api.sendMessage(text, mode); } catch (err: any) {
      setCurrentConvStatus('idle');
      setMessages((prev) => [...prev, { id: nextId(), role: 'error', content: `Failed to send: ${err.message}` }]);
    }
  }, [setCurrentConvStatus]);

  // Effective processing (combines SSE-driven status with polling fallback)
  const effectiveProcessing = isProcessing || jobProcessing;
  const effectiveTurnActive = agentTurnActive || jobProcessing;

  const modelLabel = contextUsage
    ? `${model || 'select model'} (${(contextUsage.used / 1000).toFixed(0)}k/${(contextUsage.max / 1000).toFixed(0)}k)`
    : (model || 'select model');

  return (
    <div className="flex flex-col h-screen bg-bg">
      {/* Header */}
      <header className="flex items-center justify-between px-3 sm:px-6 h-14 bg-surface border-b border-border shrink-0 gap-2 sm:gap-4">
        <div className="flex items-center gap-2 sm:gap-3 shrink-0">
          <img src="/logo-64.png" alt="OpenMLR" className="w-7 h-7 sm:w-8 sm:h-8" />
          <span className="font-bold text-base sm:text-lg text-primary tracking-tight">OpenMLR</span>
          <span 
            className={`w-2 h-2 rounded-full transition-colors duration-300 ${connected ? 'bg-success' : 'bg-error'}`} 
            title={connected ? 'Connected' : 'Disconnected'}
          />
        </div>
        <div className="flex items-center gap-1 sm:gap-2 min-w-0">
          <ComputeSelector
            currentNode={activeCompute}
            nodes={computeNodes}
            onChange={handleComputeChange}
          />
          <ModelModal currentModel={modelLabel} onModelChange={setModel} />
          <CopyModelButton model={model} />
        </div>
      </header>

      {/* Main content */}
      <div className="flex flex-1 overflow-hidden">
        <Sidebar
          conversations={conversations} currentUuid={currentConvUuid} user={user}
          convStatuses={convStatuses}
          projects={projects}
          activeProject={activeProject}
          onSwitch={handleSwitchConversation} onNew={handleNewConversation}
          onDelete={handleDeleteConversation}
          onSelectProject={setActiveProject}
          onNewProject={() => setShowProjectModal(true)}
          onManageProjects={() => setShowManageProjects(true)}
        />
        
        <div 
          className="flex flex-col flex-1 overflow-hidden relative transition-[padding] duration-200"
          style={{ paddingRight: rightPanelOpen ? '288px' : undefined }}
        >
          {/* Empty state */}
          {messages.length === 0 && !effectiveProcessing && (
            <div className="flex flex-col items-center justify-center flex-1 text-center px-4 sm:px-6 py-8 sm:py-12">
              <div className="relative mb-8">
                {/* Glow ring behind logo */}
                <div
                  className="absolute inset-0 rounded-full animate-[hero-glow_6s_ease-in-out_infinite]"
                  style={{
                    background: 'radial-gradient(circle, rgba(59,130,246,0.12) 0%, transparent 70%)',
                    transform: 'scale(2.5)',
                  }}
                />
                {/* Floating logo */}
                <img
                  src="/logo-512.png"
                  alt="OpenMLR"
                  className="relative w-24 h-24 sm:w-32 sm:h-32 select-none pointer-events-none animate-[hero-float_6s_ease-in-out_infinite]"
                  style={{ opacity: 0.35 }}
                  draggable={false}
                />
              </div>
              <p className="text-lg sm:text-xl text-text-dim animate-[fade-in_0.6s_ease-out]">What would you like to research?</p>
            </div>
          )}
          
          <MessageList messages={messages} hasDrawerOpen={!!questionsPayload} />
          {approvalEvent && <ApprovalModal event={approvalEvent} onClose={() => setApprovalEvent(null)} />}
          {questionsPayload && <QuestionDrawer payload={questionsPayload} onDone={(summary) => { 
            setQuestionsPayload(null); 
            setCurrentConvStatus('processing');
            setMessages((prev) => [...prev, { id: nextId(), role: 'user', content: `Answered:\n${summary}` }]); 
          }} onClose={() => setQuestionsPayload(null)} />}
          <InputArea 
            disabled={effectiveProcessing} 
            showStop={effectiveTurnActive}
            mode={inputMode}
            onModeChange={setInputMode}
            text={inputText}
            onTextChange={setInputText}
            onSend={sendMessage} 
            onStop={() => { api.interrupt().catch(() => {}); setCurrentConvStatus('idle'); }} 
          />
        </div>
        
        {/* RightPanel is fixed position, doesn't affect flex layout */}
        <RightPanel tasks={tasks} resources={resources} contextUsage={contextUsage} searchBudget={searchBudget} visible={rightPanelOpen} projectUuid={activeProject?.uuid || null} onToggle={() => setRightPanelOpen((v) => !v)} onViewReport={(r) => setViewingReport(r)} />
      </div>

      {/* Terminal panel */}
      <Terminal
        projectUuid={activeProject?.uuid || null}
        visible={terminalOpen}
        onToggle={() => setTerminalOpen((v) => !v)}
      />
      
      {viewingReport && <ReportDrawer reportId={viewingReport.id || ''} title={viewingReport.title} cachedContent={viewingReport.content} onClose={() => setViewingReport(null)} />}
      {showProjectModal && <ProjectModal onClose={() => setShowProjectModal(false)} onCreate={(p) => { setProjects((prev) => [p, ...prev]); setActiveProject(p); }} />}
      {showManageProjects && <ProjectManageModal projects={projects} onClose={() => setShowManageProjects(false)} onChanged={() => { loadProjects(); }} />}
    </div>
  );
}

// ── Root App with routing ───────────────────────────────
export default function App() {
  const [user, setUser] = useState<User | null>(null);
  const [model, setModel] = useState('');
  const [needsOnboarding, setNeedsOnboarding] = useState(false);

  const handleAuth = useCallback((u: User) => {
    setUser(u);
    api.getStatus().then((s) => {
      if (s?.model) {
        setModel(s.model);
        setNeedsOnboarding(false);
      } else {
        setNeedsOnboarding(true);
      }
    }).catch(() => {});
  }, []);

  const handleOnboardingComplete = useCallback((selectedModel: string) => {
    setModel(selectedModel);
    setNeedsOnboarding(false);
  }, []);

  return (
    <>
      {needsOnboarding && user && <OnboardingModal onComplete={handleOnboardingComplete} />}
      <Routes>
        {/* Public routes */}
        <Route path="/login" element={<LoginRoute onAuth={handleAuth} />} />

        {/* Protected routes */}
        <Route element={<AuthGuard onAuth={handleAuth} user={user} />}>
          <Route path="/" element={<ChatUI user={user!} model={model} setModel={setModel} />} />
          <Route path="/:uuid" element={<ChatUI user={user!} model={model} setModel={setModel} />} />
          <Route path="/settings" element={<SettingsPage />}>
            <Route index element={<Navigate to="providers" replace />} />
            <Route path="providers" element={<ProvidersSettings />} />
            <Route path="agent" element={<AgentSettings />} />
            <Route path="mcp" element={<McpSettings />} />
            <Route path="compute" element={<ComputeSettings />} />
            <Route path="writing" element={<WritingSettings />} />
          </Route>
        </Route>

        {/* Fallback */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </>
  );
}

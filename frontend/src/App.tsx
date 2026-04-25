import { useState, useCallback, useEffect } from 'react';
import { Routes, Route, Navigate, useNavigate, useParams } from 'react-router-dom';
import { useSSE } from './hooks/useSSE';
import { useJobStatus } from './hooks/useJobStatus';
import { api } from './api';
import type { AgentEvent, Message, Conversation, User, QuestionsPayload, PlanTask, Resource, ContextUsage, SearchBudget } from './types';
import { MessageList } from './components/MessageList';
import { InputArea, type Mode } from './components/InputArea';
import { Sidebar } from './components/Sidebar';
import { ModelModal } from './components/ModelModal';
import { ApprovalModal } from './components/ApprovalModal';
import { LoginPage } from './components/LoginPage';
import { SettingsPanel } from './components/SettingsPanel';
import { QuestionDrawer } from './components/QuestionDrawer';
import { RightPanel } from './components/RightPanel';
import { ReportDrawer } from './components/ReportDrawer';
import { LandingPage } from './components/LandingPage';
import { AuthGuard } from './components/AuthGuard';

let msgId = 0;
const nextId = () => `msg-${++msgId}`;
type ConvStatus = 'idle' | 'processing' | 'waiting_approval' | 'waiting_input';

const IS_PROD = window.location.hostname === 'openmlr.dev';

// ── Login wrapper (reads user from parent) ──────────────
function LoginRoute({ onAuth }: { onAuth: (u: User) => void }) {
  return <LoginPage onAuth={onAuth} />;
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
  const [isProcessing, setIsProcessing] = useState(false);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [currentConvUuid, setCurrentConvUuid] = useState<string | null>(routeUuid || null);
  const [showSettings, setShowSettings] = useState(false);
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
  const [pendingModeSwitch, setPendingModeSwitch] = useState<string | null>(null);

  const loadConversations = useCallback(async () => {
    try { setConversations((await api.listConversations()).conversations || []); } catch { /* */ }
  }, []);

  // Initial load
  useEffect(() => { loadConversations(); }, [loadConversations]);

  // Load conversation from URL param
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
      setModel(data.conversation?.model || model);
      setContextUsage(null); setSearchBudget(null);
      
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
    } catch { /* */ }
  };

  const handleSwitchConversation = async (uuid: string) => {
    navigate(`/app/${uuid}`, { replace: true });
    await switchConv(uuid);
  };

  const handleNewConversation = async () => {
    try {
      const data = await api.createConversation();
      const conv = data.conversation;
      setConversations((prev) => [conv, ...prev]);
      setCurrentConvUuid(conv.uuid);
      setMessages([]); setTasks([]); setResources([]); setContextUsage(null); setSearchBudget(null);
      setModel(conv.model || model);
      navigate(`/app/${conv.uuid}`, { replace: true });
    } catch { /* */ }
  };

  const handleDeleteConversation = async (uuid: string) => {
    try {
      await api.deleteConversation(uuid);
      setConversations((prev) => prev.filter((c) => c.uuid !== uuid));
      if (currentConvUuid === uuid) {
        setCurrentConvUuid(null); setMessages([]); setTasks([]); setResources([]);
        navigate('/app', { replace: true });
      }
    } catch { /* */ }
  };

  // ── SSE ───────────────────────────────────────────────
  const handleEvent = useCallback((event: AgentEvent) => {
    const { event_type, data } = event;
    switch (event_type) {
      case 'model_info': if (data?.model) setModel(data.model); break;
      case 'status': if (data?.status === 'ready') { setIsProcessing(false); setCurrentConvStatus('idle'); } break;
      case 'processing':
        setIsProcessing(true); setCurrentConvStatus('processing');
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
            let msgs = prev.filter((m) => !(m.role === 'system' && m.content === '::thinking::'));
            if (msgs[msgs.length - 1]?.role === 'assistant') return msgs;
            return [...msgs, { id: nextId(), role: 'assistant', content: data.content }];
          });
        }
        break;
      case 'tool_call':
        setMessages((prev) => {
          let msgs = prev.filter((m) => !(m.role === 'system' && m.content === '::thinking::'));
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
      case 'questions': setIsProcessing(false); setCurrentConvStatus('waiting_input'); setQuestionsPayload(data as QuestionsPayload); break;
      case 'plan_update': setTasks(data?.tasks || []); setRightPanelOpen(true); break;
      case 'resources_update': setResources(data?.resources || []); setRightPanelOpen(true); break;
      case 'context_usage': if (data) setContextUsage(data as ContextUsage); break;
      case 'search_budget': if (data) setSearchBudget(data as SearchBudget); break;
      case 'approval_required': setIsProcessing(false); setApprovalEvent(event); setCurrentConvStatus('waiting_approval'); break;
      case 'turn_complete':
        setIsProcessing(false); setApprovalEvent(null);
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
        setIsProcessing(false); setCurrentConvStatus('idle');
        setMessages((prev) => [...prev.filter((m) => !(m.role === 'system' && m.content === '::thinking::')), { id: nextId(), role: 'system', content: 'Interrupted.' }]);
        break;
      case 'error':
        setIsProcessing(false); setCurrentConvStatus('idle');
        setMessages((prev) => [...prev.filter((m) => !(m.role === 'system' && m.content === '::thinking::')), { id: nextId(), role: 'error', content: data?.error || 'Unknown error' }]);
        break;
      case 'compacted': setMessages((prev) => [...prev, { id: nextId(), role: 'system', content: 'Context compacted.' }]); break;
      case 'undo_complete': setMessages((prev) => [...prev, { id: nextId(), role: 'system', content: 'Undone.' }]); break;
      // Background job events (from Redis pub/sub)
      case 'job_complete': {
        const { status, error, conversation_uuid } = data || {};
        if (conversation_uuid === currentConvUuid) {
          setIsProcessing(false);
          setCurrentConvStatus('idle');
          if (status === 'failed' && error) {
            setMessages((prev) => [...prev, { id: nextId(), role: 'error', content: `Job failed: ${error}` }]);
          }
          // Refresh to get latest messages
          loadConversations();
        }
        break;
      }
    }
  }, [setCurrentConvStatus, loadConversations, setModel, model, currentConvUuid]);

  const sseToken = localStorage.getItem('openmlr_token');
  const { connected } = useSSE(handleEvent, true, sseToken);
  
  // Track background job status (fallback when SSE is disconnected)
  const { isProcessing: jobProcessing } = useJobStatus({
    conversationUuid: currentConvUuid,
    pollInterval: 5000,
    enabled: !connected,  // Only poll when SSE is not connected
  });
  
  // Update conversation status when job processing status changes
  useEffect(() => {
    if (currentConvUuid && jobProcessing && !connected) {
      setConvStatuses((prev) => ({ ...prev, [currentConvUuid]: 'processing' }));
    }
  }, [currentConvUuid, jobProcessing, connected]);

  const sendMessage = useCallback(async (text: string, mode: string) => {
    setMessages((prev) => [...prev, { id: nextId(), role: 'user', content: text, metadata: { tool: mode } }]);
    try { await api.sendMessage(text, mode); } catch (err: any) {
      setMessages((prev) => [...prev, { id: nextId(), role: 'error', content: `Failed to send: ${err.message}` }]);
    }
  }, []);

  const modelLabel = contextUsage
    ? `${model || 'select model'} (${(contextUsage.used / 1000).toFixed(0)}k/${(contextUsage.max / 1000).toFixed(0)}k)`
    : (model || 'select model');

  return (
    <div className="app">
      <header className="header">
        <div className="header-left">
          <span className="logo">OpenMLR</span>
          <span className={`connection-dot ${connected ? 'connected' : 'disconnected'}`} />
        </div>
        <div className="header-right">
          <ModelModal currentModel={modelLabel} onModelChange={setModel} />
        </div>
      </header>
      <div className="main">
        <Sidebar
          conversations={conversations} currentUuid={currentConvUuid} user={user}
          convStatuses={convStatuses}
          onSwitch={handleSwitchConversation} onNew={handleNewConversation}
          onDelete={handleDeleteConversation}
          onAction={(type) => { if (type === 'undo') api.undo(); if (type === 'compact') api.compact(); }}
          onOpenSettings={() => setShowSettings(true)}
        />
        <div className="chat">
          {messages.length === 0 && !isProcessing && !jobProcessing && (
            <div className="empty-state">
              <h2>OpenMLR</h2><p>ML Research Intern</p>
              <div className="empty-capabilities">
                <div className="capability"><strong>Plan</strong><span>Ask questions, clarify scope, break down tasks</span></div>
                <div className="capability"><strong>Research</strong><span>Papers, citations, code examples, literature</span></div>
                <div className="capability"><strong>Write</strong><span>Draft sections, manage citations, export</span></div>
                <div className="capability"><strong>Execute</strong><span>Runs code in Docker when needed in any mode</span></div>
              </div>
            </div>
          )}
          <MessageList messages={messages} />
          {approvalEvent && <ApprovalModal event={approvalEvent} onClose={() => setApprovalEvent(null)} />}
          {questionsPayload && <QuestionDrawer payload={questionsPayload} onDone={(summary, suggestedMode) => { 
            setQuestionsPayload(null); 
            setMessages((prev) => [...prev, { id: nextId(), role: 'user', content: `Answered:\n${summary}` }]); 
            if (suggestedMode) {
              setPendingModeSwitch(suggestedMode);
            }
          }} onClose={() => setQuestionsPayload(null)} />}
          {pendingModeSwitch && (
            <div className="mode-switch-prompt">
              <div className="mode-switch-content">
                <span>Agent suggests switching to <strong>{pendingModeSwitch}</strong> mode</span>
                <div className="mode-switch-actions">
                  <button className="btn-confirm" onClick={() => { setInputMode(pendingModeSwitch as Mode); setPendingModeSwitch(null); setMessages((prev) => [...prev, { id: nextId(), role: 'system', content: `Switched to ${pendingModeSwitch} mode.` }]); }}>
                    Switch to {pendingModeSwitch}
                  </button>
                  <button className="btn-cancel" onClick={() => { setPendingModeSwitch(null); setMessages((prev) => [...prev, { id: nextId(), role: 'system', content: `Mode switch declined. Staying in ${inputMode} mode.` }]); }}>
                    Stay in {inputMode}
                  </button>
                </div>
              </div>
            </div>
          )}
          <InputArea 
            disabled={isProcessing || jobProcessing} 
            mode={inputMode}
            onModeChange={setInputMode}
            text={inputText}
            onTextChange={setInputText}
            onSend={sendMessage} 
            onStop={() => api.interrupt().catch(() => {})} 
          />
        </div>
        <RightPanel tasks={tasks} resources={resources} contextUsage={contextUsage} searchBudget={searchBudget} visible={rightPanelOpen} onToggle={() => setRightPanelOpen((v) => !v)} onViewReport={(r) => setViewingReport(r)} />
      </div>
      {showSettings && <SettingsPanel onClose={() => setShowSettings(false)} />}
      {viewingReport && <ReportDrawer reportId={viewingReport.id || ''} title={viewingReport.title} cachedContent={viewingReport.content} onClose={() => setViewingReport(null)} />}
    </div>
  );
}

// ── Root App with routing ───────────────────────────────
export default function App() {
  const [user, setUser] = useState<User | null>(null);
  const [model, setModel] = useState('');

  const handleAuth = useCallback((u: User) => {
    setUser(u);
    api.getStatus().then((s) => { if (s?.model) setModel(s.model); }).catch(() => {});
  }, []);

  return (
    <Routes>
      {/* Landing page: show on prod domain, redirect to /app on self-hosted */}
      <Route path="/" element={IS_PROD ? <LandingPage /> : <Navigate to="/app" replace />} />
      <Route path="/login" element={<LoginRoute onAuth={handleAuth} />} />

      {/* Protected routes */}
      <Route element={<AuthGuard onAuth={handleAuth} user={user} />}>
        <Route path="/app" element={<ChatUI user={user!} model={model} setModel={setModel} />} />
        <Route path="/app/:uuid" element={<ChatUI user={user!} model={model} setModel={setModel} />} />
      </Route>

      {/* Fallback */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

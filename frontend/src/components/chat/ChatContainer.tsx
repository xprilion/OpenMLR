import { Suspense, lazy } from 'react';
import { MessageList } from '../MessageList';
import { InputArea } from '../InputArea';
import { ApprovalModal } from '../ApprovalModal';
import { TodoReviewDrawer } from '../TodoReviewDrawer';
import { QuestionDrawer } from '../QuestionDrawer';
import { ImageViewer } from '../ImageViewer';
import { useChat } from '../../context/ChatContext';
import { useProject, type MainTab } from '../../context/ProjectContext';
import { useCompute } from '../../context/ComputeContext';
import { nextMsgId } from '../../context/agentEventReducers';

const TerminalPanel = lazy(() => import('../Terminal').then((m) => ({ default: m.Terminal })));
const EditorPanel = lazy(() => import('../EditorPanel').then((m) => ({ default: m.EditorPanel })));
const PaperStudio = lazy(() => import('../paper/PaperStudio').then((m) => ({ default: m.PaperStudio })));
const CitationGraph = lazy(() =>
  import('../research/CitationGraph').then((m) => ({ default: m.CitationGraph }))
);
const RunDashboard = lazy(() =>
  import('../experiments/RunDashboard').then((m) => ({ default: m.RunDashboard }))
);
const PeerReviewStudio = lazy(() =>
  import('../review/PeerReviewStudio').then((m) => ({ default: m.PeerReviewStudio }))
);
const EvalBenchmarkDashboard = lazy(() =>
  import('../eval/EvalBenchmarkDashboard').then((m) => ({ default: m.EvalBenchmarkDashboard }))
);
const ResearchWorkflowStudio = lazy(() =>
  import('../research/ResearchWorkflowStudio').then((m) => ({ default: m.ResearchWorkflowStudio }))
);
const DatasetStudio = lazy(() =>
  import('../datasets/DatasetStudio').then((m) => ({ default: m.DatasetStudio }))
);
const SweepStudio = lazy(() =>
  import('../sweeps/SweepStudio').then((m) => ({ default: m.SweepStudio }))
);
const ModelStudio = lazy(() =>
  import('../models/ModelStudio').then((m) => ({ default: m.ModelStudio }))
);

const NAVIGATION_TABS: { id: MainTab; label: string }[] = [
  { id: 'agent', label: 'Agent' },
  { id: 'workflow', label: 'Workflow' },
  { id: 'editor', label: 'Editor' },
  { id: 'terminal', label: 'Terminal' },
  { id: 'paper', label: 'Paper Studio' },
  { id: 'research', label: 'Citation Graph' },
  { id: 'experiments', label: 'Experiments' },
  { id: 'datasets', label: 'Datasets' },
  { id: 'sweeps', label: 'Sweeps' },
  { id: 'models', label: 'Models' },
  { id: 'review', label: 'Peer Review' },
  { id: 'eval', label: 'Benchmarks' },
];

export function ChatContainer() {
  const {
    messages,
    effectiveProcessing,
    effectiveTurnActive,
    conversationLoading,
    questionsPayload,
    approvalEvent,
    todoApprovalPayload,
    inputMode,
    inputText,
    sendMessage,
    handleStop,
    setInputMode,
    setInputText,
    setApprovalEvent,
    setTodoApprovalPayload,
    setQuestionsPayload,
    setCurrentConvStatus,
    setMessages,
  } = useChat();

  const {
    activeProject,
    mainTab,
    setMainTab,
    openFiles,
    activeFilePath,
    setActiveFilePath,
    handleCloseFile,
    imageTab,
    setImageTab,
  } = useProject();

  const { mcpServers, terminalConnected, setTerminalConnected } = useCompute();

  return (
    <div className="flex flex-col flex-1 overflow-hidden relative">
      {/* Agent / Editor / Terminal / Paper / Research tab bar */}
      <div role="tablist" className="flex items-center border-b border-border shrink-0 bg-surface">
        {NAVIGATION_TABS.map((tab) => {
          const isSelected = mainTab === tab.id;
          return (
            <button
              key={tab.id}
              type="button"
              role="tab"
              aria-selected={isSelected}
              className={`px-4 py-2 text-sm font-medium transition-colors flex items-center gap-1.5 ${
                isSelected ? 'text-primary border-b-2 border-primary' : 'text-text-dim hover:text-text'
              }`}
              onClick={() => setMainTab(tab.id)}
            >
              {tab.label}
              {tab.id === 'editor' && openFiles.length > 0 && (
                <span className="ml-1 text-[10px] bg-primary/20 text-primary px-1.5 py-0.5 rounded-full">
                  {openFiles.length}
                </span>
              )}
              {tab.id === 'terminal' && (
                <span className={`w-1.5 h-1.5 rounded-full ${terminalConnected ? 'bg-success' : 'bg-text-dim'}`} />
              )}
            </button>
          );
        })}
        {/* Closable Image tab */}
        {imageTab && (
          <div
            className={`flex items-center gap-1 px-4 py-2 text-sm font-medium transition-colors group ${
              mainTab === 'image' ? 'text-primary border-b-2 border-primary' : 'text-text-dim hover:text-text'
            }`}
          >
            <button type="button" className="truncate" onClick={() => setMainTab('image')}>
              {imageTab.path.split('/').pop()}
            </button>
            <button
              type="button"
              className="w-4 h-4 rounded flex items-center justify-center text-text-dim hover:text-error hover:bg-surface-hover transition-colors opacity-0 group-hover:opacity-100"
              onClick={() => {
                setImageTab(null);
                if (mainTab === 'image') setMainTab('agent');
              }}
              title="Close image"
            >
              &times;
            </button>
          </div>
        )}
      </div>

      {/* Agent tab */}
      <div role="tabpanel" className={`flex flex-col flex-1 overflow-hidden relative ${mainTab === 'agent' ? '' : 'hidden'}`}>
        {messages.length === 0 && !effectiveProcessing && (
          <div className="flex flex-col items-center justify-center flex-1 text-center px-4 sm:px-6 py-8 sm:py-12">
            <div className="relative mb-8">
              <div
                className="absolute inset-0 rounded-full animate-[hero-glow_6s_ease-in-out_infinite]"
                style={{
                  background: 'radial-gradient(circle, rgba(59,130,246,0.12) 0%, transparent 70%)',
                  transform: 'scale(2.5)',
                }}
              />
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

        {conversationLoading ? (
          <div className="flex-1 flex flex-col gap-4 p-6 animate-pulse">
            <div className="h-4 bg-surface-hover rounded w-3/4" />
            <div className="h-4 bg-surface-hover rounded w-1/2" />
            <div className="h-4 bg-surface-hover rounded w-5/6" />
            <div className="h-4 bg-surface-hover rounded w-2/3" />
          </div>
        ) : (
          <MessageList messages={messages} hasDrawerOpen={!!questionsPayload} visible={mainTab === 'agent'} />
        )}

        {approvalEvent && <ApprovalModal event={approvalEvent} onClose={() => setApprovalEvent(null)} />}

        {todoApprovalPayload && (
          <TodoReviewDrawer
            payload={todoApprovalPayload}
            onDone={() => {
              setTodoApprovalPayload(null);
              setCurrentConvStatus('processing');
            }}
            onClose={() => {
              setTodoApprovalPayload(null);
              setCurrentConvStatus('idle');
            }}
          />
        )}

        {questionsPayload && (
          <QuestionDrawer
            payload={questionsPayload}
            onDone={(summary, switchToExecute) => {
              setQuestionsPayload(null);
              setCurrentConvStatus('processing');
              setMessages((prev) => [...prev, { id: nextMsgId(), role: 'user', content: `Answered:\n${summary}` }]);
              if (switchToExecute) setInputMode('execute');
            }}
            onClose={() => setQuestionsPayload(null)}
          />
        )}

        <InputArea
          disabled={effectiveProcessing}
          showStop={effectiveTurnActive}
          mode={inputMode}
          onModeChange={setInputMode}
          text={inputText}
          onTextChange={setInputText}
          onSend={sendMessage}
          onStop={handleStop}
          mcpServers={mcpServers}
          projectUuid={activeProject?.uuid ?? null}
        />
      </div>

      {/* Workflow Studio tab */}
      <div role="tabpanel" className={`flex flex-col flex-1 overflow-hidden ${mainTab === 'workflow' ? '' : 'hidden'}`}>
        <Suspense fallback={<div className="flex-1 flex items-center justify-center text-text-dim">Loading Workflow Studio...</div>}>
          <ResearchWorkflowStudio />
        </Suspense>
      </div>

      {/* Editor tab */}
      <div role="tabpanel" className={`flex flex-col flex-1 overflow-hidden ${mainTab === 'editor' ? '' : 'hidden'}`}>
        <Suspense fallback={<div className="flex-1 flex items-center justify-center text-text-dim">Loading...</div>}>
          <EditorPanel
            openFiles={openFiles}
            activeFilePath={activeFilePath}
            onActivateFile={setActiveFilePath}
            onCloseFile={handleCloseFile}
          />
        </Suspense>
      </div>

      {/* Terminal tab */}
      <div role="tabpanel" className={`flex flex-col flex-1 overflow-hidden ${mainTab === 'terminal' ? '' : 'hidden'}`}>
        <Suspense fallback={<div className="flex-1 flex items-center justify-center text-text-dim">Loading...</div>}>
          <TerminalPanel
            projectUuid={activeProject?.uuid || null}
            visible={mainTab === 'terminal'}
            onConnectionChange={setTerminalConnected}
          />
        </Suspense>
      </div>

      {/* Paper Studio tab */}
      <div role="tabpanel" className={`flex flex-col flex-1 overflow-hidden ${mainTab === 'paper' ? '' : 'hidden'}`}>
        <Suspense fallback={<div className="flex-1 flex items-center justify-center text-text-dim">Loading Paper Studio...</div>}>
          <PaperStudio />
        </Suspense>
      </div>

      {/* Citation Graph tab */}
      <div role="tabpanel" className={`flex flex-col flex-1 overflow-hidden ${mainTab === 'research' ? '' : 'hidden'}`}>
        <Suspense fallback={<div className="flex-1 flex items-center justify-center text-text-dim">Loading Citation Graph...</div>}>
          <CitationGraph />
        </Suspense>
      </div>

      {/* Experiments Dashboard tab */}
      <div role="tabpanel" className={`flex flex-col flex-1 overflow-hidden ${mainTab === 'experiments' ? '' : 'hidden'}`}>
        <Suspense fallback={<div className="flex-1 flex items-center justify-center text-text-dim">Loading Experiment Dashboard...</div>}>
          <RunDashboard />
        </Suspense>
      </div>

      {/* Dataset Studio tab */}
      <div role="tabpanel" className={`flex flex-col flex-1 overflow-hidden ${mainTab === 'datasets' ? '' : 'hidden'}`}>
        <Suspense fallback={<div className="flex-1 flex items-center justify-center text-text-dim">Loading Dataset Studio...</div>}>
          <DatasetStudio />
        </Suspense>
      </div>

      {/* Sweep Studio tab */}
      <div role="tabpanel" className={`flex flex-col flex-1 overflow-hidden ${mainTab === 'sweeps' ? '' : 'hidden'}`}>
        <Suspense fallback={<div className="flex-1 flex items-center justify-center text-text-dim">Loading Sweep Studio...</div>}>
          <SweepStudio projectId={activeProject?.uuid} />
        </Suspense>
      </div>

      {/* Models Studio tab */}
      <div role="tabpanel" className={`flex flex-col flex-1 overflow-hidden ${mainTab === 'models' ? '' : 'hidden'}`}>
        <Suspense fallback={<div className="flex-1 flex items-center justify-center text-text-dim">Loading Model Studio...</div>}>
          <ModelStudio />
        </Suspense>
      </div>

      {/* Peer Review tab */}
      <div role="tabpanel" className={`flex flex-col flex-1 overflow-hidden ${mainTab === 'review' ? '' : 'hidden'}`}>
        <Suspense fallback={<div className="flex-1 flex items-center justify-center text-text-dim">Loading Peer Review Studio...</div>}>
          <PeerReviewStudio />
        </Suspense>
      </div>

      {/* Evaluation Benchmark tab */}
      <div role="tabpanel" className={`flex flex-col flex-1 overflow-hidden ${mainTab === 'eval' ? '' : 'hidden'}`}>
        <Suspense fallback={<div className="flex-1 flex items-center justify-center text-text-dim">Loading Benchmark Harness...</div>}>
          <EvalBenchmarkDashboard />
        </Suspense>
      </div>

      {/* Image tab */}
      {mainTab === 'image' && imageTab && (
        <ImageViewer src={imageTab.url} filename={imageTab.path.split('/').pop() || 'image'} />
      )}
    </div>
  );
}

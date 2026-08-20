import { Suspense, lazy, useEffect, useMemo } from 'react';
import { X } from 'lucide-react';
import { MessageList } from '../MessageList';
import { InputArea } from '../InputArea';
import { ApprovalModal } from '../ApprovalModal';
import { TodoReviewDrawer } from '../TodoReviewDrawer';
import { QuestionDrawer } from '../QuestionDrawer';
import { ImageViewer } from '../ImageViewer';
import { StudioTabsPicker } from './StudioTabsPicker';
import { GenerativeTabPromptBanner } from './GenerativeTabPromptBanner';
import { useChat } from '../../context/ChatContext';
import { useProject, type MainTab, CORE_TABS } from '../../context/ProjectContext';
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
const FigureStudio = lazy(() =>
  import('../figures/FigureStudio').then((m) => ({ default: m.FigureStudio }))
);
const AblationStudio = lazy(() =>
  import('../ablation/AblationStudio').then((m) => ({ default: m.AblationStudio }))
);
const ReproducibilityStudio = lazy(() =>
  import('../reproducibility/ReproducibilityStudio').then((m) => ({ default: m.ReproducibilityStudio }))
);

interface TabLabelMeta {
  id: MainTab;
  label: string;
}

const TAB_METADATA: Record<MainTab, TabLabelMeta> = {
  agent: { id: 'agent', label: 'Agent' },
  editor: { id: 'editor', label: 'Editor' },
  terminal: { id: 'terminal', label: 'Terminal' },
  image: { id: 'image', label: 'Image Preview' },
  workflow: { id: 'workflow', label: 'Workflow' },
  paper: { id: 'paper', label: 'Paper Studio' },
  research: { id: 'research', label: 'Citation Graph' },
  experiments: { id: 'experiments', label: 'Experiments' },
  datasets: { id: 'datasets', label: 'Datasets' },
  sweeps: { id: 'sweeps', label: 'Sweeps' },
  models: { id: 'models', label: 'Models' },
  figures: { id: 'figures', label: 'Figures' },
  ablation: { id: 'ablation', label: 'Ablations' },
  reproducibility: { id: 'reproducibility', label: 'Reproducibility' },
  review: { id: 'review', label: 'Peer Review' },
  eval: { id: 'eval', label: 'Benchmarks' },
};

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
    enabledTabs,
    disableTab,
    promptToOpenTab,
    openFiles,
    activeFilePath,
    setActiveFilePath,
    handleCloseFile,
    imageTab,
    setImageTab,
  } = useProject();

  const { mcpServers, terminalConnected, setTerminalConnected } = useCompute();

  // Generative UI: inspect recent tool events to suggest specialized tabs with user permission
  useEffect(() => {
    if (messages.length === 0) return;
    const lastMsg = messages[messages.length - 1];
    if (lastMsg.role !== 'assistant') return;

    const content = lastMsg.content.toLowerCase();
    if (content.includes('ablation') && !enabledTabs.includes('ablation')) {
      promptToOpenTab(
        'ablation',
        'Ablation Studio',
        'Ablation study or significance testing detected in research flow.'
      );
    } else if ((content.includes('latex') || content.includes('bibtex') || content.includes('paper draft')) && !enabledTabs.includes('paper')) {
      promptToOpenTab(
        'paper',
        'Paper Studio',
        'LaTeX paper drafting or BibTeX compilation activity detected.'
      );
    } else if ((content.includes('figure') || content.includes('tikz') || content.includes('plot')) && !enabledTabs.includes('figures')) {
      promptToOpenTab(
        'figures',
        'Figures Studio',
        'Publication diagram and vector plot activity detected.'
      );
    } else if (content.includes('hyperparameter sweep') && !enabledTabs.includes('sweeps')) {
      promptToOpenTab(
        'sweeps',
        'Sweep Studio',
        'Hyperparameter exploration and parallel coordinates detected.'
      );
    } else if (content.includes('reproducibility audit') && !enabledTabs.includes('reproducibility')) {
      promptToOpenTab(
        'reproducibility',
        'Reproducibility Studio',
        'Reproducibility checklist or audit score ready for inspection.'
      );
    }
  }, [messages, enabledTabs, promptToOpenTab]);

  const activeTabsList = useMemo(() => {
    return enabledTabs.map((id) => TAB_METADATA[id] || { id, label: id });
  }, [enabledTabs]);

  return (
    <div className="flex flex-col flex-1 overflow-hidden relative">
      {/* Focused tab bar with dynamic on-demand tabs */}
      <div
        role="tablist"
        className="flex items-center justify-between border-b border-border shrink-0 bg-surface px-2 sm:px-4 overflow-x-auto"
      >
        <div className="flex items-center gap-1">
          {activeTabsList.map((tab) => {
            const isSelected = mainTab === tab.id;
            const isCore = CORE_TABS.includes(tab.id);

            return (
              <div
                key={tab.id}
                className={`flex items-center gap-1 px-3 py-2 text-sm font-medium transition-colors border-b-2 group ${
                  isSelected ? 'text-primary border-primary' : 'text-text-dim hover:text-text border-transparent'
                }`}
              >
                <button
                  type="button"
                  role="tab"
                  aria-selected={isSelected}
                  className="flex items-center gap-1.5 focus:outline-none"
                  onClick={() => setMainTab(tab.id)}
                >
                  <span>{tab.label}</span>
                  {tab.id === 'editor' && openFiles.length > 0 && (
                    <span className="text-[10px] bg-primary/20 text-primary px-1.5 py-0.5 rounded-full font-semibold">
                      {openFiles.length}
                    </span>
                  )}
                  {tab.id === 'terminal' && (
                    <span
                      className={`w-1.5 h-1.5 rounded-full ${
                        terminalConnected ? 'bg-success' : 'bg-text-dim'
                      }`}
                    />
                  )}
                </button>

                {/* Optional tab close button */}
                {!isCore && (
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      disableTab(tab.id);
                    }}
                    className="w-4 h-4 rounded flex items-center justify-center text-text-dim hover:text-error hover:bg-surface-hover transition-colors ml-0.5"
                    title={`Hide ${tab.label}`}
                    aria-label={`Close ${tab.label} tab`}
                  >
                    <X className="w-3 h-3" />
                  </button>
                )}
              </div>
            );
          })}

          {/* Closable Image preview tab */}
          {imageTab && (
            <div
              className={`flex items-center gap-1 px-3 py-2 text-sm font-medium transition-colors border-b-2 group ${
                mainTab === 'image' ? 'text-primary border-primary' : 'text-text-dim hover:text-text border-transparent'
              }`}
            >
              <button type="button" className="truncate max-w-[120px]" onClick={() => setMainTab('image')}>
                {imageTab.path.split('/').pop()}
              </button>
              <button
                type="button"
                className="w-4 h-4 rounded flex items-center justify-center text-text-dim hover:text-error hover:bg-surface-hover transition-colors"
                onClick={() => {
                  setImageTab(null);
                  if (mainTab === 'image') setMainTab('agent');
                }}
                title="Close image"
                aria-label="Close image tab"
              >
                <X className="w-3 h-3" />
              </button>
            </div>
          )}
        </div>

        {/* Add Tab Picker */}
        <StudioTabsPicker />
      </div>

      {/* Generative Tab Suggestion Banner */}
      <GenerativeTabPromptBanner />

      {/* Agent tab */}
      <div
        role="tabpanel"
        className={`flex flex-col flex-1 overflow-hidden relative ${mainTab === 'agent' ? '' : 'hidden'}`}
      >
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
            <p className="text-lg sm:text-xl text-text-dim animate-[fade-in_0.6s_ease-out]">
              What would you like to research?
            </p>
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
              setMessages((prev) => [
                ...prev,
                { id: nextMsgId(), role: 'user', content: `Answered:\n${summary}` },
              ]);
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

      {/* Editor tab */}
      <div
        role="tabpanel"
        className={`flex flex-col flex-1 overflow-hidden ${mainTab === 'editor' ? '' : 'hidden'}`}
      >
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
      <div
        role="tabpanel"
        className={`flex flex-col flex-1 overflow-hidden ${mainTab === 'terminal' ? '' : 'hidden'}`}
      >
        <Suspense fallback={<div className="flex-1 flex items-center justify-center text-text-dim">Loading...</div>}>
          <TerminalPanel
            projectUuid={activeProject?.uuid || null}
            visible={mainTab === 'terminal'}
            onConnectionChange={setTerminalConnected}
          />
        </Suspense>
      </div>

      {/* Optional Specialized Studios (rendered when active/enabled) */}
      {enabledTabs.includes('workflow') && (
        <div
          role="tabpanel"
          className={`flex flex-col flex-1 overflow-hidden ${mainTab === 'workflow' ? '' : 'hidden'}`}
        >
          <Suspense
            fallback={
              <div className="flex-1 flex items-center justify-center text-text-dim">
                Loading Workflow Studio...
              </div>
            }
          >
            <ResearchWorkflowStudio />
          </Suspense>
        </div>
      )}

      {enabledTabs.includes('paper') && (
        <div
          role="tabpanel"
          className={`flex flex-col flex-1 overflow-hidden ${mainTab === 'paper' ? '' : 'hidden'}`}
        >
          <Suspense
            fallback={
              <div className="flex-1 flex items-center justify-center text-text-dim">
                Loading Paper Studio...
              </div>
            }
          >
            <PaperStudio />
          </Suspense>
        </div>
      )}

      {enabledTabs.includes('research') && (
        <div
          role="tabpanel"
          className={`flex flex-col flex-1 overflow-hidden ${mainTab === 'research' ? '' : 'hidden'}`}
        >
          <Suspense
            fallback={
              <div className="flex-1 flex items-center justify-center text-text-dim">
                Loading Citation Graph...
              </div>
            }
          >
            <CitationGraph />
          </Suspense>
        </div>
      )}

      {enabledTabs.includes('experiments') && (
        <div
          role="tabpanel"
          className={`flex flex-col flex-1 overflow-hidden ${mainTab === 'experiments' ? '' : 'hidden'}`}
        >
          <Suspense
            fallback={
              <div className="flex-1 flex items-center justify-center text-text-dim">
                Loading Experiment Dashboard...
              </div>
            }
          >
            <RunDashboard />
          </Suspense>
        </div>
      )}

      {enabledTabs.includes('datasets') && (
        <div
          role="tabpanel"
          className={`flex flex-col flex-1 overflow-hidden ${mainTab === 'datasets' ? '' : 'hidden'}`}
        >
          <Suspense
            fallback={
              <div className="flex-1 flex items-center justify-center text-text-dim">
                Loading Dataset Studio...
              </div>
            }
          >
            <DatasetStudio />
          </Suspense>
        </div>
      )}

      {enabledTabs.includes('sweeps') && (
        <div
          role="tabpanel"
          className={`flex flex-col flex-1 overflow-hidden ${mainTab === 'sweeps' ? '' : 'hidden'}`}
        >
          <Suspense
            fallback={
              <div className="flex-1 flex items-center justify-center text-text-dim">
                Loading Sweep Studio...
              </div>
            }
          >
            <SweepStudio projectId={activeProject?.uuid} />
          </Suspense>
        </div>
      )}

      {enabledTabs.includes('models') && (
        <div
          role="tabpanel"
          className={`flex flex-col flex-1 overflow-hidden ${mainTab === 'models' ? '' : 'hidden'}`}
        >
          <Suspense
            fallback={
              <div className="flex-1 flex items-center justify-center text-text-dim">
                Loading Model Studio...
              </div>
            }
          >
            <ModelStudio />
          </Suspense>
        </div>
      )}

      {enabledTabs.includes('figures') && (
        <div
          role="tabpanel"
          className={`flex flex-col flex-1 overflow-hidden ${mainTab === 'figures' ? '' : 'hidden'}`}
        >
          <Suspense
            fallback={
              <div className="flex-1 flex items-center justify-center text-text-dim">
                Loading Figure Studio...
              </div>
            }
          >
            <FigureStudio projectId={activeProject?.uuid} />
          </Suspense>
        </div>
      )}

      {enabledTabs.includes('ablation') && (
        <div
          role="tabpanel"
          className={`flex flex-col flex-1 overflow-hidden ${mainTab === 'ablation' ? '' : 'hidden'}`}
        >
          <Suspense
            fallback={
              <div className="flex-1 flex items-center justify-center text-text-dim">
                Loading Ablation Studio...
              </div>
            }
          >
            <AblationStudio projectId={activeProject?.uuid} />
          </Suspense>
        </div>
      )}

      {enabledTabs.includes('reproducibility') && (
        <div
          role="tabpanel"
          className={`flex flex-col flex-1 overflow-hidden ${mainTab === 'reproducibility' ? '' : 'hidden'}`}
        >
          <Suspense
            fallback={
              <div className="flex-1 flex items-center justify-center text-text-dim">
                Loading Reproducibility Studio...
              </div>
            }
          >
            <ReproducibilityStudio />
          </Suspense>
        </div>
      )}

      {enabledTabs.includes('review') && (
        <div
          role="tabpanel"
          className={`flex flex-col flex-1 overflow-hidden ${mainTab === 'review' ? '' : 'hidden'}`}
        >
          <Suspense
            fallback={
              <div className="flex-1 flex items-center justify-center text-text-dim">
                Loading Peer Review Studio...
              </div>
            }
          >
            <PeerReviewStudio />
          </Suspense>
        </div>
      )}

      {enabledTabs.includes('eval') && (
        <div
          role="tabpanel"
          className={`flex flex-col flex-1 overflow-hidden ${mainTab === 'eval' ? '' : 'hidden'}`}
        >
          <Suspense
            fallback={
              <div className="flex-1 flex items-center justify-center text-text-dim">
                Loading Benchmark Harness...
              </div>
            }
          >
            <EvalBenchmarkDashboard />
          </Suspense>
        </div>
      )}

      {/* Image tab */}
      {mainTab === 'image' && imageTab && (
        <ImageViewer src={imageTab.url} filename={imageTab.path.split('/').pop() || 'image'} />
      )}
    </div>
  );
}

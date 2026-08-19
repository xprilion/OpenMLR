import { Suspense, lazy } from 'react';
import { MessageList } from '../MessageList';
import { InputArea } from '../InputArea';
import { ApprovalModal } from '../ApprovalModal';
import { TodoReviewDrawer } from '../TodoReviewDrawer';
import { QuestionDrawer } from '../QuestionDrawer';
import { ImageViewer } from '../ImageViewer';
import { useChat } from '../../context/ChatContext';
import { useProject } from '../../context/ProjectContext';
import { useCompute } from '../../context/ComputeContext';
import { nextMsgId } from '../../context/agentEventReducers';

const TerminalPanel = lazy(() => import('../Terminal').then((m) => ({ default: m.Terminal })));
const EditorPanel = lazy(() => import('../EditorPanel').then((m) => ({ default: m.EditorPanel })));

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
      {/* Agent / Editor / Terminal tab bar */}
      <div role="tablist" className="flex items-center border-b border-border shrink-0 bg-surface">
        <button
          role="tab"
          aria-selected={mainTab === 'agent'}
          className={`px-4 py-2 text-sm font-medium transition-colors ${
            mainTab === 'agent' ? 'text-primary border-b-2 border-primary' : 'text-text-dim hover:text-text'
          }`}
          onClick={() => setMainTab('agent')}
        >
          Agent
        </button>
        <button
          role="tab"
          aria-selected={mainTab === 'editor'}
          className={`px-4 py-2 text-sm font-medium transition-colors ${
            mainTab === 'editor' ? 'text-primary border-b-2 border-primary' : 'text-text-dim hover:text-text'
          }`}
          onClick={() => setMainTab('editor')}
        >
          Editor
          {openFiles.length > 0 && (
            <span className="ml-1.5 text-[10px] bg-primary/20 text-primary px-1.5 py-0.5 rounded-full">
              {openFiles.length}
            </span>
          )}
        </button>
        <button
          role="tab"
          aria-selected={mainTab === 'terminal'}
          className={`px-4 py-2 text-sm font-medium transition-colors flex items-center gap-1.5 ${
            mainTab === 'terminal' ? 'text-primary border-b-2 border-primary' : 'text-text-dim hover:text-text'
          }`}
          onClick={() => setMainTab('terminal')}
        >
          {'Terminal '}
          <span className={`w-1.5 h-1.5 rounded-full ${terminalConnected ? 'bg-success' : 'bg-text-dim'}`} />
        </button>
        {/* Closable Image tab */}
        {imageTab && (
          <div
            className={`flex items-center gap-1 px-4 py-2 text-sm font-medium transition-colors group ${
              mainTab === 'image' ? 'text-primary border-b-2 border-primary' : 'text-text-dim hover:text-text'
            }`}
          >
            <button className="truncate" onClick={() => setMainTab('image')}>
              {imageTab.path.split('/').pop()}
            </button>
            <button
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

      {/* Image tab */}
      {mainTab === 'image' && imageTab && (
        <ImageViewer src={imageTab.url} filename={imageTab.path.split('/').pop() || 'image'} />
      )}
    </div>
  );
}

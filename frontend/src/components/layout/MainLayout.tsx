import { useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Menu, PanelRightOpen } from 'lucide-react';
import { ProjectSelector } from '../ProjectSelector';
import { ComputeSelector } from '../ComputeSelector';
import { ModelModal } from '../ModelModal';
import { CopyModelButton } from '../common/CopyModelButton';
import { Sidebar } from '../Sidebar';
import { RightPanel } from '../RightPanel';
import { ReportDrawer } from '../ReportDrawer';
import { ProjectModal } from '../ProjectModal';
import { ProjectManageModal } from '../ProjectManageModal';
import { ChatContainer } from '../chat/ChatContainer';
import { useChat } from '../../context/ChatContext';
import { useProject } from '../../context/ProjectContext';
import { useCompute } from '../../context/ComputeContext';
import { api } from '../../api';
import type { User, Resource, Project } from '../../types';

export interface MainLayoutProps {
  user: User;
  model: string;
  setModel: (m: string) => void;
}

export function MainLayout({
  user,
  model,
  setModel,
}: Readonly<MainLayoutProps>) {
  const navigate = useNavigate();

  const {
    conversations,
    currentConvUuid,
    convStatuses,
    mobileSidebarOpen,
    setMobileSidebarOpen,
    mobileRightOpen,
    setMobileRightOpen,
    rightPanelOpen,
    setRightPanelOpen,
    handleSwitchConversation,
    handleNewConversation,
    handleDeleteConversation,
    tasks,
    resources,
    contextUsage,
    searchBudget,
    handleSearchBudgetChange,
    viewingReport,
    setViewingReport,
    connected,
  } = useChat();

  const {
    projects,
    activeProject,
    setActiveProject,
    showProjectModal,
    setShowProjectModal,
    showManageProjects,
    setShowManageProjects,
    loadProjects,
    setProjects,
    fileTreeRefreshKey,
    handleFileOpen,
  } = useProject();

  const {
    computeNodes,
    activeCompute,
    mcpServers,
    handleComputeChange,
  } = useCompute();

  const handleMobileSidebarClose = useCallback(() => setMobileSidebarOpen(false), [setMobileSidebarOpen]);
  const handleRightPanelToggle = useCallback(() => setRightPanelOpen((v) => !v), [setRightPanelOpen]);
  const handleMobileRightClose = useCallback(() => setMobileRightOpen(false), [setMobileRightOpen]);
  const handleViewReport = useCallback((r: Resource) => setViewingReport(r), [setViewingReport]);
  const handleCloseViewingReport = useCallback(() => setViewingReport(null), [setViewingReport]);

  const onComputeSelect = useCallback(
    (nodeId: number | null) => {
      handleComputeChange(currentConvUuid, nodeId);
    },
    [currentConvUuid, handleComputeChange]
  );

  const modelLabel = contextUsage
    ? `${model || 'select model'} (${(contextUsage.used / 1000).toFixed(0)}k/${(contextUsage.max / 1000).toFixed(0)}k)`
    : model || 'select model';

  return (
    <div className="flex flex-col h-screen bg-bg">
      {/* Header */}
      <header className="flex items-center justify-between px-3 sm:px-6 h-14 bg-surface border-b border-border shrink-0 gap-2 sm:gap-4">
        <div className="flex items-center gap-2 sm:gap-3 shrink-0">
          <button
            type="button"
            className="w-8 h-8 rounded-lg flex items-center justify-center text-text-dim hover:bg-surface-hover hover:text-text transition-colors md:hidden"
            onClick={() => setMobileSidebarOpen(true)}
            title="Open sidebar"
          >
            <Menu size={20} />
          </button>
          <img src="/logo-64.png" alt="OpenMLR" className="w-7 h-7 sm:w-8 sm:h-8" />
          <span className="font-bold text-base sm:text-lg text-primary tracking-tight max-sm:hidden">OpenMLR</span>
          <span
            className={`w-2 h-2 rounded-full transition-colors duration-300 ${connected ? 'bg-success' : 'bg-error'}`}
            title={connected ? 'Connected' : 'Disconnected'}
          />
        </div>
        <div className="flex items-center gap-1 sm:gap-2 min-w-0">
          <ProjectSelector
            projects={projects}
            activeProject={activeProject}
            onSelectProject={setActiveProject}
            onNewProject={() => setShowProjectModal(true)}
            onManageProjects={() => setShowManageProjects(true)}
          />
          <ComputeSelector
            currentNode={activeCompute}
            nodes={computeNodes}
            onChange={onComputeSelect}
          />
          <ModelModal currentModel={modelLabel} onModelChange={setModel} />
          <CopyModelButton model={model} />
          <button
            type="button"
            className="w-8 h-8 rounded-lg flex items-center justify-center text-text-dim hover:bg-surface-hover hover:text-text transition-colors lg:hidden"
            onClick={() => setMobileRightOpen(true)}
            title="Open panel"
          >
            <PanelRightOpen size={18} />
          </button>
        </div>
      </header>

      {/* Main content layout */}
      <div className="flex flex-1 overflow-hidden">
        <Sidebar
          conversations={conversations}
          currentUuid={currentConvUuid}
          user={user}
          convStatuses={convStatuses}
          mobileOpen={mobileSidebarOpen}
          onSwitch={handleSwitchConversation}
          onNew={handleNewConversation}
          onDelete={handleDeleteConversation}
          onMobileClose={handleMobileSidebarClose}
        />

        <div
          className="flex flex-col flex-1 overflow-hidden relative transition-[padding] duration-200 main-content-area"
          style={{ paddingRight: rightPanelOpen ? '288px' : '48px' }}
        >
          <ChatContainer />
        </div>

        <RightPanel
          tasks={tasks}
          resources={resources}
          contextUsage={contextUsage}
          searchBudget={searchBudget}
          mcpServers={mcpServers}
          visible={rightPanelOpen}
          mobileOpen={mobileRightOpen}
          projectUuid={activeProject?.uuid || null}
          fileTreeRefreshKey={fileTreeRefreshKey}
          onToggle={handleRightPanelToggle}
          onMobileClose={handleMobileRightClose}
          onViewReport={handleViewReport}
          onFileOpen={handleFileOpen}
          onSearchBudgetChange={handleSearchBudgetChange}
        />
      </div>

      {viewingReport && (
        <ReportDrawer
          reportId={viewingReport.id || ''}
          title={viewingReport.title}
          cachedContent={viewingReport.content}
          onClose={handleCloseViewingReport}
        />
      )}

      {showProjectModal && (
        <ProjectModal
          onClose={() => setShowProjectModal(false)}
          onCreate={async (p: Project) => {
            setProjects((prev) => [p, ...prev]);
            setActiveProject(p);
            try {
              const data = await api.createConversation(undefined, undefined, undefined, p.uuid);
              const conv = data.conversation;
              navigate(`/${conv.uuid}`, { replace: true });
            } catch {
              /* ignore */
            }
          }}
        />
      )}

      {showManageProjects && (
        <ProjectManageModal
          projects={projects}
          onClose={() => setShowManageProjects(false)}
          onChanged={() => {
            loadProjects();
          }}
        />
      )}
    </div>
  );
}

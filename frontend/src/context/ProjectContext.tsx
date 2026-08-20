/* eslint-disable react-refresh/only-export-components */
import { createContext, useContext, useState, useCallback, useMemo, useRef, useEffect, type ReactNode } from 'react';
import { api } from '../api';
import type { Project, OpenFile } from '../types';
import { isImageFile, detectLanguage } from '../utils/fileHelpers';

export type MainTab =
  | 'agent'
  | 'editor'
  | 'terminal'
  | 'image'
  | 'workflow'
  | 'paper'
  | 'research'
  | 'experiments'
  | 'datasets'
  | 'sweeps'
  | 'models'
  | 'figures'
  | 'ablation'
  | 'reproducibility'
  | 'review'
  | 'eval';

export const CORE_TABS: readonly MainTab[] = ['agent', 'editor', 'terminal'] as const;

export interface TabSuggestion {
  tab: MainTab;
  title: string;
  description: string;
  sourceEvent?: string;
}

export interface ProjectContextType {
  projects: Project[];
  activeProject: Project | null;
  activeProjectRef: React.MutableRefObject<Project | null>;
  openFiles: OpenFile[];
  activeFilePath: string | null;
  imageTab: { path: string; url: string } | null;
  fileTreeRefreshKey: number;
  showProjectModal: boolean;
  showManageProjects: boolean;
  mainTab: MainTab;
  enabledTabs: MainTab[];
  suggestedTabPrompt: TabSuggestion | null;
  setProjects: React.Dispatch<React.SetStateAction<Project[]>>;
  setActiveProject: React.Dispatch<React.SetStateAction<Project | null>>;
  setShowProjectModal: (show: boolean) => void;
  setShowManageProjects: (show: boolean) => void;
  setMainTab: (tab: MainTab) => void;
  enableTab: (tab: MainTab, switchTo?: boolean) => void;
  disableTab: (tab: MainTab) => void;
  promptToOpenTab: (tab: MainTab, title: string, description: string, sourceEvent?: string) => void;
  dismissSuggestedTabPrompt: () => void;
  setImageTab: (img: { path: string; url: string } | null) => void;
  setActiveFilePath: (path: string | null) => void;
  triggerFileTreeRefresh: () => void;
  loadProjects: () => Promise<Project[]>;
  handleFileOpen: (path: string, content: string) => void;
  handleCloseFile: (path: string) => void;
}

const ProjectContext = createContext<ProjectContextType | null>(null);

const STORAGE_KEY_TABS = 'openmlr_enabled_tabs';

function getInitialEnabledTabs(): MainTab[] {
  if (typeof window === 'undefined') return [...CORE_TABS];
  try {
    const raw = localStorage.getItem(STORAGE_KEY_TABS);
    if (!raw) return [...CORE_TABS];
    const parsed = JSON.parse(raw);
    if (Array.isArray(parsed) && parsed.length > 0) {
      // Ensure all core tabs are always present
      const combined = Array.from(new Set([...CORE_TABS, ...parsed])) as MainTab[];
      return combined;
    }
  } catch {
    // ignore parse error
  }
  return [...CORE_TABS];
}

export function ProjectProvider({ children }: Readonly<{ children: ReactNode }>) {
  const [projects, setProjects] = useState<Project[]>([]);
  const [activeProject, setActiveProject] = useState<Project | null>(null);
  const activeProjectRef = useRef<Project | null>(activeProject);
  activeProjectRef.current = activeProject;

  const [openFiles, setOpenFiles] = useState<OpenFile[]>([]);
  const [activeFilePath, setActiveFilePath] = useState<string | null>(null);
  const [imageTab, setImageTab] = useState<{ path: string; url: string } | null>(null);
  const [fileTreeRefreshKey, setFileTreeRefreshKey] = useState(0);
  const [showProjectModal, setShowProjectModal] = useState(false);
  const [showManageProjects, setShowManageProjects] = useState(false);
  const [mainTab, setMainTab] = useState<MainTab>('agent');
  const [enabledTabs, setEnabledTabs] = useState<MainTab[]>(getInitialEnabledTabs);
  const [suggestedTabPrompt, setSuggestedTabPrompt] = useState<TabSuggestion | null>(null);

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY_TABS, JSON.stringify(enabledTabs));
    } catch {
      // ignore
    }
  }, [enabledTabs]);

  const triggerFileTreeRefresh = useCallback(() => {
    setFileTreeRefreshKey((k) => k + 1);
  }, []);

  const loadProjects = useCallback(async () => {
    try {
      const data = await api.listProjects();
      const loaded = data.projects || [];
      setProjects(loaded);
      return loaded;
    } catch {
      setProjects([]);
      return [];
    }
  }, []);

  const enableTab = useCallback((tab: MainTab, switchTo = true) => {
    setEnabledTabs((prev) => {
      if (prev.includes(tab)) return prev;
      return [...prev, tab];
    });
    if (switchTo) {
      setMainTab(tab);
    }
    setSuggestedTabPrompt((curr) => (curr?.tab === tab ? null : curr));
  }, []);

  const disableTab = useCallback((tab: MainTab) => {
    // Core tabs cannot be closed
    if (CORE_TABS.includes(tab)) return;
    setEnabledTabs((prev) => prev.filter((t) => t !== tab));
    setMainTab((curr) => (curr === tab ? 'agent' : curr));
  }, []);

  const promptToOpenTab = useCallback((tab: MainTab, title: string, description: string, sourceEvent?: string) => {
    setEnabledTabs((curr) => {
      if (curr.includes(tab)) {
        // Tab is already enabled; no prompt needed
        return curr;
      }
      setSuggestedTabPrompt({ tab, title, description, sourceEvent });
      return curr;
    });
  }, []);

  const dismissSuggestedTabPrompt = useCallback(() => {
    setSuggestedTabPrompt(null);
  }, []);

  const handleFileOpen = useCallback((path: string, content: string) => {
    if (isImageFile(path) && activeProjectRef.current?.uuid) {
      const url = api.fileUrl(activeProjectRef.current.uuid, path);
      setImageTab({ path, url });
      setMainTab('image');
      return;
    }
    setOpenFiles((prev) => {
      if (prev.some((f) => f.path === path)) return prev;
      return [...prev, { path, content, language: detectLanguage(path) }];
    });
    setActiveFilePath(path);
    setMainTab('editor');
  }, []);

  const handleCloseFile = useCallback((path: string) => {
    setOpenFiles((prev) => {
      const next = prev.filter((f) => f.path !== path);
      if (activeFilePath === path) {
        if (next.length > 0) {
          setActiveFilePath(next[next.length - 1].path);
        } else {
          setActiveFilePath(null);
          setMainTab('agent');
        }
      }
      return next;
    });
  }, [activeFilePath]);

  const value = useMemo(
    () => ({
      projects,
      activeProject,
      activeProjectRef,
      openFiles,
      activeFilePath,
      imageTab,
      fileTreeRefreshKey,
      showProjectModal,
      showManageProjects,
      mainTab,
      enabledTabs,
      suggestedTabPrompt,
      setProjects,
      setActiveProject,
      setShowProjectModal,
      setShowManageProjects,
      setMainTab,
      enableTab,
      disableTab,
      promptToOpenTab,
      dismissSuggestedTabPrompt,
      setImageTab,
      setActiveFilePath,
      triggerFileTreeRefresh,
      loadProjects,
      handleFileOpen,
      handleCloseFile,
    }),
    [
      projects,
      activeProject,
      openFiles,
      activeFilePath,
      imageTab,
      fileTreeRefreshKey,
      showProjectModal,
      showManageProjects,
      mainTab,
      enabledTabs,
      suggestedTabPrompt,
      enableTab,
      disableTab,
      promptToOpenTab,
      dismissSuggestedTabPrompt,
      triggerFileTreeRefresh,
      loadProjects,
      handleFileOpen,
      handleCloseFile,
    ]
  );

  return (
    <ProjectContext.Provider value={value}>
      {children}
    </ProjectContext.Provider>
  );
}

export function useProject(): ProjectContextType {
  const context = useContext(ProjectContext);
  if (!context) {
    throw new Error('useProject must be used within a ProjectProvider');
  }
  return context;
}

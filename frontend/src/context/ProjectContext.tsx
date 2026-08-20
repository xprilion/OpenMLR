/* eslint-disable react-refresh/only-export-components */
import { createContext, useContext, useState, useCallback, useMemo, useRef, type ReactNode } from 'react';
import { api } from '../api';
import type { Project, OpenFile } from '../types';
import { isImageFile, detectLanguage } from '../utils/fileHelpers';

export type MainTab = 'agent' | 'workflow' | 'editor' | 'terminal' | 'image' | 'paper' | 'research' | 'experiments' | 'datasets' | 'review' | 'eval';

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
  setProjects: React.Dispatch<React.SetStateAction<Project[]>>;
  setActiveProject: React.Dispatch<React.SetStateAction<Project | null>>;
  setShowProjectModal: (show: boolean) => void;
  setShowManageProjects: (show: boolean) => void;
  setMainTab: (tab: MainTab) => void;
  setImageTab: (img: { path: string; url: string } | null) => void;
  setActiveFilePath: (path: string | null) => void;
  triggerFileTreeRefresh: () => void;
  loadProjects: () => Promise<Project[]>;
  handleFileOpen: (path: string, content: string) => void;
  handleCloseFile: (path: string) => void;
}

const ProjectContext = createContext<ProjectContextType | null>(null);

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
      setProjects,
      setActiveProject,
      setShowProjectModal,
      setShowManageProjects,
      setMainTab,
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

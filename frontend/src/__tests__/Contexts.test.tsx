import { describe, it, expect, vi } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { ComputeProvider, useCompute } from '../context/ComputeContext';
import { ProjectProvider, useProject } from '../context/ProjectContext';
import { isImageFile, detectLanguage } from '../utils/fileHelpers';
import { api } from '../api';

vi.mock('../api', () => ({
  api: {
    getComputeNodes: vi.fn().mockResolvedValue({ nodes: [{ id: 1, name: 'Local GPU', type: 'local', health_status: 'healthy' }] }),
    getMcpStatus: vi.fn().mockResolvedValue({ servers: [{ name: 'server1', url: 'http://localhost:8000', enabled: true, connected: true }] }),
    getConversationCompute: vi.fn().mockResolvedValue({ node: { id: 1, name: 'Local GPU', type: 'local', health_status: 'healthy' } }),
    setConversationCompute: vi.fn().mockResolvedValue({ success: true }),
    clearConversationCompute: vi.fn().mockResolvedValue({ success: true }),
    listProjects: vi.fn().mockResolvedValue({
      projects: [{ id: 1, uuid: 'proj-1', name: 'Demo Project', slug: 'demo', status: 'active', settings: {}, created_at: '', updated_at: '' }],
    }),
    fileUrl: vi.fn().mockReturnValue('http://localhost:3000/api/files/test.png'),
  },
}));

describe('fileHelpers', () => {
  it('detects image files properly', () => {
    expect(isImageFile('plot.png')).toBe(true);
    expect(isImageFile('chart.jpg')).toBe(true);
    expect(isImageFile('model.pt')).toBe(false);
    expect(isImageFile('main.py')).toBe(false);
  });

  it('detects Monaco languages properly', () => {
    expect(detectLanguage('train.py')).toBe('python');
    expect(detectLanguage('App.tsx')).toBe('typescript');
    expect(detectLanguage('config.json')).toBe('json');
    expect(detectLanguage('paper.tex')).toBe('latex');
    expect(detectLanguage('refs.bib')).toBe('bibtex');
    expect(detectLanguage('unknown.xyz')).toBe('plaintext');
  });
});

describe('ComputeContext', () => {
  it('throws error when useCompute is used outside ComputeProvider', () => {
    expect(() => renderHook(() => useCompute())).toThrow('useCompute must be used within a ComputeProvider');
  });

  it('loads compute nodes and MCP servers', async () => {
    const { result } = renderHook(() => useCompute(), { wrapper: ComputeProvider });

    await act(async () => {
      await result.current.loadComputeNodes();
      await result.current.loadMcpServers();
    });

    expect(result.current.computeNodes).toHaveLength(1);
    expect(result.current.mcpServers).toHaveLength(1);
  });

  it('handles compute node selection and clearing', async () => {
    const { result } = renderHook(() => useCompute(), { wrapper: ComputeProvider });

    await act(async () => {
      await result.current.handleComputeChange('conv-1', 1);
    });

    expect(api.setConversationCompute).toHaveBeenCalledWith('conv-1', 1);

    await act(async () => {
      await result.current.handleComputeChange('conv-1', null);
    });

    expect(api.clearConversationCompute).toHaveBeenCalledWith('conv-1');
  });
});

describe('ProjectContext', () => {
  it('throws error when useProject is used outside ProjectProvider', () => {
    expect(() => renderHook(() => useProject())).toThrow('useProject must be used within a ProjectProvider');
  });

  it('loads projects and manages active project', async () => {
    const { result } = renderHook(() => useProject(), { wrapper: ProjectProvider });

    await act(async () => {
      const projects = await result.current.loadProjects();
      expect(projects).toHaveLength(1);
    });

    expect(result.current.projects).toHaveLength(1);

    act(() => {
      result.current.setActiveProject(result.current.projects[0]);
    });

    expect(result.current.activeProject?.name).toBe('Demo Project');
  });

  it('opens and closes code and image files', () => {
    const { result } = renderHook(() => useProject(), { wrapper: ProjectProvider });

    act(() => {
      result.current.setActiveProject({ id: 1, uuid: 'proj-1', name: 'P', slug: 'p', description: null, workspace_path: null, status: 'active', settings: {}, created_at: '', updated_at: '' });
      result.current.handleFileOpen('main.py', 'print("hello")');
    });

    expect(result.current.openFiles).toHaveLength(1);
    expect(result.current.activeFilePath).toBe('main.py');
    expect(result.current.mainTab).toBe('editor');

    act(() => {
      result.current.handleCloseFile('main.py');
    });

    expect(result.current.openFiles).toHaveLength(0);
    expect(result.current.activeFilePath).toBeNull();
    expect(result.current.mainTab).toBe('agent');
  });
});

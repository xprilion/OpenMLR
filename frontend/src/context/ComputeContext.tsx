/* eslint-disable react-refresh/only-export-components */
import { createContext, useContext, useState, useCallback, useMemo, type ReactNode } from 'react';
import { api } from '../api';
import type { McpServerStatus } from '../types';
import type { ComputeNode } from '../components/ComputeSelector';

export interface ComputeContextType {
  computeNodes: ComputeNode[];
  activeCompute: ComputeNode | null;
  mcpServers: McpServerStatus[];
  terminalConnected: boolean;
  loadComputeNodes: () => Promise<void>;
  loadActiveCompute: (uuid: string) => Promise<void>;
  loadMcpServers: () => Promise<void>;
  handleComputeChange: (convUuid: string | null, nodeId: number | null) => Promise<void>;
  setTerminalConnected: (connected: boolean) => void;
  setMcpServers: React.Dispatch<React.SetStateAction<McpServerStatus[]>>;
  setActiveCompute: React.Dispatch<React.SetStateAction<ComputeNode | null>>;
}

const ComputeContext = createContext<ComputeContextType | null>(null);

export function ComputeProvider({ children }: Readonly<{ children: ReactNode }>) {
  const [computeNodes, setComputeNodes] = useState<ComputeNode[]>([]);
  const [activeCompute, setActiveCompute] = useState<ComputeNode | null>(null);
  const [mcpServers, setMcpServers] = useState<McpServerStatus[]>([]);
  const [terminalConnected, setTerminalConnected] = useState(false);

  const loadComputeNodes = useCallback(async () => {
    try {
      const data = await api.getComputeNodes();
      setComputeNodes((data.nodes || []) as ComputeNode[]);
    } catch {
      setComputeNodes([]);
    }
  }, []);

  const loadMcpServers = useCallback(async () => {
    try {
      const data = await api.getMcpStatus();
      setMcpServers(data.servers || []);
    } catch {
      setMcpServers([]);
    }
  }, []);

  const loadActiveCompute = useCallback(async (uuid: string) => {
    try {
      const data = await api.getConversationCompute(uuid);
      setActiveCompute((data.node || null) as ComputeNode | null);
    } catch {
      setActiveCompute(null);
    }
  }, []);

  const handleComputeChange = useCallback(async (convUuid: string | null, nodeId: number | null) => {
    if (!convUuid) return;
    try {
      if (nodeId === null) {
        await api.clearConversationCompute(convUuid);
      } else {
        await api.setConversationCompute(convUuid, nodeId);
      }
      await loadActiveCompute(convUuid);
    } catch {
      /* ignore */
    }
  }, [loadActiveCompute]);

  const value = useMemo(
    () => ({
      computeNodes,
      activeCompute,
      mcpServers,
      terminalConnected,
      loadComputeNodes,
      loadActiveCompute,
      loadMcpServers,
      handleComputeChange,
      setTerminalConnected,
      setMcpServers,
      setActiveCompute,
    }),
    [
      computeNodes,
      activeCompute,
      mcpServers,
      terminalConnected,
      loadComputeNodes,
      loadActiveCompute,
      loadMcpServers,
      handleComputeChange,
    ]
  );

  return (
    <ComputeContext.Provider value={value}>
      {children}
    </ComputeContext.Provider>
  );
}

export function useCompute(): ComputeContextType {
  const context = useContext(ComputeContext);
  if (!context) {
    throw new Error('useCompute must be used within a ComputeProvider');
  }
  return context;
}

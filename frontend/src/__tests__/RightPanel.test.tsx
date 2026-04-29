import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { RightPanel } from '../components/RightPanel';
import type { PlanTask, Resource, ContextUsage, SearchBudget, McpServerStatus } from '../types';

vi.mock('../api', () => ({
  api: {
    getReport: vi.fn(),
  },
}));

describe('RightPanel', () => {
  const mockTasks: PlanTask[] = [
    { title: 'Read papers', status: 'completed' },
    { title: 'Implement model', status: 'in_progress' },
    { title: 'Write report', status: 'pending' },
  ];

  const mockResources: Resource[] = [
    { title: 'Plan', type: 'plan', id: 'plan-1', url: '' },
    { title: 'ArXiv Paper', type: 'paper', id: 'paper-1', url: '' },
    { title: 'Dataset X', type: 'dataset', url: 'https://example.com' },
  ];

  const mockContext: ContextUsage = { used: 50000, max: 200000, ratio: 0.25 };
  const mockSearchBudget: SearchBudget = { used: 5, max: 25 };
  const mockMcpServers: McpServerStatus[] = [
    { name: 'test-server', url: 'https://mcp.example.com', enabled: true, connected: true },
  ];

  const baseProps = {
    resources: [] as Resource[],
    contextUsage: null as ContextUsage | null,
    searchBudget: null as SearchBudget | null,
    mcpServers: [] as McpServerStatus[],
    projectUuid: null as string | null,
    onToggle: vi.fn(),
    onViewReport: vi.fn(),
  };

  it('renders collapsed rail with expand button when not visible', () => {
    render(
      <RightPanel {...baseProps} tasks={mockTasks} resources={mockResources} contextUsage={mockContext} visible={false} />
    );
    expect(screen.getByTitle('Expand panel')).toBeInTheDocument();
    expect(screen.getByTitle('Todos')).toBeInTheDocument();
  });

  it('renders tasks when visible', () => {
    render(
      <RightPanel {...baseProps} tasks={mockTasks} visible={true} />
    );
    expect(screen.getByText('Read papers')).toBeInTheDocument();
    expect(screen.getByText('Implement model')).toBeInTheDocument();
    expect(screen.getByText('Write report')).toBeInTheDocument();
  });

  it('shows task completion count badge', () => {
    render(
      <RightPanel {...baseProps} tasks={mockTasks} visible={true} />
    );
    expect(screen.getByText('1/3')).toBeInTheDocument();
  });

  it('shows "No tasks yet" when empty', () => {
    render(
      <RightPanel {...baseProps} tasks={[]} visible={true} />
    );
    expect(screen.getByText('No tasks yet')).toBeInTheDocument();
  });

  it('renders context gauge with data', () => {
    render(
      <RightPanel {...baseProps} tasks={[]} contextUsage={mockContext} visible={true} />
    );
    expect(screen.getByText(/50k/)).toBeInTheDocument();
    expect(screen.getByText(/200k/)).toBeInTheDocument();
  });

  it('renders context gauge placeholder when null', () => {
    render(
      <RightPanel {...baseProps} tasks={[]} visible={true} />
    );
    expect(screen.getByText('Context: --')).toBeInTheDocument();
  });

  it('renders search budget gauge', () => {
    render(
      <RightPanel {...baseProps} tasks={[]} searchBudget={mockSearchBudget} visible={true} />
    );
    expect(screen.getByText(/Searches:/)).toBeInTheDocument();
  });

  it('renders default search budget when null', () => {
    render(
      <RightPanel {...baseProps} tasks={[]} visible={true} />
    );
    expect(screen.getByText('Searches: 0 / 25')).toBeInTheDocument();
  });

  it('does not render resources section (resources are now in FileTree)', () => {
    render(
      <RightPanel {...baseProps} tasks={mockTasks} resources={mockResources} visible={true} />
    );
    expect(screen.queryByText('No resources yet')).not.toBeInTheDocument();
  });

  it('does not render paper export buttons (papers are now in FileTree)', () => {
    render(
      <RightPanel
        {...baseProps}
        tasks={[]}
        resources={[{ title: 'My Paper', type: 'paper', id: 'paper-1', url: '' }]}
        visible={true}
      />
    );
    expect(screen.queryByText('.md')).not.toBeInTheDocument();
    expect(screen.queryByText('.tex')).not.toBeInTheDocument();
  });

  it('shows task count badge on collapsed rail', () => {
    render(
      <RightPanel {...baseProps} tasks={mockTasks} visible={false} />
    );
    const todosButton = screen.getByTitle('Todos');
    const badge = todosButton.querySelector('span');
    expect(badge?.textContent).toBe('3');
  });

  it('has search budget settings button', () => {
    render(
      <RightPanel {...baseProps} tasks={[]} visible={true} />
    );
    expect(screen.getByTitle('Change search budget')).toBeInTheDocument();
  });

  it('renders MCP servers section when servers are configured', () => {
    render(
      <RightPanel {...baseProps} tasks={[]} mcpServers={mockMcpServers} visible={true} />
    );
    expect(screen.getByText('MCP Servers')).toBeInTheDocument();
    expect(screen.getByText('test-server')).toBeInTheDocument();
  });

  it('shows MCP server count badge on collapsed rail', () => {
    render(
      <RightPanel {...baseProps} tasks={[]} mcpServers={mockMcpServers} visible={false} />
    );
    expect(screen.getByTitle('MCP Servers')).toBeInTheDocument();
  });

  it('does not render MCP section when no servers configured', () => {
    render(
      <RightPanel {...baseProps} tasks={[]} mcpServers={[]} visible={true} />
    );
    expect(screen.queryByText('MCP Servers')).not.toBeInTheDocument();
  });
});

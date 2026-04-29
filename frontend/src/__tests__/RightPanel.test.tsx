import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { RightPanel } from '../components/RightPanel';
import type { PlanTask, Resource, ContextUsage, SearchBudget } from '../types';

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

  it('renders collapsed rail with expand button when not visible', () => {
    render(
      <RightPanel
        tasks={mockTasks}
        resources={mockResources}
        contextUsage={mockContext}
        searchBudget={null}
        visible={false}
        projectUuid={null}
        onToggle={vi.fn()}
        onViewReport={vi.fn()}
      />
    );
    expect(screen.getByTitle('Expand panel')).toBeInTheDocument();
    expect(screen.getByTitle('Todos')).toBeInTheDocument();
  });

  it('renders tasks when visible', () => {
    render(
      <RightPanel
        tasks={mockTasks}
        resources={[]}
        contextUsage={null}
        searchBudget={null}
        visible={true}
        projectUuid={null}
        onToggle={vi.fn()}
        onViewReport={vi.fn()}
      />
    );
    expect(screen.getByText('Read papers')).toBeInTheDocument();
    expect(screen.getByText('Implement model')).toBeInTheDocument();
    expect(screen.getByText('Write report')).toBeInTheDocument();
  });

  it('shows task completion count badge', () => {
    render(
      <RightPanel
        tasks={mockTasks}
        resources={[]}
        contextUsage={null}
        searchBudget={null}
        visible={true}
        projectUuid={null}
        onToggle={vi.fn()}
        onViewReport={vi.fn()}
      />
    );
    // CollapsiblePanel renders badge with "done/total"
    expect(screen.getByText('1/3')).toBeInTheDocument();
  });

  it('shows "No tasks yet" when empty', () => {
    render(
      <RightPanel
        tasks={[]}
        resources={[]}
        contextUsage={null}
        searchBudget={null}
        visible={true}
        projectUuid={null}
        onToggle={vi.fn()}
        onViewReport={vi.fn()}
      />
    );
    expect(screen.getByText('No tasks yet')).toBeInTheDocument();
  });

  it('renders context gauge with data', () => {
    render(
      <RightPanel
        tasks={[]}
        resources={[]}
        contextUsage={mockContext}
        searchBudget={null}
        visible={true}
        projectUuid={null}
        onToggle={vi.fn()}
        onViewReport={vi.fn()}
      />
    );
    expect(screen.getByText(/50k/)).toBeInTheDocument();
    expect(screen.getByText(/200k/)).toBeInTheDocument();
  });

  it('renders context gauge placeholder when null', () => {
    render(
      <RightPanel
        tasks={[]}
        resources={[]}
        contextUsage={null}
        searchBudget={null}
        visible={true}
        projectUuid={null}
        onToggle={vi.fn()}
        onViewReport={vi.fn()}
      />
    );
    expect(screen.getByText('Context: --')).toBeInTheDocument();
  });

  it('renders search budget gauge', () => {
    render(
      <RightPanel
        tasks={[]}
        resources={[]}
        contextUsage={null}
        searchBudget={mockSearchBudget}
        visible={true}
        projectUuid={null}
        onToggle={vi.fn()}
        onViewReport={vi.fn()}
      />
    );
    expect(screen.getByText(/Searches:/)).toBeInTheDocument();
  });

  it('renders default search budget when null', () => {
    render(
      <RightPanel
        tasks={[]}
        resources={[]}
        contextUsage={null}
        searchBudget={null}
        visible={true}
        projectUuid={null}
        onToggle={vi.fn()}
        onViewReport={vi.fn()}
      />
    );
    expect(screen.getByText('Searches: 0 / 25')).toBeInTheDocument();
  });

  it('does not render resources section (resources are now in FileTree)', () => {
    render(
      <RightPanel
        tasks={mockTasks}
        resources={mockResources}
        contextUsage={null}
        searchBudget={null}
        visible={true}
        projectUuid={null}
        onToggle={vi.fn()}
        onViewReport={vi.fn()}
      />
    );
    // Resources section was removed — resources now appear as files in the workspace
    expect(screen.queryByText('No resources yet')).not.toBeInTheDocument();
  });

  it('does not render paper export buttons (papers are now in FileTree)', () => {
    render(
      <RightPanel
        tasks={[]}
        resources={[
          { title: 'My Paper', type: 'paper', id: 'paper-1', url: '' },
        ]}
        contextUsage={null}
        searchBudget={null}
        visible={true}
        projectUuid={null}
        onToggle={vi.fn()}
        onViewReport={vi.fn()}
      />
    );
    // Paper export buttons were removed — papers are now files in workspace
    expect(screen.queryByText('.md')).not.toBeInTheDocument();
    expect(screen.queryByText('.tex')).not.toBeInTheDocument();
  });

  it('shows task count badge on collapsed rail', () => {
    render(
      <RightPanel
        tasks={mockTasks}
        resources={[]}
        contextUsage={null}
        searchBudget={null}
        visible={false}
        projectUuid={null}
        onToggle={vi.fn()}
        onViewReport={vi.fn()}
      />
    );
    const todosButton = screen.getByTitle('Todos');
    const badge = todosButton.querySelector('span');
    expect(badge?.textContent).toBe('3');
  });

  it('has search budget settings button', () => {
    render(
      <RightPanel
        tasks={[]}
        resources={[]}
        contextUsage={null}
        searchBudget={null}
        visible={true}
        projectUuid={null}
        onToggle={vi.fn()}
        onViewReport={vi.fn()}
      />
    );
    expect(screen.getByTitle('Change search budget')).toBeInTheDocument();
  });
});

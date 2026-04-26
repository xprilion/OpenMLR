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

  it('renders toggle button when not visible', () => {
    render(
      <RightPanel
        tasks={mockTasks}
        resources={mockResources}
        contextUsage={mockContext}
        searchBudget={null}
        visible={false}
        onToggle={vi.fn()}
        onViewReport={vi.fn()}
      />
    );
    expect(screen.getByTitle('Tasks & resources')).toBeInTheDocument();
  });

  it('renders tasks when visible', () => {
    render(
      <RightPanel
        tasks={mockTasks}
        resources={[]}
        contextUsage={null}
        searchBudget={null}
        visible={true}
        onToggle={vi.fn()}
        onViewReport={vi.fn()}
      />
    );
    expect(screen.getByText('Read papers')).toBeInTheDocument();
    expect(screen.getByText('Implement model')).toBeInTheDocument();
    expect(screen.getByText('Write report')).toBeInTheDocument();
  });

  it('shows task count', () => {
    render(
      <RightPanel
        tasks={mockTasks}
        resources={[]}
        contextUsage={null}
        searchBudget={null}
        visible={true}
        onToggle={vi.fn()}
        onViewReport={vi.fn()}
      />
    );
    expect(screen.getByText('Tasks (1/3)')).toBeInTheDocument();
  });

  it('shows "No tasks yet" when empty', () => {
    render(
      <RightPanel
        tasks={[]}
        resources={[]}
        contextUsage={null}
        searchBudget={null}
        visible={true}
        onToggle={vi.fn()}
        onViewReport={vi.fn()}
      />
    );
    expect(screen.getByText('No tasks yet')).toBeInTheDocument();
    expect(screen.getByText('No resources yet')).toBeInTheDocument();
  });

  it('renders context gauge', () => {
    render(
      <RightPanel
        tasks={[]}
        resources={[]}
        contextUsage={mockContext}
        searchBudget={null}
        visible={true}
        onToggle={vi.fn()}
        onViewReport={vi.fn()}
      />
    );
    expect(screen.getByText(/50k/)).toBeInTheDocument();
    expect(screen.getByText(/200k/)).toBeInTheDocument();
  });

  it('renders search budget gauge', () => {
    render(
      <RightPanel
        tasks={[]}
        resources={[]}
        contextUsage={null}
        searchBudget={mockSearchBudget}
        visible={true}
        onToggle={vi.fn()}
        onViewReport={vi.fn()}
      />
    );
    expect(screen.getByText(/Searches:/)).toBeInTheDocument();
  });

  it('renders resources', () => {
    render(
      <RightPanel
        tasks={mockTasks}
        resources={mockResources}
        contextUsage={null}
        searchBudget={null}
        visible={true}
        onToggle={vi.fn()}
        onViewReport={vi.fn()}
      />
    );
    expect(screen.getByText('Dataset X')).toBeInTheDocument();
  });

  it('renders paper resource with export buttons', () => {
    render(
      <RightPanel
        tasks={[]}
        resources={[
          { title: 'My Paper', type: 'paper', id: 'paper-1', url: '' },
        ]}
        contextUsage={null}
        searchBudget={null}
        visible={true}
        onToggle={vi.fn()}
        onViewReport={vi.fn()}
      />
    );
    expect(screen.getByText('.md')).toBeInTheDocument();
    expect(screen.getByText('.tex')).toBeInTheDocument();
  });

  it('hides toggle badge when no tasks and visible', () => {
    render(
      <RightPanel
        tasks={[]}
        resources={[]}
        contextUsage={null}
        searchBudget={null}
        visible={false}
        onToggle={vi.fn()}
        onViewReport={vi.fn()}
      />
    );
    expect(screen.queryByTitle('Tasks & resources')).not.toBeInTheDocument();
  });

  it('shows toggle badge with task count when collapsed with tasks', () => {
    render(
      <RightPanel
        tasks={mockTasks}
        resources={[]}
        contextUsage={null}
        searchBudget={null}
        visible={false}
        onToggle={vi.fn()}
        onViewReport={vi.fn()}
      />
    );
    const badge = document.querySelector('.toggle-badge');
    expect(badge?.textContent).toBe('3');
  });
});

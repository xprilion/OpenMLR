import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ProjectSelector } from '../components/ProjectSelector';
import type { Project } from '../types';

const mockProjects: Project[] = [
  {
    id: 1,
    uuid: 'proj-1',
    name: 'ML Research',
    slug: 'ml-research',
    description: 'Machine learning research',
    workspace_path: '/tmp/ml',
    status: 'active',
    settings: {},
    created_at: '2024-01-01',
    updated_at: '2024-01-01',
    conversation_count: 3,
  },
  {
    id: 2,
    uuid: 'proj-2',
    name: 'NLP Project',
    slug: 'nlp-project',
    description: null,
    workspace_path: '/tmp/nlp',
    status: 'active',
    settings: {},
    created_at: '2024-01-02',
    updated_at: '2024-01-02',
    conversation_count: 1,
  },
];

describe('ProjectSelector', () => {
  it('renders active project name', () => {
    render(
      <ProjectSelector
        projects={mockProjects}
        activeProject={mockProjects[0]}
        onSelectProject={vi.fn()}
        onNewProject={vi.fn()}
        onManageProjects={vi.fn()}
      />
    );
    expect(screen.getByText('ML Research')).toBeInTheDocument();
  });

  it('renders "Project" when no active project', () => {
    render(
      <ProjectSelector
        projects={mockProjects}
        activeProject={null}
        onSelectProject={vi.fn()}
        onNewProject={vi.fn()}
        onManageProjects={vi.fn()}
      />
    );
    expect(screen.getByText('Project')).toBeInTheDocument();
  });

  it('does NOT show "All Conversations" option', () => {
    render(
      <ProjectSelector
        projects={mockProjects}
        activeProject={mockProjects[0]}
        onSelectProject={vi.fn()}
        onNewProject={vi.fn()}
        onManageProjects={vi.fn()}
      />
    );
    fireEvent.click(screen.getByText('ML Research'));
    expect(screen.queryByText('All Conversations')).not.toBeInTheDocument();
  });

  it('shows all projects in dropdown', () => {
    render(
      <ProjectSelector
        projects={mockProjects}
        activeProject={mockProjects[0]}
        onSelectProject={vi.fn()}
        onNewProject={vi.fn()}
        onManageProjects={vi.fn()}
      />
    );
    fireEvent.click(screen.getByText('ML Research'));
    expect(screen.getByText('NLP Project')).toBeInTheDocument();
  });

  it('highlights active project', () => {
    render(
      <ProjectSelector
        projects={mockProjects}
        activeProject={mockProjects[0]}
        onSelectProject={vi.fn()}
        onNewProject={vi.fn()}
        onManageProjects={vi.fn()}
      />
    );
    fireEvent.click(screen.getByText('ML Research'));
    // The active project button in dropdown should have primary styling
    const buttons = screen.getAllByRole('button');
    const activeButton = buttons.find((b) => b.textContent?.includes('ML Research') && b.className.includes('bg-primary'));
    expect(activeButton).toBeTruthy();
  });

  it('calls onSelectProject when project clicked', () => {
    const onSelect = vi.fn();
    render(
      <ProjectSelector
        projects={mockProjects}
        activeProject={mockProjects[0]}
        onSelectProject={onSelect}
        onNewProject={vi.fn()}
        onManageProjects={vi.fn()}
      />
    );
    fireEvent.click(screen.getByText('ML Research'));
    fireEvent.click(screen.getByText('NLP Project'));
    expect(onSelect).toHaveBeenCalledWith(mockProjects[1]);
  });

  it('calls onSelectProject with Project, never null', () => {
    const onSelect = vi.fn();
    render(
      <ProjectSelector
        projects={mockProjects}
        activeProject={mockProjects[0]}
        onSelectProject={onSelect}
        onNewProject={vi.fn()}
        onManageProjects={vi.fn()}
      />
    );
    fireEvent.click(screen.getByText('ML Research'));
    fireEvent.click(screen.getByText('NLP Project'));
    // Verify the argument is a Project object, not null
    expect(onSelect).toHaveBeenCalledTimes(1);
    expect(onSelect.mock.calls[0][0]).not.toBeNull();
    expect(onSelect.mock.calls[0][0].uuid).toBe('proj-2');
  });

  it('shows "New Project" button in dropdown', () => {
    render(
      <ProjectSelector
        projects={mockProjects}
        activeProject={mockProjects[0]}
        onSelectProject={vi.fn()}
        onNewProject={vi.fn()}
        onManageProjects={vi.fn()}
      />
    );
    fireEvent.click(screen.getByText('ML Research'));
    expect(screen.getByText('New Project')).toBeInTheDocument();
  });

  it('calls onNewProject when "New Project" clicked', () => {
    const onNew = vi.fn();
    render(
      <ProjectSelector
        projects={mockProjects}
        activeProject={mockProjects[0]}
        onSelectProject={vi.fn()}
        onNewProject={onNew}
        onManageProjects={vi.fn()}
      />
    );
    fireEvent.click(screen.getByText('ML Research'));
    fireEvent.click(screen.getByText('New Project'));
    expect(onNew).toHaveBeenCalled();
  });

  it('shows conversation count per project', () => {
    render(
      <ProjectSelector
        projects={mockProjects}
        activeProject={mockProjects[0]}
        onSelectProject={vi.fn()}
        onNewProject={vi.fn()}
        onManageProjects={vi.fn()}
      />
    );
    fireEvent.click(screen.getByText('ML Research'));
    expect(screen.getByText('3')).toBeInTheDocument();
    expect(screen.getByText('1')).toBeInTheDocument();
  });

  it('shows "No projects yet" when empty', () => {
    render(
      <ProjectSelector
        projects={[]}
        activeProject={null}
        onSelectProject={vi.fn()}
        onNewProject={vi.fn()}
        onManageProjects={vi.fn()}
      />
    );
    fireEvent.click(screen.getByText('Project'));
    expect(screen.getByText('No projects yet')).toBeInTheDocument();
  });

  it('shows Manage Projects when projects exist', () => {
    render(
      <ProjectSelector
        projects={mockProjects}
        activeProject={mockProjects[0]}
        onSelectProject={vi.fn()}
        onNewProject={vi.fn()}
        onManageProjects={vi.fn()}
      />
    );
    fireEvent.click(screen.getByText('ML Research'));
    expect(screen.getByText('Manage Projects')).toBeInTheDocument();
  });

  it('closes dropdown on project select', () => {
    render(
      <ProjectSelector
        projects={mockProjects}
        activeProject={mockProjects[0]}
        onSelectProject={vi.fn()}
        onNewProject={vi.fn()}
        onManageProjects={vi.fn()}
      />
    );
    fireEvent.click(screen.getByText('ML Research'));
    expect(screen.getByText('NLP Project')).toBeInTheDocument();
    fireEvent.click(screen.getByText('NLP Project'));
    // Dropdown should be closed
    expect(screen.queryByText('New Project')).not.toBeInTheDocument();
  });
});

import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { FigureStudio } from './FigureStudio';
import { api } from '../../api';
import type { FigureArtifact } from './types';

vi.mock('../../api', () => ({
  api: {
    listFigures: vi.fn(),
    generateFigure: vi.fn(),
    getFigure: vi.fn(),
    deleteFigure: vi.fn(),
    createMultiPanelLayout: vi.fn(),
  },
}));

const mockFigure1: FigureArtifact = {
  id: 'fig_loss_01',
  project_id: 'proj_test',
  title: 'Training Loss Curve',
  caption: 'Validation loss across 2000 steps.',
  plot_type: 'loss_curve',
  style_theme: 'neurips',
  palette: 'colorblind',
  python_script: 'import matplotlib.pyplot as plt\nplt.plot([1, 2], [3, 4])',
  latex_snippet: '\\begin{figure}\n\\includegraphics{fig.pdf}\n\\end{figure}',
  tikz_code: '\\begin{tikzpicture}\n\\end{tikzpicture}',
  svg_preview: '<svg><text>Mock Plot</text></svg>',
  created_at: '2026-08-20T12:00:00Z',
};

const mockFigure2: FigureArtifact = {
  id: 'fig_bar_02',
  project_id: 'proj_test',
  title: 'Ablation Accuracy Comparison',
  caption: 'Downstream performance across model ablations.',
  plot_type: 'ablation_bar',
  style_theme: 'icml',
  palette: 'viridis',
  python_script: 'import matplotlib.pyplot as plt\nplt.bar([1, 2], [3, 4])',
  latex_snippet: '\\begin{figure}\n\\includegraphics{bar.pdf}\n\\end{figure}',
  tikz_code: '\\begin{tikzpicture}\n\\end{tikzpicture}',
  svg_preview: '<svg><text>Mock Bar</text></svg>',
  created_at: '2026-08-20T12:05:00Z',
};

describe('FigureStudio Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders studio title and loads figures', async () => {
    vi.mocked(api.listFigures).mockResolvedValue({ figures: [mockFigure1, mockFigure2], total_count: 2 });

    render(<FigureStudio projectId="proj_test" />);

    expect(screen.getByText('Publication Figure Studio')).toBeInTheDocument();
    await waitFor(() => {
      expect(api.listFigures).toHaveBeenCalledWith('proj_test');
      expect(screen.getByText('Training Loss Curve')).toBeInTheDocument();
      expect(screen.getByText('Ablation Accuracy Comparison')).toBeInTheDocument();
    });
  });

  it('opens generate figure modal and submits', async () => {
    vi.mocked(api.listFigures).mockResolvedValue({ figures: [], total_count: 0 });
    vi.mocked(api.generateFigure).mockResolvedValue({ figure: mockFigure1 });

    render(<FigureStudio projectId="proj_test" />);

    const generateBtns = screen.getAllByRole('button', { name: /Generate Figure/i });
    fireEvent.click(generateBtns[0]);

    expect(screen.getByText('Generate Publication Figure')).toBeInTheDocument();

    const titleInput = screen.getByLabelText(/Figure Title \*/i);
    fireEvent.change(titleInput, { target: { value: 'Scaling Law Plot' } });

    const submitBtns = screen.getAllByRole('button', { name: /Generate Figure/i });
    fireEvent.click(submitBtns[submitBtns.length - 1]);

    await waitFor(() => {
      expect(api.generateFigure).toHaveBeenCalled();
    });
  });

  it('deletes a figure when clicking delete button', async () => {
    vi.mocked(api.listFigures).mockResolvedValue({ figures: [mockFigure1], total_count: 1 });
    vi.mocked(api.deleteFigure).mockResolvedValue({ success: true });

    render(<FigureStudio projectId="proj_test" />);

    await waitFor(() => {
      expect(screen.getByText('Training Loss Curve')).toBeInTheDocument();
    });

    const deleteBtn = screen.getByLabelText('Delete figure');
    fireEvent.click(deleteBtn);

    await waitFor(() => {
      expect(api.deleteFigure).toHaveBeenCalledWith('proj_test', 'fig_loss_01');
    });
  });

  it('allows multi-panel selection and opens multi-panel modal', async () => {
    vi.mocked(api.listFigures).mockResolvedValue({ figures: [mockFigure1, mockFigure2], total_count: 2 });
    vi.mocked(api.createMultiPanelLayout).mockResolvedValue({
      title: 'Combined Evaluation',
      caption: 'Overview of all experiments.',
      figure_count: 2,
      latex_code: '\\begin{figure*}\\end{figure*}',
      included_figures: [mockFigure1, mockFigure2],
    });

    render(<FigureStudio projectId="proj_test" />);

    await waitFor(() => {
      expect(screen.getByText('Training Loss Curve')).toBeInTheDocument();
    });

    const check1 = screen.getByLabelText(`Select ${mockFigure1.title} for multi-panel`);
    const check2 = screen.getByLabelText(`Select ${mockFigure2.title} for multi-panel`);

    fireEvent.click(check1);
    fireEvent.click(check2);

    const multiBtn = screen.getByRole('button', { name: /Multi-Panel \(2\)/i });
    expect(multiBtn).toBeInTheDocument();
    fireEvent.click(multiBtn);

    expect(screen.getByText('Multi-Panel Subfigure Grid Layout')).toBeInTheDocument();

    const submitMultiBtn = screen.getByRole('button', { name: /Create Subfigure Grid/i });
    fireEvent.click(submitMultiBtn);

    await waitFor(() => {
      expect(api.createMultiPanelLayout).toHaveBeenCalledWith('proj_test', expect.objectContaining({
        figure_ids: ['fig_loss_01', 'fig_bar_02'],
      }));
    });
  });
});

export type PlotType =
  | 'loss_curve'
  | 'ablation_bar'
  | 'pareto_frontier'
  | 'confusion_matrix'
  | 'radar_benchmark'
  | 'heatmap';

export type StyleTheme = 'neurips' | 'icml' | 'iclr' | 'cvpr' | 'dark';

export type ColorPalette = 'colorblind' | 'viridis' | 'muted' | 'deep' | 'tableau';

export interface FigureArtifact {
  id: string;
  project_id: string;
  title: string;
  caption: string;
  plot_type: PlotType;
  style_theme: StyleTheme;
  palette: ColorPalette;
  python_script: string;
  latex_snippet: string;
  tikz_code: string;
  svg_preview: string;
  created_at: string;
}

export interface MultiPanelResult {
  title: string;
  caption: string;
  figure_count: number;
  latex_code: string;
  included_figures: FigureArtifact[];
}

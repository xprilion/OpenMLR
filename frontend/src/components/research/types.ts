export interface PaperNode {
  id: string;
  title: string;
  authors: string[];
  year: number;
  venue?: string;
  citations: number;
  abstract: string;
  claims: string[];
  methodology: string;
  dataset: string;
  metric: string;
  baseline: string;
  gap: string;
  cluster: 'Architecture' | 'Optimization' | 'Data & Evaluation' | 'Theoretical Analysis';
  pdfUrl?: string;
  doi?: string;
  x?: number;
  y?: number;
}

export interface CitationEdge {
  id: string;
  source: string;
  target: string;
  type: 'cites' | 'extends' | 'compares_against';
}

export interface LiteratureMatrixRow {
  id: string;
  title: string;
  year: number;
  authors: string;
  method: string;
  dataset: string;
  metric: string;
  baseline: string;
  gap: string;
}

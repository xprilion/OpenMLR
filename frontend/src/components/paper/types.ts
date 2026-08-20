export type PaperViewMode = 'split' | 'editor' | 'preview' | 'diff';

export interface PaperSection {
  id: string;
  title: string;
  content: string;
  level: number;
}

export interface PaperMetadata {
  title: string;
  authors: string[];
  abstract: string;
  keywords: string[];
  venue?: string;
  date?: string;
}

export interface BibtexEntry {
  id: string;
  citationKey: string;
  entryType: string;
  title: string;
  author: string;
  year: string;
  journal?: string;
  booktitle?: string;
  doi?: string;
  raw: string;
}

export interface SectionDiff {
  id: string;
  sectionId: string;
  sectionTitle: string;
  originalText: string;
  proposedText: string;
  reason: string;
  status: 'pending' | 'applied' | 'rejected';
}

export interface PaperDocument {
  metadata: PaperMetadata;
  sections: PaperSection[];
  bibtexEntries: BibtexEntry[];
  rawLatex?: string;
}

import { useMemo } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import type { PaperMetadata, PaperSection, BibtexEntry } from './types';

export interface LatexPreviewProps {
  metadata: PaperMetadata;
  sections: PaperSection[];
  bibtexEntries: BibtexEntry[];
}

export function LatexPreview({
  metadata,
  sections,
  bibtexEntries,
}: Readonly<LatexPreviewProps>) {
  const formattedSections = useMemo(() => {
    return sections.map((sec, idx) => {
      // Replace LaTeX citation markers \cite{key} with clickable badges
      let processedContent = sec.content;
      processedContent = processedContent.replace(/\\cite\{([^}]+)\}/g, (_match, key: string) => {
        const entry = bibtexEntries.find((b) => b.citationKey === key.trim());
        const firstAuthor = entry ? entry.author.replace(/[,;].*$/, '').trim() : '';
        const label = entry ? `${firstAuthor} et al., ${entry.year}` : key;
        return ` [**${label}**](#ref-${key.trim()})`;
      });

      return {
        ...sec,
        displayNumber: idx + 1,
        processedContent,
      };
    });
  }, [sections, bibtexEntries]);

  return (
    <div className="flex-1 h-full overflow-y-auto bg-surface p-6 sm:p-10 text-text font-serif leading-relaxed select-text">
      {/* Paper Container (Academic Style) */}
      <article className="max-w-3xl mx-auto bg-bg border border-border rounded-xl p-8 sm:p-12 shadow-sm font-sans">
        {/* Header / Title */}
        <header className="text-center mb-8 border-b border-border pb-6">
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-text mb-3">
            {metadata.title || 'Untitled Research Paper'}
          </h1>
          {metadata.authors.length > 0 && (
            <p className="text-sm font-medium text-text-dim mb-2">
              {metadata.authors.join('  •  ')}
            </p>
          )}
          {metadata.venue && (
            <span className="inline-block text-xs uppercase tracking-wider bg-primary/10 text-primary px-2.5 py-1 rounded-full font-semibold">
              {metadata.venue}
            </span>
          )}
        </header>

        {/* Abstract */}
        {metadata.abstract && (
          <section className="mb-8 px-6 py-4 bg-surface rounded-lg border border-border/60">
            <h2 className="text-xs font-bold uppercase tracking-wider text-primary mb-2 text-center">
              Abstract
            </h2>
            <p className="text-sm text-text/90 italic leading-relaxed text-justify">
              {metadata.abstract}
            </p>
            {metadata.keywords.length > 0 && (
              <div className="mt-3 flex flex-wrap items-center gap-1.5 pt-2 border-t border-border/40">
                <span className="text-xs font-semibold text-text-dim">Keywords:</span>
                {metadata.keywords.map((kw) => (
                  <span key={kw} className="text-xs text-text-dim bg-bg px-2 py-0.5 rounded border border-border">
                    {kw}
                  </span>
                ))}
              </div>
            )}
          </section>
        )}

        {/* Sections */}
        <main className="flex flex-col gap-6">
          {formattedSections.map((sec) => (
            <section key={sec.id} className="prose prose-invert max-w-none">
              <h3 className="text-lg font-bold text-text mb-2 pb-1 border-b border-border/40 flex items-center gap-2">
                <span className="text-primary font-mono text-sm">{sec.displayNumber}.</span>
                <span>{sec.title}</span>
              </h3>
              <div className="text-sm leading-relaxed text-text/90">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {sec.processedContent}
                </ReactMarkdown>
              </div>
            </section>
          ))}
        </main>

        {/* References / Bibliography */}
        {bibtexEntries.length > 0 && (
          <footer className="mt-12 pt-8 border-t-2 border-border">
            <h3 className="text-lg font-bold text-text mb-4">References</h3>
            <ol className="flex flex-col gap-3 text-xs text-text-dim list-decimal pl-4">
              {bibtexEntries.map((bib) => (
                <li key={bib.id} id={`ref-${bib.citationKey}`} className="leading-normal">
                  <span className="font-semibold text-text">[{bib.citationKey}]</span>{' '}
                  <span className="text-text">{bib.author}</span> ({bib.year}).{' '}
                  <span className="italic text-text/90">"{bib.title}"</span>.{' '}
                  {bib.journal && <span>{bib.journal}.</span>}
                  {bib.booktitle && <span>In {bib.booktitle}.</span>}
                  {bib.doi && (
                    <span className="ml-1 text-primary hover:underline font-mono">
                      doi:{bib.doi}
                    </span>
                  )}
                </li>
              ))}
            </ol>
          </footer>
        )}
      </article>
    </div>
  );
}

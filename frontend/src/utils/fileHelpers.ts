export const IMAGE_EXTENSIONS = new Set(['.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp', '.bmp', '.ico']);

export function isImageFile(path: string): boolean {
  const ext = '.' + (path.split('.').pop()?.toLowerCase() || '');
  return IMAGE_EXTENSIONS.has(ext);
}

/** Map file extensions to Monaco language IDs. */
export function detectLanguage(path: string): string {
  const ext = path.split('.').pop()?.toLowerCase() || '';
  const map: Record<string, string> = {
    py: 'python',
    js: 'javascript',
    ts: 'typescript',
    tsx: 'typescript',
    jsx: 'javascript',
    json: 'json',
    md: 'markdown',
    yaml: 'yaml',
    yml: 'yaml',
    toml: 'toml',
    sh: 'shell',
    bash: 'shell',
    html: 'html',
    css: 'css',
    sql: 'sql',
    r: 'r',
    txt: 'plaintext',
    csv: 'plaintext',
    log: 'plaintext',
    cfg: 'ini',
    ini: 'ini',
    tex: 'latex',
    bib: 'bibtex',
    xml: 'xml',
    dockerfile: 'dockerfile',
  };
  return map[ext] || 'plaintext';
}

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { EditorPanel } from '../components/EditorPanel';
import type { OpenFile } from '../types';

// Mock the Monaco Editor — it requires a browser environment with Web Workers
// which jsdom doesn't provide. We mock it as a simple div.
vi.mock('@monaco-editor/react', () => ({
  default: ({ value, language }: { value: string; language: string }) => (
    <div data-testid="monaco-editor" data-language={language}>
      {value}
    </div>
  ),
}));

const pythonFile: OpenFile = {
  path: 'code/train.py',
  content: 'import torch\nprint("hello")',
  language: 'python',
};

const markdownFile: OpenFile = {
  path: 'papers/draft.md',
  content: '# My Paper\n\nAbstract goes here.',
  language: 'markdown',
};

const jsonFile: OpenFile = {
  path: 'config.json',
  content: '{"key": "value"}',
  language: 'json',
};

describe('EditorPanel', () => {
  // ── Empty state ──

  it('renders empty state when no files are open', () => {
    render(
      <EditorPanel
        openFiles={[]}
        activeFilePath={null}
        onActivateFile={vi.fn()}
        onCloseFile={vi.fn()}
      />
    );
    expect(screen.getByText(/Select a file from the Files panel/)).toBeInTheDocument();
  });

  it('does not render Monaco editor when no files are open', () => {
    render(
      <EditorPanel
        openFiles={[]}
        activeFilePath={null}
        onActivateFile={vi.fn()}
        onCloseFile={vi.fn()}
      />
    );
    expect(screen.queryByTestId('monaco-editor')).not.toBeInTheDocument();
  });

  // ── Single file ──

  it('renders a single file tab with the filename', () => {
    render(
      <EditorPanel
        openFiles={[pythonFile]}
        activeFilePath="code/train.py"
        onActivateFile={vi.fn()}
        onCloseFile={vi.fn()}
      />
    );
    expect(screen.getByText('train.py')).toBeInTheDocument();
  });

  it('renders Monaco editor with file content', () => {
    render(
      <EditorPanel
        openFiles={[pythonFile]}
        activeFilePath="code/train.py"
        onActivateFile={vi.fn()}
        onCloseFile={vi.fn()}
      />
    );
    const editor = screen.getByTestId('monaco-editor');
    expect(editor).toBeInTheDocument();
    expect(editor.textContent).toContain('import torch');
    expect(editor).toHaveAttribute('data-language', 'python');
  });

  // ── Multiple files ──

  it('renders multiple file tabs', () => {
    render(
      <EditorPanel
        openFiles={[pythonFile, markdownFile, jsonFile]}
        activeFilePath="code/train.py"
        onActivateFile={vi.fn()}
        onCloseFile={vi.fn()}
      />
    );
    expect(screen.getByText('train.py')).toBeInTheDocument();
    expect(screen.getByText('draft.md')).toBeInTheDocument();
    expect(screen.getByText('config.json')).toBeInTheDocument();
  });

  it('shows the active file content in the editor', () => {
    render(
      <EditorPanel
        openFiles={[pythonFile, markdownFile]}
        activeFilePath="papers/draft.md"
        onActivateFile={vi.fn()}
        onCloseFile={vi.fn()}
      />
    );
    const editor = screen.getByTestId('monaco-editor');
    expect(editor.textContent).toContain('My Paper');
    expect(editor).toHaveAttribute('data-language', 'markdown');
  });

  // ── Tab interactions ──

  it('calls onActivateFile when clicking a tab', () => {
    const onActivate = vi.fn();
    render(
      <EditorPanel
        openFiles={[pythonFile, markdownFile]}
        activeFilePath="code/train.py"
        onActivateFile={onActivate}
        onCloseFile={vi.fn()}
      />
    );
    fireEvent.click(screen.getByText('draft.md'));
    expect(onActivate).toHaveBeenCalledWith('papers/draft.md');
  });

  it('calls onCloseFile when clicking close button on a tab', () => {
    const onClose = vi.fn();
    render(
      <EditorPanel
        openFiles={[pythonFile, markdownFile]}
        activeFilePath="code/train.py"
        onActivateFile={vi.fn()}
        onCloseFile={onClose}
      />
    );
    // Each tab has a Close button with title="Close"
    const closeButtons = screen.getAllByTitle('Close');
    // Close the second tab (draft.md)
    fireEvent.click(closeButtons[1]);
    expect(onClose).toHaveBeenCalledWith('papers/draft.md');
  });

  it('close button does not activate the tab', () => {
    const onActivate = vi.fn();
    const onClose = vi.fn();
    render(
      <EditorPanel
        openFiles={[pythonFile, markdownFile]}
        activeFilePath="code/train.py"
        onActivateFile={onActivate}
        onCloseFile={onClose}
      />
    );
    const closeButtons = screen.getAllByTitle('Close');
    fireEvent.click(closeButtons[0]);
    // onCloseFile should be called but not onActivateFile
    expect(onClose).toHaveBeenCalledWith('code/train.py');
    expect(onActivate).not.toHaveBeenCalled();
  });

  // ── Tab shows full path as tooltip ──

  it('shows full file path as tooltip on tab', () => {
    render(
      <EditorPanel
        openFiles={[pythonFile]}
        activeFilePath="code/train.py"
        onActivateFile={vi.fn()}
        onCloseFile={vi.fn()}
      />
    );
    expect(screen.getByTitle('code/train.py')).toBeInTheDocument();
  });

  // ── No active file but files open ──

  it('shows select-a-tab message when no file is active but files are open', () => {
    render(
      <EditorPanel
        openFiles={[pythonFile]}
        activeFilePath={null}
        onActivateFile={vi.fn()}
        onCloseFile={vi.fn()}
      />
    );
    expect(screen.getByText(/Select a tab above/)).toBeInTheDocument();
  });

  // ── Active file highlighting ──

  it('highlights the active tab with bg-bg class', () => {
    render(
      <EditorPanel
        openFiles={[pythonFile, markdownFile]}
        activeFilePath="code/train.py"
        onActivateFile={vi.fn()}
        onCloseFile={vi.fn()}
      />
    );
    const trainTab = screen.getByTitle('code/train.py').closest('div');
    const draftTab = screen.getByTitle('papers/draft.md').closest('div');
    expect(trainTab?.className).toContain('bg-bg');
    expect(draftTab?.className).not.toContain('bg-bg');
  });
});

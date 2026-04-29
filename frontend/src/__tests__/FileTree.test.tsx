import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { FileTree } from '../components/FileTree';

vi.mock('../api', () => ({
  api: {
    listFiles: vi.fn().mockResolvedValue({
      entries: [
        { name: 'code', path: 'code', is_dir: true, size: null, modified: 1000 },
        { name: 'train.py', path: 'train.py', is_dir: false, size: 1234, modified: 2000 },
        { name: 'README.md', path: 'README.md', is_dir: false, size: 500, modified: 3000 },
      ],
    }),
    readFile: vi.fn().mockResolvedValue({ content: 'file content here' }),
  },
}));

describe('FileTree', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders file entries after loading', async () => {
    render(<FileTree projectUuid="proj-1" />);

    await waitFor(() => {
      expect(screen.getByText('train.py')).toBeInTheDocument();
      expect(screen.getByText('README.md')).toBeInTheDocument();
      expect(screen.getByText('code')).toBeInTheDocument();
    });
  });

  it('shows loading state initially', () => {
    render(<FileTree projectUuid="proj-1" />);
    expect(screen.getByText('Loading files...')).toBeInTheDocument();
  });

  it('renders refresh button', async () => {
    render(<FileTree projectUuid="proj-1" />);
    await waitFor(() => {
      expect(screen.getByTitle('Refresh')).toBeInTheDocument();
    });
  });

  it('shows "No files yet" when directory is empty', async () => {
    const { api } = await import('../api');
    vi.mocked(api.listFiles).mockResolvedValueOnce({ entries: [] });

    render(<FileTree projectUuid="proj-1" />);

    await waitFor(() => {
      expect(screen.getByText('No files yet')).toBeInTheDocument();
    });
  });

  it('calls onFileSelect when a file is clicked', async () => {
    const onFileSelect = vi.fn();
    render(<FileTree projectUuid="proj-1" onFileSelect={onFileSelect} />);

    await waitFor(() => {
      expect(screen.getByText('train.py')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('train.py'));

    await waitFor(() => {
      expect(onFileSelect).toHaveBeenCalledWith('train.py', 'file content here');
    });
  });

  it('fetches file content via api.readFile when file is clicked', async () => {
    const { api } = await import('../api');
    render(<FileTree projectUuid="proj-1" onFileSelect={vi.fn()} />);

    await waitFor(() => {
      expect(screen.getByText('README.md')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('README.md'));

    await waitFor(() => {
      expect(api.readFile).toHaveBeenCalledWith('proj-1', 'README.md');
    });
  });

  it('does not have an inline file preview panel', async () => {
    render(<FileTree projectUuid="proj-1" onFileSelect={vi.fn()} />);

    await waitFor(() => {
      expect(screen.getByText('train.py')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('train.py'));

    // There should be no inline preview with <pre> content
    await waitFor(() => {
      expect(screen.queryByText('file content here')).not.toBeInTheDocument();
    });
  });

  it('calls api.listFiles with the project UUID', async () => {
    const { api } = await import('../api');
    render(<FileTree projectUuid="my-proj-uuid" />);

    await waitFor(() => {
      expect(api.listFiles).toHaveBeenCalledWith('my-proj-uuid', '');
    });
  });

  it('clicking a directory does not call onFileSelect', async () => {
    const onFileSelect = vi.fn();
    render(<FileTree projectUuid="proj-1" onFileSelect={onFileSelect} />);

    await waitFor(() => {
      expect(screen.getByText('code')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('code'));

    // Directories toggle expansion, they don't trigger onFileSelect
    expect(onFileSelect).not.toHaveBeenCalled();
  });

  it('renders Files header', async () => {
    render(<FileTree projectUuid="proj-1" />);

    await waitFor(() => {
      expect(screen.getByText('Files')).toBeInTheDocument();
    });
  });
});

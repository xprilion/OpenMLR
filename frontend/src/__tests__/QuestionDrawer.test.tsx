import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QuestionDrawer } from '../components/QuestionDrawer';
import { api } from '../api';
import type { QuestionsPayload } from '../types';

vi.mock('../api', () => ({
  api: {
    submitAnswers: vi.fn(),
  },
}));

const defaultPayload: QuestionsPayload = {
  questions: [
    {
      id: 'q1',
      question: 'What is your preference?',
      options: [
        { label: 'Option A', description: 'First option' },
        { label: 'Option B' },
        { label: 'Option C', description: 'Third option' },
      ],
    },
    {
      id: 'q2',
      question: 'Choose a framework.',
      options: [
        { label: 'PyTorch' },
        { label: 'JAX', description: 'Functional approach' },
      ],
    },
  ],
  context: 'Project setup questions',
};

describe('QuestionDrawer', () => {
  it('renders context title', () => {
    vi.mocked(api.submitAnswers).mockResolvedValue({});
    render(
      <QuestionDrawer payload={defaultPayload} onDone={vi.fn()} onClose={vi.fn()} />
    );
    expect(screen.getByText('Project setup questions')).toBeInTheDocument();
  });

  it('renders question tabs', () => {
    vi.mocked(api.submitAnswers).mockResolvedValue({});
    render(
      <QuestionDrawer payload={defaultPayload} onDone={vi.fn()} onClose={vi.fn()} />
    );
    expect(screen.getByText('1')).toBeInTheDocument();
    expect(screen.getByText('2')).toBeInTheDocument();
  });

  it('renders current question text', () => {
    vi.mocked(api.submitAnswers).mockResolvedValue({});
    render(
      <QuestionDrawer payload={defaultPayload} onDone={vi.fn()} onClose={vi.fn()} />
    );
    expect(screen.getByText('What is your preference?')).toBeInTheDocument();
  });

  it('renders options with descriptions', () => {
    vi.mocked(api.submitAnswers).mockResolvedValue({});
    render(
      <QuestionDrawer payload={defaultPayload} onDone={vi.fn()} onClose={vi.fn()} />
    );
    expect(screen.getByText('Option A')).toBeInTheDocument();
    expect(screen.getByText('First option')).toBeInTheDocument();
    expect(screen.getByText('Option C')).toBeInTheDocument();
    expect(screen.getByText('Third option')).toBeInTheDocument();
  });

  it('shows text input by default', () => {
    vi.mocked(api.submitAnswers).mockResolvedValue({});
    render(
      <QuestionDrawer payload={defaultPayload} onDone={vi.fn()} onClose={vi.fn()} />
    );
    expect(screen.getByPlaceholderText('Or type your own answer...')).toBeInTheDocument();
  });

  it('navigates to next question', () => {
    vi.mocked(api.submitAnswers).mockResolvedValue({});
    render(
      <QuestionDrawer payload={defaultPayload} onDone={vi.fn()} onClose={vi.fn()} />
    );
    fireEvent.click(screen.getByText('Next'));
    expect(screen.getByText('Choose a framework.')).toBeInTheDocument();
  });

  it('shows progress', () => {
    vi.mocked(api.submitAnswers).mockResolvedValue({});
    render(
      <QuestionDrawer payload={defaultPayload} onDone={vi.fn()} onClose={vi.fn()} />
    );
    expect(screen.getByText('0 / 2')).toBeInTheDocument();
  });

  it('selects option and advances', async () => {
    vi.mocked(api.submitAnswers).mockResolvedValue({});
    render(
      <QuestionDrawer payload={defaultPayload} onDone={vi.fn()} onClose={vi.fn()} />
    );
    fireEvent.click(screen.getByText('Option A'));
    await waitFor(() => {
      expect(screen.getByText('Choose a framework.')).toBeInTheDocument();
    });
  });

  it('calls submit with answers', async () => {
    const mockSubmit = vi.mocked(api.submitAnswers).mockResolvedValue({});
    const onDone = vi.fn();
    render(
      <QuestionDrawer payload={defaultPayload} onDone={onDone} onClose={vi.fn()} />
    );
    // Answer first question
    fireEvent.click(screen.getByText('Option A'));
    await waitFor(() => {
      expect(screen.getByText('Choose a framework.')).toBeInTheDocument();
    });
    // Answer second question
    fireEvent.click(screen.getByText('PyTorch'));

    fireEvent.click(screen.getByText('Submit'));
    expect(mockSubmit).toHaveBeenCalledWith({ q1: 'Option A', q2: 'PyTorch' });
  });

  it('calls onClose when X clicked', () => {
    vi.mocked(api.submitAnswers).mockResolvedValue({});
    const onClose = vi.fn();
    const { container } = render(
      <QuestionDrawer payload={defaultPayload} onDone={vi.fn()} onClose={onClose} />
    );
    // Close button now uses Lucide X icon
    const closeBtn = container.querySelector('.lucide-x')?.closest('button');
    expect(closeBtn).toBeTruthy();
    fireEvent.click(closeBtn!);
    expect(onClose).toHaveBeenCalled();
  });
});

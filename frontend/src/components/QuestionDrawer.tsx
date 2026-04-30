import { useState } from 'react';
import { X, ChevronLeft, ChevronRight, Send, Play } from 'lucide-react';
import { api } from '../api';
import type { QuestionsPayload } from '../types';

interface Props {
  payload: QuestionsPayload;
  onDone: (summary: string, switchToExecute?: boolean) => void;
  onClose: () => void;
}

export function QuestionDrawer({ payload, onDone, onClose }: Props) {
  const { questions, context, suggest_mode } = payload;
  const [currentIdx, setCurrentIdx] = useState(0);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [textInputs, setTextInputs] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);

  const current = questions[currentIdx];
  const allowText = current.allow_text !== false; // default true
  const allAnswered = questions.every((q) => answers[q.id]);
  const isLast = currentIdx === questions.length - 1;

  const selectOption = (label: string) => {
    setAnswers((prev) => ({ ...prev, [current.id]: label }));
    setTextInputs((prev) => ({ ...prev, [current.id]: '' })); // clear text if option selected
    if (!isLast) setTimeout(() => setCurrentIdx((i) => Math.min(i + 1, questions.length - 1)), 200);
  };

  const setTextAnswer = (text: string) => {
    setTextInputs((prev) => ({ ...prev, [current.id]: text }));
    if (text.trim()) {
      setAnswers((prev) => ({ ...prev, [current.id]: text.trim() }));
    } else {
      // Remove text answer, revert to option if one was selected
      setAnswers((prev) => {
        const next = { ...prev };
        // Only remove if the current answer IS the text (not an option)
        const opts = current.options.map((o) => o.label);
        if (next[current.id] && !opts.includes(next[current.id])) {
          delete next[current.id];
        }
        return next;
      });
    }
  };

  const doSubmit = async (switchToExecute: boolean) => {
    setSubmitting(true);
    try {
      await api.submitAnswers(answers);
      const lines = questions.map((q) => `${q.question} → ${answers[q.id]}`);
      onDone(lines.join('\n'), switchToExecute);
    } catch { /* */ }
    finally { setSubmitting(false); }
  };

  return (
    <div className="absolute inset-x-0 bottom-0 bg-surface border-t border-border shadow-xl animate-slide-up z-30">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-border">
        <div className="font-semibold text-text">{context || 'Clarifying questions'}</div>
        <div className="flex items-center gap-2">
          {questions.map((q, i) => (
            <button
              key={q.id}
              className={`w-8 h-8 rounded-full text-sm font-medium transition-all ${
                i === currentIdx 
                  ? 'bg-primary text-white' 
                  : answers[q.id] 
                    ? 'bg-success/20 text-success border border-success' 
                    : 'bg-surface-hover text-text-dim border border-border'
              }`}
              onClick={() => setCurrentIdx(i)}
            >
              {i + 1}
            </button>
          ))}
        </div>
        <button 
          className="w-8 h-8 rounded-lg flex items-center justify-center text-text-dim hover:bg-surface-hover hover:text-text transition-colors"
          onClick={onClose}
        >
          <X size={18} />
        </button>
      </div>

      {/* Body */}
      <div className="px-6 py-5">
        <div className="text-lg font-medium text-text mb-4">{current.question}</div>
        
        <div className="flex flex-wrap gap-2 mb-4">
          {current.options.map((opt) => (
            <button
              key={opt.label}
              className={`px-4 py-2.5 rounded-lg text-sm transition-all ${
                answers[current.id] === opt.label && !textInputs[current.id]
                  ? 'bg-primary text-white'
                  : 'bg-surface-hover text-text border border-border hover:border-primary'
              }`}
              onClick={() => selectOption(opt.label)}
            >
              <span className="font-medium">{opt.label}</span>
              {opt.description && <span className="block text-xs opacity-70 mt-0.5">{opt.description}</span>}
            </button>
          ))}
        </div>
        
        {allowText && (
          <input
            type="text"
            className="w-full bg-bg border border-border rounded-lg px-4 py-3 text-text placeholder-text-dim focus:border-primary focus:outline-none transition-colors"
            placeholder="Or type your own answer..."
            value={textInputs[current.id] || ''}
            onChange={(e) => setTextAnswer(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && textInputs[current.id]?.trim()) {
                if (!isLast) setCurrentIdx((i) => i + 1);
              }
            }}
          />
        )}
      </div>

      {/* Footer */}
      <div className="flex items-center justify-between px-6 py-4 border-t border-border bg-bg">
        <div className="text-sm text-text-dim">
          {Object.keys(answers).length} / {questions.length}
        </div>
        <div className="flex items-center gap-3">
          {currentIdx > 0 && (
            <button 
              className="flex items-center gap-1 px-4 py-2 text-sm text-text-dim hover:text-text transition-colors"
              onClick={() => setCurrentIdx((i) => i - 1)}
            >
              <ChevronLeft size={16} />
              Previous
            </button>
          )}
          {!isLast && (
            <button 
              className="flex items-center gap-1 px-4 py-2 text-sm text-text-dim hover:text-text transition-colors"
              onClick={() => setCurrentIdx((i) => i + 1)}
            >
              Next
              <ChevronRight size={16} />
            </button>
          )}
          {allAnswered && (
            <div className="flex items-center gap-2">
              {/* Submit: stays in current mode */}
              <button 
                className="flex items-center gap-2 px-5 py-2.5 bg-surface-hover text-text border border-border rounded-lg font-medium hover:bg-surface transition-all disabled:opacity-50"
                onClick={() => doSubmit(false)} 
                disabled={submitting}
              >
                <Send size={16} />
                {submitting ? 'Submitting...' : 'Submit'}
              </button>
              {/* Submit & Execute: submits answers AND switches to execute mode */}
              <button 
                className={`flex items-center gap-2 px-5 py-2.5 rounded-lg font-medium transition-all disabled:opacity-50 ${
                  suggest_mode === 'execute'
                    ? 'bg-primary text-white hover:bg-primary-hover ring-2 ring-primary/30'
                    : 'bg-primary text-white hover:bg-primary-hover'
                }`}
                onClick={() => doSubmit(true)} 
                disabled={submitting}
              >
                <Play size={16} fill="currentColor" />
                {submitting ? 'Submitting...' : 'Submit & Execute'}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

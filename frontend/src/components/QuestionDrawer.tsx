import { useState } from 'react';
import { api } from '../api';
import type { QuestionsPayload } from '../types';

interface Props {
  payload: QuestionsPayload;
  onDone: (summary: string, suggestedMode?: string) => void;
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

  const submit = async () => {
    setSubmitting(true);
    try {
      await api.submitAnswers(answers);
      const lines = questions.map((q) => `${q.question} → ${answers[q.id]}`);
      onDone(lines.join('\n'), suggest_mode || undefined);
    } catch { /* */ }
    finally { setSubmitting(false); }
  };

  return (
    <div className="question-drawer">
      <div className="question-drawer-header">
        <div className="question-drawer-title">{context || 'Clarifying questions'}</div>
        <div className="question-tabs">
          {questions.map((q, i) => (
            <button
              key={q.id}
              className={`question-tab ${i === currentIdx ? 'active' : ''} ${answers[q.id] ? 'answered' : ''}`}
              onClick={() => setCurrentIdx(i)}
            >{i + 1}</button>
          ))}
        </div>
        <button className="question-drawer-close" onClick={onClose}>&times;</button>
      </div>

      <div className="question-body">
        <div className="question-text">{current.question}</div>
        <div className="question-options">
          {current.options.map((opt) => (
            <button
              key={opt.label}
              className={`question-option ${answers[current.id] === opt.label && !textInputs[current.id] ? 'selected' : ''}`}
              onClick={() => selectOption(opt.label)}
            >
              <span className="option-label">{opt.label}</span>
              {opt.description && <span className="option-desc">{opt.description}</span>}
            </button>
          ))}
        </div>
        {allowText && (
          <div className="question-text-input">
            <input
              type="text"
              placeholder="Or type your own answer..."
              value={textInputs[current.id] || ''}
              onChange={(e) => setTextAnswer(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && textInputs[current.id]?.trim()) {
                  if (!isLast) setCurrentIdx((i) => i + 1);
                }
              }}
            />
          </div>
        )}
      </div>

      <div className="question-footer">
        <div className="question-progress">{Object.keys(answers).length} / {questions.length}</div>
        <div className="question-actions">
          {currentIdx > 0 && <button className="question-nav" onClick={() => setCurrentIdx((i) => i - 1)}>Previous</button>}
          {!isLast && <button className="question-nav" onClick={() => setCurrentIdx((i) => i + 1)}>Next</button>}
          {allAnswered && (
            <button className="question-submit" onClick={submit} disabled={submitting}>
              {submitting ? 'Submitting...' : suggest_mode ? `Submit & ${suggest_mode}` : 'Submit'}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

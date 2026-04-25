import { useState, useRef, useEffect, useCallback } from 'react';

type Mode = 'plan' | 'research' | 'write';

interface Props {
  disabled: boolean;
  onSend: (text: string, mode: Mode) => void;
  onStop: () => void;
}

const MODE_INFO: Record<Mode, { label: string; icon: string; placeholder: string }> = {
  plan: { label: 'Plan', icon: 'P', placeholder: 'Ask questions, plan tasks, clarify scope...' },
  research: { label: 'Research', icon: 'R', placeholder: 'Search papers, find code, explore literature...' },
  write: { label: 'Write', icon: 'W', placeholder: 'Write sections, manage citations, draft content...' },
};

export function InputArea({ disabled, onSend, onStop }: Props) {
  const [text, setText] = useState('');
  const [mode, setMode] = useState<Mode>('plan');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = Math.min(el.scrollHeight, 200) + 'px';
  }, [text]);

  useEffect(() => { textareaRef.current?.focus(); }, [mode]);

  const submit = useCallback(() => {
    const trimmed = text.trim();
    if (!trimmed || disabled) return;
    setText('');
    onSend(trimmed, mode);
    if (textareaRef.current) textareaRef.current.style.height = 'auto';
  }, [text, disabled, onSend, mode]);

  const info = MODE_INFO[mode];

  return (
    <div className="input-area">
      <div className="input-mode-bar">
        {(Object.keys(MODE_INFO) as Mode[]).map((m) => (
          <button
            key={m}
            className={`input-mode-btn ${mode === m ? 'active' : ''}`}
            onClick={() => setMode(m)}
            title={MODE_INFO[m].label}
          >
            <span className="input-mode-icon">{MODE_INFO[m].icon}</span>
            <span className="input-mode-label">{MODE_INFO[m].label}</span>
          </button>
        ))}
      </div>
      <div className="input-row">
        <textarea
          ref={textareaRef}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); submit(); }
          }}
          placeholder={info.placeholder}
          rows={1}
          disabled={disabled}
        />
        {disabled ? (
          <button className="stop-btn" onClick={onStop} title="Stop">
            <span className="stop-icon" />
          </button>
        ) : (
          <button className="send-btn" onClick={submit} disabled={!text.trim()}>
            <span>&#x2191;</span>
          </button>
        )}
      </div>
    </div>
  );
}

import { useRef, useEffect, useCallback } from 'react';

export type Mode = 'plan' | 'research' | 'write' | 'general';

interface Props {
  disabled: boolean;
  showStop?: boolean;  // Show the stop button even when input is enabled (e.g., during questions/approval)
  mode: Mode;
  onModeChange: (mode: Mode) => void;
  onSend: (text: string, mode: Mode) => void;
  onStop: () => void;
  text: string;
  onTextChange: (text: string) => void;
}

const MODE_INFO: Record<Mode, { label: string; icon: string; placeholder: string }> = {
  plan: { label: 'Plan', icon: 'P', placeholder: 'Ask questions, plan tasks, clarify scope...' },
  research: { label: 'Research', icon: 'R', placeholder: 'Search papers, find code, explore literature...' },
  write: { label: 'Write', icon: 'W', placeholder: 'Write sections, manage citations, draft content...' },
  general: { label: 'General', icon: 'G', placeholder: 'General conversation, any task...' },
};

export function InputArea({ disabled, showStop, mode, onModeChange, onSend, onStop, text, onTextChange }: Props) {
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
    onTextChange('');
    onSend(trimmed, mode);
    if (textareaRef.current) textareaRef.current.style.height = 'auto';
  }, [text, disabled, onSend, mode, onTextChange]);

  const modes: Mode[] = ['plan', 'research', 'write', 'general'];

  return (
    <div className="input-area">
      <div className="input-mode-bar">
        {modes.map((m) => (
          <button
            key={m}
            className={`input-mode-btn ${mode === m ? 'active' : ''}`}
            onClick={() => onModeChange(m)}
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
          onChange={(e) => onTextChange(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); submit(); }
          }}
          placeholder={MODE_INFO[mode].placeholder}
          rows={1}
          disabled={disabled}
        />
        {/* Always show stop button when agent turn is active */}
        {showStop && (
          <button className="stop-btn" onClick={onStop} title="Stop">
            <span className="stop-icon" />
          </button>
        )}
        {/* Show send button when input is enabled */}
        {!disabled && (
          <button className="send-btn" onClick={submit} disabled={!text.trim()}>
            <span>&#x2191;</span>
          </button>
        )}
      </div>
    </div>
  );
}

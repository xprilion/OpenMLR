import { useRef, useEffect, useCallback } from 'react';

export type Mode = 'plan' | 'execute';

interface Props {
  disabled: boolean;
  showStop?: boolean;
  mode: Mode;
  onModeChange: (mode: Mode) => void;
  onSend: (text: string, mode: Mode) => void;
  onStop: () => void;
  text: string;
  onTextChange: (text: string) => void;
}

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

  const toggleMode = useCallback(() => {
    onModeChange(mode === 'plan' ? 'execute' : 'plan');
  }, [mode, onModeChange]);

  // Keyboard shortcut: Cmd+M (or Ctrl+M) toggles between Plan and Execute
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (!(e.metaKey || e.ctrlKey)) return;
      if (e.key === 'm' || e.key === 'M') {
        e.preventDefault();
        onModeChange(mode === 'plan' ? 'execute' : 'plan');
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [mode, onModeChange]);

  const isPlan = mode === 'plan';

  return (
    <div className="input-area">
      <div className="input-row">
        <button
          className={`mode-toggle ${isPlan ? 'mode-plan' : 'mode-execute'}`}
          onClick={toggleMode}
          title={`${isPlan ? 'Plan' : 'Execute'} mode — Cmd+M to toggle`}
        >
          {isPlan ? 'P' : 'E'}
        </button>
        <textarea
          ref={textareaRef}
          value={text}
          onChange={(e) => onTextChange(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); submit(); }
          }}
          placeholder={isPlan ? 'Plan: ask questions, gather context, create plan...' : 'Execute: tell the agent what to do...'}
          rows={1}
          disabled={disabled}
        />
        {showStop && (
          <button className="stop-btn" onClick={onStop} title="Stop">
            <span className="stop-icon" />
          </button>
        )}
        {!disabled && (
          <button className="send-btn" onClick={submit} disabled={!text.trim()}>
            <span>&#x2191;</span>
          </button>
        )}
      </div>
    </div>
  );
}

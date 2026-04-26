import { useRef, useEffect, useCallback } from 'react';
import { ArrowUp, Square } from 'lucide-react';

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
    <div className="px-6 py-4 bg-bg border-t border-border">
      <div className="flex items-center gap-3 max-w-4xl mx-auto">
        {/* Mode toggle button - fixed height to match input */}
        <button
          className={`h-11 w-11 rounded-lg flex items-center justify-center text-sm font-bold shrink-0 transition-all ${
            isPlan 
              ? 'bg-warning text-black hover:opacity-90' 
              : 'bg-primary text-white hover:bg-primary-hover'
          }`}
          onClick={toggleMode}
          title={`${isPlan ? 'Plan' : 'Execute'} mode — Cmd+M to toggle`}
        >
          {isPlan ? 'P' : 'E'}
        </button>
        
        {/* Textarea - minimum height matches buttons */}
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
          className="flex-1 min-h-[44px] bg-surface border border-border rounded-lg px-4 py-2.5 text-base text-text placeholder-text-dim resize-none focus:border-primary focus:outline-none transition-colors disabled:opacity-50 disabled:cursor-not-allowed leading-normal"
        />
        
        {/* Stop button - same height as mode toggle */}
        {showStop && (
          <button 
            className="h-11 w-11 rounded-lg flex items-center justify-center bg-error text-white hover:opacity-90 transition-all shrink-0"
            onClick={onStop} 
            title="Stop"
          >
            <Square size={16} fill="currentColor" />
          </button>
        )}
        
        {/* Send button - same height as mode toggle */}
        {!disabled && (
          <button 
            className="h-11 w-11 rounded-lg flex items-center justify-center bg-primary text-white hover:bg-primary-hover transition-all shrink-0 disabled:opacity-40 disabled:cursor-not-allowed"
            onClick={submit} 
            disabled={!text.trim()}
            title="Send message"
          >
            <ArrowUp size={20} strokeWidth={2.5} />
          </button>
        )}
      </div>
    </div>
  );
}

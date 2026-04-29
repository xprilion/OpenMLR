import { useRef, useEffect, useCallback, useState } from 'react';
import { ArrowUp, Square, Play } from 'lucide-react';

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

  /** Send message AND switch to execute mode in one action. */
  const submitAndExecute = useCallback(() => {
    const trimmed = text.trim();
    if (!trimmed || disabled) return;
    onTextChange('');
    onModeChange('execute');
    onSend(trimmed, 'execute');
    if (textareaRef.current) textareaRef.current.style.height = 'auto';
  }, [text, disabled, onSend, onModeChange, onTextChange]);

  const toggleMode = useCallback(() => {
    onModeChange(mode === 'plan' ? 'execute' : 'plan');
  }, [mode, onModeChange]);

  // Keyboard shortcuts
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (!(e.metaKey || e.ctrlKey)) return;
      if (e.key === 'm' || e.key === 'M') {
        // Cmd+M: toggle mode
        e.preventDefault();
        onModeChange(mode === 'plan' ? 'execute' : 'plan');
      } else if (e.key === 'Enter' && mode === 'plan') {
        // Cmd+Enter in plan mode: send & execute
        e.preventDefault();
        submitAndExecute();
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [mode, onModeChange, submitAndExecute]);

  const isPlan = mode === 'plan';
  
  // Use shorter placeholders on mobile (check window width)
  const [isMobile, setIsMobile] = useState(false);
  
  useEffect(() => {
    const checkMobile = () => setIsMobile(window.innerWidth < 640);
    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, []);
  
  const placeholder = isPlan 
    ? (isMobile ? 'Plan your research...' : 'Plan: ask questions, gather context, create plan...')
    : (isMobile ? 'Execute task...' : 'Execute: tell the agent what to do...');

  return (
    <div className="px-3 sm:px-6 py-3 sm:py-4 bg-bg border-t border-border">
      <div className="flex items-center gap-2 sm:gap-3 max-w-4xl mx-auto">
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
          placeholder={placeholder}
          rows={1}
          disabled={disabled}
          className="flex-1 min-h-[44px] bg-surface border border-border rounded-lg px-4 py-2.5 text-base text-text placeholder-text-dim resize-none focus:outline-none transition-colors disabled:opacity-50 disabled:cursor-not-allowed leading-normal"
          style={{
            borderColor: undefined,
          }}
          onFocus={(e) => {
            e.target.style.borderColor = isPlan ? '#f59e0b' : '#3b82f6';
          }}
          onBlur={(e) => {
            e.target.style.borderColor = '';
          }}
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
        
        {/* Send buttons */}
        {!disabled && (
          <div className="flex items-center gap-1.5 shrink-0">
            {/* Primary send: uses current mode */}
            <button 
              className="h-11 w-11 rounded-lg flex items-center justify-center transition-all disabled:opacity-40 disabled:cursor-not-allowed"
              style={{
                backgroundColor: isPlan ? '#f59e0b' : '#3b82f6',
                color: isPlan ? '#000' : '#fff',
              }}
              onClick={submit} 
              disabled={!text.trim()}
              title={isPlan ? 'Send in Plan mode (Enter)' : 'Send in Execute mode (Enter)'}
            >
              <ArrowUp size={20} strokeWidth={2.5} />
            </button>
            
            {/* Send & Execute: visible only in Plan mode */}
            {isPlan && (
              <button 
                className="h-11 px-3 rounded-lg flex items-center justify-center gap-1.5 text-xs font-semibold transition-all disabled:opacity-40 disabled:cursor-not-allowed bg-primary text-white hover:bg-primary-hover"
                onClick={submitAndExecute} 
                disabled={!text.trim()}
                title="Send & switch to Execute mode (Cmd+Enter)"
              >
                <Play size={14} fill="currentColor" />
                <span className="hidden sm:inline">Execute</span>
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

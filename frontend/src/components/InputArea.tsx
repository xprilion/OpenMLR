import { useRef, useEffect, useCallback, useState } from 'react';
import { ArrowUp, Square } from 'lucide-react';
import type { McpServerStatus, Mention } from '../types';
import { MentionPopover } from './MentionPopover';

export type Mode = 'plan' | 'execute';

interface Props {
  disabled: boolean;
  showStop?: boolean;
  mode: Mode;
  onModeChange: (mode: Mode) => void;
  onSend: (text: string, mode: Mode, mentions?: Mention[]) => void;
  onStop: () => void;
  text: string;
  onTextChange: (text: string) => void;
  mcpServers?: readonly McpServerStatus[];
  projectUuid?: string | null;
}

export function InputArea({ disabled, showStop, mode, onModeChange, onSend, onStop, text, onTextChange, mcpServers = [], projectUuid = null }: Props) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const [mentions, setMentions] = useState<Mention[]>([]);
  const [mentionPopoverOpen, setMentionPopoverOpen] = useState(false);
  const [mentionQuery, setMentionQuery] = useState('');
  const [mentionStartPos, setMentionStartPos] = useState<number | null>(null);

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
    // Filter mentions to only those still present in the text
    const activeMentions = mentions.filter((m) => {
      const tag = `@${m.value}`;
      return trimmed.includes(tag);
    });
    onTextChange('');
    onSend(trimmed, mode, activeMentions.length > 0 ? activeMentions : undefined);
    setMentions([]);
    setMentionPopoverOpen(false);
    if (textareaRef.current) textareaRef.current.style.height = 'auto';
  }, [text, disabled, onSend, mode, onTextChange, mentions]);

  const toggleMode = useCallback(() => {
    onModeChange(mode === 'plan' ? 'execute' : 'plan');
  }, [mode, onModeChange]);

  // Detect @ trigger in text changes
  const handleTextChange = useCallback((newText: string) => {
    onTextChange(newText);

    const el = textareaRef.current;
    if (!el) return;
    const cursorPos = el.selectionStart;

    // Find the last @ before cursor that's preceded by whitespace, newline, or is at position 0
    let atPos = -1;
    for (let i = cursorPos - 1; i >= 0; i--) {
      const ch = newText[i];
      if (ch === '@') {
        if (i === 0 || /\s/.test(newText[i - 1])) {
          atPos = i;
        }
        break;
      }
      // Stop searching if we hit whitespace (except within the query which can have /)
      if (ch === ' ' || ch === '\n') break;
    }

    if (atPos >= 0) {
      const query = newText.slice(atPos + 1, cursorPos);
      // Don't show popover if there's a space in the query (mention completed)
      if (!query.includes(' ')) {
        setMentionPopoverOpen(true);
        setMentionQuery(query);
        setMentionStartPos(atPos);
        return;
      }
    }
    setMentionPopoverOpen(false);
  }, [onTextChange]);

  const handleMentionSelect = useCallback((mention: Mention, _displayText: string) => {
    if (mentionStartPos === null) return;
    const el = textareaRef.current;
    if (!el) return;

    // For directory selections, update the query to browse deeper
    if (mention.type === 'file' && mention.value.endsWith('/')) {
      const newText = text.slice(0, mentionStartPos + 1) + mention.value;
      onTextChange(newText);
      setMentionQuery(mention.value);
      // Keep popover open for continued browsing
      setTimeout(() => {
        if (textareaRef.current) {
          textareaRef.current.selectionStart = newText.length;
          textareaRef.current.selectionEnd = newText.length;
          textareaRef.current.focus();
        }
      }, 0);
      return;
    }

    // Insert the mention text, replacing @query
    const before = text.slice(0, mentionStartPos);
    const after = text.slice(mentionStartPos + 1 + mentionQuery.length);
    const insertText = `@${mention.value}`;
    const newText = before + insertText + (after.startsWith(' ') ? after : ' ' + after);
    onTextChange(newText);

    // Track the mention
    setMentions((prev) => {
      if (prev.some((m) => m.type === mention.type && m.value === mention.value)) return prev;
      return [...prev, mention];
    });

    setMentionPopoverOpen(false);
    setMentionStartPos(null);

    // Restore focus and cursor position
    setTimeout(() => {
      if (textareaRef.current) {
        const pos = before.length + insertText.length + 1;
        textareaRef.current.selectionStart = pos;
        textareaRef.current.selectionEnd = pos;
        textareaRef.current.focus();
      }
    }, 0);
  }, [text, mentionStartPos, mentionQuery, onTextChange]);

  // Keyboard shortcuts
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (!(e.metaKey || e.ctrlKey)) return;
      if (e.key === 'm' || e.key === 'M') {
        // Cmd+M: toggle mode
        e.preventDefault();
        onModeChange(mode === 'plan' ? 'execute' : 'plan');
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [mode, onModeChange]);

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
    ? (isMobile ? 'Plan your research...' : 'Plan: ask questions, gather context... (@ to mention)')
    : (isMobile ? 'Execute task...' : 'Execute: tell the agent what to do... (@ to mention)');

  // Show mention chips above input
  const mentionChips = mentions.filter((m) => {
    const tag = `@${m.value}`;
    return text.includes(tag);
  });

  return (
    <div className="px-3 sm:px-6 py-3 sm:py-4 bg-bg border-t border-border">
      <div className="flex flex-col gap-1.5 max-w-4xl mx-auto">
        {/* Active mention chips */}
        {mentionChips.length > 0 && (
          <div className="flex flex-wrap gap-1 px-12">
            {mentionChips.map((m) => (
              <span
                key={`${m.type}-${m.value}`}
                className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs ${
                  m.type === 'server'
                    ? 'bg-primary/20 text-primary'
                    : 'bg-warning/20 text-warning'
                }`}
              >
                {m.type === 'server' ? 'MCP:' : ''} @{m.value}
              </span>
            ))}
          </div>
        )}

        <div className="flex items-center gap-2 sm:gap-3 relative">
          {/* Mode toggle button */}
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
          
          {/* Textarea wrapper with popover */}
          <div className="flex-1 relative">
            {mentionPopoverOpen && (
              <MentionPopover
                query={mentionQuery}
                mcpServers={mcpServers}
                projectUuid={projectUuid ?? null}
                onSelect={handleMentionSelect}
                onClose={() => setMentionPopoverOpen(false)}
              />
            )}
            <textarea
              ref={textareaRef}
              value={text}
              onChange={(e) => handleTextChange(e.target.value)}
              onKeyDown={(e) => {
                if (mentionPopoverOpen) {
                  // Let the popover handle navigation keys
                  if (['ArrowUp', 'ArrowDown', 'Tab'].includes(e.key)) return;
                  if (e.key === 'Enter') return;
                  if (e.key === 'Escape') {
                    e.preventDefault();
                    setMentionPopoverOpen(false);
                    return;
                  }
                }
                if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); submit(); }
              }}
              placeholder={placeholder}
              rows={1}
              disabled={disabled}
              className="w-full min-h-[44px] bg-surface border border-border rounded-lg px-4 py-2.5 text-base text-text placeholder-text-dim resize-none focus:outline-none transition-colors disabled:opacity-50 disabled:cursor-not-allowed leading-normal"
              style={{ borderColor: undefined }}
              onFocus={(e) => {
                e.target.style.borderColor = isPlan ? '#f59e0b' : '#3b82f6';
              }}
              onBlur={(e) => {
                e.target.style.borderColor = '';
              }}
            />
          </div>
          
          {/* Stop button */}
          {showStop && (
            <button 
              className="h-11 w-11 rounded-lg flex items-center justify-center bg-error text-white hover:opacity-90 transition-all shrink-0"
              onClick={onStop} 
              title="Stop"
            >
              <Square size={16} fill="currentColor" />
            </button>
          )}
          
          {/* Send button */}
          {!disabled && (
            <button 
              className="h-11 w-11 rounded-lg flex items-center justify-center transition-all disabled:opacity-40 disabled:cursor-not-allowed shrink-0"
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
          )}
        </div>
      </div>
    </div>
  );
}

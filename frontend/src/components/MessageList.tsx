import React, { useState, useRef, useEffect, useCallback } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import type { Message, SubAgentChild } from '../types';

interface Props {
  messages: Message[];
  hasDrawerOpen?: boolean; // When QuestionDrawer is visible
  visible?: boolean; // Whether the agent tab is currently visible
}

/** Format seconds into human-readable duration */
function formatDuration(seconds?: number): string {
  if (!seconds) return '';
  if (seconds < 60) return `${seconds.toFixed(1)}s`;
  const m = Math.floor(seconds / 60);
  const s = (seconds % 60).toFixed(0);
  return `${m}m ${s}s`;
}

/** Get a compact arrow/icon prefix for tool names */
function toolPrefix(tool: string): string {
  if (tool.startsWith('sub_agent:')) return '\u2234'; // therefore symbol
  const readTools = ['read', 'read_file', 'github_read_file', 'Read'];
  const searchTools = ['web_search', 'search', 'papers', 'github_find_examples', 'Grep', 'Glob'];
  const writeTools = ['write', 'write_file', 'edit', 'writing'];
  if (readTools.some(t => tool.includes(t))) return '\u2192'; // arrow right
  if (searchTools.some(t => tool.includes(t))) return '*';
  if (writeTools.some(t => tool.includes(t))) return '\u270E'; // pencil
  return '\u2192';
}

/** Compact tool call row */
function ToolCallRow({ msg, expanded, onToggle }: { msg: Message; expanded: boolean; onToggle: () => void }) {
  const tool = msg.metadata?.tool || 'tool';
  const args = msg.metadata?.args || '';
  const output = msg.metadata?.output;
  const success = msg.metadata?.outputSuccess;
  const isPending = output === undefined;
  const isError = success === false;
  const prefix = toolPrefix(tool);

  return (
    <div className="font-mono text-sm px-1 max-w-[95%]">
      <button 
        className={`flex items-center gap-2 py-0.5 px-1 border-none bg-transparent cursor-pointer w-full text-left transition-colors leading-relaxed ${
          isPending ? 'text-tool-text' : isError ? 'text-error' : 'text-text-dim hover:text-text'
        }`}
        onClick={onToggle} 
        title={output ? 'Click to expand output' : undefined}
      >
        <span className="w-4 text-center shrink-0">{prefix}</span>
        <span className={`font-semibold shrink-0 ${isPending ? 'text-tool-text' : isError ? 'text-error' : 'text-text-dim'}`}>
          {tool}
        </span>
        {args && <span className="text-text-dim/70 truncate max-w-[500px]">{args}</span>}
        {isPending && (
          <span className="w-2.5 h-2.5 border-2 border-tool-text border-t-transparent rounded-full animate-spin shrink-0" />
        )}
        {output && !expanded && isError && <span className="text-error text-xs">(error)</span>}
      </button>
      {expanded && output !== undefined && (
        <pre className={`mt-2 p-3 rounded-md text-xs overflow-x-auto max-h-64 overflow-y-auto ${
          isError ? 'bg-error-bg text-error' : 'bg-bg text-text-dim border border-border'
        }`}>
          {output}
        </pre>
      )}
    </div>
  );
}

/** Sub-agent block with nested tool calls */
function SubAgentBlock({ msg, expanded, onToggle }: { msg: Message; expanded: boolean; onToggle: () => void }) {
  const agentType = msg.metadata?.agentType || 'task';
  const description = msg.metadata?.args || '';
  const children = (msg.metadata?.children || []) as SubAgentChild[];
  const toolCount = msg.metadata?.toolCount || children.length;
  const duration = msg.metadata?.duration;
  const output = msg.metadata?.output;
  const isPending = output === undefined;

  const label = agentType === 'research' ? 'Research Task' : 'General Task';

  return (
    <div className="font-mono text-sm bg-tool-bg rounded-lg p-3 max-w-[95%]">
      <button 
        className="flex items-center gap-2 text-left w-full bg-transparent border-none cursor-pointer text-text hover:text-primary-light transition-colors"
        onClick={onToggle}
      >
        <span className="text-tool-text">{isPending ? '\u23F3' : '\u2234'}</span>
        <span className="font-semibold text-tool-text">{label}</span>
        <span className="text-text-dim">&mdash;</span>
        <span className="text-text truncate">{description}</span>
      </button>
      
      <div className="flex items-center gap-2 mt-2 text-xs text-text-dim">
        {toolCount > 0 && <span>{toolCount} toolcalls</span>}
        {toolCount > 0 && duration && <span>&middot;</span>}
        {duration && <span>{formatDuration(duration)}</span>}
        {isPending && <span className="text-tool-text animate-pulse">running...</span>}
      </div>
      
      {children.length > 0 && (
        <div className={`mt-3 flex flex-col gap-1 ${expanded ? '' : 'max-h-20 overflow-hidden'}`}>
          {children.map((child, i) => (
            <div 
              key={child.id || i} 
              className={`flex items-center gap-2 text-xs ${child.success === false ? 'text-error' : 'text-text-dim'}`}
            >
              <span className="w-3 text-center">{toolPrefix(child.tool)}</span>
              <span className="font-semibold">{child.tool}</span>
              {child.args && <span className="truncate max-w-[500px] opacity-70">{child.args}</span>}
            </div>
          ))}
        </div>
      )}
      
      {expanded && output && (
        <pre className="mt-3 p-3 bg-bg rounded-md text-xs text-text-dim overflow-x-auto max-h-48 overflow-y-auto border border-border">
          {output}
        </pre>
      )}
    </div>
  );
}

/** Format thinking duration into human-readable text */
function formatThinkingDuration(seconds?: number): string {
  if (!seconds) return 'a moment';
  if (seconds < 2) return '1 second';
  if (seconds < 60) return `${Math.round(seconds)} seconds`;
  const m = Math.floor(seconds / 60);
  const s = Math.round(seconds % 60);
  if (s === 0) return `${m} minute${m !== 1 ? 's' : ''}`;
  return `${m}m ${s}s`;
}

/** Thinking/reasoning block — shows model thinking, collapses when reply starts */
function ThinkingBlock({ msg, expanded, onToggle }: { msg: Message; expanded: boolean; onToggle: () => void }) {
  const thinking = msg.thinking || '';
  const duration = msg.thinkingDuration;
  const collapsed = msg.thinkingCollapsed;

  if (!collapsed) {
    // Active thinking — show faded content with streaming indicator
    return (
      <div className="max-w-[95%] rounded-lg border border-border/40 bg-surface/30 px-4 py-3 mt-1">
        <div className="flex items-center gap-2 mb-2 text-xs text-text-dim">
          <span className="flex gap-1">
            <span className="w-1.5 h-1.5 bg-primary/60 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
            <span className="w-1.5 h-1.5 bg-primary/60 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
            <span className="w-1.5 h-1.5 bg-primary/60 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
          </span>
          <span>Thinking...</span>
        </div>
        <pre className="whitespace-pre-wrap text-sm text-text-dim/50 leading-relaxed m-0 p-0 bg-transparent max-h-48 overflow-y-auto font-sans">
          {thinking}
          <span className="inline-block w-[2px] h-[1em] bg-text-dim/30 animate-pulse align-middle ml-0.5" />
        </pre>
      </div>
    );
  }

  // Collapsed — show summary label, clickable to expand
  return (
    <div className="max-w-[95%]">
      <button
        className="flex items-center gap-2 text-xs text-text-dim/60 hover:text-text-dim transition-colors py-1 bg-transparent border-none cursor-pointer"
        onClick={onToggle}
        title="Click to expand thinking"
      >
        <span className="text-text-dim/40">{expanded ? '\u25BC' : '\u25B6'}</span>
        <span>Thought for {formatThinkingDuration(duration)}</span>
      </button>
      {expanded && thinking && (
        <div className="rounded-lg border border-border/40 bg-surface/30 px-4 py-3 mt-1">
          <pre className="whitespace-pre-wrap text-sm text-text-dim/50 leading-relaxed m-0 p-0 bg-transparent max-h-64 overflow-y-auto font-sans">
            {thinking}
          </pre>
        </div>
      )}
    </div>
  );
}

/** Individual message row — memoized to skip re-renders when other messages update */
const MessageRow = React.memo(function MessageRow({ msg, isExpanded, onToggle }: {
  msg: Message;
  isExpanded: boolean;
  onToggle: (id: string) => void;
}) {
  const handleToggle = useCallback(() => onToggle(msg.id), [onToggle, msg.id]);
  return (
    <div className="flex animate-fade-in">
      {/* User messages */}
      {msg.role === 'user' && (
        <div className={`bg-surface text-text py-3 px-4 max-w-[90%] leading-relaxed whitespace-pre-wrap mt-4 border-l-[3px] ${
          msg.metadata?.tool === 'execute' ? 'border-l-primary' : 'border-l-warning'
        }`}>
          {msg.metadata?.tool && (
            <span className={`inline-block text-[10px] font-bold uppercase tracking-wide mr-2 px-1.5 py-0.5 rounded align-middle ${
              msg.metadata.tool === 'execute' 
                ? 'text-primary bg-primary/10' 
                : 'text-warning bg-warning/10'
            }`}>
              {msg.metadata.tool}
            </span>
          )}
          {msg.content}
        </div>
      )}

      {/* Assistant messages — render markdown seamlessly during streaming */}
      {msg.role === 'assistant' && (
        <div className="prose max-w-[95%] mt-1">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {msg.content}
          </ReactMarkdown>
          {msg.streaming && (
            <span className="inline-block w-[2px] h-[1em] bg-primary animate-pulse align-middle ml-0.5" />
          )}
        </div>
      )}

      {/* Tool calls */}
      {msg.role === 'tool' && !msg.metadata?.isSubAgent && (
        <ToolCallRow
          msg={msg}
          expanded={isExpanded}
          onToggle={handleToggle}
        />
      )}

      {/* Sub-agent blocks */}
      {msg.role === 'tool' && msg.metadata?.isSubAgent && (
        <SubAgentBlock
          msg={msg}
          expanded={isExpanded}
          onToggle={handleToggle}
        />
      )}

      {/* Thinking indicator (before any thinking content arrives) */}
      {msg.role === 'system' && msg.content === '::thinking::' && (
        <div className="flex items-center gap-3 py-3 text-text-dim">
          <span className="flex gap-1">
            <span className="w-2 h-2 bg-primary rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
            <span className="w-2 h-2 bg-primary rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
            <span className="w-2 h-2 bg-primary rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
          </span>
          <span className="text-sm">Thinking...</span>
        </div>
      )}

      {/* Thinking content block (streaming or collapsed) */}
      {msg.role === 'system' && msg.content === '::thinking_content::' && (
        <ThinkingBlock
          msg={msg}
          expanded={isExpanded}
          onToggle={handleToggle}
        />
      )}

      {/* System messages */}
      {msg.role === 'system' && msg.content !== '::thinking::' && msg.content !== '::thinking_content::' && (
        <div className="text-sm text-text-dim italic py-2 px-3 bg-surface/50 rounded-md">
          {msg.content}
        </div>
      )}

      {/* Error messages */}
      {msg.role === 'error' && (
        <div className="text-sm text-error bg-error-bg py-3 px-4 rounded-md border border-error/30">
          {msg.content}
        </div>
      )}
    </div>
  );
});

export const MessageList = React.memo(function MessageList({ messages, hasDrawerOpen, visible = true }: Props) {
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const containerRef = useRef<HTMLDivElement>(null);
  // Track message count to detect new messages (not layout changes)
  const prevMessageCountRef = useRef<number>(0);

  // Only scroll to bottom when NEW messages are added
  // This prevents scrolling on layout changes (e.g., RightPanel opening)
  // Using container.scrollTop instead of scrollIntoView to avoid scrolling parent containers
  useEffect(() => {
    const currentCount = messages.length;
    const prevCount = prevMessageCountRef.current;
    
    // Only scroll if message count increased (new message added)
    if (currentCount > prevCount && prevCount > 0) {
      // Small delay to let DOM settle, then scroll
      const timer = setTimeout(() => {
        const container = containerRef.current;
        if (container) {
          // Scroll the container itself, not using scrollIntoView which can affect parents
          container.scrollTop = container.scrollHeight;
        }
      }, 50);
      return () => clearTimeout(timer);
    }
    
    prevMessageCountRef.current = currentCount;
  }, [messages.length]);

  // Scroll to bottom when the agent tab becomes visible again
  // (scroll events during display:none have no effect)
  const prevVisibleRef = useRef(visible);
  useEffect(() => {
    if (visible && !prevVisibleRef.current) {
      const container = containerRef.current;
      if (container) container.scrollTop = container.scrollHeight;
    }
    prevVisibleRef.current = visible;
  }, [visible]);

  const toggle = useCallback((id: string) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);

  return (
    <div 
      ref={containerRef}
      className="flex-1 overflow-y-auto px-6 py-5 flex flex-col gap-2 min-h-0"
      style={{ paddingBottom: hasDrawerOpen ? '280px' : undefined }}
    >
      {messages.map((msg) => (
        <MessageRow
          key={msg.id}
          msg={msg}
          isExpanded={expanded.has(msg.id)}
          onToggle={toggle}
        />
      ))}
    </div>
  );
});

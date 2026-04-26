import { useState, useRef, useEffect, useCallback } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import type { Message, SubAgentChild } from '../types';

interface Props {
  messages: Message[];
  hasDrawerOpen?: boolean; // When QuestionDrawer is visible
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

export function MessageList({ messages, hasDrawerOpen }: Props) {
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const bottomRef = useRef<HTMLDivElement>(null);
  const scrollTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Debounced scroll to bottom - prevents jittering during rapid message updates
  const scrollToBottom = useCallback(() => {
    if (scrollTimeoutRef.current) {
      clearTimeout(scrollTimeoutRef.current);
    }
    scrollTimeoutRef.current = setTimeout(() => {
      // Use 'auto' for instant scroll during rapid updates, prevents animation conflicts
      bottomRef.current?.scrollIntoView({ behavior: 'auto', block: 'end' });
    }, 50); // 50ms debounce
  }, []);

  useEffect(() => {
    scrollToBottom();
    return () => {
      if (scrollTimeoutRef.current) {
        clearTimeout(scrollTimeoutRef.current);
      }
    };
  }, [messages, scrollToBottom]);

  const toggle = (id: string) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  return (
    <div 
      ref={containerRef}
      className="flex-1 overflow-y-auto px-6 py-5 flex flex-col gap-2 min-h-0"
      style={{ paddingBottom: hasDrawerOpen ? '280px' : undefined }}
    >
      {messages.map((msg) => (
        <div key={msg.id} className="flex animate-fade-in">
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

          {/* Assistant messages */}
          {msg.role === 'assistant' && (
            <div className="prose max-w-[95%] mt-1">
              {msg.streaming ? (
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {msg.content + '\u258C'}
                </ReactMarkdown>
              ) : (
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {msg.content}
                </ReactMarkdown>
              )}
            </div>
          )}

          {/* Tool calls */}
          {msg.role === 'tool' && !msg.metadata?.isSubAgent && (
            <ToolCallRow
              msg={msg}
              expanded={expanded.has(msg.id)}
              onToggle={() => toggle(msg.id)}
            />
          )}

          {/* Sub-agent blocks */}
          {msg.role === 'tool' && msg.metadata?.isSubAgent && (
            <SubAgentBlock
              msg={msg}
              expanded={expanded.has(msg.id)}
              onToggle={() => toggle(msg.id)}
            />
          )}

          {/* Thinking indicator */}
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

          {/* System messages */}
          {msg.role === 'system' && msg.content !== '::thinking::' && (
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
      ))}
      <div ref={bottomRef} />
    </div>
  );
}

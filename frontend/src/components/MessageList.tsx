import { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import type { Message, SubAgentChild } from '../types';

interface Props {
  messages: Message[];
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

  const statusClass = isPending ? 'tc-pending' : isError ? 'tc-error' : 'tc-success';

  return (
    <div className={`tc-row ${statusClass}`}>
      <button className="tc-compact" onClick={onToggle} title={output ? 'Click to expand output' : undefined}>
        <span className="tc-prefix">{prefix}</span>
        <span className="tc-tool-name">{tool}</span>
        {args && <span className="tc-tool-args">{args}</span>}
        {isPending && <span className="tc-spinner" />}
        {output && !expanded && <span className="tc-expand-hint">{isError ? '(error)' : ''}</span>}
      </button>
      {expanded && output !== undefined && (
        <pre className={`tc-output ${isError ? 'tc-output-error' : ''}`}>
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
    <div className="sa-block">
      <button className="sa-header" onClick={onToggle}>
        <span className="sa-icon">{isPending ? '\u23F3' : '\u2234'}</span>
        <span className="sa-label">{label}</span>
        <span className="sa-sep">&mdash;</span>
        <span className="sa-desc">{description}</span>
      </button>
      <div className="sa-stats">
        {toolCount > 0 && <span className="sa-stat">{toolCount} toolcalls</span>}
        {toolCount > 0 && duration && <span className="sa-dot">&middot;</span>}
        {duration && <span className="sa-stat">{formatDuration(duration)}</span>}
        {isPending && <span className="sa-stat sa-running">running...</span>}
      </div>
      {children.length > 0 && (
        <div className={`sa-children ${expanded ? 'sa-expanded' : 'sa-collapsed'}`}>
          {children.map((child, i) => (
            <div key={child.id || i} className={`sa-child ${child.success === false ? 'sa-child-error' : ''}`}>
              <span className="sa-child-prefix">{toolPrefix(child.tool)}</span>
              <span className="sa-child-name">{child.tool}</span>
              {child.args && <span className="sa-child-args">{child.args}</span>}
            </div>
          ))}
        </div>
      )}
      {expanded && output && (
        <pre className="sa-output">{output}</pre>
      )}
    </div>
  );
}

export function MessageList({ messages }: Props) {
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const toggle = (id: string) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  return (
    <div className="message-list">
      {messages.map((msg) => (
        <div key={msg.id} className={`msg msg-${msg.role}`}>
          {/* User messages */}
          {msg.role === 'user' && (
            <div className={`msg-user-bubble ${msg.metadata?.tool === 'execute' ? 'mode-execute' : ''}`}>
              {msg.metadata?.tool && (
                <span className={`msg-user-mode ${msg.metadata.tool === 'execute' ? 'mode-execute' : ''}`}>{msg.metadata.tool}</span>
              )}
              {msg.content}
            </div>
          )}

          {/* Assistant messages */}
          {msg.role === 'assistant' && (
            <div className="msg-assistant-body">
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
            <div className="msg-thinking">
              <span className="thinking-dots">
                <span /><span /><span />
              </span>
              <span className="thinking-label">Thinking...</span>
            </div>
          )}

          {/* System messages */}
          {msg.role === 'system' && msg.content !== '::thinking::' && (
            <div className="msg-system">{msg.content}</div>
          )}

          {/* Error messages */}
          {msg.role === 'error' && (
            <div className="msg-error">{msg.content}</div>
          )}
        </div>
      ))}
      <div ref={bottomRef} />
    </div>
  );
}

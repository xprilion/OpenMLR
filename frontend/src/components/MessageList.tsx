import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import type { Message } from '../types';

interface Props {
  messages: Message[];
}

export function MessageList({ messages }: Props) {
  const [expanded, setExpanded] = useState<Set<string>>(new Set());

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
          {msg.role === 'user' && (
            <div className="msg-user-bubble">{msg.content}</div>
          )}

          {msg.role === 'assistant' && (
            <div className="msg-assistant-body">
              {msg.streaming ? (
                <span>{msg.content}</span>
              ) : (
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {msg.content}
                </ReactMarkdown>
              )}
            </div>
          )}

          {msg.role === 'tool' && (
            <div className="msg-tool">
              <button
                className={`tool-header ${
                  msg.metadata?.output === undefined
                    ? 'pending'
                    : msg.metadata?.outputSuccess === false
                    ? 'error'
                    : 'success'
                }`}
                onClick={() => toggle(msg.id)}
              >
                <span className="tool-icon">
                  {expanded.has(msg.id) ? '\u25BC' : '\u25B6'}
                </span>
                <span className="tool-name">{msg.metadata?.tool}</span>
                <span className="tool-args">{msg.metadata?.args}</span>
              </button>
              {msg.metadata?.output !== undefined && expanded.has(msg.id) && (
                <pre className={`tool-output ${msg.metadata?.outputSuccess === false ? 'error' : ''}`}>
                  {msg.metadata.output}
                </pre>
              )}
            </div>
          )}

          {msg.role === 'system' && (
            <div className="msg-system">{msg.content}</div>
          )}

          {msg.role === 'error' && (
            <div className="msg-error">{msg.content}</div>
          )}
        </div>
      ))}
    </div>
  );
}

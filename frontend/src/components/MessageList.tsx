import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import type { Message } from '../types';

interface Props {
  messages: Message[];
}

export function MessageList({ messages }: Props) {
  return (
    <div className="message-list">
      {messages.map((msg) => (
        <div key={msg.id} className={`msg msg-${msg.role}`}>
          {msg.role === 'user' && (
            <div className="msg-user-bubble">{msg.content}</div>
          )}

          {msg.role === 'assistant' && (
            <div className="msg-assistant-body">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {msg.content}
              </ReactMarkdown>
            </div>
          )}

          {msg.role === 'tool' && (
            <div className="msg-tool">
              <span className="tool-icon">&#9654;</span>
              <span className="tool-name">{msg.metadata?.tool}</span>
              <span className="tool-args">{msg.metadata?.args}</span>
            </div>
          )}

          {msg.role === 'tool-output' && (
            <pre className={`msg-tool-output ${msg.metadata?.success === false ? 'error' : ''}`}>
              {msg.content}
            </pre>
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

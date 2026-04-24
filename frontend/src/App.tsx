import { useState, useCallback, useRef } from 'react';
import { useSSE } from './hooks/useSSE';
import { api } from './api';
import type { AgentEvent, Message } from './types';
import { MessageList } from './components/MessageList';
import { InputArea } from './components/InputArea';
import { Sidebar } from './components/Sidebar';
import { ModelModal } from './components/ModelModal';
import { ApprovalModal } from './components/ApprovalModal';

let msgId = 0;
const nextId = () => `msg-${++msgId}`;

export default function App() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [status, setStatus] = useState('ready');
  const [model, setModel] = useState('');
  const [approvalEvent, setApprovalEvent] = useState<any>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const streamRef = useRef<Message | null>(null);

  const handleEvent = useCallback((event: AgentEvent) => {
    switch (event.event_type) {
      case 'model_info':
        setModel(event.data?.model || '');
        break;

      case 'status':
        setStatus(event.data?.status || 'ready');
        break;

      case 'processing':
        setIsProcessing(true);
        break;

      case 'assistant_chunk': {
        const chunk = event.data?.content || '';
        setMessages((prev) => {
          if (streamRef.current) {
            streamRef.current.content += chunk;
            return [...prev];
          }
          const msg: Message = {
            id: nextId(),
            role: 'assistant',
            content: chunk,
          };
          streamRef.current = msg;
          return [...prev, msg];
        });
        break;
      }

      case 'assistant_stream_end':
        streamRef.current = null;
        break;

      case 'assistant_message': {
        const content = event.data?.content;
        if (content) {
          setMessages((prev) => [
            ...prev,
            { id: nextId(), role: 'assistant', content },
          ]);
        }
        break;
      }

      case 'tool_call':
        setMessages((prev) => [
          ...prev,
          {
            id: nextId(),
            role: 'tool',
            content: '',
            metadata: {
              tool: event.data?.tool ?? '',
              args: JSON.stringify(event.data?.arguments ?? {}).slice(0, 80),
            },
          },
        ]);
        break;

      case 'tool_output':
        setMessages((prev) => [
          ...prev,
          {
            id: nextId(),
            role: 'tool-output',
            content: event.data?.output || '',
            metadata: { success: event.data?.success },
          },
        ]);
        break;

      case 'tool_log': {
        const tool = event.data?.tool;
        const log = event.data?.log;
        if (tool && log) {
          setMessages((prev) => [
            ...prev,
            {
              id: nextId(),
              role: 'system',
              content: `${tool}: ${log}`,
            },
          ]);
        }
        break;
      }

      case 'approval_required':
        setIsProcessing(false);
        setApprovalEvent(event);
        break;

      case 'turn_complete':
        setIsProcessing(false);
        setApprovalEvent(null);
        break;

      case 'interrupted':
        setIsProcessing(false);
        setApprovalEvent(null);
        streamRef.current = null;
        break;

      case 'error':
        setIsProcessing(false);
        setApprovalEvent(null);
        streamRef.current = null;
        setMessages((prev) => [
          ...prev,
          {
            id: nextId(),
            role: 'error',
            content: event.data?.error || 'Unknown error',
          },
        ]);
        break;

      case 'compacted':
        setMessages((prev) => [
          ...prev,
          {
            id: nextId(),
            role: 'system',
            content: `Context compacted: ${event.data?.old_tokens || 0} -> ${event.data?.new_tokens || 0} tokens`,
          },
        ]);
        break;

      case 'undo_complete':
        setMessages((prev) => [
          ...prev,
          { id: nextId(), role: 'system', content: 'Undone.' },
        ]);
        break;
    }
  }, []);

  const { connected } = useSSE(handleEvent);

  const sendMessage = useCallback(async (text: string) => {
    setMessages((prev) => [...prev, { id: nextId(), role: 'user', content: text }]);
    await api.sendMessage(text);
  }, []);

  return (
    <div className="app">
      <header className="header">
        <div className="header-left">
          <span className="logo">Open-MLR</span>
          <span className={`connection-dot ${connected ? 'connected' : 'disconnected'}`} />
          {!connected && <span className="connection-label">reconnecting...</span>}
        </div>
        <div className="header-right">
          <ModelModal currentModel={model || 'loading...'} onModelChange={setModel} />
          <span className={`status-badge ${status === 'thinking...' ? 'thinking' : ''}`}>
            {status}
          </span>
        </div>
      </header>

      <div className="main">
        <Sidebar onAction={(type) => {
          if (type === 'undo') setMessages((prev) => prev);
          if (type === 'compact') setMessages((prev) => prev);
        }} />

        <div className="chat">
          <MessageList messages={messages} />

          {approvalEvent && (
            <ApprovalModal
              event={approvalEvent}
              onClose={() => setApprovalEvent(null)}
            />
          )}

          <InputArea disabled={isProcessing} onSend={sendMessage} />
        </div>
      </div>
    </div>
  );
}

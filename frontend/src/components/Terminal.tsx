import { useEffect, useRef, useState, useCallback } from 'react';
import {
  Terminal as TerminalIcon,
  X,
  Maximize2,
  Minimize2,
} from 'lucide-react';

interface Props {
  projectUuid: string | null;
  visible: boolean;
  onToggle: () => void;
}

/**
 * Interactive terminal connected to the project workspace via WebSocket.
 * Uses a basic approach without xterm.js dependency — renders terminal output
 * in a pre element and captures keyboard input.
 *
 * For a production deployment, install @xterm/xterm and use the attach addon.
 * This implementation provides core functionality without the extra dependency.
 */
export function Terminal({ projectUuid, visible, onToggle }: Props) {
  const [connected, setConnected] = useState(false);
  const [output, setOutput] = useState<string[]>([]);
  const [maximized, setMaximized] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const outputRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const [inputLine, setInputLine] = useState('');
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const connect = useCallback(() => {
    if (!projectUuid) return;

    const token = localStorage.getItem('openmlr_token');
    if (!token) return;

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/api/terminal/${projectUuid}?token=${token}`;

    try {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        setConnected(true);
        setOutput((prev) => [...prev, '\r\n--- Connected ---\r\n']);
        // Send initial resize
        ws.send(JSON.stringify({ type: 'resize', cols: 120, rows: 30 }));
      };

      ws.onmessage = (event) => {
        if (event.data instanceof Blob) {
          event.data.text().then((text: string) => {
            setOutput((prev) => [...prev, text]);
          });
        } else {
          setOutput((prev) => [...prev, event.data]);
        }
      };

      ws.onclose = () => {
        setConnected(false);
        setOutput((prev) => [...prev, '\r\n--- Disconnected ---\r\n']);
        wsRef.current = null;
      };

      ws.onerror = () => {
        setConnected(false);
      };
    } catch {
      setConnected(false);
    }
  }, [projectUuid]);

  // Connect when visible and project is set
  useEffect(() => {
    if (visible && projectUuid && !wsRef.current) {
      connect();
    }
    return () => {
      if (reconnectTimer.current) {
        clearTimeout(reconnectTimer.current);
      }
    };
  }, [visible, projectUuid, connect]);

  // Disconnect when hidden
  useEffect(() => {
    if (!visible && wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
  }, [visible]);

  // Auto-scroll to bottom
  useEffect(() => {
    if (outputRef.current) {
      outputRef.current.scrollTop = outputRef.current.scrollHeight;
    }
  }, [output]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;

    if (e.key === 'Enter') {
      e.preventDefault();
      wsRef.current.send(JSON.stringify({ type: 'input', data: inputLine + '\n' }));
      setInputLine('');
    } else if (e.key === 'Tab') {
      e.preventDefault();
      wsRef.current.send(JSON.stringify({ type: 'input', data: '\t' }));
    } else if (e.ctrlKey && e.key === 'c') {
      e.preventDefault();
      wsRef.current.send(JSON.stringify({ type: 'input', data: '\x03' }));
    } else if (e.ctrlKey && e.key === 'd') {
      e.preventDefault();
      wsRef.current.send(JSON.stringify({ type: 'input', data: '\x04' }));
    } else if (e.ctrlKey && e.key === 'l') {
      e.preventDefault();
      wsRef.current.send(JSON.stringify({ type: 'input', data: '\x0c' }));
      setOutput([]);
    }
  }, [inputLine]);

  if (!visible) {
    return (
      <button
        className="fixed bottom-4 right-4 z-30 w-10 h-10 rounded-lg bg-surface border border-border flex items-center justify-center text-text-dim hover:text-text hover:border-primary transition-all shadow-md"
        onClick={onToggle}
        title="Open terminal"
      >
        <TerminalIcon size={18} />
      </button>
    );
  }

  return (
    <div
      className={`bg-[#0d0d0d] border-t border-border flex flex-col ${
        maximized ? 'fixed inset-0 z-50' : ''
      }`}
      style={maximized ? undefined : { height: '280px' }}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-1.5 bg-[#1a1a1a] border-b border-border shrink-0">
        <div className="flex items-center gap-2">
          <TerminalIcon size={14} className="text-primary" />
          <span className="text-xs font-medium text-text">Terminal</span>
          <span className={`w-2 h-2 rounded-full ${connected ? 'bg-success' : 'bg-error'}`} />
          {!connected && projectUuid && (
            <button
              className="text-xs text-primary hover:underline"
              onClick={connect}
            >
              Connect
            </button>
          )}
          {!projectUuid && (
            <span className="text-xs text-text-dim">No project selected</span>
          )}
        </div>
        <div className="flex items-center gap-1">
          <button
            className="w-6 h-6 rounded flex items-center justify-center text-text-dim hover:text-text hover:bg-surface-hover transition-colors"
            onClick={() => setMaximized(!maximized)}
            title={maximized ? 'Minimize' : 'Maximize'}
          >
            {maximized ? <Minimize2 size={12} /> : <Maximize2 size={12} />}
          </button>
          <button
            className="w-6 h-6 rounded flex items-center justify-center text-text-dim hover:text-text hover:bg-surface-hover transition-colors"
            onClick={onToggle}
            title="Close terminal"
          >
            <X size={12} />
          </button>
        </div>
      </div>

      {/* Output area */}
      <div
        ref={outputRef}
        className="flex-1 overflow-auto px-3 py-2 font-mono text-xs text-green-400 whitespace-pre-wrap"
        onClick={() => inputRef.current?.focus()}
      >
        {output.join('')}
      </div>

      {/* Input line */}
      <div className="flex items-center gap-2 px-3 py-1.5 bg-[#1a1a1a] border-t border-border shrink-0">
        <span className="text-xs text-primary font-mono">$</span>
        <textarea
          ref={inputRef}
          className="flex-1 bg-transparent text-xs text-green-400 font-mono outline-none resize-none"
          rows={1}
          value={inputLine}
          onChange={(e) => setInputLine(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={connected ? 'Type command...' : 'Not connected'}
          disabled={!connected}
          autoFocus
        />
      </div>
    </div>
  );
}

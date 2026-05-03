
import { useEffect, useRef, useState, useCallback } from 'react';
import {
  Terminal as TerminalIcon,
  Maximize2,
  Minimize2,
} from 'lucide-react';
import { Terminal as XTerm } from '@xterm/xterm';
import { FitAddon } from '@xterm/addon-fit';
import { WebLinksAddon } from '@xterm/addon-web-links';
import '@xterm/xterm/css/xterm.css';

interface Props {
  readonly projectUuid: string | null;
  readonly visible: boolean;
  readonly onConnectionChange?: (connected: boolean) => void;
}

export function Terminal({ projectUuid, visible, onConnectionChange }: Props) {
  const [connected, setConnected] = useState(false);
  const [maximized, setMaximized] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const termRef = useRef<XTerm | null>(null);
  const fitAddonRef = useRef<FitAddon | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const termInitialized = useRef(false);

  // Initialize xterm instance once
  const initTerm = useCallback(() => {
    if (termInitialized.current || !containerRef.current) return;

    const term = new XTerm({
      cursorBlink: true,
      fontSize: 13,
      fontFamily: "'JetBrains Mono', 'Fira Code', 'Cascadia Code', Menlo, Monaco, monospace",
      theme: {
        background: '#0d0d0d',
        foreground: '#e0e0e0',
        cursor: '#3b82f6',
        selectionBackground: '#3b82f640',
        black: '#1a1a1a',
        red: '#ef4444',
        green: '#22c55e',
        yellow: '#eab308',
        blue: '#3b82f6',
        magenta: '#a855f7',
        cyan: '#06b6d4',
        white: '#e0e0e0',
        brightBlack: '#525252',
        brightRed: '#f87171',
        brightGreen: '#4ade80',
        brightYellow: '#fde047',
        brightBlue: '#60a5fa',
        brightMagenta: '#c084fc',
        brightCyan: '#22d3ee',
        brightWhite: '#ffffff',
      },
      scrollback: 5000,
      convertEol: true,
      allowProposedApi: true,
    });

    const fitAddon = new FitAddon();
    term.loadAddon(fitAddon);
    term.loadAddon(new WebLinksAddon());

    term.open(containerRef.current);
    fitAddon.fit();

    termRef.current = term;
    fitAddonRef.current = fitAddon;
    termInitialized.current = true;

    return term;
  }, []);

  // Connect WebSocket
  const connect = useCallback(() => {
    const token = localStorage.getItem('openmlr_token');
    if (!token) return;

    const term = termRef.current || initTerm();
    if (!term) return;

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const path = projectUuid ? `/api/terminal/${projectUuid}` : '/api/terminal';
    const wsUrl = `${protocol}//${window.location.host}${path}?token=${token}`;

    try {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.binaryType = 'arraybuffer';

      ws.onopen = () => {
        setConnected(true);
        onConnectionChange?.(true);
        // Send resize to match current terminal dimensions
        const dims = fitAddonRef.current?.proposeDimensions();
        if (dims) {
          ws.send(JSON.stringify({ type: 'resize', cols: dims.cols, rows: dims.rows }));
        }
      };

      ws.onmessage = (event) => {
        if (event.data instanceof ArrayBuffer) {
          term.write(new Uint8Array(event.data));
        } else {
          term.write(event.data);
        }
      };

      ws.onclose = () => {
        setConnected(false);
        onConnectionChange?.(false);
        term.writeln('\r\n\x1b[90m--- Disconnected ---\x1b[0m');
        wsRef.current = null;
      };

      ws.onerror = () => {
        setConnected(false);
        onConnectionChange?.(false);
      };

      // Forward terminal input to WebSocket
      term.onData((data) => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: 'input', data }));
        }
      });

    } catch {
      setConnected(false);
      onConnectionChange?.(false);
    }
  }, [projectUuid, initTerm, onConnectionChange]);

  // Connect when visible
  useEffect(() => {
    if (visible && !wsRef.current) {
      // Small delay to ensure container is rendered
      const timer = setTimeout(() => connect(), 50);
      return () => clearTimeout(timer);
    }
  }, [visible, projectUuid, connect]);

  // Disconnect when hidden
  useEffect(() => {
    if (!visible && wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
  }, [visible]);

  // Fit terminal on resize or maximize toggle
  useEffect(() => {
    if (!visible || !fitAddonRef.current) return;

    const handleResize = () => {
      fitAddonRef.current?.fit();
      // Notify backend of new size
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        const dims = fitAddonRef.current?.proposeDimensions();
        if (dims) {
          wsRef.current.send(JSON.stringify({ type: 'resize', cols: dims.cols, rows: dims.rows }));
        }
      }
    };

    // Fit after layout settles
    const timer = setTimeout(handleResize, 100);
    window.addEventListener('resize', handleResize);
    return () => {
      clearTimeout(timer);
      window.removeEventListener('resize', handleResize);
    };
  }, [visible, maximized]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      wsRef.current?.close();
      termRef.current?.dispose();
      termInitialized.current = false;
    };
  }, []);

  return (
    <div
      className={`bg-[#0d0d0d] flex flex-col ${
        maximized ? 'fixed inset-0 z-50' : 'flex-1 h-full'
      } ${visible ? '' : 'hidden'}`}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-1.5 bg-[#1a1a1a] border-b border-border shrink-0">
        <div className="flex items-center gap-2">
          <TerminalIcon size={14} className="text-primary" />
          <span className="text-xs font-medium text-text">Terminal</span>
          <span className={`w-2 h-2 rounded-full ${connected ? 'bg-success' : 'bg-error'}`} />
          {!connected && (
            <button
              className="text-xs text-primary hover:underline"
              onClick={connect}
            >
              Connect
            </button>
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
        </div>
      </div>

      {/* xterm.js container */}
      <div className="flex-1 min-h-0 px-1 relative">
        <div ref={containerRef} className="h-full w-full" />
        <button
          type="button"
          className="absolute inset-0 w-full h-full cursor-text bg-transparent"
          onClick={() => termRef.current?.focus()}
          aria-label="Click to focus terminal"
        />
      </div>
    </div>
  );
}

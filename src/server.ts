import { config } from "dotenv";
import { resolve } from "path";
import { readFileSync } from "fs";
import { Session, runAgentTurn, handleApproval, undoSession, compactSession, loadConfig } from "./agent/index.js";
import { saveProjectConfig } from "./project-config.js";

config({ path: resolve(process.cwd(), ".env") });

const agentConfig = loadConfig();
const session = new Session(agentConfig);

// ---- SSE clients with heartbeat ----
interface Client {
  controller: ReadableStreamDefaultController;
  encoder: TextEncoder;
  heartbeat: ReturnType<typeof setInterval>;
}

const clients = new Set<Client>();
let isProcessing = false;
let messageQueue: string[] = [];

function makeEventPayload(event: any): string {
  return `data: ${JSON.stringify(event)}\n\n`;
}

function broadcast(event: any) {
  const payload = makeEventPayload(event);
  for (const client of clients) {
    try {
      client.controller.enqueue(client.encoder.encode(payload));
    } catch {
      cleanupClient(client);
    }
  }
}

function cleanupClient(client: Client) {
  clearInterval(client.heartbeat);
  clients.delete(client);
  try { client.controller.close(); } catch {}
}

function addClient(controller: ReadableStreamDefaultController) {
  const encoder = new TextEncoder();
  const client: Client = {
    controller,
    encoder,
    heartbeat: setInterval(() => {
      try {
        controller.enqueue(encoder.encode(':ping\n\n'));
      } catch {
        cleanupClient(client);
      }
    }, 20000),
  };
  clients.add(client);

  // Send initial model info
  broadcast({
    event_type: "model_info",
    data: { model: session.config.model_name },
  });
}

session.onEvent(broadcast);

async function processQueue() {
  if (isProcessing || messageQueue.length === 0) return;
  isProcessing = true;
  broadcast({ event_type: "status", data: { status: "thinking..." } });

  while (messageQueue.length > 0) {
    const msg = messageQueue.shift()!;
    try {
      await runAgentTurn(session, msg);
    } catch (e: any) {
      broadcast({ event_type: "error", data: { error: e.message || String(e) } });
    }
  }

  isProcessing = false;
  broadcast({ event_type: "status", data: { status: "ready" } });
}

// ---- Static file serving ----
const FRONTEND_DIST = resolve(process.cwd(), "frontend", "dist");

function getMimeType(path: string): string {
  if (path.endsWith('.html')) return 'text/html';
  if (path.endsWith('.js')) return 'application/javascript';
  if (path.endsWith('.css')) return 'text/css';
  if (path.endsWith('.svg')) return 'image/svg+xml';
  if (path.endsWith('.png')) return 'image/png';
  if (path.endsWith('.json')) return 'application/json';
  return 'application/octet-stream';
}

async function serveStatic(pathname: string): Promise<Response | null> {
  // Security: prevent directory traversal
  const safePath = pathname.replace(/\.\.\//g, '').replace(/^\//, '');
  const filePath = resolve(FRONTEND_DIST, safePath || 'index.html');

  // Ensure we're still inside the dist dir
  if (!filePath.startsWith(FRONTEND_DIST)) {
    return null;
  }

  try {
    const file = Bun.file(filePath);
    if (!(await file.exists())) {
      return null;
    }
    return new Response(file, {
      headers: { 'Content-Type': getMimeType(filePath) },
    });
  } catch {
    return null;
  }
}

// ---- Server ----
const PORT = Number(process.env.PORT) || 3000;

Bun.serve({
  port: PORT,
  development: false,
  async fetch(req) {
    const url = new URL(req.url);

    // API routes
    if (url.pathname.startsWith('/api/')) {
      // CORS for dev
      const corsHeaders = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type',
      };

      if (req.method === 'OPTIONS') {
        return new Response(null, { headers: corsHeaders });
      }

      // SSE events
      if (url.pathname === '/api/events') {
        const stream = new ReadableStream({
          start(controller) {
            addClient(controller);
          },
          cancel() {
            // Client disconnected; heartbeat interval cleans up via catch
          },
        });
        return new Response(stream, {
          headers: {
            'Content-Type': 'text/event-stream',
            'Cache-Control': 'no-cache',
            Connection: 'keep-alive',
            ...corsHeaders,
          },
        });
      }

      // POST message
      if (url.pathname === '/api/message' && req.method === 'POST') {
        const { message } = await req.json();
        messageQueue.push(message);
        processQueue();
        return Response.json({ ok: true }, { headers: corsHeaders });
      }

      // POST approval
      if (url.pathname === '/api/approval' && req.method === 'POST') {
        const { approvals } = await req.json();
        handleApproval(session, approvals).catch((e: any) => {
          broadcast({ event_type: "error", data: { error: String(e) } });
        });
        return Response.json({ ok: true }, { headers: corsHeaders });
      }

      // POST undo
      if (url.pathname === '/api/undo' && req.method === 'POST') {
        undoSession(session);
        return Response.json({ ok: true }, { headers: corsHeaders });
      }

      // POST compact
      if (url.pathname === '/api/compact' && req.method === 'POST') {
        compactSession(session);
        return Response.json({ ok: true }, { headers: corsHeaders });
      }

      // POST model switch
      if (url.pathname === '/api/model' && req.method === 'POST') {
        const { model } = await req.json();
        session.updateModel(model);
        saveProjectConfig({ model_name: model });
        broadcast({ event_type: "model_info", data: { model } });
        return Response.json({ ok: true }, { headers: corsHeaders });
      }

      return new Response("Not found", { status: 404, headers: corsHeaders });
    }

    // Static files (built frontend)
    const staticResponse = await serveStatic(url.pathname);
    if (staticResponse) return staticResponse;

    // Fallback to index.html for SPA routing
    const indexFile = Bun.file(resolve(FRONTEND_DIST, 'index.html'));
    if (await indexFile.exists()) {
      return new Response(indexFile, { headers: { 'Content-Type': 'text/html' } });
    }

    return new Response("Not found", { status: 404 });
  },
});

console.log(`Open-MLR server running at http://localhost:${PORT}`);

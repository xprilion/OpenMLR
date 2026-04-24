import { createServer } from "http";
import { config } from "dotenv";
import { resolve } from "path";
import { readFile, access } from "fs/promises";
import { constants } from "fs";
import { Session, runAgentTurn, handleApproval, undoSession, compactSession, loadConfig } from "./agent/index.js";
import { saveProjectConfig } from "./project-config.js";

config({ path: resolve(process.cwd(), ".env") });

const agentConfig = loadConfig();
const session = new Session(agentConfig);

// ---- SSE clients with heartbeat ----
interface Client {
  res: import("http").ServerResponse;
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
      client.res.write(payload);
    } catch {
      cleanupClient(client);
    }
  }
}

function cleanupClient(client: Client) {
  clearInterval(client.heartbeat);
  clients.delete(client);
  try { client.res.end(); } catch {}
}

function addClient(res: import("http").ServerResponse) {
  res.writeHead(200, {
    "Content-Type": "text/event-stream",
    "Cache-Control": "no-cache",
    Connection: "keep-alive",
  });

  const client: Client = {
    res,
    heartbeat: setInterval(() => {
      try {
        res.write(":ping\n\n");
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

async function fileExists(filePath: string): Promise<boolean> {
  try {
    await access(filePath, constants.F_OK);
    return true;
  } catch {
    return false;
  }
}

async function serveStatic(pathname: string): Promise<{ data: Buffer; mimeType: string } | null> {
  const safePath = pathname.replace(/\.\.\//g, '').replace(/^\//, '');
  const filePath = resolve(FRONTEND_DIST, safePath || 'index.html');

  if (!filePath.startsWith(FRONTEND_DIST)) {
    return null;
  }

  try {
    if (!(await fileExists(filePath))) {
      return null;
    }
    const data = await readFile(filePath);
    return { data, mimeType: getMimeType(filePath) };
  } catch {
    return null;
  }
}

async function readBody(req: import("http").IncomingMessage): Promise<any> {
  return new Promise((resolve, reject) => {
    let body = "";
    req.on("data", (chunk) => { body += chunk; });
    req.on("end", () => {
      try {
        resolve(JSON.parse(body));
      } catch {
        resolve({});
      }
    });
    req.on("error", reject);
  });
}

// ---- Server ----
const PORT = Number(process.env.PORT) || 3000;

const server = createServer(async (req, res) => {
  const url = new URL(req.url || "/", `http://${req.headers.host}`);

  // CORS for dev
  const corsHeaders: Record<string, string> = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
  };

  if (req.method === "OPTIONS") {
    res.writeHead(204, corsHeaders);
    res.end();
    return;
  }

  // API routes
  if (url.pathname.startsWith('/api/')) {
    // SSE events
    if (url.pathname === '/api/events') {
      addClient(res);
      req.on('close', () => {
        for (const client of clients) {
          if (client.res === res) {
            cleanupClient(client);
            break;
          }
        }
      });
      return;
    }

    // POST message
    if (url.pathname === '/api/message' && req.method === 'POST') {
      const { message } = await readBody(req);
      messageQueue.push(message);
      processQueue();
      res.writeHead(200, { "Content-Type": "application/json", ...corsHeaders });
      res.end(JSON.stringify({ ok: true }));
      return;
    }

    // POST approval
    if (url.pathname === '/api/approval' && req.method === 'POST') {
      const { approvals } = await readBody(req);
      handleApproval(session, approvals).catch((e: any) => {
        broadcast({ event_type: "error", data: { error: String(e) } });
      });
      res.writeHead(200, { "Content-Type": "application/json", ...corsHeaders });
      res.end(JSON.stringify({ ok: true }));
      return;
    }

    // POST undo
    if (url.pathname === '/api/undo' && req.method === 'POST') {
      undoSession(session);
      res.writeHead(200, { "Content-Type": "application/json", ...corsHeaders });
      res.end(JSON.stringify({ ok: true }));
      return;
    }

    // POST compact
    if (url.pathname === '/api/compact' && req.method === 'POST') {
      compactSession(session);
      res.writeHead(200, { "Content-Type": "application/json", ...corsHeaders });
      res.end(JSON.stringify({ ok: true }));
      return;
    }

    // POST model switch
    if (url.pathname === '/api/model' && req.method === 'POST') {
      const { model } = await readBody(req);
      session.updateModel(model);
      saveProjectConfig({ model_name: model });
      broadcast({ event_type: "model_info", data: { model } });
      res.writeHead(200, { "Content-Type": "application/json", ...corsHeaders });
      res.end(JSON.stringify({ ok: true }));
      return;
    }

    res.writeHead(404, { ...corsHeaders });
    res.end("Not found");
    return;
  }

  // Static files (built frontend)
  const staticResponse = await serveStatic(url.pathname);
  if (staticResponse) {
    res.writeHead(200, { "Content-Type": staticResponse.mimeType });
    res.end(staticResponse.data);
    return;
  }

  // Fallback to index.html for SPA routing
  const indexPath = resolve(FRONTEND_DIST, 'index.html');
  if (await fileExists(indexPath)) {
    const data = await readFile(indexPath);
    res.writeHead(200, { "Content-Type": "text/html" });
    res.end(data);
    return;
  }

  res.writeHead(404);
  res.end("Not found");
});

server.listen(PORT, () => {
  console.log(`Open-MLR server running at http://localhost:${PORT}`);
});

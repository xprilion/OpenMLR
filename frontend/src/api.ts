const TOKEN_KEY = 'openmlr_token';

function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string | null) {
  if (token) {
    localStorage.setItem(TOKEN_KEY, token);
  } else {
    localStorage.removeItem(TOKEN_KEY);
  }
}

function authHeaders(): Record<string, string> {
  const token = getToken();
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  return headers;
}

async function request(method: string, path: string, body?: unknown) {
  const opts: RequestInit = {
    method,
    headers: authHeaders(),
  };
  if (body !== undefined) {
    opts.body = JSON.stringify(body);
  }
  const res = await fetch(path, opts);

  if (res.status === 401) {
    // Token expired or invalid — clear it; App.tsx catch handler shows login
    setToken(null);
    throw new Error('Unauthorized');
  }

  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: `HTTP ${res.status}` }));
    throw new Error(err.detail || err.error || `HTTP ${res.status}`);
  }
  return res.json();
}

async function post(path: string, body: unknown) {
  return request('POST', path, body);
}

async function get(path: string) {
  return request('GET', path);
}

async function put(path: string, body: unknown) {
  return request('PUT', path, body);
}

async function del(path: string) {
  return request('DELETE', path);
}

export const api = {
  // Auth
  checkSetup: () => get('/api/auth/check'),
  register: (username: string, password: string, display_name?: string) =>
    post('/api/auth/register', { username, password, display_name }),
  login: (username: string, password: string) =>
    post('/api/auth/login', { username, password }),
  getMe: () => get('/api/auth/me'),

  // Messages
  sendMessage: (message: string, mode?: string, mentions?: Array<{ type: string; value: string }>) =>
    post('/api/message', { message, mode, request_id: crypto.randomUUID(), mentions: mentions?.length ? mentions : undefined }),
  submitAnswers: (answers: Record<string, string>) => post('/api/answers', { answers }),
  interrupt: () => post('/api/interrupt', {}),
  sendApproval: (approvals: Record<string, boolean>) => post('/api/approval', { approvals }),
  submitTodoApproval: (approved: boolean, tasks?: any[]) =>
    post('/api/todo-approval', { approved, tasks }),
  undo: () => post('/api/undo', {}),
  compact: () => post('/api/compact', {}),
  setModel: (model: string) => post('/api/model', { model }),

  // Conversations
  listConversations: () => get('/api/conversations'),
  createConversation: (title?: string, model?: string, mode?: string, projectUuid?: string) =>
    post('/api/conversations', { title, model, mode, project_uuid: projectUuid }),
  getConversation: (uuid: string) => get(`/api/conversations/${uuid}`),
  deleteConversation: (uuid: string) => del(`/api/conversations/${uuid}`),
  searchConversations: (query: string, projectUuid?: string) => {
    const params = new URLSearchParams({ q: query });
    if (projectUuid) params.set('project_uuid', projectUuid);
    return get(`/api/conversations/search?${params.toString()}`);
  },
  switchConversation: (uuid: string) => post(`/api/conversations/${uuid}/switch`, {}),
  getConversationCompute: (uuid: string) => get(`/api/conversations/${uuid}/compute`),
  setConversationCompute: (uuid: string, nodeId: number | null) =>
    post(`/api/conversations/${uuid}/compute`, { node_id: nodeId }),
  clearConversationCompute: (uuid: string) => del(`/api/conversations/${uuid}/compute`),

  // Settings
  getSettings: () => get('/api/settings'),
  getSettingsCategory: (category: string) => get(`/api/settings/${category}`),
  updateSetting: (category: string, key: string, value: any) =>
    put(`/api/settings/${category}/${key}`, { value }),
  deleteSetting: (category: string, key: string) => del(`/api/settings/${category}/${key}`),

  // Reports
  getReport: (reportId: string) => get(`/api/reports/${reportId}`),

  // Background Jobs
  getJobStatus: (jobId: string) => get(`/api/jobs/${jobId}`),
  getConversationJobs: (uuid: string) => get(`/api/conversations/${uuid}/jobs`),
  cancelJob: (jobId: string) => post(`/api/jobs/${jobId}/cancel`, {}),

  // Providers & Models
  getProviders: () => get('/api/providers'),
  getModels: (provider?: string) => get(`/api/models${provider ? `?provider=${encodeURIComponent(provider)}` : ''}`),
  getStatus: () => get('/api/status'),
  saveConfig: (config: Record<string, string>) => post('/api/config', config),
  fetchCustomProviderModels: (providerId: string) => post(`/api/providers/${encodeURIComponent(providerId)}/fetch-models`, {}),

  // SSH Keys
  getKeys: () => get('/api/keys'),
  createKey: (body: Record<string, any>) => post('/api/keys', body),
  deleteKey: (filename: string) => del(`/api/keys/${filename}`),

  // Projects
  listProjects: (includeArchived = false) => get(`/api/projects${includeArchived ? '?include_archived=true' : ''}`),
  createProject: (name: string, description?: string) => post('/api/projects', { name, description }),
  getProject: (uuid: string) => get(`/api/projects/${uuid}`),
  updateProject: (uuid: string, body: Record<string, any>) => put(`/api/projects/${uuid}`, body),
  deleteProject: (uuid: string) => del(`/api/projects/${uuid}`),
  listProjectConversations: (uuid: string) => get(`/api/projects/${uuid}/conversations`),
  attachConversation: (projectUuid: string, convUuid: string) =>
    post(`/api/projects/${projectUuid}/attach/${convUuid}`, {}),
  detachConversation: (projectUuid: string, convUuid: string) =>
    post(`/api/projects/${projectUuid}/detach/${convUuid}`, {}),

  // Project Files
  listFiles: (projectUuid: string, path = '') =>
    get(`/api/projects/${projectUuid}/files${path ? `?path=${encodeURIComponent(path)}` : ''}`),
  readFile: (projectUuid: string, filePath: string) =>
    get(`/api/projects/${projectUuid}/files/${encodeURIComponent(filePath)}`),
  /** Build an authenticated URL for directly loading a binary file (e.g. images). */
  fileUrl: (projectUuid: string, filePath: string): string => {
    const token = getToken();
    const base = `/api/projects/${projectUuid}/files/${encodeURIComponent(filePath)}`;
    return token ? `${base}?token=${token}` : base;
  },
  writeFile: (projectUuid: string, filePath: string, content: string) =>
    put(`/api/projects/${projectUuid}/files/${encodeURIComponent(filePath)}`, { content }),
  deleteFile: (projectUuid: string, filePath: string) =>
    del(`/api/projects/${projectUuid}/files/${encodeURIComponent(filePath)}`),

  // Compute Nodes
  getComputeNodes: () => get('/api/compute/nodes'),
  createComputeNode: (body: Record<string, any>) => post('/api/compute/nodes', body),
  getComputeNode: (id: number) => get(`/api/compute/nodes/${id}`),
  updateComputeNode: (id: number, body: Record<string, any>) => put(`/api/compute/nodes/${id}`, body),
  deleteComputeNode: (id: number) => del(`/api/compute/nodes/${id}`),
  testComputeNode: (id: number) => post(`/api/compute/nodes/${id}/test`, {}),
  testComputeConfig: (type: string, config: Record<string, any>) =>
    post('/api/compute/test', { type, config }),
  probeComputeNode: (id: number) => post(`/api/compute/nodes/${id}/probe`, {}),
  setDefaultComputeNode: (id: number) => post(`/api/compute/nodes/${id}/set-default`, {}),

  // MCP Servers
  getMcpStatus: () => get('/api/mcp/status'),
  testMcpServer: (url: string, headers?: Record<string, string>, params?: Record<string, string>) =>
    post('/api/mcp/test', { url, headers: headers || null, params: params || null }),

  // Peer Review Simulation
  getReviewRubrics: () => get('/api/review/rubrics'),
  evaluateSubmission: (body: {
    submission_text: string;
    venue?: string;
    title?: string;
    context?: Record<string, unknown>;
  }) => post('/api/review/evaluate', body),
  reviewProjectWorkspace: (
    projectId: number,
    body: { venue?: string; include_latex?: boolean; include_notes?: boolean }
  ) => post(`/api/projects/${projectId}/review`, body),

  // Evaluation & Benchmark Harness
  listEvalSuites: () => get('/api/eval/suites'),
  listEvalTasks: (category?: string) =>
    get(`/api/eval/tasks${category ? `?category=${encodeURIComponent(category)}` : ''}`),
  getEvalTask: (taskId: string) => get(`/api/eval/tasks/${encodeURIComponent(taskId)}`),
  evaluateTask: (taskId: string, agentOutput: unknown) =>
    post(`/api/eval/tasks/${encodeURIComponent(taskId)}/evaluate`, { agent_output: agentOutput }),
  runEvalSuite: (suiteName = 'reproduction', maxConcurrency = 4, simulatedOutputs?: Record<string, unknown>) =>
    post('/api/eval/run', {
      suite_name: suiteName,
      max_concurrency: maxConcurrency,
      simulated_outputs: simulatedOutputs,
    }),
  registerCustomReproductionTask: (body: Record<string, unknown>) =>
    post('/api/eval/custom-task/reproduction', body),
  registerCustomOptimizationTask: (body: Record<string, unknown>) =>
    post('/api/eval/custom-task/optimization', body),

  // Research State Machine & Orchestrator
  getResearchPhases: () => get('/api/research/phases'),
  getResearchGuidelines: () => get('/api/research/guidelines'),
  getProjectResearchState: (projectId: number) =>
    get(`/api/projects/${projectId}/research/state`),
  startProjectResearch: (
    projectId: number,
    body: { goal: string; initial_phase?: string; generate_default_milestones?: boolean }
  ) => post(`/api/projects/${projectId}/research/start`, body),
  transitionProjectResearchPhase: (
    projectId: number,
    body: { next_phase: string; reason: string; artifacts_produced?: string[]; milestone_id?: string }
  ) => post(`/api/projects/${projectId}/research/transition`, body),
  createResearchMilestone: (
    projectId: number,
    body: { title: string; description?: string; phase?: string; criteria?: string[] }
  ) => post(`/api/projects/${projectId}/research/milestones`, body),
  updateResearchMilestone: (
    projectId: number,
    milestoneId: string,
    body: { status?: string; output_artifacts?: string[] }
  ) => put(`/api/projects/${projectId}/research/milestones/${encodeURIComponent(milestoneId)}`, body),
  addResearchArtifact: (
    projectId: number,
    body: { type: string; data: unknown; section_name?: string }
  ) => post(`/api/projects/${projectId}/research/artifacts`, body),

  // Machine Learning Experiments & Runs
  listExperimentRuns: (params?: {
    projectUuid?: string;
    status?: string;
    search?: string;
    limit?: number;
    offset?: number;
  }) => {
    const q = new URLSearchParams();
    if (params?.projectUuid) q.append('project_uuid', params.projectUuid);
    if (params?.status) q.append('status', params.status);
    if (params?.search) q.append('search', params.search);
    if (params?.limit) q.append('limit', String(params.limit));
    if (params?.offset) q.append('offset', String(params.offset));
    const qs = q.toString();
    return get(`/api/experiments/runs${qs ? `?${qs}` : ''}`);
  },
  createExperimentRun: (body: {
    name: string;
    description?: string;
    hyperparameters?: Record<string, unknown>;
    compute_target?: string;
    tags?: string[];
    total_steps?: number;
    total_epochs?: number;
    project_uuid?: string;
  }) => post('/api/experiments/runs', body),
  getExperimentRun: (runId: string, projectUuid?: string) =>
    get(`/api/experiments/runs/${encodeURIComponent(runId)}${projectUuid ? `?project_uuid=${encodeURIComponent(projectUuid)}` : ''}`),
  logRunMetrics: (
    runId: string,
    body: { step: number; epoch?: number; metrics: Record<string, number>; timestamp?: number },
    projectUuid?: string
  ) => post(`/api/experiments/runs/${encodeURIComponent(runId)}/metrics${projectUuid ? `?project_uuid=${encodeURIComponent(projectUuid)}` : ''}`, body),
  updateRunStatus: (
    runId: string,
    body: { status: string; reason?: string },
    projectUuid?: string
  ) => post(`/api/experiments/runs/${encodeURIComponent(runId)}/status${projectUuid ? `?project_uuid=${encodeURIComponent(projectUuid)}` : ''}`, body),
  appendRunLogs: (runId: string, lines: string[], projectUuid?: string) =>
    post(`/api/experiments/runs/${encodeURIComponent(runId)}/logs${projectUuid ? `?project_uuid=${encodeURIComponent(projectUuid)}` : ''}`, { lines }),
  getRunLogs: (runId: string, limit = 200, projectUuid?: string) =>
    get(`/api/experiments/runs/${encodeURIComponent(runId)}/logs?limit=${limit}${projectUuid ? `&project_uuid=${encodeURIComponent(projectUuid)}` : ''}`),
  registerRunCheckpoint: (
    runId: string,
    body: {
      name: string;
      step: number;
      epoch?: number;
      path?: string;
      file_size_mb?: number;
      metrics?: Record<string, number>;
      download_url?: string;
    },
    projectUuid?: string
  ) => post(`/api/experiments/runs/${encodeURIComponent(runId)}/checkpoints${projectUuid ? `?project_uuid=${encodeURIComponent(projectUuid)}` : ''}`, body),
  compareExperimentRuns: (runIds: string[], projectUuid?: string) =>
    get(`/api/experiments/compare?run_ids=${encodeURIComponent(runIds.join(','))}${projectUuid ? `&project_uuid=${encodeURIComponent(projectUuid)}` : ''}`),
  deleteExperimentRun: (runId: string, projectUuid?: string) =>
    del(`/api/experiments/runs/${encodeURIComponent(runId)}${projectUuid ? `?project_uuid=${encodeURIComponent(projectUuid)}` : ''}`),
};

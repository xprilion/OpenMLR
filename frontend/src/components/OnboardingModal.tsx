import { useState, useEffect, useMemo } from 'react';
import { api } from '../api';
import type { Project } from '../types';

interface Provider {
  id: string;
  name: string;
  key_env: string;
  configured: boolean;
  categories?: string[];
}

interface ModelInfo {
  id: string;
  name: string;
  provider: string;
}

interface Props {
  onComplete: (model: string, project?: Project) => void;
}

export function OnboardingModal({ onComplete }: Props) {
  const [step, setStep] = useState<'providers' | 'model' | 'project'>('providers');
  const [providers, setProviders] = useState<Provider[]>([]);
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [keyInputs, setKeyInputs] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);
  const [search, setSearch] = useState('');
  const [selectedProvider, setSelectedProvider] = useState<string>('all');
  const [selectedModel, setSelectedModel] = useState('');

  // Project creation state
  const [projectName, setProjectName] = useState('');
  const [projectDesc, setProjectDesc] = useState('');
  const [creatingProject, setCreatingProject] = useState(false);

  const loadData = async () => {
    setLoading(true);
    try {
      const [pData, mData] = await Promise.all([api.getProviders(), api.getModels()]);
      const provs = pData.providers || [];
      const mdls = mData.models || [];
      setProviders(provs);
      setModels(mdls);
      // If any provider is configured AND models are available, skip to model selection
      if (provs.some((p: Provider) => p.configured) && mdls.length > 0) {
        setStep('model');
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const configuredProviders = providers.filter((p) => p.configured);
  const llmProviders = providers.filter((p) =>
    p.categories?.includes('models') || ['openai', 'anthropic', 'openrouter', 'opencode-go', 'ollama', 'lmstudio'].includes(p.id)
  );

  const filteredModels = useMemo(() => {
    let list = models;
    if (selectedProvider !== 'all') {
      list = list.filter((m) => m.provider === selectedProvider);
    }
    if (search.trim()) {
      const q = search.toLowerCase();
      list = list.filter((m) => m.name.toLowerCase().includes(q) || m.id.toLowerCase().includes(q));
    }
    return list;
  }, [models, selectedProvider, search]);

  const saveKeys = async () => {
    const toSave: Record<string, string> = {};
    for (const p of providers) {
      const val = keyInputs[p.id];
      if (val?.trim()) toSave[p.key_env] = val.trim();
    }
    if (Object.keys(toSave).length === 0) return;
    setSaving(true);
    try {
      await api.saveConfig(toSave);
      const [pData, mData] = await Promise.all([api.getProviders(), api.getModels()]);
      setProviders(pData.providers || []);
      setModels(mData.models || []);
      setKeyInputs({});
      if ((mData.models || []).length > 0) {
        setStep('model');
      }
    } finally {
      setSaving(false);
    }
  };

  const selectModel = async (modelId: string) => {
    await api.setModel(modelId);
    setSelectedModel(modelId);
    // Move to project creation step
    setStep('project');
  };

  const createProjectAndFinish = async () => {
    if (!projectName.trim()) return;
    setCreatingProject(true);
    try {
      const data = await api.createProject(projectName.trim(), projectDesc.trim() || undefined);
      const project = data.project as Project;
      onComplete(selectedModel, project);
    } catch {
      // If project creation fails, still complete onboarding with the model
      onComplete(selectedModel);
    } finally {
      setCreatingProject(false);
    }
  };

  if (loading) {
    return (
      <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
        <div className="bg-surface rounded-2xl border border-border p-8 text-center">
          <div className="text-text-dim">Loading...</div>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
      <div className="bg-surface rounded-2xl border border-border w-full max-w-lg max-h-[85vh] flex flex-col shadow-2xl">
        {/* Header */}
        <div className="px-8 pt-8 pb-4 text-center">
          <h2 className="text-2xl font-bold text-text mb-2">Welcome to OpenMLR</h2>
          <p className="text-text-dim">
            {step === 'providers'
              ? 'Configure at least one LLM provider to get started.'
              : step === 'model'
              ? 'Pick a model to use for conversations.'
              : 'Create your first research project.'}
          </p>
          {/* Step indicator */}
          <div className="flex items-center justify-center gap-2 mt-4">
            {['providers', 'model', 'project'].map((s, i) => (
              <div
                key={s}
                className={`w-2.5 h-2.5 rounded-full transition-colors ${
                  s === step ? 'bg-primary' : i < ['providers', 'model', 'project'].indexOf(step) ? 'bg-success' : 'bg-border'
                }`}
              />
            ))}
          </div>
        </div>

        {/* Providers step */}
        {step === 'providers' && (
          <div className="flex-1 overflow-hidden flex flex-col px-8 pb-8">
            <div className="flex-1 overflow-y-auto flex flex-col gap-3 py-4">
              {llmProviders.map((p) => (
                <div 
                  key={p.id} 
                  className={`p-4 rounded-lg border ${
                    p.configured ? 'bg-success/10 border-success/30' : 'bg-bg border-border'
                  }`}
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-medium text-text">{p.name}</span>
                    {p.configured && (
                      <span className="text-xs text-success font-medium">configured</span>
                    )}
                  </div>
                  {!p.configured && (
                    <input
                      type="password"
                      className="w-full bg-surface border border-border rounded-md px-3 py-2 text-sm text-text placeholder-text-dim focus:border-primary focus:outline-none"
                      placeholder={`Paste ${p.key_env}`}
                      value={keyInputs[p.id] || ''}
                      onChange={(e) => setKeyInputs((prev) => ({ ...prev, [p.id]: e.target.value }))}
                    />
                  )}
                </div>
              ))}
            </div>
            
            <div className="flex gap-3 pt-4">
              <button
                className="flex-1 py-3 bg-primary text-white rounded-lg font-semibold hover:bg-primary-hover transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                onClick={saveKeys}
                disabled={saving || Object.values(keyInputs).every((v) => !v?.trim())}
              >
                {saving ? 'Saving...' : 'Save & Continue'}
              </button>
              {configuredProviders.length > 0 && models.length > 0 && (
                <button 
                  className="px-6 py-3 bg-surface-hover border border-border text-text-dim rounded-lg hover:text-text transition-colors"
                  onClick={() => setStep('model')}
                >
                  Skip
                </button>
              )}
            </div>
          </div>
        )}

        {/* Model step */}
        {step === 'model' && (
          <div className="flex-1 overflow-hidden flex flex-col px-8 pb-8">
            {models.length === 0 ? (
              <div className="flex-1 flex flex-col items-center justify-center py-8 gap-4">
                <div className="text-center">
                  <p className="text-text font-medium mb-2">No models available</p>
                  <p className="text-text-dim text-sm">
                    No LLM providers are configured yet. Add at least one provider API key to see available models.
                  </p>
                </div>
                <button 
                  className="py-3 px-8 bg-primary text-white rounded-lg font-semibold hover:bg-primary-hover transition-colors"
                  onClick={() => setStep('providers')}
                >
                  Configure a Provider
                </button>
              </div>
            ) : (
              <>
                <div className="flex gap-3 py-4">
                  <input
                    type="text"
                    className="flex-1 bg-bg border border-border rounded-md px-3 py-2 text-sm text-text placeholder-text-dim focus:border-primary focus:outline-none"
                    placeholder="Search models..."
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                  />
                  <select 
                    className="bg-bg border border-border rounded-md px-3 py-2 text-sm text-text focus:border-primary focus:outline-none"
                    value={selectedProvider} 
                    onChange={(e) => setSelectedProvider(e.target.value)}
                  >
                    <option value="all">All providers</option>
                    {configuredProviders.map((p) => (
                      <option key={p.id} value={p.id}>{p.name}</option>
                    ))}
                  </select>
                </div>
                
                <div className="flex-1 overflow-y-auto flex flex-col gap-1">
                  {filteredModels.map((m) => (
                    <button 
                      key={m.id} 
                      className="flex items-center justify-between px-4 py-3 rounded-lg text-left hover:bg-surface-hover transition-colors"
                      onClick={() => selectModel(m.id)}
                    >
                      <span className="font-medium text-text">{m.name}</span>
                      <span className="text-xs text-text-dim font-mono">{m.id}</span>
                    </button>
                  ))}
                  {filteredModels.length === 0 && (
                    <div className="flex-1 flex items-center justify-center text-text-dim text-center py-8">
                      No models match your search.
                    </div>
                  )}
                </div>
              </>
            )}
          </div>
        )}

        {/* Project creation step */}
        {step === 'project' && (
          <div className="flex-1 overflow-hidden flex flex-col px-8 pb-8">
            <div className="flex-1 flex flex-col gap-4 py-6">
              <p className="text-sm text-text-dim">
                Projects organize your research. Each project has its own workspace
                with files, knowledge graph, and conversation history.
              </p>
              <div>
                <label className="block text-sm font-medium text-text mb-1.5">
                  Project Name <span className="text-error">*</span>
                </label>
                <input
                  type="text"
                  className="w-full bg-bg border border-border rounded-lg px-4 py-3 text-text placeholder-text-dim focus:border-primary focus:outline-none transition-colors"
                  placeholder="e.g., Transformer Efficiency Survey"
                  value={projectName}
                  onChange={(e) => setProjectName(e.target.value)}
                  onKeyDown={(e) => { if (e.key === 'Enter' && projectName.trim()) createProjectAndFinish(); }}
                  autoFocus
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-text mb-1.5">
                  Description <span className="text-text-dim">(optional)</span>
                </label>
                <textarea
                  className="w-full bg-bg border border-border rounded-lg px-4 py-3 text-text placeholder-text-dim focus:border-primary focus:outline-none transition-colors resize-none"
                  rows={3}
                  placeholder="What is this project about?"
                  value={projectDesc}
                  onChange={(e) => setProjectDesc(e.target.value)}
                />
              </div>
            </div>

            <button
              className="w-full py-3 bg-primary text-white rounded-lg font-semibold hover:bg-primary-hover transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              onClick={createProjectAndFinish}
              disabled={creatingProject || !projectName.trim()}
            >
              {creatingProject ? 'Creating...' : 'Create Project & Start'}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

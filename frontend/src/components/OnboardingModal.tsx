import { useState, useEffect, useMemo } from 'react';
import { api } from '../api';

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
  onComplete: (model: string) => void;
}

export function OnboardingModal({ onComplete }: Props) {
  const [step, setStep] = useState<'providers' | 'model'>('providers');
  const [providers, setProviders] = useState<Provider[]>([]);
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [keyInputs, setKeyInputs] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);
  const [search, setSearch] = useState('');
  const [selectedProvider, setSelectedProvider] = useState<string>('all');

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
      // Refresh providers and models after saving keys
      const [pData, mData] = await Promise.all([api.getProviders(), api.getModels()]);
      setProviders(pData.providers || []);
      setModels(mData.models || []);
      setKeyInputs({});
      // Only go to model step if we now have models
      if ((mData.models || []).length > 0) {
        setStep('model');
      }
    } finally {
      setSaving(false);
    }
  };

  const selectModel = async (modelId: string) => {
    await api.setModel(modelId);
    onComplete(modelId);
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
              : 'Pick a model to use for conversations.'}
          </p>
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
              /* No models available — send user back to configure a provider */
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
                {/* Filters */}
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
                
                {/* Model list */}
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
      </div>
    </div>
  );
}

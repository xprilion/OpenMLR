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

  useEffect(() => {
    setLoading(true);
    Promise.all([api.getProviders(), api.getModels()])
      .then(([pData, mData]) => {
        const provs = pData.providers || [];
        setProviders(provs);
        setModels(mData.models || []);
        // If any provider is already configured, skip to model selection
        if (provs.some((p: Provider) => p.configured)) {
          setStep('model');
        }
      })
      .finally(() => setLoading(false));
  }, []);

  const configuredProviders = providers.filter((p) => p.configured);
  const llmProviders = providers.filter((p) =>
    ['openai', 'anthropic', 'openrouter', 'opencode-go', 'ollama', 'lmstudio'].includes(p.id)
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
      const data = await api.getProviders();
      setProviders(data.providers || []);
      setKeyInputs({});
      setStep('model');
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
      <div className="onboarding-overlay">
        <div className="onboarding-card">
          <div className="onboarding-loading">Loading...</div>
        </div>
      </div>
    );
  }

  return (
    <div className="onboarding-overlay">
      <div className="onboarding-card">
        <div className="onboarding-header">
          <h2>Welcome to OpenMLR</h2>
          <p>{step === 'providers'
            ? 'Configure at least one LLM provider to get started.'
            : 'Pick a model to use for conversations.'
          }</p>
        </div>

        {step === 'providers' && (
          <div className="onboarding-body">
            <div className="onboarding-providers">
              {llmProviders.map((p) => (
                <div key={p.id} className={`onboarding-provider ${p.configured ? 'configured' : ''}`}>
                  <div className="onboarding-provider-info">
                    <span className="onboarding-provider-name">{p.name}</span>
                    {p.configured && <span className="onboarding-provider-ok">configured</span>}
                  </div>
                  {!p.configured && (
                    <input
                      type="password"
                      placeholder={`Paste ${p.key_env}`}
                      value={keyInputs[p.id] || ''}
                      onChange={(e) => setKeyInputs((prev) => ({ ...prev, [p.id]: e.target.value }))}
                    />
                  )}
                </div>
              ))}
            </div>
            <div className="onboarding-actions">
              <button
                className="onboarding-btn primary"
                onClick={saveKeys}
                disabled={saving || Object.values(keyInputs).every((v) => !v?.trim())}
              >
                {saving ? 'Saving...' : 'Save & Continue'}
              </button>
              {configuredProviders.length > 0 && (
                <button className="onboarding-btn secondary" onClick={() => setStep('model')}>
                  Skip, use existing
                </button>
              )}
            </div>
          </div>
        )}

        {step === 'model' && (
          <div className="onboarding-body">
            <div className="onboarding-model-filters">
              <input
                type="text"
                placeholder="Search models..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
              <select value={selectedProvider} onChange={(e) => setSelectedProvider(e.target.value)}>
                <option value="all">All providers</option>
                {providers.filter((p) => p.configured).map((p) => (
                  <option key={p.id} value={p.id}>{p.name}</option>
                ))}
              </select>
            </div>
            <div className="onboarding-model-list">
              {filteredModels.map((m) => (
                <button key={m.id} className="onboarding-model-option" onClick={() => selectModel(m.id)}>
                  <span className="onboarding-model-name">{m.name}</span>
                  <span className="onboarding-model-id">{m.id}</span>
                </button>
              ))}
              {filteredModels.length === 0 && (
                <div className="onboarding-empty">No models found. Configure a provider first.</div>
              )}
            </div>
            {configuredProviders.length === 0 && (
              <button className="onboarding-btn secondary" onClick={() => setStep('providers')}>
                Configure a provider
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

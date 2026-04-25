import { useState, useEffect, useMemo } from 'react';
import { api } from '../api';

interface Provider {
  id: string;
  name: string;
  key_env: string;
  configured: boolean;
}

interface ModelInfo {
  id: string;
  name: string;
  provider: string;
}

interface Props {
  currentModel: string;
  onModelChange: (model: string) => void;
}

type Tab = 'models' | 'providers';

export function ModelModal({ currentModel, onModelChange }: Props) {
  const [open, setOpen] = useState(false);
  const [tab, setTab] = useState<Tab>('models');
  const [providers, setProviders] = useState<Provider[]>([]);
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState('');
  const [selectedProvider, setSelectedProvider] = useState<string>('all');
  const [customModel, setCustomModel] = useState('');

  // Provider key inputs
  const [keyInputs, setKeyInputs] = useState<Record<string, string>>({});
  const [savingKeys, setSavingKeys] = useState(false);

  useEffect(() => {
    if (!open) return;
    setLoading(true);
    Promise.all([api.getProviders(), api.getModels()])
      .then(([pData, mData]) => {
        setProviders(pData.providers || []);
        setModels(mData.models || []);
      })
      .catch(() => {
        // ignore
      })
      .finally(() => setLoading(false));
  }, [open]);

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

  const selectModel = async (modelId: string) => {
    await api.setModel(modelId);
    onModelChange(modelId);
    setOpen(false);
  };

  const saveKeys = async () => {
    const toSave: Record<string, string> = {};
    for (const p of providers) {
      const val = keyInputs[p.id];
      if (val && val.trim()) {
        toSave[p.key_env] = val.trim();
      }
    }
    if (Object.keys(toSave).length === 0) return;
    setSavingKeys(true);
    try {
      await api.saveConfig(toSave);
      // Refresh providers to show updated status
      const data = await api.getProviders();
      setProviders(data.providers || []);
      setKeyInputs({});
    } catch {
      // ignore
    } finally {
      setSavingKeys(false);
    }
  };

  return (
    <>
      <button className="model-btn" onClick={() => setOpen(true)}>
        {currentModel}
      </button>

      {open && (
        <div className="modal-overlay" onClick={() => setOpen(false)}>
          <div className="modal model-picker-modal" onClick={(e) => e.stopPropagation()}>
            <div className="model-picker-tabs">
              <button
                className={`model-picker-tab ${tab === 'models' ? 'active' : ''}`}
                onClick={() => setTab('models')}
              >
                Models
              </button>
              <button
                className={`model-picker-tab ${tab === 'providers' ? 'active' : ''}`}
                onClick={() => setTab('providers')}
              >
                Providers
              </button>
            </div>

            {tab === 'models' && (
              <div className="model-picker-body">
                <div className="model-picker-filters">
                  <input
                    type="text"
                    className="model-search"
                    placeholder="Search models..."
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                  />
                  <select
                    className="model-provider-filter"
                    value={selectedProvider}
                    onChange={(e) => setSelectedProvider(e.target.value)}
                  >
                    <option value="all">All providers</option>
                    {providers.map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.name}
                      </option>
                    ))}
                  </select>
                </div>

                {loading ? (
                  <div className="model-picker-loading">Loading models...</div>
                ) : (
                  <div className="model-picker-list">
                    {filteredModels.map((m) => (
                      <button
                        key={m.id}
                        className={`model-picker-option ${m.id === currentModel ? 'active' : ''}`}
                        onClick={() => selectModel(m.id)}
                      >
                        <span className="model-picker-name">{m.name}</span>
                        <span className="model-picker-id">{m.id}</span>
                      </button>
                    ))}
                    {filteredModels.length === 0 && (
                      <div className="model-picker-empty">No models found</div>
                    )}
                  </div>
                )}

                <div className="custom-model-row">
                  <input
                    type="text"
                    placeholder="Custom model ID"
                    value={customModel}
                    onChange={(e) => setCustomModel(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && customModel.trim()) {
                        selectModel(customModel.trim());
                      }
                    }}
                  />
                  <button
                    disabled={!customModel.trim()}
                    onClick={() => customModel.trim() && selectModel(customModel.trim())}
                  >
                    Use
                  </button>
                </div>
              </div>
            )}

            {tab === 'providers' && (
              <div className="model-picker-body">
                <div className="provider-list">
                  {providers.map((p) => (
                    <div key={p.id} className="provider-row">
                      <div className="provider-info">
                        <span className="provider-name">{p.name}</span>
                        <span className={`provider-status ${p.configured ? 'ok' : 'missing'}`}>
                          {p.configured ? 'Configured' : 'API key missing'}
                        </span>
                      </div>
                      <input
                        type="password"
                        className="provider-key-input"
                        placeholder={`Paste ${p.key_env}`}
                        value={keyInputs[p.id] || ''}
                        onChange={(e) =>
                          setKeyInputs((prev) => ({ ...prev, [p.id]: e.target.value }))
                        }
                      />
                    </div>
                  ))}
                </div>
                <button
                  className="provider-save-btn"
                  onClick={saveKeys}
                  disabled={savingKeys || Object.values(keyInputs).every((v) => !v?.trim())}
                >
                  {savingKeys ? 'Saving...' : 'Save API Keys'}
                </button>
                <p className="provider-hint">
                  Keys are saved to your <code>.env</code> file. You can also set them manually.
                </p>
              </div>
            )}

            <button className="modal-close" onClick={() => setOpen(false)}>
              Close
            </button>
          </div>
        </div>
      )}
    </>
  );
}

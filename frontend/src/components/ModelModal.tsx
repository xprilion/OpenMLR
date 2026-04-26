import { useState, useEffect, useMemo } from 'react';
import { Search, ChevronDown, Check, X, Save } from 'lucide-react';
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

  // Extract raw model ID from label (which may include context info)
  const rawModelId = currentModel.split(' ')[0];

  return (
    <>
      <button 
        className="flex items-center gap-2 bg-surface-hover border border-border text-text-dim px-3 py-1.5 rounded-lg text-sm font-mono cursor-pointer transition-all max-w-[200px] truncate hover:border-primary hover:text-text"
        onClick={() => setOpen(true)}
      >
        <span className="truncate">{currentModel}</span>
        <ChevronDown size={14} className="shrink-0" />
      </button>

      {open && (
        <div 
          className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4"
          onClick={() => setOpen(false)}
        >
          <div 
            className="bg-surface rounded-xl border border-border w-full max-w-lg max-h-[80vh] flex flex-col shadow-xl"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Tabs */}
            <div className="flex border-b border-border">
              <button
                className={`flex-1 py-3 px-4 text-sm font-medium transition-colors ${
                  tab === 'models' ? 'text-primary border-b-2 border-primary' : 'text-text-dim hover:text-text'
                }`}
                onClick={() => setTab('models')}
              >
                Models
              </button>
              <button
                className={`flex-1 py-3 px-4 text-sm font-medium transition-colors ${
                  tab === 'providers' ? 'text-primary border-b-2 border-primary' : 'text-text-dim hover:text-text'
                }`}
                onClick={() => setTab('providers')}
              >
                Providers
              </button>
            </div>

            {/* Models tab */}
            {tab === 'models' && (
              <div className="flex-1 flex flex-col overflow-hidden p-4">
                {/* Filters */}
                <div className="flex gap-3 mb-4">
                  <div className="relative flex-1">
                    <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-dim" />
                    <input
                      type="text"
                      className="w-full bg-bg border border-border rounded-lg pl-9 pr-3 py-2 text-sm text-text placeholder-text-dim focus:border-primary focus:outline-none"
                      placeholder="Search models..."
                      value={search}
                      onChange={(e) => setSearch(e.target.value)}
                    />
                  </div>
                  <select
                    className="bg-bg border border-border rounded-lg px-3 py-2 text-sm text-text focus:border-primary focus:outline-none"
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

                {/* Model list */}
                {loading ? (
                  <div className="flex-1 flex items-center justify-center text-text-dim">Loading models...</div>
                ) : (
                  <div className="flex-1 overflow-y-auto flex flex-col gap-1">
                    {filteredModels.map((m) => (
                      <button
                        key={m.id}
                        className={`flex items-center justify-between px-4 py-3 rounded-lg text-left transition-all ${
                          m.id === rawModelId 
                            ? 'bg-primary/15 border border-primary' 
                            : 'bg-transparent border border-transparent hover:bg-surface-hover'
                        }`}
                        onClick={() => selectModel(m.id)}
                      >
                        <div className="flex items-center gap-2">
                          {m.id === rawModelId && <Check size={16} className="text-primary shrink-0" />}
                          <span className="font-medium text-text">{m.name}</span>
                        </div>
                        <span className="text-xs text-text-dim font-mono">{m.id}</span>
                      </button>
                    ))}
                    {filteredModels.length === 0 && (
                      <div className="flex-1 flex items-center justify-center text-text-dim text-sm">
                        No models found
                      </div>
                    )}
                  </div>
                )}

                {/* Custom model */}
                <div className="flex gap-2 mt-4 pt-4 border-t border-border">
                  <input
                    type="text"
                    className="flex-1 bg-bg border border-border rounded-lg px-3 py-2 text-sm text-text placeholder-text-dim focus:border-primary focus:outline-none"
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
                    className="px-4 py-2 bg-primary text-white rounded-lg text-sm font-medium hover:bg-primary-hover transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    disabled={!customModel.trim()}
                    onClick={() => customModel.trim() && selectModel(customModel.trim())}
                  >
                    Use
                  </button>
                </div>
              </div>
            )}

            {/* Providers tab */}
            {tab === 'providers' && (
              <div className="flex-1 flex flex-col overflow-hidden p-4">
                <div className="flex-1 overflow-y-auto flex flex-col gap-3">
                  {providers.map((p) => (
                    <div key={p.id} className="flex items-center gap-3 p-3 bg-bg rounded-lg border border-border">
                      <div className="flex-1">
                        <span className="font-medium text-text block">{p.name}</span>
                        <span className={`text-xs flex items-center gap-1 ${p.configured ? 'text-success' : 'text-text-dim'}`}>
                          {p.configured && <Check size={12} />}
                          {p.configured ? 'Configured' : 'API key missing'}
                        </span>
                      </div>
                      <input
                        type="password"
                        className="w-48 bg-surface border border-border rounded-lg px-3 py-2 text-sm text-text placeholder-text-dim focus:border-primary focus:outline-none"
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
                  className="mt-4 w-full py-3 bg-primary text-white rounded-lg font-medium hover:bg-primary-hover transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                  onClick={saveKeys}
                  disabled={savingKeys || Object.values(keyInputs).every((v) => !v?.trim())}
                >
                  <Save size={16} />
                  {savingKeys ? 'Saving...' : 'Save API Keys'}
                </button>
                
                <p className="mt-3 text-xs text-text-dim text-center">
                  Keys are saved to your <code className="bg-bg px-1 rounded">`.env`</code> file. You can also set them manually.
                </p>
              </div>
            )}

            {/* Close button */}
            <button 
              className="mx-4 mb-4 py-2 text-center text-sm text-text-dim hover:text-text transition-colors flex items-center justify-center gap-1"
              onClick={() => setOpen(false)}
            >
              <X size={14} />
              Close
            </button>
          </div>
        </div>
      )}
    </>
  );
}

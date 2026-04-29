

import { useState, useEffect, useMemo, useCallback } from 'react';
import { Search, ChevronDown, Check, X, Filter, Save } from 'lucide-react';
import { api } from '../api';
import { useNavigate } from 'react-router-dom';

interface Provider {
  id: string;
  name: string;
  key_env: string;
  configured: boolean;
  categories?: string[];
  is_custom?: boolean;
  sdk_type?: string;
  api_base?: string;
}

interface ModelInfo {
  id: string;
  name: string;
  provider: string;
  release_date?: string;
}

interface Props {
  currentModel: string;
  onModelChange: (model: string) => void;
}

type Tab = 'models' | 'providers';

/** Tiny provider logo from models.dev — uses currentColor, gracefully falls back */
function ProviderLogo({ providerId, size = 16 }: { providerId: string; size?: number }) {
  return (
    <img
      src={`https://models.dev/logos/${providerId}.svg`}
      alt=""
      width={size}
      height={size}
      className="shrink-0 opacity-60"
      style={{ filter: 'grayscale(0.3)' }}
      loading="lazy"
      onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }}
    />
  );
}

/** Skeleton rows shown while loading */
function LoadingSkeleton() {
  return (
    <div className="flex-1 flex flex-col gap-1 animate-pulse">
      {/* Fake "Recently Used" heading */}
      <div className="px-2 py-1">
        <div className="h-3 w-24 bg-surface-hover rounded" />
      </div>
      {[1, 2].map((i) => (
        <div key={`r${i}`} className="flex items-center justify-between px-4 py-3">
          <div className="h-4 w-32 bg-surface-hover rounded" />
          <div className="h-3 w-24 bg-surface-hover rounded" />
        </div>
      ))}
      <div className="my-2 border-t border-border" />
      {/* Fake provider group */}
      <div className="px-2 py-1 flex items-center gap-2">
        <div className="h-4 w-4 bg-surface-hover rounded" />
        <div className="h-3 w-20 bg-surface-hover rounded" />
      </div>
      {[1, 2, 3, 4].map((i) => (
        <div key={`m${i}`} className="flex items-center justify-between px-4 py-3">
          <div className="h-4 bg-surface-hover rounded" style={{ width: `${100 + i * 20}px` }} />
          <div className="h-3 w-28 bg-surface-hover rounded" />
        </div>
      ))}
      {/* Second fake group */}
      <div className="px-2 py-1 mt-2 flex items-center gap-2">
        <div className="h-4 w-4 bg-surface-hover rounded" />
        <div className="h-3 w-16 bg-surface-hover rounded" />
      </div>
      {[1, 2, 3].map((i) => (
        <div key={`n${i}`} className="flex items-center justify-between px-4 py-3">
          <div className="h-4 bg-surface-hover rounded" style={{ width: `${80 + i * 25}px` }} />
          <div className="h-3 w-32 bg-surface-hover rounded" />
        </div>
      ))}
    </div>
  );
}

export function ModelModal({ currentModel, onModelChange }: Props) {
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const [tab, setTab] = useState<Tab>('models');
  const [providers, setProviders] = useState<Provider[]>([]);
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [recentModels, setRecentModels] = useState<ModelInfo[]>([]);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState('');
  const [filterProvider, setFilterProvider] = useState<string>('all');
  const [customModel, setCustomModel] = useState('');

  // Provider key inputs
  const [keyInputs, setKeyInputs] = useState<Record<string, string>>({});
  const [savingKeys, setSavingKeys] = useState(false);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [pData, mData] = await Promise.all([api.getProviders(), api.getModels()]);
      const provs = pData.providers || [];
      setProviders(provs);
      setModels(mData.models || []);
      setRecentModels(mData.recent_models || []);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!open) return;
    loadData();
  }, [open, loadData]);

  // Get only configured providers that are in the models category
  const configuredModelProviders = useMemo(() => {
    return providers.filter((p) => p.configured && p.categories?.includes('models'));
  }, [providers]);

  // Group models by provider, sorted by release_date descending
  const groupedModels = useMemo(() => {
    const groups: Record<string, ModelInfo[]> = {};
    for (const p of configuredModelProviders) {
      groups[p.id] = [];
    }
    for (const m of models) {
      if (groups[m.provider]) {
        groups[m.provider].push(m);
      }
    }
    // Sort each group by release_date descending (newest first)
    for (const pid of Object.keys(groups)) {
      groups[pid].sort((a, b) => {
        const da = a.release_date || '1900-01-01';
        const db = b.release_date || '1900-01-01';
        return db.localeCompare(da);
      });
    }
    return groups;
  }, [models, configuredModelProviders]);

  // Filter across recent + all grouped models
  const filteredRecent = useMemo(() => {
    let list = recentModels;
    if (filterProvider !== 'all') {
      list = list.filter((m) => m.provider === filterProvider);
    }
    if (search.trim()) {
      const q = search.toLowerCase();
      list = list.filter(
        (m) => m.name.toLowerCase().includes(q) || m.id.toLowerCase().includes(q)
      );
    }
    return list;
  }, [recentModels, search, filterProvider]);

  const filteredGroups = useMemo(() => {
    const q = search.toLowerCase();
    const result: Record<string, ModelInfo[]> = {};
    for (const pid of Object.keys(groupedModels)) {
      // Skip providers that don't match the filter
      if (filterProvider !== 'all' && pid !== filterProvider) continue;
      const list = search.trim()
        ? groupedModels[pid].filter(
            (m) => m.name.toLowerCase().includes(q) || m.id.toLowerCase().includes(q)
          )
        : groupedModels[pid];
      if (list.length > 0) {
        result[pid] = list;
      }
    }
    return result;
  }, [groupedModels, search, filterProvider]);

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
      const data = await api.getProviders();
      setProviders(data.providers || []);
      setKeyInputs({});
    } catch {
      // ignore
    } finally {
      setSavingKeys(false);
    }
  };

  const goToSettings = () => {
    setOpen(false);
    navigate('/settings/providers');
  };

  // Extract raw model ID from label (which may include context info)
  const rawModelId = currentModel.split(' ')[0];

  const renderModelButton = (m: ModelInfo) => (
    <button
      key={m.id}
      className={`flex items-center justify-between px-4 py-2.5 rounded-lg text-left transition-all w-full ${
        m.id === rawModelId
          ? 'bg-primary/15 border border-primary'
          : 'bg-transparent border border-transparent hover:bg-surface-hover'
      }`}
      onClick={() => selectModel(m.id)}
    >
      <div className="flex items-center gap-2 min-w-0">
        {m.id === rawModelId && <Check size={14} className="text-primary shrink-0" />}
        <span className="text-sm font-medium text-text truncate">{m.name}</span>
      </div>
      <span className="text-xs text-text-dim font-mono shrink-0 ml-2">{m.id}</span>
    </button>
  );

  return (
    <>
      <button
        className="flex items-center gap-1 sm:gap-2 bg-surface-hover border border-border text-text-dim px-2 sm:px-3 py-1.5 rounded-lg text-sm font-mono cursor-pointer transition-all max-w-[120px] sm:max-w-[200px] hover:border-primary hover:text-text"
        onClick={() => setOpen(true)}
        title={currentModel}
      >
        <span className="truncate">{currentModel}</span>
        <ChevronDown size={14} className="shrink-0" />
      </button>

      {open && (
        <div
          className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4"
          onClick={() => setOpen(false)}
          onKeyDown={(e) => e.key === 'Escape' && setOpen(false)}
          role="presentation"
        >
          {/* Fixed-size modal — never changes dimensions between loading and loaded */}
          <div
            className="bg-surface rounded-xl border border-border w-full max-w-lg flex flex-col shadow-xl"
            style={{ height: 'min(80vh, 600px)' }}
            onClick={(e) => e.stopPropagation()}
            onKeyDown={(e) => e.stopPropagation()}
            role="dialog"
            aria-modal="true"
            aria-labelledby="model-modal-title"
          >
            {/* Tabs */}
            <div className="flex border-b border-border shrink-0">
              <button
                id="model-modal-title"
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
              <div className="flex-1 flex flex-col overflow-hidden p-4 min-h-0">
                {/* Search + Provider filter — always visible */}
                <div className="flex gap-2 mb-3 shrink-0">
                  <div className="relative flex-1">
                    <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-dim" />
                    <input
                      type="text"
                      className="w-full bg-bg border border-border rounded-lg pl-9 pr-3 py-2 text-sm text-text placeholder-text-dim focus:border-primary focus:outline-none"
                      placeholder="Search models..."
                      value={search}
                      onChange={(e) => setSearch(e.target.value)}
                      autoFocus
                    />
                  </div>
                  <div className="relative shrink-0">
                    <Filter size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-text-dim pointer-events-none" />
                    <select
                      className="bg-bg border border-border rounded-lg pl-8 pr-3 py-2 text-sm text-text focus:border-primary focus:outline-none appearance-none cursor-pointer"
                      value={filterProvider}
                      onChange={(e) => setFilterProvider(e.target.value)}
                      title="Filter by provider"
                    >
                      <option value="all">All</option>
                      {configuredModelProviders.map((p) => (
                        <option key={p.id} value={p.id}>{p.name}</option>
                      ))}
                    </select>
                  </div>
                </div>

                {/* Scrollable model list area — same size whether loading or loaded */}
                <div className="flex-1 overflow-y-auto min-h-0">
                  {loading ? (
                    <LoadingSkeleton />
                  ) : (
                    <div className="flex flex-col gap-0.5">
                      {/* Recently used */}
                      {!search.trim() && filteredRecent.length > 0 && (
                        <>
                          <div className="px-2 py-1">
                            <span className="text-xs font-semibold text-text-dim uppercase tracking-wider">Recently Used</span>
                          </div>
                          {filteredRecent.map(renderModelButton)}
                          <div className="my-2 border-t border-border" />
                        </>
                      )}

                      {/* Provider groups */}
                      {configuredModelProviders.map((p) => {
                        const groupModels = filteredGroups[p.id] || [];
                        if (groupModels.length === 0) return null;
                        return (
                          <div key={p.id} className="mb-2">
                            <div className="px-2 py-1.5 flex items-center gap-2">
                              <ProviderLogo providerId={p.id} size={16} />
                              <span className="text-xs font-semibold text-text-dim uppercase tracking-wider">{p.name}</span>
                              {p.is_custom && (
                                <span className="text-[10px] px-1.5 py-0.5 bg-surface-hover rounded text-text-dim">{p.sdk_type}</span>
                              )}
                            </div>
                            <div className="flex flex-col gap-0.5">
                              {groupModels.map(renderModelButton)}
                            </div>
                          </div>
                        );
                      })}

                      {Object.keys(filteredGroups).length === 0 && filteredRecent.length === 0 && (
                        <div className="flex-1 flex items-center justify-center text-text-dim text-sm py-12">
                          No models found
                        </div>
                      )}

                      {configuredModelProviders.length === 0 && !loading && (
                        <div className="flex-1 flex flex-col items-center justify-center gap-3 text-text-dim text-sm py-12">
                          <p>No providers configured.</p>
                          <button
                            className="px-4 py-2 bg-primary text-white rounded-lg text-sm font-medium hover:bg-primary-hover transition-colors"
                            onClick={goToSettings}
                          >
                            Configure Providers
                          </button>
                        </div>
                      )}
                    </div>
                  )}
                </div>

                {/* Custom model — always at the bottom */}
                <div className="flex gap-2 mt-3 pt-3 border-t border-border shrink-0">
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
              <div className="flex-1 flex flex-col overflow-hidden p-4 min-h-0">
                <div className="flex-1 overflow-y-auto flex flex-col gap-3 min-h-0">
                  {providers.map((p) => (
                    <div key={p.id} className="flex items-center gap-3 p-3 bg-bg rounded-lg border border-border">
                      <div className="flex-1 min-w-0">
                        <span className="font-medium text-text block">{p.name}</span>
                        <span className={`text-xs flex items-center gap-1 ${p.configured ? 'text-success' : 'text-text-dim'}`}>
                          {p.configured && <Check size={12} />}
                          {p.configured ? 'Configured' : 'API key missing'}
                        </span>
                      </div>
                      <input
                        type="password"
                        className="w-48 bg-surface border border-border rounded-lg px-3 py-2 text-sm text-text placeholder-text-dim focus:border-primary focus:outline-none shrink-0"
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
                  className="mt-4 w-full py-3 bg-primary text-white rounded-lg font-medium hover:bg-primary-hover transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 shrink-0"
                  onClick={saveKeys}
                  disabled={savingKeys || Object.values(keyInputs).every((v) => !v?.trim())}
                >
                  <Save size={16} />
                  {savingKeys ? 'Saving...' : 'Save API Keys'}
                </button>

                <p className="mt-3 text-xs text-text-dim text-center shrink-0">
                  Keys are saved to your <code className="bg-bg px-1 rounded">`.env`</code> file. You can also set them manually.
                </p>
              </div>
            )}

            {/* Footer: settings link + close */}
            <div className="mx-4 mb-4 flex items-center justify-between shrink-0">
              <button
                className="text-xs text-text-dim hover:text-primary transition-colors"
                onClick={goToSettings}
              >
                More provider settings
              </button>
              <button
                className="py-2 text-sm text-text-dim hover:text-text transition-colors flex items-center gap-1"
                onClick={() => setOpen(false)}
              >
                <X size={14} />
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

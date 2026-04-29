

import { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { api } from '../../api';
import type { Provider } from '../../types';

// Tab definitions with display order
const TABS = [
  { id: 'models', label: 'Models', description: 'LLM providers for AI models' },
  { id: 'search', label: 'Search', description: 'Web search providers' },
  { id: 'papers', label: 'Papers', description: 'Academic paper and research providers' },
  { id: 'compute', label: 'Compute', description: 'Cloud compute providers' },
  { id: 'others', label: 'Others', description: 'Other integrations' },
] as const;

type TabId = typeof TABS[number]['id'];

type SdkType = 'openai-sdk' | 'anthropic-sdk' | 'openrouter' | 'litellm';

interface CustomProvider {
  id: string;
  name: string;
  sdk_type: SdkType;
  api_base: string;
  api_key: string;
  models?: { id: string; name: string; release_date?: string }[];
  last_fetched_at?: string;
}

const SDK_OPTIONS: { value: SdkType; label: string }[] = [
  { value: 'openai-sdk', label: 'OpenAI SDK' },
  { value: 'anthropic-sdk', label: 'Anthropic SDK' },
  { value: 'openrouter', label: 'OpenRouter' },
  { value: 'litellm', label: 'LiteLLM' },
];

export function ProvidersSettings() {
  const [providers, setProviders] = useState<Provider[]>([]);
  const [keyInputs, setKeyInputs] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);
  const [saveMsg, setSaveMsg] = useState('');
  const [activeTab, setActiveTab] = useState<TabId>('models');

  // Custom provider modal state
  const customDialogRef = useRef<HTMLDialogElement>(null);
  const [showCustomModal, setShowCustomModal] = useState(false);
  const [customForm, setCustomForm] = useState<{
    name: string;
    id: string;
    sdk_type: SdkType;
    api_base: string;
    api_key: string;
  }>({
    name: '',
    id: '',
    sdk_type: 'openai-sdk',
    api_base: '',
    api_key: '',
  });
  const [fetchingModels, setFetchingModels] = useState(false);
  const [fetchMsg, setFetchMsg] = useState('');

  useEffect(() => {
    api.getProviders().then((d) => setProviders(d.providers || [])).catch(() => {});
  }, []);

  // Handle custom provider dialog open/close
  useEffect(() => {
    const dialog = customDialogRef.current;
    if (!dialog) return;
    
    if (showCustomModal && !dialog.open) {
      dialog.showModal();
    } else if (!showCustomModal && dialog.open) {
      dialog.close();
    }

    const handleCancel = (e: Event) => {
      e.preventDefault();
      setShowCustomModal(false);
    };

    dialog.addEventListener('cancel', handleCancel);
    return () => dialog.removeEventListener('cancel', handleCancel);
  }, [showCustomModal]);

  // Group providers by tab (a provider can appear in multiple tabs)
  const providersByTab = useMemo(() => {
    const grouped: Record<string, Provider[]> = {};
    for (const tab of TABS) {
      grouped[tab.id] = providers.filter((p) =>
        p.categories?.includes(tab.id)
      );
    }
    return grouped;
  }, [providers]);

  const activeTabInfo = TABS.find(t => t.id === activeTab);
  const activeProviders = providersByTab[activeTab] || [];

  const flash = useCallback((msg: string) => {
    setSaveMsg(msg);
    setTimeout(() => setSaveMsg(''), 2000);
  }, []);

  const saveProviderKeys = async () => {
    setSaving(true);
    try {
      for (const p of providers) {
        const val = keyInputs[p.id];
        if (val && val.trim()) {
          await api.updateSetting('providers', `${p.id}_api_key`, val.trim());
        }
      }
      const data = await api.getProviders();
      setProviders(data.providers || []);
      setKeyInputs({});
      flash('Saved');
    } catch {
      flash('Error saving');
    } finally {
      setSaving(false);
    }
  };

  const saveCustomProvider = async () => {
    if (!customForm.name.trim() || !customForm.id.trim() || !customForm.api_base.trim() || !customForm.api_key.trim()) {
      flash('Please fill in all fields');
      return;
    }

    // Load existing custom providers
    const settingsRes = await api.getSettingsCategory('providers').catch(() => ({ settings: {} }));
    const existing: CustomProvider[] = Array.isArray(settingsRes.settings?.custom_providers)
      ? settingsRes.settings.custom_providers
      : [];

    // Remove existing entry with same ID if present
    const filtered = existing.filter((cp) => cp.id !== customForm.id.trim());

    const newProvider: CustomProvider = {
      id: customForm.id.trim(),
      name: customForm.name.trim(),
      sdk_type: customForm.sdk_type,
      api_base: customForm.api_base.trim(),
      api_key: customForm.api_key.trim(),
      models: [],
    };

    filtered.push(newProvider);

    await api.updateSetting('providers', 'custom_providers', filtered);

    // Reset form and refresh
    setCustomForm({ name: '', id: '', sdk_type: 'openai-sdk', api_base: '', api_key: '' });
    setShowCustomModal(false);
    const data = await api.getProviders();
    setProviders(data.providers || []);
    flash('Custom provider added');
  };

  const deleteCustomProvider = async (providerId: string) => {
    const settingsRes = await api.getSettingsCategory('providers').catch(() => ({ settings: {} }));
    const existing: CustomProvider[] = Array.isArray(settingsRes.settings?.custom_providers)
      ? settingsRes.settings.custom_providers
      : [];

    const filtered = existing.filter((cp) => cp.id !== providerId);
    await api.updateSetting('providers', 'custom_providers', filtered);

    const data = await api.getProviders();
    setProviders(data.providers || []);
    flash('Custom provider removed');
  };

  const fetchModelsForProvider = async (providerId: string) => {
    setFetchingModels(true);
    setFetchMsg('');
    try {
      const res = await api.fetchCustomProviderModels(providerId);
      const count = res.models?.length || 0;
      setFetchMsg(count > 0 ? `Fetched ${count} models` : 'No models found');
      // Refresh providers to get updated model list
      const data = await api.getProviders();
      setProviders(data.providers || []);
    } catch (err: any) {
      setFetchMsg(err?.message || 'Failed to fetch models');
    } finally {
      setFetchingModels(false);
      setTimeout(() => setFetchMsg(''), 3000);
    }
  };

  const renderProviderCard = (p: Provider) => (
    <div key={p.id} className="flex items-center gap-3 p-4 bg-bg rounded-lg border border-border">
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="font-medium text-text">{p.name}</span>
          {p.is_custom && (
            <span className="text-[10px] px-1.5 py-0.5 bg-surface-hover rounded text-text-dim border border-border">
              {p.sdk_type}
            </span>
          )}
          {p.docs_url && !p.is_custom && (
            <a
              href={p.docs_url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-text-dim hover:text-primary transition-colors"
              title="View documentation"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                width="14"
                height="14"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
                <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
              </svg>
            </a>
          )}
        </div>
        <span className={`text-xs ${p.configured ? 'text-success' : 'text-text-dim'}`}>
          {p.configured ? 'Configured' : 'Not set'}
        </span>
        {p.is_custom && p.api_base && (
          <span className="text-xs text-text-dim block truncate">{p.api_base}</span>
        )}
      </div>
      {!p.is_custom ? (
        <input
          type="password"
          className="w-48 bg-surface border border-border rounded-md px-3 py-2 text-sm text-text placeholder-text-dim focus:border-primary focus:outline-none transition-colors shrink-0"
          placeholder={p.key_env}
          value={keyInputs[p.id] || ''}
          onChange={(e) =>
            setKeyInputs((prev) => ({ ...prev, [p.id]: e.target.value }))
          }
        />
      ) : (
        <div className="flex items-center gap-2 shrink-0">
          <button
            className="px-3 py-2 bg-surface-hover border border-border rounded-md text-sm text-text-dim hover:text-text transition-colors"
            onClick={() => fetchModelsForProvider(p.id)}
            disabled={fetchingModels}
          >
            {fetchingModels ? '...' : 'Fetch Models'}
          </button>
          <button
            className="px-3 py-2 bg-error/10 border border-error/30 rounded-md text-sm text-error hover:bg-error/20 transition-colors"
            onClick={() => deleteCustomProvider(p.id)}
          >
            Delete
          </button>
        </div>
      )}
    </div>
  );

  return (
    <div>
      {saveMsg && (
        <div className="mb-4 px-4 py-2 bg-success/10 text-success rounded-lg text-sm">
          {saveMsg}
        </div>
      )}

      {fetchMsg && (
        <div className={`mb-4 px-4 py-2 rounded-lg text-sm ${fetchMsg.includes('Failed') || fetchMsg.includes('Error') ? 'bg-error/10 text-error' : 'bg-success/10 text-success'}`}>
          {fetchMsg}
        </div>
      )}

      <p className="text-text-dim mb-6">
        API keys are stored in the database per-user. They override .env values.
      </p>

      {/* Tab navigation */}
      <div className="flex flex-wrap gap-2 mb-6">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
              activeTab === tab.id
                ? 'bg-primary text-white'
                : 'bg-surface-hover text-text-dim hover:text-text'
            }`}
            onClick={() => setActiveTab(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="mb-6">
        {activeTabInfo && (
          <p className="text-sm text-text-dim mb-4">{activeTabInfo.description}</p>
        )}
        {activeProviders.length > 0 ? (
          <div className="flex flex-col gap-3">
            {activeProviders.map((p) => renderProviderCard(p))}
          </div>
        ) : (
          <p className="text-text-dim text-center py-8 bg-surface rounded-lg border border-border">
            No providers configured for this category yet.
          </p>
        )}
      </div>

      {/* Add Custom Provider button (only on Models tab) */}
      {activeTab === 'models' && (
        <div className="mb-6">
          <button
            className="w-full py-3 bg-surface-hover border border-border border-dashed text-text-dim rounded-lg font-medium hover:text-text hover:border-primary transition-colors"
            onClick={() => setShowCustomModal(true)}
          >
            + Add Custom Provider
          </button>
        </div>
      )}

      <button
        className="w-full py-3 bg-primary text-white rounded-lg font-medium hover:bg-primary-hover transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        onClick={saveProviderKeys}
        disabled={saving || Object.values(keyInputs).every((v) => !v?.trim())}
      >
        {saving ? 'Saving...' : 'Save Keys'}
      </button>

      {/* Custom Provider Modal */}
      <dialog
        ref={customDialogRef}
        className="fixed bg-transparent p-4 m-0 max-w-none max-h-none w-full h-full backdrop:bg-black/60"
        onClick={(e) => {
          if (e.target === customDialogRef.current) setShowCustomModal(false);
        }}
        aria-labelledby="custom-provider-title"
      >
        <div className="flex items-center justify-center min-h-full">
          <div
            className="bg-surface rounded-xl border border-border w-full max-w-md flex flex-col shadow-xl p-6"
            onClick={(e) => e.stopPropagation()}
          >
            <h3 id="custom-provider-title" className="text-lg font-semibold text-text mb-4">Add Custom Provider</h3>

            <div className="flex flex-col gap-4">
              <div>
                <label className="block text-sm text-text-dim mb-1" htmlFor="custom-provider-name">Display Name</label>
                <input
                  id="custom-provider-name"
                  type="text"
                  className="w-full bg-bg border border-border rounded-lg px-3 py-2 text-sm text-text placeholder-text-dim focus:border-primary focus:outline-none"
                  placeholder="e.g. My Organization"
                  value={customForm.name}
                  onChange={(e) => setCustomForm((f) => ({ ...f, name: e.target.value }))}
                />
              </div>

              <div>
                <label className="block text-sm text-text-dim mb-1" htmlFor="custom-provider-id">Provider ID (prefix)</label>
                <input
                  id="custom-provider-id"
                  type="text"
                  className="w-full bg-bg border border-border rounded-lg px-3 py-2 text-sm text-text placeholder-text-dim focus:border-primary focus:outline-none"
                  placeholder="e.g. my-org (models will be my-org/model-name)"
                  value={customForm.id}
                  onChange={(e) => setCustomForm((f) => ({ ...f, id: e.target.value }))}
                />
              </div>

              <div>
                <label className="block text-sm text-text-dim mb-1" htmlFor="custom-provider-sdk">SDK Type</label>
                <select
                  id="custom-provider-sdk"
                  className="w-full bg-bg border border-border rounded-lg px-3 py-2 text-sm text-text focus:border-primary focus:outline-none"
                  value={customForm.sdk_type}
                  onChange={(e) => setCustomForm((f) => ({ ...f, sdk_type: e.target.value as SdkType }))}
                >
                  {SDK_OPTIONS.map((opt) => (
                    <option key={opt.value} value={opt.value}>{opt.label}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm text-text-dim mb-1" htmlFor="custom-provider-base">API Base URL</label>
                <input
                  id="custom-provider-base"
                  type="text"
                  className="w-full bg-bg border border-border rounded-lg px-3 py-2 text-sm text-text placeholder-text-dim focus:border-primary focus:outline-none"
                  placeholder="https://api.my-org.com/v1"
                  value={customForm.api_base}
                  onChange={(e) => setCustomForm((f) => ({ ...f, api_base: e.target.value }))}
                />
              </div>

              <div>
                <label className="block text-sm text-text-dim mb-1" htmlFor="custom-provider-key">API Key</label>
                <input
                  id="custom-provider-key"
                  type="password"
                  className="w-full bg-bg border border-border rounded-lg px-3 py-2 text-sm text-text placeholder-text-dim focus:border-primary focus:outline-none"
                  placeholder="sk-..."
                  value={customForm.api_key}
                  onChange={(e) => setCustomForm((f) => ({ ...f, api_key: e.target.value }))}
                />
              </div>
            </div>

            <div className="flex gap-3 mt-6">
              <button
                className="flex-1 py-3 bg-primary text-white rounded-lg font-semibold hover:bg-primary-hover transition-colors"
                onClick={saveCustomProvider}
              >
                Save Provider
              </button>
              <button
                className="px-6 py-3 bg-surface-hover border border-border text-text-dim rounded-lg hover:text-text transition-colors"
                onClick={() => setShowCustomModal(false)}
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      </dialog>
    </div>
  );
}

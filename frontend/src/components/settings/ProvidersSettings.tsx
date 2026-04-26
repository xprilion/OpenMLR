import { useState, useEffect, useCallback, useMemo } from 'react';
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

export function ProvidersSettings() {
  const [providers, setProviders] = useState<Provider[]>([]);
  const [keyInputs, setKeyInputs] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);
  const [saveMsg, setSaveMsg] = useState('');
  const [activeTab, setActiveTab] = useState<TabId>('models');

  useEffect(() => {
    api.getProviders().then((d) => setProviders(d.providers || [])).catch(() => {});
  }, []);

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

  const renderProviderCard = (p: Provider) => (
    <div key={p.id} className="flex items-center gap-3 p-4 bg-bg rounded-lg border border-border">
      <div className="flex-1">
        <div className="flex items-center gap-2">
          <span className="font-medium text-text">{p.name}</span>
          {p.docs_url && (
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
      </div>
      <input
        type="password"
        className="w-48 bg-surface border border-border rounded-md px-3 py-2 text-sm text-text placeholder-text-dim focus:border-primary focus:outline-none transition-colors"
        placeholder={p.key_env}
        value={keyInputs[p.id] || ''}
        onChange={(e) =>
          setKeyInputs((prev) => ({ ...prev, [p.id]: e.target.value }))
        }
      />
    </div>
  );

  return (
    <div>
      {saveMsg && (
        <div className="mb-4 px-4 py-2 bg-success/10 text-success rounded-lg text-sm">
          {saveMsg}
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

      <button
        className="w-full py-3 bg-primary text-white rounded-lg font-medium hover:bg-primary-hover transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        onClick={saveProviderKeys}
        disabled={saving || Object.values(keyInputs).every((v) => !v?.trim())}
      >
        {saving ? 'Saving...' : 'Save Keys'}
      </button>
    </div>
  );
}

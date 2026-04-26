import { useState, useEffect, useCallback } from 'react';
import { api } from '../../api';
import type { Provider } from '../../types';

export function ProvidersSettings() {
  const [providers, setProviders] = useState<Provider[]>([]);
  const [keyInputs, setKeyInputs] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);
  const [saveMsg, setSaveMsg] = useState('');

  useEffect(() => {
    api.getProviders().then((d) => setProviders(d.providers || [])).catch(() => {});
  }, []);

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

  return (
    <div className="settings-section">
      {saveMsg && <span className="save-flash">{saveMsg}</span>}
      <p className="settings-hint">
        API keys are stored in the database per-user. They override .env values.
      </p>
      <div className="provider-list">
        {providers.map((p) => (
          <div key={p.id} className="provider-row">
            <div className="provider-info">
              <span className="provider-name">{p.name}</span>
              <span className={`provider-status ${p.configured ? 'ok' : 'missing'}`}>
                {p.configured ? 'Configured' : 'Not set'}
              </span>
            </div>
            <input
              type="password"
              className="provider-key-input"
              placeholder={p.key_env}
              value={keyInputs[p.id] || ''}
              onChange={(e) =>
                setKeyInputs((prev) => ({ ...prev, [p.id]: e.target.value }))
              }
            />
          </div>
        ))}
      </div>
      <button
        className="settings-save-btn"
        onClick={saveProviderKeys}
        disabled={saving || Object.values(keyInputs).every((v) => !v?.trim())}
      >
        {saving ? 'Saving...' : 'Save Keys'}
      </button>
    </div>
  );
}

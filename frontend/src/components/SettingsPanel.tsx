import { useState, useEffect, useCallback } from 'react';
import { api } from '../api';
import type { Provider } from '../types';

interface Props {
  onClose: () => void;
}

type Tab = 'providers' | 'agent' | 'sandbox' | 'writing';

export function SettingsPanel({ onClose }: Props) {
  const [tab, setTab] = useState<Tab>('providers');
  const [providers, setProviders] = useState<Provider[]>([]);
  const [keyInputs, setKeyInputs] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);
  const [saveMsg, setSaveMsg] = useState('');
  const [, setSettings] = useState<Record<string, any>>({});

  // Agent settings form state
  const [agentForm, setAgentForm] = useState({
    default_model: '',
    research_model: '',
    yolo_mode: false,
  });

  // Sandbox form state
  const [sandboxForm, setSandboxForm] = useState({
    default_sandbox: 'local',
    modal_token_id: '',
    modal_token_secret: '',
  });

  // Writing form state
  const [writingForm, setWritingForm] = useState({
    citation_style: 'apa',
    export_format: 'markdown',
  });

  useEffect(() => {
    api.getProviders().then((d) => setProviders(d.providers || [])).catch(() => {});
    api.getSettings().then((d) => {
      const s = d.settings || {};
      setSettings(s);
      if (s.agent) {
        setAgentForm((prev) => ({
          ...prev,
          default_model: s.agent.default_model || '',
          research_model: s.agent.research_model || '',
          yolo_mode: s.agent.yolo_mode === true,
        }));
      }
      if (s.sandbox) {
        setSandboxForm((prev) => ({
          ...prev,
          default_sandbox: s.sandbox.default_sandbox || 'local',
        }));
      }
      if (s.writing) {
        setWritingForm((prev) => ({
          ...prev,
          citation_style: s.writing.citation_style || 'apa',
          export_format: s.writing.export_format || 'markdown',
        }));
      }
    }).catch(() => {});
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

  const saveAgentSettings = async () => {
    setSaving(true);
    try {
      if (agentForm.default_model) {
        await api.updateSetting('agent', 'default_model', agentForm.default_model);
      }
      if (agentForm.research_model) {
        await api.updateSetting('agent', 'research_model', agentForm.research_model);
      }
      await api.updateSetting('agent', 'yolo_mode', agentForm.yolo_mode);
      flash('Saved');
    } catch {
      flash('Error saving');
    } finally {
      setSaving(false);
    }
  };

  const saveSandboxSettings = async () => {
    setSaving(true);
    try {
      await api.updateSetting('sandbox', 'default_sandbox', sandboxForm.default_sandbox);
      if (sandboxForm.modal_token_id) {
        await api.updateSetting('providers', 'modal_token_id', sandboxForm.modal_token_id);
      }
      if (sandboxForm.modal_token_secret) {
        await api.updateSetting('providers', 'modal_token_secret', sandboxForm.modal_token_secret);
      }
      flash('Saved');
    } catch {
      flash('Error saving');
    } finally {
      setSaving(false);
    }
  };

  const saveWritingSettings = async () => {
    setSaving(true);
    try {
      await api.updateSetting('writing', 'citation_style', writingForm.citation_style);
      await api.updateSetting('writing', 'export_format', writingForm.export_format);
      flash('Saved');
    } catch {
      flash('Error saving');
    } finally {
      setSaving(false);
    }
  };

  const tabs: { id: Tab; label: string }[] = [
    { id: 'providers', label: 'Providers' },
    { id: 'agent', label: 'Agent' },
    { id: 'sandbox', label: 'Sandbox' },
    { id: 'writing', label: 'Writing' },
  ];

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal settings-modal" onClick={(e) => e.stopPropagation()}>
        <div className="settings-header">
          <h2>Settings</h2>
          <div className="settings-header-right">
            {saveMsg && <span className="save-flash">{saveMsg}</span>}
            <button className="modal-close-btn" onClick={onClose}>&times;</button>
          </div>
        </div>

        <div className="settings-tabs">
          {tabs.map((t) => (
            <button
              key={t.id}
              className={`settings-tab ${tab === t.id ? 'active' : ''}`}
              onClick={() => setTab(t.id)}
            >
              {t.label}
            </button>
          ))}
        </div>

        <div className="settings-body">
          {/* ── Providers ── */}
          {tab === 'providers' && (
            <div className="settings-section">
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
          )}

          {/* ── Agent ── */}
          {tab === 'agent' && (
            <div className="settings-section">
              <p className="settings-hint">
                Model used for new conversations. Leave blank to auto-detect from configured providers.
              </p>
              <div className="settings-field">
                <label>Default Model</label>
                <input
                  type="text"
                  placeholder="auto-detect (e.g. anthropic/claude-sonnet-4)"
                  value={agentForm.default_model}
                  onChange={(e) => setAgentForm((f) => ({ ...f, default_model: e.target.value }))}
                />
              </div>
              <div className="settings-field">
                <label>Research / Title Model (cheaper)</label>
                <input
                  type="text"
                  placeholder="auto-detect (e.g. openai/gpt-4o-mini)"
                  value={agentForm.research_model}
                  onChange={(e) => setAgentForm((f) => ({ ...f, research_model: e.target.value }))}
                />
              </div>
              <div className="settings-field checkbox-field">
                <label>
                  <input
                    type="checkbox"
                    checked={agentForm.yolo_mode}
                    onChange={(e) => setAgentForm((f) => ({ ...f, yolo_mode: e.target.checked }))}
                  />
                  YOLO Mode (auto-approve all tool calls)
                </label>
              </div>
              <button className="settings-save-btn" onClick={saveAgentSettings} disabled={saving}>
                {saving ? 'Saving...' : 'Save Agent Settings'}
              </button>
            </div>
          )}

          {/* ── Sandbox ── */}
          {tab === 'sandbox' && (
            <div className="settings-section">
              <p className="settings-hint">
                Execution environment for running code. Local runs on your machine.
              </p>
              <div className="settings-field">
                <label>Default Sandbox</label>
                <select
                  value={sandboxForm.default_sandbox}
                  onChange={(e) => setSandboxForm((f) => ({ ...f, default_sandbox: e.target.value }))}
                >
                  <option value="local">Local</option>
                  <option value="ssh">SSH Remote</option>
                  <option value="modal">Modal Cloud</option>
                </select>
              </div>
              <div className="settings-field">
                <label>Modal Token ID</label>
                <input
                  type="password"
                  placeholder="MODAL_TOKEN_ID"
                  value={sandboxForm.modal_token_id}
                  onChange={(e) => setSandboxForm((f) => ({ ...f, modal_token_id: e.target.value }))}
                />
              </div>
              <div className="settings-field">
                <label>Modal Token Secret</label>
                <input
                  type="password"
                  placeholder="MODAL_TOKEN_SECRET"
                  value={sandboxForm.modal_token_secret}
                  onChange={(e) => setSandboxForm((f) => ({ ...f, modal_token_secret: e.target.value }))}
                />
              </div>
              <button className="settings-save-btn" onClick={saveSandboxSettings} disabled={saving}>
                {saving ? 'Saving...' : 'Save Sandbox Settings'}
              </button>
            </div>
          )}

          {/* ── Writing ── */}
          {tab === 'writing' && (
            <div className="settings-section">
              <p className="settings-hint">Paper writing preferences.</p>
              <div className="settings-field">
                <label>Citation Style</label>
                <select
                  value={writingForm.citation_style}
                  onChange={(e) => setWritingForm((f) => ({ ...f, citation_style: e.target.value }))}
                >
                  <option value="apa">APA</option>
                  <option value="ieee">IEEE</option>
                  <option value="acm">ACM</option>
                  <option value="chicago">Chicago</option>
                </select>
              </div>
              <div className="settings-field">
                <label>Export Format</label>
                <select
                  value={writingForm.export_format}
                  onChange={(e) => setWritingForm((f) => ({ ...f, export_format: e.target.value }))}
                >
                  <option value="markdown">Markdown</option>
                  <option value="latex">LaTeX</option>
                </select>
              </div>
              <button className="settings-save-btn" onClick={saveWritingSettings} disabled={saving}>
                {saving ? 'Saving...' : 'Save Writing Settings'}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

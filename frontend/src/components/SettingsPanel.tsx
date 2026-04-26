import { useState, useEffect, useCallback } from 'react';
import { X } from 'lucide-react';
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
    <div 
      className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4"
      onClick={onClose}
    >
      <div 
        className="bg-surface rounded-xl border border-border w-full max-w-2xl max-h-[80vh] flex flex-col shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-border">
          <h2 className="text-xl font-semibold text-text">Settings</h2>
          <div className="flex items-center gap-3">
            {saveMsg && <span className="text-sm text-success">{saveMsg}</span>}
            <button 
              className="w-8 h-8 rounded-lg flex items-center justify-center text-text-dim hover:bg-surface-hover hover:text-text transition-colors"
              onClick={onClose}
            >
              <X size={18} />
            </button>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-border px-6">
          {tabs.map((t) => (
            <button
              key={t.id}
              className={`py-3 px-4 text-sm font-medium transition-colors ${
                tab === t.id ? 'text-primary border-b-2 border-primary' : 'text-text-dim hover:text-text'
              }`}
              onClick={() => setTab(t.id)}
            >
              {t.label}
            </button>
          ))}
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto p-6">
          {/* Providers */}
          {tab === 'providers' && (
            <div>
              <p className="text-sm text-text-dim mb-4">
                API keys are stored in the database per-user. They override .env values.
              </p>
              <div className="flex flex-col gap-3 mb-6">
                {providers.map((p) => (
                  <div key={p.id} className="flex items-center gap-3 p-3 bg-bg rounded-lg border border-border">
                    <div className="flex-1">
                      <span className="font-medium text-text block">{p.name}</span>
                      <span className={`text-xs ${p.configured ? 'text-success' : 'text-text-dim'}`}>
                        {p.configured ? 'Configured' : 'Not set'}
                      </span>
                    </div>
                    <input
                      type="password"
                      className="w-48 bg-surface border border-border rounded-lg px-3 py-2 text-sm text-text placeholder-text-dim focus:border-primary focus:outline-none"
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
                className="w-full py-3 bg-primary text-white rounded-lg font-medium hover:bg-primary-hover transition-colors disabled:opacity-50"
                onClick={saveProviderKeys}
                disabled={saving || Object.values(keyInputs).every((v) => !v?.trim())}
              >
                {saving ? 'Saving...' : 'Save Keys'}
              </button>
            </div>
          )}

          {/* Agent */}
          {tab === 'agent' && (
            <div>
              <p className="text-sm text-text-dim mb-4">
                Model used for new conversations. Leave blank to auto-detect from configured providers.
              </p>
              <div className="flex flex-col gap-4 mb-6">
                <div>
                  <label className="block text-sm font-medium text-text mb-1.5">Default Model</label>
                  <input
                    type="text"
                    className="w-full bg-bg border border-border rounded-lg px-4 py-2.5 text-text placeholder-text-dim focus:border-primary focus:outline-none"
                    placeholder="auto-detect (e.g. anthropic/claude-sonnet-4)"
                    value={agentForm.default_model}
                    onChange={(e) => setAgentForm((f) => ({ ...f, default_model: e.target.value }))}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-text mb-1.5">Research / Title Model (cheaper)</label>
                  <input
                    type="text"
                    className="w-full bg-bg border border-border rounded-lg px-4 py-2.5 text-text placeholder-text-dim focus:border-primary focus:outline-none"
                    placeholder="auto-detect (e.g. openai/gpt-4o-mini)"
                    value={agentForm.research_model}
                    onChange={(e) => setAgentForm((f) => ({ ...f, research_model: e.target.value }))}
                  />
                </div>
                <div>
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      className="w-4 h-4 rounded border-border text-primary focus:ring-primary"
                      checked={agentForm.yolo_mode}
                      onChange={(e) => setAgentForm((f) => ({ ...f, yolo_mode: e.target.checked }))}
                    />
                    <span className="text-sm text-text">YOLO Mode (auto-approve all tool calls)</span>
                  </label>
                </div>
              </div>
              <button 
                className="w-full py-3 bg-primary text-white rounded-lg font-medium hover:bg-primary-hover transition-colors disabled:opacity-50"
                onClick={saveAgentSettings} 
                disabled={saving}
              >
                {saving ? 'Saving...' : 'Save Agent Settings'}
              </button>
            </div>
          )}

          {/* Sandbox */}
          {tab === 'sandbox' && (
            <div>
              <p className="text-sm text-text-dim mb-4">
                Execution environment for running code. Local runs on your machine.
              </p>
              <div className="flex flex-col gap-4 mb-6">
                <div>
                  <label className="block text-sm font-medium text-text mb-1.5">Default Sandbox</label>
                  <select
                    className="w-full bg-bg border border-border rounded-lg px-4 py-2.5 text-text focus:border-primary focus:outline-none"
                    value={sandboxForm.default_sandbox}
                    onChange={(e) => setSandboxForm((f) => ({ ...f, default_sandbox: e.target.value }))}
                  >
                    <option value="local">Local</option>
                    <option value="ssh">SSH Remote</option>
                    <option value="modal">Modal Cloud</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-text mb-1.5">Modal Token ID</label>
                  <input
                    type="password"
                    className="w-full bg-bg border border-border rounded-lg px-4 py-2.5 text-text placeholder-text-dim focus:border-primary focus:outline-none"
                    placeholder="MODAL_TOKEN_ID"
                    value={sandboxForm.modal_token_id}
                    onChange={(e) => setSandboxForm((f) => ({ ...f, modal_token_id: e.target.value }))}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-text mb-1.5">Modal Token Secret</label>
                  <input
                    type="password"
                    className="w-full bg-bg border border-border rounded-lg px-4 py-2.5 text-text placeholder-text-dim focus:border-primary focus:outline-none"
                    placeholder="MODAL_TOKEN_SECRET"
                    value={sandboxForm.modal_token_secret}
                    onChange={(e) => setSandboxForm((f) => ({ ...f, modal_token_secret: e.target.value }))}
                  />
                </div>
              </div>
              <button 
                className="w-full py-3 bg-primary text-white rounded-lg font-medium hover:bg-primary-hover transition-colors disabled:opacity-50"
                onClick={saveSandboxSettings} 
                disabled={saving}
              >
                {saving ? 'Saving...' : 'Save Sandbox Settings'}
              </button>
            </div>
          )}

          {/* Writing */}
          {tab === 'writing' && (
            <div>
              <p className="text-sm text-text-dim mb-4">Paper writing preferences.</p>
              <div className="flex flex-col gap-4 mb-6">
                <div>
                  <label className="block text-sm font-medium text-text mb-1.5">Citation Style</label>
                  <select
                    className="w-full bg-bg border border-border rounded-lg px-4 py-2.5 text-text focus:border-primary focus:outline-none"
                    value={writingForm.citation_style}
                    onChange={(e) => setWritingForm((f) => ({ ...f, citation_style: e.target.value }))}
                  >
                    <option value="apa">APA</option>
                    <option value="ieee">IEEE</option>
                    <option value="acm">ACM</option>
                    <option value="chicago">Chicago</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-text mb-1.5">Export Format</label>
                  <select
                    className="w-full bg-bg border border-border rounded-lg px-4 py-2.5 text-text focus:border-primary focus:outline-none"
                    value={writingForm.export_format}
                    onChange={(e) => setWritingForm((f) => ({ ...f, export_format: e.target.value }))}
                  >
                    <option value="markdown">Markdown</option>
                    <option value="latex">LaTeX</option>
                  </select>
                </div>
              </div>
              <button 
                className="w-full py-3 bg-primary text-white rounded-lg font-medium hover:bg-primary-hover transition-colors disabled:opacity-50"
                onClick={saveWritingSettings} 
                disabled={saving}
              >
                {saving ? 'Saving...' : 'Save Writing Settings'}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

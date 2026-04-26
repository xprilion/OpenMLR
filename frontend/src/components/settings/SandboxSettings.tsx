import { useState, useEffect, useCallback } from 'react';
import { api } from '../../api';

export function SandboxSettings() {
  const [form, setForm] = useState({
    default_sandbox: 'local',
    modal_token_id: '',
    modal_token_secret: '',
  });
  const [saving, setSaving] = useState(false);
  const [saveMsg, setSaveMsg] = useState('');

  useEffect(() => {
    api.getSettings().then((d) => {
      const s = d.settings || {};
      if (s.sandbox) {
        setForm((prev) => ({
          ...prev,
          default_sandbox: s.sandbox.default_sandbox || 'local',
        }));
      }
    }).catch(() => {});
  }, []);

  const flash = useCallback((msg: string) => {
    setSaveMsg(msg);
    setTimeout(() => setSaveMsg(''), 2000);
  }, []);

  const save = async () => {
    setSaving(true);
    try {
      await api.updateSetting('sandbox', 'default_sandbox', form.default_sandbox);
      if (form.modal_token_id) {
        await api.updateSetting('providers', 'modal_token_id', form.modal_token_id);
      }
      if (form.modal_token_secret) {
        await api.updateSetting('providers', 'modal_token_secret', form.modal_token_secret);
      }
      flash('Saved');
    } catch {
      flash('Error saving');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div>
      {saveMsg && (
        <div className="mb-4 px-4 py-2 bg-success/10 text-success rounded-lg text-sm">
          {saveMsg}
        </div>
      )}
      
      <p className="text-text-dim mb-6">
        Execution environment for running code. Local runs on your machine.
      </p>
      
      <div className="flex flex-col gap-5 mb-8">
        <div>
          <label className="block text-sm font-medium text-text mb-2">Default Sandbox</label>
          <select
            className="w-full bg-bg border border-border rounded-lg px-4 py-3 text-text focus:border-primary focus:outline-none transition-colors"
            value={form.default_sandbox}
            onChange={(e) => setForm((f) => ({ ...f, default_sandbox: e.target.value }))}
          >
            <option value="local">Local</option>
            <option value="ssh">SSH Remote</option>
            <option value="modal">Modal Cloud</option>
          </select>
        </div>
        
        <div>
          <label className="block text-sm font-medium text-text mb-2">Modal Token ID</label>
          <input
            type="password"
            className="w-full bg-bg border border-border rounded-lg px-4 py-3 text-text placeholder-text-dim focus:border-primary focus:outline-none transition-colors"
            placeholder="MODAL_TOKEN_ID"
            value={form.modal_token_id}
            onChange={(e) => setForm((f) => ({ ...f, modal_token_id: e.target.value }))}
          />
        </div>
        
        <div>
          <label className="block text-sm font-medium text-text mb-2">Modal Token Secret</label>
          <input
            type="password"
            className="w-full bg-bg border border-border rounded-lg px-4 py-3 text-text placeholder-text-dim focus:border-primary focus:outline-none transition-colors"
            placeholder="MODAL_TOKEN_SECRET"
            value={form.modal_token_secret}
            onChange={(e) => setForm((f) => ({ ...f, modal_token_secret: e.target.value }))}
          />
        </div>
      </div>
      
      <button 
        className="w-full py-3 bg-primary text-white rounded-lg font-medium hover:bg-primary-hover transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        onClick={save} 
        disabled={saving}
      >
        {saving ? 'Saving...' : 'Save Sandbox Settings'}
      </button>
    </div>
  );
}

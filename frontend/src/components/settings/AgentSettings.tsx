

import { useState, useEffect, useCallback } from 'react';
import { api } from '../../api';

export function AgentSettings() {
  const [form, setForm] = useState({
    default_model: '',
    research_model: '',
    yolo_mode: false,
  });
  const [saving, setSaving] = useState(false);
  const [saveMsg, setSaveMsg] = useState('');

  useEffect(() => {
    api.getSettings().then((d) => {
      const s = d.settings || {};
      if (s.agent) {
        setForm((prev) => ({
          ...prev,
          default_model: s.agent.default_model || '',
          research_model: s.agent.research_model || '',
          yolo_mode: s.agent.yolo_mode === true,
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
      if (form.default_model) {
        await api.updateSetting('agent', 'default_model', form.default_model);
      }
      if (form.research_model) {
        await api.updateSetting('agent', 'research_model', form.research_model);
      }
      await api.updateSetting('agent', 'yolo_mode', form.yolo_mode);
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
        Model used for new conversations. Leave blank to auto-detect from configured providers.
      </p>
      
      <div className="flex flex-col gap-5 mb-8">
        <div>
          <label className="block text-sm font-medium text-text mb-2">Default Model</label>
          <input
            type="text"
            className="w-full bg-bg border border-border rounded-lg px-4 py-3 text-text placeholder-text-dim focus:border-primary focus:outline-none transition-colors"
            placeholder="auto-detect (e.g. anthropic/claude-sonnet-4)"
            value={form.default_model}
            onChange={(e) => setForm((f) => ({ ...f, default_model: e.target.value }))}
          />
        </div>
        
        <div>
          <label className="block text-sm font-medium text-text mb-2">Research / Title Model (cheaper)</label>
          <input
            type="text"
            className="w-full bg-bg border border-border rounded-lg px-4 py-3 text-text placeholder-text-dim focus:border-primary focus:outline-none transition-colors"
            placeholder="auto-detect (e.g. openai/gpt-4o-mini)"
            value={form.research_model}
            onChange={(e) => setForm((f) => ({ ...f, research_model: e.target.value }))}
          />
        </div>
        
        <div className="flex items-center gap-3 p-4 bg-surface rounded-lg border border-border">
          <input
            type="checkbox"
            id="yolo-mode"
            className="w-5 h-5 rounded border-border text-primary focus:ring-primary cursor-pointer"
            checked={form.yolo_mode}
            onChange={(e) => setForm((f) => ({ ...f, yolo_mode: e.target.checked }))}
          />
          <label htmlFor="yolo-mode" className="cursor-pointer">
            <span className="font-medium text-text block">YOLO Mode</span>
            <span className="text-sm text-text-dim">Auto-approve all tool calls</span>
          </label>
        </div>
      </div>
      
      <button 
        className="w-full py-3 bg-primary text-white rounded-lg font-medium hover:bg-primary-hover transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        onClick={save} 
        disabled={saving}
      >
        {saving ? 'Saving...' : 'Save Agent Settings'}
      </button>
    </div>
  );
}

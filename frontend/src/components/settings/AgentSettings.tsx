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
    <div className="settings-section">
      {saveMsg && <span className="save-flash">{saveMsg}</span>}
      <p className="settings-hint">
        Model used for new conversations. Leave blank to auto-detect from configured providers.
      </p>
      <div className="settings-field">
        <label>Default Model</label>
        <input
          type="text"
          placeholder="auto-detect (e.g. anthropic/claude-sonnet-4)"
          value={form.default_model}
          onChange={(e) => setForm((f) => ({ ...f, default_model: e.target.value }))}
        />
      </div>
      <div className="settings-field">
        <label>Research / Title Model (cheaper)</label>
        <input
          type="text"
          placeholder="auto-detect (e.g. openai/gpt-4o-mini)"
          value={form.research_model}
          onChange={(e) => setForm((f) => ({ ...f, research_model: e.target.value }))}
        />
      </div>
      <div className="settings-field checkbox-field">
        <label>
          <input
            type="checkbox"
            checked={form.yolo_mode}
            onChange={(e) => setForm((f) => ({ ...f, yolo_mode: e.target.checked }))}
          />
          YOLO Mode (auto-approve all tool calls)
        </label>
      </div>
      <button className="settings-save-btn" onClick={save} disabled={saving}>
        {saving ? 'Saving...' : 'Save Agent Settings'}
      </button>
    </div>
  );
}

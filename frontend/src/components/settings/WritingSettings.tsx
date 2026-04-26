import { useState, useEffect, useCallback } from 'react';
import { api } from '../../api';

export function WritingSettings() {
  const [form, setForm] = useState({
    citation_style: 'apa',
    export_format: 'markdown',
  });
  const [saving, setSaving] = useState(false);
  const [saveMsg, setSaveMsg] = useState('');

  useEffect(() => {
    api.getSettings().then((d) => {
      const s = d.settings || {};
      if (s.writing) {
        setForm((prev) => ({
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

  const save = async () => {
    setSaving(true);
    try {
      await api.updateSetting('writing', 'citation_style', form.citation_style);
      await api.updateSetting('writing', 'export_format', form.export_format);
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
      <p className="settings-hint">Paper writing preferences.</p>
      <div className="settings-field">
        <label>Citation Style</label>
        <select
          value={form.citation_style}
          onChange={(e) => setForm((f) => ({ ...f, citation_style: e.target.value }))}
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
          value={form.export_format}
          onChange={(e) => setForm((f) => ({ ...f, export_format: e.target.value }))}
        >
          <option value="markdown">Markdown</option>
          <option value="latex">LaTeX</option>
        </select>
      </div>
      <button className="settings-save-btn" onClick={save} disabled={saving}>
        {saving ? 'Saving...' : 'Save Writing Settings'}
      </button>
    </div>
  );
}

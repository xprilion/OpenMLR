import { useState, useEffect, useCallback } from 'react';
import { api } from '../../api';

export function WritingSettings() {
  const [form, setForm] = useState({
    citation_style: 'apa',
    export_format: 'markdown',
    author_name: '',
    author_email: '',
    author_affiliation: '',
    author_orcid: '',
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
          author_name: s.writing.author_name || '',
          author_email: s.writing.author_email || '',
          author_affiliation: s.writing.author_affiliation || '',
          author_orcid: s.writing.author_orcid || '',
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
      if (form.author_name) await api.updateSetting('writing', 'author_name', form.author_name);
      if (form.author_email) await api.updateSetting('writing', 'author_email', form.author_email);
      if (form.author_affiliation) await api.updateSetting('writing', 'author_affiliation', form.author_affiliation);
      if (form.author_orcid) await api.updateSetting('writing', 'author_orcid', form.author_orcid);
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
      
      <p className="text-text-dim mb-6">Paper writing preferences and author information.</p>
      
      <div className="flex flex-col gap-5 mb-8">
        {/* Author Information Section */}
        <div className="border-b border-border pb-5 mb-2">
          <h3 className="text-sm font-semibold text-text mb-4">Author Information</h3>
          <p className="text-xs text-text-dim mb-4">These details will be included in generated papers.</p>
          
          <div className="flex flex-col gap-4">
            <div>
              <label className="block text-sm font-medium text-text mb-2">Full Name</label>
              <input
                type="text"
                className="w-full bg-bg border border-border rounded-lg px-4 py-3 text-text placeholder-text-dim focus:border-primary focus:outline-none transition-colors"
                placeholder="e.g., Jane Doe"
                value={form.author_name}
                onChange={(e) => setForm((f) => ({ ...f, author_name: e.target.value }))}
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-text mb-2">Email</label>
              <input
                type="email"
                className="w-full bg-bg border border-border rounded-lg px-4 py-3 text-text placeholder-text-dim focus:border-primary focus:outline-none transition-colors"
                placeholder="e.g., jane.doe@university.edu"
                value={form.author_email}
                onChange={(e) => setForm((f) => ({ ...f, author_email: e.target.value }))}
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-text mb-2">Affiliation</label>
              <input
                type="text"
                className="w-full bg-bg border border-border rounded-lg px-4 py-3 text-text placeholder-text-dim focus:border-primary focus:outline-none transition-colors"
                placeholder="e.g., Department of Computer Science, MIT"
                value={form.author_affiliation}
                onChange={(e) => setForm((f) => ({ ...f, author_affiliation: e.target.value }))}
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-text mb-2">ORCID <span className="text-text-dim font-normal">(optional)</span></label>
              <input
                type="text"
                className="w-full bg-bg border border-border rounded-lg px-4 py-3 text-text placeholder-text-dim focus:border-primary focus:outline-none transition-colors"
                placeholder="e.g., 0000-0002-1234-5678"
                value={form.author_orcid}
                onChange={(e) => setForm((f) => ({ ...f, author_orcid: e.target.value }))}
              />
            </div>
          </div>
        </div>
        
        {/* Writing Preferences Section */}
        <div>
          <label className="block text-sm font-medium text-text mb-2">Citation Style</label>
          <select
            className="w-full bg-bg border border-border rounded-lg px-4 py-3 text-text focus:border-primary focus:outline-none transition-colors"
            value={form.citation_style}
            onChange={(e) => setForm((f) => ({ ...f, citation_style: e.target.value }))}
          >
            <option value="apa">APA</option>
            <option value="ieee">IEEE</option>
            <option value="acm">ACM</option>
            <option value="chicago">Chicago</option>
          </select>
        </div>
        
        <div>
          <label className="block text-sm font-medium text-text mb-2">Export Format</label>
          <select
            className="w-full bg-bg border border-border rounded-lg px-4 py-3 text-text focus:border-primary focus:outline-none transition-colors"
            value={form.export_format}
            onChange={(e) => setForm((f) => ({ ...f, export_format: e.target.value }))}
          >
            <option value="markdown">Markdown</option>
            <option value="latex">LaTeX</option>
          </select>
        </div>
      </div>
      
      <button 
        className="w-full py-3 bg-primary text-white rounded-lg font-medium hover:bg-primary-hover transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        onClick={save} 
        disabled={saving}
      >
        {saving ? 'Saving...' : 'Save Writing Settings'}
      </button>
    </div>
  );
}

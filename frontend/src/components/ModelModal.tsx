import { useState } from 'react';
import { api } from '../api';

interface Props {
  currentModel: string;
  onModelChange: (model: string) => void;
}

const POPULAR_MODELS = [
  { label: 'OpenAI GPT-4o', value: 'openai/gpt-4o' },
  { label: 'OpenAI GPT-4o-mini', value: 'openai/gpt-4o-mini' },
  { label: 'Anthropic Claude Sonnet 4', value: 'anthropic/claude-sonnet-4' },
  { label: 'Anthropic Claude Opus 4', value: 'anthropic/claude-opus-4' },
  { label: 'OpenRouter GPT-4o', value: 'openrouter/openai/gpt-4o' },
  { label: 'OpenRouter Claude Sonnet', value: 'openrouter/anthropic/claude-sonnet-4' },
];

export function ModelModal({ currentModel, onModelChange }: Props) {
  const [open, setOpen] = useState(false);
  const [custom, setCustom] = useState('');

  const select = async (model: string) => {
    await api.setModel(model);
    onModelChange(model);
    setOpen(false);
  };

  return (
    <>
      <button className="model-btn" onClick={() => setOpen(true)}>
        {currentModel}
      </button>

      {open && (
        <div className="modal-overlay" onClick={() => setOpen(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h3>Switch Model</h3>
            <div className="model-list">
              {POPULAR_MODELS.map((m) => (
                <button
                  key={m.value}
                  className={`model-option ${m.value === currentModel ? 'active' : ''}`}
                  onClick={() => select(m.value)}
                >
                  {m.label}
                </button>
              ))}
            </div>
            <div className="custom-model">
              <input
                type="text"
                placeholder="Custom model ID (e.g. openrouter/anthropic/claude-3-opus)"
                value={custom}
                onChange={(e) => setCustom(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && custom.trim()) {
                    select(custom.trim());
                  }
                }}
              />
              <button
                disabled={!custom.trim()}
                onClick={() => custom.trim() && select(custom.trim())}
              >
                Use Custom
              </button>
            </div>
            <button className="modal-close" onClick={() => setOpen(false)}>
              Cancel
            </button>
          </div>
        </div>
      )}
    </>
  );
}

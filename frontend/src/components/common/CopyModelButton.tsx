import { useState } from 'react';
import { Copy, Check } from 'lucide-react';

export function CopyModelButton({ model }: Readonly<{ model: string }>) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    // Extract just the model ID (remove context info if present)
    const modelId = model.split(' ')[0];
    try {
      if (typeof navigator !== 'undefined' && navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(modelId);
      } else {
        const textArea = document.createElement('textarea');
        textArea.value = modelId;
        document.body.appendChild(textArea);
        textArea.select();
        textArea.remove();
      }
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback
    }
  };

  return (
    <button
      type="button"
      onClick={handleCopy}
      className="w-8 h-8 rounded-lg flex items-center justify-center text-text-dim hover:bg-surface-hover hover:text-text transition-colors"
      title="Copy model ID"
    >
      {copied ? <Check size={16} className="text-success" /> : <Copy size={16} />}
    </button>
  );
}

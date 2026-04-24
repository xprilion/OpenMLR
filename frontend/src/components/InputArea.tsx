import { useState, useRef, useEffect } from 'react';

interface Props {
  disabled: boolean;
  onSend: (text: string) => void;
}

export function InputArea({ disabled, onSend }: Props) {
  const [text, setText] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = Math.min(el.scrollHeight, 200) + 'px';
  }, [text]);

  const submit = () => {
    const trimmed = text.trim();
    if (!trimmed || disabled) return;
    setText('');
    onSend(trimmed);
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  return (
    <div className="input-area">
      <textarea
        ref={textareaRef}
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            submit();
          }
        }}
        placeholder="Type a message..."
        rows={1}
        disabled={disabled}
      />
      <button onClick={submit} disabled={disabled || !text.trim()}>
        {disabled ? 'Thinking...' : 'Send'}
      </button>
    </div>
  );
}

import React, { useState } from 'react';
import { Send } from 'lucide-react';

const InputArea = ({ onSend, disabled }) => {
  const [input, setInput] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!input.trim() || disabled) return;
    onSend(input);
    setInput('');
  };

  return (
    <form className="input-area" onSubmit={handleSubmit}>
      <input 
        type="text" 
        className="input-field" 
        placeholder="How can I help you find assessments today?" 
        value={input}
        onChange={(e) => setInput(e.target.value)}
        disabled={disabled}
      />
      <button type="submit" className="send-btn" disabled={disabled || !input.trim()}>
        <Send size={20} />
      </button>
    </form>
  );
};

export default InputArea;

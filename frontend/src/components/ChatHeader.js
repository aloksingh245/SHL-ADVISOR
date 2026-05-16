import React from 'react';
import { Trash2, RotateCcw } from 'lucide-react';

const ChatHeader = ({ onClear }) => (
  <header className="header">
    <div className="header-left">
      <div className="header-logo">SHL ADVISOR</div>
      <div className="header-subtitle">EXPERT SYSTEM</div>
    </div>
    <button className="clear-btn" onClick={onClear} title="Clear Chat">
      <RotateCcw size={18} />
      <span>Reset Session</span>
    </button>
  </header>
);

export default ChatHeader;

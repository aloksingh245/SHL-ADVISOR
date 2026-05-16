import React, { useState, useEffect, useRef } from 'react';
import './styles/App.css';
import ChatHeader from './components/ChatHeader';
import ChatWindow from './components/ChatWindow';
import InputArea from './components/InputArea';

const API_URL = 'http://localhost:8001';

function App() {
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [suggestions, setSuggestions] = useState([
    "Junior Java Developer",
    "Senior Product Manager",
    "Sales Associate skills",
    "Compare cognitive tests"
  ]);

  const initChat = async () => {
    setLoading(true);
    try {
      const response = await fetch(`${API_URL}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ messages: [] })
      });
      const data = await response.json();
      setMessages([{ 
        role: 'assistant', 
        content: data.reply, 
        recommendations: data.recommendations 
      }]);
    } catch (error) {
      console.error('Failed to init:', error);
      setMessages([{ 
        role: 'assistant', 
        content: "Connection error. Please ensure the FastAPI backend is running on port 8001.", 
        recommendations: [] 
      }]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    initChat();
  }, []);

  const handleClear = () => {
    setMessages([]);
    initChat();
  };

  const handleSend = async (input) => {
    if (!input.trim() || loading) return;

    const userMsg = { role: 'user', content: input };
    const currentHistory = messages.map(m => ({ role: m.role, content: m.content }));
    const newHistory = [...currentHistory, userMsg];
    
    setMessages(prev => [...prev, userMsg]);
    setLoading(true);
    setSuggestions([]); // Clear suggestions when user starts typing/sending

    try {
      const response = await fetch(`${API_URL}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ messages: newHistory })
      });
      const data = await response.json();
      setMessages(prev => [...prev, { 
        role: 'assistant', 
        content: data.reply, 
        recommendations: data.recommendations 
      }]);
      
      // Dynamic suggestions based on state or role if we had them, 
      // but for now just some follow-ups
      if (data.recommendations && data.recommendations.length > 0) {
        setSuggestions(["Tell me more about the first one", "Compare these results", "I have more requirements"]);
      } else {
        setSuggestions(["Junior role", "Management role", "Technical skills focus"]);
      }

    } catch (error) {
      console.error('Chat error:', error);
      setMessages(prev => [...prev, { 
        role: 'assistant', 
        content: "Sorry, I encountered an error processing your request.", 
        recommendations: [] 
      }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app-container">
      <ChatHeader onClear={handleClear} />
      <ChatWindow messages={messages} loading={loading} />
      <div className="suggestions-container">
        {suggestions.map((s, i) => (
          <button key={i} className="suggestion-chip" onClick={() => handleSend(s)}>
            {s}
          </button>
        ))}
      </div>
      <InputArea onSend={handleSend} disabled={loading} />
    </div>
  );
}

export default App;

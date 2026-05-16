import React, { useRef, useEffect } from 'react';
import MessageBubble from './MessageBubble';
import { motion, AnimatePresence } from 'framer-motion';

const ChatWindow = ({ messages, loading }) => {
  const chatEndRef = useRef(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  return (
    <main className="chat-window">
      <AnimatePresence>
        {messages.map((msg, idx) => (
          <motion.div
            key={idx}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3 }}
            style={{ width: '100%' }}
          >
            <MessageBubble message={msg} />
          </motion.div>
        ))}
      </AnimatePresence>
      
      {loading && (
        <motion.div 
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="typing-indicator"
        >
          <span></span>
          <span></span>
          <span></span>
          <p>Advisor is thinking...</p>
        </motion.div>
      )}
      <div ref={chatEndRef} />
    </main>
  );
};

export default ChatWindow;

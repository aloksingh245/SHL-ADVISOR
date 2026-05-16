import React from 'react';
import ReactMarkdown from 'react-markdown';
import RecommendationGrid from './RecommendationGrid';

const MessageBubble = ({ message }) => {
  const { role, content, recommendations } = message;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', width: '100%' }}>
      <div className={`message message-${role}`}>
        <ReactMarkdown 
          components={{
            a: ({node, ...props}) => <a {...props} target="_blank" rel="noopener noreferrer" />
          }}
        >
          {content}
        </ReactMarkdown>
      </div>
      {recommendations && recommendations.length > 0 && (
        <RecommendationGrid recommendations={recommendations} />
      )}
    </div>
  );
};

export default MessageBubble;

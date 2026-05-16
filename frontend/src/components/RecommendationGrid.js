import React from 'react';
import { ExternalLink } from 'lucide-react';
import { motion } from 'framer-motion';

const RecommendationGrid = ({ recommendations }) => {
  return (
    <div className="recommendation-grid">
      {recommendations.map((rec, idx) => (
        <motion.div 
          key={idx} 
          className="card"
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: idx * 0.1 }}
          whileHover={{ y: -5, boxShadow: "0 10px 15px -3px rgba(0, 0, 0, 0.1)" }}
        >
          <div>
            <div className="card-type">{rec.test_type}</div>
            <div className="card-name">{rec.name}</div>
            {rec.duration && <div className="card-meta">Duration: {rec.duration}</div>}
          </div>
          <a 
            href={rec.url} 
            target="_blank" 
            rel="noopener noreferrer" 
            className="card-link"
          >
            View Product Details
            <ExternalLink size={14} style={{ marginLeft: '4px' }} />
          </a>
        </motion.div>
      ))}
    </div>
  );
};

export default RecommendationGrid;

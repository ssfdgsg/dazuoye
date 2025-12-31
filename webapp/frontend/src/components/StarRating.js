import React, { useState } from 'react';
import './StarRating.css';

function StarRating({ value = 0, onChange, readonly = false, max = 10 }) {
  const [hoverValue, setHoverValue] = useState(0);

  const handleClick = (rating) => {
    if (!readonly && onChange) {
      onChange(rating);
    }
  };

  const handleMouseMove = (e, starIndex) => {
    if (readonly) return;
    const rect = e.target.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const isHalf = x < rect.width / 2;
    setHoverValue(starIndex * 2 - (isHalf ? 1 : 0));
  };

  const displayValue = hoverValue || value;
  const fullStars = Math.floor(displayValue / 2);
  const hasHalf = displayValue % 2 === 1;

  return (
    <div className="star-rating">
      <div className="stars" onMouseLeave={() => setHoverValue(0)}>
        {[1, 2, 3, 4, 5].map((star) => {
          const isFull = star <= fullStars;
          const isHalf = star === fullStars + 1 && hasHalf;
          return (
            <span
              key={star}
              className={`star ${isFull ? 'filled' : ''} ${isHalf ? 'half' : ''}`}
              onClick={() => handleClick(star * 2)}
              onMouseMove={(e) => handleMouseMove(e, star)}
              style={{ cursor: readonly ? 'default' : 'pointer' }}
            >
              {isFull ? '★' : isHalf ? '★' : '☆'}
            </span>
          );
        })}
      </div>
      <div className="rating-value">
        {displayValue} <span>/ {max}</span>
      </div>
    </div>
  );
}

export default StarRating;

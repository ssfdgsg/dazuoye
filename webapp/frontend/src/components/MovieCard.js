import React from 'react';
import { useNavigate } from 'react-router-dom';
import './MovieCard.css';

function MovieCard({ movie, showSimilarity = false }) {
  const navigate = useNavigate();

  const handleClick = () => {
    navigate(`/movie/${movie.id}`);
  };

  const posterUrl = movie.poster?.startsWith('http')
    ? movie.poster
    : `/${movie.poster || 'static/img/default.webp'}`;

  return (
    <div className="movie-card" onClick={handleClick}>
      <div className="movie-card-poster">
        <img
          src={posterUrl}
          alt={movie.title}
          onError={(e) => { e.target.src = '/static/img/default.webp'; }}
        />
        {movie.rating && (
          <span className="movie-card-rating">
            ⭐ {movie.rating.toFixed(1)}
          </span>
        )}
      </div>
      <div className="movie-card-info">
        <h3 className="movie-card-title" title={movie.title}>{movie.title}</h3>
        <div className="movie-card-meta">
          {movie.release_date && (
            <span className="movie-card-year">
              {new Date(movie.release_date).getFullYear()}
            </span>
          )}
          {showSimilarity && movie.similarity && (
            <span className="movie-card-similarity">
              相似度 {(movie.similarity * 100).toFixed(0)}%
            </span>
          )}
        </div>
      </div>
    </div>
  );
}

export function MovieCardSkeleton() {
  return (
    <div className="movie-card-skeleton">
      <div className="skeleton-poster" />
      <div className="skeleton-info">
        <div className="skeleton-title" />
        <div className="skeleton-meta" />
      </div>
    </div>
  );
}

export default MovieCard;

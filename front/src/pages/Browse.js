import React, { useState, useEffect } from 'react';
import MovieCard, { MovieCardSkeleton } from '../components/MovieCard';
import { getMoviesByGenre } from '../services/api';
import './Browse.css';

const GENRES = [
  { key: 'all', label: '全部', icon: '🎬', color: '#6366f1' },
  { key: 'Action', label: '动作', icon: '💥', color: '#ef4444' },
  { key: 'Comedy', label: '喜剧', icon: '😂', color: '#f59e0b' },
  { key: 'Drama', label: '剧情', icon: '🎭', color: '#8b5cf6' },
  { key: 'Romance', label: '爱情', icon: '💕', color: '#ec4899' },
  { key: 'Science Fiction', label: '科幻', icon: '🚀', color: '#06b6d4' },
  { key: 'Horror', label: '恐怖', icon: '👻', color: '#6b7280' },
  { key: 'Animation', label: '动画', icon: '🎨', color: '#14b8a6' },
  { key: 'Thriller', label: '惊悚', icon: '😱', color: '#dc2626' },
  { key: 'Adventure', label: '冒险', icon: '🗺️', color: '#10b981' },
  { key: 'Fantasy', label: '奇幻', icon: '🧙', color: '#a855f7' },
  { key: 'Crime', label: '犯罪', icon: '🔪', color: '#64748b' },
];

function Browse() {
  const [activeGenre, setActiveGenre] = useState('all');
  const [movies, setMovies] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadMovies(activeGenre);
  }, [activeGenre]);

  const loadMovies = async (genre) => {
    setLoading(true);
    try {
      const data = await getMoviesByGenre(genre, 24);
      setMovies(data.movies || []);
    } catch (err) {
      console.error('Failed to load movies:', err);
    } finally {
      setLoading(false);
    }
  };

  const activeGenreData = GENRES.find(g => g.key === activeGenre);

  return (
    <div className="browse container fade-in">
      <div className="browse-header">
        <div className="header-content">
          <h1 className="browse-title">🎬 电影类型库</h1>
          <p className="browse-subtitle">探索你喜欢的电影类型，发现精彩作品</p>
        </div>
      </div>

      <div className="genre-cloud-section">
        <h2 className="section-title">选择类型</h2>
        <div className="genre-cloud">
          {GENRES.map((genre) => {
            const isActive = activeGenre === genre.key;
            return (
              <button
                key={genre.key}
                className={`genre-tag ${isActive ? 'active' : ''}`}
                onClick={() => setActiveGenre(genre.key)}
                style={{
                  '--tag-color': genre.color,
                  '--tag-size': isActive ? '1.2' : '1',
                }}
              >
                <span className="tag-icon">{genre.icon}</span>
                <span className="tag-label">{genre.label}</span>
              </button>
            );
          })}
        </div>
      </div>

      <div className="browse-content">
        <div className="content-header">
          <div className="active-genre-badge" style={{ backgroundColor: activeGenreData?.color }}>
            <span className="badge-icon">{activeGenreData?.icon}</span>
            <span className="badge-text">{activeGenreData?.label}</span>
          </div>
          <span className="movie-count">{movies.length} 部电影</span>
        </div>

        {loading ? (
          <div className="movie-grid">
            {[...Array(12)].map((_, i) => <MovieCardSkeleton key={i} />)}
          </div>
        ) : movies.length > 0 ? (
          <div className="movie-grid">
            {movies.map((movie) => (
              <MovieCard key={movie.id} movie={movie} />
            ))}
          </div>
        ) : (
          <div className="empty-state">
            <div className="empty-state-icon">📭</div>
            <p>该类型暂无电影</p>
          </div>
        )}
      </div>
    </div>
  );
}

export default Browse;

import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { getRankings, getGenres } from '../services/api';
import './Rankings.css';

const RANK_TYPES = [
  { key: 'rating', label: '评分榜', icon: '⭐' },
  { key: 'popularity', label: '热度榜', icon: '🔥' },
  { key: 'new', label: '新片榜', icon: '🆕' },
  { key: 'boxoffice', label: '票房榜', icon: '💰' },
];

const GENRE_OPTIONS = [
  { key: 'all', label: '全部类型' },
  { key: 'Action', label: '动作' },
  { key: 'Comedy', label: '喜剧' },
  { key: 'Drama', label: '剧情' },
  { key: 'Science Fiction', label: '科幻' },
  { key: 'Romance', label: '爱情' },
  { key: 'Thriller', label: '惊悚' },
  { key: 'Horror', label: '恐怖' },
  { key: 'Animation', label: '动画' },
];

function Rankings() {
  const navigate = useNavigate();
  const [rankType, setRankType] = useState('rating');
  const [genre, setGenre] = useState('all');
  const [yearFrom, setYearFrom] = useState('');
  const [yearTo, setYearTo] = useState('');
  const [movies, setMovies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [hasMore, setHasMore] = useState(true);
  const [showFilters, setShowFilters] = useState(false);

  useEffect(() => {
    loadRankings(true);
  }, [rankType, genre, yearFrom, yearTo]);

  const loadRankings = async (reset = false) => {
    setLoading(true);
    try {
      const data = await getRankings(rankType, 50, 0, {
        genre,
        yearFrom,
        yearTo,
      });
      setMovies(data || []);
      setHasMore(false);
    } catch (err) {
      console.error('Failed to load rankings:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleMovieClick = (id) => {
    navigate(`/movie/${id}`);
  };

  const clearFilters = () => {
    setGenre('all');
    setYearFrom('');
    setYearTo('');
  };

  const hasActiveFilters = genre !== 'all' || yearFrom || yearTo;

  return (
    <div className="rankings container fade-in">
      <div className="rankings-header">
        <h1 className="rankings-title">🏆 电影排行榜</h1>
        <div className="sort-tabs">
          {RANK_TYPES.map((opt) => (
            <button
              key={opt.key}
              className={`sort-tab ${rankType === opt.key ? 'active' : ''}`}
              onClick={() => setRankType(opt.key)}
            >
              {opt.icon} {opt.label}
            </button>
          ))}
        </div>
      </div>

      <div className="filter-section">
        <button
          className={`filter-toggle ${showFilters ? 'active' : ''}`}
          onClick={() => setShowFilters(!showFilters)}
        >
          🎛️ 筛选 {hasActiveFilters && <span className="filter-badge">•</span>}
        </button>
        {showFilters && (
          <div className="filter-panel">
            <div className="filter-group">
              <label>类型</label>
              <select value={genre} onChange={(e) => setGenre(e.target.value)}>
                {GENRE_OPTIONS.map((g) => (
                  <option key={g.key} value={g.key}>{g.label}</option>
                ))}
              </select>
            </div>
            <div className="filter-group">
              <label>年份</label>
              <div className="year-range">
                <input
                  type="number"
                  placeholder="从"
                  value={yearFrom}
                  onChange={(e) => setYearFrom(e.target.value)}
                  min="1900"
                  max="2025"
                />
                <span>-</span>
                <input
                  type="number"
                  placeholder="到"
                  value={yearTo}
                  onChange={(e) => setYearTo(e.target.value)}
                  min="1900"
                  max="2025"
                />
              </div>
            </div>
            {hasActiveFilters && (
              <button className="clear-filters" onClick={clearFilters}>
                清除筛选
              </button>
            )}
          </div>
        )}
      </div>

      <div className="rankings-list">
        {movies.map((movie, index) => {
          const posterUrl = movie.poster?.startsWith('http')
            ? movie.poster
            : `/${movie.poster || 'static/img/default.webp'}`;
          return (
            <div
              key={movie.id}
              className="ranking-item"
              onClick={() => handleMovieClick(movie.id)}
            >
              <div className={`rank-badge ${index < 3 ? `top-${index + 1}` : ''}`}>
                {movie.rank || index + 1}
              </div>
              <div className="ranking-poster">
                <img src={posterUrl} alt={movie.title} onError={(e) => { e.target.src = '/static/img/default.webp'; }} />
              </div>
              <div className="ranking-info">
                <h3 className="ranking-movie-title">{movie.title}</h3>
                <div className="ranking-meta">
                  <span className="ranking-rating">⭐ {movie.rating?.toFixed(1) || 'N/A'}</span>
                  {movie.vote_count && <span className="ranking-votes">{movie.vote_count} 人评价</span>}
                  {rankType === 'boxoffice' && movie.revenue && (
                    <span className="ranking-revenue">💵 {movie.revenue}</span>
                  )}
                  {rankType === 'new' && movie.release_date && (
                    <span className="ranking-date">📅 {movie.release_date}</span>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {loading && (
        <div className="loading-more">
          <div className="spinner" />
        </div>
      )}
    </div>
  );
}

export default Rankings;

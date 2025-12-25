import React, { useState, useEffect } from 'react';
import MovieCard, { MovieCardSkeleton } from '../components/MovieCard';
import { getMoviesByGenre } from '../services/api';
import './Browse.css';

const GENRES = [
  { key: 'all', label: '全部', icon: '🎬' },
  { key: 'Action', label: '动作', icon: '💥' },
  { key: 'Comedy', label: '喜剧', icon: '😂' },
  { key: 'Drama', label: '剧情', icon: '🎭' },
  { key: 'Romance', label: '爱情', icon: '💕' },
  { key: 'Science Fiction', label: '科幻', icon: '🚀' },
  { key: 'Horror', label: '恐怖', icon: '👻' },
  { key: 'Animation', label: '动画', icon: '🎨' },
  { key: 'Thriller', label: '惊悚', icon: '😱' },
  { key: 'Adventure', label: '冒险', icon: '🗺️' },
  { key: 'Fantasy', label: '奇幻', icon: '🧙' },
  { key: 'Crime', label: '犯罪', icon: '🔪' },
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

  return (
    <div className="browse container">
      <div className="browse-header">
        <h1 className="browse-title">📂 按类型浏览</h1>
        <p className="browse-subtitle">选择你喜欢的电影类型</p>
      </div>

      <div className="genre-tabs">
        {GENRES.map((genre) => (
          <button
            key={genre.key}
            className={`genre-tab ${activeGenre === genre.key ? 'active' : ''}`}
            onClick={() => setActiveGenre(genre.key)}
          >
            {genre.icon} {genre.label}
          </button>
        ))}
      </div>

      <div className="browse-content">
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

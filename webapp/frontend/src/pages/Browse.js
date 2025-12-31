import React, { useState, useEffect } from 'react';
import MovieCard, { MovieCardSkeleton } from '../components/MovieCard';
import { getMoviesByGenre } from '../services/api';
import './Browse.css';

const GENRES = [
  { key: 'all', label: '全部' },
  { key: 'Action', label: '动作' },
  { key: 'Comedy', label: '喜剧' },
  { key: 'Drama', label: '剧情' },
  { key: 'Romance', label: '爱情' },
  { key: 'Science Fiction', label: '科幻' },
  { key: 'Horror', label: '恐怖' },
  { key: 'Animation', label: '动画' },
  { key: 'Thriller', label: '惊悚' },
  { key: 'Adventure', label: '冒险' },
  { key: 'Fantasy', label: '奇幻' },
  { key: 'Crime', label: '犯罪' },
  { key: 'War', label: '战争' },
  { key: 'Documentary', label: '纪录' },
  { key: 'History', label: '历史' },
  { key: 'Mystery', label: '悬疑' },
  { key: 'Family', label: '家庭' },
  { key: 'Music', label: '音乐' },
  { key: 'Western', label: '西部' },
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
    <div className="browse container fade-in">
      <div className="filter-bar">
        <div className="filter-row">
          <span className="filter-label">按类型:</span>
          <div className="filter-options">
            {GENRES.map((genre) => (
              <span
                key={genre.key}
                className={`filter-item ${activeGenre === genre.key ? 'active' : ''}`}
                onClick={() => setActiveGenre(genre.key)}
              >
                {genre.label}
              </span>
            ))}
          </div>
        </div>
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
            <p>该类型暂无电影</p>
          </div>
        )}
      </div>
    </div>
  );
}

export default Browse;

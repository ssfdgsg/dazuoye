import React, { useState, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import MovieCard, { MovieCardSkeleton } from '../components/MovieCard';
import { searchMovies } from '../services/api';
import './Search.css';

function Search() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const query = searchParams.get('q') || '';
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [searchInput, setSearchInput] = useState(query);

  useEffect(() => {
    if (query) {
      performSearch(query);
    }
  }, [query]);

  const performSearch = async (q) => {
    setLoading(true);
    try {
      const data = await searchMovies(q);
      setResults(data.results || []);
    } catch (err) {
      console.error('Search failed:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = (e) => {
    e.preventDefault();
    if (searchInput.trim()) {
      navigate(`/search?q=${encodeURIComponent(searchInput.trim())}`);
    }
  };

  return (
    <div className="search-page container fade-in">
      <form className="search-form-large" onSubmit={handleSearch}>
        <input
          type="text"
          placeholder="搜索电影、导演或演员..."
          value={searchInput}
          onChange={(e) => setSearchInput(e.target.value)}
        />
        <button type="submit">🔍 搜索</button>
      </form>

      {query && (
        <div className="search-results">
          <div className="search-header">
            <h2 className="search-title">
              搜索结果：<span className="search-query">"{query}"</span>
            </h2>
            <span className="search-count">找到 {results.length} 部电影</span>
          </div>

          {loading ? (
            <div className="movie-grid">
              {[...Array(8)].map((_, i) => <MovieCardSkeleton key={i} />)}
            </div>
          ) : results.length > 0 ? (
            <div className="movie-grid">
              {results.map((movie) => (
                <MovieCard key={movie.id} movie={movie} />
              ))}
            </div>
          ) : (
            <div className="no-results">
              <div className="no-results-icon">🔍</div>
              <h3>未找到相关电影</h3>
              <p>试试其他关键词吧</p>
            </div>
          )}
        </div>
      )}

      {!query && (
        <div className="search-empty">
          <div className="search-empty-icon">🎬</div>
          <h2>搜索你喜欢的电影</h2>
          <p>输入电影名称、导演或演员开始搜索</p>
        </div>
      )}
    </div>
  );
}

export default Search;

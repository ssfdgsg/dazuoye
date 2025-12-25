import { useState, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { getMovie, searchMovies } from '../services/api';
import './Compare.css';

function Compare() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [movies, setMovies] = useState([null, null, null]);
  const [loading, setLoading] = useState([false, false, false]);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [searching, setSearching] = useState(false);
  const [activeSlot, setActiveSlot] = useState(null);

  // 从 URL 加载电影
  useEffect(() => {
    const ids = searchParams.get('ids')?.split(',').filter(Boolean) || [];
    ids.slice(0, 3).forEach((id, index) => {
      loadMovie(parseInt(id), index);
    });
  }, []);

  const loadMovie = async (movieId, slot) => {
    const newLoading = [...loading];
    newLoading[slot] = true;
    setLoading(newLoading);
    try {
      const data = await getMovie(movieId);
      const newMovies = [...movies];
      newMovies[slot] = data;
      setMovies(newMovies);
      updateUrl(newMovies);
    } catch (err) {
      console.error('Failed to load movie:', err);
    } finally {
      const finalLoading = [...loading];
      finalLoading[slot] = false;
      setLoading(finalLoading);
    }
  };

  const updateUrl = (movieList) => {
    const ids = movieList.filter(Boolean).map(m => m.id).join(',');
    if (ids) {
      navigate(`/compare?ids=${ids}`, { replace: true });
    }
  };

  const handleSearch = async (query) => {
    setSearchQuery(query);
    if (query.length < 2) {
      setSearchResults([]);
      return;
    }
    setSearching(true);
    try {
      const data = await searchMovies(query, 8);
      // API 返回格式是 { query, total, results }
      setSearchResults(data.results || []);
    } catch (err) {
      console.error('Search failed:', err);
      setSearchResults([]);
    } finally {
      setSearching(false);
    }
  };

  const selectMovie = (movie) => {
    if (activeSlot === null) return;
    const newMovies = [...movies];
    newMovies[activeSlot] = movie;
    setMovies(newMovies);
    updateUrl(newMovies);
    setActiveSlot(null);
    setSearchQuery('');
    setSearchResults([]);
  };

  const removeMovie = (slot) => {
    const newMovies = [...movies];
    newMovies[slot] = null;
    setMovies(newMovies);
    updateUrl(newMovies);
  };

  const clearAll = () => {
    setMovies([null, null, null]);
    navigate('/compare', { replace: true });
  };

  const validMovies = movies.filter(Boolean);
  const getPosterUrl = (movie) => movie?.poster?.startsWith('http') 
    ? movie.poster 
    : `/${movie?.poster || 'static/img/default.webp'}`;

  // 对比数据项
  const compareItems = [
    { label: '评分', key: 'rating', format: (v) => v?.toFixed(1) || 'N/A', icon: '⭐' },
    { label: '评价人数', key: 'vote_count', format: (v) => v?.toLocaleString() || 'N/A', icon: '👥' },
    { label: '上映年份', key: 'release_date', format: (v) => v ? new Date(v).getFullYear() : 'N/A', icon: '📅' },
    { label: '时长', key: 'runtime', format: (v) => v ? `${v} 分钟` : 'N/A', icon: '⏱️' },
    { label: '预算', key: 'budget', format: (v) => v > 0 ? `$${v}M` : 'N/A', icon: '💰' },
    { label: '票房', key: 'revenue', format: (v) => v && v !== '0' ? v : 'N/A', icon: '📈' },
  ];

  const getHighlight = (key, value, allValues) => {
    const nums = allValues.map(v => {
      if (key === 'release_date') return v ? new Date(v).getFullYear() : 0;
      if (key === 'revenue') return parseFloat(String(v).replace(/[^0-9.]/g, '')) || 0;
      return parseFloat(v) || 0;
    }).filter(n => n > 0);
    if (nums.length < 2) return '';
    const max = Math.max(...nums);
    const currentNum = key === 'release_date' 
      ? (value ? new Date(value).getFullYear() : 0)
      : key === 'revenue' 
        ? (parseFloat(String(value).replace(/[^0-9.]/g, '')) || 0)
        : (parseFloat(value) || 0);
    return currentNum === max && currentNum > 0 ? 'highlight' : '';
  };

  return (
    <div className="compare-page container fade-in">
      <div className="compare-header">
        <h1>🎬 电影对比</h1>
        <p>选择 2-3 部电影进行对比分析</p>
        {validMovies.length > 0 && (
          <button className="clear-btn" onClick={clearAll}>清空全部</button>
        )}
      </div>

      {/* 电影选择卡片 */}
      <div className="compare-slots">
        {[0, 1, 2].map((slot) => (
          <div key={slot} className={`compare-slot ${movies[slot] ? 'filled' : ''} ${activeSlot === slot ? 'active' : ''}`}>
            {loading[slot] ? (
              <div className="slot-loading"><div className="spinner"></div></div>
            ) : movies[slot] ? (
              <div className="slot-movie">
                <button className="remove-btn" onClick={() => removeMovie(slot)}>✕</button>
                <img src={getPosterUrl(movies[slot])} alt={movies[slot].title} 
                  onError={(e) => { e.target.src = '/static/img/default.webp'; }} />
                <h3>{movies[slot].title}</h3>
                <div className="slot-genres">
                  {movies[slot].genres?.slice(0, 2).map((g, i) => (
                    <span key={i} className="genre-tag">{g}</span>
                  ))}
                </div>
              </div>
            ) : (
              <button className="add-movie-btn" onClick={() => setActiveSlot(slot)}>
                <span className="add-icon">+</span>
                <span>添加电影</span>
              </button>
            )}
          </div>
        ))}
      </div>

      {/* 搜索面板 */}
      {activeSlot !== null && (
        <div className="search-panel">
          <div className="search-header">
            <h3>搜索电影</h3>
            <button className="close-search" onClick={() => { setActiveSlot(null); setSearchResults([]); }}>✕</button>
          </div>
          <input
            type="text"
            placeholder="输入电影名称..."
            value={searchQuery}
            onChange={(e) => handleSearch(e.target.value)}
            autoFocus
          />
          <div className="search-results">
            {searching ? (
              <div className="searching">搜索中...</div>
            ) : searchResults.length > 0 ? (
              searchResults.map((movie) => (
                <div key={movie.id} className="search-item" onClick={() => selectMovie(movie)}>
                  <img src={getPosterUrl(movie)} alt={movie.title}
                    onError={(e) => { e.target.src = '/static/img/default.webp'; }} />
                  <div className="search-item-info">
                    <span className="search-item-title">{movie.title}</span>
                    <span className="search-item-year">
                      {movie.release_date ? new Date(movie.release_date).getFullYear() : ''}
                    </span>
                  </div>
                </div>
              ))
            ) : searchQuery.length >= 2 ? (
              <div className="no-results">未找到相关电影</div>
            ) : null}
          </div>
        </div>
      )}

      {/* 对比表格 */}
      {validMovies.length >= 2 && (
        <div className="compare-table">
          <h2>📊 数据对比</h2>
          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>对比项</th>
                  {validMovies.map((m) => <th key={m.id}>{m.title}</th>)}
                </tr>
              </thead>
              <tbody>
                {compareItems.map((item) => (
                  <tr key={item.key}>
                    <td className="item-label">{item.icon} {item.label}</td>
                    {validMovies.map((m) => (
                      <td key={m.id} className={getHighlight(item.key, m[item.key], validMovies.map(v => v[item.key]))}>
                        {item.format(m[item.key])}
                      </td>
                    ))}
                  </tr>
                ))}
                <tr>
                  <td className="item-label">🎭 类型</td>
                  {validMovies.map((m) => (
                    <td key={m.id}>{m.genres?.join(' / ') || 'N/A'}</td>
                  ))}
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      )}

      {validMovies.length < 2 && (
        <div className="compare-hint">
          <p>💡 请至少选择 2 部电影开始对比</p>
        </div>
      )}
    </div>
  );
}

export default Compare;

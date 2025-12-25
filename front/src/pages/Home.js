import React, { useState, useEffect } from 'react';
import MovieCard, { MovieCardSkeleton } from '../components/MovieCard';
import { getMoviesByGenre, getRecommendations, getALSTask } from '../services/api';
import { useAuth } from '../context/AuthContext';
import './Home.css';

const GENRES = [
  { key: 'all', label: '全部', icon: '🎬' },
  { key: 'Action', label: '动作', icon: '💥' },
  { key: 'Comedy', label: '喜剧', icon: '😂' },
  { key: 'Drama', label: '剧情', icon: '🎭' },
  { key: 'Romance', label: '爱情', icon: '💕' },
  { key: 'Science Fiction', label: '科幻', icon: '🚀' },
  { key: 'Horror', label: '恐怖', icon: '👻' },
  { key: 'Animation', label: '动画', icon: '🎨' },
];

function Home() {
  const { user } = useAuth();
  const [activeGenre, setActiveGenre] = useState('all');
  const [genreMovies, setGenreMovies] = useState([]);
  const [recommendations, setRecommendations] = useState([]);
  const [loadingGenre, setLoadingGenre] = useState(true);
  const [loadingRecs, setLoadingRecs] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [recMethod, setRecMethod] = useState('');
  const [alsTask, setAlsTask] = useState(null);

  useEffect(() => {
    loadGenreMovies(activeGenre);
  }, [activeGenre]);

  useEffect(() => {
    loadRecommendations();
  }, [user]);

  // 轮询 ALS 任务状态
  useEffect(() => {
    if (!user) return;
    let interval;
    const checkTask = async () => {
      try {
        const task = await getALSTask(user.userId);
        setAlsTask(task);
        if (task.status === 'done') {
          loadRecommendations();
          clearInterval(interval);
          setTimeout(() => setAlsTask(null), 3000);
        } else if (task.status === 'error') {
          clearInterval(interval);
          setTimeout(() => setAlsTask(null), 5000);
        }
      } catch {
        setAlsTask(null);
      }
    };
    checkTask();
    interval = setInterval(checkTask, 3000);
    return () => clearInterval(interval);
  }, [user]);

  const loadGenreMovies = async (genre) => {
    setLoadingGenre(true);
    try {
      const data = await getMoviesByGenre(genre, 12);
      setGenreMovies(data.movies || []);
    } catch (err) {
      console.error('Failed to load movies:', err);
    } finally {
      setLoadingGenre(false);
    }
  };

  const loadRecommendations = async (force = false) => {
    if (force) setRefreshing(true);
    else setLoadingRecs(true);
    try {
      const data = await getRecommendations(12, force);
      setRecommendations(data.movies || []);
      setRecMethod(data.method || '');
    } catch (err) {
      console.error('Failed to load recommendations:', err);
    } finally {
      setLoadingRecs(false);
      setRefreshing(false);
    }
  };

  return (
    <div className="home container">
      <section className="hero">
        <h1 className="hero-title">发现你的下一部最爱</h1>
        <p className="hero-subtitle">基于智能推荐算法，为你精选好电影</p>
      </section>

      <section className="section">
        <div className="section-header">
          <h2 className="section-title">
            <span className="section-title-icon">🎯</span>
            猜你喜欢
            {recMethod && (
              <span className={`rec-method-badge ${recMethod}`}>
                {recMethod === 'als' || recMethod === 'als_model' ? '🤖 AI推荐' : recMethod === 'random' ? '🎲 随机推荐' : '📊 热门推荐'}
              </span>
            )}
          </h2>
          <button
            className={`refresh-btn ${refreshing ? 'loading' : ''}`}
            onClick={() => loadRecommendations(true)}
            disabled={refreshing}
          >
            <span className="refresh-icon">🔄</span>
            {refreshing ? '刷新中...' : '换一批'}
          </button>
        </div>
        {alsTask && (alsTask.status === 'running' || alsTask.status === 'queued') && (
          <div className="als-progress">
            <div className="als-progress-info">
              <span className="als-progress-label">🔄 正在为你计算个性化推荐...</span>
              <span className="als-progress-percent">{alsTask.progress || 0}%</span>
            </div>
            <div className="als-progress-bar">
              <div className="als-progress-fill" style={{ width: `${alsTask.progress || 0}%` }} />
            </div>
            {alsTask.message && <p className="als-progress-msg">{alsTask.message}</p>}
          </div>
        )}
        {alsTask && alsTask.status === 'done' && (
          <div className="als-done-notice">✅ 推荐已更新！</div>
        )}
        {loadingRecs ? (
          <div className="movie-grid">
            {[...Array(6)].map((_, i) => <MovieCardSkeleton key={i} />)}
          </div>
        ) : recommendations.length > 0 ? (
          <div className="movie-grid">
            {recommendations.map((movie) => (
              <MovieCard key={movie.id} movie={movie} />
            ))}
          </div>
        ) : (
          <div className="empty-state">
            <div className="empty-state-icon">🎬</div>
            <p>暂无推荐，登录后获取个性化推荐</p>
          </div>
        )}
      </section>

      <section className="section">
        <div className="section-header">
          <h2 className="section-title">
            <span className="section-title-icon">📂</span>
            按类型浏览
          </h2>
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
        {loadingGenre ? (
          <div className="movie-grid">
            {[...Array(6)].map((_, i) => <MovieCardSkeleton key={i} />)}
          </div>
        ) : genreMovies.length > 0 ? (
          <div className="movie-grid">
            {genreMovies.map((movie) => (
              <MovieCard key={movie.id} movie={movie} />
            ))}
          </div>
        ) : (
          <div className="empty-state">
            <div className="empty-state-icon">📭</div>
            <p>该类型暂无电影</p>
          </div>
        )}
      </section>
    </div>
  );
}

export default Home;

import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import MovieCard, { MovieCardSkeleton } from '../components/MovieCard';
import { getUserCFRecommendations } from '../services/api';
import { useAuth } from '../context/AuthContext';
import './UserCF.css';

function UserCF() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [recommendations, setRecommendations] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [stats, setStats] = useState(null);

  // 登录后自动加载推荐
  useEffect(() => {
    if (user?.id) {
      loadRecommendations();
    }
  }, [user]);

  const loadRecommendations = async () => {
    if (!user?.id) {
      setError('请先登录');
      return;
    }

    setLoading(true);
    setError('');
    setRecommendations([]);
    setStats(null);

    try {
      const data = await getUserCFRecommendations(user.id, 12);
      
      if (data.error) {
        setError(data.error);
      } else if (data.recommendations && data.recommendations.length > 0) {
        const movies = data.recommendations.map(r => ({
          id: r.movie_id,
          title: r.title,
          genres: r.genre?.split(',') || [],
          rating: r.vote_average || 0,
          poster: r.poster || `/static/img/${r.movie_id}.webp`,
          prediction: r.predict_rating,
        }));
        setRecommendations(movies);
        setStats({
          method: data.method,
          similarUsers: data.similar_users_count,
          userId: data.user_id,
          message: data.message,
        });
      } else {
        setError(data.message || '暂无推荐结果，多评几部电影试试');
      }
    } catch (err) {
      setError(err.message || '获取推荐失败');
    } finally {
      setLoading(false);
    }
  };

  // 未登录状态
  if (!user) {
    return (
      <div className="usercf-page container fade-in">
        <div className="usercf-header">
          <h1>👥 其他人在看</h1>
          <p>看看和你品味相似的用户都在看什么电影</p>
        </div>
        <div className="usercf-empty">
          <div className="empty-icon">🔐</div>
          <p>登录后查看个性化推荐</p>
          <button className="login-btn-large" onClick={() => navigate('/login')}>
            立即登录
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="usercf-page container fade-in">
      <div className="usercf-header">
        <h1>👥 其他人在看</h1>
        <p>看看和你品味相似的用户都在看什么电影</p>
      </div>

      {error && (
        <div className="usercf-error">
          <span>⚠️</span> {error}
          <button className="retry-btn" onClick={loadRecommendations}>重试</button>
        </div>
      )}

      {stats && (
        <div className="usercf-stats">
          {stats.similarUsers && (
            <div className="stat-item">
              <span className="stat-label">相似用户</span>
              <span className="stat-value">{stats.similarUsers} 人</span>
            </div>
          )}
          <div className="stat-item">
            <span className="stat-label">推荐数量</span>
            <span className="stat-value">{recommendations.length} 部</span>
          </div>
          {stats.message && (
            <div className="stat-item wide">
              <span className="stat-value small">{stats.message}</span>
            </div>
          )}
        </div>
      )}

      {loading ? (
        <div className="movie-grid">
          {[...Array(6)].map((_, i) => <MovieCardSkeleton key={i} />)}
        </div>
      ) : recommendations.length > 0 ? (
        <>
          <div className="results-header">
            <h2 className="results-title">🎬 他们也喜欢这些电影</h2>
            <button className="refresh-btn" onClick={loadRecommendations}>🔄 换一批</button>
          </div>
          <div className="movie-grid">
            {recommendations.map((movie) => (
              <div key={movie.id} className="movie-card-wrapper">
                <MovieCard movie={movie} />
                {movie.prediction && (
                  <div className="prediction-badge">
                    预测 {movie.prediction.toFixed(1)} 分
                  </div>
                )}
              </div>
            ))}
          </div>
        </>
      ) : !error && !loading ? (
        <div className="usercf-empty">
          <div className="empty-icon">🎬</div>
          <p>正在加载推荐...</p>
        </div>
      ) : null}
    </div>
  );
}

export default UserCF;

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import MovieCard, { MovieCardSkeleton } from '../components/MovieCard';
import { getUserCFRecommendations } from '../services/api';
import { useAuth } from '../context/AuthContext';
import './UserCF.css';

function UserCF() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [userId, setUserId] = useState(user?.id?.toString() || '');
  const [recommendations, setRecommendations] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [stats, setStats] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!userId.trim()) {
      setError('请输入用户 ID');
      return;
    }

    setLoading(true);
    setError('');
    setRecommendations([]);
    setStats(null);

    try {
      const data = await getUserCFRecommendations(parseInt(userId), 12);
      
      if (data.error) {
        setError(data.error);
      } else if (data.recommendations && data.recommendations.length > 0) {
        // 转换数据格式以适配 MovieCard
        const movies = data.recommendations.map(r => ({
          id: r.movie_id,
          title: r.title,
          genres: r.genre?.split(',') || [],
          rating: r.vote_average || 0,
          poster: `img/${r.movie_id}.webp`,
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
        setError(data.message || '该用户暂无推荐结果，可能评分数据不足');
      }
    } catch (err) {
      setError(err.message || '获取推荐失败');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="usercf-page container fade-in">
      <div className="usercf-header">
        <h1>👥 其他人在看</h1>
        <p>看看和你品味相似的用户都在看什么电影</p>
      </div>

      <form className="usercf-form" onSubmit={handleSubmit}>
        <div className="form-row">
          <input
            type="number"
            placeholder="输入用户 ID（如：1, 2, 503...）"
            value={userId}
            onChange={(e) => setUserId(e.target.value)}
            min="1"
          />
          <button type="submit" disabled={loading}>
            {loading ? '查找中...' : '🔍 查看推荐'}
          </button>
        </div>
        {user && (
          <p className="form-hint">
            当前登录用户 ID: <strong>{user.id}</strong>
            <button type="button" className="use-my-id" onClick={() => setUserId(user.id.toString())}>
              使用我的 ID
            </button>
          </p>
        )}
      </form>

      {error && (
        <div className="usercf-error">
          <span>⚠️</span> {error}
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
          <h2 className="results-title">🎬 他们也喜欢这些电影</h2>
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
      ) : null}

      {!loading && !error && recommendations.length === 0 && (
        <div className="usercf-empty">
          <div className="empty-icon">🎬</div>
          <p>输入用户 ID，发现更多好电影</p>
        </div>
      )}
    </div>
  );
}

export default UserCF;

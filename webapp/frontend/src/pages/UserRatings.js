import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { getUserRatings } from '../services/api';
import './UserRatings.css';

function RatingPoster({ item }) {
  const [imgError, setImgError] = useState(false);
  const posterUrl = item.poster?.startsWith('http') || item.poster?.startsWith('/')
    ? item.poster
    : item.poster ? `/${item.poster}` : null;

  return (
    <div className="rating-poster">
      {posterUrl && !imgError ? (
        <img src={posterUrl} alt={item.title} onError={() => setImgError(true)} />
      ) : (
        <div className="rating-placeholder"><span>🎬</span></div>
      )}
    </div>
  );
}

function UserRatings() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [ratings, setRatings] = useState([]);
  const [stats, setStats] = useState({ total: 0, avg: 0 });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!user) {
      navigate('/login');
      return;
    }
    loadRatings();
  }, [user]);

  const loadRatings = async () => {
    try {
      const data = await getUserRatings(user.id);
      setRatings(data.ratings || []);
      setStats({ total: data.total_ratings || 0, avg: data.avg_rating || 0 });
    } catch (err) {
      console.error('Failed to load ratings:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleMovieClick = (id) => {
    navigate(`/movie/${id}`);
  };

  if (loading) {
    return (
      <div className="user-ratings container">
        <div className="loading-state">
          <div className="spinner" />
        </div>
      </div>
    );
  }

  return (
    <div className="user-ratings container fade-in">
      <div className="ratings-header">
        <h1 className="ratings-title">📊 我的评分记录</h1>
        <div className="ratings-stats">
          <div className="stat-item">
            <span className="stat-value">{stats.total}</span>
            <span className="stat-label">评分数</span>
          </div>
          <div className="stat-item">
            <span className="stat-value">{stats.avg.toFixed(1)}</span>
            <span className="stat-label">平均分</span>
          </div>
        </div>
      </div>

      {ratings.length > 0 ? (
        <div className="ratings-list">
          {ratings.map((item) => {
            return (
              <div
                key={item.movie_id}
                className="rating-item"
                onClick={() => handleMovieClick(item.movie_id)}
              >
                <RatingPoster item={item} />
                <div className="rating-info">
                  <h3 className="rating-movie-title">{item.title}</h3>
                  <div className="rating-meta">
                    {item.release_date && (
                      <span className="rating-year">{new Date(item.release_date).getFullYear()}</span>
                    )}
                    <span className="rating-time">
                      评分于 {new Date(item.rating_time).toLocaleDateString()}
                    </span>
                  </div>
                </div>
                <div className="rating-score">
                  <span className="score-star">⭐</span>
                  <span className="score-value">{item.rating}</span>
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <div className="empty-ratings">
          <div className="empty-icon">📝</div>
          <h3>还没有评分记录</h3>
          <p>去看看电影，留下你的评价吧</p>
          <button onClick={() => navigate('/')}>浏览电影</button>
        </div>
      )}
    </div>
  );
}

export default UserRatings;

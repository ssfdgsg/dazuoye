import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import MovieCard, { MovieCardSkeleton } from '../components/MovieCard';
import StarRating from '../components/StarRating';
import { getMovie, getSimilarMovies, rateMovie, getAIReview } from '../services/api';
import { useAuth } from '../context/AuthContext';
import './MovieDetail.css';

function MovieDetail() {
  const { id } = useParams();
  const { user } = useAuth();
  const navigate = useNavigate();
  const [movie, setMovie] = useState(null);
  const [similarMovies, setSimilarMovies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [rating, setRating] = useState(0);
  const [comment, setComment] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [rateSuccess, setRateSuccess] = useState(false);
  const [aiReview, setAiReview] = useState('');
  const [aiLoading, setAiLoading] = useState(false);
  const [aiError, setAiError] = useState('');

  useEffect(() => {
    loadMovie();
    loadSimilarMovies();
    setAiReview('');
    setAiError('');
  }, [id]);

  const loadAIReview = async () => {
    if (!movie || aiLoading) return;
    setAiLoading(true);
    setAiError('');
    try {
      const review = await getAIReview(movie);
      setAiReview(review);
    } catch (err) {
      setAiError('AI 评价生成失败，请稍后重试');
    } finally {
      setAiLoading(false);
    }
  };

  const loadMovie = async () => {
    setLoading(true);
    try {
      const data = await getMovie(id);
      setMovie(data);
    } catch (err) {
      console.error('Failed to load movie:', err);
    } finally {
      setLoading(false);
    }
  };

  const loadSimilarMovies = async () => {
    try {
      const data = await getSimilarMovies(id, 6);
      setSimilarMovies(data || []);
    } catch (err) {
      console.error('Failed to load similar movies:', err);
    }
  };

  const handleRate = async () => {
    if (!user) {
      navigate('/login');
      return;
    }
    if (rating === 0) return;

    setSubmitting(true);
    try {
      await rateMovie(id, rating, comment);
      setRateSuccess(true);
      setTimeout(() => setRateSuccess(false), 3000);
    } catch (err) {
      alert(err.message || '评分失败');
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="movie-detail container">
        <div className="detail-skeleton">
          <div className="skeleton-poster" />
          <div className="skeleton-content">
            <div className="skeleton-title" />
            <div className="skeleton-text" />
            <div className="skeleton-text short" />
          </div>
        </div>
      </div>
    );
  }

  if (!movie) {
    return (
      <div className="movie-detail container">
        <div className="not-found">
          <div className="not-found-icon">🎬</div>
          <h2>电影未找到</h2>
          <button onClick={() => navigate('/')}>返回首页</button>
        </div>
      </div>
    );
  }

  const posterUrl = movie.poster?.startsWith('http')
    ? movie.poster
    : `/${movie.poster || 'static/img/default.webp'}`;

  return (
    <div className="movie-detail container fade-in">
      <div className="detail-card">
        <div className="detail-poster">
          <img src={posterUrl} alt={movie.title} onError={(e) => { e.target.src = '/static/img/default.webp'; }} />
        </div>
        <div className="detail-content">
          <h1 className="detail-title">{movie.title}</h1>
          <div className="detail-rating">
            <span className="rating-star">⭐</span>
            <span className="rating-score">{movie.rating?.toFixed(1) || 'N/A'}</span>
            {movie.vote_count && <span className="rating-count">({movie.vote_count} 人评价)</span>}
          </div>
          <div className="detail-meta">
            {movie.release_date && (
              <span className="meta-item">📅 {new Date(movie.release_date).getFullYear()}</span>
            )}
            {movie.runtime && <span className="meta-item">⏱️ {movie.runtime} 分钟</span>}
            {movie.genres?.length > 0 && (
              <span className="meta-item">🎭 {movie.genres.join(' / ')}</span>
            )}
          </div>
          {movie.keywords?.length > 0 && (
            <div className="detail-keywords">
              {movie.keywords.slice(0, 6).map((kw, i) => (
                <span key={i} className="keyword-tag">{kw}</span>
              ))}
            </div>
          )}

          {/* 额外信息 */}
          <div className="detail-extra">
            {movie.budget > 0 && (
              <div className="extra-item">
                <span className="extra-label">💰 预算</span>
                <span className="extra-value">${movie.budget}M</span>
              </div>
            )}
            {movie.revenue && movie.revenue !== '0' && (
              <div className="extra-item">
                <span className="extra-label">📈 票房</span>
                <span className="extra-value">{movie.revenue}</span>
              </div>
            )}
            {movie.production_companies?.length > 0 && (
              <div className="extra-item full">
                <span className="extra-label">🏢 制作公司</span>
                <span className="extra-value">{movie.production_companies.slice(0, 3).join(', ')}</span>
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="ai-review-section">
        <h2 className="ai-review-title">🤖 AI 智能评价</h2>
        {aiReview ? (
          <div className="ai-review-content">
            <p>{aiReview}</p>
            <button className="ai-refresh-btn" onClick={loadAIReview} disabled={aiLoading}>
              {aiLoading ? '生成中...' : '🔄 重新生成'}
            </button>
          </div>
        ) : aiError ? (
          <div className="ai-review-error">
            <p>{aiError}</p>
            <button className="ai-generate-btn" onClick={loadAIReview} disabled={aiLoading}>
              重试
            </button>
          </div>
        ) : (
          <div className="ai-review-placeholder">
            <p>点击下方按钮，让 AI 为你分析这部电影</p>
            <button className="ai-generate-btn" onClick={loadAIReview} disabled={aiLoading}>
              {aiLoading ? (
                <>
                  <span className="ai-loading-spinner"></span>
                  AI 正在分析...
                </>
              ) : (
                '✨ 生成 AI 评价'
              )}
            </button>
          </div>
        )}
      </div>

      <div className="rate-section">
        <h2 className="rate-title">📝 我的评分</h2>
        <div className="rate-form">
          <StarRating value={rating} onChange={setRating} />
          <textarea
            className="rate-comment"
            placeholder="写下你的评论（可选）..."
            value={comment}
            onChange={(e) => setComment(e.target.value)}
          />
          <button
            className={`rate-btn ${rateSuccess ? 'success' : ''}`}
            onClick={handleRate}
            disabled={submitting || rating === 0}
          >
            {submitting ? '提交中...' : rateSuccess ? '✓ 评分成功' : '提交评分'}
          </button>
        </div>
      </div>

      {similarMovies.length > 0 && (
        <div className="similar-section">
          <h2 className="similar-title">🎯 相似电影推荐</h2>
          <div className="similar-grid">
            {similarMovies.map((m) => (
              <MovieCard key={m.id} movie={m} showSimilarity />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default MovieDetail;

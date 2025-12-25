const API_BASE = '/api';

async function request(url, options = {}) {
  const res = await fetch(`${API_BASE}${url}`, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || 'Request failed');
  return data;
}

// 认证
export const login = (username, password) =>
  request('/login', { method: 'POST', body: JSON.stringify({ username, password }) });

export const register = (username, password) =>
  request('/register', { method: 'POST', body: JSON.stringify({ username, password }) });

export const logout = () => request('/logout', { method: 'POST' });

export const getSession = () => request('/session');

// 电影
export const getMovie = (id) => request(`/movie/${id}`);

export const getMoviesByGenre = (genre = 'all', limit = 12) =>
  request(`/movies/by-genre?genre=${encodeURIComponent(genre)}&limit=${limit}`);

export const getRecommendations = (topN = 12, force = false) =>
  request(`/movies/recommendations?topN=${topN}${force ? '&force=1' : ''}`);

export const getSimilarMovies = (movieId, limit = 12) =>
  request(`/similar-movies/${movieId}?limit=${limit}`);

export const getGenres = () => request('/genres');

export const searchMovies = (query, limit = 50) =>
  request(`/search?q=${encodeURIComponent(query)}&limit=${limit}`);

export const getRankings = (type = 'rating', limit = 20, offset = 0, options = {}) => {
  const params = new URLSearchParams({
    type,
    limit: String(limit),
    offset: String(offset),
  });
  if (options.genre && options.genre !== 'all') params.append('genre', options.genre);
  if (options.yearFrom) params.append('year_from', options.yearFrom);
  if (options.yearTo) params.append('year_to', options.yearTo);
  return request(`/rankings?${params.toString()}`);
};

// 评分
export const rateMovie = (movieId, rating, comment = '') =>
  request(`/movie/${movieId}/rate`, { method: 'POST', body: JSON.stringify({ rating, comment }) });

export const getUserRatings = (userId) => request(`/user/${userId}/ratings`);

// ALS 状态
export const getALSStatus = () => request('/als/status');

export const getALSTask = (userId) => request(`/als/task/${userId}`);

export const getALSLogs = (userId) => request(`/als/logs/${userId}`);

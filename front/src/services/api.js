const API_BASE = '/api';

async function request(url, options = {}) {
  try {
    const res = await fetch(`${API_BASE}${url}`, {
      headers: { 'Content-Type': 'application/json', ...options.headers },
      ...options,
    });
    
    // 检查响应内容类型
    const contentType = res.headers.get('content-type');
    if (!contentType || !contentType.includes('application/json')) {
      if (!res.ok) {
        throw new Error(`请求失败: ${res.status} ${res.statusText}`);
      }
      // 非 JSON 响应但成功
      const text = await res.text();
      return { success: true, message: text };
    }
    
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || data.error || '请求失败');
    }
    return data;
  } catch (err) {
    // 网络错误或 JSON 解析错误
    if (err.name === 'SyntaxError') {
      throw new Error('服务器响应格式错误');
    }
    throw err;
  }
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

export const getUserCFRecommendations = (userId, topN = 10) =>
  request(`/user/${userId}/recommend-cf?topN=${topN}`);

export const getSimilarMovies = (movieId, limit = 12) =>
  request(`/similar-movies/${movieId}?limit=${limit}`);

export const getGenres = () => request('/genres');

export const searchMovies = (query, limit = 50) =>
  request(`/search?q=${encodeURIComponent(query)}&limit=${limit}`);

export const getRankings = (type = 'rating', limit = 20, offset = 0, options = {}) => {
  const params = new URLSearchParams({
    type,
    limit: String(limit),
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


// AI 评价
const AI_API_URL = 'http://157.230.37.18/proxy/gemini_openai';
const AI_API_KEY = 'sk-o2md1WVDQNYRXh4g4H62xHt2DlNc4XBUAWx8KiANSDx3YBer';

export const getAIReview = async (movie) => {
  const prompt = `请用中文为电影《${movie.title}》写一段简短的AI评价（100字左右）。
电影信息：
- 类型：${movie.genres?.join('、') || '未知'}
- 评分：${movie.rating || '未知'}
- 简介：${movie.overview || '暂无'}
请从剧情、演技、视觉效果等方面给出客观评价，语言简洁有力。`;

  const response = await fetch(`${AI_API_URL}/v1/chat/completions`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${AI_API_KEY}`,
    },
    body: JSON.stringify({
      model: 'gemini-2.5-pro',
      messages: [{ role: 'user', content: prompt }],
      max_tokens: 300,
      temperature: 0.7,
    }),
  });

  if (!response.ok) {
    throw new Error('AI 评价生成失败');
  }

  const data = await response.json();
  return data.choices?.[0]?.message?.content || '暂无AI评价';
};

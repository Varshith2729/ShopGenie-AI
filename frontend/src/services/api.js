import axios from 'axios';

const BASE_URL = import.meta.env.VITE_API_BASE_URL 
  ? `${import.meta.env.VITE_API_BASE_URL.replace(/\/$/, '')}/api` 
  : '/api';

const api = axios.create({
  baseURL: BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Attach JWT token to requests if present
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('shopfaq_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
}, (error) => Promise.reject(error));

// Response interceptor for session expiration
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 401) {
      // If unauthorized on admin routes, clear token
      if (window.location.pathname.startsWith('/admin')) {
        localStorage.removeItem('shopfaq_token');
        localStorage.removeItem('shopfaq_user');
        localStorage.removeItem('shopfaq_shop');
        window.location.href = '/login?session_expired=1';
      }
    }
    return Promise.reject(error);
  }
);

// Auth Service
export const authApi = {
  register: (payload) => api.post('/auth/register', payload),
  login: (payload) => api.post('/auth/login', payload),
  logout: () => api.post('/auth/logout'),
  me: () => api.get('/auth/me'),
};

// Dashboard Service
export const dashboardApi = {
  getStats: () => api.get('/dashboard/stats'),
  getRecentQuestions: () => api.get('/dashboard/recent-questions'),
};

// Knowledge Base Service
export const knowledgeApi = {
  list: (params) => api.get('/knowledge', { params }),
  create: (payload) => api.post('/knowledge', payload),
  update: (id, payload) => api.put(`/knowledge/${id}`, payload),
  delete: (id) => api.delete(`/knowledge/${id}`),
};

// Shop Service
export const shopApi = {
  getProfile: () => api.get('/shop/profile'),
  updateProfile: (payload) => api.put('/shop/profile', payload),
  getPublicLink: () => api.get('/shop/public-link'),
};

// Customer Questions Service
export const questionsApi = {
  list: (params) => api.get('/questions', { params }),
  get: (id) => api.get(`/questions/${id}`),
  answer: (id, answer, options = {}) => api.post(`/questions/${id}/answer`, { answer, ...options }),
  retryEmail: (id, force = false) => api.post(`/questions/${id}/retry-email`, { force }),
  sendFollowUp: (id, reply) => api.post(`/questions/${id}/follow-up`, { reply }),
};

// Rate Answers / Feedback Service
export const feedbackApi = {
  list: (params) => api.get('/feedback', { params }),
  listOwnerReplies: (params) => api.get('/feedback/owner-replies', { params }),
  submitGood: (id) => api.post(`/feedback/${id}/good`),
  submitBad: (id, reason, correctAnswer) => api.post(`/feedback/${id}/bad`, {
    reason,
    correct_answer: correctAnswer,
  }),
};

// Email Two-Way Sync Service
export const emailApi = {
  syncInbox: () => api.post('/email/sync'),
};

// Public Customer Chatbot Service
export const customerApi = {
  getShop: (slug) => api.get(`/public/shop/${slug}`),
  createSession: (slug, payload) => api.post(`/public/shop/${slug}/session`, payload),
  validateSession: (slug, token) => api.get(`/public/shop/${slug}/session/validate`, {
    headers: { 'X-Customer-Session': token }
  }),
  sendChat: (slug, token, message) => api.post(
    `/public/shop/${slug}/chat`,
    { message, session_token: token },
    { headers: { 'X-Customer-Session': token } }
  ),
  sendChatStream: async (slug, token, message, { onStart, onChunk, onDone, onError }, signal) => {
    const url = `${BASE_URL}/public/shop/${slug}/chat/stream`;
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Customer-Session': token,
      },
      body: JSON.stringify({ message, session_token: token }),
      signal,
    });

    if (!response.ok) {
      let errData;
      try {
        errData = await response.json();
      } catch (e) {
        errData = { message: `Request failed with status ${response.status}` };
      }
      const err = new Error(errData.message || 'Stream connection failed');
      err.response = { status: response.status, data: errData };
      throw err;
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder('utf-8');
    let buffer = '';

    try {
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        const lines = buffer.split('\n');
        buffer = lines.pop();

        let currentEvent = 'message';
        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed) {
            currentEvent = 'message';
            continue;
          }
          if (trimmed.startsWith('event:')) {
            currentEvent = trimmed.slice(6).trim();
          } else if (trimmed.startsWith('data:')) {
            const dataStr = trimmed.slice(5).trim();
            try {
              const data = JSON.parse(dataStr);
              if (currentEvent === 'start' && onStart) {
                onStart(data);
              } else if (currentEvent === 'chunk' && onChunk) {
                onChunk(data.chunk);
              } else if (currentEvent === 'done' && onDone) {
                onDone(data);
              } else if (currentEvent === 'error' && onError) {
                onError(data);
              } else if (currentEvent === 'message') {
                if (data.chunk && onChunk) onChunk(data.chunk);
                if (data.answer && onDone) onDone(data);
              }
            } catch (e) {
              console.error("Failed to parse SSE JSON:", e, dataStr);
            }
          }
        }
      }
    } finally {
      reader.releaseLock();
    }
  },
  submitOwnerFeedback: (slug, token, payload) => api.post(
    `/public/shop/${slug}/owner-feedback`,
    payload,
    { headers: { 'X-Customer-Session': token } }
  ),
};

export default api;


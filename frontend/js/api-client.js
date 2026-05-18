/* ══════════════════════════════════════
   API Client — fetch wrapper with retry & timeout
   ══════════════════════════════════════ */

const API_BASE = window.API_BASE_URL || 'http://127.0.0.1:8000';

const api = {
  async request(path, options = {}) {
    const url = `${API_BASE}${path}`;
    const config = {
      headers: { 'Content-Type': 'application/json', ...options.headers },
      ...options,
    };

    let lastError = null;
    for (let attempt = 0; attempt < 3; attempt++) {
      try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 30000);
        config.signal = controller.signal;

        const response = await fetch(url, config);
        clearTimeout(timeoutId);

        if (!response.ok) {
          const body = await response.json().catch(() => ({}));
          const msg = body.detail || `请求失败 (${response.status})`;
          throw new Error(msg);
        }

        return await response.json();
      } catch (err) {
        lastError = err;
        if (err.name === 'AbortError') {
          lastError = new Error('请求超时，请检查网络连接');
        }
        if (attempt < 2) {
          await new Promise(r => setTimeout(r, Math.pow(2, attempt) * 1000));
        }
      }
    }
    throw lastError || new Error('未知错误');
  },

  // Food
  recognizeFood(query) {
    return this.request('/api/v1/food/recognize', {
      method: 'POST',
      body: JSON.stringify({ query }),
    });
  },

  searchFood(keyword) {
    return this.request(`/api/v1/food/search?keyword=${encodeURIComponent(keyword)}`);
  },

  // Diet
  recordDiet(mealType, foodName, amountG) {
    return this.request('/api/v1/diet/record', {
      method: 'POST',
      body: JSON.stringify({ meal_type: mealType, food_name: foodName, amount_g: amountG }),
    });
  },

  getToday() {
    return this.request('/api/v1/diet/today');
  },

  getWeekly() {
    return this.request('/api/v1/diet/weekly');
  },

  deleteRecord(id) {
    return this.request(`/api/v1/diet/record/${id}`, { method: 'DELETE' });
  },

  // AI
  analyzeDiet() {
    return this.request('/api/v1/ai/analyze', { method: 'POST' });
  },

  scoreMeal(mealType, foods) {
    return this.request('/api/v1/ai/score', {
      method: 'POST',
      body: JSON.stringify({ meal_type: mealType, foods }),
    });
  },

  aiChat(message, userContext) {
    return this.request('/api/v1/ai/chat', {
      method: 'POST',
      body: JSON.stringify({ message, user_context: userContext }),
    });
  },

  // User profile
  getProfile() {
    return this.request('/api/v1/user/profile');
  },

  saveProfile(data) {
    return this.request('/api/v1/user/profile', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  health() {
    return this.request('/api/v1/health');
  },
};

/* ══════════════════════════════════════
   AI减脂营养师 — Application Logic
   ══════════════════════════════════════ */

(function () {
  'use strict';

  // ─── State ───────────────────────────
  const state = {
    page: 'onboarding',      // 'onboarding' | 'home'
    homeTab: 'record',       // 'record' | 'analysis' | 'ai'
    onboardingStep: 1,
    user: {
      height: 170,
      weight: 70,
      gender: 'male',
      goal: 'lose',
      targetWeight: 65,
      dailyCalorieTarget: 1800,
      macros: { protein: 135, carbs: 202, fat: 50 },
    },
    todayData: null,
    weeklyData: null,
    aiAnalysis: null,
    chatHistory: [],
    swipeStartX: null,
  };

  // ─── DOM refs ────────────────────────
  function $(id) { return document.getElementById(id); }
  function qs(sel, ctx) { return (ctx || document).querySelector(sel); }
  function qsa(sel, ctx) { return (ctx || document).querySelectorAll(sel); }

  // ─── Toast ──────────────────────────
  function toast(msg, type = '') {
    const t = $('toast');
    t.textContent = msg;
    t.className = 'toast show ' + type;
    clearTimeout(t._timeout);
    t._timeout = setTimeout(() => { t.className = 'toast hide'; }, 2500);
  }

  // ─── Page Navigation ────────────────
  function switchPage(page, navTab) {
    state.page = page;
    qsa('.page').forEach(p => p.classList.remove('active'));
    const pageEl = $('page-' + page);
    if (pageEl) pageEl.classList.add('active');

    qsa('.nav-item').forEach(n => {
      const np = n.dataset.page;
      let active = np === page;
      if (navTab && np === navTab) active = true;
      n.classList.toggle('active', active);
    });

    if (page === 'home' && state.homeTab === 'analysis') loadAnalysis();
  }

  function switchTab(tab) {
    state.homeTab = tab;
    qsa('.tab-btn').forEach(b => b.classList.toggle('active', b.dataset.tab === tab));
    qsa('.tab-content').forEach(c => c.classList.toggle('active', c.dataset.tab === tab));

    if (tab === 'analysis') loadAnalysis();
    if (tab === 'record') loadToday();
  }

  // ─── Onboarding ──────────────────────
  function initOnboarding() {
    // Step navigation
    $('btn-step-next').addEventListener('click', () => {
      const h = parseFloat($('input-height').value) || 170;
      const w = parseFloat($('input-weight').value) || 70;
      state.user.height = h;
      state.user.weight = w;

      // Determine gender selection
      const maleSelected = $('gender-male').classList.contains('selected');
      const femaleSelected = $('gender-female').classList.contains('selected');
      state.user.gender = maleSelected ? 'male' : femaleSelected ? 'female' : 'male';

      goToStep(2);
    });

    // Gender selector
    $('gender-male').addEventListener('click', () => {
      $('gender-male').classList.add('selected');
      $('gender-female').classList.remove('selected');
    });
    $('gender-female').addEventListener('click', () => {
      $('gender-female').classList.add('selected');
      $('gender-male').classList.remove('selected');
    });

    // Goal selector
    qsa('.goal-card').forEach(card => {
      card.addEventListener('click', () => {
        qsa('.goal-card').forEach(c => c.classList.remove('selected'));
        card.classList.add('selected');
        state.user.goal = card.dataset.goal;
        goToStep(3);
      });
    });

    // Start button
    $('btn-start').addEventListener('click', startJourney);
  }

  function goToStep(step) {
    state.onboardingStep = step;
    qsa('.step').forEach(s => s.classList.remove('active'));
    const stepEl = qs('.step[data-step="' + step + '"]');
    if (stepEl) stepEl.classList.add('active');

    if (step === 2) {
      // Set target weight based on goal
      if (state.user.goal === 'lose') state.user.targetWeight = state.user.weight - 10;
      else if (state.user.goal === 'gain') state.user.targetWeight = state.user.weight + 5;
      else state.user.targetWeight = state.user.weight;
    }

    if (step === 3) {
      calculateCalorieTarget();
    }
  }

  function calculateCalorieTarget() {
    const { height, weight, gender, goal } = state.user;

    // Mifflin-St Jeor BMR
    let bmr;
    if (gender === 'male') {
      bmr = 10 * weight + 6.25 * height - 5 * 25 + 5;
    } else {
      bmr = 10 * weight + 6.25 * height - 5 * 25 - 161;
    }

    // TDEE (moderate activity)
    let tdee = bmr * 1.55;

    // Adjust for goal
    let target;
    if (goal === 'lose') target = Math.round(tdee - 500);
    else if (goal === 'gain') target = Math.round(tdee + 300);
    else target = Math.round(tdee);

    // Round to nearest 50
    target = Math.round(target / 50) * 50;
    target = Math.max(1200, Math.min(3000, target));

    state.user.dailyCalorieTarget = target;
    state.user.macros = {
      protein: Math.round(target * 0.3 / 4),
      carbs: Math.round(target * 0.45 / 4),
      fat: Math.round(target * 0.25 / 9),
    };

    // Animate
    const el = $('calorie-target-display');
    el.textContent = '0';
    ChartUtils.animateNumber(el, target, 800);

    $('macro-protein').textContent = state.user.macros.protein;
    $('macro-carbs').textContent = state.user.macros.carbs;
    $('macro-fat').textContent = state.user.macros.fat;
  }

  async function startJourney() {
    // Ripple effect
    const btn = $('btn-start');
    const rect = btn.getBoundingClientRect();
    const cx = rect.left + rect.width / 2;
    const cy = rect.top + rect.height / 2;
    const overlay = $('ripple-overlay');

    const circle = document.createElement('div');
    circle.className = 'ripple-circle';
    circle.style.left = cx + 'px';
    circle.style.top = cy + 'px';
    circle.style.width = '20px';
    circle.style.height = '20px';
    overlay.appendChild(circle);

    // Save profile
    try {
      await api.saveProfile({
        height_cm: state.user.height,
        weight_kg: state.user.weight,
        target_weight_kg: state.user.targetWeight,
        daily_calorie_target: state.user.dailyCalorieTarget,
      });
    } catch (e) { /* ok */ }

    setTimeout(() => {
      overlay.innerHTML = '';
      switchPage('home', 'home');
      switchTab('record');
      loadToday();
      updateGreeting();
      updateProfileDisplay();
    }, 600);
  }

  // ─── Home Page ───────────────────────
  function updateGreeting() {
    const hour = new Date().getHours();
    let greeting = '早安';
    if (hour >= 12 && hour < 18) greeting = '午安';
    else if (hour >= 18) greeting = '晚安';

    const emoji = hour < 12 ? '🌤️' : hour < 18 ? '☀️' : '🌙';
    $('greeting-text').textContent = greeting + emoji;
    // Show first char of name or default
    $('avatar-letter').textContent = '我';
    $('greeting-name').textContent = '减脂用户';
  }

  function updateProfileDisplay() {
    $('profile-name-display').textContent = '减脂用户';
    $('profile-stats-display').textContent =
      `${state.user.height}cm · ${state.user.weight}kg · 目标${state.user.targetWeight}kg`;
    $('settings-target').textContent = state.user.dailyCalorieTarget;
    $('settings-height').textContent = state.user.height;
    $('settings-weight').textContent = state.user.weight;
    $('settings-target-wt').textContent = state.user.targetWeight;
  }

  async function loadToday() {
    try {
      const data = await api.getToday();
      state.todayData = data;
      renderToday(data);
      renderCalorieRing(data.total_calories, data.daily_target);
      updateSummaryBar(data);
    } catch (e) {
      // Show empty state
      $('meals-container').innerHTML =
        '<div class="text-center text-muted" style="padding:40px">还没有饮食记录<br>搜索食物开始记录吧</div>';
      renderCalorieRing(0, state.user.dailyCalorieTarget);
      updateSummaryBar(null);
    }
  }

  function renderToday(data) {
    const container = $('meals-container');
    if (!data || !data.meals || data.meals.length === 0) {
      container.innerHTML =
        '<div class="text-center text-muted" style="padding:40px">还没有饮食记录<br>搜索食物开始记录吧</div>';
      return;
    }

    container.innerHTML = data.meals.map(meal => `
      <div class="meal-group">
        <div class="meal-group-header">
          <span class="meal-group-title">${meal.meal_type}</span>
          <span class="meal-group-summary">${meal.subtotal_calories} 千卡</span>
        </div>
        ${meal.items.map(item => `
          <div class="food-item fly-in" data-id="${item.id}" data-meal="${meal.meal_type}">
            <div class="food-item-info" onclick="this.nextElementSibling.classList.toggle('show')">
              <div class="food-item-name">${item.food_name}</div>
              <div class="food-item-amount">${item.amount_g}g · 蛋白${item.protein_g}g 碳水${item.carbs_g}g 脂肪${item.fat_g}g</div>
            </div>
            <div class="food-detail" style="display:none">
              <span class="food-detail-item" style="color:#4CAF50">蛋白 ${item.protein_g}g</span>
              <span class="food-detail-item" style="color:#42A5F5">碳水 ${item.carbs_g}g</span>
              <span class="food-detail-item" style="color:#FFCA28">脂肪 ${item.fat_g}g</span>
            </div>
            <span class="food-item-cal">${item.calories}</span>
            <div class="food-item-delete" onclick="App.deleteRecord(${item.id})">🗑</div>
          </div>
        `).join('')}
      </div>
    `).join('');

    // Re-bind swipe for new items
    bindSwipeDelete();
  }

  function renderCalorieRing(consumed, target) {
    const remaining = Math.round(target - consumed);
    $('ring-remaining').textContent = remaining;
    $('ring-remaining').style.color = remaining < 0 ? '#FF5252' : '#4CAF50';

    ChartUtils.drawCalorieRing('calorie-ring-canvas', consumed, target, 110);

    // Update streak (mock: count days with records)
    if (consumed > 0) {
      $('streak-days').textContent = '1';
    }
  }

  function updateSummaryBar(data) {
    if (!data) {
      $('summary-cal').textContent = '0';
      $('summary-target').textContent = state.user.dailyCalorieTarget;
      $('summary-protein').textContent = '0';
      $('summary-carbs').textContent = '0';
      $('summary-fat').textContent = '0';
      $('summary-progress').style.width = '0%';
      $('summary-progress').classList.remove('over');
      return;
    }

    $('summary-cal').textContent = data.total_calories;
    $('summary-target').textContent = data.daily_target;
    $('summary-protein').textContent = data.total_protein_g;
    $('summary-carbs').textContent = data.total_carbs_g;
    $('summary-fat').textContent = data.total_fat_g;

    const pct = Math.min((data.total_calories / data.daily_target) * 100, 150);
    $('summary-progress').style.width = pct + '%';
    $('summary-progress').classList.toggle('over', data.total_calories > data.daily_target);

    // Color coding for surplus
    const calEl = $('summary-cal');
    if (data.total_calories > data.daily_target) {
      calEl.style.color = '#FF5252';
      if (!calEl.classList.contains('shake')) {
        calEl.classList.add('shake');
        setTimeout(() => calEl.classList.remove('shake'), 500);
      }
    } else {
      calEl.style.color = '#FFFFFF';
    }
  }

  function bindSwipeDelete() {
    qsa('.food-item').forEach(item => {
      let startX = 0, currentX = 0;
      item.addEventListener('touchstart', e => {
        startX = e.touches[0].clientX;
      });
      item.addEventListener('touchmove', e => {
        currentX = e.touches[0].clientX;
        const diff = startX - currentX;
        if (diff > 0 && diff < 80) {
          const deleteBtn = qs('.food-item-delete', item);
          if (deleteBtn) deleteBtn.style.transform = `translateX(${Math.max(0, 60 - diff)}px)`;
        }
      });
      item.addEventListener('touchend', () => {
        const diff = startX - currentX;
        const deleteBtn = qs('.food-item-delete', item);
        if (diff > 30 && deleteBtn) {
          deleteBtn.style.transform = 'translateX(0)';
          item.classList.add('swiped');
        } else if (deleteBtn) {
          deleteBtn.style.transform = 'translateX(60px)';
          item.classList.remove('swiped');
        }
      });
    });
  }

  window.App = {
    async deleteRecord(id) {
      try {
        await api.deleteRecord(id);
        toast('已删除');
        loadToday();
      } catch (e) {
        toast('删除失败: ' + e.message, 'error');
      }
    },
  };

  // ─── Food Search & Add ──────────────
  let searchTimer = null;
  function initSearch() {
    const input = $('search-food-input');
    const dropdown = $('search-dropdown');

    input.addEventListener('input', () => {
      clearTimeout(searchTimer);
      const keyword = input.value.trim();
      if (!keyword) {
        dropdown.classList.remove('show');
        return;
      }
      searchTimer = setTimeout(async () => {
        try {
          const results = await api.searchFood(keyword);
          renderSearchResults(results, keyword);
        } catch (e) {
          dropdown.innerHTML = `<div class="search-ai-hint">尝试AI识别"${keyword}"</div>`;
          dropdown.classList.add('show');
          // Click on AI hint
          qs('.search-ai-hint', dropdown).addEventListener('click', () => aiRecognize(keyword));
        }
      }, 300);
    });

    // Camera button (mock)
    $('btn-camera').addEventListener('click', () => {
      toast('拍照识别功能 — 请描述食物', '');
      input.focus();
    });
  }

  function renderSearchResults(results, keyword) {
    const dropdown = $('search-dropdown');
    if (!results || results.length === 0) {
      dropdown.innerHTML = `<div class="search-ai-hint">尝试AI识别"${keyword}"</div>`;
      dropdown.classList.add('show');
      qs('.search-ai-hint', dropdown).addEventListener('click', () => aiRecognize(keyword));
      return;
    }

    dropdown.innerHTML = results.map(r => `
      <div class="search-result-item" data-name="${r.food_name}" data-cat="${r.category}"
           data-cal="${r.calories_per_100g}" data-protein="${r.protein_per_100g}"
           data-carbs="${r.carbs_per_100g}" data-fat="${r.fat_per_100g}"
           data-portion="${r.typical_portion_g || 100}">
        <div>
          <div class="search-result-name">${highlightMatch(r.food_name, keyword)}</div>
          <div class="search-result-cat">${r.category}</div>
        </div>
        <div class="search-result-cal">${r.calories_per_100g}千卡/100g</div>
      </div>
    `).join('');

    dropdown.classList.add('show');

    // Bind click
    qsa('.search-result-item', dropdown).forEach(item => {
      item.addEventListener('click', () => {
        dropdown.classList.remove('show');
        $('search-food-input').value = '';
        showAddFoodModal(item.dataset);
      });
    });
  }

  function highlightMatch(text, keyword) {
    const idx = text.indexOf(keyword);
    if (idx === -1) return text;
    return text.substring(0, idx) +
      '<span style="color:#4CAF50">' + text.substring(idx, idx + keyword.length) + '</span>' +
      text.substring(idx + keyword.length);
  }

  async function aiRecognize(query) {
    try {
      toast('AI识别中...');
      const result = await api.recognizeFood(query);
      $('search-dropdown').classList.remove('show');
      $('search-food-input').value = '';
      showAddFoodModal({
        name: result.food_name,
        cat: result.category,
        cal: result.calories / result.amount_g * 100,
        protein: result.protein_g / result.amount_g * 100,
        carbs: result.carbs_g / result.amount_g * 100,
        fat: result.fat_g / result.amount_g * 100,
        portion: result.amount_g,
      });
      toast('已识别: ' + result.food_name);
    } catch (e) {
      toast('AI识别失败，请重试', 'error');
    }
  }

  // ─── Add Food Modal ──────────────────
  function showAddFoodModal(foodData) {
    const overlay = $('modal-overlay');
    const sheet = $('modal-sheet');
    $('modal-food-name').textContent = foodData.name;
    $('modal-food-cat').textContent = foodData.cat;

    let amount = parseFloat(foodData.portion) || 100;

    $('modal-amount-val').textContent = amount;

    // Stepper
    $('stepper-minus').onclick = () => {
      amount = Math.max(10, amount - 10);
      $('modal-amount-val').textContent = amount;
      updateModalNutrition(foodData, amount);
    };
    $('stepper-plus').onclick = () => {
      amount = Math.min(2000, amount + 10);
      $('modal-amount-val').textContent = amount;
      updateModalNutrition(foodData, amount);
    };

    updateModalNutrition(foodData, amount);

    // Meal type
    let mealType = '午餐';
    qsa('.meal-type-option').forEach(opt => {
      opt.classList.remove('selected');
      opt.onclick = () => {
        qsa('.meal-type-option').forEach(o => o.classList.remove('selected'));
        opt.classList.add('selected');
        mealType = opt.dataset.type;
      };
    });
    qs('.meal-type-option[data-type="午餐"]').classList.add('selected');

    overlay.classList.add('show');

    $('btn-confirm-add').onclick = async () => {
      try {
        const record = await api.recordDiet(mealType, foodData.name, amount);
        toast('已添加: ' + foodData.name);
        overlay.classList.remove('show');
        loadToday();
      } catch (e) {
        toast('添加失败: ' + e.message, 'error');
      }
    };

    $('btn-cancel-add').onclick = () => {
      overlay.classList.remove('show');
    };
  }

  function updateModalNutrition(foodData, amount) {
    const ratio = amount / 100;
    $('modal-nutrition').textContent =
      `热量${Math.round(foodData.cal * ratio)}千卡 · 蛋白${(foodData.protein * ratio).toFixed(1)}g · 碳水${(foodData.carbs * ratio).toFixed(1)}g · 脂肪${(foodData.fat * ratio).toFixed(1)}g`;
  }

  // ─── Analysis Tab ────────────────────
  async function loadAnalysis() {
    if (state.homeTab !== 'analysis') return;

    try {
      const [today, weekly, analysis] = await Promise.all([
        api.getToday(),
        api.getWeekly(),
        api.analyzeDiet().catch(() => null),
      ]);

      state.todayData = today;
      state.weeklyData = weekly;
      state.aiAnalysis = analysis;

      renderMacroChart(today);
      renderWeeklyChart(weekly);
      renderAIScore(analysis);
      renderSuggestions(analysis);
      renderTrendLine();
    } catch (e) {
      // Show fallback
      $('macro-chart-area').innerHTML =
        '<div class="text-center text-muted p-4">暂无数据</div>';
    }
  }

  function renderMacroChart(data) {
    if (!data) return;
    ChartUtils.drawMacroRings(
      'macro-ring-canvas',
      data.total_protein_g, data.protein_goal_g,
      data.total_carbs_g, data.carbs_goal_g,
      data.total_fat_g, data.fat_goal_g,
      200
    );

    const pctP = Math.round(data.total_protein_g / data.protein_goal_g * 100);
    const pctC = Math.round(data.total_carbs_g / data.carbs_goal_g * 100);
    const pctF = Math.round(data.total_fat_g / data.fat_goal_g * 100);

    const color = v => v > 100 ? '#FF5252' : v >= 80 ? '#4CAF50' : '#FF9800';

    $('macro-center-cal').textContent = data.total_calories;
    $('macro-center-target').textContent = '/' + data.daily_target;
    $('pct-protein').textContent = pctP + '%';
    $('pct-carbs').textContent = pctC + '%';
    $('pct-fat').textContent = pctF + '%';
    $('pct-protein').style.color = color(pctP);
    $('pct-carbs').style.color = color(pctC);
    $('pct-fat').style.color = color(pctF);
  }

  function renderWeeklyChart(data) {
    if (!data) return;
    ChartUtils.drawWeeklyChart(
      'weekly-chart-canvas',
      data.daily_calories,
      data.target_line,
      320, 160
    );
    $('weekly-avg').textContent = '日均 ' + data.avg_daily + ' 千卡';
  }

  function renderAIScore(analysis) {
    if (!analysis) {
      $('ai-score-display').textContent = '--';
      $('ai-score-comment').textContent = '暂无AI分析';
      return;
    }
    const score = analysis.score;
    const el = $('ai-score-display');
    el.textContent = score;
    if (score >= 9) el.style.color = '#4CAF50';
    else if (score >= 7) el.style.color = '#8BC34A';
    else if (score >= 5) el.style.color = '#FF9800';
    else el.style.color = '#FF5252';
    $('ai-score-comment').textContent = analysis.summary || '';
  }

  function renderSuggestions(analysis) {
    const container = $('suggestions-list');
    if (!analysis) {
      container.innerHTML = '<div class="text-center text-muted">记录饮食后可获得AI建议</div>';
      return;
    }

    const items = [];
    if (analysis.issues && analysis.issues.length) {
      analysis.issues.forEach(i => {
        items.push({ icon: '❌', text: i });
      });
    }
    if (analysis.suggestions && analysis.suggestions.length) {
      analysis.suggestions.forEach(s => {
        items.push({ icon: '✅', text: s });
      });
    }

    container.innerHTML = items.map(item => `
      <div class="suggestion-item">
        <span class="suggestion-icon">${item.icon}</span>
        <span class="suggestion-text">${item.text}</span>
      </div>
    `).join('');
  }

  function renderTrendLine() {
    // Mock 7-day scores for demo
    const scores = [7, 6, 8, 5, 9, 7, state.aiAnalysis ? state.aiAnalysis.score : 0];
    ChartUtils.drawTrendLine('trend-canvas', scores, 280, 100);

    const first = scores[0] || 0;
    const last = scores[scores.length - 1] || 0;
    const trend = $('trend-arrow');
    if (last > first) {
      trend.textContent = '↗️ 上升中';
      trend.style.color = '#4CAF50';
    } else if (last < first) {
      trend.textContent = '↘️ 下降中';
      trend.style.color = '#FF5252';
    } else {
      trend.textContent = '→ 持平';
      trend.style.color = '#FF9800';
    }
  }

  // ─── AI Chat Tab ─────────────────────
  function initChat() {
    $('btn-send').addEventListener('click', sendChatMessage);
    $('chat-input').addEventListener('keydown', e => {
      if (e.key === 'Enter') sendChatMessage();
    });
    $('chat-input').addEventListener('input', () => {
      const has = $('chat-input').value.trim().length > 0;
      $('btn-send').disabled = !has;
    });

    // Quick questions
    qsa('.quick-chip').forEach(chip => {
      chip.addEventListener('click', () => {
        sendChatMessage(chip.textContent);
      });
    });
  }

  async function sendChatMessage(text) {
    const input = $('chat-input');
    const message = text || input.value.trim();
    if (!message) return;

    // Add user bubble
    appendChatBubble(message, 'user');
    input.value = '';
    $('btn-send').disabled = true;

    // Show typing indicator
    const typingDiv = appendTypingIndicator();

    try {
      const userContext = `身高${state.user.height}，体重${state.user.weight}，目标体重${state.user.targetWeight}，日目标${state.user.dailyCalorieTarget}千卡`;
      const res = await api.aiChat(message, userContext);

      // Remove typing indicator
      typingDiv.remove();

      // Typewriter effect
      await typewriterReply(res.reply);
    } catch (e) {
      // Remove typing indicator
      typingDiv.remove();

      // ─── Offline fallback: use built-in nutrition knowledge base ───
      const userContext = `身高${state.user.height}，体重${state.user.weight}，目标体重${state.user.targetWeight}，日目标${state.user.dailyCalorieTarget}千卡`;

      // Include today's nutrition if available
      let fullContext = userContext;
      if (state.todayData) {
        fullContext += ` | 已摄入：热量${state.todayData.total_calories}千卡/目标${state.todayData.daily_target}千卡 | 蛋白质${state.todayData.total_protein_g}g/目标${state.todayData.protein_goal_g}g`;
      }

      const offlineReply = OfflineKB.generateReply(message, fullContext);
      await typewriterReply(offlineReply, true);
    }
  }

  function appendChatBubble(text, role) {
    const area = $('chat-messages');
    const div = document.createElement('div');
    div.className = 'chat-bubble ' + role;
    div.textContent = text;
    area.appendChild(div);
    area.scrollTop = area.scrollHeight;
    return div;
  }

  function appendTypingIndicator() {
    const area = $('chat-messages');
    const row = document.createElement('div');
    row.className = 'chat-row';
    row.innerHTML = `
      <div class="chat-avatar">🥗</div>
      <div class="chat-bubble ai">
        <div class="typing-dots">
          <div class="typing-dot"></div>
          <div class="typing-dot"></div>
          <div class="typing-dot"></div>
        </div>
      </div>
    `;
    area.appendChild(row);
    area.scrollTop = area.scrollHeight;
    return row;
  }

  async function typewriterReply(text, isOffline) {
    const area = $('chat-messages');
    const row = document.createElement('div');
    row.className = 'chat-row';
    row.innerHTML = '<div class="chat-avatar">🥗</div><div class="chat-bubble ai"></div>';
    const bubble = row.querySelector('.chat-bubble');

    if (isOffline) {
      const badge = document.createElement('span');
      badge.className = 'offline-badge';
      badge.textContent = '离线模式';
      bubble.appendChild(badge);
    }

    const textSpan = document.createElement('span');
    bubble.appendChild(textSpan);
    area.appendChild(row);

    for (let i = 0; i < text.length; i++) {
      textSpan.textContent += text[i];
      area.scrollTop = area.scrollHeight;
      await new Promise(r => setTimeout(r, 30));
    }
  }

  // ─── Settings Page ───────────────────
  function initSettings() {
    $('settings-avatar-letter').textContent = '我';

    // Target adjust buttons
    $('target-minus').addEventListener('click', () => {
      state.user.dailyCalorieTarget = Math.max(1200, state.user.dailyCalorieTarget - 50);
      $('settings-target').textContent = state.user.dailyCalorieTarget;
      updateSettingsMacros();
    });
    $('target-plus').addEventListener('click', () => {
      state.user.dailyCalorieTarget = Math.min(3000, state.user.dailyCalorieTarget + 50);
      $('settings-target').textContent = state.user.dailyCalorieTarget;
      updateSettingsMacros();
    });

    // Preference tags
    qsa('.tag').forEach(tag => {
      tag.addEventListener('click', () => tag.classList.toggle('selected'));
    });

    // Clear today
    $('btn-clear-today').addEventListener('click', async () => {
      if (!confirm('确定清除今日所有饮食记录？此操作不可恢复。')) return;
      if (state.todayData && state.todayData.meals) {
        for (const meal of state.todayData.meals) {
          for (const item of meal.items) {
            try { await api.deleteRecord(item.id); } catch (e) { /* ok */ }
          }
        }
      }
      toast('已清除今日记录');
      loadToday();
    });

    // Edit profile
    $('btn-edit-profile').addEventListener('click', () => {
      toast('编辑资料功能');
    });

    // Export
    $('btn-export').addEventListener('click', () => {
      toast('导出功能开发中');
    });
  }

  function updateSettingsMacros() {
    const cal = state.user.dailyCalorieTarget;
    state.user.macros = {
      protein: Math.round(cal * 0.3 / 4),
      carbs: Math.round(cal * 0.45 / 4),
      fat: Math.round(cal * 0.25 / 9),
    };
    $('settings-macros').textContent =
      `蛋白质 ${state.user.macros.protein}g · 碳水 ${state.user.macros.carbs}g · 脂肪 ${state.user.macros.fat}g`;
  }

  // ─── Navigation Events ───────────────
  function initNavigation() {
    qsa('.nav-item').forEach(item => {
      item.addEventListener('click', () => {
        const page = item.dataset.page;
        if (page === 'settings') {
          switchPage('settings');
        } else if (page === 'analysis-nav') {
          switchPage('home', 'analysis-nav');
          switchTab('analysis');
        } else if (page === 'ai-nav') {
          switchPage('home', 'ai-nav');
          switchTab('ai');
        } else {
          switchPage('home', page);
          switchTab('record');
        }
      });
    });

    qsa('.tab-btn').forEach(btn => {
      btn.addEventListener('click', () => switchTab(btn.dataset.tab));
    });

    // Meal quick access buttons
    qsa('.meal-quick-item').forEach(item => {
      item.addEventListener('click', () => {
        const mealType = item.dataset.meal;
        if (mealType) {
          // Pre-select the meal type in the modal and open search
          $('search-food-input').focus();
          document.querySelectorAll('.meal-type-option').forEach(opt => {
            opt.classList.toggle('selected', opt.dataset.type === mealType);
          });
        }
      });
    });
  }

  // ─── Init ───────────────────────────
  function init() {
    initOnboarding();
    initSearch();
    initChat();
    initSettings();
    initNavigation();

    // Click outside dropdown to close
    document.addEventListener('click', e => {
      if (!e.target.closest('.search-input-wrap')) {
        $('search-dropdown').classList.remove('show');
      }
    });

    // Close modal on overlay click
    $('modal-overlay').addEventListener('click', e => {
      if (e.target === $('modal-overlay')) {
        $('modal-overlay').classList.remove('show');
      }
    });

    // Try to load existing profile
    api.getProfile().then(p => {
      if (p) {
        state.user.height = p.height_cm;
        state.user.weight = p.weight_kg;
        state.user.targetWeight = p.target_weight_kg;
        state.user.dailyCalorieTarget = p.daily_calorie_target;
      }
    }).catch(() => {});
  }

  // Expose init for HTML
  window.AppInit = init;
})();

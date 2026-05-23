// ── Config ──────────────────────────────────────────────────────
var API_BASE = (function() {
  try { return window.ENV.API_BASE; } catch(e) {}
  var h = window.location.hostname;
  if (h === 'localhost' || h === '127.0.0.1') return 'http://localhost:8000';
  return 'https://food-app-backend-1n2n.onrender.com';
})();

var STEP_NAMES = {
  1: '市场洞察', 2: '竞品拆解', 3: '产品定义',
  4: '供应链辅助', 5: '测试方案', 6: '文案输出', 7: '上市跟进'
};
var STEP_ICONS = {
  1: '📊', 2: '🔍', 3: '🎯', 4: '🏭', 5: '🧪', 6: '✍️', 7: '🚀'
};

// ── State ───────────────────────────────────────────────────────
var allResults = {};
var currentCategory = '';
var isGenerating = false;
var abortController = null;
var completedSteps = 0;

// ── DOM refs ────────────────────────────────────────────────────
function $(id) { return document.getElementById(id); }

// ── Toast ───────────────────────────────────────────────────────
var _toastTimer;
function showToast(msg) {
  var t = $('toast');
  t.textContent = msg;
  t.classList.add('show');
  clearTimeout(_toastTimer);
  _toastTimer = setTimeout(function() { t.classList.remove('show'); }, 2000);
}

// ── Progress ────────────────────────────────────────────────────
function updateProgress(completed, total) {
  var wrap = $('progress-wrap');
  var fill = $('progress-fill');
  var text = $('progress-text');
  wrap.classList.add('visible');
  var pct = total > 0 ? Math.round((completed / total) * 100) : 0;
  fill.style.width = pct + '%';
  text.textContent = completed + '/' + total + ' 步骤';
}

function resetProgress() {
  var wrap = $('progress-wrap');
  wrap.classList.remove('visible');
  $('progress-fill').style.width = '0%';
  $('progress-text').textContent = '0/7 步骤';
}

// ── Card Templates ──────────────────────────────────────────────
function createStepCard(step) {
  var name = STEP_NAMES[step];
  var icon = STEP_ICONS[step];
  var card = document.createElement('div');
  card.className = 'step-card loading-card';
  card.id = 'step-card-' + step;
  card.innerHTML =
    '<div class="step-card-header" onclick="toggleCard(' + step + ')">' +
      '<div class="step-card-left">' +
        '<div class="step-icon">' + icon + '</div>' +
        '<div>' +
          '<div class="step-title">步骤 ' + step + '/7：' + name + '</div>' +
          '<div class="step-status" id="step-status-' + step + '">正在生成...</div>' +
        '</div>' +
      '</div>' +
      '<div class="step-card-actions">' +
        '<button class="btn-icon" id="btn-regen-' + step + '" title="重新生成" onclick="event.stopPropagation();regenerateStep(' + step + ')" style="display:none;">🔄</button>' +
        '<span class="chevron" id="chevron-' + step + '">▾</span>' +
      '</div>' +
    '</div>' +
    '<div class="step-card-body" id="step-body-' + step + '">' +
      '<div class="shimmer">' +
        '<div class="shimmer-line"></div>' +
        '<div class="shimmer-line medium"></div>' +
        '<div class="shimmer-line short"></div>' +
      '</div>' +
    '</div>';
  return card;
}

function updateStepCard(step, content, status) {
  var card = $('step-card-' + step);
  var statusEl = $('step-status-' + step);
  var body = $('step-body-' + step);
  var regenBtn = $('btn-regen-' + step);

  card.classList.remove('loading-card');

  if (status === 'completed') {
    card.classList.add('completed');
    statusEl.textContent = '已完成';
    statusEl.style.color = 'var(--green)';
    body.innerHTML = '<div class="step-card-content">' + escapeHtml(content) + '</div>';
    regenBtn.style.display = 'flex';
    // Auto-expand completed cards
    card.classList.add('expanded');
  } else if (status === 'error') {
    card.classList.add('error');
    statusEl.textContent = '生成失败';
    statusEl.style.color = 'var(--red)';
    body.innerHTML = '<div class="step-card-content" style="color:var(--red);">' + escapeHtml(content) + '</div>';
    regenBtn.style.display = 'flex';
    card.classList.add('expanded');
  }
}

// ── Card Collapse/Expand ────────────────────────────────────────
function toggleCard(step) {
  var card = $('step-card-' + step);
  if (!card) return;
  if (card.classList.contains('expanded')) {
    card.classList.remove('expanded');
  } else {
    card.classList.add('expanded');
  }
}

// ── SSE Streaming ───────────────────────────────────────────────
function startGeneration() {
  if (isGenerating) return;

  var input = $('input-category');
  var category = input.value.trim();
  if (!category) { showToast('请输入产品品类名称'); return; }

  currentCategory = category;
  isGenerating = true;
  completedSteps = 0;
  allResults = {};

  // UI reset
  $('btn-send').disabled = true;
  $('input-category').disabled = true;
  resetProgress();
  updateProgress(0, 7);

  var welcome = $('welcome-msg');
  if (welcome) welcome.style.display = 'none';

  // Hide copy-all bar
  var copyBar = $('copy-all-bar');
  copyBar.classList.remove('visible');

  // Remove old step cards
  var chatArea = $('chat-area');
  var oldCards = chatArea.querySelectorAll('.step-card, .msg-user');
  oldCards.forEach(function(el) { el.remove(); });

  // Show user message
  var userMsg = document.createElement('div');
  userMsg.className = 'msg-user';
  userMsg.innerHTML = '<div class="bubble">' + escapeHtml(category) + '</div>';
  chatArea.insertBefore(userMsg, copyBar);

  // Create 7 placeholder cards
  for (var i = 1; i <= 7; i++) {
    var card = createStepCard(i);
    chatArea.insertBefore(card, copyBar);
  }

  $('btn-new-session').style.display = 'block';

  // Start SSE connection
  abortController = new AbortController();

  fetch(API_BASE + '/api/v1/product-agent/generate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ product_category: category }),
    signal: abortController.signal
  }).then(function(response) {
    if (!response.ok) {
      throw new Error('请求失败 (' + response.status + ')');
    }
    return readSSEStream(response);
  }).catch(function(err) {
    if (err.name === 'AbortError') return;
    console.error('SSE error:', err);
    showToast('连接失败: ' + err.message);
    finishGeneration(false);
  });
}

function readSSEStream(response) {
  var reader = response.body.getReader();
  var decoder = new TextDecoder();
  var buffer = '';

  function process() {
    return reader.read().then(function(result) {
      if (result.done) {
        // Process remaining buffer
        if (buffer.trim()) {
          parseSSELines(buffer);
        }
        finishGeneration(true);
        return;
      }

      buffer += decoder.decode(result.value, { stream: true });

      // Split by double newline to get complete SSE events
      var parts = buffer.split('\n\n');
      // Last part may be incomplete — keep in buffer
      buffer = parts.pop();

      parts.forEach(function(part) {
        parseSSELines(part);
      });

      return process();
    });
  }

  return process();
}

function parseSSELines(text) {
  var lines = text.split('\n');
  lines.forEach(function(line) {
    if (line.startsWith('data: ')) {
      var jsonStr = line.substring(6);
      try {
        var data = JSON.parse(jsonStr);
        handleSSEEvent(data);
      } catch(e) {
        // Skip malformed JSON
      }
    }
  });
}

function handleSSEEvent(data) {
  if (data.status === 'all_completed') {
    finishGeneration(true);
    return;
  }

  var step = data.step;
  var name = data.name || STEP_NAMES[step];
  var content = data.content || '';
  var status = data.status || 'completed';

  if (status === 'completed') {
    allResults[String(step)] = content;
    completedSteps++;
    updateStepCard(step, content, 'completed');
    updateProgress(completedSteps, 7);
  } else if (status === 'error') {
    updateStepCard(step, content, 'error');
  }
}

// ── Finish Generation ───────────────────────────────────────────
function finishGeneration(success) {
  isGenerating = false;
  abortController = null;
  $('btn-send').disabled = false;
  $('input-category').disabled = false;
  $('input-category').focus();

  if (success && completedSteps === 7) {
    updateProgress(7, 7);
    showToast('全部7步分析完成！');
    var copyBar = $('copy-all-bar');
    copyBar.classList.add('visible');
  }
}

// ── Regenerate Single Step ──────────────────────────────────────
function regenerateStep(step) {
  if (isGenerating) return;
  if (!currentCategory) return;

  var regenBtn = $('btn-regen-' + step);
  regenBtn.classList.add('regenerating');
  regenBtn.style.pointerEvents = 'none';

  var statusEl = $('step-status-' + step);
  statusEl.textContent = '重新生成中...';
  statusEl.style.color = 'var(--blue)';

  var card = $('step-card-' + step);
  card.classList.add('loading-card');
  card.classList.remove('completed', 'error');

  var body = $('step-body-' + step);
  body.innerHTML =
    '<div class="shimmer">' +
      '<div class="shimmer-line"></div>' +
      '<div class="shimmer-line medium"></div>' +
      '<div class="shimmer-line short"></div>' +
    '</div>';

  fetch(API_BASE + '/api/v1/product-agent/regenerate-step', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      product_category: currentCategory,
      step: step,
      current_results: allResults
    })
  }).then(function(resp) {
    if (!resp.ok) {
      return resp.json().then(function(err) {
        throw new Error(err.detail || '请求失败');
      });
    }
    return resp.json();
  }).then(function(data) {
    allResults[String(step)] = data.content;
    updateStepCard(step, data.content, 'completed');
    showToast('步骤' + step + ' 已重新生成');
  }).catch(function(err) {
    console.error('Regenerate error:', err);
    updateStepCard(step, '重新生成失败: ' + err.message, 'error');
    showToast('重新生成失败: ' + err.message);
  }).finally(function() {
    regenBtn.classList.remove('regenerating');
    regenBtn.style.pointerEvents = '';
  });
}

// ── Copy All ────────────────────────────────────────────────────
function copyAll() {
  if (Object.keys(allResults).length === 0) {
    showToast('暂无内容可复制');
    return;
  }

  var text = '产品开发方案：' + currentCategory + '\n';
  text += '='.repeat(50) + '\n\n';

  for (var i = 1; i <= 7; i++) {
    var content = allResults[String(i)];
    if (!content) continue;
    text += '步骤' + i + '/7：' + STEP_NAMES[i] + '\n';
    text += '-'.repeat(40) + '\n';
    text += content + '\n\n';
  }

  var btn = $('btn-copy-all');

  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(text).then(function() {
      onCopyAllSuccess(btn);
    }).catch(function() {
      fallbackCopyAll(text, btn);
    });
  } else {
    fallbackCopyAll(text, btn);
  }
}

function onCopyAllSuccess(btn) {
  btn.classList.add('copied');
  btn.textContent = '✅ 已复制全部方案';
  showToast('全部方案已复制到剪贴板');
  setTimeout(function() {
    btn.classList.remove('copied');
    btn.textContent = '📋 复制全部方案';
  }, 2000);
}

function fallbackCopyAll(text, btn) {
  var textarea = document.createElement('textarea');
  textarea.value = text;
  textarea.style.position = 'fixed';
  textarea.style.left = '-9999px';
  textarea.style.top = '-9999px';
  document.body.appendChild(textarea);
  textarea.focus();
  textarea.select();
  try {
    document.execCommand('copy');
    onCopyAllSuccess(btn);
  } catch(e) {
    showToast('复制失败，请手动选择复制');
  }
  document.body.removeChild(textarea);
}

// ── Reset Session ───────────────────────────────────────────────
function resetSession() {
  if (isGenerating && abortController) {
    abortController.abort();
  }

  isGenerating = false;
  abortController = null;
  completedSteps = 0;
  allResults = {};
  currentCategory = '';

  resetProgress();

  $('btn-send').disabled = false;
  $('input-category').disabled = false;
  $('input-category').value = '';
  $('btn-new-session').style.display = 'none';

  var copyBar = $('copy-all-bar');
  copyBar.classList.remove('visible');

  var chatArea = $('chat-area');
  var oldCards = chatArea.querySelectorAll('.step-card, .msg-user');
  oldCards.forEach(function(el) { el.remove(); });

  var welcome = $('welcome-msg');
  if (welcome) welcome.style.display = '';
}

// ── Quick Start ─────────────────────────────────────────────────
function quickStart(category) {
  $('input-category').value = category;
  startGeneration();
}

// ── Utility ─────────────────────────────────────────────────────
function escapeHtml(str) {
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

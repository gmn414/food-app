const API_BASE = (function() {
  try { return window.ENV.API_BASE; } catch(e) {}
  var h = window.location.hostname;
  if (h === 'localhost' || h === '127.0.0.1') return 'http://localhost:8000';
  return 'https://food-app-backend-1n2n.onrender.com';
})();

var _results = {};

function showToast(msg) {
  var t = document.getElementById('toast');
  t.textContent = msg;
  t.classList.add('show');
  clearTimeout(t._timeout);
  t._timeout = setTimeout(function() { t.classList.remove('show'); }, 2000);
}

function setStatus(state) {
  var dot = document.getElementById('status-dot');
  var text = document.getElementById('status-text');
  dot.className = 'status-dot';
  if (state === 'loading') {
    dot.classList.add('active');
    text.textContent = '正在调用AI生成...';
  } else if (state === 'done') {
    dot.classList.add('done');
    text.textContent = '生成完成';
  } else if (state === 'error') {
    dot.style.background = 'var(--red)';
    text.textContent = '生成失败，请重试';
  } else {
    text.textContent = state || '等待输入产品信息';
  }
}

function showShimmer(cardId) {
  var body = document.getElementById('body-' + cardId);
  body.innerHTML = '<div class="shimmer"><div class="shimmer-line"></div><div class="shimmer-line medium"></div><div class="shimmer-line short"></div></div>';
  document.getElementById('card-' + cardId).classList.add('loading-card');
}

function showResult(cardId, html) {
  var body = document.getElementById('body-' + cardId);
  body.innerHTML = html;
  document.getElementById('card-' + cardId).classList.remove('loading-card');
  document.getElementById('card-' + cardId).classList.add('pending');
}

function renderKeywords(raw) {
  if (!raw) return '';

  var coreMatch = raw.match(/【核心关键词】\s*([\s\S]*?)(?=【长尾关键词】|$)/);
  var longMatch = raw.match(/【长尾关键词】\s*([\s\S]*)/);

  var html = '';

  if (coreMatch && coreMatch[1].trim()) {
    var coreWords = coreMatch[1].trim().split(/[,，、]/).map(function(k) { return k.trim(); }).filter(Boolean);
    html += '<div class="kw-section"><div class="kw-label">核心关键词</div><div class="kw-tags">';
    coreWords.forEach(function(k) {
      html += '<span class="kw-tag">' + escapeHtml(k) + '</span>';
    });
    html += '</div></div>';
  }

  if (longMatch && longMatch[1].trim()) {
    var longWords = longMatch[1].trim().split(/[,，、]/).map(function(k) { return k.trim(); }).filter(Boolean);
    html += '<div class="kw-section"><div class="kw-label">长尾关键词</div><div class="kw-tags">';
    longWords.forEach(function(k) {
      html += '<span class="kw-tag">' + escapeHtml(k) + '</span>';
    });
    html += '</div></div>';
  }

  if (!html) {
    var words = raw.trim().split(/[,，、\n]/).map(function(k) { return k.trim(); }).filter(Boolean);
    if (words.length > 0) {
      html += '<div class="kw-tags">';
      words.forEach(function(k) {
        html += '<span class="kw-tag">' + escapeHtml(k) + '</span>';
      });
      html += '</div>';
    }
  }

  return html || escapeHtml(raw);
}

function escapeHtml(str) {
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function renderBulletPoints(raw) {
  if (!raw) return '';
  var lines = raw.split('\n').filter(function(l) { return l.trim(); });
  if (lines.length === 0) return escapeHtml(raw);
  var html = '<ul style="padding-left:20px;margin:0;">';
  lines.forEach(function(line) {
    var cleaned = line.replace(/^\d+[\.\)、]\s*/, '').trim();
    if (cleaned) {
      html += '<li style="margin-bottom:8px;">' + escapeHtml(cleaned) + '</li>';
    }
  });
  html += '</ul>';
  return html;
}

function renderDescription(raw) {
  if (!raw) return '';
  // If already contains HTML tags, return raw (sanitized)
  if (/<\/?[a-z][\s\S]*>/i.test(raw)) return raw;
  // Otherwise wrap paragraphs
  var parts = raw.split('\n\n').filter(function(p) { return p.trim(); });
  if (parts.length <= 1) return '<p>' + escapeHtml(raw) + '</p>';
  return parts.map(function(p) { return '<p>' + escapeHtml(p.trim()) + '</p>'; }).join('');
}

async function generateListing() {
  var btn = document.getElementById('btn-generate');
  var productName = document.getElementById('input-product-name').value.trim();
  var sellingPoints = document.getElementById('input-selling-points').value.trim();
  var targetUser = document.getElementById('input-target-user').value.trim();
  var specifications = document.getElementById('input-specifications').value.trim();

  if (!productName) { showToast('请输入产品名称'); return; }
  if (!sellingPoints) { showToast('请输入核心卖点'); return; }

  // Enter loading state
  btn.classList.add('loading');
  btn.disabled = true;
  setStatus('loading');

  var fields = ['title', 'bullet_points', 'description', 'keywords'];
  fields.forEach(function(f) { showShimmer(f); });

  try {
    var resp = await fetch(API_BASE + '/api/v1/generate-listing', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        product_name: productName,
        selling_points: sellingPoints,
        target_user: targetUser,
        specifications: specifications
      })
    });

    if (!resp.ok) {
      var errData = await resp.json().catch(function() { return {}; });
      throw new Error(errData.detail || '请求失败 (' + resp.status + ')');
    }

    var data = await resp.json();
    _results = data;

    showResult('title', '<p>' + escapeHtml(data.title || '') + '</p>');
    showResult('bullets', renderBulletPoints(data.bullet_points));
    showResult('desc', renderDescription(data.description));
    showResult('kw', renderKeywords(data.keywords));

    setStatus('done');
    showToast('生成完成！');

  } catch (err) {
    console.error('Generate listing error:', err);
    setStatus('error');

    fields.forEach(function(f) {
      var body = document.getElementById('body-' + f);
      body.innerHTML = '<span style="color:var(--red);">生成失败: ' + escapeHtml(err.message) + '</span>';
      document.getElementById('card-' + f).classList.remove('loading-card');
    });

    showToast('生成失败: ' + err.message);
  } finally {
    btn.classList.remove('loading');
    btn.disabled = false;
  }
}

function copyResult(field) {
  var text = '';
  if (field === 'title') {
    text = _results.title || '';
  } else if (field === 'bullet_points') {
    text = _results.bullet_points || '';
  } else if (field === 'description') {
    text = _results.description || '';
  } else if (field === 'keywords') {
    text = _results.keywords || '';
  }

  if (!text) { showToast('暂无内容可复制'); return; }

  // Strip HTML from description if any
  if (field === 'description') {
    var tmp = document.createElement('div');
    tmp.innerHTML = text;
    text = tmp.textContent || tmp.innerText || '';
  }

  var btn = document.getElementById('btn-copy-' + (field === 'bullet_points' ? 'bullets' : field === 'description' ? 'desc' : field === 'keywords' ? 'kw' : field));

  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(text).then(function() {
      btn.classList.add('copied');
      btn.textContent = '已复制';
      showToast('已复制到剪贴板');
      setTimeout(function() {
        btn.classList.remove('copied');
        btn.textContent = '📋 复制';
      }, 1500);
    }).catch(function() {
      fallbackCopy(text, btn);
    });
  } else {
    fallbackCopy(text, btn);
  }
}

function fallbackCopy(text, btn) {
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
    btn.classList.add('copied');
    btn.textContent = '已复制';
    showToast('已复制到剪贴板');
    setTimeout(function() {
      btn.classList.remove('copied');
      btn.textContent = '📋 复制';
    }, 1500);
  } catch(e) {
    showToast('复制失败，请手动选择复制');
  }
  document.body.removeChild(textarea);
}

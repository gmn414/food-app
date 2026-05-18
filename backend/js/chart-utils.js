/* ══════════════════════════════════════
   Chart Utils — Canvas-based chart drawing
   ══════════════════════════════════════ */

const ChartUtils = {
  /**
   * Draw calorie progress ring.
   * @param {string} canvasId
   * @param {number} consumed - calories consumed
   * @param {number} target - daily target
   * @param {number} size - canvas size in px
   */
  drawCalorieRing(canvasId, consumed, target, size = 120) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;
    const dpr = window.devicePixelRatio || 1;
    canvas.width = size * dpr;
    canvas.height = size * dpr;
    canvas.style.width = size + 'px';
    canvas.style.height = size + 'px';
    const ctx = canvas.getContext('2d');
    ctx.scale(dpr, dpr);

    const cx = size / 2, cy = size / 2;
    const radius = size / 2 - 8;
    const lineWidth = 8;
    const ratio = Math.min(consumed / target, 1);

    // Background ring
    ctx.beginPath();
    ctx.arc(cx, cy, radius, 0, Math.PI * 2);
    ctx.strokeStyle = 'rgba(255,255,255,0.1)';
    ctx.lineWidth = lineWidth;
    ctx.lineCap = 'round';
    ctx.stroke();

    // Determine color
    let color = '#4CAF50';
    if (ratio > 0.9) color = '#FF5252';
    else if (ratio > 0.7) color = '#FF9800';

    // Progress arc (animated)
    const targetAngle = ratio * Math.PI * 2;
    let currentAngle = 0;
    const duration = 1000;
    const startTime = performance.now();

    const animate = (now) => {
      const elapsed = now - startTime;
      const progress = Math.min(elapsed / duration, 1);
      // easeOutCubic
      const eased = 1 - Math.pow(1 - progress, 3);
      currentAngle = targetAngle * eased;

      // Clear only the ring area
      ctx.clearRect(0, 0, size, size);

      // Redraw background
      ctx.beginPath();
      ctx.arc(cx, cy, radius, 0, Math.PI * 2);
      ctx.strokeStyle = 'rgba(255,255,255,0.1)';
      ctx.lineWidth = lineWidth;
      ctx.lineCap = 'round';
      ctx.stroke();

      // Draw progress
      ctx.beginPath();
      ctx.arc(cx, cy, radius, -Math.PI / 2, -Math.PI / 2 + currentAngle);
      ctx.strokeStyle = color;
      ctx.lineWidth = lineWidth;
      ctx.lineCap = 'round';
      ctx.stroke();

      if (progress < 1) {
        requestAnimationFrame(animate);
      }
    };

    requestAnimationFrame(animate);

    // Center text
    const remaining = Math.max(0, Math.round(target - consumed));
    return { remaining, ratio, color };
  },

  /**
   * Draw three-ring macro chart.
   */
  drawMacroRings(canvasId, protein, proteinGoal, carbs, carbsGoal, fat, fatGoal, size = 200) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;
    const dpr = window.devicePixelRatio || 1;
    canvas.width = size * dpr;
    canvas.height = size * dpr;
    canvas.style.width = size + 'px';
    canvas.style.height = size + 'px';
    const ctx = canvas.getContext('2d');
    ctx.scale(dpr, dpr);

    const cx = size / 2, cy = size / 2;
    const colors = ['#4CAF50', '#42A5F5', '#FFCA28'];
    const rings = [
      { value: protein, goal: proteinGoal, color: colors[0], radius: 84, width: 10 },
      { value: carbs, goal: carbsGoal, color: colors[1], radius: 68, width: 10 },
      { value: fat, goal: fatGoal, color: colors[2], radius: 52, width: 10 },
    ];

    rings.forEach((ring) => {
      const ratio = Math.min(ring.value / ring.goal, 1.5);

      // Background
      ctx.beginPath();
      ctx.arc(cx, cy, ring.radius, 0, Math.PI * 2);
      ctx.strokeStyle = 'rgba(255,255,255,0.08)';
      ctx.lineWidth = ring.width;
      ctx.stroke();

      // Progress
      const angle = Math.min(ratio, 1) * Math.PI * 2;
      const arcColor = ratio > 1 ? '#FF5252' : ring.color;
      ctx.beginPath();
      ctx.arc(cx, cy, ring.radius, -Math.PI / 2, -Math.PI / 2 + angle);
      ctx.strokeStyle = arcColor;
      ctx.lineWidth = ring.width;
      ctx.lineCap = 'round';
      ctx.stroke();
    });

    // Center text placeholder — caller can add text overlay via HTML
  },

  /**
   * Draw weekly calorie bar chart.
   */
  drawWeeklyChart(canvasId, dailyData, targetLine, size = 320, height = 160) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;
    const dpr = window.devicePixelRatio || 1;
    canvas.width = size * dpr;
    canvas.height = height * dpr;
    canvas.style.width = size + 'px';
    canvas.style.height = height + 'px';
    const ctx = canvas.getContext('2d');
    ctx.scale(dpr, dpr);

    const padding = { top: 20, right: 8, bottom: 28, left: 8 };
    const chartW = size - padding.left - padding.right;
    const chartH = height - padding.top - padding.bottom;
    const maxVal = Math.max(targetLine * 1.3, ...dailyData.map(d => d.total));
    const barWidth = (chartW / dailyData.length) * 0.6;
    const barGap = chartW / dailyData.length;

    // Target line
    const targetY = padding.top + chartH - (targetLine / maxVal) * chartH;
    ctx.beginPath();
    ctx.setLineDash([6, 4]);
    ctx.moveTo(padding.left, targetY);
    ctx.lineTo(size - padding.right, targetY);
    ctx.strokeStyle = 'rgba(255,255,255,0.3)';
    ctx.lineWidth = 1;
    ctx.stroke();
    ctx.setLineDash([]);

    // Target label
    ctx.fillStyle = 'rgba(255,255,255,0.4)';
    ctx.font = '10px -apple-system, sans-serif';
    ctx.fillText(targetLine + '', size - padding.right - 24, targetY - 4);

    // Chinese day labels
    const dayLabels = ['一', '二', '三', '四', '五', '六', '日'];

    dailyData.forEach((d, i) => {
      const x = padding.left + i * barGap + (barGap - barWidth) / 2;
      const barH = (d.total / maxVal) * chartH;
      const y = padding.top + chartH - barH;

      const color = d.total > targetLine ? '#FF5252' : '#4CAF50';
      ctx.fillStyle = color;
      this._roundRect(ctx, x, y, barWidth, barH, 4);

      // Value on top
      if (d.total > 0) {
        ctx.fillStyle = 'rgba(255,255,255,0.8)';
        ctx.font = '9px -apple-system, sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText(d.total + '', x + barWidth / 2, y - 4);
        ctx.textAlign = 'start';
      }

      // Day label
      ctx.fillStyle = 'rgba(255,255,255,0.5)';
      ctx.font = '11px -apple-system, sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText(dayLabels[i], x + barWidth / 2, padding.top + chartH + 16);
      ctx.textAlign = 'start';
    });
  },

  /**
   * Draw 7-day score trend line.
   */
  drawTrendLine(canvasId, scores, size = 280, height = 100) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;
    const dpr = window.devicePixelRatio || 1;
    canvas.width = size * dpr;
    canvas.height = height * dpr;
    canvas.style.width = size + 'px';
    canvas.style.height = height + 'px';
    const ctx = canvas.getContext('2d');
    ctx.scale(dpr, dpr);

    const padding = { top: 10, right: 10, bottom: 20, left: 30 };
    const chartW = size - padding.left - padding.right;
    const chartH = height - padding.top - padding.bottom;

    if (scores.length < 2) return;

    const maxScore = 10, minScore = 0;
    const stepX = chartW / (scores.length - 1);
    const points = scores.map((s, i) => ({
      x: padding.left + i * stepX,
      y: padding.top + chartH - ((s - minScore) / (maxScore - minScore)) * chartH,
    }));

    // Grid lines
    for (let i = 0; i <= 4; i++) {
      const y = padding.top + (chartH / 4) * i;
      ctx.beginPath();
      ctx.moveTo(padding.left, y);
      ctx.lineTo(size - padding.right, y);
      ctx.strokeStyle = 'rgba(255,255,255,0.05)';
      ctx.stroke();
      ctx.fillStyle = 'rgba(255,255,255,0.3)';
      ctx.font = '9px -apple-system, sans-serif';
      ctx.fillText((10 - i * 2.5) + '', 4, y + 3);
    }

    // Line
    ctx.beginPath();
    ctx.moveTo(points[0].x, points[0].y);
    for (let i = 1; i < points.length; i++) {
      ctx.lineTo(points[i].x, points[i].y);
    }
    ctx.strokeStyle = '#4CAF50';
    ctx.lineWidth = 2;
    ctx.lineJoin = 'round';
    ctx.stroke();

    // Dots
    points.forEach(p => {
      ctx.beginPath();
      ctx.arc(p.x, p.y, 4, 0, Math.PI * 2);
      ctx.fillStyle = '#4CAF50';
      ctx.fill();
      ctx.beginPath();
      ctx.arc(p.x, p.y, 2, 0, Math.PI * 2);
      ctx.fillStyle = '#fff';
      ctx.fill();
    });
  },

  _roundRect(ctx, x, y, w, h, r) {
    ctx.beginPath();
    ctx.moveTo(x + r, y);
    ctx.lineTo(x + w - r, y);
    ctx.arcTo(x + w, y, x + w, y + r, r);
    ctx.lineTo(x + w, y + h);
    ctx.arcTo(x + w, y + h, x - r, y + h, r);
    ctx.lineTo(x, y + h);
    ctx.arcTo(x, y + h, x, y, r);
    ctx.lineTo(x, y + r);
    ctx.arcTo(x, y, x + r, y, r);
    ctx.closePath();
    ctx.fill();
  },

  /** Animate number from start to end */
  animateNumber(el, end, duration = 500) {
    const start = parseInt(el.textContent) || 0;
    const startTime = performance.now();
    const animate = (now) => {
      const elapsed = now - startTime;
      const progress = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      el.textContent = Math.round(start + (end - start) * eased);
      if (progress < 1) requestAnimationFrame(animate);
    };
    requestAnimationFrame(animate);
  },
};

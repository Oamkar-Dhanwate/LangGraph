// Shared UI components
/**
 * ClientIQ — Shared UI Components
 * Reusable DOM-building helpers for tables, badges, risk indicators, citations.
 */

// ── Risk Badge ────────────────────────────────────────────────────────────────

function riskBadge(level) {
  const map = {
    critical: ['badge-red',    '● Critical'],
    high:     ['badge-red',    '● High'],
    medium:   ['badge-amber',  '● Medium'],
    low:      ['badge-green',  '● Low'],
  };
  const [cls, label] = map[level?.toLowerCase()] || ['badge-gray', level || '—'];
  return `<span class="badge ${cls}">${label}</span>`;
}

// ── Sentiment Badge ───────────────────────────────────────────────────────────

function sentimentBadge(label, score) {
  const map = {
    positive: ['badge-green',  '▲'],
    neutral:  ['badge-gray',   '●'],
    negative: ['badge-red',    '▼'],
  };
  const [cls, icon] = map[label?.toLowerCase()] || ['badge-gray', '●'];
  const scoreStr = score !== undefined ? ` (${Number(score).toFixed(2)})` : '';
  return `<span class="badge ${cls}">${icon} ${label || '—'}${scoreStr}</span>`;
}

// ── Health Score Bar ──────────────────────────────────────────────────────────

function healthBar(score) {
  const s = Number(score) || 0;
  const color = s >= 70 ? 'var(--accent-green)' : s >= 40 ? 'var(--accent-amber)' : 'var(--accent-red)';
  return `
    <div style="display:flex;align-items:center;gap:8px;">
      <div class="progress-bar" style="width:80px;flex-shrink:0">
        <div class="progress-fill" style="width:${s}%;background:${color}"></div>
      </div>
      <span class="text-sm" style="color:${color};font-weight:600">${s.toFixed(0)}</span>
    </div>`;
}

// ── Churn Risk Display ────────────────────────────────────────────────────────

function churnRiskDisplay(prob) {
  const p = Number(prob) || 0;
  const pct = (p * 100).toFixed(1);
  const level = p >= 0.75 ? 'critical' : p >= 0.50 ? 'high' : p >= 0.25 ? 'medium' : 'low';
  return `${riskBadge(level)} <span class="text-sm text-muted">${pct}%</span>`;
}

// ── Tier Badge ────────────────────────────────────────────────────────────────

function tierBadge(tier) {
  const map = {
    platinum: 'badge-purple',
    gold:     'badge-amber',
    silver:   'badge-blue',
    bronze:   'badge-gray',
  };
  return `<span class="badge ${map[tier] || 'badge-gray'}">${(tier || '—').toUpperCase()}</span>`;
}

// ── Status Badge ──────────────────────────────────────────────────────────────

function statusBadge(status) {
  const map = {
    active:       'badge-green',
    open:         'badge-red',
    in_progress:  'badge-amber',
    resolved:     'badge-teal',
    closed:       'badge-gray',
    expired:      'badge-gray',
    terminated:   'badge-red',
    pending_customer: 'badge-blue',
  };
  return `<span class="badge ${map[status?.toLowerCase()] || 'badge-gray'}">${(status || '—').replaceAll('_', ' ')}</span>`;
}

// ── Priority Badge ────────────────────────────────────────────────────────────

function priorityBadge(priority) {
  const map = { critical: 'badge-red', high: 'badge-amber', medium: 'badge-blue', low: 'badge-gray' };
  return `<span class="badge ${map[priority?.toLowerCase()] || 'badge-gray'}">${priority || '—'}</span>`;
}

// ── Currency Format ───────────────────────────────────────────────────────────

function formatCurrency(amount, compact = true) {
  const n = Number(amount) || 0;
  if (compact) {
    if (n >= 1e9) return `$${(n / 1e9).toFixed(1)}B`;
    if (n >= 1e6) return `$${(n / 1e6).toFixed(1)}M`;
    if (n >= 1e3) return `$${(n / 1e3).toFixed(0)}K`;
  }
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(n);
}

// ── Date Format ───────────────────────────────────────────────────────────────

function formatDate(isoStr, opts = {}) {
  if (!isoStr) return '—';
  const d = new Date(isoStr);
  if (isNaN(d)) return '—';
  return d.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric', ...opts });
}

function timeAgo(isoStr) {
  if (!isoStr) return '—';
  const diff = Date.now() - new Date(isoStr).getTime();
  const d = Math.floor(diff / 86400000);
  if (d === 0) return 'Today';
  if (d === 1) return 'Yesterday';
  if (d < 30) return `${d}d ago`;
  if (d < 365) return `${Math.floor(d / 30)}mo ago`;
  return `${Math.floor(d / 365)}yr ago`;
}

// ── Citation Card ─────────────────────────────────────────────────────────────

function citationCard(citation, index) {
  const score = Number(citation.score || 0);
  const pct = (score * 100).toFixed(0);
  const typeIcons = { email: '✉', meeting: '👥', call: '📞', contract: '📄', ticket: '🎫' };
  const icon = typeIcons[citation.source_type] || '📄';
  return `
    <div class="card" style="margin-bottom:10px;padding:14px">
      <div class="flex items-center justify-between mb-2">
        <span class="text-sm" style="font-weight:600">${icon} ${citation.source || 'Source ' + (index + 1)}</span>
        <span class="badge badge-blue">${pct}% match</span>
      </div>
      <p class="text-sm text-muted" style="line-height:1.5;font-style:italic">"${citation.excerpt || '—'}"</p>
    </div>`;
}

// ── Recommendation Card ───────────────────────────────────────────────────────

function recommendationCard(text, priority = 'medium') {
  const icons = { critical: '🚨', high: '⚠️', medium: '💡', low: '📌' };
  const icon = icons[priority] || '💡';
  return `
    <div style="display:flex;gap:10px;padding:10px 0;border-bottom:1px solid var(--border)">
      <span style="font-size:16px;flex-shrink:0">${icon}</span>
      <p class="text-sm" style="line-height:1.5">${text}</p>
    </div>`;
}

// ── Empty State ───────────────────────────────────────────────────────────────

function emptyState(icon, title, subtitle) {
  return `
    <div style="text-align:center;padding:48px 24px;color:var(--text-secondary)">
      <div style="font-size:40px;margin-bottom:12px">${icon}</div>
      <p style="font-weight:600;color:var(--text-primary);margin-bottom:4px">${title}</p>
      <p class="text-sm">${subtitle}</p>
    </div>`;
}

// ── Loading Skeleton ──────────────────────────────────────────────────────────

function loadingSkeleton(rows = 5, cols = 4) {
  const style = 'background:var(--bg-elevated);border-radius:4px;height:14px;animation:shimmer 1.5s infinite';
  const widths = ['60%', '45%', '30%', '20%', '50%'];
  let html = '';
  for (let r = 0; r < rows; r++) {
    html += '<tr>';
    for (let c = 0; c < cols; c++) {
      html += `<td><div style="${style};width:${widths[(r+c)%5]}"></div></td>`;
    }
    html += '</tr>';
  }
  return html;
}

// ── Sidebar Active Link ───────────────────────────────────────────────────────

function highlightActiveNav() {
  const current = window.location.pathname.split('/').pop() || 'dashboard.html';
  document.querySelectorAll('.nav-item[href]').forEach(el => {
    el.classList.toggle('active', el.getAttribute('href') === current);
  });
}

// ── Metric Card Builder ───────────────────────────────────────────────────────

function setMetric(id, value, delta, deltaUp) {
  const el = document.getElementById(id);
  if (!el) return;
  el.querySelector('[data-value]').textContent = value;
  if (delta !== undefined) {
    const deltaEl = el.querySelector('[data-delta]');
    if (deltaEl) {
      deltaEl.textContent = delta;
      deltaEl.className = `metric-delta ${deltaUp ? 'up' : 'down'}`;
    }
  }
}
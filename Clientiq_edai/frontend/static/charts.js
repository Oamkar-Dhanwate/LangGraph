// Chart.js helpers
/**
 * ClientIQ — Chart Helpers
 * Preconfigured Chart.js builders with the enterprise dark theme.
 */

// ── Default Chart.js Global Defaults ─────────────────────────────────────────

if (typeof Chart !== 'undefined') {
  Chart.defaults.color = '#8b949e';
  Chart.defaults.borderColor = 'rgba(240,246,252,0.10)';
  Chart.defaults.font.family = "'DM Sans', system-ui, sans-serif";
  Chart.defaults.font.size = 12;
  Chart.defaults.plugins.legend.labels.boxWidth = 12;
  Chart.defaults.plugins.tooltip.backgroundColor = '#1c2128';
  Chart.defaults.plugins.tooltip.borderColor = 'rgba(240,246,252,0.20)';
  Chart.defaults.plugins.tooltip.borderWidth = 1;
  Chart.defaults.plugins.tooltip.padding = 10;
  Chart.defaults.plugins.tooltip.titleColor = '#e6edf3';
  Chart.defaults.plugins.tooltip.bodyColor = '#8b949e';
}

// ── Color Palette ─────────────────────────────────────────────────────────────

const CIQ_COLORS = {
  blue:   '#388bfd',
  teal:   '#1fa788',
  amber:  '#d29922',
  red:    '#f85149',
  green:  '#3fb950',
  purple: '#a371f7',
  gray:   '#484f58',
};

const CHART_PALETTE = Object.values(CIQ_COLORS);

function hexToRgba(hex, alpha) {
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  return `rgba(${r},${g},${b},${alpha})`;
}

// ── Revenue Line Chart ────────────────────────────────────────────────────────

function buildRevenueChart(canvasId, labels, values) {
  const ctx = document.getElementById(canvasId);
  if (!ctx) return null;
  const existing = Chart.getChart(canvasId);
  if (existing) existing.destroy();

  return new Chart(ctx, {
    type: 'line',
    data: {
      labels,
      datasets: [{
        label: 'Revenue',
        data: values,
        borderColor: CIQ_COLORS.blue,
        backgroundColor: hexToRgba(CIQ_COLORS.blue, 0.08),
        borderWidth: 2,
        pointBackgroundColor: CIQ_COLORS.blue,
        pointRadius: 4,
        pointHoverRadius: 6,
        fill: true,
        tension: 0.4,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { grid: { display: false } },
        y: {
          ticks: {
            callback: v => v >= 1e6 ? `$${(v/1e6).toFixed(1)}M` : v >= 1e3 ? `$${(v/1e3).toFixed(0)}K` : `$${v}`
          }
        }
      }
    }
  });
}

// ── Health Distribution Doughnut ──────────────────────────────────────────────

function buildHealthDonut(canvasId, data) {
  const ctx = document.getElementById(canvasId);
  if (!ctx) return null;
  const existing = Chart.getChart(canvasId);
  if (existing) existing.destroy();

  return new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: ['Healthy (70+)', 'At Risk (40-70)', 'Critical (<40)'],
      datasets: [{
        data: [data.healthy || 0, data.at_risk || 0, data.critical || 0],
        backgroundColor: [CIQ_COLORS.green, CIQ_COLORS.amber, CIQ_COLORS.red],
        borderWidth: 0,
        hoverOffset: 4,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: '70%',
      plugins: {
        legend: { position: 'bottom', labels: { padding: 16 } }
      }
    }
  });
}

// ── Sentiment Timeline Line Chart ─────────────────────────────────────────────

function buildSentimentChart(canvasId, dataPoints) {
  const ctx = document.getElementById(canvasId);
  if (!ctx) return null;
  const existing = Chart.getChart(canvasId);
  if (existing) existing.destroy();

  const labels = dataPoints.map(d => formatDate(d.date, { month: 'short', day: 'numeric' }));
  const scores = dataPoints.map(d => Number(d.score).toFixed(3));

  return new Chart(ctx, {
    type: 'line',
    data: {
      labels,
      datasets: [{
        label: 'Sentiment Score',
        data: scores,
        borderColor: CIQ_COLORS.teal,
        backgroundColor: hexToRgba(CIQ_COLORS.teal, 0.07),
        borderWidth: 2,
        pointRadius: 2,
        fill: true,
        tension: 0.4,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { grid: { display: false }, ticks: { maxTicksLimit: 8 } },
        y: { min: -1, max: 1, ticks: { stepSize: 0.5 } }
      }
    }
  });
}

// ── Churn Risk Horizontal Bar ─────────────────────────────────────────────────

function buildChurnChart(canvasId, companies) {
  const ctx = document.getElementById(canvasId);
  if (!ctx) return null;
  const existing = Chart.getChart(canvasId);
  if (existing) existing.destroy();

  const top = companies.slice(0, 10);
  const labels = top.map(c => c.name.length > 18 ? c.name.slice(0, 18) + '…' : c.name);
  const data   = top.map(c => (Number(c.churn_risk) * 100).toFixed(1));
  const colors = data.map(v => v >= 75 ? CIQ_COLORS.red : v >= 50 ? CIQ_COLORS.amber : CIQ_COLORS.blue);

  return new Chart(ctx, {
    type: 'bar',
    data: {
      labels,
      datasets: [{
        label: 'Churn Risk %',
        data,
        backgroundColor: colors,
        borderRadius: 4,
        borderSkipped: false,
      }]
    },
    options: {
      indexAxis: 'y',
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { min: 0, max: 100, ticks: { callback: v => v + '%' } },
        y: { grid: { display: false } }
      }
    }
  });
}

// ── KPI Radar Chart ───────────────────────────────────────────────────────────

function buildRadarChart(canvasId, labels, dataset1, dataset2, label1 = 'Current', label2 = 'Target') {
  const ctx = document.getElementById(canvasId);
  if (!ctx) return null;
  const existing = Chart.getChart(canvasId);
  if (existing) existing.destroy();

  return new Chart(ctx, {
    type: 'radar',
    data: {
      labels,
      datasets: [
        {
          label: label1,
          data: dataset1,
          borderColor: CIQ_COLORS.blue,
          backgroundColor: hexToRgba(CIQ_COLORS.blue, 0.1),
          borderWidth: 2,
          pointBackgroundColor: CIQ_COLORS.blue,
        },
        {
          label: label2,
          data: dataset2,
          borderColor: CIQ_COLORS.teal,
          backgroundColor: hexToRgba(CIQ_COLORS.teal, 0.08),
          borderWidth: 2,
          borderDash: [4, 4],
          pointBackgroundColor: CIQ_COLORS.teal,
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        r: {
          angleLines: { color: 'rgba(240,246,252,0.08)' },
          grid:       { color: 'rgba(240,246,252,0.08)' },
          ticks: { display: false },
          pointLabels: { color: '#8b949e', font: { size: 11 } }
        }
      }
    }
  });
}

// ── Pipeline Funnel / Stage Bar ────────────────────────────────────────────────

function buildPipelineChart(canvasId, stages, counts) {
  const ctx = document.getElementById(canvasId);
  if (!ctx) return null;
  const existing = Chart.getChart(canvasId);
  if (existing) existing.destroy();

  return new Chart(ctx, {
    type: 'bar',
    data: {
      labels: stages,
      datasets: [{
        label: 'Deals',
        data: counts,
        backgroundColor: CHART_PALETTE,
        borderRadius: 6,
        borderSkipped: false,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { grid: { display: false } },
        y: {}
      }
    }
  });
}
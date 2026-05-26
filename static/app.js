'use strict';

const BOOK_NAMES = {};
let allResults = [];
let sortCol = 'ev_vs_pinnacle';
let sortDir = 'desc';

// ── Helpers ───────────────────────────────────────────────────────────────────

function fmtEV(val) {
  if (val === null || val === undefined) return { text: '—', cls: 'ev-null' };
  const pct = val.toFixed(2);
  if (val > 5) return { text: `+${pct}%`, cls: 'ev-pos ev-warn' };
  if (val > 0) return { text: `+${pct}%`, cls: 'ev-pos' };
  if (val < 0) return { text: `${pct}%`, cls: 'ev-neg' };
  return { text: `${pct}%`, cls: 'ev-null' };
}

function fmtOdds(american) {
  if (american === null || american === undefined) return '—';
  return american >= 0 ? `+${american}` : `${american}`;
}

function fmtAge(seconds) {
  if (seconds < 0) return 'no cache';
  if (seconds < 60) return `${seconds}s ago`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  return `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m ago`;
}

function bookLabel(book) {
  return BOOK_NAMES[book] || book;
}

function bookBadgeClass(book) {
  if (book === 'pinnacle') return 'book-badge pinnacle';
  if (book === 'kalshi') return 'book-badge kalshi';
  return 'book-badge';
}

function sortValue(r, col) {
  switch (col) {
    case 'sport': return r.odds.sport;
    case 'market': return r.odds.market;
    case 'event': return r.odds.event;
    case 'selection': return r.odds.selection;
    case 'book': return r.odds.book;
    case 'american_odds': return r.odds.american_odds;
    case 'ev_vs_pinnacle': return r.ev_vs_pinnacle ?? -Infinity;
    case 'ev_vs_best': return r.ev_vs_best ?? -Infinity;
    default: return '';
  }
}

// ── State & Filters ───────────────────────────────────────────────────────────

function getFilters() {
  return {
    sport: document.getElementById('sport-filter').value,
    method: document.getElementById('method-filter').value,
    positiveOnly: document.getElementById('positive-only').checked,
    minEV: parseFloat(document.getElementById('min-ev').value),
    book: document.getElementById('book-filter').value,
  };
}

function applyFilters(results) {
  const f = getFilters();
  return results.filter(r => {
    if (f.sport && r.odds.sport !== f.sport) return false;
    if (f.book && r.odds.book !== f.book) return false;

    if (f.positiveOnly || f.minEV > 0) {
      const evs = [];
      if (f.method !== 'best' && r.ev_vs_pinnacle !== null) evs.push(r.ev_vs_pinnacle);
      if (f.method !== 'pinnacle' && r.ev_vs_best !== null) evs.push(r.ev_vs_best);
      if (!evs.length || Math.max(...evs) < f.minEV) return false;
    }

    return true;
  });
}

function applySorting(results) {
  return [...results].sort((a, b) => {
    const av = sortValue(a, sortCol);
    const bv = sortValue(b, sortCol);
    if (av < bv) return sortDir === 'asc' ? -1 : 1;
    if (av > bv) return sortDir === 'asc' ? 1 : -1;
    return 0;
  });
}

// ── Render ────────────────────────────────────────────────────────────────────

function renderTable() {
  const filtered = applyFilters(allResults);
  const sorted = applySorting(filtered);
  const tbody = document.getElementById('results-body');
  const method = document.getElementById('method-filter').value;

  if (!sorted.length) {
    tbody.innerHTML = '<tr><td colspan="8" class="empty">No results match your filters.</td></tr>';
    document.getElementById('row-count').textContent = '';
    return;
  }

  tbody.innerHTML = sorted.map(r => {
    const ev_pin = fmtEV(r.ev_vs_pinnacle);
    const ev_best = fmtEV(r.ev_vs_best);
    const oddsSign = r.odds.american_odds >= 0 ? 'odds-pos' : 'odds-neg';

    const ev_pin_cell = method === 'best'
      ? '<td class="ev-null">—</td>'
      : `<td class="${ev_pin.cls}">${ev_pin.text}</td>`;

    const ev_best_cell = method === 'pinnacle'
      ? '<td class="ev-null">—</td>'
      : `<td class="${ev_best.cls}">${ev_best.text}</td>`;

    return `<tr>
      <td>${r.odds.sport.toUpperCase()}</td>
      <td>${r.odds.market}</td>
      <td>${r.odds.event}</td>
      <td>${r.odds.selection}</td>
      <td><span class="${bookBadgeClass(r.odds.book)}">${bookLabel(r.odds.book)}</span></td>
      <td class="${oddsSign}">${fmtOdds(r.odds.american_odds)}</td>
      ${ev_pin_cell}
      ${ev_best_cell}
    </tr>`;
  }).join('');

  document.getElementById('row-count').textContent =
    `${sorted.length} line${sorted.length !== 1 ? 's' : ''} shown`;
}

// ── Sort headers ──────────────────────────────────────────────────────────────

function updateSortHeaders() {
  document.querySelectorAll('th[data-col]').forEach(th => {
    th.classList.remove('sort-asc', 'sort-desc');
    if (th.dataset.col === sortCol) {
      th.classList.add(sortDir === 'asc' ? 'sort-asc' : 'sort-desc');
    }
  });
}

document.querySelectorAll('th.sortable').forEach(th => {
  th.addEventListener('click', () => {
    const col = th.dataset.col;
    if (sortCol === col) {
      sortDir = sortDir === 'asc' ? 'desc' : 'asc';
    } else {
      sortCol = col;
      sortDir = col === 'ev_vs_pinnacle' || col === 'ev_vs_best' ? 'desc' : 'asc';
    }
    updateSortHeaders();
    renderTable();
  });
});

// ── Status bar ────────────────────────────────────────────────────────────────

function showStatus(msg, type = 'info') {
  const bar = document.getElementById('status-bar');
  bar.textContent = msg;
  bar.className = `status-bar ${type}`;
}

function hideStatus() {
  document.getElementById('status-bar').className = 'status-bar hidden';
}

// ── Data loading ──────────────────────────────────────────────────────────────

async function loadSports() {
  try {
    const res = await fetch('/api/sports');
    const data = await res.json();

    Object.assign(BOOK_NAMES, data.books || {});

    const sportSel = document.getElementById('sport-filter');
    (data.sports || []).forEach(s => {
      const opt = document.createElement('option');
      opt.value = s.key;
      opt.textContent = s.description;
      sportSel.appendChild(opt);
    });

    const bookSel = document.getElementById('book-filter');
    Object.entries(data.books || {}).forEach(([key, name]) => {
      const opt = document.createElement('option');
      opt.value = key;
      opt.textContent = name;
      bookSel.appendChild(opt);
    });
  } catch (e) {
    console.warn('Could not load sports metadata:', e);
  }
}

async function loadData(params = {}) {
  const qs = new URLSearchParams(params).toString();
  try {
    const res = await fetch(`/api/scan${qs ? '?' + qs : ''}`);
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || res.statusText);
    }
    const data = await res.json();
    allResults = data.results || [];

    // Scan time
    const scanTime = new Date(data.scan_time);
    document.getElementById('scan-time').textContent =
      `Scanned ${scanTime.toLocaleTimeString()}`;

    // Cache age summary
    const ages = data.cache_ages || {};
    const ageStr = Object.entries(ages)
      .map(([src, secs]) => `${src}: ${fmtAge(secs)}`)
      .join(' · ');
    if (ageStr) {
      document.getElementById('scan-time').textContent += ` · ${ageStr}`;
    }

    // Credits badge
    if (data.requests_remaining !== null && data.requests_remaining !== undefined) {
      document.getElementById('credits-badge').textContent =
        `${data.requests_remaining} API credits remaining`;
    }

    hideStatus();
    renderTable();
  } catch (e) {
    showStatus(`Error: ${e.message}`, 'error');
    document.getElementById('results-body').innerHTML =
      '<tr><td colspan="8" class="empty">Failed to load data. Check your .env configuration.</td></tr>';
  }
}

// ── Refresh button ────────────────────────────────────────────────────────────

document.getElementById('refresh-btn').addEventListener('click', async () => {
  const btn = document.getElementById('refresh-btn');
  btn.disabled = true;
  btn.textContent = '↻ Refreshing…';
  showStatus('Forcing refresh — fetching fresh data from all sources…', 'info');
  try {
    const res = await fetch('/api/refresh', { method: 'POST' });
    if (res.status === 429) {
      const err = await res.json();
      showStatus(err.detail, 'error');
      return;
    }
    await loadData();
  } catch (e) {
    showStatus(`Refresh failed: ${e.message}`, 'error');
  } finally {
    btn.disabled = false;
    btn.textContent = '↻ Refresh';
  }
});

// ── Filter controls ───────────────────────────────────────────────────────────

['sport-filter', 'method-filter', 'book-filter'].forEach(id => {
  document.getElementById(id).addEventListener('change', renderTable);
});

document.getElementById('positive-only').addEventListener('change', renderTable);

document.getElementById('min-ev').addEventListener('input', function () {
  const v = parseFloat(this.value);
  document.getElementById('min-ev-val').textContent = `${v >= 0 ? '+' : ''}${v}%`;
  renderTable();
});

// ── Init ──────────────────────────────────────────────────────────────────────

(async () => {
  updateSortHeaders();
  await loadSports();
  await loadData();
})();

// ── API base ──────────────────────────────────────────────────────────────────
export const API = {
  async get(path) {
    const r = await fetch(path);
    if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
    return r.json();
  },
  async post(path, body) {
    const r = await fetch(path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!r.ok) {
      const err = await r.json().catch(() => ({}));
      throw new Error(err.detail || `${r.status} ${r.statusText}`);
    }
    return r.json();
  },
  async patch(path, body) {
    const r = await fetch(path, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
    return r.json();
  },
  async del(path) {
    const r = await fetch(path, { method: 'DELETE' });
    if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
  },
};

// ── Toast ─────────────────────────────────────────────────────────────────────
export function toast(msg, type = 'info', duration = 3500) {
  const icons = { success: 'ph-check-circle', error: 'ph-x-circle', info: 'ph-info' };
  const el = document.createElement('div');
  el.className = `toast ${type}`;
  el.innerHTML = `<i class="ph ${icons[type] || icons.info}"></i><span>${msg}</span>`;
  document.getElementById('toast-container').appendChild(el);
  setTimeout(() => el.remove(), duration);
}

// ── Modal ─────────────────────────────────────────────────────────────────────
export function openModal(title, html, size = '') {
  const modal = document.getElementById('modal');
  modal.className = `modal ${size}`.trim();
  document.getElementById('modal-title').textContent = title;
  document.getElementById('modal-body').innerHTML = html;
  document.getElementById('modal-overlay').classList.remove('hidden');
}
export function closeModal() {
  document.getElementById('modal-overlay').classList.add('hidden');
  document.getElementById('modal-body').innerHTML = '';
  const modal = document.getElementById('modal');
  if (modal) modal.className = 'modal';
}

// ── Status helpers ────────────────────────────────────────────────────────────
export function statusChip(status) {
  const map = {
    UP:      '<span class="chip chip-up"><i class="ph ph-check-circle"></i>UP</span>',
    DOWN:    '<span class="chip chip-down"><i class="ph ph-x-circle"></i>DOWN</span>',
    UNKNOWN: '<span class="chip chip-unknown"><i class="ph ph-question"></i>UNKNOWN</span>',
  };
  return map[status] || map.UNKNOWN;
}

export function checkIcon(ok) {
  if (ok === true)  return '<span class="check-icon ok"><i class="ph ph-check-bold"></i></span>';
  if (ok === false) return '<span class="check-icon fail"><i class="ph ph-x-bold"></i></span>';
  return '<span class="check-icon warn"><i class="ph ph-minus"></i></span>';
}

export function timeAgo(iso) {
  if (!iso) return '—';
  const diff = (Date.now() - new Date(iso + (iso.endsWith('Z') ? '' : 'Z'))) / 1000;
  if (diff < 60)  return `${Math.floor(diff)}s ago`;
  if (diff < 3600) return `${Math.floor(diff/60)}m ago`;
  return `${Math.floor(diff/3600)}h ago`;
}

export function latencyColor(ms) {
  if (ms <= 0)   return 'var(--unknown)';
  if (ms < 20)   return 'var(--up)';
  if (ms < 100)  return 'var(--accent)';
  if (ms < 300)  return 'var(--amber)';
  return 'var(--down)';
}

export function latencyBars(history) {
  if (!history || history.length === 0) return '';
  const maxLat = Math.max(...history.filter(v => v > 0), 1);
  return history.map(v => {
    const h = v > 0 ? Math.max(15, (v / maxLat) * 100) : 100;
    const cls = v > 0 ? '' : ' down-bar';
    const pct = v > 0 ? `${v.toFixed(1)}ms` : 'DOWN';
    return `<span class="${cls}" style="height:${h}%;background:${v > 0 ? latencyColor(v) : 'var(--down)'}" title="${pct}"></span>`;
  }).join('');
}

export function deviceTypeIcon(type) {
  const map = {
    'Server':      'ph-hard-drives',
    'Workstation': 'ph-desktop-tower',
    'Laptop':      'ph-laptop',
    'Printer':     'ph-printer',
    'Switch':      'ph-git-fork',
    'Router':      'ph-router',
    'AP':          'ph-wifi-high',
    'Camera':      'ph-camera',
    'Phone':       'ph-phone',
    'Other':       'ph-cube',
  };
  return map[type] || 'ph-cube';
}

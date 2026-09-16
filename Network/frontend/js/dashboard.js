import { API, statusChip, timeAgo, latencyBars, latencyColor } from './utils.js';

let _charts = {};

export async function renderDashboard(container) {
  container.innerHTML = `
    <div class="page-header">
      <div>
        <h1>Network Dashboard</h1>
        <p>Live overview of all monitored devices</p>
      </div>
      <button class="btn btn-primary" id="dash-refresh"><i class="ph ph-arrows-clockwise"></i> Refresh</button>
    </div>

    <!-- Stats row -->
    <div class="grid-4" id="dash-stats">
      ${statSkeleton(4)}
    </div>

    <!-- Device grid -->
    <div class="section-divider">Monitored Devices</div>
    <div class="toolbar">
      <div class="search-box">
        <i class="ph ph-magnifying-glass"></i>
        <input type="text" id="dash-search" placeholder="Search by name, IP, group…" />
      </div>
      <select id="dash-filter-group" style="width:auto">
        <option value="">All Groups</option>
      </select>
      <select id="dash-filter-status" style="width:auto">
        <option value="">All Status</option>
        <option value="UP">UP</option>
        <option value="DOWN">DOWN</option>
        <option value="UNKNOWN">UNKNOWN</option>
      </select>
    </div>
    <div class="grid-auto" id="dash-device-grid">
      <div class="empty-state"><div class="spinner spinner-lg"></div></div>
    </div>
  `;

  document.getElementById('dash-refresh').addEventListener('click', () => loadData());

  // Filters
  ['dash-search','dash-filter-group','dash-filter-status'].forEach(id => {
    document.getElementById(id)?.addEventListener('input', applyFilters);
  });

  let _allDevices = [];

  async function loadData() {
    try {
      _allDevices = await API.get('/api/network/status/all');
      renderStats(_allDevices);
      populateGroupFilter(_allDevices);
      applyFilters();
    } catch(e) {
      document.getElementById('dash-device-grid').innerHTML =
        `<div class="empty-state"><i class="ph ph-warning-circle"></i><p>${e.message}</p></div>`;
    }
  }

  function renderStats(devices) {
    const total   = devices.length;
    const up      = devices.filter(d => d.status === 'UP').length;
    const down    = devices.filter(d => d.status === 'DOWN').length;
    const avgLat  = devices.filter(d => d.latency_ms > 0).reduce((s,d) => s+d.latency_ms, 0) /
                    (devices.filter(d => d.latency_ms > 0).length || 1);

    document.getElementById('dash-stats').innerHTML = `
      <div class="stat-card">
        <div class="stat-icon blue"><i class="ph ph-devices"></i></div>
        <div><div class="stat-value">${total}</div><div class="stat-label">Total Devices</div></div>
      </div>
      <div class="stat-card">
        <div class="stat-icon green"><i class="ph ph-check-circle"></i></div>
        <div><div class="stat-value" style="color:var(--up)">${up}</div><div class="stat-label">Online</div></div>
      </div>
      <div class="stat-card">
        <div class="stat-icon red"><i class="ph ph-x-circle"></i></div>
        <div><div class="stat-value" style="color:var(--down)">${down}</div><div class="stat-label">Offline</div></div>
      </div>
      <div class="stat-card">
        <div class="stat-icon amber"><i class="ph ph-activity"></i></div>
        <div><div class="stat-value" style="color:${latencyColor(avgLat)}">${avgLat.toFixed(1)}<small style="font-size:14px">ms</small></div><div class="stat-label">Avg Latency</div></div>
      </div>
    `;
  }

  function populateGroupFilter(devices) {
    const groups = [...new Set(devices.map(d => d.group_name).filter(Boolean))].sort();
    const sel = document.getElementById('dash-filter-group');
    const cur = sel.value;
    sel.innerHTML = `<option value="">All Groups</option>` +
      groups.map(g => `<option value="${g}" ${g===cur?'selected':''}>${g}</option>`).join('');
  }

  function applyFilters() {
    const search  = (document.getElementById('dash-search')?.value || '').toLowerCase();
    const group   = document.getElementById('dash-filter-group')?.value || '';
    const status  = document.getElementById('dash-filter-status')?.value || '';

    const filtered = _allDevices.filter(d =>
      (!search || d.name.toLowerCase().includes(search) || d.ip.includes(search) || (d.hostname||'').toLowerCase().includes(search)) &&
      (!group  || d.group_name === group) &&
      (!status || d.status === status)
    );

    renderDeviceGrid(filtered);
  }

  function renderDeviceGrid(devices) {
    const grid = document.getElementById('dash-device-grid');
    if (!devices.length) {
      grid.innerHTML = `<div class="empty-state" style="grid-column:1/-1"><i class="ph ph-desktop-tower"></i><p>No devices found</p></div>`;
      return;
    }
    grid.innerHTML = devices.map(d => deviceCard(d)).join('');
    // click -> detail modal
    grid.querySelectorAll('.device-card').forEach(card => {
      card.addEventListener('click', () => openDeviceDetail(card.dataset.id, _allDevices));
    });
  }

  loadData();

  // Listen for WS updates
  window._dashUpdate = (data) => {
    if (data.type === 'status_update') {
      _allDevices = data.devices;
      renderStats(_allDevices);
      applyFilters();
    }
  };
}

function deviceCard(d) {
  const statusClass = d.status === 'UP' ? 'status-up' : d.status === 'DOWN' ? 'status-down' : 'status-unknown';
  const dotClass    = d.status === 'UP' ? 'up' : d.status === 'DOWN' ? 'down' : 'unknown';
  const lat         = d.latency_ms > 0 ? `<span style="color:${latencyColor(d.latency_ms)};font-family:'JetBrains Mono',monospace;font-size:12px">${d.latency_ms.toFixed(1)}ms</span>` : '';
  return `
  <div class="device-card ${statusClass}" data-id="${d.id}">
    <div class="device-header">
      <div>
        <div class="device-name">${d.name}</div>
        <div class="device-ip">${d.ip}${d.hostname ? ` · ${d.hostname}` : ''}</div>
        <span class="device-type-tag">${d.device_type} · ${d.group_name}</span>
      </div>
      ${lat}
    </div>
    <div class="device-status">
      <span class="dot ${dotClass}"></span>
      ${d.status}
      <span style="color:var(--text-muted);font-size:11px;margin-left:auto">${timeAgo(d.last_seen)}</span>
    </div>
    <div class="latency-bar">${latencyBars(d.latency_history)}</div>
  </div>`;
}

async function openDeviceDetail(id, devices) {
  const d = devices.find(x => String(x.id) === String(id));
  if (!d) return;
  const { openModal } = await import('./utils.js');

  // Load history
  let history = [];
  try { history = await API.get(`/api/network/history/${d.id}?limit=50`); } catch(_) {}

  const upPct = history.length
    ? Math.round(history.filter(h => h.status === 'UP').length / history.length * 100) : 0;

  openModal(`${d.name} — Detail`, `
    <div style="display:flex;align-items:center;gap:14px;margin-bottom:16px">
      <div class="stat-icon blue" style="width:42px;height:42px"><i class="ph ph-desktop-tower"></i></div>
      <div>
        <div style="font-weight:700">${d.ip}</div>
        <div style="color:var(--text-muted);font-size:12px">${d.hostname || '—'}</div>
      </div>
      <div style="margin-left:auto">
        ${d.status === 'UP'
          ? `<span class="chip chip-up"><i class="ph ph-check-circle"></i>UP</span>`
          : `<span class="chip chip-down"><i class="ph ph-x-circle"></i>DOWN</span>`}
      </div>
    </div>
    <div class="grid-2" style="margin-bottom:16px">
      <div class="card" style="padding:12px">
        <div class="stat-label">Latency</div>
        <div style="font-size:20px;font-weight:700;color:${latencyColor(d.latency_ms)}">${d.latency_ms > 0 ? d.latency_ms.toFixed(1)+'ms' : '—'}</div>
      </div>
      <div class="card" style="padding:12px">
        <div class="stat-label">Uptime (last ${history.length} polls)</div>
        <div style="font-size:20px;font-weight:700;color:${upPct>80?'var(--up)':'var(--down)'}">${upPct}%</div>
      </div>
    </div>
    <canvas id="detail-chart" height="120"></canvas>
  `);

  // Chart
  const ctx = document.getElementById('detail-chart');
  if (ctx && history.length) {
    new Chart(ctx, {
      type: 'line',
      data: {
        labels: history.map(h => h.timestamp.slice(11,16)),
        datasets: [{
          label: 'Latency ms',
          data: history.map(h => h.status === 'UP' ? h.latency_ms : null),
          borderColor: '#4f8ef7',
          backgroundColor: 'rgba(79,142,247,0.1)',
          tension: 0.4, fill: true,
          pointRadius: 2,
          spanGaps: true,
        }]
      },
      options: {
        responsive: true,
        plugins: { legend: { display: false } },
        scales: {
          x: { ticks: { color: '#475569', maxTicksLimit: 8 }, grid: { color: 'rgba(255,255,255,0.04)' } },
          y: { ticks: { color: '#475569' }, grid: { color: 'rgba(255,255,255,0.04)' }, beginAtZero: true }
        }
      }
    });
  }
}

function statSkeleton(n) {
  return Array(n).fill('<div class="stat-card" style="opacity:.4"><div class="spinner"></div></div>').join('');
}

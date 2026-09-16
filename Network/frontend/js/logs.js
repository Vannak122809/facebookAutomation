import { API, toast, timeAgo } from './utils.js';

export async function renderLogs(container) {
  container.innerHTML = `
    <div class="page-header">
      <div><h1>Alerts</h1><p>Device downtime notifications and alert history</p></div>
      <div style="display:flex;gap:10px">
        <button class="btn btn-ghost" id="btn-ack-all"><i class="ph ph-checks"></i> Acknowledge All</button>
        <button class="btn btn-ghost" id="btn-refresh-alerts"><i class="ph ph-arrows-clockwise"></i> Refresh</button>
      </div>
    </div>

    <div class="toolbar">
      <label style="display:flex;align-items:center;gap:8px;cursor:pointer;font-size:13px;color:var(--text-secondary)">
        <input type="checkbox" id="unread-only" style="width:auto" />
        Show unread only
      </label>
    </div>

    <div id="alerts-list">
      <div class="empty-state"><div class="spinner spinner-lg"></div></div>
    </div>
  `;

  document.getElementById('btn-refresh-alerts').addEventListener('click', load);
  document.getElementById('btn-ack-all').addEventListener('click', async () => {
    try {
      await API.post('/api/logs/alerts/ack-all', {});
      toast('All alerts acknowledged', 'success');
      await load();
      updateBadge();
    } catch(e) { toast(e.message, 'error'); }
  });
  document.getElementById('unread-only').addEventListener('change', load);

  async function load() {
    const unreadOnly = document.getElementById('unread-only').checked;
    const list = document.getElementById('alerts-list');
    list.innerHTML = `<div class="empty-state"><div class="spinner spinner-lg"></div></div>`;
    try {
      const alerts = await API.get(`/api/logs/alerts?limit=100&unread_only=${unreadOnly}`);
      if (!alerts.length) {
        list.innerHTML = `
          <div class="empty-state">
            <i class="ph ph-bell-slash"></i>
            <p>${unreadOnly ? 'No unread alerts' : 'No alerts yet'}</p>
          </div>`;
        return;
      }
      list.innerHTML = alerts.map(a => alertRow(a)).join('');
      list.querySelectorAll('[data-ack-id]').forEach(btn => {
        btn.addEventListener('click', async () => {
          const id = +btn.dataset.ackId;
          try {
            await API.post(`/api/logs/alerts/${id}/ack`, {});
            const row = btn.closest('.alert-row');
            row.classList.add('acked');
            btn.remove();
            updateBadge();
          } catch(e) { toast(e.message, 'error'); }
        });
      });
    } catch(e) {
      list.innerHTML = `<div class="empty-state"><i class="ph ph-warning-circle"></i><p>${e.message}</p></div>`;
    }
  }

  load();
}

function alertRow(a) {
  const typeMap = {
    HOST_DOWN: { cls: 'host-down', icon: 'ph-wifi-x', label: 'Host Down' },
  };
  const t   = typeMap[a.alert_type] || { cls: 'host-down', icon: 'ph-warning', label: a.alert_type };
  const ack = a.acknowledged ? 'acked' : '';
  const btn = !a.acknowledged
    ? `<button class="btn btn-ghost btn-sm" data-ack-id="${a.id}" title="Acknowledge">
         <i class="ph ph-check"></i>
       </button>` : '';
  return `
    <div class="alert-row ${ack}">
      <div class="alert-icon ${t.cls}">
        <i class="ph ${t.icon}"></i>
      </div>
      <div style="flex:1">
        <div class="alert-msg">
          <strong>${a.device_name || 'System'}</strong> — ${a.message}
        </div>
        <div class="alert-time">
          ${t.label} · ${timeAgo(a.created_at)}
          ${a.acknowledged ? '<span style="color:var(--up);margin-left:8px"><i class="ph ph-check-circle"></i> Acknowledged</span>' : ''}
        </div>
      </div>
      ${btn}
    </div>`;
}

export async function updateBadge() {
  try {
    const r = await API.get('/api/logs/alerts/count');
    const badge = document.getElementById('alert-badge');
    if (badge) {
      badge.textContent = r.unread || '';
      badge.style.display = r.unread > 0 ? '' : 'none';
    }
  } catch(_) {}
}

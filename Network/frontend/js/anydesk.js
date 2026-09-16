import { API, toast, openModal, closeModal, timeAgo } from './utils.js';

export async function renderAnydesk(container) {
  container.innerHTML = `
    <div class="page-header">
      <div><h1>AnyDesk Remote Manager</h1><p>Connect to any remote computer · Manage saved remotes · Run diagnostics</p></div>
    </div>

    <!-- Sub-tabs -->
    <div class="ad-tabs" id="ad-tabs">
      ${[
        ['connect',    'ph-plug',           'Quick Connect'],
        ['saved',      'ph-bookmark-simple','Saved Remotes'],
        ['history',    'ph-clock-counter-clockwise','History'],
        ['diagnose',   'ph-stethoscope',    'Diagnostics'],
      ].map(([id,icon,label],i) => `
        <button class="ad-tab ${i===0?'active':''}" data-tab="${id}">
          <i class="ph ${icon}"></i> ${label}
        </button>`).join('')}
    </div>

    <!-- PANEL: Quick Connect -->
    <div class="ad-panel" id="panel-connect">
      <div style="display:flex;gap:20px;flex-wrap:wrap;align-items:flex-start">

        <!-- Connect form -->
        <div class="card" style="flex:1;min-width:300px;max-width:480px">
          <div class="card-header">
            <span class="card-title"><i class="ph ph-plug"></i> Connect to Remote</span>
          </div>
          <div class="form-group">
            <label>AnyDesk ID or Alias</label>
            <input id="conn-id" placeholder="e.g. 123 456 789 or user@ad" autofocus />
          </div>
          <div class="form-group">
            <label>Password <span style="color:var(--text-muted);font-size:11px">(optional — unattended access)</span></label>
            <div style="position:relative">
              <input type="password" id="conn-pw" placeholder="Leave blank for interactive session" style="padding-right:40px" />
              <button onclick="togglePw('conn-pw',this)" style="position:absolute;right:10px;top:50%;transform:translateY(-50%);background:none;border:none;color:var(--text-muted);font-size:16px">
                <i class="ph ph-eye"></i>
              </button>
            </div>
          </div>
          <div class="form-group">
            <label>Label <span style="color:var(--text-muted);font-size:11px">(for history)</span></label>
            <input id="conn-label" placeholder="e.g. Office PC, Boss Laptop…" />
          </div>
          <div style="display:flex;gap:10px;flex-wrap:wrap">
            <button class="btn btn-primary" id="btn-connect" style="flex:1">
              <i class="ph ph-arrow-square-out"></i> Connect Now
            </button>
            <button class="btn btn-ghost" id="btn-save-quick" style="flex:1">
              <i class="ph ph-bookmark-simple"></i> Save Remote
            </button>
          </div>
          <div id="connect-status" style="margin-top:14px"></div>
        </div>

        <!-- AnyDesk path info -->
        <div style="flex:1;min-width:260px">
          <div class="card" style="margin-bottom:14px" id="anydesk-path-card">
            <div class="card-header"><span class="card-title"><i class="ph ph-terminal"></i> AnyDesk Binary</span></div>
            <div id="anydesk-path-info" style="font-size:13px;color:var(--text-muted)">
              Checking…
            </div>
          </div>
          <div class="card">
            <div class="card-header"><span class="card-title"><i class="ph ph-info"></i> How it works</span></div>
            <div style="font-size:12px;color:var(--text-secondary);line-height:1.8">
              <div>① Enter the remote AnyDesk ID</div>
              <div>② Optionally set password for unattended access</div>
              <div>③ Click Connect — AnyDesk opens the session</div>
              <div style="margin-top:10px;color:var(--text-muted)">
                The app launches your local AnyDesk client. Make sure AnyDesk is installed on this machine.
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- PANEL: Saved Remotes -->
    <div class="ad-panel" id="panel-saved" style="display:none">
      <div class="page-header" style="margin-bottom:16px">
        <div style="flex:1"></div>
        <button class="btn btn-primary" id="btn-add-saved"><i class="ph ph-plus"></i> Add Remote</button>
      </div>
      <div class="toolbar">
        <div class="search-box">
          <i class="ph ph-magnifying-glass"></i>
          <input type="text" id="saved-search" placeholder="Search saved remotes…" />
        </div>
      </div>
      <div id="saved-grid" class="grid-auto">
        <div class="empty-state"><div class="spinner spinner-lg"></div></div>
      </div>
    </div>

    <!-- PANEL: History -->
    <div class="ad-panel" id="panel-history" style="display:none">
      <div style="display:flex;justify-content:flex-end;margin-bottom:14px;gap:10px">
        <button class="btn btn-ghost" id="btn-refresh-hist"><i class="ph ph-arrows-clockwise"></i> Refresh</button>
        <button class="btn btn-danger btn-sm" id="btn-clear-hist"><i class="ph ph-trash"></i> Clear</button>
      </div>
      <div class="card" style="padding:0">
        <div class="table-wrap">
          <table>
            <thead>
              <tr><th>ID / Target</th><th>Label</th><th>Status</th><th>Time</th><th>Error</th></tr>
            </thead>
            <tbody id="history-tbody">
              <tr><td colspan="5" style="text-align:center;padding:40px"><div class="spinner" style="margin:0 auto"></div></td></tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- PANEL: Diagnostics -->
    <div class="ad-panel" id="panel-diagnose" style="display:none">
      <div class="page-header" style="margin-bottom:16px">
        <div><p style="color:var(--text-secondary)">Analyze why AnyDesk can't connect to outside</p></div>
        <button class="btn btn-primary" id="btn-diagnose">
          <i class="ph ph-stethoscope"></i> Run Diagnostics
        </button>
      </div>
      <div class="card" style="margin-bottom:20px;display:none" id="score-banner">
        <div style="display:flex;align-items:center;gap:24px;flex-wrap:wrap">
          <div class="score-ring" id="score-ring">
            <svg width="100" height="100" viewBox="0 0 100 100">
              <circle cx="50" cy="50" r="42" fill="none" stroke="var(--bg-elevated)" stroke-width="10"/>
              <circle cx="50" cy="50" r="42" fill="none" stroke="var(--accent)" stroke-width="10"
                stroke-dasharray="264" stroke-dashoffset="264" id="score-arc" stroke-linecap="round"/>
            </svg>
            <div class="score-text"><span id="score-num">0</span><span class="score-label">/ 100</span></div>
          </div>
          <div style="flex:1">
            <div id="score-overall" style="font-size:20px;font-weight:700"></div>
            <div id="score-detail" style="color:var(--text-secondary);font-size:13px;margin-top:4px"></div>
            <div id="score-time" style="color:var(--text-muted);font-size:11px;margin-top:6px"></div>
          </div>
        </div>
      </div>
      <div id="diag-checks" style="margin-bottom:24px"></div>
      <div class="section-divider">AnyDesk Trace Log</div>
      <div class="card">
        <div class="card-header">
          <span class="card-title"><i class="ph ph-scroll"></i> ad.trace — Last 100 lines</span>
          <button class="btn btn-ghost btn-sm" id="btn-refresh-log"><i class="ph ph-arrows-clockwise"></i> Refresh</button>
        </div>
        <div class="log-viewer" id="anydesk-log">
          <span style="color:var(--text-muted)">Run diagnostics or click Refresh to load log…</span>
        </div>
      </div>
    </div>
  `;

  // ── Tab switching ─────────────────────────────────────────────────────────
  const tabs = document.querySelectorAll('.ad-tab');
  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      tabs.forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      document.querySelectorAll('.ad-panel').forEach(p => p.style.display = 'none');
      document.getElementById(`panel-${tab.dataset.tab}`).style.display = '';
      if (tab.dataset.tab === 'saved')   loadSaved();
      if (tab.dataset.tab === 'history') loadHistory();
    });
  });

  // ── Connect panel ─────────────────────────────────────────────────────────
  checkAnyDeskBinary();

  document.getElementById('btn-connect').addEventListener('click', doConnect);
  document.getElementById('conn-id').addEventListener('keydown', e => {
    if (e.key === 'Enter') doConnect();
  });

  document.getElementById('btn-save-quick').addEventListener('click', () => {
    const id = document.getElementById('conn-id').value.trim();
    if (!id) return toast('Enter an AnyDesk ID first', 'error');
    openSavedModal({ anydesk_id: id, name: document.getElementById('conn-label').value || id });
  });

  // ── Saved remotes ─────────────────────────────────────────────────────────
  document.getElementById('btn-add-saved').addEventListener('click', () => openSavedModal());
  document.getElementById('saved-search').addEventListener('input', e => filterSaved(e.target.value));

  // ── History ───────────────────────────────────────────────────────────────
  document.getElementById('btn-refresh-hist').addEventListener('click', loadHistory);
  document.getElementById('btn-clear-hist').addEventListener('click', async () => {
    if (!confirm('Clear all session history?')) return;
    await API.del('/api/anydesk/sessions');
    loadHistory();
    toast('History cleared', 'success');
  });

  // ── Diagnostics ───────────────────────────────────────────────────────────
  document.getElementById('btn-diagnose').addEventListener('click', runDiag);
  document.getElementById('btn-refresh-log').addEventListener('click', loadLog);

  // ── State ─────────────────────────────────────────────────────────────────
  let _savedAll = [];

  // ──────────────────────────────────────────────────────────────────────────
  // CONNECT
  // ──────────────────────────────────────────────────────────────────────────
  async function doConnect() {
    const id    = document.getElementById('conn-id').value.trim();
    const pw    = document.getElementById('conn-pw').value;
    const label = document.getElementById('conn-label').value.trim() || id;
    const status = document.getElementById('connect-status');

    if (!id) return toast('Enter an AnyDesk ID or alias', 'error');

    const btn = document.getElementById('btn-connect');
    btn.disabled = true;
    btn.innerHTML = `<div class="spinner" style="width:16px;height:16px;border-width:2px"></div> Connecting…`;
    status.innerHTML = '';

    try {
      const r = await API.post('/api/anydesk/connect', { anydesk_id: id, password: pw || null, label });
      status.innerHTML = `
        <div class="check-item">
          <div class="check-icon ok"><i class="ph ph-check-bold"></i></div>
          <div>
            <div class="check-title" style="color:var(--up)">AnyDesk launched</div>
            <div class="check-detail">Connecting to <strong>${id}</strong></div>
            <div class="check-detail" style="font-size:11px;color:var(--text-muted);margin-top:4px">Binary: ${r.anydesk_bin}</div>
          </div>
        </div>`;
      toast(`Connecting to ${id}…`, 'success');
    } catch(e) {
      const msg = e.message || 'Connection failed';
      status.innerHTML = `
        <div class="check-item">
          <div class="check-icon fail"><i class="ph ph-x-bold"></i></div>
          <div>
            <div class="check-title" style="color:var(--down)">Connection failed</div>
            <div class="check-detail">${msg}</div>
            ${msg.includes('not found') ? `<div class="check-fix"><i class="ph ph-wrench"></i>
              Install AnyDesk from <a href="https://anydesk.com/download" target="_blank" style="color:var(--accent)">anydesk.com/download</a>
            </div>` : ''}
          </div>
        </div>`;
      toast(msg, 'error');
    } finally {
      btn.disabled = false;
      btn.innerHTML = `<i class="ph ph-arrow-square-out"></i> Connect Now`;
    }
  }

  async function checkAnyDeskBinary() {
    const card = document.getElementById('anydesk-path-info');
    try {
      // Quick ping to diagnose endpoint which runs process check
      const r = await API.get('/api/anydesk/diagnose');
      const proc = r.process;
      if (proc?.ok) {
        card.innerHTML = `
          <div style="color:var(--up);font-weight:600;margin-bottom:6px">
            <i class="ph ph-check-circle"></i> AnyDesk is running
          </div>
          ${(proc.data||[]).map(p => `
            <div style="font-family:'JetBrains Mono',monospace;font-size:11px;color:var(--text-secondary)">
              PID ${p.pid} · ${p.name} · ${p.status}
            </div>`).join('')}`;
      } else {
        card.innerHTML = `<div style="color:var(--warn)"><i class="ph ph-warning"></i> AnyDesk process not running<br>
          <span style="font-size:11px;color:var(--text-muted)">Start AnyDesk before connecting</span></div>`;
      }
    } catch(e) {
      card.innerHTML = `<span style="color:var(--text-muted);font-size:12px">${e.message}</span>`;
    }
  }

  // ──────────────────────────────────────────────────────────────────────────
  // SAVED REMOTES
  // ──────────────────────────────────────────────────────────────────────────
  async function loadSaved() {
    const grid = document.getElementById('saved-grid');
    grid.innerHTML = `<div class="empty-state"><div class="spinner spinner-lg"></div></div>`;
    try {
      _savedAll = await API.get('/api/anydesk/saved');
      renderSavedGrid(_savedAll);
    } catch(e) { toast(e.message, 'error'); }
  }

  function filterSaved(q) {
    const lower = q.toLowerCase();
    renderSavedGrid(_savedAll.filter(r =>
      r.name.toLowerCase().includes(lower) ||
      r.anydesk_id.includes(lower) ||
      (r.description||'').toLowerCase().includes(lower)
    ));
  }

  function renderSavedGrid(remotes) {
    const grid = document.getElementById('saved-grid');
    if (!remotes.length) {
      grid.innerHTML = `<div class="empty-state" style="grid-column:1/-1">
        <i class="ph ph-bookmark-simple"></i>
        <p>No saved remotes yet. Add one above or save from Quick Connect.</p>
      </div>`;
      return;
    }
    grid.innerHTML = remotes.map(r => savedCard(r)).join('');
    // wire buttons
    grid.querySelectorAll('[data-connect-id]').forEach(btn => {
      btn.addEventListener('click', () => {
        // Pre-fill Quick Connect and switch tab
        switchToConnectWith(btn.dataset.connectId, btn.dataset.connectLabel);
      });
    });
    grid.querySelectorAll('[data-edit-id]').forEach(btn => {
      btn.addEventListener('click', () => {
        const r = _savedAll.find(x => String(x.id) === btn.dataset.editId);
        if (r) openSavedModal(r);
      });
    });
    grid.querySelectorAll('[data-del-id]').forEach(btn => {
      btn.addEventListener('click', async () => {
        if (!confirm(`Delete "${btn.dataset.delName}"?`)) return;
        await API.del(`/api/anydesk/saved/${btn.dataset.delId}`);
        _savedAll = _savedAll.filter(x => String(x.id) !== btn.dataset.delId);
        renderSavedGrid(_savedAll);
        toast('Deleted', 'success');
      });
    });
  }

  function savedCard(r) {
    return `
    <div class="device-card" style="cursor:default;border-left:3px solid var(--accent)">
      <div class="device-header">
        <div>
          <div class="device-name">${r.name}</div>
          <div class="device-ip" style="color:var(--accent)">${r.anydesk_id}</div>
          <span class="device-type-tag">${r.group_name}</span>
        </div>
        <div style="display:flex;flex-direction:column;gap:4px;align-items:flex-end">
          <button class="btn btn-primary btn-sm" data-connect-id="${r.anydesk_id}" data-connect-label="${r.name}">
            <i class="ph ph-plug"></i> Connect
          </button>
        </div>
      </div>
      ${r.description ? `<div style="margin-top:10px;font-size:12px;color:var(--text-muted)">${r.description}</div>` : ''}
      <div style="display:flex;gap:6px;margin-top:12px">
        <button class="btn btn-ghost btn-sm" data-edit-id="${r.id}"><i class="ph ph-pencil"></i> Edit</button>
        <button class="btn btn-danger btn-sm" data-del-id="${r.id}" data-del-name="${r.name}"><i class="ph ph-trash"></i></button>
      </div>
    </div>`;
  }

  function switchToConnectWith(id, label) {
    // Switch to Connect tab
    document.querySelector('[data-tab="connect"]').click();
    document.getElementById('conn-id').value = id;
    document.getElementById('conn-label').value = label || '';
    document.getElementById('conn-id').focus();
  }

  function openSavedModal(prefill = {}) {
    openModal(prefill.id ? 'Edit Saved Remote' : 'Add Saved Remote', `
      <form id="saved-form">
        <div class="form-group">
          <label>Name / Label *</label>
          <input name="name" required value="${prefill.name || ''}" placeholder="e.g. Office Desktop, Boss PC" />
        </div>
        <div class="form-group">
          <label>AnyDesk ID or Alias *</label>
          <input name="anydesk_id" required value="${prefill.anydesk_id || ''}" placeholder="e.g. 123 456 789" />
        </div>
        <div class="form-group">
          <label>Group</label>
          <input name="group_name" value="${prefill.group_name || 'General'}" placeholder="e.g. IT, Office, Home" />
        </div>
        <div class="form-group">
          <label>Description</label>
          <textarea name="description">${prefill.description || ''}</textarea>
        </div>
        <div class="form-actions">
          <button type="button" class="btn btn-ghost" id="saved-cancel">Cancel</button>
          <button type="submit" class="btn btn-primary"><i class="ph ph-check"></i> Save</button>
        </div>
      </form>
    `);
    document.getElementById('saved-cancel').addEventListener('click', closeModal);
    document.getElementById('saved-form').addEventListener('submit', async e => {
      e.preventDefault();
      const f = e.target;
      const body = {
        name:        f.name.value.trim(),
        anydesk_id:  f.anydesk_id.value.trim(),
        group_name:  f.group_name.value.trim() || 'General',
        description: f.description.value.trim(),
      };
      try {
        if (prefill.id) {
          const updated = await API.patch(`/api/anydesk/saved/${prefill.id}`, body);
          _savedAll = _savedAll.map(x => x.id === updated.id ? updated : x);
        } else {
          const created = await API.post('/api/anydesk/saved', body);
          _savedAll.unshift(created);
        }
        renderSavedGrid(_savedAll);
        closeModal();
        toast(prefill.id ? 'Updated' : 'Saved', 'success');
      } catch(err) { toast(err.message, 'error'); }
    });
  }

  // ──────────────────────────────────────────────────────────────────────────
  // HISTORY
  // ──────────────────────────────────────────────────────────────────────────
  async function loadHistory() {
    const tbody = document.getElementById('history-tbody');
    if (!tbody) return;
    tbody.innerHTML = `<tr><td colspan="5" style="text-align:center;padding:30px"><div class="spinner" style="margin:0 auto"></div></td></tr>`;
    try {
      const sessions = await API.get('/api/anydesk/sessions?limit=100');
      if (!sessions.length) {
        tbody.innerHTML = `<tr><td colspan="5"><div class="empty-state"><i class="ph ph-clock"></i><p>No session history yet</p></div></td></tr>`;
        return;
      }
      tbody.innerHTML = sessions.map(s => `
        <tr>
          <td><span class="mono" style="color:var(--accent)">${s.anydesk_id}</span></td>
          <td>${s.label || '—'}</td>
          <td>${s.status === 'launched'
            ? '<span class="chip chip-up"><i class="ph ph-check-circle"></i>Launched</span>'
            : '<span class="chip chip-down"><i class="ph ph-x-circle"></i>Error</span>'
          }</td>
          <td style="color:var(--text-muted);font-size:12px">${timeAgo(s.started_at)}</td>
          <td style="color:var(--down);font-size:12px">${s.error_msg || '—'}</td>
        </tr>`).join('');
    } catch(e) { toast(e.message, 'error'); }
  }

  // ──────────────────────────────────────────────────────────────────────────
  // DIAGNOSTICS (same as before)
  // ──────────────────────────────────────────────────────────────────────────
  async function runDiag() {
    const btn = document.getElementById('btn-diagnose');
    btn.disabled = true;
    btn.innerHTML = `<div class="spinner" style="width:16px;height:16px;border-width:2px"></div> Running…`;
    document.getElementById('diag-checks').innerHTML = loadingChecks();
    document.getElementById('score-banner').style.display = 'none';
    try {
      const r = await API.get('/api/anydesk/diagnose');
      renderChecks(r);
      renderScore(r.summary);
      await loadLog();
    } catch(e) {
      toast(e.message, 'error');
    } finally {
      btn.disabled = false;
      btn.innerHTML = `<i class="ph ph-stethoscope"></i> Run Diagnostics`;
    }
  }

  function loadingChecks() {
    return ['Process','Service','Relay Servers','Config','Log Analysis','NAT / Internet'].map(n =>
      `<div class="check-item">
        <div class="check-icon loading"><i class="ph ph-circle-notch"></i></div>
        <div><div class="check-title">${n}</div><div class="check-detail">Checking…</div></div>
      </div>`).join('');
  }

  function renderChecks(r) {
    const items = [
      checkItem('AnyDesk Process', r.process),
      checkItem('AnyDesk Service', r.service),
      checkItem('Internet / NAT', r.nat, r.nat?.external_ip ? `External IP: <strong>${r.nat.external_ip}</strong>` : null),
      relayCheck(r.relay),
      configCheck(r.config),
      logCheck(r.log),
    ];
    document.getElementById('diag-checks').innerHTML = items.join('');
  }

  function checkItem(title, check, extra = null) {
    if (!check) return '';
    const ok  = check.ok;
    const icon = ok === true ? 'check-bold' : ok === false ? 'x-bold' : 'minus';
    const cls  = ok === true ? 'ok' : ok === false ? 'fail' : 'warn';
    return `<div class="check-item">
      <div class="check-icon ${cls}"><i class="ph ph-${icon}"></i></div>
      <div style="flex:1">
        <div class="check-title">${title}</div>
        <div class="check-detail">${check.detail || ''}</div>
        ${extra ? `<div class="check-detail">${extra}</div>` : ''}
        ${check.fix ? `<div class="check-fix"><i class="ph ph-wrench"></i> Fix: ${check.fix}</div>` : ''}
      </div>
    </div>`;
  }

  function relayCheck(relay) {
    if (!relay) return '';
    const ok  = relay.ok; const cls = ok ? 'ok' : 'fail'; const ico = ok ? 'check-bold' : 'x-bold';
    const servers = (relay.servers||[]).map(s => `
      <div class="relay-row">
        <div class="relay-row-header">
          <span style="color:${s.ok?'var(--up)':'var(--down)'}"><i class="ph ph-${s.ok?'check-circle':'x-circle'}"></i></span>
          ${s.host} <span style="color:var(--text-muted);font-family:'JetBrains Mono',monospace;font-size:11px">${s.ip||''}</span>
        </div>
        <div class="relay-ports">
          ${(s.ports||[]).map(p => `<span class="port-chip ${p.open?'open':'closed'}" title="${p.error||''}">
            ${p.open?'<i class="ph ph-lock-open"></i>':'<i class="ph ph-lock"></i>'} :${p.port}</span>`).join('')}
        </div>
        ${!s.ok && s.fix ? `<div class="check-fix" style="margin-top:8px"><i class="ph ph-wrench"></i> ${s.fix}</div>` : ''}
      </div>`).join('');
    return `<div class="check-item" style="flex-direction:column;align-items:flex-start">
      <div style="display:flex;align-items:center;gap:14px;width:100%">
        <div class="check-icon ${cls}"><i class="ph ph-${ico}"></i></div>
        <div style="flex:1">
          <div class="check-title">AnyDesk Relay Servers</div>
          <div class="check-detail">${relay.detail}</div>
          ${!ok && relay.fix ? `<div class="check-fix"><i class="ph ph-wrench"></i> ${relay.fix}</div>` : ''}
        </div>
      </div>
      <div style="width:100%;margin-top:10px;padding-left:46px">${servers}</div>
    </div>`;
  }

  function configCheck(cfg) {
    if (!cfg) return '';
    const ok=cfg.ok; const cls=ok===true?'ok':ok===false?'fail':'warn'; const ico=ok===true?'check-bold':ok===false?'x-bold':'minus';
    const entries = cfg.data && Object.keys(cfg.data).length
      ? `<div style="margin-top:8px;font-family:'JetBrains Mono',monospace;font-size:11px;color:var(--text-secondary)">
          ${Object.entries(cfg.data).slice(0,12).map(([k,v])=>`<div><span style="color:var(--accent)">${k}</span> = ${v}</div>`).join('')}</div>` : '';
    return `<div class="check-item">
      <div class="check-icon ${cls}"><i class="ph ph-${ico}"></i></div>
      <div style="flex:1"><div class="check-title">AnyDesk Configuration</div>
        <div class="check-detail">${cfg.detail}</div>${entries}
        ${cfg.fix ? `<div class="check-fix"><i class="ph ph-wrench"></i> ${cfg.fix}</div>` : ''}</div>
    </div>`;
  }

  function logCheck(log) {
    if (!log) return '';
    const ok=log.ok; const cls=ok===true?'ok':ok===false?'fail':'warn'; const ico=ok===true?'check-bold':ok===false?'x-bold':'minus';
    const errors=(log.errors||[]).slice(0,5).map(e=>`<div class="check-fix"><i class="ph ph-warning"></i> <strong>${e.issue}</strong>: ${e.fix}</div>`).join('');
    return `<div class="check-item">
      <div class="check-icon ${cls}"><i class="ph ph-${ico}"></i></div>
      <div style="flex:1"><div class="check-title">Log Analysis</div>
        <div class="check-detail">${log.detail}</div>
        ${log.log_path?`<div style="font-size:11px;color:var(--text-muted);margin-top:4px;font-family:'JetBrains Mono',monospace">${log.log_path}</div>`:''}
        ${errors}</div>
    </div>`;
  }

  function renderScore(summary) {
    if (!summary) return;
    document.getElementById('score-banner').style.display = '';
    document.getElementById('score-num').textContent = summary.score;
    const arc   = document.getElementById('score-arc');
    const color = summary.score >= 85 ? 'var(--up)' : summary.score >= 50 ? 'var(--amber)' : 'var(--down)';
    arc.style.stroke = color;
    arc.style.transition = 'stroke-dashoffset 1s ease';
    setTimeout(() => { arc.style.strokeDashoffset = 264 - (summary.score/100)*264; }, 50);
    const el = document.getElementById('score-overall');
    el.textContent = summary.overall; el.style.color = color;
    document.getElementById('score-detail').textContent = `${summary.passed} of ${summary.total} checks passed`;
    document.getElementById('score-time').textContent = `Checked at ${new Date(summary.timestamp+'Z').toLocaleTimeString()}`;
  }

  async function loadLog() {
    const logEl = document.getElementById('anydesk-log');
    if (!logEl) return;
    logEl.innerHTML = '<span style="color:var(--text-muted)">Loading…</span>';
    try {
      const r = await API.get('/api/anydesk/log?lines=100');
      if (!r.lines.length) { logEl.innerHTML = '<span style="color:var(--text-muted)">Log file empty or not found.</span>'; return; }
      logEl.innerHTML = r.lines.map(line => {
        const cls = /error|fail|refused|block|timeout/i.test(line) ? 'error' : /warn|retry/i.test(line) ? 'warn' : '';
        return `<div class="log-line ${cls}">${esc(line)}</div>`;
      }).join('');
      logEl.scrollTop = logEl.scrollHeight;
    } catch(e) { logEl.innerHTML = `<span style="color:var(--down)">${e.message}</span>`; }
  }
}

// ── Global helpers ─────────────────────────────────────────────────────────────
window.togglePw = (inputId, btn) => {
  const input = document.getElementById(inputId);
  const isText = input.type === 'text';
  input.type = isText ? 'password' : 'text';
  btn.innerHTML = `<i class="ph ph-${isText ? 'eye' : 'eye-slash'}"></i>`;
};

function esc(s) {
  return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

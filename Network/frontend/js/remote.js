import { API, toast, openModal, closeModal, timeAgo } from './utils.js';

// Track open terminal instances so we can dispose them
const _terminals = new Map();

export async function renderRemote(container) {
  container.innerHTML = `
    <div class="page-header">
      <div>
        <h1>Self-Hosted Remote Manager</h1>
        <p>In-Browser Remote Desktop (Local Agent Hub) · SSH &amp; VNC · Self-Hosted RustDesk</p>
      </div>
      <div style="display:flex;gap:10px">
        <button class="btn btn-primary" id="btn-add-session"><i class="ph ph-plus"></i> Add SSH/VNC</button>
      </div>
    </div>

    <!-- Sub-tabs -->
    <div class="ad-tabs" id="remote-sub-tabs">
      ${[
        ['agent-hub', 'ph-monitor-play', 'Live Local Desktops (Agent Hub)'],
        ['ssh-vnc',   'ph-terminal',     'Saved SSH / VNC Sessions'],
        ['rustdesk',  'ph-hard-drive',   'Self-Hosted RustDesk Setup'],
      ].map(([id, icon, label], i) => `
        <button class="ad-tab ${i===0?'active':''}" data-tab="${id}">
          <i class="ph ${icon}"></i> ${label}
        </button>`).join('')}
    </div>

    <!-- ═══════════════════════════════════════════════════════════════════
         PANEL 1: Live Local Desktop Agents Hub
         ═══════════════════════════════════════════════════════════════════ -->
    <div class="remote-panel" id="panel-agent-hub">
      
      <!-- Deployment Helper Banner -->
      <div class="card" style="margin-bottom:20px;border-left:3px solid var(--accent)">
        <div class="card-header">
          <span class="card-title"><i class="ph ph-lightning"></i> Deploy Agent to Target Computer (Windows, Mac, Linux)</span>
          <button class="btn btn-ghost btn-sm" id="btn-refresh-agents"><i class="ph ph-arrows-clockwise"></i> Refresh Agents</button>
        </div>
        <p style="font-size:12px;color:var(--text-secondary);margin-bottom:10px">
          Run this single command on any PC in your local network to stream its screen and control it directly in this browser:
        </p>
        <div style="display:flex;gap:8px;align-items:center;background:var(--bg-base);padding:8px 12px;border-radius:var(--radius-sm);border:1px solid var(--border)">
          <code class="mono" id="agent-cmd" style="flex:1;color:var(--up);font-size:12px">
            curl -s http://${location.host}/api/local-remote/agent.py | python3
          </code>
          <button class="btn btn-ghost btn-sm" id="btn-copy-cmd"><i class="ph ph-copy"></i> Copy</button>
        </div>
      </div>

      <!-- Live Agents Grid -->
      <div class="section-divider">Online Local Computers</div>
      <div id="live-agents-grid" class="grid-auto">
        <div class="empty-state"><div class="spinner spinner-lg"></div></div>
      </div>

      <!-- Active In-App Desktop Canvas Viewer -->
      <div id="agent-active-viewer" style="display:none;margin-top:24px">
        <div class="card" style="padding:0;overflow:hidden">
          <div class="rs-session-bar">
            <div style="display:flex;align-items:center;gap:10px">
              <div class="status-dot connected" id="agent-dot"></div>
              <span id="agent-view-title" style="font-weight:600;font-size:14px">Desktop Viewer</span>
              <span id="agent-view-stats" style="font-size:12px;color:var(--text-muted)"></span>
            </div>
            <div style="display:flex;gap:8px;align-items:center">
              <label style="font-size:12px;display:flex;align-items:center;gap:6px;cursor:pointer;color:var(--text-secondary)">
                <input type="checkbox" id="agent-enable-input" checked style="width:auto" />
                Enable Mouse &amp; Keyboard Control
              </label>
              <button class="btn btn-ghost btn-sm" id="agent-fullscreen-btn"><i class="ph ph-arrows-out"></i> Fullscreen</button>
              <button class="btn btn-danger btn-sm" id="agent-disconnect-btn"><i class="ph ph-x-circle"></i> Close Stream</button>
            </div>
          </div>
          <div style="background:#0a0d16;display:flex;justify-content:center;align-items:center;min-height:540px;position:relative;user-select:none" id="agent-canvas-container">
            <canvas id="agent-canvas" style="max-width:100%;max-height:80vh;display:block;cursor:crosshair"></canvas>
            <div id="agent-loading-overlay" style="position:absolute;inset:0;display:flex;align-items:center;justify-content:center;background:rgba(10,13,22,0.85);color:var(--text-muted)">
              <div style="text-align:center"><div class="spinner spinner-lg" style="margin:0 auto 12px"></div>Connecting to live screen stream…</div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- ═══════════════════════════════════════════════════════════════════
         PANEL 2: Saved SSH / VNC Sessions
         ═══════════════════════════════════════════════════════════════════ -->
    <div class="remote-panel" id="panel-ssh-vnc" style="display:none">
      <div class="toolbar">
        <div class="search-box">
          <i class="ph ph-magnifying-glass"></i>
          <input type="text" id="rs-search" placeholder="Search sessions…" />
        </div>
        <select id="rs-filter" style="width:auto">
          <option value="">All Types</option>
          <option value="ssh">SSH</option>
          <option value="vnc">VNC</option>
        </select>
      </div>

      <!-- Session cards grid -->
      <div id="rs-grid" class="grid-auto">
        <div class="empty-state"><div class="spinner spinner-lg"></div></div>
      </div>

      <!-- Active terminal/VNC area -->
      <div id="rs-active-area" style="display:none;margin-top:24px">
        <div class="card" style="padding:0;overflow:hidden">
          <div class="rs-session-bar">
            <div style="display:flex;align-items:center;gap:10px">
              <div class="status-dot connected" id="rs-conn-dot"></div>
              <span id="rs-session-label" style="font-weight:600;font-size:14px">Session</span>
              <span id="rs-session-info" style="font-size:12px;color:var(--text-muted)"></span>
            </div>
            <div style="display:flex;gap:8px">
              <button class="btn btn-ghost btn-sm" id="rs-fullscreen-btn"><i class="ph ph-arrows-out"></i> Fullscreen</button>
              <button class="btn btn-danger btn-sm" id="rs-disconnect-btn"><i class="ph ph-x-circle"></i> Disconnect</button>
            </div>
          </div>
          <!-- SSH terminal -->
          <div id="rs-terminal-wrap" style="display:none;background:#0a0d16;padding:8px">
            <div id="rs-terminal"></div>
          </div>
          <!-- VNC viewer -->
          <div id="rs-vnc-wrap" style="display:none;background:#111;min-height:500px;position:relative">
            <canvas id="rs-vnc-canvas" style="display:block;margin:0 auto"></canvas>
            <div id="rs-vnc-status" style="position:absolute;inset:0;display:flex;align-items:center;justify-content:center;font-size:14px;color:var(--text-muted)">
              <div style="text-align:center"><div class="spinner spinner-lg" style="margin:0 auto 12px"></div>Connecting to VNC…</div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- ═══════════════════════════════════════════════════════════════════
         PANEL 3: Self-Hosted RustDesk Manager
         ═══════════════════════════════════════════════════════════════════ -->
    <div class="remote-panel" id="panel-rustdesk" style="display:none">
      <div class="card" style="margin-bottom:20px">
        <div class="card-header">
          <span class="card-title"><i class="ph ph-shield"></i> Self-Host Your Own RustDesk Relay &amp; Rendezvous Server</span>
        </div>
        <p style="font-size:13px;color:var(--text-secondary);margin-bottom:14px">
          RustDesk is a 100% open-source, private alternative to AnyDesk/TeamViewer. You can run your own local relay server on your LAN or cloud VPS with zero dependency on third parties.
        </p>
        <div class="form-group" style="max-width:380px">
          <label>Your Local Server IP / Domain</label>
          <div style="display:flex;gap:8px">
            <input id="rd-server-ip" value="${location.hostname}" placeholder="192.168.1.100" />
            <button class="btn btn-primary" id="btn-generate-rd">Generate Config</button>
          </div>
        </div>
      </div>

      <div id="rd-compose-result"></div>
    </div>
  `;

  // ── Tab switching ─────────────────────────────────────────────────────────
  const tabs = document.querySelectorAll('#remote-sub-tabs .ad-tab');
  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      tabs.forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      document.querySelectorAll('.remote-panel').forEach(p => p.style.display = 'none');
      const target = document.getElementById(`panel-${tab.dataset.tab}`);
      if (target) target.style.display = '';
      if (tab.dataset.tab === 'agent-hub') loadLiveAgents();
      if (tab.dataset.tab === 'ssh-vnc') loadSessions();
      if (tab.dataset.tab === 'rustdesk') generateRustDeskConfig();
    });
  });

  // Copy agent command
  document.getElementById('btn-copy-cmd').addEventListener('click', () => {
    const txt = document.getElementById('agent-cmd').innerText.trim();
    navigator.clipboard.writeText(txt);
    toast('Copied agent launch command!', 'success');
  });

  // ═══════════════════════════════════════════════════════════════════════════
  // 1. LIVE AGENTS HUB & STREAM VIEWER
  // ═══════════════════════════════════════════════════════════════════════════
  document.getElementById('btn-refresh-agents').addEventListener('click', loadLiveAgents);
  let _agentWs = null;

  async function loadLiveAgents() {
    const grid = document.getElementById('live-agents-grid');
    grid.innerHTML = `<div class="empty-state"><div class="spinner spinner-lg"></div></div>`;
    try {
      const agents = await API.get('/api/local-remote/agents');
      if (!agents.length) {
        grid.innerHTML = `
          <div class="empty-state" style="grid-column:1/-1">
            <i class="ph ph-monitor-play" style="font-size:40px;opacity:0.3"></i>
            <p style="margin-top:8px">No local agents streaming right now.</p>
            <p style="font-size:12px;color:var(--text-muted);margin-top:4px">Run the deploy command above on any PC to see it appear here live.</p>
          </div>`;
        return;
      }
      grid.innerHTML = agents.map(a => `
        <div class="device-card status-up">
          <div class="device-header">
            <div>
              <div class="device-name">${a.name}</div>
              <div class="device-ip">${a.hostname}</div>
              <span class="device-type-tag">${a.os}</span>
            </div>
            <span class="chip chip-up"><i class="ph ph-check-circle"></i>LIVE</span>
          </div>
          <div style="font-size:11px;color:var(--text-muted);margin-top:10px">
            Control: ${a.input_supported ? '<strong style="color:var(--up)">Interactive (Mouse &amp; Keys)</strong>' : 'View-Only'}
          </div>
          <button class="btn btn-primary btn-sm" style="margin-top:12px;width:100%;justify-content:center"
            onclick="window._viewAgent('${a.agent_id}', '${a.name}')">
            <i class="ph ph-play"></i> Stream &amp; Control Desktop
          </button>
        </div>
      `).join('');
    } catch(e) {
      grid.innerHTML = `<div class="empty-state" style="grid-column:1/-1;color:var(--down)">${e.message}</div>`;
    }
  }

  window._viewAgent = (agentId, agentName) => {
    if (_agentWs) { _agentWs.close(); _agentWs = null; }

    const viewer = document.getElementById('agent-active-viewer');
    const overlay = document.getElementById('agent-loading-overlay');
    const canvas = document.getElementById('agent-canvas');
    const ctx = canvas.getContext('2d');
    const stats = document.getElementById('agent-view-stats');

    viewer.style.display = '';
    overlay.style.display = 'flex';
    document.getElementById('agent-view-title').textContent = `${agentName} (${agentId})`;
    viewer.scrollIntoView({ behavior: 'smooth' });

    const wsUrl = `ws://${location.host}/api/local-remote/ws/viewer/${agentId}`;
    const ws = new WebSocket(wsUrl);
    ws.binaryType = 'arraybuffer';
    _agentWs = ws;

    let frameCount = 0;
    let lastFpsTime = Date.now();
    let currentFps = 0;

    ws.onopen = () => {
      document.getElementById('agent-dot').className = 'status-dot connected';
    };

    ws.onmessage = (event) => {
      if (typeof event.data === 'string') {
        const msg = JSON.parse(event.data);
        if (msg.type === 'agent_offline') {
          toast('Remote computer disconnected', 'error');
          overlay.style.display = 'flex';
          overlay.innerHTML = '<div style="color:var(--down)">Agent disconnected / went offline</div>';
        }
      } else {
        // Binary frame: 4 bytes header len + header json + JPEG data
        overlay.style.display = 'none';
        const buffer = event.data;
        const view = new DataView(buffer);
        const headerLen = view.getUint32(0);
        
        const headerBytes = new Uint8Array(buffer, 4, headerLen);
        const headerStr = new TextDecoder().decode(headerBytes);
        const meta = JSON.parse(headerStr);

        const imgBytes = new Uint8Array(buffer, 4 + headerLen);
        const blob = new Blob([imgBytes], { type: 'image/jpeg' });
        const url = URL.createObjectURL(blob);
        const img = new Image();
        img.onload = () => {
          if (canvas.width !== meta.w || canvas.height !== meta.h) {
            canvas.width = meta.w;
            canvas.height = meta.h;
          }
          ctx.drawImage(img, 0, 0);
          URL.revokeObjectURL(url);
          
          frameCount++;
          const now = Date.now();
          if (now - lastFpsTime >= 1000) {
            currentFps = frameCount;
            frameCount = 0;
            lastFpsTime = now;
            stats.textContent = `${meta.w}x${meta.h} · ${currentFps} FPS`;
          }
        };
        img.src = url;
      }
    };

    ws.onclose = () => {
      document.getElementById('agent-dot').className = 'status-dot disconnected';
    };

    // Mouse & Keyboard Input Dispatcher
    canvas.onmousemove = (e) => {
      if (!document.getElementById('agent-enable-input').checked) return;
      if (ws.readyState !== WebSocket.OPEN) return;
      const rect = canvas.getBoundingClientRect();
      const normX = (e.clientX - rect.left) / rect.width;
      const normY = (e.clientY - rect.top) / rect.height;
      ws.send(JSON.stringify({ type: 'mouse_move', x: normX, y: normY }));
    };

    canvas.onmousedown = (e) => {
      if (!document.getElementById('agent-enable-input').checked) return;
      if (ws.readyState !== WebSocket.OPEN) return;
      const btn = e.button === 2 ? 'right' : (e.button === 1 ? 'middle' : 'left');
      ws.send(JSON.stringify({ type: 'mouse_down', button: btn }));
    };

    canvas.onmouseup = (e) => {
      if (!document.getElementById('agent-enable-input').checked) return;
      if (ws.readyState !== WebSocket.OPEN) return;
      const btn = e.button === 2 ? 'right' : (e.button === 1 ? 'middle' : 'left');
      ws.send(JSON.stringify({ type: 'mouse_up', button: btn }));
    };

    canvas.oncontextmenu = (e) => e.preventDefault();

    window.onkeydown = (e) => {
      if (viewer.style.display === 'none') return;
      if (!document.getElementById('agent-enable-input').checked) return;
      if (ws.readyState !== WebSocket.OPEN) return;
      if (document.activeElement.tagName === 'INPUT' || document.activeElement.tagName === 'TEXTAREA') return;

      if (e.key.length === 1) {
        ws.send(JSON.stringify({ type: 'write', text: e.key }));
      } else {
        const keyMap = { 'Enter': 'enter', 'Backspace': 'backspace', 'Tab': 'tab', 'Escape': 'esc', 'ArrowUp': 'up', 'ArrowDown': 'down', 'ArrowLeft': 'left', 'ArrowRight': 'right' };
        if (keyMap[e.key]) {
          ws.send(JSON.stringify({ type: 'key', key: keyMap[e.key] }));
        }
      }
    };
  };

  document.getElementById('agent-disconnect-btn').addEventListener('click', () => {
    if (_agentWs) { _agentWs.close(); _agentWs = null; }
    document.getElementById('agent-active-viewer').style.display = 'none';
  });

  document.getElementById('agent-fullscreen-btn').addEventListener('click', () => {
    const el = document.getElementById('agent-canvas-container');
    if (!document.fullscreenElement) el.requestFullscreen?.();
    else document.exitFullscreen?.();
  });

  // ═══════════════════════════════════════════════════════════════════════════
  // 2. SAVED SSH / VNC SESSIONS
  // ═══════════════════════════════════════════════════════════════════════════
  document.getElementById('btn-add-session').addEventListener('click', () => openSessionModal());
  document.getElementById('rs-search').addEventListener('input', e => filterSessions(e.target.value));
  document.getElementById('rs-filter').addEventListener('change', () => filterSessions(document.getElementById('rs-search').value));
  document.getElementById('rs-disconnect-btn').addEventListener('click', disconnectSshVnc);
  document.getElementById('rs-fullscreen-btn').addEventListener('click', () => {
    const area = document.getElementById('rs-active-area').querySelector('.card');
    if (!document.fullscreenElement) area.requestFullscreen?.();
    else document.exitFullscreen?.();
  });

  let _sessions = [];
  let _activeWs = null;
  let _activeTerm = null;

  async function loadSessions() {
    try {
      _sessions = await API.get('/api/remote/sessions');
      filterSessions('');
    } catch(e) {
      document.getElementById('rs-grid').innerHTML = `<div class="empty-state"><i class="ph ph-warning-circle"></i><p>${e.message}</p></div>`;
    }
  }

  function filterSessions(q) {
    const lower = q.toLowerCase();
    const type  = document.getElementById('rs-filter').value;
    const filtered = _sessions.filter(s =>
      (!type || s.session_type === type) &&
      (!lower || s.name.toLowerCase().includes(lower) || s.host.includes(lower))
    );
    renderSessionGrid(filtered);
  }

  function renderSessionGrid(sessions) {
    const grid = document.getElementById('rs-grid');
    if (!sessions.length) {
      grid.innerHTML = `<div class="empty-state" style="grid-column:1/-1"><i class="ph ph-terminal"></i><p>No SSH, VNC, or RDP sessions saved yet.</p></div>`;
      return;
    }
    grid.innerHTML = sessions.map(s => {
      const typeColor = s.session_type === 'ssh' ? 'var(--up)' : (s.session_type === 'rdp' ? 'var(--accent)' : 'var(--purple)');
      const typeIcon  = s.session_type === 'ssh' ? 'ph-terminal' : (s.session_type === 'rdp' ? 'ph-windows-logo' : 'ph-monitor');
      
      const connectBtn = s.session_type === 'rdp'
        ? `<div style="display:flex;gap:6px;width:100%">
             <button class="btn btn-primary btn-sm" style="flex:1;justify-content:center" onclick="window._launchRdp('${s.host}', ${s.port}, '${s.username||''}')">
               <i class="ph ph-arrow-square-out"></i> Launch RDP
             </button>
             <a class="btn btn-ghost btn-sm" href="/api/remote/rdp/download?host=${encodeURIComponent(s.host)}&username=${encodeURIComponent(s.username||'')}&port=${s.port}" download title="Download .rdp file">
               <i class="ph ph-download-simple"></i> .rdp
             </a>
           </div>`
        : `<button class="btn btn-primary btn-sm" onclick="window._launchSshVnc(${s.id})" style="flex:1;justify-content:center">
             <i class="ph ph-play"></i> Connect
           </button>`;

      return `
        <div class="device-card" style="border-left:3px solid ${typeColor}">
          <div class="device-header">
            <div>
              <div class="device-name">${s.name}</div>
              <div class="device-ip">${s.username ? s.username+'@' : ''}${s.host}:${s.port}</div>
              <span class="device-type-tag">${s.group_name} · ${s.session_type.toUpperCase()}</span>
            </div>
            <div style="font-size:22px;color:${typeColor}"><i class="ph ${typeIcon}"></i></div>
          </div>
          <div style="display:flex;gap:6px;margin-top:14px;flex-wrap:wrap">
            ${connectBtn}
            <button class="btn btn-ghost btn-sm" onclick="window._editSshVnc(${s.id})"><i class="ph ph-pencil"></i></button>
            <button class="btn btn-danger btn-sm" onclick="window._delSshVnc(${s.id},'${s.name}')"><i class="ph ph-trash"></i></button>
          </div>
        </div>`;
    }).join('');
  }

  window._launchRdp = async (host, port, username) => {
    try {
      const r = await API.post(`/api/remote/rdp/launch?host=${encodeURIComponent(host)}&port=${port}&username=${encodeURIComponent(username)}`, {});
      toast(r.message || 'Launched Remote Desktop', 'success');
    } catch(e) {
      // If native launch fails (e.g. browser security), fallback to download
      window.location.href = `/api/remote/rdp/download?host=${encodeURIComponent(host)}&username=${encodeURIComponent(username)}&port=${port}`;
      toast('Downloaded .rdp file — opening connection', 'info');
    }
  };

  window._launchSshVnc = (id) => {
    const s = _sessions.find(x => x.id === id);
    if (!s) return;
    disconnectSshVnc();

    document.getElementById('rs-active-area').style.display = '';
    document.getElementById('rs-session-label').textContent = s.name;
    document.getElementById('rs-session-info').textContent = `${s.session_type.toUpperCase()} · ${s.host}:${s.port}`;
    document.getElementById('rs-conn-dot').className = 'status-dot';

    if (s.session_type === 'ssh') {
      const termWrap = document.getElementById('rs-terminal-wrap');
      const vncWrap  = document.getElementById('rs-vnc-wrap');
      termWrap.style.display = ''; vncWrap.style.display = 'none';
      const termEl = document.getElementById('rs-terminal');
      termEl.innerHTML = '';

      const term = new window.Terminal({
        theme: { background: '#0a0d16', foreground: '#c8d3f5', cursor: '#4f8ef7' },
        fontFamily: "'JetBrains Mono', monospace",
        fontSize: 14, cursorBlink: true,
      });
      const fitAddon = new window.FitAddon.FitAddon();
      term.loadAddon(fitAddon);
      term.open(termEl);
      fitAddon.fit();
      _activeTerm = term;

      const ws = new WebSocket(`ws://${location.host}/api/remote/ws/ssh/${s.id}`);
      _activeWs = ws;
      ws.onopen = () => { document.getElementById('rs-conn-dot').className = 'status-dot connected'; term.focus(); };
      ws.onmessage = (e) => term.write(e.data);
      ws.onclose = () => { document.getElementById('rs-conn-dot').className = 'status-dot disconnected'; term.write('\r\n\x1b[33m[Disconnected]\x1b[0m\r\n'); };
      term.onData(data => { if (ws.readyState === WebSocket.OPEN) ws.send(data); });
    }
    document.getElementById('rs-active-area').scrollIntoView({ behavior: 'smooth' });
  };

  window._editSshVnc = (id) => {
    const s = _sessions.find(x => x.id === id);
    if (s) openSessionModal(s);
  };

  window._delSshVnc = async (id, name) => {
    if (!confirm(`Delete session "${name}"?`)) return;
    await API.del(`/api/remote/sessions/${id}`);
    _sessions = _sessions.filter(x => x.id !== id);
    filterSessions('');
    toast('Session deleted', 'success');
  };

  function disconnectSshVnc() {
    if (_activeWs) { try { _activeWs.close(); } catch(_) {} _activeWs = null; }
    if (_activeTerm) { try { _activeTerm.dispose(); } catch(_) {} _activeTerm = null; }
    document.getElementById('rs-active-area').style.display = 'none';
  }

  function openSessionModal(s = {}) {
    const isEdit = !!s.id;
    openModal(isEdit ? 'Edit Session' : 'New SSH / VNC Session', `
      <form id="rs-form">
        <div class="form-group">
          <label>Session Name *</label>
          <input name="name" required value="${s.name||''}" placeholder="e.g. Linux Main Server" />
        </div>
        <div class="form-row">
          <div class="form-group">
            <label>Type</label>
            <select name="session_type" onchange="const p=this.form.port; if(this.value==='ssh')p.value=22; else if(this.value==='vnc')p.value=5900; else if(this.value==='rdp')p.value=3389;">
              <option value="ssh" ${s.session_type==='ssh'||!s.id?'selected':''}>SSH Terminal</option>
              <option value="vnc" ${s.session_type==='vnc'?'selected':''}>VNC Desktop</option>
              <option value="rdp" ${s.session_type==='rdp'?'selected':''}>RDP (Windows Remote Desktop)</option>
            </select>
          </div>
          <div class="form-group">
            <label>Group</label>
            <input name="group_name" value="${s.group_name||'General'}" />
          </div>
        </div>
        <div class="form-row">
          <div class="form-group">
            <label>Host / IP *</label>
            <input name="host" required value="${s.host||''}" placeholder="192.168.1.50" />
          </div>
          <div class="form-group">
            <label>Port</label>
            <input name="port" type="number" value="${s.port||22}" />
          </div>
        </div>
        <div class="form-row">
          <div class="form-group">
            <label>Username</label>
            <input name="username" value="${s.username||''}" placeholder="root / admin" />
          </div>
          <div class="form-group">
            <label>Password</label>
            <input type="password" name="password" placeholder="${s.has_password?'(saved — leave blank to keep)':''}" />
          </div>
        </div>
        <div class="form-actions">
          <button type="button" class="btn btn-ghost" id="rs-cancel">Cancel</button>
          <button type="submit" class="btn btn-primary"><i class="ph ph-check"></i> ${isEdit?'Save':'Create'}</button>
        </div>
      </form>
    `);
    document.getElementById('rs-cancel').addEventListener('click', closeModal);
    document.getElementById('rs-form').addEventListener('submit', async e => {
      e.preventDefault();
      const f = e.target;
      const body = {
        name: f.name.value.trim(),
        session_type: f.session_type.value,
        host: f.host.value.trim(),
        port: parseInt(f.port.value) || 22,
        group_name: f.group_name.value.trim(),
        username: f.username.value.trim(),
        password: f.password.value,
      };
      if (isEdit && !body.password) delete body.password;
      if (isEdit) await API.patch(`/api/remote/sessions/${s.id}`, body);
      else await API.post('/api/remote/sessions', body);
      closeModal();
      loadSessions();
      toast('Saved', 'success');
    });
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // 3. RUSTDESK SELF-HOSTED MANAGER
  // ═══════════════════════════════════════════════════════════════════════════
  document.getElementById('btn-generate-rd').addEventListener('click', generateRustDeskConfig);

  async function generateRustDeskConfig() {
    const ip = document.getElementById('rd-server-ip').value.trim() || location.hostname;
    const res = document.getElementById('rd-compose-result');
    res.innerHTML = `<div class="empty-state"><div class="spinner"></div></div>`;
    try {
      const data = await API.get(`/api/local-remote/rustdesk/compose?server_ip=${encodeURIComponent(ip)}`);
      res.innerHTML = `
        <div class="card" style="background:var(--bg-elevated);border:1px solid var(--border);margin-bottom:16px">
          <div class="card-header">
            <span class="card-title"><i class="ph ph-file-code"></i> docker-compose.yml for ${data.server_ip}</span>
            <button class="btn btn-ghost btn-sm" id="btn-copy-compose"><i class="ph ph-copy"></i> Copy YAML</button>
          </div>
          <pre class="mono" style="font-size:12px;background:#0a0d16;padding:12px;border-radius:6px;overflow-x:auto;color:#c8d3f5">${data.docker_compose_yaml}</pre>
        </div>

        <div class="card">
          <div class="card-header"><span class="card-title"><i class="ph ph-steps"></i> Step-by-Step Setup Guide</span></div>
          <div style="font-size:13px;color:var(--text-secondary);line-height:1.8">
            ${data.setup_instructions.map(step => `<div>• ${step}</div>`).join('')}
          </div>
        </div>
      `;
      document.getElementById('btn-copy-compose')?.addEventListener('click', () => {
        navigator.clipboard.writeText(data.docker_compose_yaml);
        toast('Copied docker-compose.yml!', 'success');
      });
    } catch(e) {
      res.innerHTML = `<div style="color:var(--down)">${e.message}</div>`;
    }
  }

  // Initial load
  loadLiveAgents();
}

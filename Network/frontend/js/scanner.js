import { API, toast } from './utils.js';

export async function renderScanner(container) {
  container.innerHTML = `
    <div class="page-header">
      <div>
        <h1>Network Tools &amp; Diagnostics</h1>
        <p>Comprehensive suite: Ping, Port Scan, Subnet Sweep, Traceroute, Wake-on-LAN, ARP Discovery, Subnet Calc &amp; SSL Inspector</p>
      </div>
    </div>

    <!-- Tabs -->
    <div class="ad-tabs" id="scanner-tabs">
      ${[
        ['0', 'ph-broadcast', 'Ping Host'],
        ['1', 'ph-door-open', 'Port Scanner'],
        ['2', 'ph-radar', 'Subnet Sweep'],
        ['3', 'ph-path', 'Traceroute'],
        ['4', 'ph-power', 'Wake-on-LAN'],
        ['5', 'ph-table', 'ARP &amp; MAC Discovery'],
        ['6', 'ph-calculator', 'Subnet Calculator'],
        ['7', 'ph-shield-check', 'SSL Inspector'],
      ['8', 'ph-printer', 'Printer Counter'],
      ].map(([idx, icon, label], i) => `
        <button class="ad-tab ${i===0?'active':''}" data-tab="${idx}">
          <i class="ph ${icon}"></i> ${label}
        </button>
      `).join('')}
    </div>

    <!-- TAB 0: Ping -->
    <div id="scan-panel-0" class="scan-panel">
      <div class="card" style="max-width:580px">
        <div class="card-header"><span class="card-title"><i class="ph ph-broadcast"></i> Ping Host</span></div>
        <div class="form-row">
          <div class="form-group">
            <label>IP / Hostname</label>
            <input id="ping-ip" placeholder="e.g. 192.168.1.1 or google.com" />
          </div>
          <div class="form-group">
            <label>Count</label>
            <input id="ping-count" type="number" value="4" min="1" max="10" />
          </div>
        </div>
        <button class="btn btn-primary" id="btn-ping"><i class="ph ph-paper-plane-right"></i> Send Ping</button>
        <div id="ping-result" style="margin-top:16px"></div>
      </div>
    </div>

    <!-- TAB 1: Port Scan -->
    <div id="scan-panel-1" class="scan-panel" style="display:none">
      <div class="card" style="max-width:580px">
        <div class="card-header"><span class="card-title"><i class="ph ph-door-open"></i> TCP Port Scanner</span></div>
        <div class="form-group">
          <label>Target IP</label>
          <input id="ps-ip" placeholder="e.g. 192.168.1.1" />
        </div>
        <div class="form-group">
          <label>Ports to Scan (comma-separated)</label>
          <input id="ps-ports" value="21,22,25,80,443,3306,3389,5432,5900,8080" />
        </div>
        <button class="btn btn-primary" id="btn-portscan"><i class="ph ph-magnifying-glass"></i> Scan Ports</button>
        <div id="ps-result" style="margin-top:16px"></div>
      </div>
    </div>

    <!-- TAB 2: Subnet Sweep -->
    <div id="scan-panel-2" class="scan-panel" style="display:none">
      <div class="card" style="max-width:580px">
        <div class="card-header"><span class="card-title"><i class="ph ph-radar"></i> Subnet Sweep (IP Range Scanner)</span></div>
        <div class="form-group">
          <label>CIDR Range (e.g. 192.168.1.0/24)</label>
          <input id="subnet-cidr" placeholder="e.g. 192.168.1.0/24" />
        </div>
        <button class="btn btn-primary" id="btn-sweep"><i class="ph ph-play"></i> Start Sweep</button>
        <div id="sweep-result" style="margin-top:16px"></div>
      </div>
    </div>

    <!-- TAB 3: Traceroute -->
    <div id="scan-panel-3" class="scan-panel" style="display:none">
      <div class="card" style="max-width:580px">
        <div class="card-header"><span class="card-title"><i class="ph ph-path"></i> Visual Traceroute</span></div>
        <div class="form-row">
          <div class="form-group">
            <label>Target IP / Host</label>
            <input id="tr-ip" placeholder="e.g. 8.8.8.8 or gateway IP" />
          </div>
          <div class="form-group">
            <label>Max Hops</label>
            <input id="tr-hops" type="number" value="20" min="5" max="30" />
          </div>
        </div>
        <button class="btn btn-primary" id="btn-trace"><i class="ph ph-graph"></i> Trace Route</button>
        <div id="tr-result" style="margin-top:16px"></div>
      </div>
    </div>

    <!-- TAB 4: Wake-on-LAN -->
    <div id="scan-panel-4" class="scan-panel" style="display:none">
      <div class="card" style="max-width:580px">
        <div class="card-header"><span class="card-title"><i class="ph ph-power"></i> Wake-on-LAN (WoL)</span></div>
        <div class="form-group">
          <label>Target MAC Address *</label>
          <input id="wol-mac" placeholder="e.g. 00:11:22:33:44:55 or 00-11-22-33-44-55" />
        </div>
        <div class="form-row">
          <div class="form-group">
            <label>Broadcast IP</label>
            <input id="wol-bcast" value="255.255.255.255" placeholder="255.255.255.255 or 192.168.1.255" />
          </div>
          <div class="form-group">
            <label>UDP Port</label>
            <input id="wol-port" type="number" value="9" />
          </div>
        </div>
        <button class="btn btn-primary" id="btn-wol"><i class="ph ph-broadcast"></i> Send Magic Packet</button>
        <div id="wol-result" style="margin-top:16px"></div>
      </div>
    </div>

    <!-- TAB 5: ARP & MAC Discovery -->
    <div id="scan-panel-5" class="scan-panel" style="display:none">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px">
        <span style="font-size:13px;color:var(--text-secondary)">Read switch ARP cache &amp; detect device hardware manufacturers (OUI lookup)</span>
        <button class="btn btn-primary btn-sm" id="btn-refresh-arp"><i class="ph ph-arrows-clockwise"></i> Refresh ARP Table</button>
      </div>
      <div class="card" style="padding:0">
        <div class="table-wrap">
          <table>
            <thead>
              <tr><th>IP Address</th><th>MAC Address</th><th>Hardware Vendor</th><th>Interface</th></tr>
            </thead>
            <tbody id="arp-tbody">
              <tr><td colspan="4" style="text-align:center;padding:30px"><div class="spinner" style="margin:0 auto"></div></td></tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- TAB 6: Subnet Calculator -->
    <div id="scan-panel-6" class="scan-panel" style="display:none">
      <div class="card" style="max-width:580px">
        <div class="card-header"><span class="card-title"><i class="ph ph-calculator"></i> Subnet / CIDR Calculator</span></div>
        <div class="form-group">
          <label>IP Address with CIDR Prefix</label>
          <input id="calc-cidr" placeholder="e.g. 192.168.1.50/24 or 10.0.0.0/16" value="192.168.1.0/24" />
        </div>
        <button class="btn btn-primary" id="btn-calc-subnet"><i class="ph ph-equals"></i> Calculate</button>
        <div id="calc-result" style="margin-top:16px"></div>
      </div>
    </div>

    <!-- TAB 7: SSL Certificate Inspector -->
    <div id="scan-panel-7" class="scan-panel" style="display:none">
      <div class="card" style="max-width:580px">
        <div class="card-header"><span class="card-title"><i class="ph ph-shield-check"></i> SSL / TLS Certificate Checker</span></div>
        <div class="form-row">
          <div class="form-group">
            <label>Domain or Host IP</label>
            <input id="ssl-host" placeholder="e.g. your-internal-server.local or google.com" />
          </div>
          <div class="form-group">
            <label>Port</label>
            <input id="ssl-port" type="number" value="443" />
          </div>
        </div>
        <button class="btn btn-primary" id="btn-check-ssl"><i class="ph ph-certificate"></i> Inspect Certificate</button>
        <div id="ssl-result" style="margin-top:16px"></div>
      </div>
    </div>
  <div id="scan-panel-8" class="scan-panel" style="display:none">
  <div class="card" style="max-width:580px">
    <div class="card-header">
      <span class="card-title"><i class="ph ph-printer"></i> Printer Counter</span>
    </div>
    <div class="form-group">
      <div style="display:flex; justify-content:space-between; align-items:flex-end; margin-bottom: 4px;">
        <label style="margin-bottom:0">Printer IPs (comma or newline separated)</label>
        <button class="btn btn-ghost" id="btn-load-printers" style="padding: 2px 6px; font-size: 11px; color: var(--accent); border-color: var(--accent);">
          <i class="ph ph-download-simple"></i> Load from Devices
        </button>
      </div>
      <textarea id="printer-ips" rows="3" placeholder="e.g. 192.168.1.100&#10;192.168.1.101"></textarea>
    </div>
    <div class="form-group">
      <label>Department ID</label>
      <input id="printer-dept" value="999" />
    </div>
    <div class="form-group">
      <label>PIN</label>
      <input id="printer-pin" value="9900" />
    </div>
    <button class="btn btn-primary" id="btn-printer-counter"><i class="ph ph-printer"></i> Get Counter</button>
    <div id="printer-result" style="margin-top:16px"></div>
  </div>
</div>
`;

  // ── Tab switching ─────────────────────────────────────────────────────────
  const tabs = document.querySelectorAll('#scanner-tabs .ad-tab');
  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      tabs.forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      document.querySelectorAll('.scan-panel').forEach(p => p.style.display = 'none');
      const target = document.getElementById(`scan-panel-${tab.dataset.tab}`);
      if (target) target.style.display = '';
      if (tab.dataset.tab === '5') loadArpTable();
    });
  });

  // ── 0. Ping ───────────────────────────────────────────────────────────────
  document.getElementById('btn-ping').addEventListener('click', async () => {
    const ip    = document.getElementById('ping-ip').value.trim();
    const count = parseInt(document.getElementById('ping-count').value) || 4;
    const res   = document.getElementById('ping-result');
    if (!ip) return toast('Enter an IP or hostname', 'error');
    res.innerHTML = `<div class="empty-state" style="padding:20px"><div class="spinner"></div><p style="margin-top:8px">Pinging ${ip}…</p></div>`;
    try {
      const r = await API.post('/api/network/ping', { ip, count });
      const color = r.status === 'UP' ? 'var(--up)' : 'var(--down)';
      res.innerHTML = `
        <div class="check-item">
          <div class="check-icon ${r.status==='UP'?'ok':'fail'}">
            <i class="ph ph-${r.status==='UP'?'check-bold':'x-bold'}"></i>
          </div>
          <div>
            <div class="check-title" style="color:${color}">${r.status} — ${ip}</div>
            ${r.hostname ? `<div class="check-detail">Hostname: ${r.hostname}</div>` : ''}
            ${r.latency_ms>0 ? `<div class="check-detail">Avg latency: <strong>${r.latency_ms.toFixed(1)} ms</strong></div>` : ''}
            <div class="check-detail" style="margin-top:6px;font-family:'JetBrains Mono',monospace;font-size:11px;white-space:pre-wrap">${(r.output||'').slice(0,500)}</div>
          </div>
        </div>`;
    } catch(e) { res.innerHTML = `<div style="color:var(--down)">${e.message}</div>`; }
  });

  // ── 1. Port Scan ──────────────────────────────────────────────────────────
  document.getElementById('btn-portscan').addEventListener('click', async () => {
    const ip    = document.getElementById('ps-ip').value.trim();
    const ports = document.getElementById('ps-ports').value.split(',').map(p => parseInt(p.trim())).filter(Boolean);
    const res   = document.getElementById('ps-result');
    if (!ip) return toast('Enter an IP address', 'error');
    res.innerHTML = `<div class="empty-state" style="padding:20px"><div class="spinner"></div><p style="margin-top:8px">Scanning ${ports.length} ports…</p></div>`;
    try {
      const r = await API.post('/api/network/portscan', { ip, ports });
      res.innerHTML = `
        <div style="margin-bottom:10px;font-size:13px">
          <strong style="color:var(--up)">${r.open_count} open</strong>
          <span style="color:var(--text-muted)"> / ${ports.length} scanned on ${ip}</span>
        </div>
        <div style="display:flex;flex-wrap:wrap;gap:6px">
          ${r.ports.map(p => `
            <span class="port-chip ${p.open?'open':'closed'}" title="${p.error||''}">
              ${p.open ? '<i class="ph ph-lock-open"></i>' : '<i class="ph ph-lock"></i>'}
              ${p.port}
            </span>`).join('')}
        </div>`;
    } catch(e) { res.innerHTML = `<div style="color:var(--down)">${e.message}</div>`; }
  });

  // ── 2. Subnet Sweep ───────────────────────────────────────────────────────
  document.getElementById('btn-sweep').addEventListener('click', async () => {
    const cidr = document.getElementById('subnet-cidr').value.trim();
    const res  = document.getElementById('sweep-result');
    if (!cidr) return toast('Enter a CIDR range', 'error');
    res.innerHTML = `<div class="empty-state" style="padding:20px"><div class="spinner"></div><p style="margin-top:8px">Sweeping ${cidr}… (this may take 15-30s)</p></div>`;
    try {
      const r = await API.post('/api/network/scan', { cidr });
      res.innerHTML = `
        <div style="margin-bottom:12px;font-size:13px">
          <strong style="color:var(--up)">${r.alive_count} hosts alive</strong>
          <span style="color:var(--text-muted)"> in ${cidr}</span>
          <button class="btn btn-ghost btn-sm" style="margin-left:12px" id="import-hosts">
            <i class="ph ph-download-simple"></i> Import to Devices
          </button>
        </div>
        <div id="sweep-hosts">
          ${r.hosts.map(h => `
            <div class="scan-result-item">
              <span class="dot up" style="width:8px;height:8px;border-radius:50%;background:var(--up);flex-shrink:0"></span>
              <span class="s-ip">${h.ip}</span>
              <span class="s-host">${h.hostname || '—'}</span>
              <span class="s-lat">${h.latency_ms ? h.latency_ms.toFixed(1)+'ms' : ''}</span>
            </div>`).join('')}
        </div>`;

      document.getElementById('import-hosts')?.addEventListener('click', async () => {
        let added = 0;
        for (const h of r.hosts) {
          try {
            await API.post('/api/devices', {
              name: h.hostname || h.ip, ip: h.ip, hostname: h.hostname,
              group_name: 'Discovered', device_type: 'Other'
            });
            added++;
          } catch(_) {}
        }
        toast(`${added} host(s) imported to Devices`, 'success');
      });
    } catch(e) { res.innerHTML = `<div style="color:var(--down)">${e.message}</div>`; }
  });

  // ── 3. Traceroute ─────────────────────────────────────────────────────────
  document.getElementById('btn-trace').addEventListener('click', async () => {
    const ip   = document.getElementById('tr-ip').value.trim();
    const hops = parseInt(document.getElementById('tr-hops').value) || 20;
    const res  = document.getElementById('tr-result');
    if (!ip) return toast('Enter a target IP', 'error');
    res.innerHTML = `<div class="empty-state" style="padding:20px"><div class="spinner"></div><p style="margin-top:8px">Tracing route to ${ip}…</p></div>`;
    try {
      const r = await API.post('/api/network/traceroute', { ip, max_hops: hops });
      if (!r.hops.length) {
        res.innerHTML = `<div style="color:var(--text-muted)">No hops returned.</div>`;
        return;
      }
      const maxLat = Math.max(...r.hops.filter(h=>h.latency_ms).map(h=>h.latency_ms), 1);
      res.innerHTML = `
        <div style="font-size:13px;color:var(--text-muted);margin-bottom:10px">Route to <strong>${ip}</strong> — ${r.hops.length} hop(s)</div>
        ${r.hops.map(h => `
          <div class="hop-row">
            <span class="hop-num">${h.hop}</span>
            <span class="hop-ip">${h.ip}</span>
            <div class="hop-bar">
              <div class="hop-bar-fill" style="width:${h.latency_ms ? (h.latency_ms/maxLat*100) : 0}%"></div>
            </div>
            <span class="hop-lat">${h.latency_ms != null ? h.latency_ms+'ms' : '*'}</span>
          </div>`).join('')}`;
    } catch(e) { res.innerHTML = `<div style="color:var(--down)">${e.message}</div>`; }
  });

  // ── 4. Wake-on-LAN ────────────────────────────────────────────────────────
  document.getElementById('btn-wol').addEventListener('click', async () => {
    const mac   = document.getElementById('wol-mac').value.trim();
    const bcast = document.getElementById('wol-bcast').value.trim() || '255.255.255.255';
    const port  = parseInt(document.getElementById('wol-port').value) || 9;
    const res   = document.getElementById('wol-result');
    if (!mac) return toast('Enter target MAC address', 'error');

    res.innerHTML = `<div class="empty-state" style="padding:15px"><div class="spinner"></div><p style="margin-top:8px">Sending Magic Packet…</p></div>`;
    try {
      const r = await API.post('/api/network/wol', { mac, broadcast_ip: bcast, port });
      if (r.success) {
        res.innerHTML = `
          <div class="check-item">
            <div class="check-icon ok"><i class="ph ph-check-bold"></i></div>
            <div>
              <div class="check-title" style="color:var(--up)">Magic Packet Sent!</div>
              <div class="check-detail">${r.message}</div>
              <div class="check-detail" style="font-size:11px;color:var(--text-muted);margin-top:4px">Target MAC: ${r.mac} · Broadcast: ${r.broadcast_ip}</div>
            </div>
          </div>`;
        toast('Wake-on-LAN packet broadcasted', 'success');
      } else {
        res.innerHTML = `<div class="check-item"><div class="check-icon fail"><i class="ph ph-x-bold"></i></div><div><div class="check-title" style="color:var(--down)">Error</div><div class="check-detail">${r.error}</div></div></div>`;
      }
    } catch(e) { res.innerHTML = `<div style="color:var(--down)">${e.message}</div>`; }
  });

  // ── 5. ARP Table ──────────────────────────────────────────────────────────
  document.getElementById('btn-refresh-arp').addEventListener('click', loadArpTable);

  async function loadArpTable() {
    const tbody = document.getElementById('arp-tbody');
    tbody.innerHTML = `<tr><td colspan="4" style="text-align:center;padding:30px"><div class="spinner" style="margin:0 auto"></div></td></tr>`;
    try {
      const r = await API.get('/api/network/arp');
      if (!r.entries || !r.entries.length) {
        tbody.innerHTML = `<tr><td colspan="4"><div class="empty-state"><i class="ph ph-table"></i><p>No ARP entries found.</p></div></td></tr>`;
        return;
      }
      tbody.innerHTML = r.entries.map(e => `
        <tr>
          <td><span class="mono">${e.ip}</span></td>
          <td><span class="mono" style="color:var(--accent)">${e.mac}</span></td>
          <td><span class="chip ${e.vendor!=='Unknown Vendor'?'chip-up':'chip-unknown'}">${e.vendor}</span></td>
          <td class="mono" style="color:var(--text-muted)">${e.interface || '—'}</td>
        </tr>
      `).join('');
    } catch(err) {
      tbody.innerHTML = `<tr><td colspan="4" style="color:var(--down);text-align:center;padding:20px">${err.message}</td></tr>`;
    }
  }

  // ── 6. Subnet Calculator ──────────────────────────────────────────────────
  document.getElementById('btn-calc-subnet').addEventListener('click', async () => {
    const cidr = document.getElementById('calc-cidr').value.trim();
    const res  = document.getElementById('calc-result');
    if (!cidr) return toast('Enter a CIDR notation', 'error');

    res.innerHTML = `<div class="empty-state" style="padding:15px"><div class="spinner"></div></div>`;
    try {
      const r = await API.post('/api/network/subnet-calc', { cidr });
      res.innerHTML = `
        <div class="card" style="background:var(--bg-elevated);padding:14px;border:1px solid var(--border)">
          <div style="font-size:16px;font-weight:700;color:var(--accent);margin-bottom:12px">${r.cidr}</div>
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;font-size:12px">
            <div><span style="color:var(--text-muted)">Network Address:</span> <strong class="mono">${r.network_address}</strong></div>
            <div><span style="color:var(--text-muted)">Subnet Mask:</span> <strong class="mono">${r.netmask}</strong></div>
            <div><span style="color:var(--text-muted)">Wildcard Mask:</span> <strong class="mono">${r.wildcard_mask}</strong></div>
            <div><span style="color:var(--text-muted)">Broadcast Address:</span> <strong class="mono">${r.broadcast_address}</strong></div>
            <div><span style="color:var(--text-muted)">Total Addresses:</span> <strong>${r.total_addresses.toLocaleString()}</strong></div>
            <div><span style="color:var(--text-muted)">Usable Host Count:</span> <strong style="color:var(--up)">${r.usable_hosts.toLocaleString()}</strong></div>
            <div><span style="color:var(--text-muted)">First Usable IP:</span> <strong class="mono">${r.first_usable_ip}</strong></div>
            <div><span style="color:var(--text-muted)">Last Usable IP:</span> <strong class="mono">${r.last_usable_ip}</strong></div>
          </div>
        </div>`;
    } catch(e) { res.innerHTML = `<div style="color:var(--down)">${e.message}</div>`; }
  });

  // ── 7. SSL Checker ────────────────────────────────────────────────────────
  document.getElementById('btn-check-ssl').addEventListener('click', async () => {
    const host = document.getElementById('ssl-host').value.trim();
    const port = parseInt(document.getElementById('ssl-port').value) || 443;
    const res  = document.getElementById('ssl-result');
    if (!host) return toast('Enter domain or host', 'error');

    res.innerHTML = `<div class="empty-state" style="padding:15px"><div class="spinner"></div><p style="margin-top:8px">Inspecting SSL certificate…</p></div>`;
    try {
      const r = await API.post('/api/network/ssl-check', { host, port });
      if (r.ok) {
        const isExp = r.is_expired;
        const color = isExp ? 'var(--down)' : (r.days_left < 15 ? 'var(--warn)' : 'var(--up)');
        res.innerHTML = `
          <div class="check-item">
            <div class="check-icon ${isExp?'fail':'ok'}"><i class="ph ph-${isExp?'x-bold':'shield-check'}"></i></div>
            <div style="flex:1">
              <div class="check-title" style="color:${color}">
                ${isExp ? 'EXPIRED' : 'VALID'} — ${r.common_name} (${r.days_left !== null ? r.days_left + ' days left' : ''})
              </div>
              <div class="check-detail" style="margin-top:4px">Issuer: <strong>${r.issuer_common_name || r.issuer_org || 'Self-signed'}</strong></div>
              <div class="check-detail">TLS: ${r.tls_version} · Cipher: ${r.cipher}</div>
              <div class="check-detail" style="font-size:11px;color:var(--text-muted);margin-top:4px">
                Expires on: ${r.valid_until}
              </div>
            </div>
          </div>`;
      } else {
        res.innerHTML = `<div class="check-item"><div class="check-icon fail"><i class="ph ph-x-bold"></i></div><div><div class="check-title" style="color:var(--down)">SSL Check Failed</div><div class="check-detail">${r.error}</div></div></div>`;
      }
    } catch(e) { res.innerHTML = `<div style="color:var(--down)">${e.message}</div>`; }
  });

  // ── 8. Printer Counter ────────────────────────────────────────────────────
  document.getElementById('btn-load-printers').addEventListener('click', async () => {
    try {
      const devices = await API.get('/api/devices');
      const printers = devices.filter(d => d.device_type === 'Printer' && d.enabled).map(d => d.ip);
      if (printers.length === 0) return toast('No enabled printers found in Device Manager', 'warn');
      document.getElementById('printer-ips').value = printers.join('\n');
      toast(`Loaded ${printers.length} printer IPs`, 'success');
    } catch(e) {
      toast('Failed to load devices: ' + e.message, 'error');
    }
  });

  document.getElementById('btn-printer-counter').addEventListener('click', async () => {
    const ipsRaw = document.getElementById('printer-ips').value;
    const dept = document.getElementById('printer-dept').value.trim() || '999';
    const pin  = document.getElementById('printer-pin').value.trim() || '9900';
    const res  = document.getElementById('printer-result');
    
    const ips = ipsRaw.split(/[\s,]+/).map(ip => ip.trim()).filter(Boolean);
    if (ips.length === 0) return toast('Enter at least one printer IP address', 'error');

    res.innerHTML = `<div class="empty-state" style="padding:20px"><div class="spinner"></div><p style="margin-top:8px">Checking ${ips.length} printer(s)…</p></div>`;
    
    let htmlContent = `
        <style>
          @media print {
            body * { visibility: hidden; }
            #printer-result { visibility: visible; position: absolute; left: 0; top: 0; width: 100%; margin: 0; padding: 0; }
            #printer-result * { visibility: visible; }
            .canon-print-area {
              page-break-inside: avoid;
              background: #fff !important;
            }
            .canon-print-area:last-child {
              page-break-after: auto;
            }
            .no-print { display: none !important; }
          }
          .canon-print-area {
            font-family: Arial, Helvetica, sans-serif;
            font-size: 12px;
            color: #000;
            background: #fff;
            padding: 10px 20px;
            line-height: 1.4;
            margin-bottom: 30px;
            border: 1px solid #ccc;
          }
          @media print {
            .canon-print-area { border: none; margin-bottom: 0; padding: 0; }
          }
          .canon-print-area a { color: #0000ee; text-decoration: none; }
          .canon-print-area a:hover { text-decoration: underline; }
          .canon-sidebar-nav { margin-bottom: 8px; }
          .canon-sidebar-title { padding-bottom: 2px; }
          .canon-sidebar-link { padding: 1px 0 1px 16px; font-size: 12px; }
          .canon-sidebar-link a { color: #0000ee; }
          .canon-table { width: 100%; border-collapse: collapse; font-size: 12px; margin-bottom: 24px; }
          .canon-table th { text-align: left; padding: 4px; border-top: 1px solid #1e4b7a; border-bottom: 1px solid #1e4b7a; font-weight: normal; }
          .canon-table td { padding: 4px; border-bottom: 1px solid #ddd; }
        </style>
        
        <div class="no-print" style="margin-bottom: 16px; text-align: right;">
          <button onclick="window.print()" class="btn btn-primary"><i class="ph ph-printer"></i> Print All Pages</button>
        </div>
    `;

    for (let i = 0; i < ips.length; i++) {
      const ip = ips[i];
      try {
        const r = await API.post('/api/network/printer-counter', { ip, dept_id: dept, pin });

        if (!r.success) {
          htmlContent += `
            <div class="check-item no-print">
              <div class="check-icon fail"><i class="ph ph-x-bold"></i></div>
              <div>
                <div class="check-title" style="color:var(--down)">Connection Failed (${ip})</div>
                <div class="check-detail">${r.error}</div>
                <div class="check-detail" style="font-size:11px;color:var(--text-muted);margin-top:4px">Dept: ${r.dept_id}</div>
              </div>
            </div>`;
          continue;
        }

        const mainRows = Object.entries(r.main_counter || {});
        const sendRows = Object.entries(r.send_counter || {});

        htmlContent += `
          <div class="canon-print-area">
            <!-- Logo & Title row -->
            <div style="display:flex;justify-content:space-between;align-items:flex-end;margin-bottom:4px">
              <div style="display:flex;align-items:center;gap:6px;color:#888;font-weight:bold;font-size:13px">
                <svg width="14" height="14" viewBox="0 0 16 16" xmlns="http://www.w3.org/2000/svg" style="display:block">
                  <rect x="0" y="0" width="16" height="16" fill="#e0e0e0" stroke="#999" stroke-width="1"/>
                  <rect x="3" y="3" width="10" height="10" fill="#d32f2f"/>
                </svg>
                imageRUNNER ADVANCE
              </div>
              <div style="text-align:right">
                <div style="font-weight:bold;font-size:12px;color:#666;margin-bottom:4px">${r.model || 'KP Color Printer 201 / iR-ADV C5235'}</div>
                <div style="font-size:11px;font-weight:bold">
                  <a href="#" style="color:#5f9ea0">To Portal</a> &nbsp;
                  <span style="color:#000">Login User : ${r.dept_id === 'SNMP' ? 'SNMP Polling' : '0000' + r.dept_id}</span> &nbsp;
                  <a href="#" style="color:#5f9ea0">Log Out</a>
                </div>
              </div>
            </div>
            
            <!-- Thick separator line -->
            <div style="border-top:2px solid #000;margin-bottom:6px"></div>
            
            <!-- Status Monitor Header -->
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">
              <div style="display:flex;align-items:center;gap:8px">
                <div style="width:20px;height:20px;border:1px solid #999;background:#eee;display:flex;align-items:center;justify-content:center">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#666" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path><circle cx="12" cy="12" r="3"></circle></svg>
                </div>
                <span style="font-size:16px;font-weight:bold;color:#000">Status Monitor/Cancel</span>
              </div>
              <div><a href="#" style="color:#0000ee;text-decoration:underline">Mail to System Manager</a></div>
            </div>
            
            <!-- Dotted line -->
            <div style="border-top:1px dotted #666;margin-bottom:12px"></div>
            
            <!-- Two columns layout -->
            <div style="display:flex;gap:20px">
              <!-- Sidebar -->
              <div style="width:160px;flex-shrink:0">
                <div class="canon-sidebar-nav">
                  <div class="canon-sidebar-title">Copy/Print</div>
                  <div class="canon-sidebar-link"><a href="#" onclick="return false">Job Status</a></div>
                  <div class="canon-sidebar-link"><a href="#" onclick="return false">Job Log</a></div>
                </div>
                <div class="canon-sidebar-nav">
                  <div class="canon-sidebar-title">Send</div>
                  <div class="canon-sidebar-link"><a href="#" onclick="return false">Job Status</a></div>
                  <div class="canon-sidebar-link"><a href="#" onclick="return false">Job Log</a></div>
                </div>
                <div class="canon-sidebar-nav">
                  <div class="canon-sidebar-title">Receive</div>
                  <div class="canon-sidebar-link"><a href="#" onclick="return false">Job Status</a></div>
                  <div class="canon-sidebar-link"><a href="#" onclick="return false">Job Log</a></div>
                </div>
                <div class="canon-sidebar-nav">
                  <div class="canon-sidebar-title">Store</div>
                  <div class="canon-sidebar-link"><a href="#" onclick="return false">Job Status</a></div>
                  <div class="canon-sidebar-link"><a href="#" onclick="return false">Job Log</a></div>
                </div>
                <div style="margin-top:12px">
                  <div style="padding:2px 0"><a href="#" onclick="return false">Error Information</a></div>
                  <div style="padding:2px 0"><a href="#" onclick="return false">Consumables</a></div>
                  <div style="padding:2px 0"><a href="#" onclick="return false">Device Features</a></div>
                  <div style="padding:2px 0"><a href="#" onclick="return false">Device Information</a></div>
                  <div style="padding:2px 0"><a href="#" onclick="return false">Counter Check</a></div>
                </div>
              </div>
              
              <!-- Main Content Area -->
              <div style="flex:1">
                <div style="color:#666;margin-bottom:4px">Status Monitor/Cancel : Counter Check</div>
                <!-- Gray border box -->
                <div style="border:1px solid #666;background:#f0f0f0;padding:2px 4px;display:flex;justify-content:space-between;align-items:center;margin-bottom:16px">
                  <span style="color:#666">Counter Check</span>
                  <div style="display:flex;align-items:center;gap:8px">
                    <span style="color:#888;font-size:11px">Last Updated : ${r.device_date || '27/08 2026 14:14:59'}</span>
                    <div class="no-print" style="display:flex;gap:4px">
                      <button onclick="window.print()" style="background:#ddd;border:1px solid #999;padding:1px 4px;cursor:pointer;font-size:10px;font-weight:bold" title="Print">Print</button>
                    </div>
                  </div>
                </div>
                
                <!-- Tables -->
                ${mainRows.length ? `
                  <div style="font-weight:bold;color:#1e4b7a;margin-bottom:4px;padding-left:4px">Main Counter</div>
                  <table class="canon-table">
                    <thead><tr><th style="width:65%">Type</th><th>No. of Copies</th></tr></thead>
                    <tbody>${mainRows.map(([lbl, val]) => `<tr><td>${lbl}</td><td>${val}</td></tr>`).join('')}</tbody>
                  </table>
                ` : ''}
                
                ${sendRows.length ? `
                  <div style="font-weight:bold;color:#1e4b7a;margin-bottom:4px;padding-left:4px">Send Application ID : ${r.app_id || 'ae53008a-aa81-4aae-95c7-d746db532c88'}</div>
                  <table class="canon-table">
                    <thead><tr><th style="width:65%">Type</th><th>No. of Copies</th></tr></thead>
                    <tbody>${sendRows.map(([lbl, val]) => `<tr><td>${lbl}</td><td>${val}</td></tr>`).join('')}</tbody>
                  </table>
                ` : ''}
                
                <!-- Eject icon placeholder -->
                <div style="margin-top:10px">
                  <div style="display:inline-block;border:1px solid #999;background:#e5e5e5;padding:0 2px;box-shadow:1px 1px 1px rgba(0,0,0,0.2)">
                     <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="#333" stroke-width="2"><path d="M2 12h20M12 2l-7 7h14l-7-7z"></path></svg>
                  </div>
                </div>
              </div>
            </div>
            
            <!-- Bottom solid line -->
            <div style="border-top:1px solid #000;margin-top:30px;padding-top:4px;text-align:right;font-size:10px;color:#000">
              Copyright CANON INC. 2012
            </div>
          </div>`;
      } catch(e) {
        htmlContent += `<div style="color:var(--down)" class="no-print">Error checking ${ip}: ${e.message}</div>`;
      }
    }
    
    res.innerHTML = htmlContent;
    toast('Printer counters retrieved', 'success');
  });
}


import { API, toast, openModal, closeModal, statusChip, timeAgo, deviceTypeIcon } from './utils.js?v=2.3';

const DEVICE_TYPES = ['Workstation','Server','Laptop','Printer','Switch','Router','AP','Camera','Phone','Other'];

// IPv4 and basic IPv6 validation regex
const IP_REGEX = /^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$|^(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}$/;

export async function renderDevices(container) {
  container.innerHTML = `
    <div class="page-header">
      <div>
        <h1>Device Manager</h1>
        <p>Add and manage monitored network hosts</p>
      </div>
      <div style="display:flex;gap:10px;flex-wrap:wrap">
        <button class="btn btn-ghost" id="btn-export-devices" title="Export all devices to CSV">
          <i class="ph ph-download-simple"></i> Export CSV
        </button>
        <button class="btn btn-ghost" id="btn-import-batch" style="border-color:var(--accent);color:var(--accent)" title="Import multiple devices from CSV or JSON">
          <i class="ph ph-file-arrow-up"></i> Import Batch
        </button>
        <button class="btn btn-primary" id="btn-add-device">
          <i class="ph ph-plus"></i> Add Device
        </button>
      </div>
    </div>
    <div class="toolbar">
      <div class="search-box">
        <i class="ph ph-magnifying-glass"></i>
        <input type="text" id="dev-search" placeholder="Search devices by name, IP, group or hostname…" />
      </div>
    </div>
    <div class="card" style="padding:0">
      <div class="table-wrap">
        <table id="devices-table">
          <thead>
            <tr>
              <th>Name</th><th>IP Address</th><th>Type</th><th>Group</th>
              <th>Hostname</th><th>Enabled</th><th>Added</th><th>Actions</th>
            </tr>
          </thead>
          <tbody id="devices-tbody">
            <tr><td colspan="8" style="text-align:center;padding:40px">
              <div class="spinner" style="margin:0 auto"></div>
            </td></tr>
          </tbody>
        </table>
      </div>
    </div>
  `;

  document.getElementById('btn-add-device').addEventListener('click', () => openAddModal());
  document.getElementById('btn-import-batch').addEventListener('click', () => openBatchImportModal());
  document.getElementById('btn-export-devices').addEventListener('click', () => exportDevicesToCsv());
  document.getElementById('dev-search').addEventListener('input', e => filterTable(e.target.value));

  let _devices = [];

  async function load() {
    try {
      _devices = await API.get('/api/devices');
      renderTable(_devices);
    } catch(e) {
      toast(e.message, 'error');
    }
  }

  function filterTable(q) {
    const lower = q.toLowerCase();
    const filtered = _devices.filter(d =>
      d.name.toLowerCase().includes(lower) ||
      d.ip.includes(lower) ||
      (d.hostname || '').toLowerCase().includes(lower) ||
      d.group_name.toLowerCase().includes(lower)
    );
    renderTable(filtered);
  }

  function renderTable(devices) {
    const tbody = document.getElementById('devices-tbody');
    if (!devices.length) {
      tbody.innerHTML = `<tr><td colspan="8">
        <div class="empty-state">
          <i class="ph ph-desktop-tower"></i>
          <p>No devices found. Click "Add Device" or "Import Batch" to get started.</p>
        </div>
      </td></tr>`;
      return;
    }
    tbody.innerHTML = devices.map(d => `
      <tr>
        <td><strong>${escapeHtml(d.name)}</strong></td>
        <td><span class="mono">${escapeHtml(d.ip)}</span></td>
        <td><i class="ph ${deviceTypeIcon(d.device_type)}"></i> ${escapeHtml(d.device_type)}</td>
        <td>${escapeHtml(d.group_name)}</td>
        <td class="mono" style="color:var(--text-secondary)">${escapeHtml(d.hostname || '—')}</td>
        <td>
          <label class="toggle-switch" style="display:inline-flex;align-items:center;gap:8px;cursor:pointer">
            <input type="checkbox" ${d.enabled ? 'checked' : ''} onchange="window._toggleDevice(${d.id}, this.checked)" style="width:auto" />
            <span style="font-size:12px;color:var(--text-muted)">${d.enabled ? 'Yes' : 'No'}</span>
          </label>
        </td>
        <td style="color:var(--text-muted);font-size:12px">${timeAgo(d.created_at)}</td>
        <td>
          <div style="display:flex;gap:6px">
            <button class="btn btn-ghost btn-sm" onclick="window._editDevice(${d.id})" title="Edit"><i class="ph ph-pencil"></i></button>
            <button class="btn btn-danger btn-sm" onclick="window._deleteDevice(${d.id},'${escapeHtml(d.name)}')" title="Delete"><i class="ph ph-trash"></i></button>
          </div>
        </td>
      </tr>
    `).join('');
  }

  // ── Global handlers ───────────────────────────────────────────────────────
  window._toggleDevice = async (id, enabled) => {
    try {
      await API.patch(`/api/devices/${id}`, { enabled });
      const d = _devices.find(x => x.id === id);
      if (d) d.enabled = enabled;
      toast(`Device ${enabled ? 'enabled' : 'disabled'}`, 'success');
    } catch(e) { toast(e.message, 'error'); }
  };

  window._editDevice = (id) => {
    const d = _devices.find(x => x.id === id);
    if (d) openEditModal(d);
  };

  window._deleteDevice = async (id, name) => {
    if (!confirm(`Delete device "${name}"?`)) return;
    try {
      await API.del(`/api/devices/${id}`);
      _devices = _devices.filter(x => x.id !== id);
      renderTable(_devices);
      toast(`"${name}" deleted`, 'success');
    } catch(e) { toast(e.message, 'error'); }
  };

  // ── Add single modal ──────────────────────────────────────────────────────
  function openAddModal() {
    openModal('Add Device', deviceForm(null, true));
    
    document.getElementById('tab-mode-batch')?.addEventListener('click', () => {
      openBatchImportModal();
    });

    document.getElementById('device-form').addEventListener('submit', async e => {
      e.preventDefault();
      const body = collectForm();
      try {
        const created = await API.post('/api/devices', body);
        _devices.unshift(created);
        renderTable(_devices);
        closeModal();
        toast(`"${created.name}" added`, 'success');
      } catch(err) { toast(err.message, 'error'); }
    });
    document.getElementById('form-cancel').addEventListener('click', closeModal);
  }

  function openEditModal(d) {
    openModal('Edit Device', deviceForm(d, false));
    document.getElementById('device-form').addEventListener('submit', async e => {
      e.preventDefault();
      const body = collectForm();
      try {
        const updated = await API.patch(`/api/devices/${d.id}`, body);
        const idx = _devices.findIndex(x => x.id === d.id);
        if (idx !== -1) _devices[idx] = updated;
        renderTable(_devices);
        closeModal();
        toast('Device updated', 'success');
      } catch(err) { toast(err.message, 'error'); }
    });
    document.getElementById('form-cancel').addEventListener('click', closeModal);
  }

  function deviceForm(d = {}, isAdd = false) {
    const typeOpts = DEVICE_TYPES.map(t =>
      `<option value="${t}" ${d && d.device_type===t?'selected':''}>${t}</option>`).join('');
    
    const tabSwitcher = isAdd ? `
      <div class="import-subtabs" style="margin-bottom:16px">
        <button type="button" class="import-subtab active" id="tab-mode-single">
          <i class="ph ph-plus-circle"></i> Single Device
        </button>
        <button type="button" class="import-subtab" id="tab-mode-batch">
          <i class="ph ph-file-arrow-up"></i> Import Batch (CSV / JSON)
        </button>
      </div>
    ` : '';

    return `
      ${tabSwitcher}
      <form id="device-form">
        <div class="form-row">
          <div class="form-group">
            <label>Device Name *</label>
            <input name="name" required value="${escapeHtml((d && d.name)||'')}" placeholder="e.g. Main Switch" />
          </div>
          <div class="form-group">
            <label>IP Address *</label>
            <input name="ip" required value="${escapeHtml((d && d.ip)||'')}" placeholder="e.g. 192.168.1.1" />
          </div>
        </div>
        <div class="form-row">
          <div class="form-group">
            <label>Device Type</label>
            <select name="device_type">${typeOpts}</select>
          </div>
          <div class="form-group">
            <label>Group</label>
            <input name="group_name" value="${escapeHtml((d && d.group_name)||'General')}" placeholder="e.g. IT, Finance" />
          </div>
        </div>
        <div class="form-group">
          <label>Hostname (optional)</label>
          <input name="hostname" value="${escapeHtml((d && d.hostname)||'')}" placeholder="auto-detected if blank" />
        </div>
        <div class="form-group">
          <label>Notes</label>
          <textarea name="notes">${escapeHtml((d && d.notes)||'')}</textarea>
        </div>
        <div class="form-actions">
          <button type="button" class="btn btn-ghost" id="form-cancel">Cancel</button>
          <button type="submit" class="btn btn-primary"><i class="ph ph-check"></i> Save</button>
        </div>
      </form>`;
  }

  function collectForm() {
    const f = document.getElementById('device-form');
    return {
      name:        f.name.value.trim(),
      ip:          f.ip.value.trim(),
      device_type: f.device_type.value,
      group_name:  f.group_name.value.trim(),
      hostname:    f.hostname.value.trim(),
      notes:       f.notes.value.trim(),
    };
  }

  // ── Batch Import Modal ────────────────────────────────────────────────────
  function openBatchImportModal() {
    const typeOpts = DEVICE_TYPES.map(t => `<option value="${t}">${t}</option>`).join('');
    
    const html = `
      <div class="import-container">
        <div style="display:flex;align-items:center;justify-content:space-between;gap:10px;flex-wrap:wrap">
          <p style="font-size:13px;color:var(--text-secondary);margin:0">
            Import multiple devices via CSV, JSON, or plain text list.
          </p>
          <button type="button" class="btn btn-ghost btn-sm" id="btn-download-sample">
            <i class="ph ph-file-csv"></i> Download Sample CSV
          </button>
        </div>

        <!-- Input Mode Switcher -->
        <div class="import-subtabs">
          <button type="button" class="import-subtab active" id="tab-btn-file" data-tab="file">
            <i class="ph ph-upload-simple"></i> Upload File
          </button>
          <button type="button" class="import-subtab" id="tab-btn-text" data-tab="text">
            <i class="ph ph-code"></i> Paste Text / JSON
          </button>
        </div>

        <!-- Mode 1: File Upload -->
        <div id="import-panel-file">
          <div class="dropzone" id="import-dropzone">
            <input type="file" id="import-file-input" accept=".csv,.json,.txt,.tsv" style="display:none" />
            <i class="ph ph-cloud-arrow-up dropzone-icon"></i>
            <div class="dropzone-title">Click to browse or drag &amp; drop file here</div>
            <div class="dropzone-sub">Supported formats: CSV, TSV, JSON, TXT</div>
            <div id="import-file-info" style="display:none"></div>
          </div>
        </div>

        <!-- Mode 2: Paste Area -->
        <div id="import-panel-text" style="display:none">
          <textarea id="import-raw-text" class="import-textarea" placeholder="Paste CSV or JSON here...&#10;Example CSV:&#10;name,ip,group_name,device_type,hostname,notes&#10;Switch-Core,192.168.1.1,Network,Switch,core.lan,Main switch&#10;Server-DB,192.168.1.10,Servers,Server,db.lan,PostgreSQL&#10;&#10;Or simple list:&#10;192.168.1.20, Printer HP&#10;192.168.1.21, Workstation 01"></textarea>
        </div>

        <!-- Import Config Grid -->
        <div class="import-config-grid">
          <div class="form-group" style="margin:0">
            <label>If IP Already Exists</label>
            <select id="import-dup-action">
              <option value="update" selected>Update existing device details</option>
              <option value="skip">Skip duplicates (keep current)</option>
              <option value="error">Cancel on duplicate error</option>
            </select>
          </div>
          <div class="form-group" style="margin:0">
            <label>Default Group (if missing)</label>
            <input id="import-def-group" value="General" placeholder="e.g. General" />
          </div>
          <div class="form-group" style="margin:0">
            <label>Default Device Type (if missing)</label>
            <select id="import-def-type">${typeOpts}</select>
          </div>
          <div class="form-group" style="margin:0">
            <label>Auto-Generate Names</label>
            <select id="import-auto-name">
              <option value="ip">Use IP as Name if missing</option>
              <option value="hostname">Use Hostname as Name if missing</option>
            </select>
          </div>
        </div>

        <!-- Live Preview Section -->
        <div class="import-preview-box">
          <div class="import-preview-header">
            <span><i class="ph ph-table"></i> Parsed Preview (<span id="prev-count">0</span> items)</span>
            <div id="prev-badges" style="display:flex;gap:8px;font-size:11px"></div>
          </div>
          <div class="import-preview-body">
            <table style="width:100%">
              <thead>
                <tr>
                  <th style="width:36px">#</th>
                  <th>Name</th>
                  <th>IP Address</th>
                  <th>Type</th>
                  <th>Group</th>
                  <th>Hostname</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody id="import-preview-tbody">
                <tr><td colspan="7" style="text-align:center;color:var(--text-muted);padding:24px">
                  No data loaded yet. Upload a file or paste data above.
                </td></tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- Modal Actions -->
        <div class="form-actions" style="margin-top:8px">
          <button type="button" class="btn btn-ghost" id="import-btn-cancel">Cancel</button>
          <button type="button" class="btn btn-primary" id="import-btn-submit" disabled>
            <i class="ph ph-check"></i> Import Devices (<span id="import-valid-num">0</span>)
          </button>
        </div>
      </div>
    `;

    openModal('Import Devices in Batch', html, 'modal-lg');

    // ── Elements & State ────────────────────────────────────────────────────
    let currentRawContent = '';
    let parsedItems = [];

    const dropzone   = document.getElementById('import-dropzone');
    const fileInput  = document.getElementById('import-file-input');
    const fileInfo   = document.getElementById('import-file-info');
    const rawText    = document.getElementById('import-raw-text');
    const dupAction  = document.getElementById('import-dup-action');
    const defGroup   = document.getElementById('import-def-group');
    const defType    = document.getElementById('import-def-type');
    const autoName   = document.getElementById('import-auto-name');
    const btnSubmit  = document.getElementById('import-btn-submit');
    const prevTbody  = document.getElementById('import-preview-tbody');
    const prevCount  = document.getElementById('prev-count');
    const prevBadges = document.getElementById('prev-badges');
    const validNum   = document.getElementById('import-valid-num');

    // Tab Switching
    document.getElementById('tab-btn-file').addEventListener('click', () => {
      document.getElementById('tab-btn-file').classList.add('active');
      document.getElementById('tab-btn-text').classList.remove('active');
      document.getElementById('import-panel-file').style.display = '';
      document.getElementById('import-panel-text').style.display = 'none';
    });

    document.getElementById('tab-btn-text').addEventListener('click', () => {
      document.getElementById('tab-btn-text').classList.add('active');
      document.getElementById('tab-btn-file').classList.remove('active');
      document.getElementById('import-panel-text').style.display = '';
      document.getElementById('import-panel-file').style.display = 'none';
    });

    // File Input / Drag & Drop
    dropzone.addEventListener('click', (e) => {
      if (e.target.closest('#btn-remove-file')) return;
      fileInput.click();
    });

    ['dragenter', 'dragover'].forEach(name => {
      dropzone.addEventListener(name, (e) => {
        e.preventDefault();
        dropzone.classList.add('dragover');
      });
    });

    ['dragleave', 'drop'].forEach(name => {
      dropzone.addEventListener(name, (e) => {
        e.preventDefault();
        dropzone.classList.remove('dragover');
      });
    });

    dropzone.addEventListener('drop', (e) => {
      const files = e.dataTransfer.files;
      if (files.length > 0) handleFile(files[0]);
    });

    fileInput.addEventListener('change', () => {
      if (fileInput.files.length > 0) handleFile(fileInput.files[0]);
    });

    function handleFile(file) {
      const reader = new FileReader();
      reader.onload = (e) => {
        currentRawContent = e.target.result;
        rawText.value = currentRawContent;
        fileInfo.style.display = 'block';
        fileInfo.innerHTML = `
          <div class="import-file-badge">
            <i class="ph ph-file-text"></i>
            <span><strong>${escapeHtml(file.name)}</strong> (${(file.size / 1024).toFixed(1)} KB)</span>
            <button type="button" id="btn-remove-file" title="Remove file"><i class="ph ph-x-circle"></i></button>
          </div>
        `;
        document.getElementById('btn-remove-file')?.addEventListener('click', (ev) => {
          ev.stopPropagation();
          fileInput.value = '';
          currentRawContent = '';
          rawText.value = '';
          fileInfo.style.display = 'none';
          runParser();
        });
        runParser();
      };
      reader.readAsText(file);
    }

    rawText.addEventListener('input', () => {
      currentRawContent = rawText.value;
      runParser();
    });

    [dupAction, defGroup, defType, autoName].forEach(el => {
      el.addEventListener('change', runParser);
      el.addEventListener('input', runParser);
    });

    // Sample CSV Template Download
    document.getElementById('btn-download-sample').addEventListener('click', () => {
      const sampleCsv = `name,ip,group_name,device_type,hostname,notes\nCore Switch,192.168.1.1,Network,Switch,switch-01.lan,Main core distribution switch\nPrimary Router,192.168.1.254,Network,Router,gw.lan,Default gateway\nFile Server,192.168.1.10,Servers,Server,files.lan,Samba and NFS shares\nDatabase Server,192.168.1.11,Servers,Server,db.lan,PostgreSQL database cluster\nOffice AP Floor 1,192.168.1.50,Wireless,AP,ap-fl1.lan,Ubiquiti UniFi AP\nAdmin Workstation,192.168.1.101,IT,Workstation,admin-pc.lan,IT administrator desktop\nColor LaserJet,192.168.1.200,Printers,Printer,hp-color.lan,Marketing department printer\n`;
      downloadFile(sampleCsv, 'devices_sample_template.csv', 'text/csv');
    });

    // Parser Logic
    function runParser() {
      const text = currentRawContent.trim();
      if (!text) {
        parsedItems = [];
        prevTbody.innerHTML = `<tr><td colspan="7" style="text-align:center;color:var(--text-muted);padding:24px">No data loaded yet. Upload a file or paste data above.</td></tr>`;
        prevCount.textContent = '0';
        prevBadges.innerHTML = '';
        validNum.textContent = '0';
        btnSubmit.disabled = true;
        return;
      }

      parsedItems = parseRawInput(text, {
        defaultGroup: defGroup.value.trim() || 'General',
        defaultType: defType.value || 'Workstation',
        autoNameMode: autoName.value,
        existingDevices: _devices
      });

      renderPreview(parsedItems);
    }

    function renderPreview(items) {
      prevCount.textContent = items.length;
      const validCount = items.filter(i => i.isValid).length;
      const newCount = items.filter(i => i.isValid && !i.isExisting).length;
      const updateCount = items.filter(i => i.isValid && i.isExisting).length;
      const errorCount = items.filter(i => !i.isValid).length;

      validNum.textContent = validCount;
      btnSubmit.disabled = validCount === 0;

      prevBadges.innerHTML = `
        <span class="badge-status valid"><i class="ph ph-plus-circle"></i> ${newCount} New</span>
        ${updateCount > 0 ? `<span class="badge-status exists"><i class="ph ph-arrows-clockwise"></i> ${updateCount} Update</span>` : ''}
        ${errorCount > 0 ? `<span class="badge-status invalid"><i class="ph ph-warning-circle"></i> ${errorCount} Errors</span>` : ''}
      `;

      if (!items.length) {
        prevTbody.innerHTML = `<tr><td colspan="7" style="text-align:center;color:var(--text-muted);padding:24px">No valid records found in input.</td></tr>`;
        return;
      }

      prevTbody.innerHTML = items.map((item, idx) => {
        let statusBadge = '';
        if (!item.isValid) {
          statusBadge = `<span class="badge-status invalid" title="${escapeHtml(item.error)}"><i class="ph ph-x"></i> ${escapeHtml(item.error)}</span>`;
        } else if (item.isExisting) {
          const actionText = dupAction.value === 'skip' ? 'Skip' : (dupAction.value === 'error' ? 'Error' : 'Update');
          statusBadge = `<span class="badge-status exists"><i class="ph ph-arrows-clockwise"></i> ${actionText}</span>`;
        } else {
          statusBadge = `<span class="badge-status valid"><i class="ph ph-check"></i> Valid</span>`;
        }

        return `
          <tr style="${!item.isValid ? 'background:rgba(244,63,94,0.05)' : ''}">
            <td style="color:var(--text-muted)">${idx + 1}</td>
            <td><strong>${escapeHtml(item.name || '—')}</strong></td>
            <td><span class="mono">${escapeHtml(item.ip || '—')}</span></td>
            <td><i class="ph ${deviceTypeIcon(item.device_type)}"></i> ${escapeHtml(item.device_type)}</td>
            <td>${escapeHtml(item.group_name)}</td>
            <td class="mono" style="color:var(--text-secondary)">${escapeHtml(item.hostname || '—')}</td>
            <td>${statusBadge}</td>
          </tr>
        `;
      }).join('');
    }

    // Submit Batch
    btnSubmit.addEventListener('click', async () => {
      const validItems = parsedItems.filter(i => i.isValid).map(i => ({
        name: i.name,
        ip: i.ip,
        device_type: i.device_type,
        group_name: i.group_name,
        hostname: i.hostname || '',
        notes: i.notes || '',
        enabled: true
      }));

      if (!validItems.length) {
        return toast('No valid devices to import', 'error');
      }

      btnSubmit.disabled = true;
      btnSubmit.innerHTML = `<div class="spinner" style="width:14px;height:14px;border-width:2px;display:inline-block;vertical-align:middle;margin-right:6px"></div> Importing...`;

      try {
        const payload = {
          devices: validItems,
          on_duplicate: dupAction.value
        };

        const res = await API.post('/api/devices/batch', payload);
        closeModal();

        const addedMsg = res.added ? `${res.added} added` : '';
        const updatedMsg = res.updated ? `${res.updated} updated` : '';
        const skippedMsg = res.skipped ? `${res.skipped} skipped` : '';
        const parts = [addedMsg, updatedMsg, skippedMsg].filter(Boolean).join(', ');
        
        toast(`Batch import finished: ${parts || '0 devices'}`, 'success', 4500);

        if (res.errors && res.errors.length > 0) {
          toast(`${res.errors.length} item(s) had errors`, 'error', 5000);
        }

        await load();
      } catch(err) {
        toast(`Import failed: ${err.message}`, 'error', 5000);
        btnSubmit.disabled = false;
        btnSubmit.innerHTML = `<i class="ph ph-check"></i> Import Devices (${validItems.length})`;
      }
    });

    document.getElementById('import-btn-cancel').addEventListener('click', closeModal);
  }

  // ── Export to CSV ─────────────────────────────────────────────────────────
  function exportDevicesToCsv() {
    if (!_devices.length) {
      return toast('No devices to export', 'error');
    }

    const headers = ['name', 'ip', 'device_type', 'group_name', 'hostname', 'notes', 'enabled', 'created_at'];
    const rows = _devices.map(d => [
      escapeCsvValue(d.name),
      escapeCsvValue(d.ip),
      escapeCsvValue(d.device_type),
      escapeCsvValue(d.group_name),
      escapeCsvValue(d.hostname || ''),
      escapeCsvValue(d.notes || ''),
      d.enabled ? 'true' : 'false',
      escapeCsvValue(d.created_at || '')
    ].join(','));

    const csvContent = [headers.join(','), ...rows].join('\r\n');
    const dateStr = new Date().toISOString().slice(0, 10);
    downloadFile(csvContent, `netmanager_devices_${dateStr}.csv`, 'text/csv');
    toast(`Exported ${_devices.length} device(s) to CSV`, 'success');
  }

  load();
}

// ── Parser Utilities ────────────────────────────────────────────────────────
function parseRawInput(raw, opts) {
  const { defaultGroup, defaultType, autoNameMode, existingDevices } = opts;
  const existingIps = new Set(existingDevices.map(d => d.ip.toLowerCase().trim()));
  const seenInBatch = new Set();
  const results = [];

  // 1. Try parsing JSON
  if ((raw.startsWith('[') && raw.endsWith(']')) || (raw.startsWith('{') && raw.endsWith('}'))) {
    try {
      const parsed = JSON.parse(raw);
      const list = Array.isArray(parsed) ? parsed : [parsed];
      list.forEach((item, idx) => {
        const row = normalizeDeviceObj(item, idx, defaultGroup, defaultType, autoNameMode, existingIps, seenInBatch);
        if (row) results.push(row);
      });
      return results;
    } catch (_) {
      // If JSON parsing fails, fall back to line-by-line / CSV parsing
    }
  }

  // 2. Parse CSV / TSV / Delimited lines
  const lines = raw.split(/\r?\n/).map(l => l.trim()).filter(l => l.length > 0);
  if (lines.length === 0) return [];

  // Check if first line is a header
  const firstLine = lines[0].toLowerCase();
  let headers = null;
  let startIdx = 0;

  if (firstLine.includes('ip') || firstLine.includes('name') || firstLine.includes('host') || firstLine.includes('group')) {
    const rawHeaders = splitDelimitedLine(lines[0]);
    headers = rawHeaders.map(h => normalizeHeader(h));
    startIdx = 1;
  }

  for (let i = startIdx; i < lines.length; i++) {
    const line = lines[i];
    if (line.startsWith('#') || line.startsWith('//')) continue; // Skip comments

    const cols = splitDelimitedLine(line);
    let dev = {};

    if (headers && headers.length > 0) {
      headers.forEach((h, colIdx) => {
        if (h && cols[colIdx] !== undefined) {
          dev[h] = cols[colIdx].trim();
        }
      });
    } else {
      // Positional heuristic
      if (cols.length === 1) {
        dev.ip = cols[0].trim();
      } else if (cols.length === 2) {
        if (IP_REGEX.test(cols[0].trim())) {
          dev.ip = cols[0].trim();
          dev.name = cols[1].trim();
        } else {
          dev.name = cols[0].trim();
          dev.ip = cols[1].trim();
        }
      } else {
        // Assume name, ip, group, type, hostname, notes
        if (IP_REGEX.test(cols[0].trim())) {
          dev.ip = cols[0].trim();
          dev.name = cols[1].trim();
        } else {
          dev.name = cols[0].trim();
          dev.ip = cols[1].trim();
        }
        if (cols[2]) dev.group_name = cols[2].trim();
        if (cols[3]) dev.device_type = cols[3].trim();
        if (cols[4]) dev.hostname = cols[4].trim();
        if (cols[5]) dev.notes = cols[5].trim();
      }
    }

    const row = normalizeDeviceObj(dev, i, defaultGroup, defaultType, autoNameMode, existingIps, seenInBatch);
    if (row) results.push(row);
  }

  return results;
}

function splitDelimitedLine(line) {
  if (!line) return [];
  const delimiter = line.includes('\t') ? '\t' : (line.includes(';') && !line.includes(',') ? ';' : ',');
  const result = [];
  let current = '';
  let inQuotes = false;

  for (let i = 0; i < line.length; i++) {
    const char = line[i];
    if (char === '"') {
      if (inQuotes && line[i + 1] === '"') {
        current += '"';
        i++; // skip escaped quote
      } else {
        inQuotes = !inQuotes;
      }
    } else if (char === delimiter && !inQuotes) {
      result.push(current.trim());
      current = '';
    } else {
      current += char;
    }
  }
  result.push(current.trim());
  return result;
}

function normalizeHeader(h) {
  const clean = h.toLowerCase().replace(/[^a-z0-9_]/g, '');
  if (clean === 'ip' || clean === 'ipaddress' || clean === 'ip_address' || clean === 'address') return 'ip';
  if (clean === 'name' || clean === 'devicename' || clean === 'label') return 'name';
  if (clean === 'group' || clean === 'groupname' || clean === 'group_name' || clean === 'department') return 'group_name';
  if (clean === 'type' || clean === 'devicetype' || clean === 'device_type' || clean === 'category') return 'device_type';
  if (clean === 'host' || clean === 'hostname' || clean === 'fqdn') return 'hostname';
  if (clean === 'notes' || clean === 'note' || clean === 'description' || clean === 'comment') return 'notes';
  return clean;
}

function normalizeDeviceObj(item, idx, defGroup, defType, autoNameMode, existingIps, seenInBatch) {
  let ip = (item.ip || item.IP || item.ip_address || item.address || '').trim();
  let name = (item.name || item.Name || item.device_name || '').trim();
  let hostname = (item.hostname || item.Hostname || item.host || '').trim();
  let group_name = (item.group_name || item.group || item.Group || defGroup).trim();
  let device_type = (item.device_type || item.type || item.Type || defType).trim();
  let notes = (item.notes || item.Notes || item.description || '').trim();

  // Validate Type
  const matchedType = DEVICE_TYPES.find(t => t.toLowerCase() === device_type.toLowerCase());
  if (matchedType) device_type = matchedType;
  else device_type = defType;

  // Auto name resolution
  if (!name) {
    if (autoNameMode === 'hostname' && hostname) name = hostname;
    else if (ip) name = ip;
    else name = `Device-${idx + 1}`;
  }

  let isValid = true;
  let error = '';

  if (!ip) {
    isValid = false;
    error = 'Missing IP address';
  } else if (!IP_REGEX.test(ip)) {
    isValid = false;
    error = 'Invalid IP address format';
  } else if (seenInBatch.has(ip.toLowerCase())) {
    isValid = false;
    error = 'Duplicate IP in batch';
  } else {
    seenInBatch.add(ip.toLowerCase());
  }

  const isExisting = isValid && existingIps.has(ip.toLowerCase());

  return {
    rawIndex: idx,
    name,
    ip,
    hostname,
    group_name: group_name || defGroup,
    device_type: device_type || defType,
    notes,
    isValid,
    isExisting,
    error
  };
}

function escapeHtml(str) {
  if (str === null || str === undefined) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

function escapeCsvValue(str) {
  const val = String(str || '');
  if (val.includes(',') || val.includes('"') || val.includes('\n')) {
    return `"${val.replace(/"/g, '""')}"`;
  }
  return val;
}

function downloadFile(content, fileName, mimeType) {
  const blob = new Blob([content], { type: `${mimeType};charset=utf-8;` });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.setAttribute('href', url);
  link.setAttribute('download', fileName);
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}


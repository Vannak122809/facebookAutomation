import { renderDashboard } from './dashboard.js?v=2.3';
import { renderDevices }   from './devices.js?v=2.3';
import { renderScanner }   from './scanner.js?v=2.3';
import { renderAnydesk }   from './anydesk.js?v=2.3';
import { renderLogs, updateBadge } from './logs.js?v=2.3';
import { renderRemote }    from './remote.js?v=2.3';
import { connectWS }       from './ws.js?v=2.3';
import { closeModal }      from './utils.js?v=2.3';

// ── Clock ─────────────────────────────────────────────────────────────────────
function startClock() {
  const el = document.getElementById('clock');
  const tick = () => {
    const now = new Date();
    el.textContent = now.toLocaleTimeString('en-GB', { hour:'2-digit', minute:'2-digit', second:'2-digit' });
  };
  tick();
  setInterval(tick, 1000);
}

// ── Router ────────────────────────────────────────────────────────────────────
const PAGES = {
  dashboard: { title: 'Dashboard',        render: renderDashboard },
  devices:   { title: 'Device Manager',   render: renderDevices },
  scanner:   { title: 'Network Scanner',  render: renderScanner },
  anydesk:   { title: 'AnyDesk Diagnostics', render: renderAnydesk },
  logs:      { title: 'Alerts',              render: renderLogs },
  remote:    { title: 'Remote Sessions',     render: renderRemote },
};

let _currentPage = null;

async function navigate(page) {
  if (!PAGES[page]) page = 'dashboard';
  if (_currentPage === page) return;
  _currentPage = page;

  // Update sidebar active state
  document.querySelectorAll('.nav-item').forEach(a => {
    a.classList.toggle('active', a.dataset.page === page);
  });

  // Update page title
  document.getElementById('page-title').textContent = PAGES[page].title;

  // Hide all pages, show target
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  const container = document.getElementById(`page-${page}`);
  if (container) {
    container.classList.add('active');
    container.innerHTML = ''; // clear previous render
    await PAGES[page].render(container);
  }

  // Close sidebar on mobile
  document.getElementById('sidebar').classList.remove('open');
}

// ── Init ──────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', async () => {
  startClock();
  connectWS();

  // Nav clicks
  document.querySelectorAll('.nav-item').forEach(a => {
    a.addEventListener('click', e => {
      e.preventDefault();
      navigate(a.dataset.page);
    });
  });

  // Mobile menu toggle
  document.getElementById('menu-toggle').addEventListener('click', () => {
    document.getElementById('sidebar').classList.toggle('open');
  });

  // Modal close
  document.getElementById('modal-close').addEventListener('click', closeModal);
  document.getElementById('modal-overlay').addEventListener('click', e => {
    if (e.target === document.getElementById('modal-overlay')) closeModal();
  });

  // Hash-based routing
  const initialPage = location.hash.replace('#', '') || 'dashboard';
  await navigate(initialPage);

  // Poll alert badge every 60s
  updateBadge();
  setInterval(updateBadge, 60000);
});

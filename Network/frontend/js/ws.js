// WebSocket client — real-time updates from backend
let _ws = null;
let _reconnectTimer = null;
const WS_URL = `ws://${location.host}/ws/live`;

export function connectWS() {
  clearTimeout(_reconnectTimer);
  try {
    _ws = new WebSocket(WS_URL);
  } catch(e) { scheduleReconnect(); return; }

  _ws.onopen = () => {
    console.log('[WS] Connected');
    setIndicator(true);
    // keep-alive ping every 20s
    _ws._ping = setInterval(() => {
      if (_ws.readyState === WebSocket.OPEN) _ws.send('ping');
    }, 20000);
  };

  _ws.onmessage = (ev) => {
    try {
      const data = JSON.parse(ev.data);
      if (data.type === 'pong') return;
      // Route to active page handler
      if (typeof window._dashUpdate === 'function') window._dashUpdate(data);
      // Update alert badge
      if (data.unread_alerts !== undefined) {
        const badge = document.getElementById('alert-badge');
        if (badge) {
          badge.textContent = data.unread_alerts || '';
          badge.style.display = data.unread_alerts > 0 ? '' : 'none';
        }
      }
    } catch(_) {}
  };

  _ws.onclose = () => {
    clearInterval(_ws._ping);
    setIndicator(false);
    scheduleReconnect();
  };

  _ws.onerror = () => {
    _ws.close();
  };
}

function scheduleReconnect() {
  setIndicator(false);
  _reconnectTimer = setTimeout(connectWS, 5000);
}

function setIndicator(connected) {
  const dot   = document.getElementById('ws-indicator');
  const label = document.getElementById('ws-label');
  if (dot) {
    dot.className = `status-dot ${connected ? 'connected' : 'disconnected'}`;
  }
  if (label) label.textContent = connected ? 'Live' : 'Reconnecting…';
}

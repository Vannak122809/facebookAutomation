import asyncio
import os
import platform
import re
import socket
import subprocess
import psutil
from datetime import datetime
from typing import Dict, Any, List, Optional

SYSTEM = platform.system().lower()

# ─── AnyDesk log/config paths per OS ──────────────────────────────────────────
def _anydesk_paths() -> Dict[str, str]:
    if SYSTEM == "windows":
        appdata = os.environ.get("APPDATA", "C:\\Users\\Default\\AppData\\Roaming")
        programdata = os.environ.get("PROGRAMDATA", "C:\\ProgramData")
        return {
            "trace_log": os.path.join(appdata, "AnyDesk", "ad.trace"),
            "service_conf": os.path.join(programdata, "AnyDesk", "service.conf"),
            "process_name": "anydesk.exe",
            "service_name": "AnyDesk",
        }
    elif SYSTEM == "darwin":
        home = os.path.expanduser("~")
        return {
            "trace_log": os.path.join(home, "Library", "Application Support", "AnyDesk", "ad.trace"),
            "service_conf": "/Library/Application Support/AnyDesk/service.conf",
            "process_name": "AnyDesk",
            "service_name": "com.anydesk.anydesk",
        }
    else:  # linux
        home = os.path.expanduser("~")
        return {
            "trace_log": os.path.join(home, ".anydesk", "ad.trace"),
            "service_conf": "/etc/anydesk/service.conf",
            "process_name": "anydesk",
            "service_name": "anydesk",
        }

ANYDESK_RELAY_HOSTS = [
    "relay.anydesk.com",
    "relay-eu.anydesk.com",
    "relay-us.anydesk.com",
]
ANYDESK_PORTS = [80, 443, 7070]

# ─── Individual Checks ────────────────────────────────────────────────────────

def _check_process() -> Dict[str, Any]:
    paths = _anydesk_paths()
    proc_name = paths["process_name"].lower()
    running = []
    for proc in psutil.process_iter(["pid", "name", "status", "create_time"]):
        try:
            if proc_name in proc.info["name"].lower():
                running.append({
                    "pid": proc.info["pid"],
                    "name": proc.info["name"],
                    "status": proc.info["status"],
                    "started": datetime.fromtimestamp(proc.info["create_time"]).isoformat(),
                })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return {
        "check": "process",
        "ok": len(running) > 0,
        "detail": f"AnyDesk process found ({len(running)} instance(s))" if running else "AnyDesk process NOT running",
        "data": running,
        "fix": None if running else "Start AnyDesk application or service",
    }


def _check_service_windows() -> Dict[str, Any]:
    try:
        result = subprocess.run(
            ["sc", "query", "AnyDesk"],
            capture_output=True, text=True, timeout=5
        )
        out = result.stdout
        if "RUNNING" in out:
            return {"check": "service", "ok": True, "detail": "AnyDesk Windows service is RUNNING", "fix": None}
        elif "STOPPED" in out:
            return {"check": "service", "ok": False, "detail": "AnyDesk Windows service is STOPPED",
                    "fix": "Run: sc start AnyDesk  (or open Services → AnyDesk → Start)"}
        else:
            return {"check": "service", "ok": False, "detail": "AnyDesk service not installed", "fix": "Install AnyDesk as a service from its settings"}
    except Exception as e:
        return {"check": "service", "ok": None, "detail": f"Service check failed: {e}", "fix": None}


def _check_service_linux() -> Dict[str, Any]:
    try:
        result = subprocess.run(
            ["systemctl", "is-active", "anydesk"],
            capture_output=True, text=True, timeout=5
        )
        active = result.stdout.strip() == "active"
        return {
            "check": "service",
            "ok": active,
            "detail": f"AnyDesk systemd service: {result.stdout.strip()}",
            "fix": None if active else "Run: sudo systemctl start anydesk",
        }
    except Exception as e:
        return {"check": "service", "ok": None, "detail": f"systemctl check failed: {e}", "fix": None}


async def _check_relay_connectivity() -> List[Dict[str, Any]]:
    results = []
    loop = asyncio.get_event_loop()

    for host in ANYDESK_RELAY_HOSTS:
        # Resolve IP
        try:
            ip = await loop.run_in_executor(None, lambda h=host: socket.gethostbyname(h))
        except Exception:
            results.append({
                "host": host, "ip": None,
                "ping": False, "ports": [],
                "ok": False,
                "detail": f"DNS resolution FAILED for {host}",
                "fix": "Check DNS settings or internet connectivity",
            })
            continue

        # Ping
        ping_result = await _async_ping(ip)

        # Port checks
        port_results = []
        for port in ANYDESK_PORTS:
            pr = await _tcp_connect(ip, port)
            port_results.append(pr)

        any_port_open = any(p["open"] for p in port_results)
        ok = ping_result or any_port_open

        results.append({
            "host": host,
            "ip": ip,
            "ping": ping_result,
            "ports": port_results,
            "ok": ok,
            "detail": f"Relay {host} reachable via " + (
                ", ".join(f"port {p['port']}" for p in port_results if p["open"])
                if any_port_open else "NO ports open"
            ),
            "fix": None if ok else f"Unblock outbound TCP 80/443/7070 to {host} in your firewall",
        })
    return results


async def _async_ping(ip: str, timeout: float = 2.0) -> bool:
    system = platform.system().lower()
    if system == "windows":
        cmd = ["ping", "-n", "1", "-w", str(int(timeout * 1000)), ip]
    else:
        cmd = ["ping", "-c", "1", "-W", str(int(timeout)), ip]
    try:
        loop = asyncio.get_event_loop()
        r = await loop.run_in_executor(
            None,
            lambda: subprocess.run(cmd, capture_output=True, timeout=timeout + 1)
        )
        return r.returncode == 0
    except Exception:
        return False


async def _tcp_connect(host: str, port: int, timeout: float = 3.0) -> Dict[str, Any]:
    try:
        future = asyncio.open_connection(host, port)
        reader, writer = await asyncio.wait_for(future, timeout=timeout)
        writer.close()
        await writer.wait_closed()
        return {"port": port, "open": True, "error": None}
    except asyncio.TimeoutError:
        return {"port": port, "open": False, "error": "timeout"}
    except Exception as e:
        return {"port": port, "open": False, "error": str(e)}


def _read_config() -> Dict[str, Any]:
    paths = _anydesk_paths()
    conf_path = paths["service_conf"]
    if not os.path.exists(conf_path):
        return {
            "check": "config",
            "ok": None,
            "detail": f"Config file not found: {conf_path}",
            "data": {},
            "fix": "AnyDesk may not be installed as a service",
        }
    try:
        with open(conf_path, "r", errors="replace") as f:
            content = f.read()
        parsed = {}
        for line in content.splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                parsed[k.strip()] = v.strip()
        return {
            "check": "config",
            "ok": True,
            "detail": f"Config loaded from {conf_path}",
            "data": parsed,
            "fix": None,
        }
    except Exception as e:
        return {"check": "config", "ok": False, "detail": str(e), "data": {}, "fix": None}


def _parse_trace_log(max_lines: int = 200) -> Dict[str, Any]:
    paths = _anydesk_paths()
    log_path = paths["trace_log"]
    if not os.path.exists(log_path):
        return {
            "check": "log",
            "ok": None,
            "detail": f"Log file not found: {log_path}",
            "entries": [],
            "errors": [],
            "fix": "AnyDesk hasn't been run yet, or log path differs",
        }
    try:
        with open(log_path, "r", errors="replace") as f:
            lines = f.readlines()

        recent = lines[-max_lines:]
        entries = []
        errors = []

        ERROR_PATTERNS = {
            "auth_failed": (re.compile(r"auth.*fail|login.*fail|unauthorized", re.I), "Authentication failure — check AnyDesk account/password"),
            "relay_timeout": (re.compile(r"relay.*timeout|connection.*timeout", re.I), "Relay connection timed out — relay ports may be blocked"),
            "firewall_block": (re.compile(r"firewall|blocked|refused|ECONNREFUSED", re.I), "Firewall is blocking AnyDesk connections"),
            "nat_fail": (re.compile(r"NAT.*fail|stun.*fail|peer.*unreachable", re.I), "NAT traversal failed — symmetric NAT detected"),
            "no_network": (re.compile(r"no.*network|network.*unreachable|socket.*error", re.I), "No network / socket error"),
            "ssl_error": (re.compile(r"ssl.*error|tls.*error|certificate", re.I), "TLS/SSL error — possible MITM or cert issue"),
        }

        for line in recent:
            line = line.rstrip()
            entry = {"raw": line, "level": "INFO", "issues": []}
            for issue_key, (pattern, fix) in ERROR_PATTERNS.items():
                if pattern.search(line):
                    entry["level"] = "ERROR"
                    entry["issues"].append({"key": issue_key, "fix": fix})
                    errors.append({"line": line, "issue": issue_key, "fix": fix})
            entries.append(entry)

        return {
            "check": "log",
            "ok": len(errors) == 0,
            "detail": f"Parsed {len(recent)} log lines, found {len(errors)} issue(s)",
            "entries": entries,
            "errors": errors[:20],
            "log_path": log_path,
            "fix": None,
        }
    except Exception as e:
        return {"check": "log", "ok": False, "detail": str(e), "entries": [], "errors": [], "fix": None}


def _check_nat_type() -> Dict[str, Any]:
    """Simple NAT detection by checking external IP via multiple services."""
    import urllib.request
    try:
        with urllib.request.urlopen("https://api.ipify.org", timeout=5) as r:
            external_ip = r.read().decode().strip()
        return {
            "check": "nat",
            "ok": True,
            "detail": f"External IP: {external_ip} — Internet reachable",
            "external_ip": external_ip,
            "fix": None,
        }
    except Exception as e:
        return {
            "check": "nat",
            "ok": False,
            "detail": f"Cannot reach internet: {e}",
            "external_ip": None,
            "fix": "Check internet connection / DNS",
        }


# ─── Main diagnostic runner ───────────────────────────────────────────────────

async def run_full_diagnostic() -> Dict[str, Any]:
    results = {}

    # Process check
    results["process"] = _check_process()

    # Service check
    if SYSTEM == "windows":
        results["service"] = _check_service_windows()
    elif SYSTEM == "linux":
        results["service"] = _check_service_linux()
    else:
        results["service"] = {"check": "service", "ok": None, "detail": "macOS — service check via launchctl not implemented", "fix": None}

    # Relay connectivity (async)
    relay_results = await _check_relay_connectivity()
    results["relay"] = {
        "check": "relay",
        "ok": any(r["ok"] for r in relay_results),
        "detail": f"{sum(1 for r in relay_results if r['ok'])}/{len(relay_results)} relay servers reachable",
        "servers": relay_results,
        "fix": None if any(r["ok"] for r in relay_results) else "Unblock outbound ports 80/443/7070 in firewall",
    }

    # Config
    results["config"] = _read_config()

    # Log parse
    results["log"] = _parse_trace_log()

    # NAT / internet
    loop = asyncio.get_event_loop()
    results["nat"] = await loop.run_in_executor(None, _check_nat_type)

    # Overall score
    checks = [v for v in results.values() if isinstance(v.get("ok"), bool)]
    passed = sum(1 for c in checks if c["ok"])
    total = len(checks)
    results["summary"] = {
        "passed": passed,
        "total": total,
        "score": int((passed / total) * 100) if total else 0,
        "overall": "HEALTHY" if passed == total else ("DEGRADED" if passed >= total // 2 else "FAILING"),
        "timestamp": datetime.utcnow().isoformat(),
    }

    return results


async def tail_anydesk_log(lines: int = 50) -> List[str]:
    paths = _anydesk_paths()
    log_path = paths["trace_log"]
    if not os.path.exists(log_path):
        return [f"[NOT FOUND] {log_path}"]
    try:
        with open(log_path, "r", errors="replace") as f:
            all_lines = f.readlines()
        return [l.rstrip() for l in all_lines[-lines:]]
    except Exception as e:
        return [f"[ERROR] {e}"]

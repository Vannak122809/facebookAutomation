# backend/services/printer_check.py
"""Canon iR-ADV C5235 printer counter service.
Login: POST /login  { deptid, password, uri=/rps/ }
Counter page: GET /rps/dcounter.cgi?CorePGTAG=14

Counter data is embedded in two JS patterns:
  1. write_value("TYPE_CODE", VALUE)      → Main Counter section
  2. check_type(TYPE_CODE) ... <td>VALUE< → Send Application section
"""
import re
from datetime import datetime
from typing import Dict, Any, List
import requests

requests.packages.urllib3.disable_warnings()

# ── Type code → Section + Label mapping ───────────────────────────────────────
# Mirrors exactly what is displayed on the Canon iR-ADV C5235 Counter Check page
MAIN_COUNTER_TYPES = {
    "112": "112 : Total (Black/Large)",
    "102": "102 : Total 2 (Color)",
    "101": "101 : Total 1",
    "108": "108 : Total (Large)",
}

SEND_APP_TYPES = {
    "2003": "Black Scan (Total 1)",
    "4000": "Black Scan 1",
    "4001": "Black Scan 2",
    "4002": "Black Scan 3",
    "4003": "Black Scan 4",
    "2006": "Color Scan (Total 1)",
    "3000": "Color Scan 1",
    "3001": "Color Scan 2",
    "3002": "Color Scan 3",
    "3003": "Color Scan 4",
    "5010": "Send (Trial Version)",
}


def check_printer_counter(ip: str, dept_id: str = "999", pin: str = "9900") -> Dict[str, Any]:
    """Login to Canon iR-ADV Remote UI and return all page counters grouped by section."""
    base = f"http://{ip}:8000"
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0"})

    # ── Step 1: Login ──────────────────────────────────────────────────────────
    try:
        r_login = session.post(
            base + "/login",
            data={"deptid": dept_id, "username": dept_id, "password": pin, "uri": "/rps/"},
            timeout=10, verify=False, allow_redirects=False,
        )
        
        # If HTTP 200, it usually means it just re-rendered the login page because of bad credentials.
        # Fallback to administrator account per clack's orders!
        if r_login.status_code == 200:
            r_login = session.post(
                base + "/login",
                data={
                    "username": "administrator",
                    "password": "7654321", 
                    "uri": "/rps/"
                },
                timeout=10, verify=False, allow_redirects=False,
            )

        if r_login.status_code not in (200, 302):
            return _error(ip, dept_id, pin, f"Login returned HTTP {r_login.status_code}")

        if r_login.status_code == 302:
            location = r_login.headers.get("Location", base + "/rps/")
            session.get(location, timeout=10, verify=False, allow_redirects=True)

    except requests.RequestException as e:
        return _error(ip, dept_id, pin, f"Cannot reach printer: {e}")

    # ── Step 2: Navigate to sysmonitor (sets session context for dcounter) ─────
    try:
        r_sm = session.get(base + "/sysmonitor/", timeout=10, verify=False,
                           allow_redirects=True)
        # Redirect lands on /rps/nativetop.cgi – strip filename to get base
        counter_base = re.sub(r'/[^/]*$', '/', r_sm.url)
        counter_url = counter_base + "dcounter.cgi?CorePGTAG=14"
    except requests.RequestException as e:
        return _error(ip, dept_id, pin, f"Could not load sysmonitor: {e}")

    # ── Step 3: Fetch counter page ─────────────────────────────────────────────
    try:
        r_cnt = session.get(counter_url, timeout=10, verify=False,
                            headers={"Referer": r_sm.url})
        if r_cnt.status_code != 200 or len(r_cnt.text) < 500:
            return _error(ip, dept_id, pin,
                          f"Counter page HTTP {r_cnt.status_code} (url={counter_url})")
        html = r_cnt.text
    except requests.RequestException as e:
        return _error(ip, dept_id, pin, f"Could not load counter page: {e}")

    # ── Step 4: Parse Main Counter (write_value pattern) ──────────────────────
    main_counters: Dict[str, int] = {}
    for code, value in re.findall(r'write_value\(["\'](\d+)["\']\s*,\s*(\d+)\)', html):
        label = MAIN_COUNTER_TYPES.get(code, f"Counter {code}")
        main_counters[label] = int(value)

    # ── Step 5: Parse Send Application counters (check_type + <td>VALUE< pattern)
    send_counters: Dict[str, int] = {}
    for m in re.finditer(r'check_type\((\d+)\)', html):
        code = m.group(1)
        snippet = html[m.start(): m.start() + 350]
        nums = re.findall(r'<td>(\d+)<', snippet)
        if nums and code in SEND_APP_TYPES:
            send_counters[SEND_APP_TYPES[code]] = int(nums[0])

    # ── Step 6: Extract metadata ───────────────────────────────────────────────
    # Model name
    model_match = re.search(r'deviceName[^>]*>(.*?)<\\/span>', html)
    model = (model_match.group(1).replace("\\xa0", " ").strip()
             if model_match else "Canon iR-ADV C5235")

    # Send Application ID
    app_id_match = re.search(r'Application ID\s*:\s*([a-f0-9\-]{32,})', html)
    app_id = app_id_match.group(1).strip() if app_id_match else ""

    # Last Updated timestamp from page
    date_match = re.search(r'Last Updated\s*:\s*([\d/\s:]+)', html)
    device_date = (date_match.group(1).strip()
                   if date_match else datetime.utcnow().strftime("%d/%m/%Y %H:%M:%S"))

    # If parsing failed entirely (e.g. wrong brand), fallback to SNMP
    if not main_counters:
        snmp_res = get_snmp_counter(ip)
        if snmp_res:
            return snmp_res

    return {
        "success": True,
        "ip": ip,
        "dept_id": dept_id,
        "model": model,
        "app_id": app_id,
        "device_date": device_date,
        "main_counter": main_counters,
        "send_counter": send_counters,
        # Flat counters for backward compat
        "counters": {**main_counters, **send_counters},
        "checked_at": datetime.utcnow().isoformat(),
    }


def _error(ip: str, dept_id: str, pin: str, msg: str) -> Dict[str, Any]:
    # Attempt SNMP before finally giving up
    snmp_res = get_snmp_counter(ip)
    if snmp_res:
        return snmp_res

    return {
        "success": False,
        "error": msg,
        "ip": ip,
        "dept_id": dept_id,
        "checked_at": datetime.utcnow().isoformat(),
    }

import subprocess

def get_snmp_counter(ip: str) -> Dict[str, Any]:
    """Fallback to universal SNMP to fetch counters for any brand (HP, Epson, Ricoh, etc)."""
    try:
        # standard OID for Total Printed Pages (prtMarkerLifeCount)
        cmd = ["snmpget", "-v1", "-c", "public", "-Oqv", ip, "1.3.6.1.2.1.43.10.2.1.4.1.1"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            val = result.stdout.strip()
            if val.isdigit():
                # Attempt to get Printer Model via hrDeviceDescr
                model_cmd = ["snmpget", "-v1", "-c", "public", "-Oqv", ip, "1.3.6.1.2.1.25.3.2.1.3.1"]
                model_res = subprocess.run(model_cmd, capture_output=True, text=True, timeout=5)
                model = model_res.stdout.strip().strip('"') if model_res.returncode == 0 else "Generic SNMP Printer"
                
                return {
                    "success": True,
                    "ip": ip,
                    "dept_id": "SNMP",
                    "model": model,
                    "app_id": "SNMP Fetch",
                    "device_date": datetime.utcnow().strftime("%d/%m/%Y %H:%M:%S"),
                    "main_counter": {"Total Printed Pages (SNMP)": int(val)},
                    "send_counter": {},
                    "counters": {"Total": int(val)},
                    "checked_at": datetime.utcnow().isoformat(),
                }
    except Exception:
        pass
    return None

import asyncio
import socket
import platform
import subprocess
import ipaddress
from datetime import datetime
from typing import List, Dict, Any, Optional

# ─── ICMP Ping (cross-platform) ───────────────────────────────────────────────

async def ping_host(ip: str, count: int = 3, timeout: float = 1.5) -> Dict[str, Any]:
    """Async ping using subprocess so it works without root on all platforms."""
    system = platform.system().lower()
    if system == "windows":
        cmd = ["ping", "-n", str(count), "-w", str(int(timeout * 1000)), ip]
    else:
        cmd = ["ping", "-c", str(count), "-W", str(int(timeout)), ip]

    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: subprocess.run(cmd, capture_output=True, text=True, timeout=timeout * count + 2)
        )
        output = result.stdout + result.stderr
        if result.returncode == 0:
            latency = _parse_ping_latency(output, system)
            return {"status": "UP", "latency_ms": latency, "output": output}
        else:
            return {"status": "DOWN", "latency_ms": 0.0, "output": output}
    except Exception as e:
        return {"status": "DOWN", "latency_ms": 0.0, "output": str(e)}


def _parse_ping_latency(output: str, system: str) -> float:
    """Extract average latency from ping output."""
    import re
    if system == "windows":
        m = re.search(r"Average = (\d+)ms", output)
        return float(m.group(1)) if m else 0.0
    else:
        m = re.search(r"min/avg/max.*?= [\d.]+/([\d.]+)/[\d.]+", output)
        if m:
            return float(m.group(1))
        m = re.search(r"time=([\d.]+) ms", output)
        return float(m.group(1)) if m else 0.0


# ─── Port Check ───────────────────────────────────────────────────────────────

async def check_port(ip: str, port: int, timeout: float = 2.0) -> Dict[str, Any]:
    """TCP port connectivity check."""
    loop = asyncio.get_event_loop()
    try:
        future = asyncio.open_connection(ip, port)
        reader, writer = await asyncio.wait_for(future, timeout=timeout)
        writer.close()
        await writer.wait_closed()
        return {"port": port, "open": True, "error": None}
    except asyncio.TimeoutError:
        return {"port": port, "open": False, "error": "timeout"}
    except ConnectionRefusedError:
        return {"port": port, "open": False, "error": "refused"}
    except Exception as e:
        return {"port": port, "open": False, "error": str(e)}


async def check_ports(ip: str, ports: List[int]) -> List[Dict[str, Any]]:
    tasks = [check_port(ip, p) for p in ports]
    return await asyncio.gather(*tasks)


# ─── Hostname Resolution ───────────────────────────────────────────────────────

def _get_netbios_sync(ip: str, timeout: float = 0.15) -> str:
    try:
        query = (
            b"\x13\x37\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00"
            b"\x20CKAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA\x00\x00\x21\x00\x01"
        )
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(timeout)
        sock.sendto(query, (ip, 137))
        data, _ = sock.recvfrom(1024)
        sock.close()
        if len(data) > 56:
            num_names = data[56]
            offset = 57
            for _ in range(num_names):
                name = data[offset:offset+15].decode("ascii", errors="ignore").strip()
                name_type = data[offset+15]
                if name_type == 0x00 and name and not name.startswith("__MSBROWSE__"):
                    return name
                offset += 18
    except Exception:
        pass
    return ""

async def resolve_hostname(ip: str) -> str:
    loop = asyncio.get_event_loop()
    # 1. Try NetBIOS
    nb = await loop.run_in_executor(None, lambda: _get_netbios_sync(ip))
    if nb:
        return nb
    # 2. Try reverse DNS
    try:
        result = await loop.run_in_executor(None, lambda: socket.gethostbyaddr(ip))
        return result[0]
    except Exception:
        return ""


# ─── Subnet Scanner ───────────────────────────────────────────────────────────

async def scan_subnet(cidr: str, timeout: float = 1.0) -> List[Dict[str, Any]]:
    """Ping-sweep a subnet concurrently. Returns list of alive hosts with resolved device names."""
    try:
        network = ipaddress.ip_network(cidr, strict=False)
    except ValueError as e:
        return [{"error": str(e)}]

    hosts = list(network.hosts())
    # Limit to first 254 hosts for speed
    hosts = hosts[:254]

    # Fetch DB devices
    db_map = {}
    try:
        from database import AsyncSessionLocal, Device
        from sqlalchemy import select
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(Device))
            for d in result.scalars().all():
                db_map[d.ip.strip().lower()] = {
                    "id": d.id,
                    "name": d.name,
                    "device_type": d.device_type or "Workstation",
                    "group_name": d.group_name or "General"
                }
    except Exception:
        pass

    semaphore = asyncio.Semaphore(50)  # max concurrent pings

    async def _check(ip_obj):
        async with semaphore:
            ip = str(ip_obj)
            result = await ping_host(ip, count=1, timeout=timeout)
            device_name = ""
            device_type = "Workstation"
            is_registered = False

            if result["status"] == "UP":
                ip_lower = ip.lower()
                if ip_lower in db_map:
                    device_name = db_map[ip_lower]["name"]
                    device_type = db_map[ip_lower]["device_type"]
                    is_registered = True
                else:
                    device_name = await resolve_hostname(ip)
                    if device_name.upper().startswith("NPI") or device_name.upper().startswith("CANON"):
                        device_type = "Printer"

            return {
                "ip": ip,
                "status": result["status"],
                "latency_ms": result["latency_ms"],
                "hostname": device_name,
                "device_name": device_name,
                "device_type": device_type,
                "is_registered": is_registered,
            }

    results = await asyncio.gather(*[_check(h) for h in hosts])
    return [r for r in results if r["status"] == "UP"]


# ─── Traceroute ───────────────────────────────────────────────────────────────

async def traceroute(ip: str, max_hops: int = 20) -> List[Dict[str, Any]]:
    system = platform.system().lower()
    if system == "windows":
        cmd = ["tracert", "-d", "-h", str(max_hops), "-w", "1000", ip]
    else:
        cmd = ["traceroute", "-n", "-m", str(max_hops), "-w", "1", ip]

    hops = []
    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        )
        hops = _parse_traceroute(result.stdout, system)
    except Exception as e:
        hops = [{"hop": 1, "ip": "error", "latency_ms": 0, "note": str(e)}]
    return hops


def _parse_traceroute(output: str, system: str) -> List[Dict[str, Any]]:
    import re
    hops = []
    lines = output.strip().splitlines()
    for line in lines:
        if system == "windows":
            m = re.match(r"\s*(\d+)\s+(?:\*|(\d+)\s+ms).*?([\d.]+)\s*$", line)
            if m:
                hops.append({
                    "hop": int(m.group(1)),
                    "ip": m.group(3) or "*",
                    "latency_ms": int(m.group(2)) if m.group(2) else None,
                })
        else:
            m = re.match(r"\s*(\d+)\s+\*|\s*(\d+)\s+([\d.]+)\s+([\d.]+)\s+ms", line)
            if m:
                if m.group(1):
                    hops.append({"hop": int(m.group(1)), "ip": "*", "latency_ms": None})
                else:
                    hops.append({
                        "hop": int(m.group(2)),
                        "ip": m.group(3),
                        "latency_ms": float(m.group(4)),
                    })
    return hops

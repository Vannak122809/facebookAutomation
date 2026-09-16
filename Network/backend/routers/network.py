from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from services.network_scanner import ping_host, check_ports, scan_subnet, traceroute, resolve_hostname
from services.net_tools import send_wake_on_lan, get_arp_table, calculate_subnet, check_ssl_certificate, resolve_dns_records
from database import AsyncSessionLocal, PingHistory, Device
from sqlalchemy import select, desc
from datetime import datetime

router = APIRouter(prefix="/api/network", tags=["network"])


class PingRequest(BaseModel):
    ip: str
    count: Optional[int] = 3

class PortScanRequest(BaseModel):
    ip: str
    ports: Optional[List[int]] = [22, 80, 443, 3389, 8080, 21, 25, 3306, 5432, 27017]

class SubnetScanRequest(BaseModel):
    cidr: str

class TracerouteRequest(BaseModel):
    ip: str
    max_hops: Optional[int] = 20

class WolRequest(BaseModel):
    mac: str
    broadcast_ip: Optional[str] = "255.255.255.255"
    port: Optional[int] = 9

class PrinterCounterRequest(BaseModel):
    ip: str
    dept_id: Optional[str] = "999"
    pin: Optional[str] = "9900"

class SubnetCalcRequest(BaseModel):
    cidr: str

class SslCheckRequest(BaseModel):
    host: str
    port: Optional[int] = 443

class DnsLookupRequest(BaseModel):
    domain: str


# ── Core Network Endpoints ───────────────────────────────────────────────────

@router.post("/ping")
async def ping_endpoint(body: PingRequest):
    result = await ping_host(body.ip, count=body.count)
    hostname = await resolve_hostname(body.ip) if result["status"] == "UP" else ""
    return {**result, "ip": body.ip, "hostname": hostname, "timestamp": datetime.utcnow().isoformat()}


@router.post("/portscan")
async def port_scan(body: PortScanRequest):
    results = await check_ports(body.ip, body.ports)
    return {"ip": body.ip, "ports": results, "open_count": sum(1 for r in results if r["open"]),
            "timestamp": datetime.utcnow().isoformat()}


@router.post("/scan")
async def subnet_scan(body: SubnetScanRequest):
    hosts = await scan_subnet(body.cidr)
    return {"cidr": body.cidr, "alive_count": len(hosts), "hosts": hosts,
            "timestamp": datetime.utcnow().isoformat()}


@router.post("/traceroute")
async def run_traceroute(body: TracerouteRequest):
    hops = await traceroute(body.ip, body.max_hops)
    return {"ip": body.ip, "hops": hops, "timestamp": datetime.utcnow().isoformat()}


# ── Advanced Network Management Tools ────────────────────────────────────────

@router.post("/wol")
async def trigger_wake_on_lan(body: WolRequest):
    """Broadcast Wake-on-LAN Magic Packet."""
    try:
        res = send_wake_on_lan(body.mac, body.broadcast_ip or "255.255.255.255", body.port or 9)
        return res
    except ValueError as ve:
        raise HTTPException(422, str(ve))
    except Exception as e:
        raise HTTPException(500, f"WoL error: {e}")


@router.get("/arp")
async def get_arp_table_endpoint():
    """Retrieve local ARP table and identify MAC address hardware manufacturers."""
    entries = await get_arp_table()
    return {"entries": entries, "count": len(entries), "timestamp": datetime.utcnow().isoformat()}


@router.post("/subnet-calc")
async def calculate_subnet_endpoint(body: SubnetCalcRequest):
    """Subnet breakdown and usable host calculations."""
    try:
        return calculate_subnet(body.cidr)
    except ValueError as ve:
        raise HTTPException(422, str(ve))


@router.post("/ssl-check")
async def check_ssl_endpoint(body: SslCheckRequest):
    """Check remote SSL certificate validity and expiration."""
    return await check_ssl_certificate(body.host, body.port or 443)


@router.post("/dns-lookup")
async def dns_lookup_endpoint(body: DnsLookupRequest):
    """Perform forward & reverse DNS lookup."""
    return await resolve_dns_records(body.domain)
@router.post("/printer-counter")
async def printer_counter_endpoint(body: PrinterCounterRequest):
    """Check Canon printer counters via Dept ID / PIN."""
    try:
        from services.printer_check import check_printer_counter
        return check_printer_counter(body.ip, body.dept_id, body.pin)
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "ip": body.ip,
            "dept_id": body.dept_id,
            "pin": body.pin,
        }



# ── History & Dashboard ───────────────────────────────────────────────────────

@router.get("/history/{device_id}")
async def device_history(device_id: int, limit: int = Query(default=50, le=500)):
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(PingHistory).where(PingHistory.device_id == device_id)
            .order_by(desc(PingHistory.timestamp)).limit(limit)
        )
        rows = result.scalars().all()
    return [{"id": r.id, "ip": r.ip, "status": r.status,
             "latency_ms": r.latency_ms, "timestamp": r.timestamp.isoformat()}
            for r in reversed(rows)]


@router.get("/status/all")
async def all_device_status():
    async with AsyncSessionLocal() as db:
        dev_result = await db.execute(select(Device).where(Device.enabled == True))
        devices = dev_result.scalars().all()
        statuses = []
        for d in devices:
            hist_result = await db.execute(
                select(PingHistory).where(PingHistory.device_id == d.id)
                .order_by(desc(PingHistory.timestamp)).limit(20)
            )
            history = hist_result.scalars().all()
            last = history[0] if history else None
            latencies = [h.latency_ms for h in reversed(history) if h.status == "UP"]
            statuses.append({
                "id": d.id, "name": d.name, "ip": d.ip,
                "hostname": d.hostname, "group_name": d.group_name, "device_type": d.device_type,
                "status": last.status if last else "UNKNOWN",
                "latency_ms": last.latency_ms if last else 0,
                "last_seen": last.timestamp.isoformat() if last else None,
                "latency_history": latencies,
            })
    return statuses

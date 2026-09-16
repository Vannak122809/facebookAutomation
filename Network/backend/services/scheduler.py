import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Set
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select, func
from database import AsyncSessionLocal, Device, PingHistory, AlertRecord
from services.network_scanner import ping_host

logger = logging.getLogger("scheduler")

scheduler = AsyncIOScheduler(timezone="UTC")

# Track consecutive DOWN counts per device IP
_down_counts: Dict[str, int] = {}
_alert_cooldown: Dict[str, datetime] = {}
ALERT_THRESHOLD = 2        # consecutive DOWNs before alert
ALERT_COOLDOWN_MIN = 10    # minutes between repeated alerts for same device


async def poll_devices():
    """Background job: ping all enabled devices and record results."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Device).where(Device.enabled == True))
        devices = result.scalars().all()

    if not devices:
        return

    async def _ping_and_record(device: Device):
        ping_result = await ping_host(device.ip, count=2, timeout=1.5)
        status = ping_result["status"]
        latency = ping_result["latency_ms"]

        async with AsyncSessionLocal() as db:
            db.add(PingHistory(
                device_id=device.id,
                ip=device.ip,
                status=status,
                latency_ms=latency,
                timestamp=datetime.utcnow(),
            ))
            await db.commit()

        # Alert logic
        ip = device.ip
        if status == "DOWN":
            _down_counts[ip] = _down_counts.get(ip, 0) + 1
        else:
            _down_counts[ip] = 0

        if _down_counts.get(ip, 0) >= ALERT_THRESHOLD:
            last_alert = _alert_cooldown.get(ip)
            now = datetime.utcnow()
            if last_alert is None or (now - last_alert) > timedelta(minutes=ALERT_COOLDOWN_MIN):
                _alert_cooldown[ip] = now
                async with AsyncSessionLocal() as db:
                    db.add(AlertRecord(
                        device_id=device.id,
                        device_name=device.name,
                        alert_type="HOST_DOWN",
                        message=f"Device '{device.name}' ({device.ip}) is DOWN ({_down_counts[ip]} consecutive failures)",
                    ))
                    await db.commit()
                logger.warning(f"ALERT: {device.name} ({ip}) DOWN")

    await asyncio.gather(*[_ping_and_record(d) for d in devices])


async def cleanup_old_history():
    """Remove ping history older than 7 days to keep DB lean."""
    cutoff = datetime.utcnow() - timedelta(days=7)
    async with AsyncSessionLocal() as db:
        from sqlalchemy import delete
        await db.execute(delete(PingHistory).where(PingHistory.timestamp < cutoff))
        await db.commit()
    logger.info("Old ping history cleaned up")


def start_scheduler():
    scheduler.add_job(poll_devices, "interval", seconds=30, id="poll_devices", replace_existing=True)
    scheduler.add_job(cleanup_old_history, "cron", hour=3, minute=0, id="cleanup", replace_existing=True)
    scheduler.start()
    logger.info("Background scheduler started — polling every 30s")


def stop_scheduler():
    scheduler.shutdown(wait=False)

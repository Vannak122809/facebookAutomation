from fastapi import APIRouter, Query
from sqlalchemy import select, desc, update
from database import AsyncSessionLocal, AlertRecord, AnydeskLog
from datetime import datetime

router = APIRouter(prefix="/api/logs", tags=["logs"])


@router.get("/alerts")
async def get_alerts(limit: int = Query(default=50, le=200), unread_only: bool = False):
    async with AsyncSessionLocal() as db:
        q = select(AlertRecord).order_by(desc(AlertRecord.created_at)).limit(limit)
        if unread_only:
            q = q.where(AlertRecord.acknowledged == False)
        result = await db.execute(q)
        rows = result.scalars().all()
    return [_alert_dict(r) for r in rows]


@router.post("/alerts/{alert_id}/ack")
async def acknowledge_alert(alert_id: int):
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(AlertRecord).where(AlertRecord.id == alert_id))
        alert = result.scalar_one_or_none()
        if alert:
            alert.acknowledged = True
            await db.commit()
    return {"ok": True}


@router.post("/alerts/ack-all")
async def acknowledge_all():
    async with AsyncSessionLocal() as db:
        await db.execute(
            update(AlertRecord).where(AlertRecord.acknowledged == False).values(acknowledged=True)
        )
        await db.commit()
    return {"ok": True}


@router.get("/alerts/count")
async def unread_count():
    from sqlalchemy import func
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(func.count()).select_from(AlertRecord).where(AlertRecord.acknowledged == False)
        )
        count = result.scalar()
    return {"unread": count}


def _alert_dict(r: AlertRecord) -> dict:
    return {
        "id": r.id,
        "device_id": r.device_id,
        "device_name": r.device_name,
        "alert_type": r.alert_type,
        "message": r.message,
        "acknowledged": r.acknowledged,
        "created_at": r.created_at.isoformat() if r.created_at else None,
    }

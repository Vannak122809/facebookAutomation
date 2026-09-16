import ipaddress
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, Field
from typing import Optional, List, Literal
from database import get_db, Device

router = APIRouter(prefix="/api/devices", tags=["devices"])


class DeviceCreate(BaseModel):
    name: str
    ip: str
    hostname: Optional[str] = ""
    group_name: Optional[str] = "General"
    device_type: Optional[str] = "Workstation"
    notes: Optional[str] = ""
    enabled: Optional[bool] = True


class DeviceUpdate(BaseModel):
    name: Optional[str] = None
    hostname: Optional[str] = None
    group_name: Optional[str] = None
    device_type: Optional[str] = None
    notes: Optional[str] = None
    enabled: Optional[bool] = None


class DeviceBatchItem(BaseModel):
    name: str
    ip: str
    hostname: Optional[str] = ""
    group_name: Optional[str] = "General"
    device_type: Optional[str] = "Workstation"
    notes: Optional[str] = ""
    enabled: Optional[bool] = True


class DeviceBatchImportRequest(BaseModel):
    devices: List[DeviceBatchItem]
    on_duplicate: Literal["update", "skip", "error"] = "update"


@router.get("")
async def list_devices(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Device).order_by(Device.group_name, Device.name))
    devices = result.scalars().all()
    return [_device_to_dict(d) for d in devices]


@router.post("", status_code=201)
async def create_device(body: DeviceCreate, db: AsyncSession = Depends(get_db)):
    _validate_ip(body.ip)
    existing = await db.execute(select(Device).where(Device.ip == body.ip.strip()))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail=f"Device with IP {body.ip} already exists")
    data = body.model_dump()
    data["ip"] = data["ip"].strip()
    data["name"] = data["name"].strip()
    device = Device(**data)
    db.add(device)
    await db.commit()
    await db.refresh(device)
    return _device_to_dict(device)


@router.post("/batch", status_code=200)
async def batch_import_devices(
    body: DeviceBatchImportRequest,
    db: AsyncSession = Depends(get_db)
):
    if not body.devices:
        raise HTTPException(status_code=400, detail="No devices provided in batch")

    # Fetch all existing devices by IP
    result = await db.execute(select(Device))
    existing_map = {d.ip.lower(): d for d in result.scalars().all()}

    seen_batch_ips = set()
    added_count = 0
    updated_count = 0
    skipped_count = 0
    errors = []
    processed_devices = []

    for idx, item in enumerate(body.devices, start=1):
        clean_ip = item.ip.strip()
        clean_name = item.name.strip()

        if not clean_ip:
            errors.append({"row": idx, "name": clean_name, "ip": clean_ip, "error": "IP address is required"})
            continue

        if not clean_name:
            clean_name = clean_ip

        try:
            ipaddress.ip_address(clean_ip)
        except ValueError:
            errors.append({"row": idx, "name": clean_name, "ip": clean_ip, "error": f"Invalid IP address '{clean_ip}'"})
            continue

        ip_key = clean_ip.lower()
        if ip_key in seen_batch_ips:
            if body.on_duplicate == "skip":
                skipped_count += 1
                continue
            elif body.on_duplicate == "error":
                errors.append({"row": idx, "name": clean_name, "ip": clean_ip, "error": f"Duplicate IP in batch: {clean_ip}"})
                continue

        seen_batch_ips.add(ip_key)
        existing_device = existing_map.get(ip_key)

        if existing_device:
            if body.on_duplicate == "skip":
                skipped_count += 1
                continue
            elif body.on_duplicate == "error":
                errors.append({"row": idx, "name": clean_name, "ip": clean_ip, "error": f"Device with IP {clean_ip} already exists in database"})
                continue
            else:  # update
                existing_device.name = clean_name
                if item.hostname:
                    existing_device.hostname = item.hostname.strip()
                if item.group_name:
                    existing_device.group_name = item.group_name.strip()
                if item.device_type:
                    existing_device.device_type = item.device_type.strip()
                if item.notes:
                    existing_device.notes = item.notes.strip()
                if item.enabled is not None:
                    existing_device.enabled = item.enabled
                updated_count += 1
                processed_devices.append(existing_device)
        else:
            new_device = Device(
                name=clean_name,
                ip=clean_ip,
                hostname=(item.hostname or "").strip(),
                group_name=(item.group_name or "General").strip(),
                device_type=(item.device_type or "Workstation").strip(),
                notes=(item.notes or "").strip(),
                enabled=True if item.enabled is None else item.enabled
            )
            db.add(new_device)
            existing_map[ip_key] = new_device
            added_count += 1
            processed_devices.append(new_device)

    await db.commit()
    for d in processed_devices:
        await db.refresh(d)

    return {
        "total": len(body.devices),
        "added": added_count,
        "updated": updated_count,
        "skipped": skipped_count,
        "errors": errors,
        "devices": [_device_to_dict(d) for d in processed_devices]
    }


@router.get("/{device_id}")
async def get_device(device_id: int, db: AsyncSession = Depends(get_db)):
    return _device_to_dict(await _get_or_404(device_id, db))


@router.patch("/{device_id}")
async def update_device(device_id: int, body: DeviceUpdate, db: AsyncSession = Depends(get_db)):
    device = await _get_or_404(device_id, db)
    for field, value in body.model_dump(exclude_none=True).items():
        if field == "ip":
            _validate_ip(value)
            value = value.strip()
        elif isinstance(value, str):
            value = value.strip()
        setattr(device, field, value)
    await db.commit()
    await db.refresh(device)
    return _device_to_dict(device)


@router.delete("/{device_id}", status_code=204)
async def delete_device(device_id: int, db: AsyncSession = Depends(get_db)):
    device = await _get_or_404(device_id, db)
    await db.delete(device)
    await db.commit()


def _validate_ip(ip_str: str):
    clean = (ip_str or "").strip()
    if not clean:
        raise HTTPException(status_code=422, detail="IP address cannot be empty")
    try:
        ipaddress.ip_address(clean)
    except ValueError:
        raise HTTPException(status_code=422, detail=f"'{clean}' is not a valid IPv4 or IPv6 address")


async def _get_or_404(device_id: int, db: AsyncSession) -> Device:
    result = await db.execute(select(Device).where(Device.id == device_id))
    device = result.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return device


def _device_to_dict(d: Device) -> dict:
    return {
        "id": d.id, "name": d.name, "ip": d.ip,
        "hostname": d.hostname, "group_name": d.group_name,
        "device_type": d.device_type, "notes": d.notes,
        "enabled": d.enabled,
        "created_at": d.created_at.isoformat() if d.created_at else None,
    }


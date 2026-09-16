import asyncio
import os
import platform
import subprocess
import shutil
from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy import select, desc

from services.anydesk_checker import run_full_diagnostic, tail_anydesk_log
from database import AsyncSessionLocal, SavedRemote, RemoteSession

router = APIRouter(prefix="/api/anydesk", tags=["anydesk"])

SYSTEM = platform.system().lower()


# ── Pydantic models ────────────────────────────────────────────────────────────

class ConnectRequest(BaseModel):
    anydesk_id: str
    password: Optional[str] = None
    label: Optional[str] = ""

class SavedRemoteCreate(BaseModel):
    name: str
    anydesk_id: str
    description: Optional[str] = ""
    group_name: Optional[str] = "General"

class SavedRemoteUpdate(BaseModel):
    name: Optional[str] = None
    anydesk_id: Optional[str] = None
    description: Optional[str] = None
    group_name: Optional[str] = None


# ── Diagnostics ────────────────────────────────────────────────────────────────

@router.get("/diagnose")
async def diagnose():
    """Run full AnyDesk diagnostic suite."""
    return await run_full_diagnostic()


@router.get("/log")
async def get_log(lines: int = 100):
    """Return last N lines of AnyDesk trace log."""
    entries = await tail_anydesk_log(lines)
    return {"lines": entries, "count": len(entries)}


# ── Quick Connect ──────────────────────────────────────────────────────────────

@router.post("/connect")
async def connect_remote(body: ConnectRequest):
    """
    Launch AnyDesk and connect to a remote ID.
    Works on Windows, macOS, Linux — finds AnyDesk binary automatically.
    """
    anydesk_bin = _find_anydesk()
    if not anydesk_bin:
        # Log failed attempt
        await _log_session(body.anydesk_id, body.label or body.anydesk_id,
                           "error", "AnyDesk binary not found on this machine")
        raise HTTPException(
            status_code=503,
            detail="AnyDesk executable not found. Please install AnyDesk or check PATH."
        )

    # Build command
    cmd = [anydesk_bin, body.anydesk_id]
    if body.password:
        cmd += ["--with-password"]

    status = "launched"
    error_msg = ""
    try:
        if body.password:
            # Pipe password via stdin
            proc = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
            )
            _, stderr = proc.communicate(input=body.password, timeout=5)
            if proc.returncode not in (0, None) and "already" not in (stderr or "").lower():
                error_msg = stderr.strip()
                status = "error"
        else:
            # Fire and forget — AnyDesk opens its own window
            subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
    except subprocess.TimeoutExpired:
        # That's fine — AnyDesk launched but didn't exit (it stays open)
        pass
    except Exception as e:
        status = "error"
        error_msg = str(e)

    await _log_session(body.anydesk_id, body.label or body.anydesk_id, status, error_msg)

    if status == "error":
        raise HTTPException(status_code=500, detail=f"AnyDesk launch error: {error_msg}")

    return {
        "ok": True,
        "anydesk_id": body.anydesk_id,
        "status": status,
        "anydesk_bin": anydesk_bin,
        "message": f"AnyDesk connecting to {body.anydesk_id}",
    }


# ── Session History ────────────────────────────────────────────────────────────

@router.get("/sessions")
async def get_sessions(limit: int = 50):
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(RemoteSession).order_by(desc(RemoteSession.started_at)).limit(limit)
        )
        rows = result.scalars().all()
    return [_session_dict(r) for r in rows]


@router.delete("/sessions", status_code=204)
async def clear_sessions():
    from sqlalchemy import delete as sa_delete
    async with AsyncSessionLocal() as db:
        await db.execute(sa_delete(RemoteSession))
        await db.commit()


# ── Saved Remotes CRUD ─────────────────────────────────────────────────────────

@router.get("/saved")
async def list_saved():
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(SavedRemote).order_by(SavedRemote.group_name, SavedRemote.name)
        )
        rows = result.scalars().all()
    return [_saved_dict(r) for r in rows]


@router.post("/saved", status_code=201)
async def create_saved(body: SavedRemoteCreate):
    async with AsyncSessionLocal() as db:
        remote = SavedRemote(**body.model_dump())
        db.add(remote)
        await db.commit()
        await db.refresh(remote)
    return _saved_dict(remote)


@router.patch("/saved/{rid}")
async def update_saved(rid: int, body: SavedRemoteUpdate):
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(SavedRemote).where(SavedRemote.id == rid))
        remote = result.scalar_one_or_none()
        if not remote:
            raise HTTPException(404, "Saved remote not found")
        for field, value in body.model_dump(exclude_none=True).items():
            setattr(remote, field, value)
        await db.commit()
        await db.refresh(remote)
    return _saved_dict(remote)


@router.delete("/saved/{rid}", status_code=204)
async def delete_saved(rid: int):
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(SavedRemote).where(SavedRemote.id == rid))
        remote = result.scalar_one_or_none()
        if not remote:
            raise HTTPException(404, "Saved remote not found")
        await db.delete(remote)
        await db.commit()


# ── AnyDesk path detection ────────────────────────────────────────────────────

def _find_anydesk() -> Optional[str]:
    """Find AnyDesk binary across all platforms."""
    # Check PATH first
    found = shutil.which("anydesk") or shutil.which("AnyDesk")
    if found:
        return found

    # Platform-specific well-known paths
    candidates = []
    if SYSTEM == "windows":
        candidates = [
            r"C:\Program Files (x86)\AnyDesk\AnyDesk.exe",
            r"C:\Program Files\AnyDesk\AnyDesk.exe",
            os.path.join(os.environ.get("LOCALAPPDATA", ""), "AnyDesk", "AnyDesk.exe"),
            os.path.join(os.environ.get("APPDATA", ""), "AnyDesk", "AnyDesk.exe"),
        ]
    elif SYSTEM == "darwin":
        candidates = [
            "/Applications/AnyDesk.app/Contents/MacOS/AnyDesk",
            os.path.expanduser("~/Applications/AnyDesk.app/Contents/MacOS/AnyDesk"),
        ]
    else:  # linux
        candidates = [
            "/usr/bin/anydesk",
            "/usr/local/bin/anydesk",
            "/opt/anydesk/anydesk",
            os.path.expanduser("~/.local/bin/anydesk"),
        ]

    for path in candidates:
        if path and os.path.isfile(path):
            return path
    return None


# ── Helpers ────────────────────────────────────────────────────────────────────

async def _log_session(anydesk_id: str, label: str, status: str, error_msg: str = ""):
    async with AsyncSessionLocal() as db:
        db.add(RemoteSession(
            anydesk_id=anydesk_id,
            label=label,
            status=status,
            error_msg=error_msg,
            started_at=datetime.utcnow(),
        ))
        await db.commit()


def _saved_dict(r: SavedRemote) -> dict:
    return {
        "id": r.id, "name": r.name, "anydesk_id": r.anydesk_id,
        "description": r.description, "group_name": r.group_name,
        "created_at": r.created_at.isoformat() if r.created_at else None,
    }


def _session_dict(r: RemoteSession) -> dict:
    return {
        "id": r.id, "anydesk_id": r.anydesk_id, "label": r.label,
        "status": r.status, "error_msg": r.error_msg,
        "started_at": r.started_at.isoformat() if r.started_at else None,
    }

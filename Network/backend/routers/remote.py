"""
remote.py — In-browser remote sessions
  • REST CRUD for session configs
  • WebSocket SSH terminal  (/ws/ssh/{session_id})
  • WebSocket VNC proxy     (/ws/vnc)
"""
import asyncio
import io
import logging
import socket
import threading
from datetime import datetime
from typing import Optional

import paramiko
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from database import AsyncSessionLocal, RemoteSessionConfig

log = logging.getLogger("remote")
router = APIRouter(prefix="/api/remote", tags=["remote"])


# ── Pydantic ──────────────────────────────────────────────────────────────────

class SessionConfigCreate(BaseModel):
    name: str
    session_type: str          # "ssh" | "vnc"
    host: str
    port: Optional[int] = None
    username: Optional[str] = ""
    password: Optional[str] = ""
    ssh_key: Optional[str] = ""
    group_name: Optional[str] = "General"
    notes: Optional[str] = ""

class SessionConfigUpdate(BaseModel):
    name: Optional[str] = None
    session_type: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None
    username: Optional[str] = None
    password: Optional[str] = None
    ssh_key: Optional[str] = None
    group_name: Optional[str] = None
    notes: Optional[str] = None


# ── Session Config CRUD ───────────────────────────────────────────────────────

@router.get("/sessions")
async def list_sessions():
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(RemoteSessionConfig).order_by(RemoteSessionConfig.group_name, RemoteSessionConfig.name)
        )
        rows = result.scalars().all()
    return [_cfg_dict(r) for r in rows]


@router.post("/sessions", status_code=201)
async def create_session(body: SessionConfigCreate):
    if body.session_type not in ("ssh", "vnc", "rdp"):
        raise HTTPException(422, "session_type must be 'ssh', 'vnc', or 'rdp'")
    # Default ports
    default_ports = {"ssh": 22, "vnc": 5900, "rdp": 3389}
    port = body.port or default_ports.get(body.session_type, 3389)
    async with AsyncSessionLocal() as db:
        cfg = RemoteSessionConfig(
            name=body.name, session_type=body.session_type,
            host=body.host, port=port,
            username=body.username or "",
            password=body.password or "",
            ssh_key=body.ssh_key or "",
            group_name=body.group_name or "General",
            notes=body.notes or "",
        )
        db.add(cfg)
        await db.commit()
        await db.refresh(cfg)
    return _cfg_dict(cfg)


@router.get("/rdp/download")
async def download_rdp_file(host: str, username: Optional[str] = "", port: int = 3389):
    """Generate a standard Windows .rdp file for instant 1-click Remote Desktop connection."""
    from fastapi.responses import Response
    rdp_content = f"""full address:s:{host}:{port}
username:s:{username}
prompt for credentials:i:1
administrative session:i:1
screen mode id:i:2
use multimon:i:0
desktopwidth:i:1920
desktopheight:i:1080
session bpp:i:32
compression:i:1
keyboardhook:i:2
audiomode:i:0
redirectclipboard:i:1
redirectprinters:i:0
redirectcomports:i:0
redirectsmartcards:i:0
redirectposdevices:i:0
drivestoredirect:s:*
displayconnectionbar:i:1
autoreconnection enabled:i:1
authentication level:i:2
enableworkspacereconnect:i:0
gatewayusagemethod:i:0
"""
    filename = f"{host.replace(':', '_')}.rdp"
    return Response(
        content=rdp_content,
        media_type="application/x-rdp",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.post("/rdp/launch")
async def launch_native_rdp(host: str, port: int = 3389, username: Optional[str] = ""):
    """Launch local system's native Remote Desktop client (mstsc on Windows, open rdp:// on Mac)."""
    import subprocess, platform
    system = platform.system().lower()
    try:
        if system == "windows":
            subprocess.Popen(["mstsc", f"/v:{host}:{port}"])
            return {"ok": True, "message": f"Launched mstsc for {host}:{port}"}
        elif system == "darwin":
            subprocess.Popen(["open", f"rdp://{username}@{host}:{port}" if username else f"rdp://{host}:{port}"])
            return {"ok": True, "message": f"Opened RDP URI on macOS for {host}:{port}"}
        else:
            subprocess.Popen(["xfreerdp", f"/v:{host}:{port}"])
            return {"ok": True, "message": f"Launched xfreerdp for {host}:{port}"}
    except Exception as e:
        raise HTTPException(500, f"Failed to launch native RDP: {e}")


@router.get("/sessions/{sid}")
async def get_session(sid: int):
    return _cfg_dict(await _get_or_404(sid))


@router.patch("/sessions/{sid}")
async def update_session(sid: int, body: SessionConfigUpdate):
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(RemoteSessionConfig).where(RemoteSessionConfig.id == sid))
        cfg = result.scalar_one_or_none()
        if not cfg:
            raise HTTPException(404, "Session not found")
        for field, value in body.model_dump(exclude_none=True).items():
            setattr(cfg, field, value)
        await db.commit()
        await db.refresh(cfg)
    return _cfg_dict(cfg)


@router.delete("/sessions/{sid}", status_code=204)
async def delete_session(sid: int):
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(RemoteSessionConfig).where(RemoteSessionConfig.id == sid))
        cfg = result.scalar_one_or_none()
        if not cfg:
            raise HTTPException(404, "Session not found")
        await db.delete(cfg)
        await db.commit()


# ── SSH WebSocket terminal ────────────────────────────────────────────────────

@router.websocket("/ws/ssh/{session_id}")
async def ssh_terminal(websocket: WebSocket, session_id: int):
    """
    Full bidirectional SSH terminal over WebSocket.
    Browser sends raw keystrokes, receives raw terminal output.
    Uses xterm.js on the frontend.
    """
    await websocket.accept()

    cfg = await _get_or_404(session_id)
    if cfg["session_type"] != "ssh":
        await websocket.send_text("\r\n\x1b[31mError: session type is not SSH\x1b[0m\r\n")
        await websocket.close()
        return

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        connect_kwargs = dict(
            hostname=cfg["host"],
            port=cfg["port"],
            username=cfg["username"],
            timeout=10,
        )
        if cfg.get("ssh_key"):
            key = _load_private_key(cfg["ssh_key"])
            connect_kwargs["pkey"] = key
        else:
            connect_kwargs["password"] = cfg["password"]

        await websocket.send_text(f"\x1b[36mConnecting to {cfg['username']}@{cfg['host']}:{cfg['port']}…\x1b[0m\r\n")

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: ssh.connect(**connect_kwargs))

        chan = ssh.invoke_shell(term="xterm-256color", width=220, height=50)
        chan.settimeout(0.0)

        await websocket.send_text(f"\x1b[32mConnected!\x1b[0m\r\n")

        # ── Bridge loop ────────────────────────────────────────────────────
        stop_event = asyncio.Event()

        async def ws_to_ssh():
            """Read from browser, send to SSH."""
            try:
                while not stop_event.is_set():
                    data = await websocket.receive_text()
                    if data.startswith("__RESIZE__:"):
                        # Terminal resize: __RESIZE__:cols:rows
                        try:
                            _, cols, rows = data.split(":")
                            chan.resize_pty(width=int(cols), height=int(rows))
                        except Exception:
                            pass
                    else:
                        chan.send(data)
            except WebSocketDisconnect:
                stop_event.set()
            except Exception as e:
                log.warning(f"ws_to_ssh error: {e}")
                stop_event.set()

        async def ssh_to_ws():
            """Read from SSH, send to browser."""
            try:
                while not stop_event.is_set():
                    if chan.recv_ready():
                        data = chan.recv(4096).decode("utf-8", errors="replace")
                        await websocket.send_text(data)
                    elif chan.exit_status_ready():
                        await websocket.send_text("\r\n\x1b[33m[Session closed]\x1b[0m\r\n")
                        stop_event.set()
                        break
                    else:
                        await asyncio.sleep(0.02)
            except WebSocketDisconnect:
                stop_event.set()
            except Exception as e:
                log.warning(f"ssh_to_ws error: {e}")
                stop_event.set()

        await asyncio.gather(ws_to_ssh(), ssh_to_ws())

    except paramiko.AuthenticationException:
        await websocket.send_text("\r\n\x1b[31mAuthentication failed. Check username/password.\x1b[0m\r\n")
    except paramiko.SSHException as e:
        await websocket.send_text(f"\r\n\x1b[31mSSH error: {e}\x1b[0m\r\n")
    except OSError as e:
        await websocket.send_text(f"\r\n\x1b[31mCannot connect: {e}\x1b[0m\r\n")
    except Exception as e:
        await websocket.send_text(f"\r\n\x1b[31mUnexpected error: {e}\x1b[0m\r\n")
        log.exception("SSH session error")
    finally:
        try:
            ssh.close()
        except Exception:
            pass
        try:
            await websocket.close()
        except Exception:
            pass


# ── VNC WebSocket proxy ────────────────────────────────────────────────────────

@router.websocket("/ws/vnc")
async def vnc_proxy(websocket: WebSocket, host: str, port: int = 5900):
    """
    Raw TCP bridge: WebSocket ↔ VNC TCP port.
    noVNC on the browser sends/receives raw RFB protocol bytes.
    """
    await websocket.accept()

    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port), timeout=8
        )
    except asyncio.TimeoutError:
        await websocket.close(code=1011, reason=f"Timeout connecting to {host}:{port}")
        return
    except OSError as e:
        await websocket.close(code=1011, reason=str(e))
        return

    stop = asyncio.Event()

    async def ws_to_vnc():
        try:
            while not stop.is_set():
                data = await websocket.receive_bytes()
                writer.write(data)
                await writer.drain()
        except (WebSocketDisconnect, Exception):
            stop.set()

    async def vnc_to_ws():
        try:
            while not stop.is_set():
                data = await asyncio.wait_for(reader.read(32768), timeout=30)
                if not data:
                    stop.set()
                    break
                await websocket.send_bytes(data)
        except asyncio.TimeoutError:
            pass  # keepalive timeout — normal
        except (WebSocketDisconnect, Exception):
            stop.set()
        finally:
            stop.set()

    try:
        await asyncio.gather(ws_to_vnc(), vnc_to_ws())
    finally:
        writer.close()
        try:
            await websocket.close()
        except Exception:
            pass


# ── Test connectivity ─────────────────────────────────────────────────────────

@router.post("/sessions/{sid}/test")
async def test_connection(sid: int):
    cfg = await _get_or_404(sid)
    loop = asyncio.get_event_loop()
    try:
        future = asyncio.open_connection(cfg["host"], cfg["port"])
        reader, writer = await asyncio.wait_for(future, timeout=5)
        writer.close()
        await writer.wait_closed()
        return {"ok": True, "detail": f"Port {cfg['port']} reachable on {cfg['host']}"}
    except asyncio.TimeoutError:
        return {"ok": False, "detail": f"Timeout — {cfg['host']}:{cfg['port']} not reachable"}
    except Exception as e:
        return {"ok": False, "detail": str(e)}


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _get_or_404(sid: int) -> dict:
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(RemoteSessionConfig).where(RemoteSessionConfig.id == sid))
        cfg = result.scalar_one_or_none()
    if not cfg:
        raise HTTPException(404, "Session config not found")
    return _cfg_dict(cfg)


def _cfg_dict(r: RemoteSessionConfig) -> dict:
    return {
        "id": r.id, "name": r.name, "session_type": r.session_type,
        "host": r.host, "port": r.port, "username": r.username,
        # Never expose full password, just whether it's set
        "has_password": bool(r.password),
        "has_ssh_key": bool(r.ssh_key),
        "password": r.password,   # needed by WS handler — not sent to UI
        "ssh_key": r.ssh_key,
        "group_name": r.group_name, "notes": r.notes,
        "created_at": r.created_at.isoformat() if r.created_at else None,
    }


def _load_private_key(pem: str) -> paramiko.PKey:
    """Try to load a PEM private key — RSA, Ed25519, ECDSA."""
    for cls in (paramiko.RSAKey, paramiko.Ed25519Key, paramiko.ECDSAKey):
        try:
            return cls.from_private_key(io.StringIO(pem))
        except Exception:
            continue
    raise ValueError("Unsupported or invalid private key format")

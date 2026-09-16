import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, Response
from pydantic import BaseModel

log = logging.getLogger("local_remote")
router = APIRouter(prefix="/api/local-remote", tags=["local_remote"])

# ─── Live Connected Agents In-Memory Hub ───────────────────────────────────────

class AgentConnection:
    def __init__(self, agent_id: str, ws: WebSocket, info: Dict[str, Any]):
        self.agent_id = agent_id
        self.ws = ws
        self.info = info
        self.connected_at = datetime.utcnow()
        self.last_frame_time = time_now = datetime.utcnow()
        self.viewers: List[WebSocket] = []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "name": self.info.get("name", self.agent_id),
            "hostname": self.info.get("hostname", "Unknown"),
            "os": self.info.get("os", "Unknown"),
            "input_supported": self.info.get("input_supported", False),
            "connected_at": self.connected_at.isoformat(),
            "viewer_count": len(self.viewers),
        }


active_agents: Dict[str, AgentConnection] = {}


# ─── Agent WebSocket Endpoint (Target PC connects here) ─────────────────────────

@router.websocket("/ws/agent/{agent_id}")
async def agent_websocket_hub(websocket: WebSocket, agent_id: str):
    await websocket.accept()
    log.info(f"Agent connecting: {agent_id}")
    
    agent_conn = None
    try:
        # 1. Wait for initial registration message
        first_msg = await asyncio.wait_for(websocket.receive_text(), timeout=10)
        reg_data = json.loads(first_msg)
        
        agent_conn = AgentConnection(agent_id, websocket, reg_data)
        active_agents[agent_id] = agent_conn
        log.info(f"Agent registered: {agent_id} ({reg_data.get('name')})")

        # 2. Main forward loop: Agent sends binary frames, server broadcasts to viewers
        while True:
            # We receive bytes (Frame packet)
            frame_packet = await websocket.receive_bytes()
            agent_conn.last_frame_time = datetime.utcnow()

            # Broadcast frame to all active web viewers
            dead_viewers = []
            for viewer_ws in agent_conn.viewers:
                try:
                    await viewer_ws.send_bytes(frame_packet)
                except Exception:
                    dead_viewers.append(viewer_ws)

            for d in dead_viewers:
                if d in agent_conn.viewers:
                    agent_conn.viewers.remove(d)

    except (WebSocketDisconnect, asyncio.TimeoutError):
        pass
    except Exception as e:
        log.warning(f"Agent {agent_id} disconnected with error: {e}")
    finally:
        if agent_id in active_agents:
            # Notify viewers that agent went offline
            for viewer_ws in active_agents[agent_id].viewers:
                try:
                    await viewer_ws.send_text(json.dumps({"type": "agent_offline"}))
                except Exception:
                    pass
            del active_agents[agent_id]
        log.info(f"Agent offline: {agent_id}")


# ─── Viewer WebSocket Endpoint (Browser connects here) ─────────────────────────

@router.websocket("/ws/viewer/{agent_id}")
async def viewer_websocket_hub(websocket: WebSocket, agent_id: str):
    await websocket.accept()
    
    if agent_id not in active_agents:
        await websocket.send_text(json.dumps({"type": "error", "message": f"Agent '{agent_id}' is not online"}))
        await websocket.close()
        return

    agent_conn = active_agents[agent_id]
    agent_conn.viewers.append(websocket)
    log.info(f"Web Viewer connected to Agent {agent_id}. Total viewers: {len(agent_conn.viewers)}")

    try:
        # Send initial status
        await websocket.send_text(json.dumps({
            "type": "connected",
            "agent": agent_conn.to_dict(),
        }))

        # Viewer sends mouse/keyboard input -> forward to agent
        while True:
            input_msg = await websocket.receive_text()
            # Forward JSON input commands directly to the agent's WebSocket
            if agent_conn.ws.client_state.name == "CONNECTED":
                await agent_conn.ws.send_text(input_msg)

    except WebSocketDisconnect:
        pass
    finally:
        if websocket in agent_conn.viewers:
            agent_conn.viewers.remove(websocket)
        log.info(f"Web Viewer disconnected from Agent {agent_id}")


# ─── REST Endpoints ───────────────────────────────────────────────────────────

@router.get("/agents")
async def list_connected_agents():
    """List all currently active local agents streaming to this server."""
    return [conn.to_dict() for conn in active_agents.values()]


@router.get("/agent.py")
async def download_agent_script():
    """Serve the ready-to-run Python agent script for target computers."""
    from pathlib import Path
    template_path = Path(__file__).parent.parent / "agent_template.py"
    if not template_path.exists():
        raise HTTPException(404, "Agent template file missing")
    with open(template_path, "r", encoding="utf-8") as f:
        content = f.read()
    return Response(content=content, media_type="text/x-python")


# ─── Self-Hosted RustDesk Configuration Helper ────────────────────────────────

class RustDeskConfig(BaseModel):
    server_ip: str
    key: Optional[str] = ""

@router.get("/rustdesk/compose")
async def get_rustdesk_docker_compose(server_ip: str = "192.168.1.100"):
    """Generate ready-to-use Docker Compose for self-hosting RustDesk hbbs/hbbr on LAN."""
    compose_yaml = f"""version: '3'

networks:
  rustdesk-net:
    external: false

services:
  hbbs:
    container_name: hbbs
    image: rustdesk/rustdesk-server:latest
    command: hbbs -r {server_ip}:21117 -k _
    volumes:
      - ./data:/root
    networks:
      - rustdesk-net
    restart: unless-stopped
    ports:
      - "21115:21115"
      - "21116:21116"
      - "21116:21116/udp"
      - "21118:21118"

  hbbr:
    container_name: hbbr
    image: rustdesk/rustdesk-server:latest
    command: hbbr -k _
    volumes:
      - ./data:/root
    networks:
      - rustdesk-net
    restart: unless-stopped
    ports:
      - "21117:21117"
      - "21119:21119"
"""
    return {
        "server_ip": server_ip,
        "docker_compose_yaml": compose_yaml,
        "ports": [
            {"port": "21115/tcp", "usage": "hbbs NAT type test"},
            {"port": "21116/tcp & udp", "usage": "hbbs ID registration & heartbeat"},
            {"port": "21117/tcp", "usage": "hbbr Relay server connection"},
            {"port": "21118/tcp", "usage": "hbbs Web client support"},
            {"port": "21119/tcp", "usage": "hbbr Web client support"},
        ],
        "setup_instructions": [
            "1. Save this content as docker-compose.yml on your local server.",
            "2. Run: docker compose up -d",
            "3. Retrieve your public key with: cat ./data/id_ed25519.pub",
            f"4. On client PCs in RustDesk -> Settings -> Network:",
            f"   • ID Server: {server_ip}",
            f"   • Relay Server: {server_ip}:21117",
            f"   • Key: (paste content from id_ed25519.pub)",
        ]
    }

#!/usr/bin/env python3
"""
NetManager Remote Agent — Ultra-lightweight local screen streaming & control agent.
Runs on Windows, macOS, and Linux with Python 3.

Usage:
    python3 agent.py --server ws://<SERVER_IP>:8000 --name "Office-PC"
"""

import argparse
import asyncio
import io
import json
import os
import platform
import socket
import sys
import time

try:
    import websockets
except ImportError:
    print("[!] Installing required 'websockets' package...")
    os.system(f"{sys.executable} -m pip install websockets")
    import websockets

try:
    from PIL import Image, ImageGrab
except ImportError:
    print("[!] Installing required 'Pillow' package for screen capture...")
    os.system(f"{sys.executable} -m pip install pillow")
    from PIL import Image, ImageGrab

# Optional input simulation
PYAUTOGUI_AVAILABLE = False
try:
    import pyautogui
    pyautogui.FAILSAFE = False
    pyautogui.PAUSE = 0.01
    PYAUTOGUI_AVAILABLE = True
except Exception:
    pass


def capture_screen_jpeg(quality=55, max_width=1280):
    """Capture desktop screen and return compressed JPEG bytes."""
    try:
        img = ImageGrab.grab()
        # Downscale if larger than max_width to keep bandwidth low on LAN
        if img.width > max_width:
            ratio = max_width / float(img.width)
            new_height = int(img.height * ratio)
            img = img.resize((max_width, new_height), Image.Resampling.BILINEAR)

        # Convert to RGB (in case of RGBA on macOS)
        if img.mode != "RGB":
            img = img.convert("RGB")

        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=quality, optimize=True)
        return buf.getvalue(), img.width, img.height
    except Exception as e:
        # Fallback empty black image
        img = Image.new("RGB", (640, 480), color=(20, 20, 20))
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=30)
        return buf.getvalue(), 640, 480


async def agent_loop(server_ws_url, agent_id, agent_name):
    full_url = f"{server_ws_url.rstrip('/')}/api/local-remote/ws/agent/{agent_id}"
    print(f"[*] Connecting to NetManager Hub at: {full_url}")
    
    hostname = socket.gethostname()
    os_info = f"{platform.system()} {platform.release()} ({platform.machine()})"

    while True:
        try:
            async with websockets.connect(full_url, max_size=10 * 1024 * 1024) as ws:
                print(f"[+] Connected to Hub! Registering as '{agent_name}' ({hostname})...")
                
                # Send registration info
                init_payload = {
                    "type": "register",
                    "id": agent_id,
                    "name": agent_name,
                    "hostname": hostname,
                    "os": os_info,
                    "input_supported": PYAUTOGUI_AVAILABLE,
                }
                await ws.send(json.dumps(init_payload))

                # Background frame sender
                stop_event = asyncio.Event()

                async def send_screen_stream():
                    frame_interval = 0.08  # ~12-15 FPS (smooth on LAN)
                    while not stop_event.is_set():
                        t0 = time.time()
                        jpeg_bytes, w, h = capture_screen_jpeg(quality=60)
                        
                        header = json.dumps({"type": "frame", "w": w, "h": h}).encode("utf-8")
                        # Frame packet: 4 bytes header length + header json + JPEG data
                        packet = len(header).to_bytes(4, "big") + header + jpeg_bytes
                        await ws.send(packet)

                        elapsed = time.time() - t0
                        sleep_time = max(0.01, frame_interval - elapsed)
                        await asyncio.sleep(sleep_time)

                async def receive_remote_inputs():
                    try:
                        async for message in ws:
                            if isinstance(message, str):
                                msg = json.loads(message)
                                mtype = msg.get("type")

                                if mtype == "mouse_move" and PYAUTOGUI_AVAILABLE:
                                    # Scale normalized 0.0-1.0 coords to screen
                                    sw, sh = pyautogui.size()
                                    target_x = int(msg["x"] * sw)
                                    target_y = int(msg["y"] * sh)
                                    pyautogui.moveTo(target_x, target_y)

                                elif mtype == "mouse_click" and PYAUTOGUI_AVAILABLE:
                                    button = msg.get("button", "left")
                                    pyautogui.click(button=button)

                                elif mtype == "mouse_down" and PYAUTOGUI_AVAILABLE:
                                    button = msg.get("button", "left")
                                    pyautogui.mouseDown(button=button)

                                elif mtype == "mouse_up" and PYAUTOGUI_AVAILABLE:
                                    button = msg.get("button", "left")
                                    pyautogui.mouseUp(button=button)

                                elif mtype == "key" and PYAUTOGUI_AVAILABLE:
                                    key = msg.get("key")
                                    if key:
                                        pyautogui.press(key)

                                elif mtype == "write" and PYAUTOGUI_AVAILABLE:
                                    text = msg.get("text", "")
                                    pyautogui.write(text)

                                elif mtype == "hotkey" and PYAUTOGUI_AVAILABLE:
                                    keys = msg.get("keys", [])
                                    if keys:
                                        pyautogui.hotkey(*keys)

                    except Exception as e:
                        print(f"[-] Input receiver error: {e}")
                    finally:
                        stop_event.set()

                # Run both concurrently
                await asyncio.gather(send_screen_stream(), receive_remote_inputs())

        except (websockets.exceptions.ConnectionClosed, ConnectionRefusedError, OSError) as e:
            print(f"[!] Disconnected from server ({e}). Reconnecting in 3 seconds...")
            await asyncio.sleep(3)
        except Exception as e:
            print(f"[!] Agent error: {e}. Retrying in 5 seconds...")
            await asyncio.sleep(5)


def main():
    parser = argparse.ArgumentParser(description="NetManager Remote Desktop Agent")
    parser.add_argument("--server", default="ws://localhost:8000", help="NetManager server URL (e.g., ws://192.168.1.100:8000)")
    parser.add_argument("--name", default=socket.gethostname(), help="Friendly display name for this computer")
    parser.add_argument("--id", default=None, help="Specific Agent ID (defaults to hostname-hash)")
    args = parser.parse_args()

    agent_id = args.id or f"agent-{socket.gethostname().lower()}"
    server_ws = args.server.replace("http://", "ws://").replace("https://", "wss://")

    print("=" * 60)
    print("  NetManager Local Remote Desktop Agent")
    print(f"  Target Name : {args.name}")
    print(f"  Agent ID    : {agent_id}")
    print(f"  Control API : {'PyAutoGUI (Interactive)' if PYAUTOGUI_AVAILABLE else 'View-Only (install pyautogui for mouse/keys)'}")
    print("=" * 60)

    try:
        asyncio.run(agent_loop(server_ws, agent_id, args.name))
    except KeyboardInterrupt:
        print("\n[*] Agent stopped by user.")


if __name__ == "__main__":
    main()

import asyncio
import ipaddress
import platform
import re
import socket
import ssl
import subprocess
from datetime import datetime
from typing import Any, Dict, List, Optional


# ─── 1. Wake-on-LAN (WoL) ──────────────────────────────────────────────────────

def send_wake_on_lan(mac_address: str, broadcast_ip: str = "255.255.255.255", port: int = 9) -> Dict[str, Any]:
    """
    Send a Wake-on-LAN Magic Packet to wake up a remote PC.
    Packet format: 6 bytes of 0xFF followed by 16 repetitions of target MAC.
    """
    # Clean MAC address
    clean_mac = re.sub(r"[^0-9A-Fa-f]", "", mac_address)
    if len(clean_mac) != 12:
        raise ValueError(f"Invalid MAC address format: {mac_address}. Expected 12 hex digits (e.g., 00:11:22:33:44:55).")

    mac_bytes = bytes.fromhex(clean_mac)
    magic_packet = b"\xff" * 6 + mac_bytes * 16

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.sendto(magic_packet, (broadcast_ip, port))
            # Also send to alternate port 7
            sock.sendto(magic_packet, (broadcast_ip, 7))
        return {
            "success": True,
            "mac": mac_address,
            "broadcast_ip": broadcast_ip,
            "ports": [port, 7],
            "message": f"Magic Packet successfully broadcasted for MAC {mac_address}",
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        return {
            "success": False,
            "mac": mac_address,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        }


# ─── 2. ARP Table & MAC Vendor Lookup ──────────────────────────────────────────

# Comprehensive OUI database for common network hardware manufacturers
OUI_DATABASE = {
    # Apple
    "00:03:93": "Apple, Inc.", "00:05:02": "Apple, Inc.", "00:0a:27": "Apple, Inc.", "00:0a:95": "Apple, Inc.",
    "00:0d:93": "Apple, Inc.", "00:10:fa": "Apple, Inc.", "00:11:24": "Apple, Inc.", "00:14:51": "Apple, Inc.",
    "00:16:cb": "Apple, Inc.", "00:17:f2": "Apple, Inc.", "00:19:e3": "Apple, Inc.", "00:1b:63": "Apple, Inc.",
    "00:1d:4f": "Apple, Inc.", "00:1e:52": "Apple, Inc.", "00:1e:c2": "Apple, Inc.", "00:1f:5b": "Apple, Inc.",
    "00:1f:f3": "Apple, Inc.", "00:21:e9": "Apple, Inc.", "00:22:41": "Apple, Inc.", "00:23:12": "Apple, Inc.",
    "00:23:32": "Apple, Inc.", "00:23:6c": "Apple, Inc.", "00:23:df": "Apple, Inc.", "00:24:36": "Apple, Inc.",
    "00:25:00": "Apple, Inc.", "00:25:4b": "Apple, Inc.", "00:25:bc": "Apple, Inc.", "00:26:08": "Apple, Inc.",
    "00:26:4a": "Apple, Inc.", "00:26:b0": "Apple, Inc.", "00:26:bb": "Apple, Inc.", "10:93:e9": "Apple, Inc.",
    "10:9a:dd": "Apple, Inc.", "10:b5:88": "Apple, Inc.", "14:10:9f": "Apple, Inc.", "14:20:5e": "Apple, Inc.",
    "14:7d:da": "Apple, Inc.", "14:7f:ce": "Apple, Inc.", "18:65:90": "Apple, Inc.", "18:af:61": "Apple, Inc.",
    "18:e7:28": "Apple, Inc.", "1c:1a:c0": "Apple, Inc.", "20:7d:74": "Apple, Inc.", "24:ab:81": "Apple, Inc.",
    "28:0b:5c": "Apple, Inc.", "28:6a:ba": "Apple, Inc.", "28:cf:e9": "Apple, Inc.", "2c:be:08": "Apple, Inc.",
    "30:10:e4": "Apple, Inc.", "30:90:ab": "Apple, Inc.", "34:15:9e": "Apple, Inc.", "34:36:3b": "Apple, Inc.",
    "38:ca:84": "Apple, Inc.", "3c:07:54": "Apple, Inc.", "3c:15:c2": "Apple, Inc.", "3c:ab:8e": "Apple, Inc.",
    "3c:e0:72": "Apple, Inc.", "40:30:04": "Apple, Inc.", "40:33:1a": "Apple, Inc.", "40:6c:8f": "Apple, Inc.",
    "40:98:ad": "Apple, Inc.", "44:00:10": "Apple, Inc.", "44:fb:42": "Apple, Inc.", "48:60:bc": "Apple, Inc.",
    "48:a9:1c": "Apple, Inc.", "48:d7:05": "Apple, Inc.", "48:e1:5c": "Apple, Inc.", "4c:32:75": "Apple, Inc.",
    "50:84:92": "Apple, Inc.", "50:a6:d8": "Apple, Inc.", "50:bc:96": "Apple, Inc.", "50:ea:d6": "Apple, Inc.",
    "54:26:96": "Apple, Inc.", "54:4e:90": "Apple, Inc.", "58:55:ca": "Apple, Inc.", "5c:96:9d": "Apple, Inc.",
    "60:03:08": "Apple, Inc.", "60:33:4b": "Apple, Inc.", "60:69:44": "Apple, Inc.", "60:c5:47": "Apple, Inc.",
    "60:f4:45": "Apple, Inc.", "64:a3:cb": "Apple, Inc.", "64:b0:a6": "Apple, Inc.", "64:d2:c4": "Apple, Inc.",
    "68:5b:35": "Apple, Inc.", "68:64:4b": "Apple, Inc.", "68:a8:6d": "Apple, Inc.", "68:d9:3c": "Apple, Inc.",
    "6c:40:08": "Apple, Inc.", "6c:4a:85": "Apple, Inc.", "6c:70:9f": "Apple, Inc.", "6c:96:cf": "Apple, Inc.",
    "70:11:24": "Apple, Inc.", "70:3e:ac": "Apple, Inc.", "70:a2:b3": "Apple, Inc.", "70:de:e2": "Apple, Inc.",
    "74:0e:a4": "Apple, Inc.", "74:8d:08": "Apple, Inc.", "78:31:c1": "Apple, Inc.", "78:4f:43": "Apple, Inc.",
    "78:67:d7": "Apple, Inc.", "78:7b:8a": "Apple, Inc.", "78:ca:39": "Apple, Inc.", "7c:50:49": "Apple, Inc.",
    "7c:6d:62": "Apple, Inc.", "7c:d1:c3": "Apple, Inc.", "80:49:71": "Apple, Inc.", "80:65:7c": "Apple, Inc.",
    "80:92:9f": "Apple, Inc.", "80:e6:50": "Apple, Inc.", "84:38:35": "Apple, Inc.", "84:78:8b": "Apple, Inc.",
    "88:64:40": "Apple, Inc.", "88:66:a5": "Apple, Inc.", "88:87:17": "Apple, Inc.", "88:c6:63": "Apple, Inc.",
    "8c:29:37": "Apple, Inc.", "8c:7b:9d": "Apple, Inc.", "8c:85:90": "Apple, Inc.", "90:72:40": "Apple, Inc.",
    "90:8d:6c": "Apple, Inc.", "90:9c:4a": "Apple, Inc.", "94:16:25": "Apple, Inc.", "94:e9:79": "Apple, Inc.",
    "98:01:a7": "Apple, Inc.", "98:5a:eb": "Apple, Inc.", "98:b8:e3": "Apple, Inc.", "98:d6:bb": "Apple, Inc.",
    "9c:20:7b": "Apple, Inc.", "9c:3e:53": "Apple, Inc.", "a4:83:e7": "Apple, Inc.", "a4:b1:97": "Apple, Inc.",
    "a4:c3:61": "Apple, Inc.", "a4:d1:d2": "Apple, Inc.", "a8:20:66": "Apple, Inc.", "a8:51:ab": "Apple, Inc.",
    "a8:5b:78": "Apple, Inc.", "a8:66:7f": "Apple, Inc.", "a8:8e:24": "Apple, Inc.", "ac:1f:74": "Apple, Inc.",
    "ac:29:3a": "Apple, Inc.", "ac:87:a3": "Apple, Inc.", "ac:de:48": "Apple, Inc.", "b0:34:95": "Apple, Inc.",
    "b0:65:bd": "Apple, Inc.", "b4:18:d1": "Apple, Inc.", "b4:f0:ab": "Apple, Inc.", "b8:17:c2": "Apple, Inc.",
    "b8:78:2e": "Apple, Inc.", "b8:8d:12": "Apple, Inc.", "bc:52:b7": "Apple, Inc.", "bc:60:a7": "Apple, Inc.",
    "c0:84:7a": "Apple, Inc.", "c0:9f:42": "Apple, Inc.", "c4:b3:01": "Apple, Inc.", "c8:6f:1d": "Apple, Inc.",
    "c8:b5:b7": "Apple, Inc.", "cc:08:8d": "Apple, Inc.", "cc:20:e8": "Apple, Inc.", "cc:29:f5": "Apple, Inc.",
    "d0:03:4b": "Apple, Inc.", "d0:23:db": "Apple, Inc.", "d0:81:7a": "Apple, Inc.", "d4:61:9d": "Apple, Inc.",
    "d4:90:9c": "Apple, Inc.", "d8:30:62": "Apple, Inc.", "d8:96:95": "Apple, Inc.", "d8:a2:5e": "Apple, Inc.",
    "dc:2b:2a": "Apple, Inc.", "dc:37:14": "Apple, Inc.", "dc:41:5f": "Apple, Inc.", "dc:a9:04": "Apple, Inc.",
    "e0:66:78": "Apple, Inc.", "e0:b9:ba": "Apple, Inc.", "e4:8b:7f": "Apple, Inc.", "e4:ce:8f": "Apple, Inc.",
    "e8:04:0b": "Apple, Inc.", "e8:06:88": "Apple, Inc.", "e8:80:2e": "Apple, Inc.", "ec:35:86": "Apple, Inc.",
    "ec:a9:07": "Apple, Inc.", "f0:18:98": "Apple, Inc.", "f0:76:6f": "Apple, Inc.", "f0:db:f8": "Apple, Inc.",
    "f4:0f:24": "Apple, Inc.", "f4:1b:a1": "Apple, Inc.", "f4:31:c3": "Apple, Inc.", "f4:37:b7": "Apple, Inc.",
    "f4:5c:89": "Apple, Inc.", "f4:a9:97": "Apple, Inc.", "f4:f1:5a": "Apple, Inc.", "f8:ff:c2": "Apple, Inc.",

    # Canon & Printing
    "00:00:85": "Canon Inc.", "00:1e:8f": "Canon Inc.", "00:21:e1": "Canon Inc.", "00:23:ee": "Canon Inc.",
    "00:24:1e": "Canon Inc.", "18:0c:ac": "Canon Inc.", "70:86:8b": "Canon Inc.", "84:ba:3b": "Canon Inc.",
    "a0:f6:fd": "Canon Inc.", "d0:17:6a": "Canon Inc.", "f4:81:39": "Canon Inc.", "fc:15:b4": "Canon Inc.",
    "00:04:76": "Kyocera Corporation", "00:17:c8": "Kyocera Document Solutions", "00:25:36": "Ricoh Co., Ltd.",
    "00:26:73": "Ricoh Co., Ltd.", "00:00:74": "Ricoh Co., Ltd.", "00:80:77": "Brother Industries",
    "00:1b:a9": "Brother Industries", "00:22:58": "Brother Industries", "30:05:5c": "Brother Industries",
    "00:00:48": "Seiko Epson Corp.", "00:26:ab": "Seiko Epson Corp.", "00:00:aa": "Xerox Corporation",

    # Hewlett-Packard (HP)
    "00:01:e6": "HP Inc.", "00:08:02": "HP Inc.", "00:08:83": "HP Inc.", "00:0e:7f": "HP Inc.",
    "00:0f:20": "HP Inc.", "00:10:83": "HP Inc.", "00:11:85": "HP Inc.", "00:12:79": "HP Inc.",
    "00:13:21": "HP Inc.", "00:14:38": "HP Inc.", "00:14:c2": "HP Inc.", "00:15:60": "HP Inc.",
    "00:16:35": "HP Inc.", "00:17:a4": "HP Inc.", "00:18:71": "HP Inc.", "00:19:bb": "HP Inc.",
    "00:1a:4b": "HP Inc.", "00:1b:78": "HP Inc.", "00:1c:c4": "HP Inc.", "00:1e:0b": "HP Inc.",
    "00:1f:29": "HP Inc.", "00:21:5a": "HP Inc.", "00:22:64": "HP Inc.", "00:23:7d": "HP Inc.",
    "00:24:81": "HP Inc.", "00:25:b3": "HP Inc.", "00:26:55": "HP Inc.", "00:30:c1": "HP Inc.",
    "00:60:b0": "HP Inc.", "10:62:e5": "HP Inc.", "14:02:ec": "HP Inc.", "14:58:d0": "HP Inc.",
    "18:a9:58": "HP Inc.", "1c:c1:de": "HP Inc.", "28:80:23": "HP Inc.", "2c:41:38": "HP Inc.",
    "30:8d:99": "HP Inc.", "34:64:a9": "HP Inc.", "3c:4a:92": "HP Inc.", "3c:52:82": "HP Inc.",
    "3c:d9:2b": "HP Inc.", "40:a8:f0": "HP Inc.", "48:0f:cf": "HP Inc.", "50:65:f3": "HP Inc.",
    "58:20:b1": "HP Inc.", "64:51:06": "HP Inc.", "70:5a:0f": "HP Inc.", "74:46:a0": "HP Inc.",
    "78:e3:b5": "HP Inc.", "80:c1:6e": "HP Inc.", "84:34:97": "HP Inc.", "94:57:a5": "HP Inc.",
    "9c:7b:ef": "HP Inc.", "a0:d3:c1": "HP Inc.", "a4:5d:36": "HP Inc.", "b0:5a:da": "HP Inc.",
    "b4:99:ba": "HP Inc.", "c4:34:6b": "HP Inc.", "cc:3d:82": "HP Inc.", "d4:85:64": "HP Inc.",
    "d8:9d:67": "HP Inc.", "dc:4a:3e": "HP Inc.", "e4:11:5b": "HP Inc.", "ec:8e:b5": "HP Inc.",
    "f4:03:43": "HP Inc.", "f8:bc:12": "HP Inc.",

    # Dell
    "00:06:5b": "Dell Inc.", "00:08:74": "Dell Inc.", "00:0b:db": "Dell Inc.", "00:0d:56": "Dell Inc.",
    "00:0f:1f": "Dell Inc.", "00:11:43": "Dell Inc.", "00:12:3f": "Dell Inc.", "00:13:72": "Dell Inc.",
    "00:14:22": "Dell Inc.", "00:15:c5": "Dell Inc.", "00:16:f0": "Dell Inc.", "00:18:8b": "Dell Inc.",
    "00:19:b9": "Dell Inc.", "00:1a:a0": "Dell Inc.", "00:1c:23": "Dell Inc.", "00:1d:09": "Dell Inc.",
    "00:1e:4f": "Dell Inc.", "00:1e:c9": "Dell Inc.", "00:21:70": "Dell Inc.", "00:21:9b": "Dell Inc.",
    "00:22:19": "Dell Inc.", "00:23:ae": "Dell Inc.", "00:24:e8": "Dell Inc.", "00:25:64": "Dell Inc.",
    "00:26:b9": "Dell Inc.", "14:18:77": "Dell Inc.", "14:fe:b5": "Dell Inc.", "18:03:73": "Dell Inc.",
    "18:66:da": "Dell Inc.", "24:6e:96": "Dell Inc.", "24:b6:fd": "Dell Inc.", "2c:ea:7f": "Dell Inc.",
    "34:17:eb": "Dell Inc.", "34:e6:d7": "Dell Inc.", "44:a8:42": "Dell Inc.", "4c:d9:8f": "Dell Inc.",
    "50:9a:4c": "Dell Inc.", "54:bf:64": "Dell Inc.", "5c:26:0a": "Dell Inc.", "64:00:6a": "Dell Inc.",
    "74:86:7a": "Dell Inc.", "78:2b:cb": "Dell Inc.", "84:2b:2b": "Dell Inc.", "90:b1:1c": "Dell Inc.",
    "98:90:96": "Dell Inc.", "a4:ba:db": "Dell Inc.", "b0:83:fe": "Dell Inc.", "b8:2a:72": "Dell Inc.",
    "b8:ac:6f": "Dell Inc.", "bc:30:5b": "Dell Inc.", "c8:1f:66": "Dell Inc.", "d0:67:e5": "Dell Inc.",
    "d4:81:d7": "Dell Inc.", "d4:be:d9": "Dell Inc.", "d8:9e:f3": "Dell Inc.", "e0:db:55": "Dell Inc.",
    "ec:f4:bb": "Dell Inc.", "f0:1f:af": "Dell Inc.", "f0:4d:a2": "Dell Inc.", "f8:db:88": "Dell Inc.",

    # Intel
    "00:02:b3": "Intel Corporate", "00:03:47": "Intel Corporate", "00:04:23": "Intel Corporate",
    "00:07:e9": "Intel Corporate", "00:0c:f1": "Intel Corporate", "00:0e:0c": "Intel Corporate",
    "00:11:11": "Intel Corporate", "00:12:f0": "Intel Corporate", "00:13:02": "Intel Corporate",
    "00:13:20": "Intel Corporate", "00:13:e8": "Intel Corporate", "00:15:00": "Intel Corporate",
    "00:15:17": "Intel Corporate", "00:16:6f": "Intel Corporate", "00:16:76": "Intel Corporate",
    "00:16:ea": "Intel Corporate", "00:16:eb": "Intel Corporate", "00:18:de": "Intel Corporate",
    "00:19:d1": "Intel Corporate", "00:1b:21": "Intel Corporate", "00:1c:bf": "Intel Corporate",
    "00:1d:e0": "Intel Corporate", "00:1e:64": "Intel Corporate", "00:1e:67": "Intel Corporate",
    "00:21:5c": "Intel Corporate", "00:21:6a": "Intel Corporate", "00:22:fb": "Intel Corporate",
    "00:23:14": "Intel Corporate", "00:24:d6": "Intel Corporate", "00:24:d7": "Intel Corporate",
    "34:13:e8": "Intel Corporate", "3c:fd:fe": "Intel Corporate", "40:a3:6b": "Intel Corporate",
    "48:51:b7": "Intel Corporate", "50:7b:9d": "Intel Corporate", "60:57:18": "Intel Corporate",
    "68:05:ca": "Intel Corporate", "6c:88:14": "Intel Corporate", "7c:57:58": "Intel Corporate",
    "80:86:f2": "Intel Corporate", "84:a9:38": "Intel Corporate", "8c:8d:28": "Intel Corporate",
    "94:65:9c": "Intel Corporate", "a0:36:9f": "Intel Corporate", "a4:4e:31": "Intel Corporate",
    "b4:96:91": "Intel Corporate", "c8:5b:76": "Intel Corporate", "cc:96:e5": "Intel Corporate",
    "d0:ab:d5": "Intel Corporate", "e8:2a:44": "Intel Corporate", "f4:4d:30": "Intel Corporate",

    # Cisco & Linksys
    "00:00:0c": "Cisco Systems", "00:01:42": "Cisco Systems", "00:01:43": "Cisco Systems",
    "00:01:63": "Cisco Systems", "00:01:64": "Cisco Systems", "00:01:96": "Cisco Systems",
    "00:01:97": "Cisco Systems", "00:01:c7": "Cisco Systems", "00:01:c9": "Cisco Systems",
    "00:02:16": "Cisco Systems", "00:02:17": "Cisco Systems", "00:02:4a": "Cisco Systems",
    "00:0c:41": "Cisco Systems", "00:0c:85": "Cisco Systems", "00:0e:38": "Cisco Systems",
    "00:12:01": "Cisco-Linksys", "00:13:10": "Cisco-Linksys", "00:14:bf": "Cisco-Linksys",
    "00:16:b6": "Cisco-Linksys", "00:18:39": "Cisco-Linksys", "00:1a:2b": "Cisco Systems",
    "00:1d:7e": "Cisco-Linksys", "00:1e:13": "Cisco Systems", "00:22:6b": "Cisco-Linksys",
    "00:26:0b": "Cisco Systems", "00:27:0d": "Cisco Systems", "c8:d7:19": "Cisco Systems",

    # Ubiquiti Networks
    "00:15:6d": "Ubiquiti Networks", "00:27:22": "Ubiquiti Networks", "24:a4:3c": "Ubiquiti Networks",
    "44:d9:e7": "Ubiquiti Networks", "68:72:51": "Ubiquiti Networks", "68:d7:9a": "Ubiquiti Networks",
    "70:85:c2": "Ubiquiti Networks", "78:8a:20": "Ubiquiti Networks", "80:2a:a8": "Ubiquiti Networks",
    "ac:8b:a9": "Ubiquiti Networks", "b4:fb:e4": "Ubiquiti Networks", "dc:9f:db": "Ubiquiti Networks",
    "e0:63:da": "Ubiquiti Networks", "f0:9f:c2": "Ubiquiti Networks", "fc:ec:da": "Ubiquiti Networks",

    # TP-Link
    "00:14:78": "TP-Link Technologies", "00:19:e0": "TP-Link Technologies", "00:1d:0f": "TP-Link Technologies",
    "00:21:27": "TP-Link Technologies", "00:23:cd": "TP-Link Technologies", "00:27:19": "TP-Link Technologies",
    "14:cc:20": "TP-Link Technologies", "1c:3b:f3": "TP-Link Technologies", "30:de:4b": "TP-Link Technologies",
    "50:c7:bf": "TP-Link Technologies", "60:32:b1": "TP-Link Technologies", "70:4f:57": "TP-Link Technologies",
    "84:16:f9": "TP-Link Technologies", "98:da:c4": "TP-Link Technologies", "a0:f3:c1": "TP-Link Technologies",
    "c0:25:e9": "TP-Link Technologies", "c0:4a:00": "TP-Link Technologies", "d8:0d:17": "TP-Link Technologies",
    "ec:08:6b": "TP-Link Technologies", "f4:ec:38": "TP-Link Technologies",

    # D-Link & Netgear
    "00:05:5d": "D-Link Systems", "00:0d:88": "D-Link Systems", "00:0f:3d": "D-Link Systems",
    "00:11:95": "D-Link Systems", "00:13:46": "D-Link Systems", "00:15:e9": "D-Link Systems",
    "00:18:e7": "Cameo Communications (D-Link)", "00:24:01": "D-Link International", "1c:7e:e5": "D-Link International",
    "00:09:5b": "Netgear", "00:0f:b5": "Netgear", "00:14:6c": "Netgear", "00:1b:2f": "Netgear",
    "00:1f:33": "Netgear", "20:4e:7f": "Netgear", "28:c6:8e": "Netgear", "84:1b:5e": "Netgear",
    "9c:3d:cf": "Netgear", "a0:04:60": "Netgear", "dc:ef:09": "Netgear", "e0:46:9a": "Netgear",

    # Raspberry Pi & Espressif (IoT)
    "28:cd:c1": "Raspberry Pi Trading Ltd", "b8:27:eb": "Raspberry Pi Foundation",
    "dc:a6:32": "Raspberry Pi Foundation", "e4:5f:01": "Raspberry Pi Foundation",
    "24:0a:c4": "Espressif Systems", "24:6f:28": "Espressif Systems", "24:b2:de": "Espressif Systems",
    "2c:3a:e8": "Espressif Systems", "30:ae:a4": "Espressif Systems", "3c:61:05": "Espressif Systems",
    "3c:71:bf": "Espressif Systems", "40:91:51": "Espressif Systems",
    "5c:cf:7f": "Espressif Systems", "60:01:94": "Espressif Systems", "68:c6:3a": "Espressif Systems",
    "84:0d:8e": "Espressif Systems", "84:f3:eb": "Espressif Systems", "a4:7b:9d": "Espressif Systems",
    "a4:cf:12": "Espressif Systems", "b4:e6:2d": "Espressif Systems", "bc:dd:c2": "Espressif Systems",
    "c4:4f:33": "Espressif Systems", "cc:50:e3": "Espressif Systems", "dc:4f:22": "Espressif Systems",

    # Asus, Lenovo, Samsung, Xiaomi, Huawei, Sony, Microsoft
    "00:11:d8": "ASUSTek Computer", "00:13:d4": "ASUSTek Computer", "00:15:af": "ASUSTek Computer",
    "00:18:f3": "ASUSTek Computer", "00:1b:fc": "ASUSTek Computer", "00:24:8c": "ASUSTek Computer",
    "04:d9:f5": "ASUSTek Computer", "10:7b:44": "ASUSTek Computer", "2c:fd:a1": "ASUSTek Computer",
    "00:12:fe": "Lenovo Mobile", "00:59:07": "Lenovo", "30:5a:3a": "Lenovo", "40:23:43": "Lenovo",
    "00:00:f0": "Samsung Electronics", "00:07:ab": "Samsung Electronics", "00:12:47": "Samsung Electronics",
    "00:15:99": "Samsung Electronics", "50:02:91": "Samsung Electronics", "a0:0b:ba": "Samsung Electronics",
    "18:f0:e4": "Xiaomi Communications", "28:6c:07": "Xiaomi Communications", "58:44:98": "Xiaomi Communications",
    "00:18:82": "Huawei Technologies", "00:1e:10": "Huawei Technologies", "00:25:9e": "Huawei Technologies",
    "00:04:1f": "Sony Interactive", "00:13:15": "Sony Interactive", "00:15:c1": "Sony Corporation",
    "00:15:5d": "Microsoft Hyper-V", "00:03:ff": "Microsoft Corporation", "7c:1e:52": "Microsoft Corporation",
    "00:0c:29": "VMware, Inc.", "00:50:56": "VMware, Inc.", "08:00:27": "Oracle VirtualBox", "52:54:00": "QEMU / KVM",
    "00:11:32": "Synology Incorporated", "00:08:9b": "QNAP Systems, Inc.", "24:5e:be": "QNAP Systems, Inc.",
    "00:04:4b": "NVIDIA Corporation", "48:b0:2d": "NVIDIA Corporation",
    "00:1a:11": "Google, Inc.", "3c:5a:b4": "Google, Inc.", "f4:f5:d8": "Google, Inc.",
    "00:09:0f": "Fortinet Inc.", "01:00:5e": "IPv4 Multicast", "ff:ff:ff": "Broadcast Address",
}

def is_locally_administered_mac(mac: str) -> bool:
    """Check if MAC address has IEEE 802 Locally Administered bit set (Private / Random MAC)."""
    try:
        clean = re.sub(r"[^0-9a-fA-F]", "", mac)
        if len(clean) >= 2:
            first_byte = int(clean[:2], 16)
            return bool(first_byte & 0x02)
    except Exception:
        pass
    return False

def lookup_mac_vendor(mac: str) -> str:
    """Find manufacturer vendor by MAC OUI with fallback for Private / Randomized MACs."""
    clean = re.sub(r"[^0-9a-fA-F]", "", mac).lower()
    if len(clean) >= 6:
        oui = f"{clean[0:2]}:{clean[2:4]}:{clean[4:6]}"
        if oui in OUI_DATABASE:
            return OUI_DATABASE[oui]
    if is_locally_administered_mac(mac):
        return "Private / Randomized MAC"
    return "Unknown Vendor"

def get_netbios_name(ip: str, timeout: float = 0.15) -> str:
    """Query NetBIOS Node Status (UDP 137) to get Windows / Samba / Printer computer name."""
    try:
        # RFC 1002 NBSTAT Query packet
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

def get_reverse_dns(ip: str) -> str:
    """Perform reverse DNS lookup for an IP."""
    try:
        return socket.gethostbyaddr(ip)[0]
    except Exception:
        return ""

async def get_arp_table() -> List[Dict[str, Any]]:
    """
    Parse OS ARP cache table to get IP, MAC address, vendor, and dynamically
    resolve device names via NetBIOS, DNS, and NetManager database.
    """
    system = platform.system().lower()
    loop = asyncio.get_event_loop()
    
    cmd = ["arp", "-an"] if system == "darwin" else (["arp", "-a"] if system == "windows" else ["ip", "neigh"])

    try:
        proc = await loop.run_in_executor(
            None,
            lambda: subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        )
        output = proc.stdout
    except Exception as e:
        return [{"error": f"Failed to run arp command: {e}"}]

    parsed_entries = []
    lines = output.splitlines()

    for line in lines:
        line = line.strip()
        if not line:
            continue

        ip = None
        mac = None
        if_name = ""

        if system == "darwin":
            # Format: ? (192.168.1.1) at 0:11:22:33:44:55 on en0 ifscope [ethernet]
            m = re.search(r"\(([\d\.]+)\)\s+at\s+([0-9a-fA-F:]+)\s+on\s+(\w+)", line)
            if m:
                ip = m.group(1)
                mac = m.group(2)
                if_name = m.group(3)
        elif system == "windows":
            # Format: 192.168.1.1      00-11-22-33-44-55     dynamic
            m = re.search(r"([\d\.]+)\s+([0-9a-fA-F\-]{17})\s+(\w+)", line)
            if m:
                ip = m.group(1)
                mac = m.group(2).replace("-", ":")
                if_name = m.group(3)
        else:  # linux
            # Format: 192.168.1.1 dev eth0 lladdr 00:11:22:33:44:55 REACHABLE
            m = re.search(r"([\d\.]+)\s+dev\s+(\w+)\s+lladdr\s+([0-9a-fA-F:]+)", line)
            if m:
                ip = m.group(1)
                if_name = m.group(2)
                mac = m.group(3)

        if ip and mac and mac.lower() not in ("(incomplete)", "ff:ff:ff:ff:ff:ff"):
            # Standardize MAC format with 2-digit hex zero padding
            parts = [f"{int(p, 16):02x}" for p in re.split(r"[:\-]", mac) if p]
            formatted_mac = ":".join(parts) if len(parts) == 6 else mac
            parsed_entries.append({
                "ip": ip,
                "mac": formatted_mac,
                "vendor": lookup_mac_vendor(formatted_mac),
                "interface": if_name,
            })

    # Fetch all registered devices from NetManager database
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
                    "hostname": d.hostname or "",
                    "group_name": d.group_name or "General",
                    "device_type": d.device_type or "Workstation",
                }
    except Exception:
        pass

    # Concurrent async name resolution
    sem = asyncio.Semaphore(60)

    async def _resolve_device_info(entry: Dict[str, Any]) -> Dict[str, Any]:
        ip = entry["ip"]
        ip_lower = ip.lower()

        # 1. Check if registered in NetManager DB
        if ip_lower in db_map:
            db_item = db_map[ip_lower]
            return {
                **entry,
                "device_name": db_item["name"],
                "hostname": db_item["hostname"],
                "group_name": db_item["group_name"],
                "device_type": db_item["device_type"],
                "name_source": "Saved Device",
                "is_registered": True,
                "device_id": db_item["id"],
            }

        # 2. Query NetBIOS & DNS in parallel
        async with sem:
            nb_name = await loop.run_in_executor(None, lambda: get_netbios_name(ip))
            if nb_name:
                is_printer = nb_name.upper().startswith("NPI") or nb_name.upper().startswith("CANON") or "PRINTER" in nb_name.upper()
                return {
                    **entry,
                    "device_name": nb_name,
                    "hostname": "",
                    "group_name": "Discovered",
                    "device_type": "Printer" if is_printer else "Workstation",
                    "name_source": "NetBIOS",
                    "is_registered": False,
                    "device_id": None,
                }

            rdns = await loop.run_in_executor(None, lambda: get_reverse_dns(ip))
            if rdns:
                return {
                    **entry,
                    "device_name": rdns,
                    "hostname": rdns,
                    "group_name": "Discovered",
                    "device_type": "Network Host",
                    "name_source": "DNS",
                    "is_registered": False,
                    "device_id": None,
                }

            # 3. If no name found, suggest from vendor
            vendor = entry.get("vendor", "")
            return {
                **entry,
                "device_name": "",
                "hostname": "",
                "group_name": "Discovered",
                "device_type": "Other" if vendor == "Unknown Vendor" else "Device",
                "name_source": "None",
                "is_registered": False,
                "device_id": None,
            }

    results = await asyncio.gather(*[_resolve_device_info(e) for e in parsed_entries])
    return results


# ─── 3. Subnet / CIDR Calculator ──────────────────────────────────────────────

def calculate_subnet(cidr: str) -> Dict[str, Any]:
    """Calculate full subnet breakdown given a CIDR notation (e.g. 192.168.1.0/24)."""
    try:
        net = ipaddress.ip_network(cidr.strip(), strict=False)
        hosts = list(net.hosts())
        
        # Calculate wildcard mask
        netmask_int = int(net.netmask)
        wildcard_int = ~netmask_int & 0xFFFFFFFF
        wildcard = str(ipaddress.IPv4Address(wildcard_int)) if net.version == 4 else "N/A"

        return {
            "cidr": str(net),
            "ip_version": net.version,
            "network_address": str(net.network_address),
            "netmask": str(net.netmask),
            "prefix_length": net.prefixlen,
            "wildcard_mask": wildcard,
            "broadcast_address": str(net.broadcast_address) if net.version == 4 else "N/A",
            "total_addresses": net.num_addresses,
            "usable_hosts": len(hosts),
            "first_usable_ip": str(hosts[0]) if hosts else str(net.network_address),
            "last_usable_ip": str(hosts[-1]) if hosts else str(net.network_address),
            "is_private": net.is_private,
            "is_loopback": net.is_loopback,
        }
    except Exception as e:
        raise ValueError(f"Invalid CIDR notation '{cidr}': {e}")


# ─── 4. SSL / TLS Certificate Checker ─────────────────────────────────────────

async def check_ssl_certificate(host: str, port: int = 443, timeout: float = 5.0) -> Dict[str, Any]:
    """Connect to a host via SSL/TLS and inspect the certificate validity & expiration."""
    clean_host = host.replace("https://", "").replace("http://", "").split("/")[0].split(":")[0].strip()
    loop = asyncio.get_event_loop()

    def _sync_check():
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE  # Allow reading expired/self-signed certs too

        with socket.create_connection((clean_host, port), timeout=timeout) as sock:
            with ctx.wrap_socket(sock, server_hostname=clean_host) as ssock:
                cert = ssock.getpeercert(binary_form=False)
                # If binary form needed because CERT_NONE returns empty cert dict:
                if not cert:
                    der_cert = ssock.getpeercert(binary_form=True)
                    # Use standard ssl._ssl._test_decode_cert or fallback parser
                    import ssl as _ssl_mod
                    try:
                        cert = _ssl_mod._ssl._test_decode_cert(der_cert)
                    except Exception:
                        pass
                cipher = ssock.cipher()
                version = ssock.version()
                return cert, cipher, version

    try:
        cert_data, cipher, tls_version = await loop.run_in_executor(None, _sync_check)
        
        subject = {}
        issuer = {}
        for item in cert_data.get("subject", []):
            for k, v in item:
                subject[k] = v
        for item in cert_data.get("issuer", []):
            for k, v in item:
                issuer[k] = v

        not_before = cert_data.get("notBefore", "")
        not_after = cert_data.get("notAfter", "")

        # Parse dates: e.g. "Aug 25 12:00:00 2026 GMT"
        days_left = None
        is_expired = False
        if not_after:
            try:
                exp_date = datetime.strptime(not_after, "%b %d %H:%M:%S %Y %Z")
                now = datetime.utcnow()
                delta = exp_date - now
                days_left = delta.days
                is_expired = days_left < 0
            except Exception:
                pass

        san = []
        for typ, name in cert_data.get("subjectAltName", []):
            san.append(name)

        return {
            "ok": True,
            "host": clean_host,
            "port": port,
            "tls_version": tls_version,
            "cipher": cipher[0] if cipher else "Unknown",
            "common_name": subject.get("commonName", clean_host),
            "organization": subject.get("organizationName", ""),
            "issuer_common_name": issuer.get("commonName", ""),
            "issuer_org": issuer.get("organizationName", ""),
            "valid_from": not_before,
            "valid_until": not_after,
            "days_left": days_left,
            "is_expired": is_expired,
            "alt_names": san[:10],
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        return {
            "ok": False,
            "host": clean_host,
            "port": port,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        }


# ─── 5. DNS Records Lookup ───────────────────────────────────────────────────

async def resolve_dns_records(domain: str) -> Dict[str, Any]:
    """Resolve DNS records (A, AAAA, PTR, CNAME) for a given domain/IP."""
    clean_domain = domain.replace("http://", "").replace("https://", "").split("/")[0].strip()
    loop = asyncio.get_event_loop()

    results: Dict[str, Any] = {
        "query": clean_domain,
        "a_records": [],
        "cname": "",
        "ptr": "",
        "timestamp": datetime.utcnow().isoformat(),
    }

    # Resolve IPv4 (A records)
    try:
        addr_info = await loop.run_in_executor(None, lambda: socket.getaddrinfo(clean_domain, None, socket.AF_INET))
        ips = sorted(list({item[4][0] for item in addr_info}))
        results["a_records"] = ips
    except Exception as e:
        results["a_error"] = str(e)

    # Reverse DNS (PTR)
    try:
        ptr = await loop.run_in_executor(None, lambda: socket.gethostbyaddr(clean_domain if results["a_records"] == [] else results["a_records"][0]))
        results["ptr"] = ptr[0]
    except Exception:
        pass

    return results

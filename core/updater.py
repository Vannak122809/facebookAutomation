"""
Auto-Update Module
==================
Works when run as a PyInstaller .exe OR as a normal Python script.

HOW IT WORKS:
1. version.json stores the current version (e.g., {"version": "1.0.0"})
2. On "Check for Update", fetches raw version.json from GitHub main branch
3. If remote version is newer, fetches GitHub Releases API to get the .exe download URL
4. Downloads new .exe alongside old one (.exe.new), then creates a .bat launcher
5. The .bat swaps ONLY the .exe binary — all user data (accounts, cookies, config) is untouched
6. App exits -> bat runs -> new exe starts -> bat deletes itself

DEVELOPER SETUP:
  1. Set GITHUB_REPO to your "username/repo"
  2. Set EXE_ASSET_NAME to the exact filename you attach to your GitHub Release
  3. Keep version.json in the root of your repo, update version before each release
  4. Create a GitHub Release with the .exe attached as an asset
"""

import os
import sys
import json
import urllib.request
import urllib.error

# ─── ⚙ DEVELOPER CONFIGURATION ─────────────────────────────────────────────
GITHUB_REPO      = "kiminato7777/Tool-invite-fri"
EXE_ASSET_NAME   = "ToolInviteFri.exe"   # exact filename in GitHub Release assets
VERSION_FILE_URL = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/version.json"
RELEASES_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
# ─────────────────────────────────────────────────────────────────────────────

LOCAL_VERSION_FILE = os.path.join(os.getcwd(), "version.json")


def _get_exe_dir() -> str:
    """Return the folder containing the running .exe (or script)."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(sys.argv[0]))


def get_local_version() -> str:
    """Read the local version from version.json."""
    try:
        vfile = os.path.join(_get_exe_dir(), "version.json")
        if not os.path.exists(vfile):
            vfile = LOCAL_VERSION_FILE
        if os.path.exists(vfile):
            with open(vfile, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("version", "0.0.0")
    except Exception:
        pass
    return "0.0.0"


def _compare_versions(v1: str, v2: str) -> int:
    """Compare semantic versions. Returns 1 if v1>v2, -1 if v1<v2, 0 if equal."""
    try:
        t1 = tuple(int(x) for x in v1.strip().split("."))
        t2 = tuple(int(x) for x in v2.strip().split("."))
        if t1 > t2: return 1
        if t1 < t2: return -1
        return 0
    except Exception:
        return 0


def check_for_update(timeout: int = 8) -> dict:
    """
    Check GitHub for a newer version.
    Returns dict with keys:
        has_update   — bool
        local        — str (current version)
        remote       — str (latest version on GitHub)
        download_url — str | None
        release_notes— str
        error        — str | None
    """
    local_version = get_local_version()
    result = {
        "has_update": False,
        "local": local_version,
        "remote": local_version,
        "download_url": None,
        "release_notes": "",
        "error": None
    }
    try:
        # 1. Fetch remote version.json from GitHub main branch
        req = urllib.request.Request(
            VERSION_FILE_URL,
            headers={"User-Agent": "ToolInviteFri-Updater/1.0"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            remote_data = json.loads(resp.read().decode("utf-8"))
        remote_version = remote_data.get("version", "0.0.0")
        result["remote"] = remote_version

        if _compare_versions(remote_version, local_version) <= 0:
            return result  # Already up to date

        # 2. Fetch latest release info (to get exe download URL)
        api_req = urllib.request.Request(
            RELEASES_API_URL,
            headers={
                "User-Agent": "ToolInviteFri-Updater/1.0",
                "Accept": "application/vnd.github.v3+json"
            }
        )
        with urllib.request.urlopen(api_req, timeout=timeout) as resp:
            release_data = json.loads(resp.read().decode("utf-8"))

        result["release_notes"] = release_data.get("body", "")

        for asset in release_data.get("assets", []):
            if asset.get("name") == EXE_ASSET_NAME:
                result["has_update"] = True
                result["download_url"] = asset.get("browser_download_url")
                break

        if result["has_update"] and not result["download_url"]:
            result["error"] = f"Release found but asset '{EXE_ASSET_NAME}' is not attached to it."

    except urllib.error.URLError as e:
        result["error"] = f"Network error: {e.reason}"
    except Exception as e:
        result["error"] = str(e)

    return result


def backup_user_data(exe_dir: str) -> str:
    """
    Safely copy all user data files to backups/pre_update_TIMESTAMP/.
    Data files that are preserved:
        account_history.json  — all accounts + statuses + stats
        config.json           — app settings
        categories.json       — custom categories
        version.json          — current version
        cookies/              — saved browser cookies per account
    Nothing is deleted. Returns the backup folder path.
    """
    import shutil
    import datetime

    data_files = [
        "account_history.json",
        "config.json",
        "categories.json",
        "version.json",
    ]
    data_dirs = ["cookies"]

    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = os.path.join(exe_dir, "backups", f"pre_update_{ts}")
    os.makedirs(backup_dir, exist_ok=True)

    for fname in data_files:
        src = os.path.join(exe_dir, fname)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(backup_dir, fname))

    for dname in data_dirs:
        src = os.path.join(exe_dir, dname)
        if os.path.isdir(src):
            shutil.copytree(src, os.path.join(backup_dir, dname), dirs_exist_ok=True)

    return backup_dir


def download_and_install(download_url: str, progress_callback=None, new_version: str = "") -> bool:
    """
    Download the new exe and create _update_launcher.bat to swap ONLY the exe file.

    ✅ WHAT IS UPDATED:   Only the .exe binary file
    ✅ WHAT IS PRESERVED: account_history.json, config.json, categories.json,
                          cookies/ folder — ALL user data stays 100% intact

    The bat launcher:
      1. Waits 2s for the running exe to exit cleanly
      2. Renames the downloaded .exe.new -> .exe  (only file changed)
      3. Updates version.json with the new version number
      4. Restarts the new exe
      5. Deletes itself

    Returns True on success.
    """
    import subprocess

    try:
        exe_dir = _get_exe_dir()

        if getattr(sys, "frozen", False):
            current_exe = sys.executable
        else:
            current_exe = os.path.abspath(sys.argv[0])

        # 1. Backup user data first (safety net before any file is touched)
        backup_user_data(exe_dir)

        # 2. Download new exe alongside the current one as a temp file
        download_path = current_exe + ".new"
        req = urllib.request.Request(
            download_url,
            headers={"User-Agent": "ToolInviteFri-Updater/1.0"}
        )
        with urllib.request.urlopen(req) as resp:
            total = int(resp.getheader("Content-Length", 0))
            downloaded = 0
            chunk_size = 65536  # 64 KB chunks
            with open(download_path, "wb") as out_file:
                while True:
                    chunk = resp.read(chunk_size)
                    if not chunk:
                        break
                    out_file.write(chunk)
                    downloaded += len(chunk)
                    if progress_callback:
                        progress_callback(downloaded, total)

        # 3. Write version.json update command (safe PowerShell inline)
        version_update_line = ""
        if new_version:
            vfile = os.path.join(exe_dir, "version.json").replace("\\", "\\\\")
            safe_ver = new_version.replace('"', '')
            version_update_line = (
                f'powershell -Command "$v=\'{{\\"version\\":\\"{safe_ver}\\"}}\'";'
                f'[IO.File]::WriteAllText(\\"{vfile}\\",$v,[Text.Encoding]::UTF8)" 2>nul\n'
            )

        # 4. Build the .bat swap script — only touches the .exe file
        bat_path = os.path.join(exe_dir, "_update_launcher.bat")
        bat_content = (
            "@echo off\n"
            "title Tool Invite Fri - Auto Updater\n"
            "echo ============================================\n"
            "echo  Tool Invite Fri - Applying Update...\n"
            "echo ============================================\n"
            "echo Waiting for application to fully close...\n"
            "timeout /t 2 /nobreak >nul\n"
            "\n"
            "echo Replacing application file...\n"
            f'move /Y "{download_path}" "{current_exe}"\n'
            "if errorlevel 1 (\n"
            "    echo ERROR: Could not replace the exe. Close all instances and retry.\n"
            "    pause\n"
            "    exit /b 1\n"
            ")\n"
            "\n"
            f"{version_update_line}"
            "\n"
            "echo ============================================\n"
            "echo  Update complete! Launching new version...\n"
            "echo ============================================\n"
            "timeout /t 1 /nobreak >nul\n"
            f'start "" "{current_exe}"\n'
            'del "%~f0"\n'
        )

        with open(bat_path, "w", encoding="utf-8") as f:
            f.write(bat_content)

        # 5. Launch bat and let current exe exit
        subprocess.Popen(
            ["cmd.exe", "/c", bat_path],
            creationflags=subprocess.CREATE_NEW_CONSOLE,
            close_fds=True
        )
        return True

    except Exception as e:
        print(f"[Updater] Error: {e}")
        return False

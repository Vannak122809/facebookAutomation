import os
import time
import random
import json
import base64
import hmac
import hashlib
import struct
import subprocess
import zipfile
from PySide6.QtCore import QThread, Signal
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

API_KEY = "AIzaSyBu0aZfd464GEOnAl4aZDpEPrhogWohga8"

def set_api_key(api_key: str):
    """Sets the global API key."""
    global API_KEY
    API_KEY = api_key

def get_api_key() -> str:
    """Returns the current API key."""
    return API_KEY

def generate_gemini_caption(prompt: str) -> str:
    """Generates a Facebook post caption using Google Gemini API."""
    import requests
    api_key = get_api_key()
    if not api_key:
        return "Please configure your API key in settings."
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    payload = {
        "contents": [{
            "parts": [{
                "text": f"សរសេរ Caption សម្រាប់ផុស Facebook ជាភាសាខ្មែរ ឱ្យទាក់ទាញ និងស្រស់ស្អាត (Write an attractive Facebook post caption in Khmer about this): {prompt}"
            }]
        }]
    }
    try:
        response = requests.post(url, json=payload, timeout=12)
        if response.status_code == 200:
            data = response.json()
            try:
                caption = data['candidates'][0]['content']['parts'][0]['text']
                return caption.strip()
            except Exception as parse_err:
                return f"Failed to parse Gemini response: {str(parse_err)}"
        else:
            return f"Error from Gemini API: {response.text[:200]}"
    except Exception as e:
        return f"Failed to connect to Gemini API: {str(e)}"

def parse_proxy_string(proxy_str):
    """Parses a proxy string into components.
    Supported formats:
    - host:port
    - host:port:user:pass
    - user:pass@host:port
    """
    proxy_str = proxy_str.strip()
    if not proxy_str:
        return None
        
    # Check for user:pass@host:port format
    if "@" in proxy_str:
        try:
            creds, server = proxy_str.split("@", 1)
            user, password = creds.split(":", 1)
            host, port = server.split(":", 1)
            return {
                "host": host,
                "port": port,
                "user": user,
                "pass": password
            }
        except:
            pass

    # Check for host:port:user:pass format or host:port
    parts = proxy_str.split(":")
    if len(parts) == 2:
        return {
            "host": parts[0],
            "port": parts[1],
            "user": None,
            "pass": None
        }
    elif len(parts) == 4:
        return {
            "host": parts[0],
            "port": parts[1],
            "user": parts[2],
            "pass": parts[3]
        }
    return None

def create_proxy_auth_extension(proxy_host, proxy_port, proxy_username, proxy_password):
    """Creates a temporary Chrome extension .zip file to authenticate proxies."""
    manifest_json = """{
        "version": "1.0.0",
        "manifest_version": 2,
        "name": "Chrome Proxy Auth Extension",
        "permissions": [
            "proxy",
            "tabs",
            "unlimitedStorage",
            "storage",
            "<all_urls>",
            "webRequest",
            "webRequestBlocking"
        ],
        "background": {
            "scripts": ["background.js"]
        },
        "minimum_chrome_version":"22.0.0"
    }"""

    background_js = """var config = {
            mode: "fixed_servers",
            rules: {
              singleProxy: {
                scheme: "http",
                host: "%s",
                port: parseInt(%s)
              },
              bypassList: []
            }
          };

    chrome.proxy.settings.set({value: config, scope: "regular"}, function() {});

    chrome.webRequest.onAuthRequired.addListener(
            function(details) {
                return {
                    authCredentials: {
                        username: "%s",
                        password: "%s"
                    }
                };
            },
            {urls: ["<all_urls>"]},
            ["blocking"]
    );""" % (proxy_host, proxy_port, proxy_username, proxy_password)

    temp_dir = os.path.abspath("temp_extensions")
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)
        
    zip_path = os.path.join(temp_dir, f"proxy_auth_{proxy_host}_{proxy_port}.zip")
    with zipfile.ZipFile(zip_path, 'w') as zip_file:
        zip_file.writestr("manifest.json", manifest_json)
        zip_file.writestr("background.js", background_js)
    return zip_path

def generate_totp(secret):
    """Generates a 6-digit TOTP code from a base32 secret key (Pure Python implementation)."""
    try:
        secret = secret.replace(" ", "").strip()
        if not secret:
            return ""
        # Pad secret if needed
        missing_padding = len(secret) % 8
        if missing_padding:
            secret += '=' * (8 - missing_padding)
        key = base64.b32decode(secret, casefold=True)
        # 30-second time interval
        intervals_no = int(time.time() // 30)
        msg = struct.pack(">Q", intervals_no)
        # Generate HMAC-SHA1 signature
        h = hmac.new(key, msg, hashlib.sha1).digest()
        # Dynamic truncation to get 4-byte value
        o = h[19] & 15
        token = (struct.unpack(">I", h[o:o+4])[0] & 0x7fffffff) % 1000000
        return f"{token:06d}"
    except Exception as e:
        return f"Error: {str(e)}"

class SeleniumWorker(QThread):
    # Signals to communicate with the GUI
    log_signal = Signal(str, str, str)  # username, level (INFO/SUCCESS/ERROR), message
    status_signal = Signal(str, str)     # username, status_text
    stats_signal = Signal(str, int, int) # username, invites_sent, invites_failed
    finished_signal = Signal(str, bool)  # username, success
    profile_signal = Signal(str, str, int) # username, profile_name, friend_count

    def __init__(self, account, page_urls, xpath_settings, options_settings, manual_control=False, window_index=0):
        super().__init__()
        self.account = account
        self.page_urls = page_urls
        self.xpath_settings = xpath_settings
        self.options_settings = options_settings  # headless, mobile_device, delay_range, etc.
        self.driver = None
        self.launcher = None
        self.is_running = True
        self.manual_control = manual_control
        self.window_index = window_index

    def run(self):
        username = self.account.username
        
        # Determine window position slot
        n = self.window_index or 0
        tile_w = self.options_settings.get("tile_width", 400)
        tile_h = self.options_settings.get("tile_height", 700)
        
        # Dynamic Grid index positioning (100% dynamic based on screen resolution)
        try:
            from PySide6.QtWidgets import QApplication
            screen_w = QApplication.primaryScreen().size().width()
            max_cols = max(1, screen_w // tile_w)
        except:
            max_cols = 4  # Fallback
            
        col = n % max_cols
        row = n // max_cols
        x = col * tile_w
        y = row * tile_h  # Perfect vertical stack for additional rows

        # Load per-account post settings
        photo_path = self.options_settings.get("photo_path", "")
        video_path = self.options_settings.get("video_path", "")
        post_caption = self.options_settings.get("post_caption", "")

        try:
            import json
            post_settings_file = "post_settings.json"
            if os.path.exists(post_settings_file):
                with open(post_settings_file, "r", encoding="utf-8") as f:
                    saved_settings = json.load(f)
                acc_settings = saved_settings.get(username, {})
                if acc_settings:
                    if acc_settings.get("photo_path"):
                        photo_path = acc_settings["photo_path"]
                    if acc_settings.get("video_path"):
                        video_path = acc_settings["video_path"]
                    if acc_settings.get("post_caption"):
                        post_caption = acc_settings["post_caption"]
                    if acc_settings.get("target_pages"):
                        # Parse comma-separated page URLs
                        pages_str = acc_settings["target_pages"]
                        custom_pages = [p.strip() for p in pages_str.split(",") if p.strip()]
                        if custom_pages:
                            self.page_urls = custom_pages
        except Exception as e:
            print(f"Error loading per-account settings: {e}")

        # Prepare settings dict for BrowserLauncher
        settings = {
            "headless": self.options_settings.get("headless", False),
            "tile_width": tile_w,
            "tile_height": tile_h,
            "invite_count": self.options_settings.get("invite_count", 25),
            "confirm_friend_count": self.options_settings.get("confirm_friend_count", 50),
            "add_friend_count": self.options_settings.get("add_friend_count", 10),
            "feed_mins": self.options_settings.get("feed_mins", 5),
            "video_feed_mins": self.options_settings.get("video_feed_mins", 5),
            "join_group_count": self.options_settings.get("join_group_count", 3),
            "share_group_count": self.options_settings.get("share_group_count", 3),
            "story_count": self.options_settings.get("story_count", 5),
            "scrape_limit": self.options_settings.get("scrape_limit", 100),
            "group_keyword": self.options_settings.get("group_keyword", "Shopping"),
            "random_reactions": self.options_settings.get("random_reactions", False),
            "photo_path": photo_path,
            "video_path": video_path,
            "post_caption": post_caption,
            "default_ua": self.options_settings.get("custom_user_agent", "")
        }

        # Profile data folder path
        profile_path = os.path.join(os.getcwd(), "profiles", f"profile_{username}")
        os.makedirs(profile_path, exist_ok=True)

        user_agent = self.options_settings.get("custom_user_agent", "")
        proxy = self.account.proxy

        # Import BrowserLauncher dynamically
        from browser import BrowserLauncher

        # Status and Log callback
        def status_callback(msg):
            self.status_signal.emit(username, msg)
            level = "INFO"
            if "✅" in msg or "success" in msg.lower() or "done" in msg.lower():
                level = "SUCCESS"
            elif "❌" in msg or "error" in msg.lower() or "failed" in msg.lower():
                level = "ERROR"
            elif "⚠️" in msg or "warning" in msg.lower():
                level = "WARNING"
            self.log_signal.emit(username, level, msg)

            # Parse stats
            try:
                import re
                match = re.search(r'(?:Added|Confirmed)\s+(\d+)', msg)
                if match:
                    self.stats_signal.emit(username, int(match.group(1)), 0)
                else:
                    match2 = re.search(r'Done!\s+(\d+)\s+Sent', msg)
                    if match2:
                        self.stats_signal.emit(username, int(match2.group(1)), 0)
            except:
                pass

        if self.manual_control:
            self.status_signal.emit(username, "Manual Control")
            self.log_signal.emit(username, "INFO", "Starting browser in manual mode...")
            try:
                self.launcher = BrowserLauncher(user_agent=user_agent, proxy=proxy, x=x, y=y, settings=settings)
                # Force visible browser
                self.launcher.settings["headless"] = False
                self.driver = self.launcher.launch_facebook_mobile(profile_path)
                
                # Check for cookies/auto-login
                cookie_file = os.path.join("cookies", f"{username}.json")
                if os.path.exists(cookie_file):
                    self.log_signal.emit(username, "INFO", "Loading saved cookies for manual session...")
                    # Implement simple cookie load
                    self.driver.get("https://m.facebook.com/")
                    time.sleep(2)
                    with open(cookie_file, 'r') as f:
                        cookies = json.load(f)
                    for cookie in cookies:
                        if 'expiry' in cookie:
                            cookie['expiry'] = int(cookie['expiry'])
                        self.driver.add_cookie(cookie)
                    self.driver.refresh()
                    time.sleep(3)
                else:
                    self.driver.get("https://m.facebook.com/")

                self.log_signal.emit(username, "SUCCESS", "Manual control active. Close the Chrome window to finish.")
                
                # Wait while running
                while self.is_running:
                    try:
                        _ = self.driver.window_handles
                        time.sleep(1)
                    except:
                        break
                
                if self.driver:
                    # Save cookies on exit
                    os.makedirs("cookies", exist_ok=True)
                    cookies = self.driver.get_cookies()
                    with open(cookie_file, 'w') as f:
                        json.dump(cookies, f, indent=4)
                    self.log_signal.emit(username, "SUCCESS", "Manual session finished. Cookies updated.")
                
                self.status_signal.emit(username, "Completed")
                self.finished_signal.emit(username, True)
            except Exception as e:
                self.log_signal.emit(username, "ERROR", f"Manual session ended with error: {str(e)}")
                self.status_signal.emit(username, "Error")
                self.finished_signal.emit(username, False)
            finally:
                self.close_driver()
            return

        # Sequential task execution mode
        self.status_signal.emit(username, "Initializing browser...")
        self.log_signal.emit(username, "INFO", "Starting browser session...")

        try:
            self.launcher = BrowserLauncher(user_agent=user_agent, proxy=proxy, x=x, y=y, settings=settings)
            
            # Setup headless based on visibility settings
            # We map options_settings["headless"]
            headless = self.options_settings.get("headless", False)
            # BrowserLauncher options add argument if headless
            # (launch_facebook_mobile reads the options and creates the driver)
            self.driver = self.launcher.launch_facebook_mobile(profile_path)
            
            # Perform login
            self.status_signal.emit(username, "Logging in...")
            profile_info = self.launcher.auto_login(
                uid=self.account.username,
                password=self.account.password,
                twofa_secret=self.account.two_factor_secret,
                status_callback=status_callback
            )

            if not profile_info:
                self.account.status = "Dead"
                self.status_signal.emit(username, "Dead")
                self.finished_signal.emit(username, False)
                return
            elif "error" in profile_info:
                err_msg = profile_info["error"]
                self.account.status = err_msg
                self.status_signal.emit(username, err_msg)
                self.finished_signal.emit(username, False)
                return

            # Sync profile data
            profile_name = profile_info.get("name", "FB User")
            friend_count = int(profile_info.get("friends", "0"))
            self.account.profile_name = profile_name
            self.account.friend_count = friend_count
            self.account.status = "Active"
            
            # Update GUI table
            self.profile_signal.emit(username, profile_name, friend_count)
            self.status_signal.emit(username, "Active")

            # Save cookie session
            cookie_file = os.path.join("cookies", f"{username}.json")
            os.makedirs("cookies", exist_ok=True)
            if self.driver:
                cookies = self.driver.get_cookies()
                with open(cookie_file, 'w') as f:
                    json.dump(cookies, f, indent=4)

            # Get selected tasks list
            tasks = self.options_settings.get("tasks", ["login"])
            target_links = list(self.page_urls)
            random.shuffle(target_links)
            delay_min, delay_max = self.options_settings.get("delay_range", (2, 5))

            successful_tasks = []
            for task in tasks:
                if not self.is_running:
                    break
                
                if task == "login":
                    # already logged in, skip
                    continue
                
                self.status_signal.emit(username, f"Running: {task}...")
                self.log_signal.emit(username, "INFO", f"Executing task '{task}'...")

                try:
                    if task == "warmup":
                        status_callback("🔥 Starting Warm-up...")
                        self.launcher.scroll_feeds(minutes=2, random_reactions=True, status_callback=status_callback)
                        if self.is_running:
                            self.launcher.watch_video(minutes=2, random_reactions=True, status_callback=status_callback)
                    
                    elif task == "feeds":
                        self.launcher.scroll_feeds(
                             minutes=settings["feed_mins"], 
                             random_reactions=settings["random_reactions"], 
                             status_callback=status_callback
                        )
                    
                    elif task == "watch_video":
                        self.launcher.watch_video(
                             minutes=settings["video_feed_mins"], 
                             random_reactions=settings["random_reactions"], 
                             status_callback=status_callback
                        )
                    
                    elif task == "watch_stories":
                        self.launcher.watch_stories(
                             count=settings["story_count"], 
                             random_reactions=settings["random_reactions"], 
                             status_callback=status_callback
                        )
                    
                    elif task == "invite":
                        if target_links:
                            for idx, link in enumerate(target_links):
                                if not self.is_running:
                                    break
                                status_callback(f"✉️ Page {idx+1}/{len(target_links)}: {link}")
                                try:
                                    self.driver.get(link)
                                    time.sleep(5)
                                    self.launcher.invite_friends(status_callback=status_callback)
                                    time.sleep(3)
                                except Exception as e:
                                    status_callback(f"⚠️ Failed on link {link}: {str(e)[:50]}")
                        else:
                            self.launcher.invite_friends(status_callback=status_callback)
                    
                    elif task == "add_friend":
                        self.launcher.add_friend(count=settings["add_friend_count"], status_callback=status_callback)
                    
                    elif task == "confirm_friend":
                        self.launcher.confirm_friend(count=settings["confirm_friend_count"], status_callback=status_callback)
                    
                    elif task == "join_groups":
                        self.launcher.join_groups(
                             keyword=settings["group_keyword"], 
                             count=settings["join_group_count"], 
                             status_callback=status_callback
                        )
                    
                    elif task == "share_groups":
                        if target_links:
                            for idx, link in enumerate(target_links):
                                if not self.is_running:
                                    break
                                status_callback(f"📢 Post {idx+1}/{len(target_links)}: {link}")
                                try:
                                    self.launcher.share_post_to_groups(
                                         post_url=link, 
                                         count=settings["share_group_count"], 
                                         status_callback=status_callback
                                    )
                                    time.sleep(3)
                                except Exception as e:
                                    status_callback(f"⚠️ Failed to share post {link}: {str(e)[:50]}")
                        else:
                            status_callback("⚠️ No targets found for sharing post")
                    
                    elif task == "invite_like":
                        if target_links:
                            for idx, link in enumerate(target_links):
                                if not self.is_running:
                                    break
                                status_callback(f"👍 Page {idx+1}/{len(target_links)}: {link}")
                                try:
                                    self.driver.get(link)
                                    time.sleep(5)
                                    self.launcher.invite_like_page(status_callback=status_callback)
                                    time.sleep(3)
                                except Exception as e:
                                    status_callback(f"⚠️ Failed on link {link}: {str(e)[:50]}")
                        else:
                            self.launcher.invite_like_page(status_callback=status_callback)
                    
                    elif task == "post_photo":
                        caption = settings["post_caption"]
                        if caption.lower().startswith("ai:") or caption.lower().startswith("gemini:"):
                            prompt = caption.split(":", 1)[1].strip()
                            status_callback("🤖 Generating AI caption using Gemini...")
                            caption = generate_gemini_caption(prompt)
                        self.launcher.auto_post_photo(
                             photo_path=settings["photo_path"], 
                             caption=caption, 
                             status_callback=status_callback
                        )
                    
                    elif task == "post_reel":
                        caption = settings["post_caption"]
                        if caption.lower().startswith("ai:") or caption.lower().startswith("gemini:"):
                            prompt = caption.split(":", 1)[1].strip()
                            status_callback("🤖 Generating AI caption using Gemini...")
                            caption = generate_gemini_caption(prompt)
                        self.launcher.auto_post_reel(
                             video_path=settings["video_path"], 
                             caption=caption, 
                             status_callback=status_callback
                        )
                    
                    elif task == "scrape_uids":
                        if target_links:
                            for idx, link in enumerate(target_links):
                                if not self.is_running:
                                    break
                                status_callback(f"🔍 URL {idx+1}/{len(target_links)}: {link}")
                                try:
                                    self.launcher.scrape_uids(
                                         target_url=link, 
                                         limit=settings["scrape_limit"], 
                                         status_callback=status_callback
                                    )
                                    time.sleep(3)
                                except Exception as e:
                                    status_callback(f"⚠️ Failed to scrape link {link}: {str(e)[:50]}")
                        else:
                            status_callback("⚠️ No target URL for UID scraping")

                    successful_tasks.append(task)

                    # Apply delay pause between sequential tasks to emulate realistic human behavior
                    if self.is_running and task != tasks[-1]:
                        sleep_time = random.randint(delay_min, delay_max)
                        status_callback(f"⏳ Pausing {sleep_time}s before next task...")
                        time.sleep(sleep_time)

                except Exception as task_err:
                    self.log_signal.emit(username, "ERROR", f"Task '{task}' failed with error: {str(task_err)}")
                    status_callback(f"⚠️ Task '{task}' failed, proceeding to next selected function...")

            # Clean cache/bloat
            status_callback("🧹 Cleaning browser cache and profile bloat...")
            self.launcher.clean_profile_bloat(profile_path)
            
            # --- Return Home, Reload, Alert, then Close ---
            if not self.manual_control and not self.options_settings.get("headless", False) and any(t != "login" for t in tasks):
                if self.driver:
                    try:
                        status_callback("🏠 Returning home...")
                        self.driver.get("https://www.facebook.com/")
                        time.sleep(2)
                        status_callback("🔄 Reloading page...")
                        self.driver.refresh()
                        time.sleep(3)
                        
                        task_translation = {
                            "warmup": "Warm-up (កំដៅគណនី)",
                            "feeds": "Scroll Feeds (អូសហ្វត)",
                            "watch_video": "Watch Video (មើលវីដេអូ)",
                            "watch_stories": "Watch Stories (មើលរឿង)",
                            "invite": "Invite Friends (អញ្ជើញមិត្តភក្តិ)",
                            "add_friend": "Add Friends (បន្ថែមមិត្តភក្តិ)",
                            "confirm_friend": "Confirm Friends (ទទួលមិត្តភក្តិ)",
                            "join_groups": "Join Groups (ចូលក្រុម)",
                            "share_groups": "Share to Groups (ចែករំលែកទៅក្រុម)",
                            "invite_like": "Invite to Like Page (អញ្ជើញឡាចផេក)",
                            "post_photo": "Post Photo (ផុសរូបភាព)",
                            "post_reel": "Post Reel (ផុសវីដេអូខ្លី)",
                            "scrape_uids": "Scrape UIDs (ទាញយក UID)"
                        }
                        
                        # Build tasks HTML
                        tasks_html = ""
                        if successful_tasks:
                            for t in successful_tasks:
                                friendly_name = task_translation.get(t, t)
                                tasks_html += f'<div class="task-item"><span>✅</span> <span>{friendly_name}</span></div>'
                        else:
                            tasks_html += '<div class="task-item" style="color: #ef4444 !important;"><span>❌</span> <span>គ្មានភារកិច្ចដែលសម្រេចជោគជ័យទេ</span></div>'

                        modal_template = f"""
<div id="custom-modern-modal-overlay" style="
    position: fixed !important;
    top: 0 !important;
    left: 0 !important;
    width: 100% !important;
    height: 100% !important;
    background: rgba(15, 23, 42, 0.6) !important;
    backdrop-filter: blur(6px) !important;
    -webkit-backdrop-filter: blur(6px) !important;
    z-index: 2147483647 !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    font-family: 'Segoe UI', system-ui, -apple-system, sans-serif !important;
">
    <div id="custom-modern-modal" data-clicked="false" style="
        background: #ffffff !important;
        color: #0f172a !important;
        width: 90% !important;
        max-width: 290px !important;
        border-radius: 16px !important;
        box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.15), 0 10px 10px -5px rgba(0, 0, 0, 0.05) !important;
        padding: 18px !important;
        text-align: center !important;
        border: 1px solid rgba(226, 232, 240, 0.8) !important;
        box-sizing: border-box !important;
        font-family: inherit !important;
        animation: modalFadeIn 0.25s cubic-bezier(0.34, 1.56, 0.64, 1) !important;
    ">
        <style>
            @keyframes modalFadeIn {{
                from {{ transform: scale(0.9) !important; opacity: 0 !important; }}
                to {{ transform: scale(1) !important; opacity: 1 !important; }}
            }}
            .success-btn {{
                background: linear-gradient(135deg, #3b82f6, #2563eb) !important;
                color: white !important;
                border: none !important;
                border-radius: 10px !important;
                padding: 10px 20px !important;
                font-size: 13px !important;
                font-weight: 700 !important;
                cursor: pointer !important;
                width: 100% !important;
                margin-top: 12px !important;
                box-shadow: 0 4px 6px -1px rgba(37, 99, 235, 0.2) !important;
                font-family: inherit !important;
                box-sizing: border-box !important;
                transition: all 0.2s ease !important;
            }}
            .success-btn:hover {{
                box-shadow: 0 6px 12px -1px rgba(37, 99, 235, 0.3) !important;
                filter: brightness(1.05) !important;
                transform: translateY(-1px) !important;
            }}
            .success-btn:active {{
                transform: translateY(1px) !important;
            }}
            .task-item {{
                display: flex !important;
                align-items: center !important;
                gap: 8px !important;
                background: #f8fafc !important;
                border-radius: 8px !important;
                padding: 8px 12px !important;
                margin-bottom: 6px !important;
                font-size: 11.5px !important;
                font-weight: 600 !important;
                color: #334155 !important;
                text-align: left !important;
                border: 1px solid #e2e8f0 !important;
                box-sizing: border-box !important;
                font-family: inherit !important;
            }}
        </style>
        
        <!-- Icon -->
        <div style="
            width: 46px !important;
            height: 46px !important;
            background: #dcfce7 !important;
            color: #15803d !important;
            border-radius: 50% !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            font-size: 24px !important;
            margin: 0 auto 12px auto !important;
        ">✓</div>
        
        <!-- Title -->
        <h3 style="
            margin: 0 0 6px 0 !important;
            font-size: 16px !important;
            font-weight: 800 !important;
            color: #1e293b !important;
            font-family: inherit !important;
        ">ភារកិច្ចត្រូវបានបញ្ចប់!</h3>
        
        <!-- Description -->
        <p style="
            margin: 0 0 12px 0 !important;
            font-size: 12px !important;
            color: #64748b !important;
            line-height: 1.4 !important;
            font-family: inherit !important;
        ">គណនី <b>{username}</b> បានបញ្ចប់ការងារ ១០០% ហើយ!</p>
        
        <!-- Task List Header -->
        <div style="
            text-align: left !important;
            font-size: 9.5px !important;
            font-weight: 700 !important;
            color: #94a3b8 !important;
            text-transform: uppercase !important;
            letter-spacing: 0.05em !important;
            margin-bottom: 6px !important;
            font-family: inherit !important;
        ">ភារកិច្ចដែលសម្រេចជោគជ័យ</div>
        
        <!-- Task List -->
        <div style="max-height: 110px !important; overflow-y: auto !important; margin-bottom: 6px !important;">
            {tasks_html}
        </div>
        
        <!-- OK Button -->
        <button class="success-btn" onclick="document.getElementById('custom-modern-modal').setAttribute('data-clicked', 'true'); document.getElementById('custom-modern-modal-overlay').remove();">
            OK / បិទ (5s)
        </button>
    </div>
</div>
"""
                        status_callback("🔔 Showing modern success alert...")
                        escaped_modal_html = modal_template.replace("`", "\\`").replace("'", "\\'")
                        
                        js_script = f"""
                        var existing = document.getElementById('custom-modern-modal-overlay');
                        if (existing) existing.remove();
                        var div = document.createElement('div');
                        div.innerHTML = `{escaped_modal_html}`;
                        document.body.appendChild(div.firstElementChild);
                        
                        // Start countdown timer to close automatically after 5 seconds
                        (function() {{
                            var timeLeft = 5;
                            var overlay = document.getElementById('custom-modern-modal-overlay');
                            var modal = document.getElementById('custom-modern-modal');
                            var btn = overlay ? overlay.querySelector('.success-btn') : null;
                            
                            var timer = setInterval(function() {{
                                timeLeft--;
                                if (timeLeft <= 0) {{
                                    clearInterval(timer);
                                    if (modal) {{
                                        modal.setAttribute('data-clicked', 'true');
                                    }}
                                    if (overlay) {{
                                        overlay.remove();
                                    }}
                                }} else {{
                                    if (btn) {{
                                        btn.innerHTML = 'OK / បិទ (' + timeLeft + 's)';
                                    }}
                                }}
                            }}, 1000);
                        }})();
                        """
                        self.driver.execute_script(js_script)
                        
                        # Wait for user validation
                        start_wait = time.time()
                        while self.is_running and (time.time() - start_wait < 7): # Timeout after 7 seconds
                            try:
                                modal = self.driver.find_element(By.ID, "custom-modern-modal")
                                clicked = modal.get_attribute("data-clicked")
                                if clicked == "true":
                                    break
                            except:
                                break
                            time.sleep(0.5)
                    except Exception as alert_err:
                        self.log_signal.emit(username, "WARNING", f"Could not show alert: {str(alert_err)}")

            self.status_signal.emit(username, "Completed")
            self.log_signal.emit(username, "SUCCESS", "All requested tasks finished!")
            self.finished_signal.emit(username, True)

        except Exception as e:
            self.account.status = "Dead"
            self.log_signal.emit(username, "ERROR", f"Critical automation error: {str(e)}")
            self.status_signal.emit(username, "Error")
            self.finished_signal.emit(username, False)
        finally:
            self.close_driver()

    def close_driver(self):
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
            self.driver = None
        
        if self.launcher:
            try:
                if hasattr(self.launcher, 'close'):
                    self.launcher.close()
            except:
                pass
            self.launcher = None

    def stop(self):
        self.is_running = False
        self.close_driver()

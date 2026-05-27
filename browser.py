import os
import time
import random
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from webdriver_manager.chrome import ChromeDriverManager
import pyotp
import shutil

class BrowserLauncher:
    def __init__(self, user_agent=None, proxy=None, x=0, y=0, settings=None):
        self.user_agent = user_agent
        self.proxy = proxy
        self.x = x
        self.y = y
        self.settings = settings or {}
        self.driver = None
        
        # Override default UA if provided in settings but not specific to account
        if not self.user_agent and "default_ua" in self.settings:
            self.user_agent = self.settings["default_ua"]

    def launch_facebook_mobile(self, profile_path=None):
        options = Options()
        # 1. Apply dynamically chosen UA / Platform Fingerprint
        # Upgraded to LATEST High-Stability Windows UAs (Chrome 124+)
        platforms = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 11.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0"
        ]
        if not self.user_agent:
            self.user_agent = random.choice(platforms)
            
        options.add_argument(f'--user-agent={self.user_agent}')
        
        # Language Fingerprinting
        langs = ["en-US,en;q=0.9" ]
        options.add_argument(f'--accept-lang={random.choice(langs)}')
        
        # 2. Add standard mobile arguments and positioning
        options.add_argument('--app=https://www.facebook.com/login/')
        
        # Randomize resolution slightly to mask fingerprint
        base_w = self.settings.get("tile_width", 400)
        base_h = self.settings.get("tile_height", 700)
        
        # Ensure we stay exactly within the tile boundaries for flush alignment
        w_final = base_w
        h_final = base_h
        
        options.add_argument(f'--window-size={w_final},{h_final}')
        options.add_argument(f'--window-position={self.x},{self.y}')
        
        # Standard Professional Browser Arguments
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--display-capture-permissions-policy-allowed')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        options.add_argument('--password-store=basic')
        options.add_argument('--no-first-run')
        
        # Performance & Consistency (Enabling GPU for Standard support)
        options.add_argument('--ignore-certificate-errors')
        options.add_argument('--allow-running-insecure-content')
        options.add_argument('--disable-site-isolation-trials')
        
        # Minimize resource bloat
        options.add_argument('--disk-cache-size=5242880') # 5MB Limit
        options.add_argument('--media-cache-size=5242880') 
        options.add_argument('--disable-gpu-shader-disk-cache')
        options.add_argument('--disable-metrics')
        options.add_argument('--disable-component-update')
        
        if profile_path:
            options.add_argument(f'user-data-dir={profile_path}')
            
        if self.proxy:
            options.add_argument(f'--proxy-server={self.proxy}')

        if self.settings.get("headless", False):
            options.add_argument('--headless=new')
            options.add_argument('--disable-gpu')

        # Suppress log messages
        options.add_experimental_option('excludeSwitches', ['enable-logging'])
        
        import subprocess
        service = Service(ChromeDriverManager().install())
        if os.name == 'nt':
            service.creation_flags = subprocess.CREATE_NO_WINDOW
        self.driver = webdriver.Chrome(service=service, options=options)
        
        # Apply Stealth Script
        self.apply_stealth()
        
        return self.driver

    def apply_stealth(self):
        """Injects comprehensive script to mask automation footprint and simulate a standard browser."""
        if not self.driver: return
        stealth_script = """
        // 1. Mask navigator.webdriver fully
        Object.defineProperty(navigator, 'webdriver', { get: () => undefined });

        // 2. Remove 'cdc_' automation markers from window properties
        const maskAutomation = () => {
            const keys = Object.keys(window);
            for (const key of keys) {
                if (key.includes('cdc_') || key.includes('webdriver')) {
                    delete window[key];
                }
            }
        };
        maskAutomation();

        // 3. Mock userAgentData (Latest Chrome 124)
        if (!navigator.userAgentData) {
            Object.defineProperty(navigator, 'userAgentData', {
                get: () => ({
                    brands: [
                        {brand: 'Google Chrome', version: '124'},
                        {brand: 'Chromium', version: '124'},
                        {brand: 'Not-A.Brand', version: '99'}
                    ],
                    mobile: false,
                    platform: 'Windows'
                })
            });
        }

        // 3. Mock window.chrome for standard compatibility
        window.chrome = {
            runtime: {},
            loadTimes: () => ({}),
            csi: () => ({}),
            app: { isInstalled: false }
        };

        // 4. Mock Permissions
        const originalQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = (parameters) => (
            parameters.name === 'notifications' ?
            Promise.resolve({ state: Notification.permission }) :
            originalQuery(parameters)
        );

        // 5. Mock Plugins (Standard browser list)
        Object.defineProperty(navigator, 'plugins', {
            get: () => {
                const p = [
                    { name: 'PDF Viewer', filename: 'internal-pdf-viewer', description: 'Portable Document Format' },
                    { name: 'Chrome PDF Viewer', filename: 'internal-pdf-viewer', description: 'Google Chrome PDF' }
                ];
                p.item = (i) => p[i];
                p.namedItem = (n) => p.find(x => x.name === n);
                return p;
            }
        });

        // 6. Fix for WebGL/Canvas fingerprinting
        const getParameter = WebGLRenderingContext.prototype.getParameter;
        WebGLRenderingContext.prototype.getParameter = function(parameter) {
            if (parameter === 37445) return 'Intel Inc.';
            if (parameter === 37446) return 'Intel(R) Iris(R) Xe Graphics';
            return getParameter.apply(this, arguments);
        };

        // 8. Aggressive App Upsell Blocker
        const style = document.createElement('style');
        style.innerText = `
            /* Hide sticky banners, upsell containers and Bloks elements */
            div[role="banner"], div[id*="upsell"], div[class*="upsell"], 
            div[class*="banner"], a[href*="fb.me"], [aria-label*="Get Facebook"],
            div[style*="position: sticky"], div[style*="position:fixed"] {
                display: none !important;
                height: 0px !important;
                visibility: hidden !important;
                pointer-events: none !important;
                z-index: -9999 !important;
            }
        `;
        document.head.appendChild(style);
        
        // 9. Redirect Interceptor
        setInterval(() => {
            const url = window.location.href;
            if (url.includes('fb.me') || url.includes('upsell_id') || url.includes('sticky_banner')) {
                window.location.replace('https://www.facebook.com/');
            }
        }, 500);
        """
        self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {'source': stealth_script})
        
        # 10. Aggressive Network-Level Blocking via CDP
        try:
            self.driver.execute_cdp_cmd('Network.setBlockedURLs', {
                'urls': [
                    '*fb.me/*',
                    '*upsell_id*',
                    '*bloks_ios_sticky_banner_upsell*',
                    '*sticky_banner*'
                ]
            })
            self.driver.execute_cdp_cmd('Network.enable', {})
        except: pass

    def human_sleep(self, min_s=1.0, max_s=2.5):
        """Variable delay to simulate human focus."""
        time.sleep(random.uniform(min_s, max_s))

    def human_click(self, element, use_js=False):
        """Simulate human click with random offset and prior movement."""
        if not element: return
        try:
            # 1. Ensure in view
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center', inline: 'nearest'});", element)
            time.sleep(random.uniform(0.6, 1.2))
            
            if use_js:
                self.driver.execute_script("arguments[0].click();", element)
                return

            # 2. Actions-based movement and click
            actions = ActionChains(self.driver)
            size = element.size
            w, h = size.get('width', 10), size.get('height', 10)
            
            # Random offset from center (within 30% of element radius)
            off_x = random.randint(-int(w*0.2), int(w*0.2))
            off_y = random.randint(-int(h*0.2), int(h*0.2))
            
            actions.move_to_element_with_offset(element, off_x, off_y)
            actions.pause(random.uniform(0.2, 0.4))
            actions.click()
            actions.perform()
        except:
            try: self.driver.execute_script("arguments[0].click();", element)
            except: pass

    def human_type(self, element, text):
        """Simulate human typing with varied rhythm and occasional typo correction."""
        if not element: return
        try:
            # Click to focus
            self.human_click(element)
            element.clear()
            self.human_sleep(0.4, 0.8)
            
            text_str = str(text)
            for char in text_str:
                # 2% chance of a typo
                if random.random() < 0.02:
                    typo = random.choice("abcdefghijklmnopqrstuvwxyz")
                    element.send_keys(typo)
                    time.sleep(random.uniform(0.3, 0.6))
                    element.send_keys(Keys.BACKSPACE)
                    time.sleep(random.uniform(0.4, 0.7))
                
                element.send_keys(char)
                
                # Dynamic speed based on character
                delay = random.uniform(0.06, 0.18)
                if char in " .!?,@": delay += random.uniform(0.15, 0.35)
                
                # Occasional 'long wait' (thinking)
                if random.random() < 0.06: delay += random.uniform(0.5, 1.2)
                
                time.sleep(delay)
        except:
            try: element.send_keys(text)
            except: pass

    def is_logged_in(self):
        """Checks if the current session is logged into Facebook and escapes upsell redirects."""
        try:
            if not self.driver: return False
            
            # Escape "App Upsell" or "Sticky Banner" Redirects automatically
            cur_url = self.driver.current_url.lower()
            if "fb.me/www_link_redirect" in cur_url or "upsell_id" in cur_url:
                print(f"[Anti-Gravity] Redirect detected! Escaping back to Facebook...")
                self.driver.get("https://www.facebook.com/")
                time.sleep(2)
                cur_url = self.driver.current_url.lower()
                
            if "checkpoint" in cur_url:
                return False
                
            try:
                cp_xpath = "/html/body/div[1]/div/div/div/div/div/div/div[2]/div/div/div[1]/div/div/div[1]/div/div/div/div/div/div/div/div/div/div/div/div/div[5]/div/div/div[1]/div/span/span"
                if self.driver.find_elements(By.XPATH, cp_xpath):
                    return False
            except: pass

            cookies = self.driver.get_cookies()
            return any(c['name'] == 'c_user' for c in cookies)
        except:
            return False

    def check_and_dismiss_sleep_mode(self, status_callback=None):
        """Checks for the Facebook 'You're in sleep mode' popup and clicks OK to dismiss it."""
        if not self.driver:
            return False
        try:
            body_element = self.driver.find_elements(By.TAG_NAME, "body")
            if not body_element:
                return False
            page_text = body_element[0].text.lower()
            
            # Identify sleep mode popups in English or Khmer
            if "sleep mode" in page_text or "notifications will be muted" in page_text or "close facebook" in page_text or "time to close facebook" in page_text:
                if status_callback:
                    status_callback("💤 Sleep mode popup detected! Dismissing...")
                else:
                    print("[Anti-Gravity] Sleep mode popup detected! Dismissing...")
                
                # OK button XPaths (flexible for different locales)
                ok_xpaths = [
                    "//div[@role='button' and (text()='OK' or .//span[text()='OK'])]",
                    "//button[text()='OK']",
                    "//span[text()='OK']/ancestor::div[@role='button']",
                    "//div[@role='button' and contains(., 'OK')]",
                    "//button[contains(., 'OK')]",
                    "//span[contains(text(), 'OK')]/ancestor::div[@role='button']",
                    "//div[@role='button' and (text()='យល់ព្រម' or .//span[text()='យល់ព្រម'])]",
                    "//button[text()='យល់ព្រម']"
                ]
                
                for xpath in ok_xpaths:
                    try:
                        elements = self.driver.find_elements(By.XPATH, xpath)
                        for el in elements:
                            if el.is_displayed():
                                self.human_click(el)
                                if status_callback:
                                    status_callback("✅ Sleep mode popup dismissed.")
                                else:
                                    print("[Anti-Gravity] Sleep mode popup dismissed.")
                                self.human_sleep(2.0, 4.0)
                                return True
                    except:
                        pass
                
                # Fallback: find any button containing "OK"
                try:
                    all_buttons = self.driver.find_elements(By.XPATH, "//div[@role='button'] | //button")
                    for btn in all_buttons:
                        if btn.is_displayed():
                            btn_text = btn.text.strip()
                            if btn_text == "OK" or btn_text == "យល់ព្រម":
                                self.human_click(btn)
                                if status_callback:
                                    status_callback("✅ Sleep mode popup dismissed (Fallback).")
                                self.human_sleep(2.0, 4.0)
                                return True
                except:
                    pass
        except Exception as e:
            print(f"[Anti-Gravity] Error in check_and_dismiss_sleep_mode: {e}")
        return False

    def auto_login(self, uid, password, twofa_secret=None, status_callback=None):
        if not self.driver:
            return
            
        def update_status(msg):
            print(f"[{uid}] {msg}")
            if status_callback:
                status_callback(msg)

        def check_captcha_or_checkpoint():
            if not self.driver:
                return None
            try:
                # Check for Captcha/Characters
                page_text = self.driver.find_element(By.TAG_NAME, "body").text.lower()
                if "enter the characters you see" in page_text or "we just need to make sure there's a real human" in page_text or "enter characters" in page_text:
                    update_status("Chapracters dynamic function")
                    return {"error": "Chapracters dynamic function"}
            except:
                pass
            
            # Check for standard checkpoint
            try:
                if "checkpoint" in self.driver.current_url.lower():
                    update_status("Check Point")
                    return {"error": "Check Point"}
            except:
                pass
                
            try:
                cp_xpath = "/html/body/div[1]/div/div/div/div/div/div/div[2]/div/div/div[1]/div/div/div[1]/div/div/div/div/div/div/div/div/div/div/div/div/div[5]/div/div/div[1]/div/span/span"
                if self.driver.find_elements(By.XPATH, cp_xpath):
                    update_status("Check Point")
                    return {"error": "Check Point"}
            except:
                pass
                
            try:
                page_text = self.driver.find_element(By.TAG_NAME, "body").text.lower()
                cp_keywords = ["checkpoint", "unusual activity", "account locked", "help us confirm it's you", "suspended your account", "confirm your identity"]
                if any(k in page_text for k in cp_keywords):
                    update_status("Check Point")
                    return {"error": "Check Point"}
            except:
                pass
                
            return None

        if self.is_logged_in():
            update_status("Already logged in ✅")
            return self.get_profile_data(status_callback)

        try:
            # Step 1: Initial Connection & Page Loading Check
            update_status("📡 Connecting to Facebook...")
            try:
                self.driver.get("https://www.facebook.com/login")
                WebDriverWait(self.driver, 20).until(lambda d: d.execute_script('return document.readyState') == 'complete')
            except Exception as e:
                update_status(f"❌ Connection Error (Check Proxy)")
                return None

            # Immediate checkpoint/captcha check
            res = check_captcha_or_checkpoint()
            if res:
                return res

            wait = WebDriverWait(self.driver, 20)
            
            # Helper for Dynamic Selectors (mount_ and root_)
            def wait_for_dynamic_mount(path_suffix, timeout=10):
                prefixes = ["mount_0_0_", "root_0_0_", "mount_", "root_"]
                for pref in prefixes:
                    try: 
                        xp = f"//*[contains(@id, '{pref}')]{path_suffix}"
                        el = WebDriverWait(self.driver, 2).until(EC.element_to_be_clickable((By.XPATH, xp)))
                        if el: return el
                    except: continue
                try: return self.driver.find_element(By.XPATH, f"//*[starts-with(@id, 'mount_') or starts-with(@id, 'root_') or @role='main']{path_suffix}")
                except: return None

            # Handle Cookie Consent / Privacy Banners that block login
            try:
                consent_labels = ["Accept All", "Allow All", "យល់ព្រម", "Accept", "Allow"]
                for lbl in consent_labels:
                    btns = self.driver.find_elements(By.XPATH, f"//button[contains(., '{lbl}')] | //div[@role='button' and contains(., '{lbl}')]")
                    for b in btns:
                        if b.is_displayed():
                            self.human_click(b)
                            self.human_sleep(1, 2)
            except: pass

            # ===== SMART FIELD FINDER =====
            def find_field(field_type="uid"):
                """Multi-strategy field detection for maximum reliability."""
                if field_type == "uid":
                    standard_ids = ["email", "m_login_email", "login_email"]
                    for sid in standard_ids:
                        try:
                            el = self.driver.find_element(By.ID, sid)
                            if el.is_displayed(): return el
                        except: pass
                    
                    user_xpaths = [
                        '//*[@id="login_form"]//input[@name="email"]',
                        '//*[@id="login_form"]//input[@type="text"]',
                        '//input[@data-testid="royal_email"]',
                    ]
                    for xp in user_xpaths:
                        try:
                            el = self.driver.find_element(By.XPATH, xp)
                            if el.is_displayed(): return el
                        except: pass
                else:  # password
                    standard_ids = ["pass", "m_login_password", "login_password"]
                    for sid in standard_ids:
                        try:
                            el = self.driver.find_element(By.ID, sid)
                            if el.is_displayed(): return el
                        except: pass
                    
                    pass_xpaths = [
                        '//*[@id="login_form"]//input[@name="pass"]',
                        '//*[@id="login_form"]//input[@type="password"]',
                        '//input[@data-testid="royal_pass"]',
                    ]
                    for xp in pass_xpaths:
                        try:
                            el = self.driver.find_element(By.XPATH, xp)
                            if el.is_displayed(): return el
                        except: pass
                return None

            # ===== LOGIN EXECUTION =====
            update_status("🔍 Locating credentials fields...")
            uid_field = find_field("uid")
            if uid_field:
                self.human_type(uid_field, uid)
                self.human_sleep(1.0, 2.0)
            
            pass_field = find_field("pass")
            if not pass_field:
                # Handle multi-step login
                try:
                    next_btn = self.driver.find_element(By.XPATH, "//button[contains(., 'Next')] | //button[contains(., 'Continue')]")
                    self.human_click(next_btn)
                    self.human_sleep(3, 5)
                    pass_field = find_field("pass")
                except: pass

            if pass_field:
                self.human_type(pass_field, password)
                self.human_sleep(1.2, 2.5)
                
                # Click Login
                login_clicked = False
                
                # Priority: User-provided new UI path
                path_new_login = '/div/div/div[1]/div/div/div/div[4]/div/div/div/div/div/div/div/div/div[2]/div[3]/div[3]/div/div/div'
                el_new = wait_for_dynamic_mount(path_new_login, timeout=3)
                if el_new:
                    update_status("🎯 Interactive Login Found...")
                    self.human_click(el_new)
                    login_clicked = True
                
                if not login_clicked:
                    login_selectors = [
                        (By.NAME, "login"), (By.ID, "loginbutton"),
                        (By.XPATH, "//button[@type='submit']"),
                        (By.XPATH, "//button[contains(., 'Log In')]"),
                        (By.XPATH, "//button[contains(., 'ចូលប្រើ')]"),
                    ]
                    for method, selector in login_selectors:
                        try:
                            btn = self.driver.find_element(method, selector)
                            if btn.is_displayed():
                                self.human_click(btn)
                                login_clicked = True
                                break
                        except: continue
                
                if not login_clicked:
                    pass_field.send_keys(Keys.ENTER)
            else:
                update_status("❌ Could not proceed to password")
                res = check_captcha_or_checkpoint()
                if res:
                    return res
                return None

            # Step 4: Wait for initial processing & Redirects
            update_status("⏳ Processing login...")
            self.human_sleep(7, 12)
            
            # Step 4.1: Detect Third-Party / Google Verify Block
            if "auth_platform/login_with_third_party" in self.driver.current_url.lower():
                update_status("Dead")
                return {"error": "Dead"}
                
            try:
                # Check for specific Google Error element (relaxing the dynamic mount ID)
                google_err_xpath = "//*[starts-with(@id, 'mount_0_0_')]/div/div[1]/div/div[3]/div/div/div[1]/div[1]/div[2]/div/div/div/div/div[4]/div/div/div/div/div[1]/div/span/span"
                if self.driver.find_elements(By.XPATH, google_err_xpath):
                    update_status("Error Login Google")
                    return {"error": "Error Login Google"}
            except: pass
            
            # Step 4.2: Detect common login errors (Wrong password, etc)
            try:
                page_text = self.driver.find_element(By.TAG_NAME, "body").text.lower()
                error_keywords = ["incorrect", "wrong", "invalid", "មិនត្រឹមត្រូវ", "ខុស"]
                if any(k in page_text for k in error_keywords) and not self.is_logged_in():
                    if "checkpoint" not in self.driver.current_url.lower():
                        is_cp = False
                        try:
                            cp_xpath = "/html/body/div[1]/div/div/div/div/div/div/div[2]/div/div/div[1]/div/div/div[1]/div/div/div/div/div/div/div/div/div/div/div/div/div[5]/div/div/div[1]/div/span/span"
                            if self.driver.find_elements(By.XPATH, cp_xpath):
                                is_cp = True
                        except: pass
                        
                        if not is_cp:
                            cp_keywords = ["checkpoint", "unusual activity", "account locked", "help us confirm it's you", "suspended your account", "confirm your identity"]
                            if any(k in page_text for k in cp_keywords):
                                is_cp = True
                                
                        if not is_cp:
                            update_status("❌ Incorrect Credentials Detected")
                            return None
            except: pass

            # Step 4.5: Handle Checkpoints & 2FA
            res = check_captcha_or_checkpoint()
            if res and res.get("error") == "Chapracters dynamic function":
                return res

            checkpoint_urls = ["checkpoint", "login/checkpoint", "two_step_verification"]
            if any(x in self.driver.current_url.lower() for x in checkpoint_urls):
                update_status("🔐 2FA Checkpoint Detected...")
                wait = WebDriverWait(self.driver, 15)
                
                # --- Multi-Strategy 100% Verification Sequence ---
                try:
                    # Logic block to bypass "This was me" or "Continue" screens
                    bypass_labels = ["Continue", "បន្ត", "This was me", "គឺជាខ្ញុំ", "Yes", "បាទ/ចាស", "OK", "យល់ព្រម"]
                    for _ in range(2):
                        for lbl in bypass_labels:
                            try:
                                btn = self.driver.find_element(By.XPATH, f"//button[contains(., '{lbl}')] | //a[contains(., '{lbl}')] | //div[@role='button' and contains(., '{lbl}')]")
                                if btn.is_displayed():
                                    self.human_click(btn)
                                    self.human_sleep(3, 5)
                            except: pass

                    # Execution of User-Provided High-Accuracy Sequence
                    path1 = '/div/div[1]/div/div[2]/div/div/div[1]/div[1]/div/div/div[1]/div/div/div/div[1]/div/div/div/div[4]/div/div'
                    el1 = wait_for_dynamic_mount(path1)
                    if el1: 
                        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", el1)
                        try: self.human_click(el1)
                        except: pass
                        self.human_sleep(3, 5)

                    path2 = '/div/div[1]/div/div[3]/div/div/div[1]/div/div[2]/div/div/div/div/div/div/div[4]/div[2]/div[1]/div/div/div[2]/div/div/div/div/label[2]/div[1]'
                    el2 = wait_for_dynamic_mount(path2)
                    if el2: 
                        self.human_click(el2)
                        update_status("Checkpoint Method Selected ✅")
                        self.human_sleep(3, 5)

                    path3 = '/div/div[1]/div/div[2]/div/div/div[1]/div[1]/div/div/div[1]/div/div/div/div[1]/div/div/div[3]/div/form/div/div/div/div'
                    el3 = wait_for_dynamic_mount(path3)
                    if el3: 
                        self.human_click(el3)
                        update_status("Proceeding to OTP Entry...")
                        self.human_sleep(5, 8)
                        
                    # NEW: User provided specific root-based path for New UI Login Flow
                    path_new_login = '/div/div/div[1]/div/div/div/div[4]/div/div/div/div/div/div/div/div/div[2]/div[3]/div[3]/div/div/div'
                    el_new = wait_for_dynamic_mount(path_new_login, timeout=5)
                    if el_new:
                        update_status("🎯 Interactive Element Found (Bypass Search)...")
                        self.human_click(el_new)
                        self.human_sleep(4, 7)

                except Exception as seq_err:
                    update_status(f"⚠️ Sequence Notice: Logic bypass used")
                
                self.human_sleep(3, 5)

                if twofa_secret:
                    try:
                        # 1. Generate TOTP Code
                        # Clean and pad the base32 secret
                        import re
                        clean_secret = twofa_secret.replace(" ", "").replace("-", "").upper()
                        clean_secret = re.sub(r'[^A-Z2-7]', '', clean_secret)
                        padding_len = (8 - len(clean_secret) % 8) % 8
                        clean_secret += "=" * padding_len
                        
                        totp = pyotp.TOTP(clean_secret)
                        otp_code = totp.now()
                        update_status(f"🔑 Generated OTP: {otp_code}")
                        
                        # 2. Find OTP Input Field with explicit wait and click
                        otp_field = None
                        
                        # First try specific user-provided XPaths with a wait
                        user_xpaths = [
                            '//*[@id="_r_3_"]',
                            '/html/body/div[2]/div/div[1]/div/div[2]/div/div/div[1]/div[1]/div/div/div[1]/div/div/div/div[1]/div/div/div[3]/div/form/div/div/div/div/div[1]/input'
                        ]
                        
                        update_status("🔍 Waiting for OTP field...")
                        for xp in user_xpaths:
                            try:
                                el = WebDriverWait(self.driver, 10).until(
                                    EC.element_to_be_clickable((By.XPATH, xp))
                                )
                                if el:
                                    otp_field = el
                                    update_status("🎯 OTP Field Found!")
                                    # Explicitly click the field as requested
                                    self.human_click(otp_field)
                                    self.human_sleep(0.5, 1.0)
                                    break
                            except: continue
                            
                        # Fallback to standard selectors if user XPaths not found
                        if not otp_field:
                            otp_selectors = [
                                (By.ID, "approvals_code"),
                                (By.NAME, "approvals_code"),
                                (By.CSS_SELECTOR, "input[autocomplete='one-time-code']"),
                                (By.XPATH, "//input[@type='text' or @type='tel' or @type='number']"),
                                (By.XPATH, "//input[@maxlength='6' or @maxlength='8']"),
                                (By.XPATH, "//input[contains(@name, 'approvals_code')]"),
                                (By.XPATH, "//input[contains(@placeholder, 'code') or contains(@placeholder, 'កូដ')]")
                            ]
                            
                            for method, selector in otp_selectors:
                                try:
                                    # Finding all matching elements and picking the first displayed one
                                    els = self.driver.find_elements(method, selector)
                                    for el in els:
                                        if el.is_displayed():
                                            otp_field = el
                                            self.human_click(otp_field)
                                            break
                                    if otp_field:
                                        break
                                except: continue
                            
                        if otp_field:
                            update_status("✏️ Entering OTP...")
                            self.human_type(otp_field, otp_code)
                            self.human_sleep(1.0, 2.0)
                            
                            # 3. Submit OTP
                            submit_btn = None
                            submit_selectors = [
                                (By.ID, "checkpointSubmitButton"),
                                (By.NAME, "submit[Continue]"),
                                (By.XPATH, "//button[@type='submit']"),
                                (By.XPATH, "//button[contains(., 'Continue')]"),
                                (By.XPATH, "//button[contains(., 'Submit')]"),
                                (By.XPATH, "//button[contains(., 'បន្ត')]"),
                                (By.XPATH, "//button[contains(., 'បញ្ជូន')]"),
                                (By.XPATH, "//div[@role='button' and contains(., 'Continue')]")
                            ]
                            
                            for method, selector in submit_selectors:
                                try:
                                    btn = self.driver.find_element(method, selector)
                                    if btn.is_displayed():
                                        submit_btn = btn
                                        break
                                except: continue
                                
                            if submit_btn:
                                self.human_click(submit_btn)
                                update_status("✅ OTP Submitted")
                                self.human_sleep(5, 8)
                                
                                # Handle "Save Browser" prompt (often appears after 2FA)
                                save_browser_labels = ["Save Browser", "មេម៉ូរីកម្មវិធីរុករក", "Save", "Continue", "បន្ត"]
                                for i in range(2): # Might have multiple steps like "Trust this browser"
                                    for lbl in save_browser_labels:
                                        try:
                                            btn = self.driver.find_element(By.XPATH, f"//button[contains(., '{lbl}')] | //input[@type='submit' and contains(@value, '{lbl}')]")
                                            if btn.is_displayed():
                                                self.human_click(btn)
                                                self.human_sleep(3, 5)
                                                break
                                        except: pass
                            else:
                                update_status("❌ OTP Submit button not found")
                        else:
                            update_status("❌ OTP Input field not found")
                    except Exception as te:
                        update_status(f"⚠️ 2FA Error: {str(te)[:30]}")
                else:
                    update_status("⚠️ 2FA Required but no secret provided!")
            
            self.human_sleep(3, 5)
            
            # Dismiss sleep mode popup if present
            self.check_and_dismiss_sleep_mode(status_callback)
            
            # Step 5: Handle post-login prompts
            prompt_labels = [
                "Not Now", "Not now", "OK", "Continue", 
                "Save Information", "Skip",
                "យល់ព្រម", "មិនមែនឥឡូវនេះ", "រំលង"
            ]
            for attempt in range(3):
                for lbl in prompt_labels:
                    try:
                        xpaths = [
                            f"//a[contains(text(), '{lbl}')]",
                            f"//button[contains(text(), '{lbl}')]",
                            f"//span[contains(text(), '{lbl}')]/ancestor::a",
                            f"//span[contains(text(), '{lbl}')]/ancestor::div[@role='button']",
                            f"//*[@aria-label='{lbl}']",
                        ]
                        for xp in xpaths:
                            try:
                                p_btn = self.driver.find_element(By.XPATH, xp)
                                if p_btn.is_displayed():
                                    self.human_click(p_btn)
                                    self.human_sleep(2, 4)
                                    break
                            except: pass
                    except: pass
            
            # Dismiss sleep mode popup again if it dynamically showed up
            self.check_and_dismiss_sleep_mode(status_callback)
            
            # Step 6: Verify Login Success
            if self.is_logged_in():
                update_status("✅ Login Successful!")
                return self.get_profile_data(status_callback)
            else:
                update_status("⚠️ Login may have failed - checking...")
                self.human_sleep(3, 5)
                if self.is_logged_in():
                    update_status("✅ Login Confirmed!")
                    return self.get_profile_data(status_callback)
                else:
                    res = check_captcha_or_checkpoint()
                    if res:
                        return res
                    
                    # Final attempt to check for specific landing page elements
                    try:
                        # Use much stricter selectors (Stories, Messenger icon, Create Post)
                        home_selectors = ["div[aria-label='Stories']", "svg[aria-label='Messenger']", "a[aria-label='Home']"]
                        if any(self.driver.find_elements(By.CSS_SELECTOR, s) for s in home_selectors):
                            update_status("✅ Login Confirmed (Visual)!")
                            return self.get_profile_data(status_callback)
                    except: pass

                    update_status("❌ Login Failed - Check credentials")
                    return None

        except Exception as e:
            res = check_captcha_or_checkpoint()
            if res:
                return res
            
            update_status(f"Login Error: {str(e)[:50]}")
            return None


    def get_profile_data(self, status_callback=None):
        if not self.driver: return None
        
        def update_status(msg):
            if status_callback: status_callback(msg)

        try:
            update_status("🔍 Scanning Profile Data...")
            self.human_sleep(3.0, 5.0)
            
            # Navigate to /me which redirects to the actual profile URL
            self.driver.get("https://www.facebook.com/me")
            self.human_sleep(6, 10) # Sufficient time for all layers to load
            
            # Dismiss sleep mode popup if it appears on profile load
            self.check_and_dismiss_sleep_mode(status_callback)
            
            profile_info = {}
            current_url = self.driver.current_url
            
            # 1. Extract Name (High-Accuracy Strategy)
            name = None
            # Strategy A: JavaScript forced extraction from H1
            try:
                name = self.driver.execute_script("""
                    let h1s = document.querySelectorAll('h1');
                    for(let h of h1s) {
                        let text = h.innerText.trim();
                        if(text && text.length > 1 && text.length < 50 && !text.includes('Facebook')) {
                            return text;
                        }
                    }
                    return null;
                """)
            except: pass

            # Strategy B: Fallback to aria-label or title
            if not name:
                try:
                    name = self.driver.execute_script("return document.title;").split('|')[0].strip()
                    if "Facebook" in name or not name: name = None
                except: pass

            profile_info["name"] = name if name else "Unknown Profile"

            # 2. Extract UID and Vanity Username
            # Strategy A: URL Parsing
            if "profile.php?id=" in current_url:
                uid = current_url.split("id=")[1].split("&")[0]
                profile_info["uid"] = uid
                profile_info["username"] = uid # Same for numeric IDs
            else:
                # Vanity URL extraction (e.g., facebook.com/john.doe)
                vanity = current_url.split("facebook.com/")[1].split("?")[0].split("/")[0]
                profile_info["username"] = vanity
                
                # Numeric ID extraction from source
                script = """
                    let source = document.documentElement.innerHTML;
                    let match = source.match(/"userID":"(\\\\d+)"/) || source.match(/"uid":(\\\\d+)/);
                    return match ? match[1] : null;
                """
                uid = self.driver.execute_script(script)
                if uid: profile_info["uid"] = uid

            # 3. Extract Friend Count
            try:
                f_count = self.driver.execute_script("""
                    let spans = document.querySelectorAll('span, a');
                    for(let s of spans) {
                        let t = s.innerText;
                        if(t && (t.includes(' friends') || t.includes(' មិត្តភក្តិ'))) {
                            let match = t.match(/(\\d+)/);
                            if(match) return match[1];
                        }
                    }
                    return "0";
                """)
                profile_info["friends"] = f_count if f_count else "0"
            except: 
                profile_info["friends"] = "0"

            # 4. Extract Cookies
            try:
                cookies = self.driver.get_cookies()
                profile_info["cookies"] = "; ".join([f"{c['name']}={c['value']}" for c in cookies])
            except: pass

            update_status(f"✅ Profile Sync: {profile_info.get('name')} | ID: {profile_info.get('uid')}")
            return profile_info
        except Exception as e:
            update_status(f"⚠️ Extraction Error: {str(e)[:40]}")
            return None

    def launch_chrome_store(self, profile_path=None):
        options = Options()
        options.add_argument('--app=https://chrome.google.com/webstore/devconsole')
        options.add_argument('window-size=1200,300')
        
        if profile_path:
            options.add_argument(f'user-data-dir={profile_path}')
            
        if self.proxy:
            options.add_argument(f'--proxy-server={self.proxy}')
            
        import subprocess
        service = Service(ChromeDriverManager().install())
        if os.name == 'nt':
            service.creation_flags = subprocess.CREATE_NO_WINDOW
        self.driver = webdriver.Chrome(service=service, options=options)
        return self.driver

    def invite_friends(self, status_callback=None):
        def update_status(m):
            if status_callback: status_callback(m)

        try:
            self.check_and_dismiss_sleep_mode(status_callback)
            update_status("⏳ Waiting for page elements to load...")
            
            # Key selectors to check if the page is loaded
            xp_step1 = '//*[starts-with(@id, "mount_0_0_")]/div/div[1]/div/div[3]/div/div/div[1]/div[1]/div/div/div[3]/div/div/div/div[2]/div/div'
            fallbacks = ["//span[contains(text(), 'Invite friends')]", "//span[contains(text(), 'អញ្ជើញមិត្តភក្តិ')]", "//div[@aria-label='More']", "//div[@aria-label='Actions for this Page']"]
            
            start_t = time.time()
            page_ready = False
            while time.time() - start_t < 25: # Wait up to 25 seconds
                try:
                    el1 = self.driver.find_elements(By.XPATH, xp_step1)
                    if el1 and el1[0].is_displayed():
                        page_ready = True
                        break
                except:
                    pass
                try:
                    fb_found = False
                    for fb in fallbacks:
                        els = self.driver.find_elements(By.XPATH, fb)
                        if els and any(e.is_displayed() for e in els):
                            fb_found = True
                            break
                    if fb_found:
                        page_ready = True
                        break
                except:
                    pass
                time.sleep(1)
                
            update_status("Starting specialized invite sequence...")
            self.human_sleep(2.0, 3.5)
            
            # Step 1: Entry Point
            xp_step1 = '//*[starts-with(@id, "mount_0_0_")]/div/div[1]/div/div[3]/div/div/div[1]/div[1]/div/div/div[3]/div/div/div/div[2]/div/div'
            try:
                el1 = self.driver.find_element(By.XPATH, xp_step1)
                self.human_click(el1)
                update_status("Entry point clicked.")
                self.human_sleep(3.0, 5.5)
            except: pass

            # Step 2: Invite Friends Trigger
            xp_step2 = '//*[starts-with(@id, "mount_0_0_")]/div/div[1]/div/div[4]/div/div[8]/div[1]/div/div[2]/div/div/div/div/div[1]/div[3]/div[1]/div[1]/div[2]/div/div/div/div[1]/div/span/span'
            invite_btn = None
            try:
                invite_btn = self.driver.find_element(By.XPATH, xp_step2)
                self.human_click(invite_btn)
                update_status("Invite trigger clicked! ✨")
                self.human_sleep(6.0, 9.5)
            except:
                # Fallback to Text
                fallbacks = ["//span[contains(text(), 'Invite friends')]", "//span[contains(text(), 'អញ្ជើញមិត្តភក្តិ')]"]
                for fb in fallbacks:
                    try:
                        btn = self.driver.find_element(By.XPATH, fb)
                        self.human_click(btn)
                        invite_btn = btn; break
                    except: pass

            if not invite_btn:
                update_status("Invite button not found. Sequence ended.")
                return

            # Step 4: Execute Friend Selection (Dynamic Case: Specific Count OR Select All)
            max_to_invite = self.settings.get("invite_count", 25)
            update_status(f"Selection Mode: {'Select All' if max_to_invite >= 500 else f'Count {max_to_invite}'}")
            
            friends_selected = 0
            
            # --- ATTEMPT 1: Try 'Select All' button (Robust Detection) ---
            if max_to_invite >= 500:
                update_status("Detecting 'Select All' control...")
                found_all_via_btn = False
                
                # 1. Primary: User-provided specific High-Accuracy XPath
                xp_user_all = '//*[@id="scrollview"]/div/div[2]/div/div/div/div/div[1]/div[3]/div[1]/div[1]/div[2]/div/div/div/div[1]/div/span/span'
                try:
                    all_btn = self.driver.find_element(By.XPATH, xp_user_all)
                    self.human_click(all_btn)
                    update_status("Selected All ✅")
                    friends_selected = "All"
                    found_all_via_btn = True
                    self.human_sleep(2.0, 4.0)
                except: pass

                # 2. Secondary: Broad Search for any element that might be the "Select All" control
                if not found_all_via_btn:
                    all_labels = ["Select All", "Select all", "ជ្រើសរើសទាំងអស់", "Select all friends", "All friends"]
                    all_candidates = self.driver.find_elements(By.XPATH, "//div[@role='checkbox'] | //div[@role='button'] | //span | //i | //input")
                    
                    for candidate in all_candidates:
                        try:
                            c_text = str(candidate.text).lower()
                            c_aria = str(candidate.get_attribute("aria-label")).lower()
                            c_title = str(candidate.get_attribute("title")).lower()
                            
                            if any(lbl.lower() in c_text or lbl.lower() in c_aria or lbl.lower() in c_title for lbl in all_labels):
                                # Ensure it's not already checked
                                is_checked = "true" in str(candidate.get_attribute("aria-checked")).lower() or \
                                             candidate.get_attribute("checked") is not None
                                
                                if not is_checked:
                                    self.human_click(candidate)
                                    update_status("Selected All ✅")
                                    friends_selected = "All"
                                    found_all_via_btn = True
                                    self.human_sleep(2.0, 4.0)
                                    break
                        except: continue

                # 3. Final Fallback: Absolute Text Search
                if not found_all_via_btn:
                    all_labels = ["Select All", "Select all", "ជ្រើសរើសទាំងអស់", "Select all friends"]
                    for lbl in all_labels:
                        try:
                            fb_all_btn = self.driver.find_element(By.XPATH, f"//*[contains(text(), '{lbl}')]")
                            self.human_click(fb_all_btn)
                            update_status(f"Selected All via '{lbl}'.")
                            friends_selected = "All"
                            break
                        except: continue

            # --- ATTEMPT 2: Manual Loop (For specific numbers) ---
            if friends_selected != "All":
                scroll_attempts = 0
                max_scrolls = 40 # Increased limit for scrolling
                processed_elements = set() # Track by internal ID to avoid re-processing
                
                while friends_selected < max_to_invite and scroll_attempts < max_scrolls:
                    # Target only checkboxes inside the dialog's list area
                    checks = self.driver.find_elements(By.XPATH, "//div[@role='dialog']//div[@role='checkbox']")
                    found_new_in_this_loop = False
                    
                    for c in checks:
                        if friends_selected >= max_to_invite: break
                        
                        try:
                            # Use internal element ID to track processed items
                            element_id = c.id
                            if element_id in processed_elements:
                                continue
                            
                            processed_elements.add(element_id)
                            
                            # Verify if it's a "Select All" checkbox - we MUST skip it here
                            label_attr = (c.get_attribute("aria-label") or "").lower()
                            if any(x in label_attr for x in ["all", "ជ្រើសរើសទាំងអស់", "select all"]):
                                continue

                            # Check if the friend is already selected
                            is_checked = str(c.get_attribute("aria-checked")).lower() == "true"
                            
                            if not is_checked:
                                self.human_click(c)
                                friends_selected += 1
                                found_new_in_this_loop = True
                                update_status(f"Selected: {friends_selected}/{max_to_invite}")
                                self.human_sleep(0.5, 1.2)
                        except Exception as e:
                            continue

                    if friends_selected >= max_to_invite: break
                    
                    # --- Improved Scrolling Logic ---
                    update_status(f"Loaded {friends_selected}. Scrolling more...")
                    try:
                        dialog_body = self.driver.find_element(By.XPATH, "//div[@role='dialog']//div[contains(@style, 'overflow-y: auto')]")
                        # Scroll down with variable amount
                        scroll_val = random.randint(800, 1500)
                        self.driver.execute_script(f"arguments[0].scrollTop += {scroll_val};", dialog_body)
                    except:
                        self.driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.PAGE_DOWN)
                        self.human_sleep(0.4, 0.8)
                        self.driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.PAGE_DOWN)
                    
                    self.human_sleep(2.5, 4.5) # Wait for network/UI
                    scroll_attempts += 1
                    
                    if not found_new_in_this_loop and scroll_attempts > 2:
                        update_status("Searching deeper...")
                        self.driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.END)
                        self.human_sleep(2, 4)
                        
                    if not found_new_in_this_loop and scroll_attempts > 8:
                        update_status(f"List ended at {friends_selected}.")
                        break

            # Phase 4: Sending Invites (Using User-Specific XPath for 100% Accuracy)
            update_status(f"Finalizing... Total selected: {friends_selected}")
            time.sleep(2.0)
            
            # 1. Main Send Button
            xp_send = '//*[starts-with(@id, "mount_0_0_")]/div/div[1]/div/div[4]/div/div[9]/div[1]/div/div[2]/div/div/div/div/div[1]/div[3]/div[1]/div[1]/div[2]/div/div'
            found_send = False
            try:
                send_btn = self.driver.find_element(By.XPATH, xp_send)
                update_status("Waiting 30s before Send...")
                self.human_sleep(28, 35) 
                self.human_click(send_btn)
                update_status(f"Done! {friends_selected} Sent ✅")
                found_send = True
                self.human_sleep(3, 5)
            except:
                # Fallback
                send_labels = ["Send Invites", "ផ្ញើការអញ្ជើញ", "Send", "អញ្ជើញ"]
                for lbl in send_labels:
                    try:
                        send_btn = self.driver.find_element(By.XPATH, f"//div[@role='button']//span[contains(text(), '{lbl}')]")
                        self.human_click(send_btn)
                        update_status(f"Done! {friends_selected} Sent ✅")
                        found_send = True
                        self.human_sleep(3, 5)
                        break
                    except: continue
            
            if not found_send:
                update_status("Enter key backup...")
                self.driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ENTER)
                self.human_sleep(3, 5)

            # Phase 5: Closure
            update_status("Finishing...")
            try:
                xp_final = '//*[starts-with(@id, "mount_0_0_")]/div/div[1]/div/div[4]/div/div[9]/div[1]/div/div[2]/div/div/div/div/div[1]/div[3]/div[2]/div[2]/div/div'
                final_btn = self.driver.find_element(By.XPATH, xp_final)
                update_status("Waiting 30s before Close...")
                self.human_sleep(28, 35)
                self.human_click(final_btn)
                update_status("Process completed 100% ✅")
                self.human_sleep(2, 4)
            except:
                update_status("Final step done ✅")
                
        except Exception as e:
            update_status(f"Invite Error: {str(e)[:40]}")

    def add_friend(self, count=5, status_callback=None):
        def update_status(m):
            if status_callback: status_callback(m)

        try:
            self.check_and_dismiss_sleep_mode(status_callback)
            update_status(f"🚀 Starting Add Friend (Target: {count})...")
            
            # Navigate to friend suggestions page
            current_url = self.driver.current_url.lower()
            if "/friends/suggestions" not in current_url and "/friends" not in current_url:
                self.driver.get("https://www.facebook.com/friends/suggestions")
                self.human_sleep(5, 8)
                self.check_and_dismiss_sleep_mode(status_callback)
            elif "/friends/suggestions" not in current_url:
                self.driver.get("https://www.facebook.com/friends/suggestions")
                self.human_sleep(3, 5)
                self.check_and_dismiss_sleep_mode(status_callback)
            else:
                self.human_sleep(2, 3)
                self.check_and_dismiss_sleep_mode(status_callback)

            added = 0
            scroll_attempts = 0
            max_scroll_attempts = 30
            clicked_elements = set()  # Track clicked buttons by position/text to avoid duplicates
            consecutive_failures = 0

            while added < count and scroll_attempts < max_scroll_attempts:
                # ===== FIND ADD FRIEND BUTTONS (Multi-Strategy) =====
                buttons = []
                
                # Strategy 1: Span text match (Most Common)
                add_xpaths = [
                    "//div[@role='button']//span[text()='Add friend']",
                    "//div[@role='button']//span[text()='Add Friend']",
                    "//div[@role='button']//span[contains(text(),'Add friend')]",
                    "//div[@role='button']//span[contains(text(),'Add Friend')]",
                    "//div[@role='button']//span[contains(text(),'បន្ថែមជាមិត្ត')]",
                ]
                for xp in add_xpaths:
                    try:
                        found = self.driver.find_elements(By.XPATH, xp)
                        if found:
                            buttons = found
                            break
                    except: pass
                
                # Strategy 2: aria-label match
                if not buttons:
                    aria_xpaths = [
                        "//div[@aria-label='Add Friend']",
                        "//div[@aria-label='Add friend']",
                        "//div[@aria-label='បន្ថែមជាមិត្ត']",
                        "//button[@aria-label='Add Friend']",
                    ]
                    for xp in aria_xpaths:
                        try:
                            found = self.driver.find_elements(By.XPATH, xp)
                            if found:
                                buttons = found
                                break
                        except: pass

                # Strategy 3: JavaScript DOM search
                if not buttons:
                    try:
                        buttons = self.driver.execute_script("""
                            var results = [];
                            var allBtns = document.querySelectorAll('div[role="button"], button');
                            for (var i = 0; i < allBtns.length; i++) {
                                var txt = (allBtns[i].innerText || '').trim().toLowerCase();
                                if (txt === 'add friend' || txt === 'បន្ថែមជាមិត្ត') {
                                    results.push(allBtns[i]);
                                }
                            }
                            return results;
                        """) or []
                    except: pass

                # ===== CLICK UNCLICKED BUTTONS =====
                clicked_this_round = False
                for btn in buttons:
                    if added >= count:
                        break
                    try:
                        # Generate unique key for this button
                        btn_id = btn.id  # Selenium internal element ID
                        if btn_id in clicked_elements:
                            continue
                        
                        # Make sure button is visible and clickable
                        if not btn.is_displayed():
                            continue
                        
                        # Scroll button into view
                        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn)
                        self.human_sleep(0.5, 1.0)
                        
                        # Click the button
                        self.human_click(btn)
                        clicked_elements.add(btn_id)
                        added += 1
                        clicked_this_round = True
                        consecutive_failures = 0
                        update_status(f"✅ Added {added}/{count}")
                        self.human_sleep(3.0, 6.0)
                        
                    except Exception as e:
                        consecutive_failures += 1
                        continue

                # ===== SCROLL FOR MORE =====
                if added < count:
                    if not clicked_this_round:
                        consecutive_failures += 1
                    
                    if consecutive_failures >= 5:
                        update_status(f"⚠️ No more suggestions found. Total: {added}")
                        break
                    
                    # Scroll down to load more suggestions
                    update_status(f"📜 Scrolling for more... ({added}/{count})")
                    try:
                        self.driver.execute_script("window.scrollBy(0, window.innerHeight * 0.8);")
                    except:
                        try:
                            self.driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.PAGE_DOWN)
                        except: pass
                    
                    self.human_sleep(2.5, 4.5)
                    scroll_attempts += 1

            update_status(f"🎉 Add Friend Complete! Total: {added}/{count} ✅")
            
        except Exception as e:
            update_status(f"❌ Add Friend Error: {str(e)[:50]}")

    def confirm_friend(self, count=5, status_callback=None):
        def update_status(m):
            if status_callback: status_callback(m)

        try:
            self.check_and_dismiss_sleep_mode(status_callback)
            update_status(f"🚀 Starting Confirm Friend (Target: {count})...")
            
            # Navigate to friend requests page
            current_url = self.driver.current_url.lower()
            if "/friends/requests" not in current_url:
                self.driver.get("https://www.facebook.com/friends/requests")
                self.human_sleep(5, 8)
                self.check_and_dismiss_sleep_mode(status_callback)
            else:
                self.human_sleep(2, 3)
                self.check_and_dismiss_sleep_mode(status_callback)

            confirmed = 0
            scroll_attempts = 0
            max_scroll_attempts = 20
            clicked_elements = set()
            consecutive_failures = 0

            while confirmed < count and scroll_attempts < max_scroll_attempts:
                # ===== FIND CONFIRM BUTTONS (Multi-Strategy) =====
                buttons = []
                
                # Strategy 1: Exact text match via XPath
                confirm_xpaths = [
                    "//div[@role='button']//span[text()='Confirm']",
                    "//div[@role='button']//span[contains(text(),'Confirm')]",
                    "//div[@role='button']//span[contains(text(),'បញ្ជាក់')]",
                    "//div[@role='button']//span[contains(text(),'យល់ព្រម')]",
                    "//button//span[text()='Confirm']",
                ]
                for xp in confirm_xpaths:
                    try:
                        found = self.driver.find_elements(By.XPATH, xp)
                        if found:
                            buttons = found
                            break
                    except: pass
                
                # Strategy 2: aria-label match
                if not buttons:
                    aria_xpaths = [
                        "//div[@aria-label='Confirm']",
                        "//div[@aria-label='បញ្ជាក់']",
                        "//button[@aria-label='Confirm']",
                    ]
                    for xp in aria_xpaths:
                        try:
                            found = self.driver.find_elements(By.XPATH, xp)
                            if found:
                                buttons = found
                                break
                        except: pass

                # Strategy 3: JavaScript DOM search
                if not buttons:
                    try:
                        buttons = self.driver.execute_script("""
                            var results = [];
                            var allBtns = document.querySelectorAll('div[role="button"], button');
                            for (var i = 0; i < allBtns.length; i++) {
                                var txt = (allBtns[i].innerText || '').trim().toLowerCase();
                                if (txt === 'confirm' || txt === 'បញ្ជាក់' || txt === 'យល់ព្រម') {
                                    results.push(allBtns[i]);
                                }
                            }
                            return results;
                        """) or []
                    except: pass

                # ===== CLICK UNCLICKED BUTTONS =====
                clicked_this_round = False
                for btn in buttons:
                    if confirmed >= count:
                        break
                    try:
                        btn_id = btn.id
                        if btn_id in clicked_elements:
                            continue
                        
                        if not btn.is_displayed():
                            continue
                        
                        # Scroll into view
                        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn)
                        self.human_sleep(0.5, 1.0)
                        
                        # Click confirm
                        self.human_click(btn)
                        clicked_elements.add(btn_id)
                        confirmed += 1
                        clicked_this_round = True
                        consecutive_failures = 0
                        update_status(f"✅ Confirmed {confirmed}/{count}")
                        self.human_sleep(2.5, 5.0)
                        
                    except Exception as e:
                        consecutive_failures += 1
                        continue

                # ===== SCROLL FOR MORE =====
                if confirmed < count:
                    if not clicked_this_round:
                        consecutive_failures += 1
                    
                    if consecutive_failures >= 4:
                        update_status(f"⚠️ No more requests found. Total: {confirmed}")
                        break
                    
                    update_status(f"📜 Scrolling for more... ({confirmed}/{count})")
                    try:
                        self.driver.execute_script("window.scrollBy(0, window.innerHeight * 0.7);")
                    except:
                        try:
                            self.driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.PAGE_DOWN)
                        except: pass
                    
                    self.human_sleep(2.0, 4.0)
                    scroll_attempts += 1

            update_status(f"🎉 Confirm Friend Complete! Total: {confirmed}/{count} ✅")
            
        except Exception as e:
            update_status(f"❌ Confirm Error: {str(e)[:50]}")

    def scroll_feeds(self, minutes=5, random_reactions=False, status_callback=None):
        def update_status(m):
            if status_callback: status_callback(m)

        try:
            self.check_and_dismiss_sleep_mode(status_callback)
            update_status(f"📰 Scrolling Feeds for {minutes} mins...")
            self.driver.get("https://www.facebook.com/")
            self.human_sleep(5, 8)
            self.check_and_dismiss_sleep_mode(status_callback)

            end_time = time.time() + (minutes * 60)
            while time.time() < end_time:
                remaining = int((end_time - time.time()) / 60)
                update_status(f"📰 Scrolling Feeds... {remaining} mins left")
                
                # Scroll down
                try:
                    scroll_val = random.randint(400, 1000)
                    self.driver.execute_script(f"window.scrollBy(0, {scroll_val});")
                except:
                    self.driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.PAGE_DOWN)
                
                self.human_sleep(8, 15)
                
                # Random Reaction (Multi-Strategy)
                if random_reactions and random.random() < 0.4:
                    try:
                        # Find Like button to hover or click
                        like_btns = self.driver.find_elements(By.XPATH, "//div[@role='button']//span[text()='Like' or text()='ចូលចិត្ត']")
                        if like_btns:
                            btn = random.choice(like_btns)
                            
                            if random.random() < 0.5: # 50% chance to do a complex reaction (Love, Haha, etc.)
                                update_status("🎭 Performing Complex Reaction...")
                                actions = ActionChains(self.driver)
                                actions.move_to_element(btn).perform()
                                self.human_sleep(1.5, 2.5) # Wait for reactions to appear
                                
                                # Find visible reactions in the pop-up
                                reactions_xpath = "//div[@role='dialog' or @role='presentation']//div[@role='button' and @aria-label]"
                                rx_options = self.driver.find_elements(By.XPATH, reactions_xpath)
                                if rx_options:
                                    target_rx = random.choice(rx_options)
                                    rx_label = target_rx.get_attribute("aria-label") or "Reaction"
                                    self.human_click(target_rx)
                                    update_status(f"❤️ Reacted: {rx_label}")
                                else:
                                    self.human_click(btn) # Fallback to Like
                                    update_status("👍 Liked post (Fallback)")
                            else:
                                self.human_click(btn)
                                update_status("👍 Liked post")
                    except Exception as e:
                        update_status(f"⚠️ Reaction failed: {str(e)[:20]}")
                    self.human_sleep(2, 5)
            
            update_status("✅ Feeds Completed")
        except Exception as e:
            update_status(f"❌ Feeds Error: {str(e)[:40]}")

    def watch_video(self, minutes=5, random_reactions=False, status_callback=None):
        def update_status(m):
            if status_callback: status_callback(m)

        try:
            self.check_and_dismiss_sleep_mode(status_callback)
            update_status(f"📺 Watch Video for {minutes} mins...")
            self.driver.get("https://www.facebook.com/watch")
            self.human_sleep(5, 8)
            self.check_and_dismiss_sleep_mode(status_callback)

            end_time = time.time() + (minutes * 60)
            while time.time() < end_time:
                remaining = int((end_time - time.time()) / 60)
                update_status(f"📺 Watching... {remaining} mins left")
                
                # Scroll to next video occasionally
                if random.random() < 0.2:
                    try:
                        scroll_val = random.randint(500, 900)
                        self.driver.execute_script(f"window.scrollBy(0, {scroll_val});")
                        self.human_sleep(3, 6)
                    except: pass
                
                if random_reactions and random.random() < 0.3:
                    try:
                        update_status("🎭 Selecting Random Reaction for Video...")
                        like_btns = self.driver.find_elements(By.XPATH, "//div[@role='button']//span[text()='Like' or text()='ចូលចិត្ត']")
                        if like_btns:
                            btn = random.choice(like_btns)
                            
                            # Simple or complex
                            if random.random() < 0.6:
                                actions = ActionChains(self.driver)
                                actions.move_to_element(btn).perform()
                                self.human_sleep(2, 3)
                                rx_options = self.driver.find_elements(By.XPATH, "//div[@role='dialog' or @role='presentation']//div[@role='button' and @aria-label]")
                                if rx_options:
                                    target_rx = random.choice(rx_options)
                                    update_status(f"🎯 Reacted: {target_rx.get_attribute('aria-label')}")
                                    self.human_click(target_rx)
                                else:
                                    self.human_click(btn)
                                    update_status("👍 Liked Video")
                            else:
                                self.human_click(btn)
                                update_status("👍 Liked Video")
                    except Exception as e:
                        update_status(f"⚠️ Reaction Vid Error: {str(e)[:20]}")
                
                # Watch time for the current video chunks
                self.human_sleep(10, 20)
            
            update_status("✅ Watch Video Completed")
        except Exception as e:
            update_status(f"❌ Watch Error: {str(e)[:40]}")

    def join_groups(self, keyword, count=3, status_callback=None):
        def update_status(m):
            if status_callback: status_callback(m)

        try:
            update_status(f"🔍 Searching Groups for: {keyword}")
            self.driver.get(f"https://www.facebook.com/groups/search/groups/?q={keyword}")
            self.human_sleep(5, 8)

            joined = 0
            scrolls = 0
            while joined < count and scrolls < 10:
                # Find Join buttons
                buttons = []
                xpaths = [
                    "//div[@role='button']//span[text()='Join' or text()='ចូលរួម']",
                    "//div[@role='button' and (@aria-label='Join group' or @aria-label='ចូលរួមក្រុម')]"
                ]
                for xp in xpaths:
                    try:
                        found = self.driver.find_elements(By.XPATH, xp)
                        if found: buttons.extend(found)
                    except: pass
                
                new_buttons = [b for b in buttons if b.is_displayed()]
                
                clicked = False
                for btn in new_buttons:
                    if joined >= count: break
                    try:
                        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn)
                        self.human_sleep(1, 2)
                        self.human_click(btn)
                        joined += 1
                        clicked = True
                        update_status(f"✅ Joined Group {joined}/{count}")
                        self.human_sleep(3, 6)
                    except: pass
                
                if not clicked:
                    update_status("📜 Scrolling for more groups...")
                    self.driver.execute_script("window.scrollBy(0, 800);")
                    self.human_sleep(3, 5)
                    scrolls += 1
                
            update_status(f"🎉 Group Join Complete: {joined}/{count}")
        except Exception as e:
            update_status(f"❌ Join Group Error: {str(e)[:40]}")

    def share_post_to_groups(self, post_url, count=3, status_callback=None):
        def update_status(m):
            if status_callback: status_callback(m)

        try:
            if not post_url or post_url == "Rotate" or "Empty" in post_url:
                update_status("⚠️ Invalid Post URL for Share")
                return

            update_status("🔄 Opening Post to Share...")
            self.driver.get(post_url)
            self.human_sleep(5, 8)
            
            shared = 0
            scrolls = 0
            
            while shared < count and scrolls < 5:
                try:
                    # Find Share button
                    share_btns = self.driver.find_elements(By.XPATH, "//div[@role='button']//span[contains(text(), 'Share') or contains(text(), 'ចែករំលែក')] | //div[@aria-label='Share' or @aria-label='ចែករំលែក']")
                    if not share_btns:
                        update_status("⚠️ Share button not found!")
                        break
                    
                    share_btn = share_btns[0]
                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", share_btn)
                    self.human_click(share_btn)
                    self.human_sleep(2, 4)
                    
                    # Click Share to a group
                    group_opts = self.driver.find_elements(By.XPATH, "//span[contains(text(), 'Share to a group') or contains(text(), 'ចែករំលែកទៅកាន់ក្រុម')] | //div[@role='menuitem']//span[contains(text(), 'group')]")
                    if group_opts:
                        self.human_click(group_opts[0])
                        self.human_sleep(3, 5)
                        
                        # Select a random group from the list
                        groups = self.driver.find_elements(By.XPATH, "//div[@role='button' and .//span[string-length(text()) > 3]]")
                        if len(groups) > 3: # Skip headers
                            target = random.choice(groups[3:min(15, len(groups))])
                            self.human_click(target)
                            self.human_sleep(2, 4)
                            
                            # Click Post
                            post_btns = self.driver.find_elements(By.XPATH, "//div[@role='button']//span[text()='Post' or text()='បង្ហោះ']")
                            if post_btns:
                                self.human_click(post_btns[0])
                                shared += 1
                                update_status(f"✅ Shared {shared}/{count}")
                                self.human_sleep(5, 8)
                            else:
                                update_status("⚠️ Submit button not found")
                        else:
                            update_status("⚠️ No groups found to share")
                            break
                    else:
                        update_status("⚠️ 'Share to a group' option not found")
                        break
                        
                except Exception as ex:
                    update_status(f"⚠️ Share attempt error: {str(ex)[:20]}")
                    scrolls += 1
            
            update_status(f"🎉 Share Complete: {shared}/{count}")
        except Exception as e:
            update_status(f"❌ Share Error: {str(e)[:40]}")

    def watch_stories(self, count=5, random_reactions=False, status_callback=None):
        def update_status(m):
            if status_callback: status_callback(m)

        try:
            self.check_and_dismiss_sleep_mode(status_callback)
            update_status("🔄 Opening Stories...")
            self.driver.get("https://www.facebook.com/")
            self.human_sleep(4, 7)
            self.check_and_dismiss_sleep_mode(status_callback)
            
            # Find a story to click (ignoring the "Create Story" card)
            story_cards = self.driver.find_elements(By.XPATH, "//div[@role='button' and @aria-label] | //div[contains(@class, 'story_card')] | //div[@data-visualcompletion='ignore-dynamic' and @role='button']")
            valid_stories = []
            for s in story_cards:
                try:
                    lbl = s.get_attribute("aria-label")
                    if lbl and "create" not in lbl.lower() and "add" not in lbl.lower() and "បង្កើត" not in lbl:
                        valid_stories.append(s)
                except:
                    valid_stories.append(s)
            
            if not valid_stories:
                update_status("⚠️ No stories found on Home.")
                return
                
            self.human_click(valid_stories[0])
            self.human_sleep(3, 5)
            
            viewed = 0
            while viewed < count:
                update_status(f"👀 Watching Story {viewed+1}/{count}")
                self.human_sleep(4, 8)
                
                if random_reactions and random.random() < 0.3:
                    reactions = ["Like", "Love", "Haha", "Wow", "Sad", "Angry", "ចូលចិត្ត", "ស្រឡាញ់"]
                    rx_xpath_expr = ' or '.join(f'contains(@aria-label, "{r}")' for r in reactions)
                    rx_xpath = f"//div[@role='button' and ({rx_xpath_expr})]"
                    try:
                        r_btns = self.driver.find_elements(By.XPATH, rx_xpath)
                        if r_btns:
                            self.human_click(random.choice(r_btns))
                            update_status(f"❤️ Reacted to Story {viewed+1}")
                            self.human_sleep(2, 3)
                    except: pass
                
                # Try to click next
                try:
                    next_btns = self.driver.find_elements(By.XPATH, "//div[@aria-label='Next card' or @aria-label='Next' or @aria-label='បន្ទាប់' or contains(@class, 'next')]")
                    if next_btns:
                        self.human_click(next_btns[0])
                    else:
                        self.human_sleep(2, 4) # Auto advance wait
                except: pass
                    
                viewed += 1
                
            update_status(f"🎉 Story Viewing Complete: {viewed}/{count}")
            self.driver.get("https://www.facebook.com/")
            
        except Exception as e:
            update_status(f"❌ Story Error: {str(e)[:40]}")

    def scrape_uids(self, target_url, limit=100, status_callback=None):
        def update_status(m):
            if status_callback: status_callback(m)

        try:
            if not target_url or target_url == "Rotate" or "Empty" in target_url:
                update_status("⚠️ Invalid target URL for Scraper")
                return

            update_status(f"🔄 Preparing to scrape: {target_url[:30]}...")
            self.driver.get(target_url)
            self.human_sleep(5, 8)
            
            uids = set()
            scrolls = 0
            max_scrolls = limit // 5 + 10
            
            update_status("🧲 Scrolling and extracting UIDs...")
            while len(uids) < limit and scrolls < max_scrolls:
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                self.human_sleep(2, 4)
                
                # Click 'View more comments' or 'See more' if present
                more_btns = self.driver.find_elements(By.XPATH, "//span[contains(text(), 'View more') or contains(text(), 'See more') or contains(text(), 'ច្រើនទៀត') or contains(text(), 'មើលបន្ថែម')]")
                for btn in more_btns:
                    if btn.is_displayed():
                        try:
                            self.human_click(btn)
                            self.human_sleep(1, 2)
                        except: pass
                
                # Extract links
                links = self.driver.find_elements(By.TAG_NAME, "a")
                for a in links:
                    try:
                        href = a.get_attribute("href")
                        if href and ("facebook.com/" in href or "fb.com" in href):
                            if "profile.php?id=" in href:
                                uid = href.split("id=")[1].split("&")[0]
                                if uid.isdigit(): uids.add(uid)
                            elif "/user/" in href:
                                uid = href.split("/user/")[1].split("/")[0]
                                if uid.isdigit(): uids.add(uid)
                            elif not any(x in href for x in ['/groups/', '/pages/', '/events/', '/hashtag/', '/watch/', '/marketplace/']):
                                # It might be a custom username
                                parts = href.split("facebook.com/")[1].split("?")[0].split("/")[0]
                                if parts and parts not in ["home.php", "login.php", "watch", "marketplace", "stories", "friends"]:
                                    uids.add(parts)
                    except: pass
                                
                scrolls += 1
                update_status(f"🧲 Scraped {len(uids)} UIDs...")
                
            # Save to file
            if uids:
                scraped_dir = os.path.join(os.getcwd(), "scraped_data")
                os.makedirs(scraped_dir, exist_ok=True)
                # Just base part of target url for filename
                t_name = target_url.replace("https://www.facebook.com/", "").replace("/", "_").replace("?", "_")[:15]
                fname = os.path.join(scraped_dir, f"uids_{t_name}_{int(time.time())}.txt")
                with open(fname, 'w', encoding='utf-8') as f:
                    for u in list(uids)[:limit]:
                        f.write(f"{u}\n")
                update_status(f"✅ Saved {min(len(uids), limit)} UIDs (check scraped_data/)")
                self.human_sleep(2, 3)
            else:
                update_status("⚠️ No UIDs found to scrape.")
            
        except Exception as e:
            update_status(f"❌ Scraper Error: {str(e)[:40]}")

    def invite_like_page(self, status_callback=None):
        def update_status(m):
            if status_callback: status_callback(m)

        try:
            self.check_and_dismiss_sleep_mode(status_callback)
            update_status("⏳ Waiting for page menu buttons to appear...")
            
            menu_selectors = [
                "//div[@aria-label='More']",
                "//div[@aria-label='Actions for this Page']",
                "//div[@aria-haspopup='menu' and @role='button']",
                "//div[contains(@class, 'xu0m77m')]//div[@role='button']"
            ]
            
            start_t = time.time()
            menu_ready = False
            while time.time() - start_t < 25: # Wait up to 25 seconds
                for xp in menu_selectors:
                    try:
                        btns = self.driver.find_elements(By.XPATH, xp)
                        if btns and any(b.is_displayed() for b in btns):
                            menu_ready = True
                            break
                    except:
                        pass
                if menu_ready:
                    break
                time.sleep(1)

            update_status("📡 Opening Page for Invite...")
            self.human_sleep(2, 3.5)
            
            # 1. Find the "More" or "..." menu button
            menu_selectors = [
                "//div[@aria-label='More']",
                "//div[@aria-label='Actions for this Page']",
                "//div[@aria-haspopup='menu' and @role='button']",
                "//div[contains(@class, 'xu0m77m')]//div[@role='button']" # Generic action button class
            ]
            
            menu_btn = None
            for xp in menu_selectors:
                try:
                    btns = self.driver.find_elements(By.XPATH, xp)
                    for b in btns:
                        if b.is_displayed():
                            menu_btn = b
                            break
                    if menu_btn: break
                except: pass
            
            if menu_btn:
                self.human_click(menu_btn)
                update_status("🖱️ Menu opened.")
                self.human_sleep(2, 4)
                
                # 2. Find "Invite friends" option
                invite_opts = [
                    "//span[contains(text(), 'Invite friends')]",
                    "//span[contains(text(), 'អញ្ជើញមិត្តភក្តិ')]",
                    "//div[@role='menuitem']//span[contains(text(), 'Invite')]"
                ]
                
                invite_opt = None
                for xp in invite_opts:
                    try:
                        el = self.driver.find_element(By.XPATH, xp)
                        if el.is_displayed():
                            invite_opt = el
                            break
                    except: pass
                
                if invite_opt:
                    self.human_click(invite_opt)
                    update_status("📩 Invite dialog opening...")
                    self.human_sleep(5, 8)
                    
                    # 3. Call the existing invite_friends logic if possible, 
                    # or implement a shorter version here.
                    # Since invite_friends is already implemented, we can try to reuse it 
                    # but it expects a different entry point. 
                    # For now, let's do a simple count select and send.
                    
                    update_status("✅ Dialog detected. Selecting friends...")
                    # Select All if available
                    try:
                        all_btn = self.driver.find_element(By.XPATH, "//span[contains(text(), 'Select All') or contains(text(), 'ជ្រើសរើសទាំងអស់')]")
                        self.human_click(all_btn)
                        self.human_sleep(1, 2)
                    except: pass
                    
                    # Send
                    send_btns = self.driver.find_elements(By.XPATH, "//div[@role='button']//span[contains(text(), 'Send') or contains(text(), 'ផ្ញើ')]")
                    if send_btns:
                        self.human_click(send_btns[0])
                        update_status("🎉 Invites sent successfully! ✅")
                        self.human_sleep(3, 5)
                    else:
                        update_status("⚠️ Send button not found in dialog.")
                else:
                    update_status("⚠️ 'Invite friends' option not found in menu.")
            else:
                update_status("⚠️ Page action menu (...) not found.")
                
        except Exception as e:
            update_status(f"❌ Invite Page Error: {str(e)[:40]}")

    def auto_post_photo(self, photo_path, caption="", status_callback=None):
        def update_status(m):
            if status_callback: status_callback(m)

        try:
            if not photo_path or not os.path.exists(photo_path):
                update_status("❌ Photo path invalid or empty.")
                return

            update_status("📸 Preparing to post photo...")
            self.driver.get("https://www.facebook.com/")
            self.human_sleep(5, 8)
            
            # 1. Click "Photo/video" button
            try:
                # Common selectors for the post box "Photo/video" button
                photo_btn_xp = "//span[contains(text(), 'Photo/video') or contains(text(), 'រូបថត/វីដេអូ')] | //div[@aria-label='Photo/video']"
                btn = WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((By.XPATH, photo_btn_xp)))
                self.human_click(btn)
                update_status("🖱️ Photo dialog opened.")
                self.human_sleep(3, 5)
            except:
                update_status("⚠️ Photo button not found. Trying direct input...")
            
            # 2. Find file input
            try:
                # FB uses a hidden file input
                file_input = self.driver.find_element(By.XPATH, "//input[@type='file' and contains(@accept, 'image')]")
                file_input.send_keys(os.path.abspath(photo_path))
                update_status("📤 Photo uploaded.")
                self.human_sleep(4, 7)
            except Exception as e:
                update_status(f"❌ Upload failed: {str(e)[:30]}")
                return

            # 3. Add Caption
            if caption:
                try:
                    caption_box = self.driver.find_element(By.XPATH, "//div[@role='textbox' and contains(@aria-label, 'What')] | //div[@contenteditable='true']")
                    self.human_type(caption_box, caption)
                    update_status("✏️ Caption added.")
                    self.human_sleep(2, 4)
                except: pass

            # 4. Post
            try:
                post_btn = self.driver.find_element(By.XPATH, "//div[@role='button']//span[text()='Post' or text()='បង្ហោះ']")
                self.human_click(post_btn)
                update_status("🚀 Posting...")
                self.human_sleep(10, 15)
                update_status("✅ Photo posted successfully!")
            except:
                update_status("❌ Post button not found.")

        except Exception as e:
            update_status(f"❌ Post Photo Error: {str(e)[:40]}")

    def auto_post_reel(self, video_path, caption="", status_callback=None):
        def update_status(m):
            if status_callback: status_callback(m)

        try:
            if not video_path or not os.path.exists(video_path):
                update_status("❌ Reel video path invalid.")
                return

            update_status("🎬 Preparing to post Reel...")
            self.driver.get("https://www.facebook.com/reels/create/")
            self.human_sleep(6, 10)
            
            # 1. Upload Video
            try:
                file_input = WebDriverWait(self.driver, 20).until(EC.presence_of_element_located((By.XPATH, "//input[@type='file']")))
                file_input.send_keys(os.path.abspath(video_path))
                update_status("📤 Reel video uploading...")
                # Reels upload can take time
                self.human_sleep(15, 25)
            except Exception as e:
                update_status(f"❌ Reel upload failed: {str(e)[:30]}")
                return

            # 2. Click "Next" (usually multiple steps: Trim, then Details)
            for _ in range(2):
                try:
                    next_btn = self.driver.find_element(By.XPATH, "//div[@role='button']//span[contains(text(), 'Next') or contains(text(), 'បន្ទាប់')]")
                    self.human_click(next_btn)
                    self.human_sleep(3, 5)
                except: break

            # 3. Add Caption
            if caption:
                try:
                    caption_box = self.driver.find_element(By.XPATH, "//div[@role='textbox'] | //div[@contenteditable='true']")
                    self.human_type(caption_box, caption)
                    update_status("✏️ Reel caption added.")
                    self.human_sleep(2, 4)
                except: pass

            # 4. Post/Share
            try:
                share_btn = self.driver.find_element(By.XPATH, "//div[@role='button']//span[contains(text(), 'Share') or contains(text(), 'ចែករំលែក') or contains(text(), 'Publish')]")
                self.human_click(share_btn)
                update_status("🚀 Publishing Reel...")
                self.human_sleep(15, 20)
                update_status("✅ Reel published successfully!")
            except:
                update_status("❌ Publish button not found.")

        except Exception as e:
            update_status(f"❌ Post Reel Error: {str(e)[:40]}")

    def close(self):
        if self.driver:
            self.driver.quit()

    def clean_profile_bloat(self, profile_path):
        """Cleans heavy cache, media, and temp files to keep profile sizes small"""
        if not profile_path or not os.path.exists(profile_path): return
        
        # Heavy folders typical in Chrome profiles that don't affect cookies/login state
        folders_to_delete = [
            'Cache', 'Code Cache', 'GPUCache', 'ShaderCache', 
            'GrShaderCache', 'Media Cache', 'Crashpad', 
            'System Profile/Cache', 'Default/Cache', 
            'Default/Code Cache', 'Default/GPUCache',
            'Default/Service Worker/CacheStorage', 'Default/Media Cache'
        ]
        
        for p in folders_to_delete:
            target = os.path.join(profile_path, *p.split('/'))
            if os.path.exists(target):
                try: shutil.rmtree(target, ignore_errors=True)
                except: pass


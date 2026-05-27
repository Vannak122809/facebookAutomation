import csv
import json
import os

class Account:
    def __init__(self, username, password, two_factor_secret="", status="Idle", cookies=None, profile_name="", friend_count=0, proxy="", category="All"):
        self.username = username.strip()
        self.password = password.strip()
        self.two_factor_secret = two_factor_secret.strip()
        self.status = status  # Idle, Logging In, Succeeded, Failed, Inviting, Completed
        self.cookies = cookies or []
        self.invites_sent = 0
        self.invites_failed = 0
        self.error_message = ""
        self.profile_name = profile_name.strip()
        self.friend_count = friend_count
        self.proxy = proxy.strip()
        self.category = category.strip()

    def to_dict(self):
        return {
            "username": self.username,
            "password": self.password,
            "two_factor_secret": self.two_factor_secret,
            "status": self.status,
            "invites_sent": self.invites_sent,
            "invites_failed": self.invites_failed,
            "error_message": self.error_message,
            "profile_name": self.profile_name,
            "friend_count": self.friend_count,
            "proxy": self.proxy,
            "category": self.category
        }

class AccountManager:
    def __init__(self, history_file="account_history.json"):
        self.accounts = []
        self.history_file = history_file
        self.categories_file = "categories.json"
        self.last_save_time = 0
        self.save_interval = 2.0  # Max 1 save every 2 seconds
        self._categories = self._load_categories_file()

    def _load_categories_file(self):
        """Load saved custom categories from disk."""
        try:
            if os.path.exists(self.categories_file):
                with open(self.categories_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        return data
        except Exception:
            pass
        return []

    def _save_categories_file(self):
        """Save custom categories list to disk."""
        try:
            with open(self.categories_file, 'w', encoding='utf-8') as f:
                json.dump(self._categories, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error saving categories: {e}")

    def get_categories(self):
        """Return sorted unique list of categories from both saved list and accounts."""
        from_accounts = [acc.category for acc in self.accounts if acc.category and acc.category not in ('', 'All')]
        merged = list(set(self._categories + from_accounts))
        merged = sorted([c for c in merged if c and c != 'All'])
        return ["All"] + merged

    def add_category(self, name):
        """Add a new custom category."""
        name = name.strip()
        if name and name != 'All' and name not in self._categories:
            self._categories.append(name)
            self._save_categories_file()

    def rename_category(self, old_name, new_name):
        """Rename a category and update all accounts using it."""
        old_name, new_name = old_name.strip(), new_name.strip()
        if not new_name or old_name == 'All':
            return
        if old_name in self._categories:
            idx = self._categories.index(old_name)
            self._categories[idx] = new_name
        for acc in self.accounts:
            if acc.category == old_name:
                acc.category = new_name
        self._save_categories_file()
        self.save_history(force=True)

    def delete_category(self, name):
        """Delete a category and reset accounts using it to 'All'."""
        if name == 'All':
            return
        if name in self._categories:
            self._categories.remove(name)
        for acc in self.accounts:
            if acc.category == name:
                acc.category = 'All'
        self._save_categories_file()
        self.save_history(force=True)

    def save_history(self, force=False):
        """Saves current accounts' execution statuses to a local history JSON file."""
        import time
        current_time = time.time()
        if not force and (current_time - self.last_save_time) < self.save_interval:
            return
        self.last_save_time = current_time
        
        try:
            history = {}
            # If history file already exists, load existing keys first to merge
            if os.path.exists(self.history_file):
                try:
                    with open(self.history_file, 'r', encoding='utf-8') as f:
                        history = json.load(f)
                except:
                    pass

            for acc in self.accounts:
                history[acc.username] = {
                    "password": acc.password,
                    "two_factor_secret": acc.two_factor_secret,
                    "status": acc.status,
                    "invites_sent": acc.invites_sent,
                    "invites_failed": acc.invites_failed,
                    "profile_name": acc.profile_name,
                    "friend_count": acc.friend_count,
                    "proxy": acc.proxy,
                    "category": acc.category
                }
            
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(history, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving history: {e}")

    def load_all_from_history(self):
        """Restores all fully saved accounts from history to memory upon app startup."""
        history_map = self.load_history_dict()
        for username, data in history_map.items():
            if not isinstance(data, dict):
                continue
            # We only restore it if it has a password saved (which means it's from the new format)
            password = data.get("password", "")
            two_fa = data.get("two_factor_secret", "")
            
            if password or data.get("status") in ("Active", "Completed", "Succeeded"):
                # Avoid duplicates
                if any(a.username == username for a in self.accounts):
                    continue
                    
                status = data.get("status", "Idle")
                if status in ("Login Failed", "Failed", "Error"):
                    status = "Dead"
                elif status in ("Completed", "Succeeded", "Logged In", "Active"):
                    status = "Active"
                elif status not in ("Dead", "Error Verify Google", "Error Login Google", "Check Point", "Chapracters dynamic function"):
                    status = "Idle"
                    
                acc = Account(
                    username=username,
                    password=password,
                    two_factor_secret=two_fa,
                    status=status,
                    profile_name=data.get("profile_name", ""),
                    friend_count=data.get("friend_count", 0),
                    proxy=data.get("proxy", ""),
                    category=data.get("category", "All")
                )
                acc.invites_sent = data.get("invites_sent", 0)
                acc.invites_failed = data.get("invites_failed", 0)
                self.accounts.append(acc)

    def load_history_dict(self):
        """Loads and returns the history map {username: data}."""
        if not os.path.exists(self.history_file):
            return {}
        try:
            with open(self.history_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading history file: {e}")
            return {}

    def load_from_text(self, text_content, category="All"):
        """Loads accounts from raw text.
        Supported formats:
        - username|password
        - username|password|2fa_secret
        - username|password|2fa_secret|proxy
        - username|password||proxy
        Automatically de-duplicates duplicate usernames and restores their saved status.
        Appends new unique accounts to the existing accounts list.
        """
        existing_usernames = {acc.username for acc in self.accounts}
        history_map = self.load_history_dict()
        seen_usernames = set()
        
        lines_raw = text_content.strip().split("\n")
        lines = []
        for line in lines_raw:
            line = line.strip()
            if not line:
                continue
            if '|' not in line and lines:
                # Missing pipe, probably wrapped from previous line (e.g., 2FA secret on a new line)
                lines[-1] += line
            else:
                lines.append(line)
                
        for line in lines:
            line = line.strip()
            if not line:
                continue
            parts = line.split("|")
            username = parts[0].strip()
            password = parts[1].strip() if len(parts) > 1 else ""
            two_fa = parts[2].strip() if len(parts) > 2 else ""
            proxy = parts[3].strip() if len(parts) > 3 else ""
            
            if username:
                # De-duplicate username checks (within this import batch and against existing ones)
                if username in seen_usernames or username in existing_usernames:
                    continue
                seen_usernames.add(username)
                
                # Check if there is history status for this user
                status = "Idle"
                inv_sent = 0
                inv_fail = 0
                profile_name = ""
                friend_count = 0
                hist_proxy = ""
                hist_category = category
                
                if username in history_map:
                    hist_data = history_map[username]
                    if isinstance(hist_data, dict):
                        raw_status = hist_data.get("status", "Idle")
                        # Normalize legacy/old status names to new friendly names
                        if raw_status in ("Login Failed", "Failed", "Error"):
                            status = "Dead"
                        elif raw_status in ("Completed", "Succeeded", "Logged In", "Active"):
                            status = "Active"
                        elif raw_status in ("Dead", "Error Verify Google", "Error Login Google", "Check Point", "Chapracters dynamic function"):
                            status = raw_status
                        else:
                            status = "Idle"  # Reset working/in-progress states
                        inv_sent = hist_data.get("invites_sent", 0)
                        inv_fail = hist_data.get("invites_failed", 0)
                        profile_name = hist_data.get("profile_name", "")
                        friend_count = hist_data.get("friend_count", 0)
                        hist_proxy = hist_data.get("proxy", "")
                        # If a specific category was requested (not "All"), we override the history category
                        if category != "All":
                            hist_category = category
                        else:
                            hist_category = hist_data.get("category", "All")
                    else:
                        # fallback older versions - string value
                        raw = hist_data
                        if raw in ("Login Failed", "Failed"):
                            status = "Dead"
                        elif raw in ("Completed", "Succeeded"):
                            status = "Active"
                        else:
                            status = "Idle"
                
                # Use imported proxy if present, otherwise fall back to history proxy
                proxy_to_use = proxy if proxy else hist_proxy
                
                acc = Account(
                    username, password, two_fa, 
                    status=status, 
                    profile_name=profile_name, 
                    friend_count=friend_count, 
                    proxy=proxy_to_use,
                    category=hist_category
                )
                acc.invites_sent = inv_sent
                acc.invites_failed = inv_fail
                self.accounts.append(acc)
                
        return self.accounts

    def load_from_csv(self, file_path, category="All"):
        """Loads accounts from CSV.
        Automatically de-duplicates duplicate usernames and restores their saved status.
        Appends new unique accounts to the existing accounts list.
        """
        existing_usernames = {acc.username for acc in self.accounts}
        history_map = self.load_history_dict()
        seen_usernames = set()
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                for row in reader:
                    if len(row) >= 2:
                        username = row[0].strip()
                        password = row[1].strip()
                        two_fa = row[2].strip() if len(row) > 2 else ""
                        proxy = row[3].strip() if len(row) > 3 else ""
                        
                        if username:
                            if username in seen_usernames or username in existing_usernames:
                                continue
                            seen_usernames.add(username)
                            
                            status = "Idle"
                            inv_sent = 0
                            inv_fail = 0
                            profile_name = ""
                            friend_count = 0
                            hist_proxy = ""
                            hist_category = category
                            
                            if username in history_map:
                                hist_data = history_map[username]
                                if isinstance(hist_data, dict):
                                    raw_status = hist_data.get("status", "Idle")
                                    if raw_status in ("Login Failed", "Failed", "Error"):
                                        status = "Dead"
                                    elif raw_status in ("Completed", "Succeeded", "Logged In", "Active"):
                                        status = "Active"
                                    elif raw_status in ("Dead", "Error Verify Google", "Error Login Google", "Check Point", "Chapracters dynamic function"):
                                        status = raw_status
                                    else:
                                        status = "Idle"
                                    inv_sent = hist_data.get("invites_sent", 0)
                                    inv_fail = hist_data.get("invites_failed", 0)
                                    profile_name = hist_data.get("profile_name", "")
                                    friend_count = hist_data.get("friend_count", 0)
                                    hist_proxy = hist_data.get("proxy", "")
                                    if category != "All":
                                        hist_category = category
                                    else:
                                        hist_category = hist_data.get("category", "All")
                            
                            proxy_to_use = proxy if proxy else hist_proxy
                            
                            acc = Account(
                                username, password, two_fa, 
                                status=status,
                                profile_name=profile_name,
                                friend_count=friend_count,
                                proxy=proxy_to_use,
                                category=hist_category
                            )
                            acc.invites_sent = inv_sent
                            acc.invites_failed = inv_fail
                            self.accounts.append(acc)
        except Exception as e:
            print(f"Error loading CSV: {e}")
        return self.accounts

    def clear_history(self):
        """Deletes history tracking file."""
        if os.path.exists(self.history_file):
            try:
                os.remove(self.history_file)
            except:
                pass

    def clear(self):
        self.accounts = []

# Facebook Auto-Login & Page Invite Automation Tool

A standard, modern desktop application built using **Python**, **PySide6 (Qt6)**, and **Selenium** with a premium dark-themed dashboard. This tool is designed to automate page invitations from multiple Facebook accounts concurrently using mobile emulation.

## Features

1. **Concurrent Multi-Threading**: Processes multiple account logins and page invitation tasks in parallel using PySide6 background threads (`QThread`) without freezing the interface.
2. **Mobile Emulation Viewport**: Emulates mobile phones (e.g. iPhone X, Nexus 5, Pixel 5) inside Selenium to load Facebook Mobile (`m.facebook.com`) which reduces resource consumption and improves bot detection bypass.
3. **Session Cookie Management**: Automatically exports successful login cookies to the `cookies/` directory and re-imports them on the next run to skip credentials login entirely.
4. **Pure-Python 2FA Generator**: Built-in OTP generator supports generating 6-digit 2FA login verification codes on-the-fly if a base32 2FA secret is provided.
5. **Real-time Live Stats & Dashboard**: Displays live counts of total accounts, active sessions, successful logins, failed logins, invites sent, and invites failed.
6. **Configurable Delay & Limits**: Customize random delays between invitation actions and set maximum invitations allowed per account per page.
7. **Custom XPath DOM Selectors**: Fully customizable XPath fields on the GUI dashboard to adapt quickly when Facebook updates its webpage structure.

---

## Installation & Setup

1. **Prerequisites**:
   - Install Python 3.10+
   - Install Google Chrome browser on your computer.

2. **Clone / Place Project**:
   Ensure all files are in your working directory.

3. **Install Dependencies**:
   Run the following command in your terminal:
   ```bash
   pip install -r requirements.txt
   ```

---

## How to Use

1. **Launch the Application**:
   ```bash
   python main.py
   ```

2. **Import Accounts**:
   - Click the **Import TXT** button on the top right.
   - Choose a `.txt` file containing your Facebook credentials. The format should be:
     ```text
     username_1|password_1|2fa_secret_1
     username_2|password_2|2fa_secret_2
     ```
     *(Note: The 2FA secret is optional. You can format it as `username|password` if the account does not have 2FA).*

3. **Configure Targets & Speed**:
   - Input your target Facebook Page URLs in the text area (one link per line).
   - Adjust the **Max Concurrent Threads** to set how many browsers run simultaneously.
   - Set the random **Delay Between Invites** range (e.g. 2 to 5 seconds) to simulate human speed.
   - Adjust **Max Invites Per Page** limit.

4. **Start Run**:
   - Click the green **START RUN** button.
   - Watch the account statuses update in real-time in the Table and view detailed execution logs in the console panel below.
   - Click **STOP RUN** to halt all threads instantly.

---

## File Structure

```text
├── main.py                     # App bootstrap launcher
├── requirements.txt            # Package list
├── README.md                   # Setup guide
├── cookies/                    # Created dynamically to save account session JSONs
├── core/
│   ├── account_manager.py      # Account data models and parser logic
│   └── automation.py           # Selenium web driver & multi-threaded task runner
└── ui/
    ├── dashboard.py            # Dashboard widget & layouts
    └── styles.py               # Dark-mode premium QSS stylesheets
```

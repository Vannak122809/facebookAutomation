import os
import sys

# Ensure the root directory is in python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import datetime
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QTableWidget, QTableWidgetItem, QTextEdit, QTableView,
    QLineEdit, QFormLayout, QFrame, QFileDialog, QCheckBox, QRadioButton,
    QSpinBox, QComboBox, QHeaderView, QSplitter, QScrollBar, QGroupBox,
    QMenu, QDialog, QDialogButtonBox, QMessageBox, QTabWidget, QScrollArea,
    QProgressBar, QSizePolicy, QListWidget, QAbstractItemView, QGridLayout
)
from PySide6.QtCore import Qt, Slot, QThread, Signal
from PySide6.QtGui import QColor, QFont

from core.account_manager import AccountManager, Account
from core.automation import SeleniumWorker, set_api_key
from core.updater import check_for_update, download_and_install, get_local_version
from ui.styles import LIGHT_THEME_STYLE, DARK_THEME_STYLE


# =============================================================================
# Auto-Update Worker
# =============================================================================
class UpdateCheckWorker(QThread):
    """Background thread to check GitHub for updates without blocking the UI."""
    result_signal = Signal(dict)  # emits the result dict from check_for_update()

    def run(self):
        result = check_for_update(timeout=10)
        self.result_signal.emit(result)


class UpdateDownloadWorker(QThread):
    """Background thread to download and install the new exe."""
    progress_signal  = Signal(int, int)   # downloaded_bytes, total_bytes
    finished_signal  = Signal(bool)       # success

    def __init__(self, download_url: str, new_version: str = ""):
        super().__init__()
        self.download_url = download_url
        self.new_version = new_version

    def run(self):
        def _progress(dl, total):
            self.progress_signal.emit(dl, total)
        success = download_and_install(
            self.download_url,
            progress_callback=_progress,
            new_version=self.new_version
        )
        self.finished_signal.emit(success)


class UpdateDialog(QDialog):
    """Full-featured update dialog with progress bar."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🔄 Check for Update")
        self.setMinimumSize(440, 280)
        self.setStyleSheet(parent.styleSheet() if parent else "")
        self._download_worker = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        # Title
        title = QLabel("Software Update")
        title.setStyleSheet("font-size: 16px; font-weight: 800; color: #3b82f6;")
        layout.addWidget(title)

        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        divider.setStyleSheet("background:#334155; max-height:1px; border:none;")
        layout.addWidget(divider)

        # Version info row
        ver_row = QHBoxLayout()
        self.lbl_local  = QLabel(f"Current version:  {get_local_version()}")
        self.lbl_remote = QLabel("Latest version:  Checking...")
        for lbl in (self.lbl_local, self.lbl_remote):
            lbl.setStyleSheet("font-size: 12px; font-weight: 600;")
        ver_row.addWidget(self.lbl_local)
        ver_row.addStretch()
        ver_row.addWidget(self.lbl_remote)
        layout.addLayout(ver_row)

        # Status label
        self.lbl_status = QLabel("Connecting to GitHub...")
        self.lbl_status.setStyleSheet("font-size: 12px; color: #64748b;")
        layout.addWidget(self.lbl_status)

        # Progress bar (hidden until download starts)
        self.progress = QProgressBar()
        self.progress.setMinimum(0)
        self.progress.setMaximum(100)
        self.progress.setValue(0)
        self.progress.setFixedHeight(10)
        self.progress.setTextVisible(False)
        self.progress.setStyleSheet(
            "QProgressBar { border:none; border-radius:5px; background:#1e293b; }"
            "QProgressBar::chunk { background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #3b82f6, stop:1 #7c3aed); border-radius:5px; }"
        )
        self.progress.hide()
        layout.addWidget(self.progress)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self.btn_update = QPushButton("Download & Install")
        self.btn_update.setObjectName("PrimaryButton")
        self.btn_update.setMinimumHeight(38)
        self.btn_update.setMinimumWidth(160)
        self.btn_update.setCursor(Qt.PointingHandCursor)
        self.btn_update.hide()
        self.btn_update.clicked.connect(self._start_download)

        self.btn_close = QPushButton("Close")
        self.btn_close.setMinimumHeight(38)
        self.btn_close.setMinimumWidth(80)
        self.btn_close.setCursor(Qt.PointingHandCursor)
        self.btn_close.clicked.connect(self.reject)
        btn_row.addWidget(self.btn_update)
        btn_row.addWidget(self.btn_close)
        layout.addStretch()
        layout.addLayout(btn_row)

        self._download_url = None
        self._remote_version = ""
        self._release_notes = ""

        # Start check immediately
        self._check_worker = UpdateCheckWorker()
        self._check_worker.result_signal.connect(self._on_check_result)
        self._check_worker.start()

    def _on_check_result(self, result):
        remote = result.get("remote", "?")
        self.lbl_remote.setText(f"Latest version:  {remote}")

        if result.get("error"):
            self.lbl_status.setText(f"❌ Error: {result['error']}")
            self.lbl_status.setStyleSheet("font-size: 12px; color: #ef4444;")
        elif result.get("has_update"):
            notes = result.get("release_notes", "").strip()
            note_txt = f"\nWhat's new: {notes[:120]}..." if len(notes) > 120 else (f"\nWhat's new: {notes}" if notes else "")
            self.lbl_status.setText(f"✅ Version {remote} is available!{note_txt}\n\nClick below to download and install.")
            self.lbl_status.setStyleSheet("font-size: 12px; color: #059669; font-weight: 700;")
            self._download_url = result.get("download_url")
            self._remote_version = remote
            self.btn_update.show()
        else:
            self.lbl_status.setText("✅ You are already on the latest version.")
            self.lbl_status.setStyleSheet("font-size: 12px; color: #059669;")

    def _start_download(self):
        if not self._download_url:
            return
        self.btn_update.setEnabled(False)
        self.btn_update.setText("Downloading...")
        self.progress.show()
        self.lbl_status.setText("⏬ Backing up your data, then downloading update...")

        self._download_worker = UpdateDownloadWorker(self._download_url, new_version=self._remote_version)
        self._download_worker.progress_signal.connect(self._on_progress)
        self._download_worker.finished_signal.connect(self._on_download_done)
        self._download_worker.start()

    def _on_progress(self, downloaded, total):
        if total > 0:
            pct = int(downloaded / total * 100)
            self.progress.setValue(pct)
            mb_dl = downloaded / 1_048_576
            mb_tot = total / 1_048_576
            self.lbl_status.setText(f"Downloading... {mb_dl:.1f} MB / {mb_tot:.1f} MB  ({pct}%)")
        else:
            mb_dl = downloaded / 1_048_576
            self.lbl_status.setText(f"Downloading... {mb_dl:.1f} MB")

    def _on_download_done(self, success):
        if success:
            self.lbl_status.setText("✅ Update downloaded! The app will restart automatically.")
            self.lbl_status.setStyleSheet("font-size: 12px; color: #059669; font-weight: 700;")
            self.progress.setValue(100)
            QMessageBox.information(
                self, "Update Ready",
                "Update downloaded!\nThe application will now close and restart with the new version."
            )
            import sys
            sys.exit(0)  # The .bat launcher will restart the exe
        else:
            self.lbl_status.setText("❌ Download failed. Please try again or download manually.")
            self.lbl_status.setStyleSheet("font-size: 12px; color: #ef4444;")
            self.btn_update.setEnabled(True)
            self.btn_update.setText("Retry Download")


# =============================================================================
# Account Checker Worker — runs Selenium to check if each account is alive
# =============================================================================
class AccountCheckerWorker(QThread):
    """Lightweight QThread that checks a list of Account objects sequentially."""
    result_signal  = Signal(str, str)   # username, status ("Active" | "Dead" | "Error: ...")
    progress_signal = Signal(int, int)  # current_index, total
    log_signal      = Signal(str)       # plain log line
    finished_signal = Signal()

    def __init__(self, accounts, options_settings, xpath_settings):
        super().__init__()
        self.accounts = accounts
        self.options_settings = options_settings
        self.xpath_settings   = xpath_settings
        self.is_running = True

    def stop(self):
        self.is_running = False

    def run(self):
        total = len(self.accounts)
        for idx, acc in enumerate(self.accounts):
            if not self.is_running:
                break
            self.progress_signal.emit(idx + 1, total)
            self.log_signal.emit(f"[{idx+1}/{total}] Checking: {acc.username} ...")
            try:
                # Re-use SeleniumWorker for its setup_driver / login logic
                # We set manual_control=False, page_urls=[], and skip invite task
                opts = self.options_settings.copy()
                opts["enable_invite_task"] = False
                opts["enable_profile_scrape"] = False
                worker = SeleniumWorker(acc, [], self.xpath_settings, opts)
                worker.start()
                worker.wait()   # block until this one finishes (sequential)

                if acc.status == "Active":
                    self.result_signal.emit(acc.username, "Active")
                    self.log_signal.emit(f"  ✅ {acc.username} → Active (ក្រស់)")
                elif acc.status == "Check Point":
                    self.result_signal.emit(acc.username, "Check Point")
                    self.log_signal.emit(f"  🔒 {acc.username} → Check Point (ចាក់សោ)")
                elif acc.status == "Chapracters dynamic function":
                    self.result_signal.emit(acc.username, "Chapracters dynamic function")
                    self.log_signal.emit(f"  ⚠️  {acc.username} → Chapracters dynamic function (ជាប់ Captcha)")
                else:
                    self.result_signal.emit(acc.username, acc.status if acc.status in ("Error Verify Google", "Error Login Google") else "Dead")
                    self.log_signal.emit(f"  ❌ {acc.username} → {acc.status} (ស្លាប់)")
            except Exception as e:
                self.result_signal.emit(acc.username, f"Error")
                self.log_signal.emit(f"  ⚠️  {acc.username} → Error: {str(e)[:80]}")

        self.progress_signal.emit(total, total)
        self.finished_signal.emit()


# =============================================================================
# Check Account Dialog
# =============================================================================
class CheckAccountDialog(QDialog):
    """
    Dialog for checking if Facebook accounts are alive or dead.
    Users paste accounts (user|pass or user|pass|2fa|proxy), click Start,
    and see real-time results.
    """
    def __init__(self, parent_window, config, is_dark_mode):
        super().__init__(parent_window)
        self.parent_window = parent_window
        self.config        = config
        self.is_dark_mode  = is_dark_mode
        self.worker        = None
        self._accounts_map = {}

        self.setWindowTitle("Account Checker")
        self.resize(820, 700)
        self.setMinimumSize(700, 580)
        self.setStyleSheet(parent_window.styleSheet())

        # Colors based on theme
        dark = is_dark_mode
        bg_main   = "#0f172a" if dark else "#f1f5f9"
        bg_card   = "#1e293b" if dark else "#ffffff"
        bg_header = "qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #1e3a8a,stop:1 #7c3aed)"
        border_c  = "#334155" if dark else "#e2e8f0"
        text_main = "#f1f5f9" if dark else "#0f172a"
        text_sub  = "#94a3b8" if dark else "#64748b"

        # Root layout — no margins, we handle them per section
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ═══════════════════════════════════════════
        # HEADER BANNER
        # ═══════════════════════════════════════════
        header_frame = QFrame()
        header_frame.setFixedHeight(80)
        header_frame.setStyleSheet(
            f"QFrame {{ background: {bg_header}; border: none; }}"
        )
        header_inner = QHBoxLayout(header_frame)
        header_inner.setContentsMargins(24, 0, 24, 0)
        header_inner.setSpacing(14)

        icon_lbl = QLabel("🔍")
        icon_lbl.setStyleSheet("font-size: 28px; background: transparent;")
        icon_lbl.setFixedWidth(40)

        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        h_title = QLabel("Account Checker")
        h_title.setStyleSheet(
            "font-size: 18px; font-weight: 800; color: #ffffff; background: transparent;"
        )
        h_sub = QLabel("Verify Facebook accounts — Active (ក្រស់) or Dead (ស្លាប់)")
        h_sub.setStyleSheet(
            "font-size: 11px; color: rgba(255,255,255,0.75); background: transparent;"
        )
        title_box.addWidget(h_title)
        title_box.addWidget(h_sub)

        header_inner.addWidget(icon_lbl)
        header_inner.addLayout(title_box)
        header_inner.addStretch()

        # Live counter badges in header
        self._badge_active = self._make_header_badge("✅  Active", "0", "#10b981", header_inner)
        self._badge_dead   = self._make_header_badge("❌  Dead",   "0", "#ef4444", header_inner)
        self._badge_total  = self._make_header_badge("📋  Total",  "0", "#60a5fa", header_inner)

        root.addWidget(header_frame)

        # ═══════════════════════════════════════════
        # BODY (scrollable content)
        # ═══════════════════════════════════════════
        body = QWidget()
        body.setStyleSheet(f"background: {bg_main};")
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(20, 16, 20, 0)
        body_layout.setSpacing(14)

        # ── Input Card ──────────────────────────────
        input_card = QFrame()
        input_card.setStyleSheet(
            f"QFrame {{ background: {bg_card}; border: 1.5px solid {border_c};"
            f" border-radius: 12px; }}"
        )
        input_card_layout = QVBoxLayout(input_card)
        input_card_layout.setContentsMargins(16, 14, 16, 14)
        input_card_layout.setSpacing(10)

        # Card header row
        card_title_row = QHBoxLayout()
        card_title_lbl = QLabel("📋  Paste Accounts")
        card_title_lbl.setStyleSheet(
            f"font-size: 13px; font-weight: 700; color: {'#60a5fa' if dark else '#3b82f6'};"
            f" background: transparent;"
        )
        fmt_badge = QLabel("  username | password | 2fa | proxy  ")
        fmt_badge.setStyleSheet(
            "font-size: 10px; font-weight: 600; color: #64748b;"
            " background: #f1f5f9; border: 1px solid #e2e8f0; border-radius: 6px;"
            " padding: 2px 8px;"
            if not dark else
            "font-size: 10px; font-weight: 600; color: #94a3b8;"
            " background: #0f172a; border: 1px solid #334155; border-radius: 6px;"
            " padding: 2px 8px;"
        )
        card_title_row.addWidget(card_title_lbl)
        card_title_row.addStretch()
        card_title_row.addWidget(fmt_badge)
        input_card_layout.addLayout(card_title_row)

        # Text area
        self.input_edit = QTextEdit()
        self.input_edit.setPlaceholderText(
            "example@gmail.com|mypassword123\n"
            "user2@email.com|pass456|2FA_SECRET\n"
            "user3@email.com|pass789||192.168.1.1:8080"
        )
        self.input_edit.setFixedHeight(110)
        self.input_edit.setStyleSheet(
            f"QTextEdit {{ background: {'#0f172a' if dark else '#f8fafc'};"
            f" border: 1.5px solid {border_c}; border-radius: 8px;"
            f" padding: 10px 12px; color: {text_main}; font-size: 12px;"
            f" font-family: 'Consolas', 'Courier New', monospace; }}"
            f"QTextEdit:focus {{ border-color: #3b82f6; }}"
        )
        input_card_layout.addWidget(self.input_edit)

        # Controls row inside card
        ctrl_row = QHBoxLayout()
        ctrl_row.setSpacing(8)

        self.start_btn = QPushButton("  ▶  Start Check")
        self.start_btn.setObjectName("PrimaryButton")
        self.start_btn.setMinimumHeight(38)
        self.start_btn.setMinimumWidth(140)
        self.start_btn.setCursor(Qt.PointingHandCursor)
        self.start_btn.setStyleSheet(
            "QPushButton { background: #3b82f6; color: white; border: none;"
            " border-radius: 8px; font-size: 13px; font-weight: 700; padding: 0 16px; }"
            "QPushButton:hover { background: #2563eb; }"
            "QPushButton:pressed { background: #1d4ed8; }"
            "QPushButton:disabled { background: #94a3b8; }"
        )
        self.start_btn.clicked.connect(self.start_check)

        self.stop_btn = QPushButton("  ⬛  Stop")
        self.stop_btn.setMinimumHeight(38)
        self.stop_btn.setMinimumWidth(100)
        self.stop_btn.setCursor(Qt.PointingHandCursor)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet(
            "QPushButton { background: #ef4444; color: white; border: none;"
            " border-radius: 8px; font-size: 13px; font-weight: 700; padding: 0 16px; }"
            "QPushButton:hover { background: #dc2626; }"
            "QPushButton:disabled { background: #fca5a5; color: #fee2e2; }"
        )
        self.stop_btn.clicked.connect(self.stop_check)

        self.clear_input_btn = QPushButton("  🗑  Clear")
        self.clear_input_btn.setMinimumHeight(38)
        self.clear_input_btn.setMinimumWidth(90)
        self.clear_input_btn.setCursor(Qt.PointingHandCursor)
        self.clear_input_btn.setStyleSheet(
            f"QPushButton {{ background: {'#1e293b' if dark else '#f1f5f9'}; color: {text_sub};"
            f" border: 1px solid {border_c}; border-radius: 8px;"
            f" font-size: 13px; font-weight: 600; }}"
            f"QPushButton:hover {{ background: {'#334155' if dark else '#e2e8f0'}; }}"
        )
        self.clear_input_btn.clicked.connect(self.input_edit.clear)

        ctrl_row.addWidget(self.start_btn)
        ctrl_row.addWidget(self.stop_btn)
        ctrl_row.addWidget(self.clear_input_btn)
        ctrl_row.addStretch()

        # Headless toggle with modern styling
        self.headless_chk = QCheckBox("  🖥  Headless mode")
        self.headless_chk.setObjectName("SubCheckBox")
        self.headless_chk.setChecked(True)
        ctrl_row.addWidget(self.headless_chk)
        input_card_layout.addLayout(ctrl_row)

        body_layout.addWidget(input_card)

        # ── Progress Card ────────────────────────────
        prog_card = QFrame()
        prog_card.setStyleSheet(
            f"QFrame {{ background: {bg_card}; border: 1.5px solid {border_c};"
            f" border-radius: 12px; }}"
        )
        prog_card_layout = QHBoxLayout(prog_card)
        prog_card_layout.setContentsMargins(16, 12, 16, 12)
        prog_card_layout.setSpacing(14)

        prog_icon = QLabel("⚡")
        prog_icon.setStyleSheet("font-size: 16px; background: transparent;")
        prog_icon.setFixedWidth(22)

        self.status_lbl = QLabel("Ready to check accounts")
        self.status_lbl.setStyleSheet(
            f"font-size: 12px; font-weight: 600; color: {text_sub}; background: transparent;"
        )
        self.status_lbl.setMinimumWidth(200)

        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(10)
        self.progress_bar.setStyleSheet(
            f"QProgressBar {{ border: none; border-radius: 5px;"
            f" background: {'#0f172a' if dark else '#e2e8f0'}; }}"
            f"QProgressBar::chunk {{ background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            f"stop:0 #3b82f6, stop:1 #7c3aed); border-radius: 5px; }}"
        )

        self.pct_lbl = QLabel("0%")
        self.pct_lbl.setStyleSheet(
            f"font-size: 12px; font-weight: 700; color: {'#60a5fa' if dark else '#3b82f6'};"
            f" background: transparent;"
        )
        self.pct_lbl.setFixedWidth(38)
        self.pct_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        prog_card_layout.addWidget(prog_icon)
        prog_card_layout.addWidget(self.status_lbl)
        prog_card_layout.addWidget(self.progress_bar, 1)
        prog_card_layout.addWidget(self.pct_lbl)

        body_layout.addWidget(prog_card)

        # ── Results Table ────────────────────────────
        results_lbl = QLabel("📊  Results")
        results_lbl.setStyleSheet(
            f"font-size: 13px; font-weight: 700; color: {text_sub}; margin-top: 4px;"
        )
        body_layout.addWidget(results_lbl)

        self.result_table = QTableWidget(0, 3)
        self.result_table.setHorizontalHeaderLabels(["Username / Email", "Status", "Result"])
        self.result_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.result_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.result_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.result_table.setAlternatingRowColors(True)
        self.result_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.result_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.result_table.setShowGrid(False)
        self.result_table.verticalHeader().setVisible(False)
        self.result_table.setRowHeight(0, 40)
        self.result_table.setStyleSheet(
            f"QTableWidget {{ background: {bg_card}; border: 1.5px solid {border_c};"
            f" border-radius: 12px; gridline-color: transparent; }}"
            f"QTableWidget::item {{ padding: 8px 12px; }}"
            f"QTableWidget::item:selected {{ background: {'#334155' if dark else '#e2e8f0'};"
            f" color: {'#cbd5e1' if dark else '#1e293b'}; }}"
            f"QHeaderView::section {{ background: {'#0f172a' if dark else '#f8fafc'};"
            f" color: {text_sub}; font-weight: 700; font-size: 11px;"
            f" padding: 10px 12px; border: none;"
            f" border-bottom: 2px solid {border_c}; }}"
        )
        body_layout.addWidget(self.result_table)

        # ── Summary Bar ──────────────────────────────
        self.summary_frame = QFrame()
        self.summary_frame.setFixedHeight(50)
        self.summary_frame.setStyleSheet(
            f"QFrame {{ background: {bg_card}; border: 1.5px solid {border_c};"
            f" border-radius: 10px; }}"
        )
        summary_row = QHBoxLayout(self.summary_frame)
        summary_row.setContentsMargins(16, 0, 16, 0)
        summary_row.setSpacing(20)

        self.sum_active_lbl = QLabel("✅  Active: —")
        self.sum_active_lbl.setStyleSheet(
            "font-size: 13px; font-weight: 700; color: #059669; background: transparent;"
        )
        self.sum_dead_lbl = QLabel("❌  Dead: —")
        self.sum_dead_lbl.setStyleSheet(
            "font-size: 13px; font-weight: 700; color: #dc2626; background: transparent;"
        )
        self.sum_total_lbl = QLabel("📋  Total: —")
        self.sum_total_lbl.setStyleSheet(
            f"font-size: 13px; font-weight: 700; color: {text_sub}; background: transparent;"
        )
        summary_row.addWidget(self.sum_active_lbl)
        summary_row.addWidget(self.sum_dead_lbl)
        summary_row.addWidget(self.sum_total_lbl)
        summary_row.addStretch()

        body_layout.addWidget(self.summary_frame)
        body_layout.addSpacing(4)

        root.addWidget(body)

        # ═══════════════════════════════════════════
        # BOTTOM ACTION BAR
        # ═══════════════════════════════════════════
        footer = QFrame()
        footer.setFixedHeight(58)
        footer.setStyleSheet(
            f"QFrame {{ background: {bg_card}; border-top: 1.5px solid {border_c}; }}"
        )
        footer_row = QHBoxLayout(footer)
        footer_row.setContentsMargins(20, 0, 20, 0)
        footer_row.setSpacing(10)
        footer_row.addStretch()

        close_btn = QPushButton("Close")
        close_btn.setMinimumHeight(38)
        close_btn.setMinimumWidth(110)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet(
            f"QPushButton {{ background: {'#1e293b' if dark else '#f1f5f9'}; color: {text_sub};"
            f" border: 1px solid {border_c}; border-radius: 8px;"
            f" font-size: 13px; font-weight: 600; }}"
            f"QPushButton:hover {{ background: {'#334155' if dark else '#e2e8f0'}; }}"
        )
        close_btn.clicked.connect(self.close_dialog)
        footer_row.addWidget(close_btn)

        root.addWidget(footer)

    def _make_header_badge(self, label_text, count_text, color, parent_layout):
        """Creates a compact colored stat badge for the header."""
        frame = QFrame()
        frame.setFixedSize(90, 54)
        frame.setStyleSheet(
            f"QFrame {{ background: rgba(255,255,255,0.12); border: 1px solid rgba(255,255,255,0.2);"
            f" border-radius: 8px; }}"
        )
        fl = QVBoxLayout(frame)
        fl.setContentsMargins(8, 6, 8, 6)
        fl.setSpacing(2)

        lbl = QLabel(label_text)
        lbl.setStyleSheet("font-size: 10px; color: rgba(255,255,255,0.8); background: transparent; font-weight: 600; border: none;")
        lbl.setAlignment(Qt.AlignCenter)

        val = QLabel(count_text)
        val.setStyleSheet(f"font-size: 16px; font-weight: 800; color: {color}; background: transparent; border: none;")
        val.setAlignment(Qt.AlignCenter)

        fl.addWidget(lbl)
        fl.addWidget(val)
        parent_layout.addWidget(frame)
        return val   # return value label so we can update it

    # -----------------------------------------------------------------------
    def _parse_input(self):
        """Parse the text area into a list of Account objects."""
        text = self.input_edit.toPlainText().strip()
        if not text:
            return []
        accs = []
        seen = set()
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            parts = line.split("|")
            username = parts[0].strip()
            password = parts[1].strip() if len(parts) > 1 else ""
            two_fa   = parts[2].strip() if len(parts) > 2 else ""
            proxy    = parts[3].strip() if len(parts) > 3 else ""
            if username and username not in seen:
                seen.add(username)
                accs.append(Account(username, password, two_fa, proxy=proxy))
        return accs

    def _update_badges(self):
        n_active = 0
        n_dead   = 0
        for row in range(self.result_table.rowCount()):
            item = self.result_table.item(row, 1)
            if item:
                if "Active" in item.text():
                    n_active += 1
                elif "Dead" in item.text() or "Check Point" in item.text() or "Google" in item.text() or "Chapracters" in item.text():
                    n_dead += 1
        total = self.result_table.rowCount()
        self._badge_active.setText(str(n_active))
        self._badge_dead.setText(str(n_dead))
        self._badge_total.setText(str(total))
        self.sum_active_lbl.setText(f"✅  Active: {n_active}")
        self.sum_dead_lbl.setText(f"❌  Dead: {n_dead}")
        self.sum_total_lbl.setText(f"📋  Total: {total}")

    def start_check(self):
        accounts = self._parse_input()
        if not accounts:
            QMessageBox.warning(self, "No Accounts", "Please paste at least one account to check.")
            return

        # Reset result table
        self.result_table.setRowCount(0)
        self._accounts_map.clear()

        # Reset badges
        self._badge_active.setText("0")
        self._badge_dead.setText("0")
        self._badge_total.setText(str(len(accounts)))
        self.sum_active_lbl.setText("✅  Active: 0")
        self.sum_dead_lbl.setText("❌  Dead: 0")
        self.sum_total_lbl.setText(f"📋  Total: {len(accounts)}")

        # Fill table rows (Pending state)
        for i, acc in enumerate(accounts):
            self.result_table.insertRow(i)
            self.result_table.setRowHeight(i, 40)
            username_item = QTableWidgetItem(f"  {acc.username}")
            self.result_table.setItem(i, 0, username_item)
            status_item = QTableWidgetItem("⏳  Pending")
            status_item.setTextAlignment(Qt.AlignCenter)
            status_item.setForeground(QColor("#94a3b8"))
            self.result_table.setItem(i, 1, status_item)
            dash_item = QTableWidgetItem("—")
            dash_item.setTextAlignment(Qt.AlignCenter)
            dash_item.setForeground(QColor("#94a3b8"))
            self.result_table.setItem(i, 2, dash_item)
            self._accounts_map[acc.username] = i

        self.progress_bar.setMaximum(len(accounts))
        self.progress_bar.setValue(0)
        self.pct_lbl.setText("0%")
        self.status_lbl.setText(f"Starting — 0 / {len(accounts)} accounts...")

        # Build options
        options = {
            "headless": self.headless_chk.isChecked(),
            "mobile_device": "Nexus 5",
            "login_mode": "auto",
            "max_login_retries": 1,
            "wait_timeout": 12,
            "page_load_timeout": 30,
            "enable_invite_task": False,
            "enable_profile_scrape": False,
        }
        xpath = self.config.get("xpath_settings", {})

        self.worker = AccountCheckerWorker(accounts, options, xpath)
        self.worker.result_signal.connect(self.on_result)
        self.worker.progress_signal.connect(self.on_progress)
        self.worker.log_signal.connect(self.on_log)
        self.worker.finished_signal.connect(self.on_finished)

        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.worker.start()

    def stop_check(self):
        if self.worker:
            self.worker.stop()
        self.stop_btn.setEnabled(False)
        self.status_lbl.setText("Stopping — waiting for current check...")

    def on_result(self, username, status):
        row = self._accounts_map.get(username)
        if row is None:
            return
        is_active = status == "Active"
        is_cp = status == "Check Point"
        is_captcha = status == "Chapracters dynamic function"

        if is_active:
            status_text = "✅  Active (ក្រស់)"
            status_color = "#059669"
            result_text = "Login OK ✓"
            result_color = "#059669"
        elif is_cp:
            status_text = "🔒  Check Point"
            status_color = "#dc2626"
            result_text = "Check Point ✗"
            result_color = "#ef4444"
        elif is_captcha:
            status_text = "⚠️  Captcha Block"
            status_color = "#dc2626"
            result_text = "Captcha ✗"
            result_color = "#ef4444"
        else:
            status_text = f"❌  {status} (ស្លាប់)" if status not in ("Dead", "Error") else "❌  Dead (ស្លាប់)"
            status_color = "#dc2626"
            result_text = f"{status} ✗" if status not in ("Dead", "Error") else "Login Failed ✗"
            result_color = "#ef4444"

        status_item = QTableWidgetItem(status_text)
        status_item.setTextAlignment(Qt.AlignCenter)
        status_item.setForeground(QColor(status_color))
        font = status_item.font()
        font.setBold(True)
        status_item.setFont(font)
        self.result_table.setItem(row, 1, status_item)

        result_item = QTableWidgetItem(result_text)
        result_item.setTextAlignment(Qt.AlignCenter)
        result_item.setForeground(QColor(result_color))
        self.result_table.setItem(row, 2, result_item)

        self._update_badges()

    def on_progress(self, current, total):
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)
        pct = int(current / total * 100) if total else 0
        self.pct_lbl.setText(f"{pct}%")
        self.status_lbl.setText(f"Checking — {current} / {total} accounts...")

    def on_log(self, message):
        pass

    def on_finished(self):
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self._update_badges()

        n_active = int(self._badge_active.text())
        n_dead   = int(self._badge_dead.text())
        total    = self.result_table.rowCount()
        self.pct_lbl.setText("100%")
        self.progress_bar.setValue(total)
        self.status_lbl.setText(f"Done ✅  — {total} accounts checked")

        if n_active >= n_dead:
            self.sum_active_lbl.setStyleSheet(
                "font-size: 13px; font-weight: 800; color: #059669; background: transparent;"
            )
        else:
            self.sum_dead_lbl.setStyleSheet(
                "font-size: 13px; font-weight: 800; color: #dc2626; background: transparent;"
            )

    def close_dialog(self):
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait(3000)
        self.accept()


# =============================================================================
# Post Media Manager Dialog — per-account Video & Image post management
# =============================================================================
class PostMediaManagerDialog(QDialog):
    """
    Full-featured popup for managing per-account post settings.
    Users can set individual photo/video paths, captions, target pages,
    and schedule for each Facebook account, then post all at once.
    """
    def __init__(self, parent_window, account_manager, config, is_dark_mode):
        super().__init__(parent_window)
        self.parent_window   = parent_window
        self.account_manager = account_manager
        self.config          = config
        self.is_dark_mode    = is_dark_mode
        self._account_rows   = {}   # username -> dict of widgets

        self.setWindowTitle("Post Video & Image Manager")
        self.resize(1160, 800)
        self.setMinimumSize(980, 680)

        # ── Theme tokens ──────────────────────────────────────────────────────
        dark        = is_dark_mode
        bg_main     = "#0f172a" if dark else "#f8fafc"
        bg_card     = "#1e293b" if dark else "#ffffff"
        bg_header   = "qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #0f172a,stop:1 #1e293b)" if dark else "qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #1e3a8a,stop:1 #3b82f6)"
        bg_sidebar  = "#0f172a" if dark else "#f8fafc"
        bg_toolbar  = "#1e293b" if dark else "#ffffff"
        bg_row      = "#1e293b" if dark else "#ffffff"
        bg_row_alt  = "#0f172a" if dark else "#f8fafc"
        bg_input    = "#0f172a" if dark else "#ffffff"
        border_c    = "#334155" if dark else "#cbd5e1"
        border_s    = "#475569" if dark else "#cbd5e1"
        text_main   = "#f8fafc" if dark else "#0f172a"
        text_sub    = "#94a3b8" if dark else "#475569"
        accent      = "#3b82f6"
        accent2     = "#2563eb"
        green       = "#10b981"

        # Apply dialog background
        self.setStyleSheet(
            parent_window.styleSheet() +
            f"\nQDialog {{ background: {bg_main}; }}"
        )

        # ── Root layout ────────────────────────────────────────────────────────
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ═══════════════════════════════════════════════════════
        # HEADER BANNER
        # ═══════════════════════════════════════════════════════
        header_frame = QFrame()
        header_frame.setFixedHeight(88)
        header_frame.setStyleSheet(f"QFrame {{ background: {bg_header}; border: none; }}")
        header_inner = QHBoxLayout(header_frame)
        header_inner.setContentsMargins(28, 0, 28, 0)
        header_inner.setSpacing(16)

        icon_lbl = QLabel("🎬")
        icon_lbl.setStyleSheet("font-size: 32px; background: transparent;")
        icon_lbl.setFixedWidth(44)

        title_col = QVBoxLayout()
        title_col.setSpacing(3)
        h_title = QLabel("Post Video & Image Manager")
        h_title.setStyleSheet("font-size: 20px; font-weight: 900; color: #ffffff; background: transparent; letter-spacing: 0.3px;")
        h_sub = QLabel("Manage per-account media posting — set different photos, videos, captions and pages for each account")
        h_sub.setStyleSheet("font-size: 11px; color: rgba(255,255,255,0.78); background: transparent;")
        title_col.addWidget(h_title)
        title_col.addWidget(h_sub)

        header_inner.addWidget(icon_lbl)
        header_inner.addLayout(title_col)
        header_inner.addStretch()

        # Stat badges in header
        self._badge_total   = self._make_header_badge("📋 Accounts", "0", "#60a5fa", header_inner)
        self._badge_enabled = self._make_header_badge("✅ Enabled",  "0", "#10b981", header_inner)
        self._badge_pages   = self._make_header_badge("📄 Pages",    "0", "#f59e0b", header_inner)

        root.addWidget(header_frame)

        # ═══════════════════════════════════════════════════════
        # TOOLBAR
        # ═══════════════════════════════════════════════════════
        toolbar = QFrame()
        toolbar.setFixedHeight(58)
        toolbar.setStyleSheet(
            f"QFrame {{ background: {bg_toolbar}; border: none; border-bottom: 2px solid {border_c}; }}"
        )
        tb_layout = QHBoxLayout(toolbar)
        tb_layout.setContentsMargins(16, 0, 16, 0)
        tb_layout.setSpacing(8)

        def _tb_lbl(txt):
            l = QLabel(txt)
            l.setStyleSheet(f"font-size: 12px; font-weight: 700; color: {text_sub}; background: transparent;")
            return l

        lbl_glob_cap = _tb_lbl("Global Caption:")
        self.global_caption_edit = QLineEdit()
        self.global_caption_edit.setPlaceholderText("Fill caption for all accounts at once…")
        self.global_caption_edit.setFixedHeight(32)
        self.global_caption_edit.setMaximumWidth(290)
        self.global_caption_edit.setStyleSheet(
            f"QLineEdit {{ background: {bg_input}; border: 1px solid {border_c};"
            f" border-radius: 8px; padding: 4px 10px; color: {text_main}; font-size: 12px; }}"
            f"QLineEdit:focus {{ border-color: {accent}; }}"
        )
        btn_fill_caption = QPushButton("▸ Fill All")
        btn_fill_caption.setFixedHeight(32)
        btn_fill_caption.setFixedWidth(78)
        btn_fill_caption.setCursor(Qt.PointingHandCursor)
        btn_fill_caption.setStyleSheet(
            f"QPushButton {{ background: {accent}; color: #fff; border: none;"
            f" border-radius: 8px; font-size: 12px; font-weight: 700; }}"
            f"QPushButton:hover {{ background: #1d4ed8; }}"
        )
        btn_fill_caption.clicked.connect(self._fill_all_captions)

        tb_layout.addWidget(lbl_glob_cap)
        tb_layout.addWidget(self.global_caption_edit)
        tb_layout.addWidget(btn_fill_caption)

        sep_v = QFrame(); sep_v.setFrameShape(QFrame.VLine)
        sep_v.setStyleSheet(f"background: {border_c}; max-width: 1px; border: none; margin: 10px 2px;")
        tb_layout.addWidget(sep_v)

        btn_enable_all = QPushButton("☑ Enable All")
        btn_enable_all.setFixedHeight(32)
        btn_enable_all.setCursor(Qt.PointingHandCursor)
        btn_enable_all.setStyleSheet(
            f"QPushButton {{ background: {green}; color: #fff; border: none;"
            f" border-radius: 8px; font-size: 12px; font-weight: 700; padding: 0 12px; }}"
            f"QPushButton:hover {{ background: #059669; }}"
        )
        btn_enable_all.clicked.connect(lambda: self._set_all_enabled(True))

        btn_disable_all = QPushButton("☐ Disable All")
        btn_disable_all.setFixedHeight(32)
        btn_disable_all.setCursor(Qt.PointingHandCursor)
        btn_disable_all.setStyleSheet(
            f"QPushButton {{ background: {'#1e293b' if dark else '#f1f5f9'}; color: {text_sub};"
            f" border: 1px solid {border_c}; border-radius: 8px;"
            f" font-size: 12px; font-weight: 700; padding: 0 12px; }}"
            f"QPushButton:hover {{ background: #ef4444; color: #fff; border-color: #ef4444; }}"
        )
        btn_disable_all.clicked.connect(lambda: self._set_all_enabled(False))

        tb_layout.addWidget(btn_enable_all)
        tb_layout.addWidget(btn_disable_all)
        tb_layout.addStretch()

        lbl_pt = _tb_lbl("Post Type:")
        self.post_type_combo = QComboBox()
        self.post_type_combo.addItems([
            "🖼️  Image Only", "🎬  Video Only",
            "🖼️+🎬  Image & Video", "📝  Text Only"
        ])
        self.post_type_combo.setFixedHeight(32)
        self.post_type_combo.setMinimumWidth(172)
        tb_layout.addWidget(lbl_pt)
        tb_layout.addWidget(self.post_type_combo)

        root.addWidget(toolbar)

        # ═══════════════════════════════════════════════════════
        # BODY — left sidebar + right table
        # ═══════════════════════════════════════════════════════
        body_splitter = QSplitter(Qt.Horizontal)
        body_splitter.setStyleSheet(
            f"QSplitter {{ background: {bg_main}; }}"
            f"QSplitter::handle {{ background: {border_c}; width: 2px; }}"
        )

        # ── LEFT SIDEBAR ──────────────────────────────────────
        sidebar_outer = QFrame()
        sidebar_outer.setFixedWidth(300)
        sidebar_outer.setStyleSheet(
            f"QFrame {{ background: {bg_sidebar}; border: none;"
            f" border-right: 2px solid {border_c}; }}"
        )
        sidebar_outer_v = QVBoxLayout(sidebar_outer)
        sidebar_outer_v.setContentsMargins(0, 0, 0, 0)
        sidebar_outer_v.setSpacing(0)

        sidebar_scroll = QScrollArea()
        sidebar_scroll.setWidgetResizable(True)
        sidebar_scroll.setFrameShape(QFrame.NoFrame)
        sidebar_scroll.setStyleSheet(
            f"QScrollArea {{ background: {bg_sidebar}; border: none; }}"
            f"QWidget#SidebarInner {{ background: {bg_sidebar}; }}"
        )

        sidebar_inner = QWidget()
        sidebar_inner.setObjectName("SidebarInner")
        sidebar_inner.setStyleSheet(f"background: {bg_sidebar};")
        sidebar_v = QVBoxLayout(sidebar_inner)
        sidebar_v.setContentsMargins(12, 12, 12, 12)
        sidebar_v.setSpacing(8)

        # helpers
        def _sec_hdr(txt, color=accent):
            w = QWidget()
            w.setStyleSheet("background: transparent;")
            hl = QHBoxLayout(w)
            hl.setContentsMargins(4, 6, 4, 6)
            hl.setSpacing(8)
            
            # Vertical line indicator
            ind = QFrame()
            ind.setFixedWidth(3)
            ind.setFixedHeight(14)
            ind.setStyleSheet(f"background-color: {color}; border-radius: 1.5px; border: none;")
            
            lbl = QLabel(txt)
            lbl.setStyleSheet(
                f"font-size: 11px; font-weight: 900; color: {color};"
                f" letter-spacing: 0.5px; background: transparent;"
            )
            
            hl.addWidget(ind)
            hl.addWidget(lbl, 1)
            return w

        def _slbl(txt):
            l = QLabel(txt)
            l.setStyleSheet(
                f"font-size: 11px; font-weight: 700; color: {text_sub}; background: transparent; margin-top: 4px;"
            )
            return l

        def _sinput(ph="", val=""):
            e = QLineEdit(val)
            e.setPlaceholderText(ph)
            e.setFixedHeight(32)
            e.setStyleSheet(
                f"QLineEdit {{ background: {bg_input}; border: 1px solid {border_c};"
                f" border-radius: 8px; padding: 4px 10px; color: {text_main}; font-size: 12px; }}"
                f"QLineEdit:focus {{ border-color: {accent}; }}"
            )
            return e

        def _sbrowse(line_edit, flt):
            btn = QPushButton("Browse")
            btn.setFixedHeight(32)
            btn.setMinimumWidth(80)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(
                f"QPushButton {{ background: {bg_card}; color: {text_sub}; border: 1px solid {border_c};"
                f" border-radius: 8px; font-size: 11px; font-weight: 700; }}"
                f"QPushButton:hover {{ background: #eff6ff; color: #2563eb; border-color: #3b82f6; }}"
                if not dark else
                f"QPushButton {{ background: {bg_card}; color: {text_sub}; border: 1px solid {border_c};"
                f" border-radius: 8px; font-size: 11px; font-weight: 700; }}"
                f"QPushButton:hover {{ background: #334155; color: #ffffff; border-color: #3b82f6; }}"
            )
            btn.clicked.connect(lambda: self._browse(line_edit, flt))
            row = QHBoxLayout()
            row.setSpacing(6); row.setContentsMargins(0, 0, 0, 0)
            row.addWidget(line_edit); row.addWidget(btn)
            return row

        def _ssep():
            s = QFrame(); s.setFrameShape(QFrame.HLine)
            s.setFixedHeight(1)
            s.setStyleSheet(f"background: {border_c}; border: none; margin: 4px 0;")
            return s

        # Section: Default Media
        sidebar_v.addWidget(_sec_hdr("🗂️  DEFAULT MEDIA"))
        sidebar_v.addWidget(_slbl("Default Image Path:"))
        self.def_photo_edit = _sinput("No image selected…", config.get("photo_path", ""))
        sidebar_v.addLayout(_sbrowse(self.def_photo_edit, "Images (*.png *.jpg *.jpeg *.gif *.webp)"))
        sidebar_v.addWidget(_slbl("Default Video Path:"))
        self.def_video_edit = _sinput("No video selected…", config.get("video_path", ""))
        sidebar_v.addLayout(_sbrowse(self.def_video_edit, "Videos (*.mp4 *.mov *.avi *.mkv)"))

        btn_apply_defaults = QPushButton("↓  Apply Defaults to All Accounts")
        btn_apply_defaults.setFixedHeight(34)
        btn_apply_defaults.setCursor(Qt.PointingHandCursor)
        btn_apply_defaults.setStyleSheet(
            f"QPushButton {{ background: {accent}; color: #fff; border: none;"
            f" border-radius: 8px; font-size: 12px; font-weight: 700; }}"
            f"QPushButton:hover {{ background: #1d4ed8; }}"
        )
        btn_apply_defaults.clicked.connect(self._apply_defaults_to_all)
        sidebar_v.addWidget(btn_apply_defaults)
        sidebar_v.addWidget(_ssep())

        # Section: Default Caption
        sidebar_v.addWidget(_sec_hdr("📝  DEFAULT CAPTION", "#10b981"))
        self.def_caption_edit = QTextEdit()
        self.def_caption_edit.setPlaceholderText("Default post caption / description…")
        self.def_caption_edit.setFixedHeight(90)
        self.def_caption_edit.setPlainText(config.get("post_caption", ""))
        self.def_caption_edit.setStyleSheet(
            f"QTextEdit {{ background: {bg_input}; border: 1px solid {border_c};"
            f" border-radius: 8px; padding: 6px 10px; color: {text_main}; font-size: 12px; }}"
            f"QTextEdit:focus {{ border-color: {accent}; }}"
        )
        sidebar_v.addWidget(self.def_caption_edit)
        sidebar_v.addWidget(_ssep())

        # Section: Schedule
        sidebar_v.addWidget(_sec_hdr("⏰  SCHEDULE", "#f59e0b"))
        sidebar_v.addWidget(_slbl("Post Delay — min to max (sec):"))
        delay_g_row = QHBoxLayout(); delay_g_row.setSpacing(6)
        self.g_delay_min = QSpinBox()
        self.g_delay_min.setRange(1, 600)
        self.g_delay_min.setValue(config.get("delay_min", 2))
        self.g_delay_min.setFixedHeight(32)
        self.g_delay_min.setMinimumWidth(80)
        self.g_delay_max = QSpinBox()
        self.g_delay_max.setRange(2, 1200)
        self.g_delay_max.setValue(config.get("delay_max", 5))
        self.g_delay_max.setFixedHeight(32)
        self.g_delay_max.setMinimumWidth(80)
        lbl_to = QLabel("–")
        lbl_to.setStyleSheet(f"color: {text_sub}; background: transparent; font-weight: 700;")
        lbl_to.setAlignment(Qt.AlignCenter)
        delay_g_row.addWidget(self.g_delay_min)
        delay_g_row.addWidget(lbl_to)
        delay_g_row.addWidget(self.g_delay_max)
        sidebar_v.addLayout(delay_g_row)
        sidebar_v.addWidget(_slbl("Interval between accounts (min):"))
        self.g_interval_spin = QSpinBox()
        self.g_interval_spin.setRange(0, 120); self.g_interval_spin.setValue(0)
        self.g_interval_spin.setFixedHeight(32)
        sidebar_v.addWidget(self.g_interval_spin)
        sidebar_v.addWidget(_ssep())

        # Section: Options
        sidebar_v.addWidget(_sec_hdr("⚙️  OPTIONS", text_sub))

        def _chkbox(txt, checked=False):
            c = QCheckBox(txt)
            c.setChecked(checked)
            c.setStyleSheet(
                f"QCheckBox {{ color: {text_main}; background: transparent; font-size: 12px; }}"
                f"QCheckBox::indicator {{ width: 16px; height: 16px; border-radius: 4px;"
                f" border: 1.5px solid {border_s}; background: {bg_input}; }}"
                f"QCheckBox::indicator:checked {{ background-color: {accent}; border-color: {accent};"
                f" image: url(data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCIgZmlsbD0ibm9uZSIgc3Ryb2tlPSJ3aGl0ZSIgc3Ryb2tlLXdpZHRoPSI0IiBzdHJva2UtbGluZWNhcD0icm91bmQiIHN0cm9rZS1saW5lam9pbj0icm91bmQiPjxwb2x5bGluZSBwb2ludHM9IjIwIDYgOSAxNyA0IDEyIj48L3BvbHlsaW5lPjwvc3ZnPg==); }}"
            )
            return c

        self.chk_headless      = _chkbox("🖥  Headless Mode", False)
        self.chk_auto_reaction = _chkbox("😊  Auto Random Reaction", config.get("random_reactions", False))
        self.chk_skip_posted   = _chkbox("⏭  Skip Already-Posted", True)
        sidebar_v.addWidget(self.chk_headless)
        sidebar_v.addWidget(self.chk_auto_reaction)
        sidebar_v.addWidget(self.chk_skip_posted)
        sidebar_v.addStretch()

        sidebar_scroll.setWidget(sidebar_inner)
        sidebar_outer_v.addWidget(sidebar_scroll)
        body_splitter.addWidget(sidebar_outer)

        # ── RIGHT PANEL ────────────────────────────────────────
        right_panel = QWidget()
        right_panel.setStyleSheet(f"background: {bg_main};")
        right_v = QVBoxLayout(right_panel)
        right_v.setContentsMargins(14, 12, 14, 8)
        right_v.setSpacing(10)

        # Table title + search
        tbl_hdr = QHBoxLayout()
        tbl_title_lbl = QLabel("🗂️  Per-Account Post Configuration")
        tbl_title_lbl.setStyleSheet(
            f"font-size: 14px; font-weight: 800; color: {text_main}; background: transparent;"
        )
        tbl_hdr.addWidget(tbl_title_lbl)
        tbl_hdr.addStretch()
        srch_icon = QLabel("🔍")
        srch_icon.setStyleSheet("background: transparent; font-size: 13px;")
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Filter by account name…")
        self.search_edit.setFixedHeight(32)
        self.search_edit.setMaximumWidth(210)
        self.search_edit.setStyleSheet(
            f"QLineEdit {{ background: {bg_input}; border: 1.5px solid {border_c};"
            f" border-radius: 8px; padding: 4px 10px; color: {text_main}; font-size: 12px; }}"
            f"QLineEdit:focus {{ border-color: {accent2}; }}"
        )
        self.search_edit.textChanged.connect(self._filter_table)
        tbl_hdr.addWidget(srch_icon)
        tbl_hdr.addWidget(self.search_edit)
        right_v.addLayout(tbl_hdr)

        # Accounts table
        self.acc_table = QTableWidget(0, 8)
        self.acc_table.setHorizontalHeaderLabels([
            "✓", "Account", "Image Path", "Video Path",
            "Caption", "Target Pages", "Status", "Action"
        ])
        hdr = self.acc_table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.Fixed);         self.acc_table.setColumnWidth(0, 35)
        hdr.setSectionResizeMode(1, QHeaderView.Interactive);   self.acc_table.setColumnWidth(1, 145)
        hdr.setSectionResizeMode(2, QHeaderView.Interactive);   self.acc_table.setColumnWidth(2, 165)
        hdr.setSectionResizeMode(3, QHeaderView.Interactive);   self.acc_table.setColumnWidth(3, 165)
        hdr.setSectionResizeMode(4, QHeaderView.Stretch)
        hdr.setSectionResizeMode(5, QHeaderView.Interactive);   self.acc_table.setColumnWidth(5, 135)
        hdr.setSectionResizeMode(6, QHeaderView.Fixed);         self.acc_table.setColumnWidth(6, 90)
        hdr.setSectionResizeMode(7, QHeaderView.Fixed);         self.acc_table.setColumnWidth(7, 76)

        self.acc_table.setAlternatingRowColors(True)
        self.acc_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.acc_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.acc_table.setShowGrid(False)
        self.acc_table.verticalHeader().setVisible(False)
        self.acc_table.setStyleSheet(
            f"QTableWidget {{ background: {bg_card}; border: 1px solid {border_c};"
            f" border-radius: 12px; gridline-color: transparent; outline: none; }}"
            f"QTableWidget::item {{ padding: 2px 4px; border: none; }}"
            f"QTableWidget::item:selected {{ background: {'#1e3a5f' if dark else '#dbeafe'};"
            f" color: {'#cbd5e1' if dark else '#1e40af'}; }}"
            f"QTableWidget::item:alternate {{ background: {bg_row_alt}; }}"
            f"QHeaderView::section {{ background-color: {'#0b0f19' if dark else '#f8fafc'};"
            f" color: {text_sub}; font-weight: 700; font-size: 11px; letter-spacing: 0.3px;"
            f" padding: 9px 6px; border: none; border-bottom: 2px solid {border_c}; }}"
        )
        right_v.addWidget(self.acc_table)

        # Status bar chip
        status_chip = QFrame()
        status_chip.setFixedHeight(26)
        status_chip.setStyleSheet(
            f"QFrame {{ background: {bg_toolbar}; border-radius: 6px; border: none; }}"
        )
        sc_lay = QHBoxLayout(status_chip)
        sc_lay.setContentsMargins(10, 0, 10, 0)
        self.status_bar_lbl = QLabel("Loading accounts…")
        self.status_bar_lbl.setStyleSheet(
            f"font-size: 11px; color: {text_sub}; background: transparent; font-weight: 600;"
        )
        sc_lay.addWidget(self.status_bar_lbl)
        sc_lay.addStretch()
        right_v.addWidget(status_chip)

        body_splitter.addWidget(right_panel)
        body_splitter.setSizes([300, 840])
        root.addWidget(body_splitter, 1)

        # ═══════════════════════════════════════════════════════
        # FOOTER
        # ═══════════════════════════════════════════════════════
        footer = QFrame()
        footer.setFixedHeight(62)
        footer.setStyleSheet(
            f"QFrame {{ background: {bg_card}; border-top: 2px solid {border_c}; }}"
        )
        footer_row = QHBoxLayout(footer)
        footer_row.setContentsMargins(20, 0, 20, 0)
        footer_row.setSpacing(10)

        self.lbl_footer_status = QLabel("Ready — configure accounts then press  🚀 Post.")
        self.lbl_footer_status.setStyleSheet(
            f"font-size: 12px; color: {text_sub}; background: transparent;"
        )
        footer_row.addWidget(self.lbl_footer_status)
        footer_row.addStretch()

        btn_save_cfg = QPushButton("💾  Save Config")
        btn_save_cfg.setFixedHeight(38)
        btn_save_cfg.setMinimumWidth(128)
        btn_save_cfg.setCursor(Qt.PointingHandCursor)
        btn_save_cfg.setStyleSheet(
            f"QPushButton {{ background: {'#1e293b' if dark else '#f1f5f9'}; color: {text_main};"
            f" border: 1.5px solid {border_c}; border-radius: 8px;"
            f" font-size: 13px; font-weight: 700; }}"
            f"QPushButton:hover {{ background: {'#334155' if dark else '#e2e8f0'}; }}"
        )
        btn_save_cfg.clicked.connect(self._save_config)

        self.btn_post_all = QPushButton("🚀  Post to All Enabled Accounts")
        self.btn_post_all.setFixedHeight(38)
        self.btn_post_all.setMinimumWidth(236)
        self.btn_post_all.setCursor(Qt.PointingHandCursor)
        self.btn_post_all.setStyleSheet(
            f"QPushButton {{ background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            f"stop:0 {accent},stop:1 {accent2}); color: #fff; border: none;"
            f" border-radius: 8px; font-size: 13px; font-weight: 800; }}"
            f"QPushButton:hover {{ background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            f"stop:0 #6d28d9,stop:1 #1d4ed8); }}"
            f"QPushButton:disabled {{ background: {'#263352' if dark else '#cbd5e1'};"
            f" color: {'#475569' if dark else '#94a3b8'}; }}"
        )
        self.btn_post_all.clicked.connect(self._post_all_enabled)

        btn_close = QPushButton("✕  Close")
        btn_close.setFixedHeight(38)
        btn_close.setMinimumWidth(88)
        btn_close.setCursor(Qt.PointingHandCursor)
        btn_close.setStyleSheet(
            f"QPushButton {{ background: {'#1e293b' if dark else '#f1f5f9'}; color: {text_sub};"
            f" border: 1.5px solid {border_c}; border-radius: 8px;"
            f" font-size: 13px; font-weight: 700; }}"
            f"QPushButton:hover {{ background: #ef4444; color: #fff; border-color: #ef4444; }}"
        )
        btn_close.clicked.connect(self.close)

        footer_row.addWidget(btn_save_cfg)
        footer_row.addWidget(self.btn_post_all)
        footer_row.addWidget(btn_close)
        root.addWidget(footer)

        # ── Populate table ────────────────────────────────────
        self._populate_table()

    # ──────────────────────────────────────────────────────────
    # Helpers
    # ──────────────────────────────────────────────────────────
    def _make_header_badge(self, label_text, count_text, color, parent_layout):
        frame = QFrame()
        frame.setFrameShape(QFrame.NoFrame)
        frame.setFixedSize(110, 58)
        frame.setStyleSheet(
            "QFrame { background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.15);"
            " border-radius: 10px; }"
        )
        fl = QVBoxLayout(frame)
        fl.setContentsMargins(8, 6, 8, 6)
        fl.setSpacing(2)
        lbl = QLabel(label_text)
        lbl.setStyleSheet("font-size: 10px; color: rgba(255,255,255,0.8); background: transparent; font-weight: 700; border: none;")
        lbl.setAlignment(Qt.AlignCenter)
        val = QLabel(count_text)
        val.setStyleSheet(f"font-size: 17px; font-weight: 900; color: {color}; background: transparent; border: none;")
        val.setAlignment(Qt.AlignCenter)
        fl.addWidget(lbl)
        fl.addWidget(val)
        parent_layout.addWidget(frame)
        return val

    def _update_status_badge(self, badge, status):
        """Update status badge text and apply premium pill styles dynamically."""
        dark = self.is_dark_mode
        status = status.lower().strip()
        
        if "idle" in status:
            badge.setText("⏸  Idle")
            bg = "#334155" if dark else "#e2e8f0"
            fg = "#cbd5e1" if dark else "#475569"
        elif "queued" in status or "queue" in status:
            badge.setText("⏳  Queued")
            bg = "#1e3a8a" if dark else "#dbeafe"
            fg = "#60a5fa" if dark else "#1e40af"
        elif "posting" in status or "running" in status:
            badge.setText("🔄  Posting…")
            bg = "#78350f" if dark else "#fef3c7"
            fg = "#f59e0b" if dark else "#b45309"
        elif "done" in status or "active" in status or "success" in status:
            badge.setText("✅  Done")
            bg = "#064e3b" if dark else "#d1fae5"
            fg = "#34d399" if dark else "#065f46"
        elif "failed" in status or "dead" in status or "error" in status:
            badge.setText("❌  Failed")
            bg = "#7f1d1d" if dark else "#fee2e2"
            fg = "#f87171" if dark else "#991b1b"
        else:
            badge.setText(status.upper())
            bg = "#1e293b" if dark else "#f1f5f9"
            fg = "#94a3b8" if dark else "#64748b"

        badge.setStyleSheet(
            f"QLabel {{ background-color: {bg}; color: {fg}; border-radius: 10px; "
            f"padding: 4px 10px; font-size: 11px; font-weight: 800; border: none; }}"
        )

    def _browse(self, line_edit, file_filter):
        path, _ = QFileDialog.getOpenFileName(self, "Select File", "", file_filter)
        if path:
            line_edit.setText(path)

    def _populate_table(self):
        """Build one table row per account with inline controls."""
        dark       = self.is_dark_mode
        text_sub   = "#7a93b8" if dark else "#5a6f8f"
        text_main  = "#e8edf7" if dark else "#1a2540"
        border_c   = "#263352" if dark else "#d4ddf0"
        bg_input   = "#0d1526" if dark else "#ffffff"
        accent     = "#7c3aed"
        accent2    = "#2563eb"
        green      = "#10b981"

        # Load per-account saved settings
        post_settings_file = "post_settings.json"
        saved_settings = {}
        if os.path.exists(post_settings_file):
            try:
                with open(post_settings_file, "r", encoding="utf-8") as f:
                    saved_settings = json.load(f)
            except Exception:
                pass

        accounts = self.account_manager.accounts
        self.acc_table.setRowCount(0)
        self._account_rows.clear()

        # Inline field helper
        def _field(ph, val="", focus_color=accent):
            e = QLineEdit(val)
            e.setPlaceholderText(ph)
            e.setFixedHeight(28)
            e.setStyleSheet(
                f"QLineEdit {{ background: {bg_input}; border: 1.5px solid {border_c};"
                f" border-radius: 6px; padding: 3px 7px; color: {text_main}; font-size: 11px; }}"
                f"QLineEdit:focus {{ border-color: {focus_color}; }}"
            )
            return e

        # Cell widget wrapper
        def _cell(layout):
            w = QWidget()
            w.setLayout(layout)
            return w

        for i, acc in enumerate(accounts):
            row = self.acc_table.rowCount()
            self.acc_table.insertRow(row)
            self.acc_table.setRowHeight(row, 54) # Row height 54 for modern spacious layout

            # Col 0 — Checkbox
            chk = QCheckBox()
            chk.setChecked(True)
            chk.setStyleSheet(
                f"QCheckBox {{ margin-left: 10px; }}"
                f"QCheckBox::indicator {{ width: 16px; height: 16px; border-radius: 4px;"
                f" border: 1.5px solid {border_c}; background: {bg_input}; }}"
                f"QCheckBox::indicator:checked {{ background-color: {accent}; border-color: {accent};"
                f" image: url(data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCIgZmlsbD0ibm9uZSIgc3Ryb2tlPSJ3aGl0ZSIgc3Ryb2tlLXdpZHRoPSI0IiBzdHJva2UtbGluZWNhcD0icm91bmQiIHN0cm9rZS1saW5lam9pbj0icm91bmQiPjxwb2x5bGluZSBwb2ludHM9IjIwIDYgOSAxNyA0IDEyIj48L3BvbHlsaW5lPjwvc3ZnPg==); }}"
            )
            chk.stateChanged.connect(self._refresh_badges)
            chk_l = QHBoxLayout(); chk_l.setContentsMargins(0,0,0,0); chk_l.setAlignment(Qt.AlignCenter)
            chk_l.addWidget(chk)
            self.acc_table.setCellWidget(row, 0, _cell(chk_l))

            # Col 1 — Account name
            acc_item = QTableWidgetItem(f"  {acc.username}")
            acc_item.setForeground(QColor(text_main))
            font = acc_item.font(); font.setBold(True); acc_item.setFont(font)
            self.acc_table.setItem(row, 1, acc_item)

            # Retrieve saved or fallback default configurations for this account
            acc_data = saved_settings.get(acc.username, {})
            img_val = acc_data.get("photo_path", self.def_photo_edit.text())
            vid_val = acc_data.get("video_path", self.def_video_edit.text())
            cap_val = acc_data.get("post_caption", self.def_caption_edit.toPlainText())
            pages_val = acc_data.get("target_pages", "")

            # Col 2 — Image path
            img_edit = _field("Image path…", img_val, accent)
            img_btn  = QPushButton("📷")
            img_btn.setToolTip("Browse Image")
            img_btn.setFixedHeight(28)
            img_btn.setFixedWidth(36)
            img_btn.setCursor(Qt.PointingHandCursor)
            img_btn.setStyleSheet(
                f"QPushButton {{ background: #2e1065; color: #c084fc; border: 1px solid #4c1d95; border-radius: 6px; font-size: 12px; font-weight: 800; }}"
                f"QPushButton:hover {{ background: #7c3aed; color: #ffffff; border-color: #7c3aed; }}"
                if dark else
                f"QPushButton {{ background: #ede9fe; color: #6d28d9; border: 1px solid #ddd6fe; border-radius: 6px; font-size: 12px; font-weight: 800; }}"
                f"QPushButton:hover {{ background: #7c3aed; color: #ffffff; border-color: #7c3aed; }}"
            )
            img_btn.clicked.connect(lambda _, e=img_edit: self._browse(e, "Images (*.png *.jpg *.jpeg *.gif *.webp)"))
            img_l = QHBoxLayout(); img_l.setContentsMargins(6,0,6,0); img_l.setSpacing(6); img_l.setAlignment(Qt.AlignVCenter)
            img_l.addWidget(img_edit); img_l.addWidget(img_btn)
            self.acc_table.setCellWidget(row, 2, _cell(img_l))

            # Col 3 — Video path
            vid_edit = _field("Video path…", vid_val, accent2)
            vid_btn  = QPushButton("🎥")
            vid_btn.setToolTip("Browse Video")
            vid_btn.setFixedHeight(28)
            vid_btn.setFixedWidth(36)
            vid_btn.setCursor(Qt.PointingHandCursor)
            vid_btn.setStyleSheet(
                f"QPushButton {{ background: #172554; color: #60a5fa; border: 1px solid #1e3a8a; border-radius: 6px; font-size: 12px; font-weight: 800; }}"
                f"QPushButton:hover {{ background: #2563eb; color: #ffffff; border-color: #2563eb; }}"
                if dark else
                f"QPushButton {{ background: #dbeafe; color: #1d4ed8; border: 1px solid #bfdbfe; border-radius: 6px; font-size: 12px; font-weight: 800; }}"
                f"QPushButton:hover {{ background: #2563eb; color: #ffffff; border-color: #2563eb; }}"
            )
            vid_btn.clicked.connect(lambda _, e=vid_edit: self._browse(e, "Videos (*.mp4 *.mov *.avi *.mkv)"))
            vid_l = QHBoxLayout(); vid_l.setContentsMargins(6,0,6,0); vid_l.setSpacing(6); vid_l.setAlignment(Qt.AlignVCenter)
            vid_l.addWidget(vid_edit); vid_l.addWidget(vid_btn)
            self.acc_table.setCellWidget(row, 3, _cell(vid_l))

            # Col 4 — Caption
            cap_edit = _field("Caption…", cap_val, "#10b981")
            cap_l = QHBoxLayout(); cap_l.setContentsMargins(6,0,6,0); cap_l.setAlignment(Qt.AlignVCenter)
            cap_l.addWidget(cap_edit)
            self.acc_table.setCellWidget(row, 4, _cell(cap_l))

            # Col 5 — Target Pages
            pages_edit = _field("page_url1, page_url2…", pages_val, "#f59e0b")
            pages_l = QHBoxLayout(); pages_l.setContentsMargins(6,0,6,0); pages_l.setAlignment(Qt.AlignVCenter)
            pages_l.addWidget(pages_edit)
            self.acc_table.setCellWidget(row, 5, _cell(pages_l))

            # Col 6 — Status badge
            status_badge = QLabel()
            self._update_status_badge(status_badge, "idle")
            status_badge.setAlignment(Qt.AlignCenter)
            status_l = QHBoxLayout(); status_l.setContentsMargins(0,0,0,0); status_l.setAlignment(Qt.AlignCenter)
            status_l.addWidget(status_badge)
            self.acc_table.setCellWidget(row, 6, _cell(status_l))

            # Col 7 — Row action button (Post this account only)
            btn_post_row = QPushButton("▶ Post")
            btn_post_row.setFixedHeight(28)
            btn_post_row.setCursor(Qt.PointingHandCursor)
            btn_post_row.setStyleSheet(
                f"QPushButton {{ background: {green}; color: #fff; border: none;"
                f" border-radius: 6px; font-size: 11px; font-weight: 700; padding: 0 10px; }}"
                f"QPushButton:hover {{ background: #059669; }}"
                f"QPushButton:disabled {{ background: {'#263352' if dark else '#cbd5e1'};"
                f" color: {'#475569' if dark else '#94a3b8'}; }}"
            )
            btn_post_row.clicked.connect(lambda _, u=acc.username, sb=status_badge: self._post_single(u, sb))
            btn_row_l = QHBoxLayout(); btn_row_l.setContentsMargins(6,0,6,0); btn_row_l.setAlignment(Qt.AlignCenter)
            btn_row_l.addWidget(btn_post_row)
            self.acc_table.setCellWidget(row, 7, _cell(btn_row_l))

            # Save references
            self._account_rows[acc.username] = {
                "checkbox": chk,
                "img_edit": img_edit,
                "vid_edit": vid_edit,
                "cap_edit": cap_edit,
                "pages_edit": pages_edit,
                "status_badge": status_badge,
                "row_index": row,
            }

        self._refresh_badges()

    def _refresh_badges(self):
        total   = len(self._account_rows)
        enabled = sum(1 for d in self._account_rows.values() if d["checkbox"].isChecked())
        pages   = sum(
            1 for d in self._account_rows.values()
            if d["pages_edit"].text().strip()
        )
        self._badge_total.setText(str(total))
        self._badge_enabled.setText(str(enabled))
        self._badge_pages.setText(str(pages))
        self.status_bar_lbl.setText(
            f"Total: {total} accounts  •  Enabled: {enabled}  •  With custom pages: {pages}"
        )

    def _filter_table(self, text):
        text = text.lower().strip()
        for row in range(self.acc_table.rowCount()):
            item = self.acc_table.item(row, 1)
            if item:
                self.acc_table.setRowHidden(row, text not in item.text().lower())

    def _fill_all_captions(self):
        txt = self.global_caption_edit.text().strip()
        if not txt:
            return
        for d in self._account_rows.values():
            d["cap_edit"].setText(txt)

    def _set_all_enabled(self, state: bool):
        for d in self._account_rows.values():
            d["checkbox"].setChecked(state)

    def _apply_defaults_to_all(self):
        img = self.def_photo_edit.text()
        vid = self.def_video_edit.text()
        cap = self.def_caption_edit.toPlainText()
        for d in self._account_rows.values():
            d["img_edit"].setText(img)
            d["vid_edit"].setText(vid)
            d["cap_edit"].setText(cap)

    def _post_single(self, username: str, status_badge: QLabel):
        """Placeholder — triggers posting for a single account."""
        self._update_status_badge(status_badge, "posting")
        QMessageBox.information(
            self, "Post Started",
            f"Starting post for account:\n{username}\n\n"
            "(Connect this to your automation backend to execute the actual post.)"
        )
        self._update_status_badge(status_badge, "success")

    def _post_all_enabled(self):
        """Collect enabled accounts and trigger posting."""
        enabled = [
            (uname, d) for uname, d in self._account_rows.items()
            if d["checkbox"].isChecked()
        ]
        if not enabled:
            QMessageBox.warning(self, "No Accounts", "Please enable at least one account.")
            return

        # Build payload summary
        lines = []
        for uname, d in enabled:
            img  = d["img_edit"].text().strip() or "(default)"
            vid  = d["vid_edit"].text().strip() or "(default)"
            cap  = d["cap_edit"].text().strip()[:40] or "(empty)"
            pages = d["pages_edit"].text().strip() or "(global targets)"
            lines.append(f"• {uname}\n  📷 {img}\n  🎬 {vid}\n  📝 {cap}\n  📄 {pages}")

        # Update status badges to "Queued"
        for _, d in enabled:
            self._update_status_badge(d["status_badge"], "queued")

        self.lbl_footer_status.setText(f"🚀 Posting queued for {len(enabled)} account(s)…")

        QMessageBox.information(
            self, f"Post Queued — {len(enabled)} Accounts",
            "The following accounts are queued for posting:\n\n" +
            "\n\n".join(lines[:10]) +
            ("\n\n…and more" if len(lines) > 10 else "") +
            "\n\n(Connect this dialog's payload to your automation backend to run.)"
        )

    def _save_config(self):
        """Save global defaults and per-account settings."""
        if hasattr(self.parent_window, 'config'):
            self.parent_window.config["photo_path"]       = self.def_photo_edit.text()
            self.parent_window.config["video_path"]       = self.def_video_edit.text()
            self.parent_window.config["post_caption"]     = self.def_caption_edit.toPlainText()
            self.parent_window.config["delay_min"]        = self.g_delay_min.value()
            self.parent_window.config["delay_max"]        = self.g_delay_max.value()
            self.parent_window.config["random_reactions"] = self.chk_auto_reaction.isChecked()
            self.parent_window.save_config()

        # Save per-account settings from the table
        post_settings_file = "post_settings.json"
        current_settings = {}
        for username, widgets in self._account_rows.items():
            current_settings[username] = {
                "photo_path": widgets["img_edit"].text(),
                "video_path": widgets["vid_edit"].text(),
                "post_caption": widgets["cap_edit"].text(),
                "target_pages": widgets["pages_edit"].text()
            }
        try:
            with open(post_settings_file, "w", encoding="utf-8") as f:
                json.dump(current_settings, f, indent=4, ensure_ascii=False)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save per-account settings: {str(e)}")
            return

        QMessageBox.information(self, "Saved", "Global post configuration and per-account settings saved successfully.")


class AccountDetailsDialog(QDialog):
    def __init__(self, title, username="", password="", two_fa="", proxy="", category="All", parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(400, 500)
        if parent:
            self.setStyleSheet(parent.styleSheet())
        else:
            self.setStyleSheet(LIGHT_THEME_STYLE)
        
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(12)
        
        # Header Label
        header_label = QLabel(title.upper())
        header_label.setStyleSheet("font-size: 15px; font-weight: 800; color: #1877f2; margin-bottom: 4px;")
        main_layout.addWidget(header_label)
        
        # Divider Line
        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        divider.setFrameShadow(QFrame.Sunken)
        divider.setStyleSheet("background-color: #e4e6eb; max-height: 1px; border: none;")
        main_layout.addWidget(divider)
        main_layout.addSpacing(6)
        
        # Form Layout
        form_layout = QVBoxLayout()
        form_layout.setSpacing(8)
        
        # Username Field
        lbl_user = QLabel("Username / Email")
        lbl_user.setStyleSheet("font-weight: 600; color: #606770; font-size: 12px;")
        self.username_input = QLineEdit(username)
        self.username_input.setPlaceholderText("Enter Facebook email or phone number")
        form_layout.addWidget(lbl_user)
        form_layout.addWidget(self.username_input)
        
        # Password Field
        lbl_pass = QLabel("Password")
        lbl_pass.setStyleSheet("font-weight: 600; color: #606770; font-size: 12px;")
        self.password_input = QLineEdit(password)
        self.password_input.setPlaceholderText("Enter account password")
        self.password_input.setEchoMode(QLineEdit.Password)  # Secure password entry
        form_layout.addWidget(lbl_pass)
        form_layout.addWidget(self.password_input)
        
        # 2FA Key Field
        lbl_2fa = QLabel("2FA Secret Key (Optional)")
        lbl_2fa.setStyleSheet("font-weight: 600; color: #606770; font-size: 12px;")
        self.two_fa_input = QLineEdit(two_fa)
        self.two_fa_input.setPlaceholderText("Enter 16-character 2FA secret key")
        form_layout.addWidget(lbl_2fa)
        form_layout.addWidget(self.two_fa_input)
        
        # Proxy Field
        lbl_proxy = QLabel("Proxy Configuration (Optional)")
        lbl_proxy.setStyleSheet("font-weight: 600; color: #606770; font-size: 12px;")
        self.proxy_input = QLineEdit(proxy)
        self.proxy_input.setPlaceholderText("host:port or host:port:user:pass")
        form_layout.addWidget(lbl_proxy)
        form_layout.addWidget(self.proxy_input)
        
        # Category Field
        lbl_category = QLabel("Category")
        lbl_category.setStyleSheet("font-weight: 600; color: #606770; font-size: 12px;")
        self.category_input = QComboBox()
        self.category_input.setEditable(False)
        # Populate with existing categories
        if parent and hasattr(parent, 'account_manager'):
            categories = parent.account_manager.get_categories()
            self.category_input.addItems(categories)
        self.category_input.setCurrentText(category if category else "All")
        form_layout.addWidget(lbl_category)
        form_layout.addWidget(self.category_input)
        
        main_layout.addLayout(form_layout)
        main_layout.addSpacing(10)
        
        # Custom Action Buttons Layout
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setCursor(Qt.PointingHandCursor)
        self.cancel_btn.clicked.connect(self.reject)
        
        self.ok_btn = QPushButton("Save Details" if "Edit" in title else "Add Account")
        self.ok_btn.setObjectName("PrimaryButton")  # Styles it blue
        self.ok_btn.setCursor(Qt.PointingHandCursor)
        self.ok_btn.clicked.connect(self.accept)
        
        btn_layout.addStretch()
        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addWidget(self.ok_btn)
        main_layout.addLayout(btn_layout)

    def get_data(self):
        return (
            self.username_input.text().strip(),
            self.password_input.text().strip(),
            self.two_fa_input.text().strip(),
            self.proxy_input.text().strip(),
            self.category_input.currentText().strip() or "All"
        )

class PasteAccountsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Paste Accounts")
        self.setFixedSize(700, 500)
        if parent:
            self.setStyleSheet(parent.styleSheet())
        else:
            self.setStyleSheet(LIGHT_THEME_STYLE)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)
        
        # Header Label
        header_label = QLabel("PASTE ACCOUNTS")
        header_label.setStyleSheet("font-size: 15px; font-weight: 800; color: #1877f2; margin-bottom: 4px;")
        layout.addWidget(header_label)
        
        # Divider Line
        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        divider.setFrameShadow(QFrame.Sunken)
        divider.setStyleSheet("background-color: #e4e6eb; max-height: 1px; border: none;")
        layout.addWidget(divider)
        layout.addSpacing(6)
        lbl_info = QLabel("Format: username|password|2fa_secret|proxy (One account per line, 2FA/proxy optional)")
        lbl_info.setStyleSheet("font-weight: 600; color: #606770; font-size: 12px;")
        layout.addWidget(lbl_info)
        
        self.text_area = QTextEdit()
        self.text_area.setPlaceholderText("example1@gmail.com|pass123|2FASECRET123|192.168.1.1:8080\nexample2@gmail.com|pass456\nexample3@gmail.com|pass789||192.168.1.1:8080 (without 2FA)\nexample4@gmail.com|pass999")
        layout.addWidget(self.text_area)
        
        # ── Category Section ────────────────────────────────────
        layout.addSpacing(6)
        cat_row = QHBoxLayout()
        cat_row.setSpacing(8)
        lbl_category = QLabel("Category:")
        lbl_category.setStyleSheet("font-weight: 600; color: #606770; font-size: 12px;")
        lbl_category.setFixedWidth(70)

        self.category_input = QComboBox()
        self.category_input.setEditable(False)
        self.category_input.setMinimumWidth(200)
        self.category_input.setMinimumHeight(32)
        self._parent_ref = parent  # keep reference for refresh
        self._refresh_categories()

        new_cat_btn = QPushButton("+ New")
        new_cat_btn.setFixedHeight(32)
        new_cat_btn.setFixedWidth(60)
        new_cat_btn.setCursor(Qt.PointingHandCursor)
        new_cat_btn.setStyleSheet(
            "QPushButton { background:#3b82f6; color:white; border:none; border-radius:6px; font-weight:700; font-size:12px; }"
            "QPushButton:hover { background:#2563eb; }"
        )
        new_cat_btn.clicked.connect(self._create_new_category)

        cat_row.addWidget(lbl_category)
        cat_row.addWidget(self.category_input, 1)
        cat_row.addWidget(new_cat_btn)
        layout.addLayout(cat_row)
        
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setCursor(Qt.PointingHandCursor)
        self.cancel_btn.clicked.connect(self.reject)
        
        self.add_btn = QPushButton("Add Accounts")
        self.add_btn.setObjectName("PrimaryButton")
        self.add_btn.setCursor(Qt.PointingHandCursor)
        self.add_btn.clicked.connect(self.accept)
        
        btn_layout.addStretch()
        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addWidget(self.add_btn)
        layout.addLayout(btn_layout)

    def _refresh_categories(self):
        """Reload categories from AccountManager into the dropdown."""
        current_text = self.category_input.currentText()
        self.category_input.blockSignals(True)
        self.category_input.clear()
        if self._parent_ref and hasattr(self._parent_ref, 'account_manager'):
            cats = self._parent_ref.account_manager.get_categories()
        else:
            cats = ["All"]
        self.category_input.addItems(cats)
        if current_text in cats:
            self.category_input.setCurrentText(current_text)
        else:
            self.category_input.setCurrentIndex(0)
        self.category_input.blockSignals(False)

    def _create_new_category(self):
        """Prompt user to type a new category name and add it."""
        from PySide6.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(self, "New Category", "Enter new category name:")
        if ok and name.strip():
            name = name.strip()
            if self._parent_ref and hasattr(self._parent_ref, 'account_manager'):
                self._parent_ref.account_manager.add_category(name)
            self._refresh_categories()
            self.category_input.setCurrentText(name)

    def get_text(self):
        return self.text_area.toPlainText()

    def get_category(self):
        return self.category_input.currentText().strip() or "All"

class ModernSuccessDialog(QDialog):
    def __init__(self, title, message, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(400, 220)
        
        if parent:
            self.setStyleSheet(parent.styleSheet())
        else:
            self.setStyleSheet(LIGHT_THEME_STYLE)
            
        is_dark = parent and getattr(parent, 'is_dark_mode', False)
        bg_color = "#18181b" if is_dark else "#ffffff"
        text_color = "#f8fafc" if is_dark else "#1c1e21"
        desc_color = "#94a3b8" if is_dark else "#606770"
        icon_bg = "#14532d" if is_dark else "#e7f8ec"
        icon_fg = "#4ade80" if is_dark else "#2b851a"
        
        self.setStyleSheet(self.styleSheet() + f"\nQDialog {{ background-color: {bg_color}; }}")
        
        # Remove context help button from title bar
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 25, 30, 25)
        layout.setSpacing(16)
        
        # Center layout
        content_layout = QVBoxLayout()
        content_layout.setAlignment(Qt.AlignCenter)
        content_layout.setSpacing(12)
        
        # Premium Checkmark Icon
        self.icon_label = QLabel("✓")
        self.icon_label.setStyleSheet(f"""
            background-color: {icon_bg};
            color: {icon_fg};
            font-size: 26px;
            font-weight: bold;
            border-radius: 26px;
            min-width: 52px;
            min-height: 52px;
            max-width: 52px;
            max-height: 52px;
            border: none;
        """)
        self.icon_label.setAlignment(Qt.AlignCenter)
        content_layout.addWidget(self.icon_label, alignment=Qt.AlignCenter)
        
        # Title Label
        self.title_label = QLabel(title)
        self.title_label.setStyleSheet(f"font-size: 16px; font-weight: 700; color: {text_color};")
        self.title_label.setAlignment(Qt.AlignCenter)
        content_layout.addWidget(self.title_label)
        
        # Message Label
        self.msg_label = QLabel(message)
        self.msg_label.setStyleSheet(f"font-size: 13px; color: {desc_color}; line-height: 1.5; font-weight: 500;")
        self.msg_label.setWordWrap(True)
        self.msg_label.setAlignment(Qt.AlignCenter)
        content_layout.addWidget(self.msg_label)
        
        layout.addLayout(content_layout)
        
        # OK Button
        btn_layout = QHBoxLayout()
        self.ok_btn = QPushButton("OK")
        self.ok_btn.setObjectName("PrimaryButton")
        self.ok_btn.setCursor(Qt.PointingHandCursor)
        self.ok_btn.setMinimumWidth(120)
        self.ok_btn.setStyleSheet("padding: 8px 24px; font-size: 13px; font-weight: 700;")
        self.ok_btn.clicked.connect(self.accept)
        
        btn_layout.addStretch()
        btn_layout.addWidget(self.ok_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

class GitUpdateDialog(QDialog):
    def __init__(self, release_notes, current_version="v2.0.0", new_version="New", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Software Update")
        self.resize(500, 400)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        
        is_dark = parent and getattr(parent, 'is_dark_mode', False)
        bg_color = "#ffffff" if not is_dark else "#18181b"
        text_color = "#1c1e21" if not is_dark else "#f8fafc"
        border_color = "#e4e6eb" if not is_dark else "#27272a"
        note_bg = "#f8f9fa" if not is_dark else "#27272a"
        
        self.setStyleSheet(f"QDialog {{ background-color: {bg_color}; }} QLabel {{ color: {text_color}; }}")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(15)
        
        header_layout = QHBoxLayout()
        icon_label = QLabel("⬆️")
        icon_label.setStyleSheet("font-size: 28px; background: #fff3e0; border-radius: 12px; padding: 10px; margin-right: 10px;")
        
        title_layout = QVBoxLayout()
        lbl_subtitle = QLabel("SOFTWARE UPDATE")
        lbl_subtitle.setStyleSheet("color: #f59e0b; font-size: 11px; font-weight: bold; letter-spacing: 1px;")
        lbl_title = QLabel("New Version Available")
        lbl_title.setStyleSheet("font-size: 20px; font-weight: 800;")
        title_layout.addWidget(lbl_subtitle)
        title_layout.addWidget(lbl_title)
        title_layout.setSpacing(2)
        
        header_layout.addWidget(icon_label)
        header_layout.addLayout(title_layout)
        header_layout.addStretch()
        layout.addLayout(header_layout)
        
        ver_layout = QHBoxLayout()
        ver_layout.setAlignment(Qt.AlignCenter)
        lbl_v1 = QLabel(f"📦 {current_version}")
        lbl_v1.setStyleSheet(f"background: {note_bg}; border: 1px solid {border_color}; border-radius: 12px; padding: 6px 16px; font-size: 13px; font-weight: bold;")
        
        lbl_arrow = QLabel("   >>   ")
        lbl_arrow.setStyleSheet("color: #f59e0b; font-weight: bold; font-size: 14px;")
        
        lbl_v2 = QLabel(f"✨ {new_version}")
        lbl_v2.setStyleSheet("background: #fffbeb; color: #b45309; border: 1px solid #fde68a; border-radius: 12px; padding: 6px 16px; font-size: 13px; font-weight: bold;")
        
        ver_layout.addWidget(lbl_v1)
        ver_layout.addWidget(lbl_arrow)
        ver_layout.addWidget(lbl_v2)
        layout.addLayout(ver_layout)
        layout.addSpacing(10)
        
        notes_frame = QFrame()
        notes_frame.setStyleSheet(f"background: {note_bg}; border: 1px solid {border_color}; border-radius: 12px;")
        notes_layout = QVBoxLayout(notes_frame)
        notes_layout.setContentsMargins(15, 15, 15, 15)
        
        lbl_notes_title = QLabel("📄 RELEASE NOTES")
        lbl_notes_title.setStyleSheet("font-size: 11px; font-weight: bold; color: #64748b; margin-bottom: 5px;")
        notes_layout.addWidget(lbl_notes_title)
        
        div = QFrame()
        div.setFrameShape(QFrame.HLine)
        div.setStyleSheet(f"background: {border_color}; max-height: 1px; border: none;")
        notes_layout.addWidget(div)
        
        # Limit to 5-6 lines visually or let it wrap naturally
        notes_text = "\n".join(release_notes.split("\n")[:8])
        if len(release_notes.split("\n")) > 8:
            notes_text += "\n- And more updates..."
            
        lbl_notes = QLabel(notes_text)
        lbl_notes.setWordWrap(True)
        lbl_notes.setStyleSheet(f"font-size: 13px; line-height: 1.5; font-weight: 600; margin-top: 10px; color: {text_color};")
        notes_layout.addWidget(lbl_notes)
        layout.addWidget(notes_frame)
        
        layout.addStretch()
        
        btn_layout = QHBoxLayout()
        self.btn_later = QPushButton("Maybe Later")
        self.btn_later.setCursor(Qt.PointingHandCursor)
        self.btn_later.setStyleSheet(f"border: 1px solid {border_color}; color: {text_color}; border-radius: 8px; padding: 10px 20px; font-size: 13px; font-weight: bold; background: transparent;")
        self.btn_later.clicked.connect(self.reject)
        
        self.btn_download = QPushButton("☁️ Download & Install")
        self.btn_download.setCursor(Qt.PointingHandCursor)
        self.btn_download.setStyleSheet("background-color: #f59e0b; color: white; border: none; border-radius: 8px; padding: 10px 20px; font-size: 13px; font-weight: bold;")
        self.btn_download.clicked.connect(self.accept)
        
        btn_layout.addWidget(self.btn_later)
        btn_layout.addWidget(self.btn_download)
        layout.addLayout(btn_layout)

class SettingsDialog(QDialog):
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings Configuration")
        self.resize(520, 430)
        if parent:
            self.setStyleSheet(parent.styleSheet())
        else:
            self.setStyleSheet(LIGHT_THEME_STYLE)
        
        # Remove context help button from title bar
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        
        self.config = config.copy()
        
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(12)
        
        # Tab Widget
        self.tabs = QTabWidget()
        
        # --- Tab 1: Facebook Config ---
        tab_fb = QWidget()
        fb_layout = QFormLayout(tab_fb)
        fb_layout.setSpacing(10)
        fb_layout.setContentsMargins(10, 10, 10, 10)
        
        lbl_load_to = QLabel("Page Load Timeout (sec):")
        lbl_load_to.setObjectName("FormLabel")
        self.load_to_spin = QSpinBox()
        self.load_to_spin.setRange(5, 180)
        self.load_to_spin.setValue(self.config.get("page_load_timeout", 30))
        fb_layout.addRow(lbl_load_to, self.load_to_spin)
        
        lbl_wait_to = QLabel("Element Wait Timeout (sec):")
        lbl_wait_to.setObjectName("FormLabel")
        self.wait_to_spin = QSpinBox()
        self.wait_to_spin.setRange(1, 60)
        self.wait_to_spin.setValue(self.config.get("wait_timeout", 10))
        fb_layout.addRow(lbl_wait_to, self.wait_to_spin)
        
        lbl_retries = QLabel("Max Login Retries:")
        lbl_retries.setObjectName("FormLabel")
        self.retries_spin = QSpinBox()
        self.retries_spin.setRange(0, 5)
        self.retries_spin.setValue(self.config.get("max_login_retries", 2))
        fb_layout.addRow(lbl_retries, self.retries_spin)
        
        lbl_ua = QLabel("Custom User-Agent:")
        lbl_ua.setObjectName("FormLabel")
        self.ua_input = QLineEdit(self.config.get("custom_user_agent", ""))
        self.ua_input.setPlaceholderText("Leave blank for default mobile emulation")
        fb_layout.addRow(lbl_ua, self.ua_input)
        
        lbl_lang = QLabel("Chrome Language/Locale:")
        lbl_lang.setObjectName("FormLabel")
        self.lang_combo = QComboBox()
        self.lang_combo.addItems(["Auto", "English (en)", "Khmer (km)", "Vietnamese (vi)"])
        self.lang_combo.setCurrentText(self.config.get("locale_lang", "Auto"))
        fb_layout.addRow(lbl_lang, self.lang_combo)
        
        lbl_api = QLabel("API Key:")
        lbl_api.setObjectName("FormLabel")
        self.api_input = QLineEdit(self.config.get("api_key", "AIzaSyBu0aZfd464GEOnAl4aZDpEPrhogWohga8"))
        self.api_input.setPlaceholderText("Enter API Key")
        fb_layout.addRow(lbl_api, self.api_input)
        
        self.tabs.addTab(tab_fb, "Facebook Automation")
        
        # (Custom XPaths tab removed as requested)
        
        # --- Tab 3: Backup & Storage ---
        tab_backup = QWidget()
        backup_layout = QFormLayout(tab_backup)
        backup_layout.setSpacing(10)
        backup_layout.setContentsMargins(10, 10, 10, 10)
        
        self.backup_check = QCheckBox("Enable Account Auto-Backup")
        self.backup_check.setChecked(self.config.get("auto_backup_enabled", True))
        backup_layout.addRow(self.backup_check)
        
        lbl_dir = QLabel("Backup Directory:")
        lbl_dir.setObjectName("FormLabel")
        self.dir_input = QLineEdit(self.config.get("backup_dir", "backups"))
        
        dir_box = QHBoxLayout()
        dir_box.addWidget(self.dir_input)
        self.browse_btn = QPushButton("Browse")
        self.browse_btn.clicked.connect(self.browse_backup_dir)
        self.browse_btn.setCursor(Qt.PointingHandCursor)
        dir_box.addWidget(self.browse_btn)
        backup_layout.addRow(lbl_dir, dir_box)
        
        lbl_last = QLabel("Last Backup Date:")
        lbl_last.setObjectName("FormLabel")
        self.lbl_last_val = QLabel(self.config.get("last_backup_date", "Never"))
        self.lbl_last_val.setStyleSheet("color: #64748b; font-weight: 600;")
        backup_layout.addRow(lbl_last, self.lbl_last_val)
        
        self.backup_now_btn = QPushButton("Backup Now")
        self.backup_now_btn.setObjectName("PrimaryButton")
        self.backup_now_btn.setCursor(Qt.PointingHandCursor)
        self.backup_now_btn.clicked.connect(self.run_manual_backup)
        backup_layout.addRow(self.backup_now_btn)
        
        self.tabs.addTab(tab_backup, "Backup & Storage")
        
        # --- Tab 3: Version & About ---
        tab_about = QWidget()
        about_layout = QVBoxLayout(tab_about)
        about_layout.setSpacing(12)
        about_layout.setContentsMargins(15, 15, 15, 15)
        about_layout.setAlignment(Qt.AlignCenter)
        
        lbl_app_title = QLabel("Facebook Auto-Login & Invite Master")
        lbl_app_title.setStyleSheet("font-size: 16px; font-weight: 800; color: #3b82f6;")
        lbl_app_title.setAlignment(Qt.AlignCenter)
        
        lbl_ver = QLabel("Version 2.0.0 (Stable Release)")
        lbl_ver.setStyleSheet("font-size: 13px; font-weight: 600; color: #10b981;")
        lbl_ver.setAlignment(Qt.AlignCenter)
        
        lbl_desc = QLabel("An automated bulk page invitation tool utilizing Selenium.\nOptimized for security, user simulation, and speed.")
        lbl_desc.setStyleSheet("color: #64748b; font-size: 12px; line-height: 1.4;")
        lbl_desc.setAlignment(Qt.AlignCenter)
        lbl_desc.setWordWrap(True)
        
        self.update_btn = QPushButton("Check for Updates")
        self.update_btn.setCursor(Qt.PointingHandCursor)
        self.update_btn.clicked.connect(self.check_for_updates)
        
        about_layout.addWidget(lbl_app_title)
        about_layout.addWidget(lbl_ver)
        about_layout.addWidget(lbl_desc)
        about_layout.addSpacing(10)
        about_layout.addWidget(self.update_btn, alignment=Qt.AlignCenter)
        
        self.tabs.addTab(tab_about, "About / Version")
        
        main_layout.addWidget(self.tabs)
        
        # Dialog buttons
        btn_layout = QHBoxLayout()
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setCursor(Qt.PointingHandCursor)
        self.cancel_btn.clicked.connect(self.reject)
        
        self.save_btn = QPushButton("Save Settings")
        self.save_btn.setObjectName("PrimaryButton")
        self.save_btn.setCursor(Qt.PointingHandCursor)
        self.save_btn.clicked.connect(self.save_and_accept)
        
        btn_layout.addStretch()
        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addWidget(self.save_btn)
        main_layout.addLayout(btn_layout)

    def browse_backup_dir(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Select Backup Directory", self.dir_input.text())
        if dir_path:
            self.dir_input.setText(dir_path)

    def run_manual_backup(self):
        parent = self.parent()
        if parent and hasattr(parent, 'perform_backup'):
            backup_file = parent.perform_backup(self.dir_input.text())
            if backup_file:
                now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self.lbl_last_val.setText(now_str)
                self.config["last_backup_date"] = now_str
                QMessageBox.information(self, "Backup Complete", f"Accounts successfully backed up to:\n{backup_file}")
            else:
                QMessageBox.critical(self, "Backup Failed", "Unable to create backup. Please verify your accounts list.")

    def check_for_updates(self):
        self.update_btn.setEnabled(False)
        self.update_btn.setText("Checking...")
        import threading
        
        def run_update():
            import subprocess
            try:
                # Fetch latest commits from remote
                CREATE_NO_WINDOW = subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                subprocess.run(["git", "fetch", "origin", "main"], capture_output=True, check=True, creationflags=CREATE_NO_WINDOW)
                
                # Check what commits are new
                result = subprocess.run(["git", "log", "HEAD..origin/main", "--pretty=format:- %s"], capture_output=True, text=True, creationflags=CREATE_NO_WINDOW)
                
                if result.stdout.strip():
                    msg = result.stdout.strip()
                    status = "update_available"
                else:
                    msg = "You are running the latest version.\nNo updates available."
                    status = "info"
            except Exception as e:
                msg = f"Failed to check for updates.\nMake sure git is installed and configured.\nError: {str(e)}"
                status = "error"
            
            # Update UI from main thread using QTimer
            from PySide6.QtCore import QTimer
            QTimer.singleShot(0, lambda: self.handle_update_check_result(msg, status))

        threading.Thread(target=run_update, daemon=True).start()

    def handle_update_check_result(self, msg, status):
        self.update_btn.setEnabled(True)
        self.update_btn.setText("Check for Updates")
        
        if status == "error":
            QMessageBox.critical(self, "Update Error", msg)
        elif status == "info":
            QMessageBox.information(self, "Software Update", msg)
        elif status == "update_available":
            dialog = GitUpdateDialog(release_notes=msg, current_version="v2.0.0", new_version="v2.x", parent=self)
            if dialog.exec() == QDialog.Accepted:
                self.do_git_pull()

    def do_git_pull(self):
        self.update_btn.setEnabled(False)
        self.update_btn.setText("Downloading...")
        import threading
        
        def pull_worker():
            import subprocess
            try:
                CREATE_NO_WINDOW = subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                subprocess.run(["git", "pull", "origin", "main"], capture_output=True, check=True, creationflags=CREATE_NO_WINDOW)
                status = "success"
                msg = "Update downloaded successfully!\nPlease restart the application to apply changes."
            except Exception as e:
                status = "error"
                msg = f"Failed to pull updates.\nError: {str(e)}"
            
            from PySide6.QtCore import QTimer
            QTimer.singleShot(0, lambda: self.update_check_done(msg, status))

        threading.Thread(target=pull_worker, daemon=True).start()

    def update_check_done(self, message, status):
        self.update_btn.setEnabled(True)
        self.update_btn.setText("Check for Updates")
        if status == "error":
            QMessageBox.critical(self, "Update Error", message)
        elif status == "success":
            QMessageBox.information(self, "Update Successful", message)
        else:
            QMessageBox.information(self, "Software Update", message)

    def save_and_accept(self):
        self.config["page_load_timeout"] = self.load_to_spin.value()
        self.config["wait_timeout"] = self.wait_to_spin.value()
        self.config["max_login_retries"] = self.retries_spin.value()
        self.config["custom_user_agent"] = self.ua_input.text().strip()
        self.config["locale_lang"] = self.lang_combo.currentText()
        self.config["api_key"] = self.api_input.text().strip()
        self.config["auto_backup_enabled"] = self.backup_check.isChecked()
        self.config["backup_dir"] = self.dir_input.text().strip()
        # XPaths are no longer editable in UI
        self.accept()

    def get_config(self):
        return self.config

class DashboardWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.current_status = "SYSTEM IDLE"
        self.setWindowTitle("Facebook Auto-Login & Invite Master v2.0.0")
        self.setFixedSize(1652, 903)
        
        self.is_dark_mode = False
        self.load_config()
        
        # Apply theme stylesheet based on loaded config
        if self.config.get("theme_mode", "light") == "dark":
            self.is_dark_mode = True
            self.setStyleSheet(DARK_THEME_STYLE)
        else:
            self.is_dark_mode = False
            self.setStyleSheet(LIGHT_THEME_STYLE)
        
        self.account_manager = AccountManager()
        self.account_manager.load_all_from_history() # Restore saved accounts
        self.workers = {}          # username -> worker instance
        self.pending_queue = []    # list of accounts to process
        self.max_threads = 2
        
        # Stats counters
        self.stats = {
            "total": 0,
            "running": 0,
            "success": 0,
            "failed": 0,
            "sent": 0,
            "inv_failed": 0
        }
        
        self.init_ui()
        self.refresh_table()
        self.update_stats_ui()
        
        # Perform auto-backup if enabled on startup
        if self.config.get("auto_backup_enabled", True):
            self.perform_backup()
 
    def load_config(self):
        self.config_file = "config.json"
        self.default_config = {
            "theme_mode": "light",
            "page_load_timeout": 30,
            "wait_timeout": 10,
            "max_login_retries": 2,
            "custom_user_agent": "",
            "locale_lang": "Auto",
            "api_key": "AIzaSyBu0aZfd464GEOnAl4aZDpEPrhogWohga8",
            "auto_backup_enabled": True,
            "backup_dir": "backups",
            "last_backup_date": "Never",
            "xpath_email": "//input[@name='email']",
            "xpath_pass": "//input[@name='pass']",
            "xpath_login_btn": "//button[@name='login']",
            "xpath_invite_btn": "//button[contains(.,'Invite')] | //span[text()='Invite'] | //div[text()='Invite']",
            "tasks": ["login"],
            "invite_links": [],
            "group_keyword": "Shopping",
            "post_caption": "",
            "photo_path": "",
            "video_path": "",
            "random_reactions": False,
            "feed_mins": 5,
            "video_feed_mins": 5,
            "story_count": 5,
            "invite_count": 25,
            "add_friend_count": 10,
            "confirm_friend_count": 50,
            "join_group_count": 3,
            "share_group_count": 3,
            "scrape_limit": 100
        }
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
                for key, val in self.default_config.items():
                    if key not in self.config:
                        self.config[key] = val
            except Exception as e:
                self.config = self.default_config.copy()
        else:
            self.config = self.default_config.copy()
            self.save_config()
            
        # Apply API key to core automation
        set_api_key(self.config.get("api_key", "AIzaSyBu0aZfd464GEOnAl4aZDpEPrhogWohga8"))

    def save_config(self):
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
        except Exception as e:
            self.append_log("System", "ERROR", f"Failed to save settings: {str(e)}")

    def perform_backup(self, custom_dir=None):
        backup_dir = custom_dir if custom_dir else self.config.get("backup_dir", "backups")
        if not os.path.exists(backup_dir):
            try:
                os.makedirs(backup_dir, exist_ok=True)
            except Exception as e:
                self.append_log("System", "ERROR", f"Failed to create backup directory: {str(e)}")
                return None
        
        now_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"accounts_backup_{now_str}.json"
        backup_filepath = os.path.join(backup_dir, backup_filename)
        
        try:
            accounts_data = [acc.to_dict() for acc in self.account_manager.accounts]
            with open(backup_filepath, 'w', encoding='utf-8') as f:
                json.dump(accounts_data, f, indent=4, ensure_ascii=False)
            
            # Save history dict too
            history_data = self.account_manager.load_history_dict()
            if history_data:
                history_backup_filepath = os.path.join(backup_dir, f"history_backup_{now_str}.json")
                with open(history_backup_filepath, 'w', encoding='utf-8') as f:
                    json.dump(history_data, f, indent=4, ensure_ascii=False)

            last_backup_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.config["last_backup_date"] = last_backup_str
            self.save_config()
            
            self.append_log("System", "SUCCESS", f"Auto-backup complete: {backup_filename}")
            return backup_filepath
        except Exception as e:
            self.append_log("System", "ERROR", f"Failed to perform auto-backup: {str(e)}")
            return None

    def show_settings_dialog(self):
        dialog = SettingsDialog(self.config, self)
        if dialog.exec() == QDialog.Accepted:
            self.config = dialog.get_config()
            self.save_config()
            
            # Apply API Key changes
            set_api_key(self.config.get("api_key", "AIzaSyBu0aZfd464GEOnAl4aZDpEPrhogWohga8"))
            
            self.append_log("System", "SUCCESS", "Settings saved and applied successfully.")

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)

        # ----------------- Header Section -----------------
        header_frame = QFrame()
        header_frame.setObjectName("HeaderFrame")
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(15, 10, 15, 10)
        
        title_label = QLabel("FACEBOOK AUTO-LOGIN & INVITE DASHBOARD")
        title_label.setObjectName("AppTitle")
        
        subtitle = QLabel("Mobile Format Simulation • PyQt6 & Selenium Engine • Version 2.0.0")
        subtitle.setStyleSheet("color: rgba(255, 255, 255, 0.8); font-size: 11px; font-weight: 500;")
        
        title_box = QVBoxLayout()
        title_box.addWidget(title_label)
        title_box.addWidget(subtitle)
        header_layout.addLayout(title_box)
        header_layout.addStretch()
        
        # Settings Button
        self.settings_btn = QPushButton("⚙️ Settings")
        self.settings_btn.setObjectName("SettingsButton")
        self.settings_btn.setCursor(Qt.PointingHandCursor)
        self.settings_btn.clicked.connect(self.show_settings_dialog)
        header_layout.addWidget(self.settings_btn)
        
        # Theme Toggle Button
        theme_txt = "☀️ Light Mode" if self.is_dark_mode else "🌙 Dark Mode"
        self.theme_btn = QPushButton(theme_txt)
        self.theme_btn.setObjectName("ThemeButton")
        self.theme_btn.setCursor(Qt.PointingHandCursor)
        self.theme_btn.clicked.connect(self.toggle_theme)
        header_layout.addWidget(self.theme_btn)

        # Auto-Update Button
        self.update_btn = QPushButton("🔄 Update")
        self.update_btn.setObjectName("ThemeButton")
        self.update_btn.setCursor(Qt.PointingHandCursor)
        self.update_btn.setToolTip(f"Check for updates  (Current: {get_local_version()})")
        self.update_btn.clicked.connect(self.open_update_dialog)
        header_layout.addWidget(self.update_btn)
        
        # Set initial status in window title
        self.update_global_status_label_style("SYSTEM IDLE")
        
        main_layout.addWidget(header_frame)

        # ----------------- Stats Counters Panel -----------------
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(10)
        
        self.stat_cards = {}
        labels = [
            ("Total Accounts", "total", "#1c1e21"),
            ("Active Sessions", "running", "#1877f2"),
            ("Login Success", "success", "#2b851a"),
            ("Login Dead/Failed", "failed", "#c71f3b"),
            ("Invites Sent", "sent", "#2b851a"),
            ("Invites Failed", "inv_failed", "#b8860b")
        ]
        
        for text, key, color in labels:
            card = QFrame()
            card.setObjectName(f"StatCard_{key}")
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(10, 10, 10, 10)
            
            lbl = QLabel(text)
            lbl.setObjectName("StatLabel")
            
            val = QLabel("0")
            val.setObjectName("StatValue")
            val.setStyleSheet(f"color: {color};")
            
            card_layout.addWidget(lbl)
            card_layout.addWidget(val)
            stats_layout.addWidget(card)
            
            self.stat_cards[key] = val
            
        main_layout.addLayout(stats_layout)

        # ----------------- Splitted Main Area -----------------
        splitter = QSplitter(Qt.Horizontal)
        splitter.setStyleSheet("QSplitter::handle { background-color: #232333; width: 2px; }")
        
        # 1. Configuration Panel (Left side) wrapped in a ScrollArea for 100% responsiveness
        config_scroll = QScrollArea()
        config_scroll.setWidgetResizable(True)
        config_scroll.setFrameShape(QFrame.NoFrame)
        config_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        config_card = QFrame()
        config_card.setObjectName("ConfigCardFrame")
        config_layout = QVBoxLayout(config_card)
        config_layout.setContentsMargins(15, 15, 15, 15)
        config_layout.setSpacing(16)
        
        cfg_header = QLabel("Automation Settings")
        cfg_header.setObjectName("SectionHeader")
        config_layout.addWidget(cfg_header)
        
        # Create QTabWidget for left panel settings
        self.sidebar_tabs = QTabWidget()
        
        # --- TAB 1: Tasks ---
        tab_tasks = QWidget()
        tab_tasks.setObjectName("TabTasks")
        tasks_layout = QVBoxLayout(tab_tasks)
        tasks_layout.setContentsMargins(10, 10, 10, 10)
        tasks_layout.setSpacing(10)
        
        # Wrap Tasks inside a scroll area so it is 100% responsive and scrollable!
        tasks_scroll = QScrollArea()
        tasks_scroll.setWidgetResizable(True)
        tasks_scroll.setFrameShape(QFrame.NoFrame)
        tasks_container = QWidget()
        tasks_container.setObjectName("TasksContainer")
        tasks_container_layout = QVBoxLayout(tasks_container)
        tasks_container_layout.setSpacing(12)
        tasks_container_layout.setContentsMargins(0, 0, 0, 0)
        
        # 1. Engagement Tasks Group Box
        group_engagement = QGroupBox("Engagement Options")
        layout_eng = QGridLayout(group_engagement)
        layout_eng.setSpacing(8)
        
        # 2. Growth Tasks Group Box
        group_growth = QGroupBox("Growth Options")
        layout_grw = QGridLayout(group_growth)
        layout_grw.setSpacing(8)
        
        # 3. Content & Scraping Tasks Group Box
        group_content = QGroupBox("Content & Utility")
        layout_cnt = QGridLayout(group_content)
        layout_cnt.setSpacing(8)

        # Spinboxes for task limits / options
        self.spin_feed_mins = QSpinBox(); self.spin_feed_mins.setRange(1, 240); self.spin_feed_mins.setValue(self.config.get("feed_mins", 5))
        self.spin_video_mins = QSpinBox(); self.spin_video_mins.setRange(1, 240); self.spin_video_mins.setValue(self.config.get("video_feed_mins", 5))
        self.spin_story = QSpinBox(); self.spin_story.setRange(1, 500); self.spin_story.setValue(self.config.get("story_count", 5))
        
        self.spin_invite = QSpinBox(); self.spin_invite.setRange(1, 500); self.spin_invite.setValue(self.config.get("invite_count", 25))
        self.spin_add_friend = QSpinBox(); self.spin_add_friend.setRange(1, 500); self.spin_add_friend.setValue(self.config.get("add_friend_count", 10))
        self.spin_confirm = QSpinBox(); self.spin_confirm.setRange(1, 1000); self.spin_confirm.setValue(self.config.get("confirm_friend_count", 50))
        self.spin_join_group = QSpinBox(); self.spin_join_group.setRange(1, 100); self.spin_join_group.setValue(self.config.get("join_group_count", 3))
        
        self.spin_share_group = QSpinBox(); self.spin_share_group.setRange(1, 100); self.spin_share_group.setValue(self.config.get("share_group_count", 3))
        self.spin_scrape_limit = QSpinBox(); self.spin_scrape_limit.setRange(10, 5000); self.spin_scrape_limit.setValue(self.config.get("scrape_limit", 100))
        
        for sb in [self.spin_feed_mins, self.spin_video_mins, self.spin_story, self.spin_invite, 
                   self.spin_add_friend, self.spin_confirm, self.spin_join_group, self.spin_share_group, self.spin_scrape_limit]:
            sb.setFixedSize(85, 28)
            sb.setAlignment(Qt.AlignCenter)

        # Create Task Checkboxes
        self.tasks_checkboxes = {
            "login": QCheckBox("🔑 Login & Run"),
            "warmup": QCheckBox("🔥 Warm-Up"),
            "feeds": QCheckBox("📰 Scroll Feeds"),
            "watch_video": QCheckBox("📺 Watch Video"),
            "watch_stories": QCheckBox("👀 Story Viewer"),
            "invite": QCheckBox("📨 Invite Friends"),
            "add_friend": QCheckBox("👥 Add Friends"),
            "confirm_friend": QCheckBox("✅ Confirm All"),
            "join_groups": QCheckBox("🫂 Join Groups"),
            "share_groups": QCheckBox("🔄 Share Post"),
            "invite_like": QCheckBox("📡 Invite Like"),
            "post_photo": QCheckBox("📷 Post Photo"),
            "post_reel": QCheckBox("🎬 Post Reel"),
            "scrape_uids": QCheckBox("🧲 Scrape UIDs")
        }

        # Initialize checked tasks from config
        saved_tasks = self.config.get("tasks", ["login"])
        for task_name, cb in self.tasks_checkboxes.items():
            if task_name in saved_tasks:
                cb.setChecked(True)

        # Grid placement helper for layout lists
        task_grid_mapping = [
            (self.tasks_checkboxes["login"], None, "", layout_eng, 0),
            (self.tasks_checkboxes["warmup"], None, "", layout_eng, 1),
            (self.tasks_checkboxes["feeds"], self.spin_feed_mins, "m", layout_eng, 2),
            (self.tasks_checkboxes["watch_video"], self.spin_video_mins, "m", layout_eng, 3),
            (self.tasks_checkboxes["watch_stories"], self.spin_story, "ct", layout_eng, 4),
            
            (self.tasks_checkboxes["invite"], self.spin_invite, "ct", layout_grw, 0),
            (self.tasks_checkboxes["add_friend"], self.spin_add_friend, "ct", layout_grw, 1),
            (self.tasks_checkboxes["confirm_friend"], self.spin_confirm, "ct", layout_grw, 2),
            (self.tasks_checkboxes["join_groups"], self.spin_join_group, "ct", layout_grw, 3),
            
            (self.tasks_checkboxes["share_groups"], self.spin_share_group, "ct", layout_cnt, 0),
            (self.tasks_checkboxes["invite_like"], None, "", layout_cnt, 1),
            (self.tasks_checkboxes["post_photo"], None, "", layout_cnt, 2),
            (self.tasks_checkboxes["post_reel"], None, "", layout_cnt, 3),
            (self.tasks_checkboxes["scrape_uids"], self.spin_scrape_limit, "ct", layout_cnt, 4)
        ]

        for cb, sb, unit, grid, row in task_grid_mapping:
            grid.addWidget(cb, row, 0)
            if sb:
                grid.addWidget(sb, row, 1)
                if unit:
                    unit_lbl = QLabel(unit)
                    unit_lbl.setStyleSheet("font-size: 9px; opacity: 0.6;")
                    grid.addWidget(unit_lbl, row, 2)

        # Set column stretches so elements stay packed tightly to the left
        for layout in [layout_eng, layout_grw, layout_cnt]:
            layout.setColumnStretch(0, 0)
            layout.setColumnStretch(1, 0)
            layout.setColumnStretch(2, 0)
            layout.setColumnStretch(3, 1)

        tasks_container_layout.addWidget(group_engagement)
        tasks_container_layout.addWidget(group_growth)
        tasks_container_layout.addWidget(group_content)
        tasks_container_layout.addStretch()
        
        tasks_scroll.setWidget(tasks_container)
        tasks_layout.addWidget(tasks_scroll)
        self.sidebar_tabs.addTab(tab_tasks, "🤖 Tasks")
        
        # --- TAB 2: Config ---
        tab_config = QWidget()
        tab_config.setObjectName("TabConfig")
        config_tab_layout = QVBoxLayout(tab_config)
        config_tab_layout.setContentsMargins(10, 10, 10, 10)
        config_tab_layout.setSpacing(10)
        
        config_scroll_panel = QScrollArea()
        config_scroll_panel.setWidgetResizable(True)
        config_scroll_panel.setFrameShape(QFrame.NoFrame)
        config_scroll_container = QWidget()
        config_scroll_container.setObjectName("ConfigScrollContainer")
        config_scroll_layout = QVBoxLayout(config_scroll_container)
        config_scroll_layout.setSpacing(12)
        config_scroll_layout.setContentsMargins(0, 0, 0, 0)
        
        # Target URLs List Management
        group_targets = QGroupBox("🔗 Target List")
        targets_layout = QVBoxLayout(group_targets)
        
        self.target_list = QListWidget()
        self.target_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.target_list.setFixedHeight(100)
        self.target_list.setStyleSheet("border-radius: 4px;")
        
        target_btns = QHBoxLayout()
        self.btn_edit_targets = QPushButton("⚙️ Edit")
        self.btn_edit_targets.setCursor(Qt.PointingHandCursor)
        self.btn_edit_targets.clicked.connect(self.show_links_dialog)
        
        self.btn_del_targets = QPushButton("🗑️ Del")
        self.btn_del_targets.setCursor(Qt.PointingHandCursor)
        self.btn_del_targets.clicked.connect(self.delete_selected_targets)
        
        target_btns.addWidget(self.btn_edit_targets)
        target_btns.addWidget(self.btn_del_targets)
        
        targets_layout.addLayout(target_btns)
        targets_layout.addWidget(self.target_list)
        
        # Load targets to list
        self.refresh_target_combo()
        
        # Targeting & Action Section
        group_targeting = QGroupBox("⚙️ Targeting & Actions")
        targeting_form = QFormLayout(group_targeting)
        targeting_form.setSpacing(10)
        
        self.edit_kwd = QLineEdit(self.config.get("group_keyword", "Shopping"))
        self.chk_reaction = QCheckBox("Auto-Reaction (Random Reaction)")
        self.chk_reaction.setChecked(self.config.get("random_reactions", False))
        
        targeting_form.addRow(QLabel("Search Keyword:"), self.edit_kwd)
        targeting_form.addRow(self.chk_reaction)
        
        # Standard Browser Settings
        group_browser_settings = QGroupBox("🖥️ Browser Settings")
        browser_form = QFormLayout(group_browser_settings)
        browser_form.setSpacing(10)
        
        # Concurrent Threads
        self.thread_spin = QSpinBox()
        self.thread_spin.setRange(1, 10)
        self.thread_spin.setValue(self.max_threads)
        self.thread_spin.valueChanged.connect(self.update_max_threads)
        self.thread_spin.setFixedSize(85, 28)
        self.thread_spin.setAlignment(Qt.AlignCenter)
        browser_form.addRow(QLabel("Max Threads:"), self.thread_spin)
        
        # Run Mode / Execution Strategy
        self.run_mode_combo = QComboBox()
        self.run_mode_combo.addItems(["Run by Account", "Run by Task"])
        self.run_mode_combo.setCurrentText(self.config.get("run_mode", "Run by Account"))
        browser_form.addRow(QLabel("Execution Mode:"), self.run_mode_combo)
        
        # Mobile Device Emulation
        self.device_combo = QComboBox()
        self.device_combo.addItems(["Nexus 5", "iPhone X", "Pixel 5", "Galaxy S5", "None (Custom)"])
        browser_form.addRow(QLabel("Emulated Device:"), self.device_combo)
        
        # Browser Visibility Mode (Dropdown)
        self.browser_mode_combo = QComboBox()
        self.browser_mode_combo.addItems(["Visible Browser (Normal)", "Hidden Browser (Headless)"])
        browser_form.addRow(QLabel("Browser Visibility:"), self.browser_mode_combo)

        # Scrape Profile Info (Dropdown)
        self.scrape_profile_combo = QComboBox()
        self.scrape_profile_combo.addItems(["Enabled", "Disabled"])
        browser_form.addRow(QLabel("Profile Scraping:"), self.scrape_profile_combo)
        
        # Delay sliders
        self.delay_min = QSpinBox()
        self.delay_min.setRange(1, 60)
        self.delay_min.setValue(self.config.get("delay_min", 2))
        self.delay_min.setFixedSize(85, 28)
        self.delay_min.setAlignment(Qt.AlignCenter)
        
        self.delay_max = QSpinBox()
        self.delay_max.setRange(2, 120)
        self.delay_max.setValue(self.config.get("delay_max", 5))
        self.delay_max.setFixedSize(85, 28)
        self.delay_max.setAlignment(Qt.AlignCenter)
        
        delay_box = QHBoxLayout()
        delay_box.setSpacing(8)
        delay_box.addWidget(self.delay_min)
        delay_box.addWidget(QLabel("to"))
        delay_box.addWidget(self.delay_max)
        delay_box.addWidget(QLabel("sec"))
        browser_form.addRow(QLabel("Task Delay:"), delay_box)

        # Max invites per page
        self.max_invites_spin = QSpinBox()
        self.max_invites_spin.setRange(1, 1000)
        self.max_invites_spin.setValue(self.config.get("max_invites_per_page", 10))
        self.max_invites_spin.setFixedSize(85, 28)
        self.max_invites_spin.setAlignment(Qt.AlignCenter)
        browser_form.addRow(QLabel("Max Invites/Page:"), self.max_invites_spin)
        
        config_scroll_layout.addWidget(group_targets)
        config_scroll_layout.addWidget(group_targeting)
        config_scroll_layout.addWidget(group_browser_settings)
        config_scroll_layout.addStretch()
        
        config_scroll_panel.setWidget(config_scroll_container)
        config_tab_layout.addWidget(config_scroll_panel)
        self.sidebar_tabs.addTab(tab_config, "🎯 Config")
        
        # --- TAB 3: Post Video & Image ---
        tab_post_media = QWidget()
        tab_post_media.setObjectName("TabPostMedia")
        post_media_tab_layout = QVBoxLayout(tab_post_media)
        post_media_tab_layout.setContentsMargins(15, 20, 15, 20)
        post_media_tab_layout.setSpacing(18)

        # Centered info card
        info_card = QFrame()
        info_card.setObjectName("PostManagerInfoCard")
        info_card.setStyleSheet(
            f"QFrame#PostManagerInfoCard {{ "
            f"  background: {'#13203a' if self.is_dark_mode else '#f4f7fc'}; "
            f"  border: 1.5px solid {'#263352' if self.is_dark_mode else '#d4ddf0'}; "
            f"  border-radius: 12px; "
            f"  padding: 16px; "
            f"}}"
        )
        info_layout = QVBoxLayout(info_card)
        info_layout.setSpacing(12)

        info_title = QLabel("🎬  Multi-Account Auto Post Manager")
        info_title.setStyleSheet("font-size: 14px; font-weight: 800; color: #7c3aed;")
        info_layout.addWidget(info_title)

        info_desc = QLabel(
            "Configure, manage, and schedule video and image posts across multiple Facebook accounts "
            "simultaneously. Supports unique paths, captions, and pages per account, as well as global defaults."
        )
        info_desc.setWordWrap(True)
        info_desc.setStyleSheet(f"font-size: 11px; color: {'#7a93b8' if self.is_dark_mode else '#5a6f8f'}; line-height: 1.4;")
        info_layout.addWidget(info_desc)

        # ── Manage Post button (opens full PostMediaManagerDialog) ──
        self.btn_open_post_manager = QPushButton("📋  Manage Post & Scheduler")
        self.btn_open_post_manager.setObjectName("PostManagerButton")
        self.btn_open_post_manager.setMinimumHeight(44)
        self.btn_open_post_manager.setCursor(Qt.PointingHandCursor)
        self.btn_open_post_manager.setStyleSheet(
            "QPushButton { background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            "stop:0 #7c3aed,stop:1 #3b82f6); color: #ffffff; border: none;"
            " border-radius: 9px; font-size: 13px; font-weight: 800;"
            " letter-spacing: 0.2px; }"
            "QPushButton:hover { background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            "stop:0 #6d28d9,stop:1 #2563eb); }"
            "QPushButton:pressed { background: #4c1d95; }"
        )
        self.btn_open_post_manager.clicked.connect(self.open_post_media_manager)
        info_layout.addWidget(self.btn_open_post_manager)

        post_media_tab_layout.addWidget(info_card)

        # Features list
        feat_card = QFrame()
        feat_card.setStyleSheet("background: transparent; border: none;")
        feat_layout = QVBoxLayout(feat_card)
        feat_layout.setSpacing(6)
        feat_layout.setContentsMargins(4, 0, 4, 0)

        feat_hdr = QLabel("Core Features:")
        feat_hdr.setStyleSheet(f"font-size: 11px; font-weight: 700; color: {'#e8edf7' if self.is_dark_mode else '#1a2540'};")
        feat_layout.addWidget(feat_hdr)

        features = [
            "✅ Set individual Image/Video paths per account",
            "✅ Support for custom captions and Gemini AI captions",
            "✅ Map posts to account-specific target pages",
            "✅ Persistent configuration saves on closing",
            "✅ Human-like delays & random reactions during post"
        ]
        for f in features:
            f_lbl = QLabel(f)
            f_lbl.setStyleSheet(f"font-size: 11px; color: {'#7a93b8' if self.is_dark_mode else '#5a6f8f'};")
            feat_layout.addWidget(f_lbl)

        post_media_tab_layout.addWidget(feat_card)
        post_media_tab_layout.addStretch()

        self.sidebar_tabs.addTab(tab_post_media, "🎬 Post Video & Image")
        
        config_layout.addWidget(self.sidebar_tabs)
        
        # XPath Config loaded directly from user config settings
        
        # Execution controls
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        self.start_btn = QPushButton("START RUN")
        self.start_btn.setObjectName("SuccessButton")
        self.start_btn.setMinimumHeight(38)
        self.start_btn.setCursor(Qt.PointingHandCursor)
        self.start_btn.clicked.connect(self.start_automation)
        
        self.stop_btn = QPushButton("STOP RUN")
        self.stop_btn.setObjectName("DangerButton")
        self.stop_btn.setMinimumHeight(38)
        self.stop_btn.setCursor(Qt.PointingHandCursor)
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_automation)
        
        btn_layout.addWidget(self.start_btn)
        btn_layout.addWidget(self.stop_btn)
        config_layout.addLayout(btn_layout)
        
        # Add vertical stretch to prevent controls from stretching vertically
        config_layout.addStretch()
        
        config_scroll.setWidget(config_card)
        splitter.addWidget(config_scroll)
        
        # 2. Main View Table & Console Panel (Right side with resizable Splitter layout)
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)
        
        right_splitter = QSplitter(Qt.Vertical)
        right_splitter.setStyleSheet("QSplitter::handle { background-color: #dee2e6; height: 6px; }")
        
        # Accounts Table Card
        table_card = QFrame()
        table_card.setObjectName("TableCardFrame")
        table_layout = QVBoxLayout(table_card)
        table_layout.setContentsMargins(15, 15, 15, 15)
        table_layout.setSpacing(12)
        
        tbl_header_layout = QHBoxLayout()
        tbl_title = QLabel("Accounts Management")
        tbl_title.setObjectName("SectionHeader")
        tbl_header_layout.addWidget(tbl_title)
        
        # Category Filter Dropdown
        self.category_filter = QComboBox()
        self.category_filter.addItem("All Categories")
        self.category_filter.currentIndexChanged.connect(self.refresh_table)
        self.category_filter.setMinimumWidth(150)
        
        tbl_header_layout.addWidget(QLabel("  Filter:"))
        tbl_header_layout.addWidget(self.category_filter)

        # Manage Categories button
        self.manage_cat_btn = QPushButton("⚙ Categories")
        self.manage_cat_btn.setProperty("class", "TableHeaderButton")
        self.manage_cat_btn.setCursor(Qt.PointingHandCursor)
        self.manage_cat_btn.setToolTip("Create, Rename or Delete categories")
        self.manage_cat_btn.clicked.connect(self.open_manage_categories_dialog)
        tbl_header_layout.addWidget(self.manage_cat_btn)

        tbl_header_layout.addStretch()
        
        self.run_selected_btn = QPushButton("Run Selected")
        self.run_selected_btn.setProperty("class", "TableHeaderButton")
        self.run_selected_btn.setObjectName("Success")
        self.run_selected_btn.clicked.connect(self.start_selected_automation)
        self.run_selected_btn.setCursor(Qt.PointingHandCursor)
        
        self.add_acc_btn = QPushButton("Add Account")
        self.add_acc_btn.setProperty("class", "TableHeaderButton")
        self.add_acc_btn.clicked.connect(self.show_add_account_dialog)
        self.add_acc_btn.setCursor(Qt.PointingHandCursor)
        
        self.import_btn = QPushButton("Import TXT File")
        self.import_btn.setProperty("class", "TableHeaderButton")
        self.import_btn.clicked.connect(self.import_accounts_file)
        self.import_btn.setCursor(Qt.PointingHandCursor)
        
        self.clear_btn = QPushButton("Clear All")
        self.clear_btn.setProperty("class", "TableHeaderButton")
        self.clear_btn.setObjectName("Danger")
        self.clear_btn.clicked.connect(self.clear_accounts_table)
        self.clear_btn.setCursor(Qt.PointingHandCursor)
        


        
        tbl_header_layout.addWidget(self.run_selected_btn)
        tbl_header_layout.addWidget(self.add_acc_btn)
        tbl_header_layout.addWidget(self.import_btn)
        tbl_header_layout.addWidget(self.clear_btn)

        table_layout.addLayout(tbl_header_layout)
        
        # TableView setup for high performance
        self.account_table = QTableView()
        from ui.account_model import AccountTableModel
        self.account_model = AccountTableModel(self.account_manager.accounts, self)
        self.account_table.setModel(self.account_model)
        self.account_table.verticalHeader().setVisible(False)
        
        # Enforce Model Colors overriding PySide Stylesheet limits
        from PySide6.QtWidgets import QStyledItemDelegate
        from PySide6.QtGui import QPalette
        
        class ColorEnforcingDelegate(QStyledItemDelegate):
            def paint(self, painter, option, index):
                bg = index.data(Qt.BackgroundRole)
                if bg:
                    painter.fillRect(option.rect, bg)
                
                # Setup option for text rendering
                self.initStyleOption(option, index)
                fg = index.data(Qt.ForegroundRole)
                if fg:
                    option.palette.setBrush(QPalette.Text, fg)
                    option.palette.setBrush(QPalette.WindowText, fg)
                    option.palette.setBrush(QPalette.HighlightedText, fg)
                
                # Let Qt do the rest of the drawing (it won't overwrite our fillRect if transparent is set in stylesheet)
                super().paint(painter, option, index)
        
        self.account_table.setItemDelegate(ColorEnforcingDelegate(self.account_table))

        
        # Responsive header scaling
        header = self.account_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Interactive)
        header.setSectionResizeMode(2, QHeaderView.Stretch)  # Username
        header.setSectionResizeMode(3, QHeaderView.Stretch)  # Profile Name
        header.setSectionResizeMode(5, QHeaderView.Stretch)  # Password
        
        # Set initial column widths (all columns are drag-resizable with mouse)
        self.account_table.setColumnWidth(0, 40)   # No.
        self.account_table.setColumnWidth(1, 120)  # Category
        self.account_table.setColumnWidth(2, 160)  # Username
        self.account_table.setColumnWidth(3, 130)  # Profile Name
        self.account_table.setColumnWidth(4, 95)   # Friend Count
        self.account_table.setColumnWidth(5, 140)  # Password
        self.account_table.setColumnWidth(6, 80)   # Cookies
        self.account_table.setColumnWidth(7, 120)  # Status
        self.account_table.setColumnWidth(8, 65)   # Sent
        self.account_table.setColumnWidth(9, 65)   # Failed
        
        # Enable custom context menu and row selection via mouse
        self.account_table.setSelectionBehavior(QTableView.SelectRows)
        self.account_table.setSelectionMode(QTableView.ExtendedSelection)
        self.account_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.account_table.customContextMenuRequested.connect(self.show_context_menu)
        # self.account_table.setAlternatingRowColors(True)
        self.account_table.setStyleSheet("border-radius: 4px;")
        table_layout.addWidget(self.account_table)
        
        right_splitter.addWidget(table_card)
        
        # Initialize log_console in memory so append_log doesn't crash, 
        # but do not add it to the UI layout.
        self.log_console = QTextEdit()
        
        right_layout.addWidget(right_splitter)
        
        splitter.addWidget(right_container)
        
        # Set proportions: Left (Config) = 35%, Right (Table/Console) = 65%
        splitter.setSizes([420, 780])
        main_layout.addWidget(splitter)

    # ----------------- UI Helper Actions -----------------
    def update_max_threads(self):
        self.max_threads = self.thread_spin.value()

    def refresh_target_combo(self):
        self.target_list.clear()
        links = self.config.get("invite_links", [])
        if links:
            self.target_list.addItems(links)
            self.target_list.selectAll()
        else:
            self.target_list.addItem("No target links. Click Edit to add.")

    def delete_selected_targets(self):
        sel_items = self.target_list.selectedItems()
        if not sel_items:
            QMessageBox.warning(self, "Warning", "Please select one or more links to delete.")
            return
            
        reply = QMessageBox.question(self, 'Confirm Delete', 
                                    f"Are you sure you want to delete {len(sel_items)} selected link(s)?", 
                                    QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            links = self.config.get("invite_links", [])
            for item in sel_items:
                if item.text() in links:
                    links.remove(item.text())
            
            self.config["invite_links"] = links
            self.save_config()
            self.refresh_target_combo()

    def show_links_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Manage Target Links")
        dialog.resize(500, 380)
        dialog.setStyleSheet(self.styleSheet())
        dialog.setWindowFlags(dialog.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)
        
        header_label = QLabel("EDIT TARGET LINKS")
        header_label.setStyleSheet("font-size: 15px; font-weight: 800; color: #3b82f6; margin-bottom: 4px;")
        layout.addWidget(header_label)
        
        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        divider.setFrameShadow(QFrame.Sunken)
        divider.setStyleSheet("background-color: #cbd5e1; max-height: 1px; border: none;")
        layout.addWidget(divider)
        
        lbl_info = QLabel("Paste page/profile/group URLs (One URL per line):")
        lbl_info.setStyleSheet("font-weight: 600; color: #475569; font-size: 12px;")
        layout.addWidget(lbl_info)
        
        text_area = QTextEdit()
        links = self.config.get("invite_links", [])
        text_area.setPlainText("\n".join(links))
        text_area.setPlaceholderText("https://www.facebook.com/my-page-url/\nhttps://www.facebook.com/groups/my-group-url/")
        layout.addWidget(text_area)
        
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.clicked.connect(dialog.reject)
        
        save_btn = QPushButton("Save Links")
        save_btn.setObjectName("PrimaryButton")
        save_btn.setCursor(Qt.PointingHandCursor)
        
        def save_links():
            raw_text = text_area.toPlainText().strip()
            links_list = [l.strip() for l in raw_text.split("\n") if l.strip()]
            self.config["invite_links"] = links_list
            self.save_config()
            self.refresh_target_combo()
            dialog.accept()
            
        save_btn.clicked.connect(save_links)
        
        btn_layout.addStretch()
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(save_btn)
        layout.addLayout(btn_layout)
        
        dialog.exec()

    def browse_file(self, line_edit, file_filter):
        path, _ = QFileDialog.getOpenFileName(self, "Select File", "", file_filter)
        if path:
            line_edit.setText(path)

    def backup_entire_database(self):
        backup_file = self.perform_backup()
        if backup_file:
            self.show_success_alert("Backup Complete", f"Successfully backed up database to:\n{backup_file}")
        else:
            QMessageBox.critical(self, "Backup Failed", "Unable to perform backup of database.")

    def open_update_dialog(self):
        """Open the Auto-Update dialog."""
        dlg = UpdateDialog(self)
        dlg.exec()

    def update_global_status_label_style(self, status):
        self.current_status = status
        self.setWindowTitle(f"Facebook Auto-Login & Invite Master v2.0.0 [{status}]")

    @Slot()
    def toggle_theme(self):
        self.is_dark_mode = not self.is_dark_mode
        if self.is_dark_mode:
            self.setStyleSheet(DARK_THEME_STYLE)
            self.theme_btn.setText("☀️ Light Mode")
            self.config["theme_mode"] = "dark"
        else:
            self.setStyleSheet(LIGHT_THEME_STYLE)
            self.theme_btn.setText("🌙 Dark Mode")
            self.config["theme_mode"] = "light"
            
        self.save_config()
        self.update_global_status_label_style(self.current_status)
        self.refresh_table()

    def update_stats_ui(self):
        for key, widget in self.stat_cards.items():
            widget.setText(str(self.stats[key]))

    def append_log(self, username, level, message):
        color = "#606770"
        if level == "SUCCESS":
            color = "#2b851a"
        elif level == "ERROR":
            color = "#c71f3b"
        elif level == "WARNING":
            color = "#b8860b"
            
        formatted_message = f"<font color='#1877f2'><b>[{username}]</b></font> <font color='{color}'>[{level}] {message}</font>"
        self.log_console.append(formatted_message)

    def show_success_alert(self, title, message):
        """Displays a custom styled success alert dialog popup."""
        dialog = ModernSuccessDialog(title, message, self)
        dialog.exec()

    def import_accounts_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open Accounts File", "", "Text Files (*.txt);;CSV Files (*.csv);;All Files (*)")
        if not file_path:
            return
            
        from PySide6.QtWidgets import QInputDialog
        category, ok = QInputDialog.getText(self, "Category", "Enter category for imported accounts (leave as 'All' for default):", text="All")
        if not ok:
            return
        category = category.strip() or "All"
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            old_count = len(self.account_manager.accounts)
            if file_path.endswith(".csv"):
                accounts = self.account_manager.load_from_csv(file_path, category=category)
            else:
                accounts = self.account_manager.load_from_text(content, category=category)
            new_added = len(accounts) - old_count
            
            self.refresh_table()
            self.append_log("System", "SUCCESS", f"Imported accounts. Added {new_added} new unique accounts. Total: {len(accounts)}")
            
            if self.config.get("auto_backup_enabled", True):
                self.perform_backup()
                
            self.show_success_alert("Import Success", f"Successfully imported accounts!\n\nAdded: {new_added} new unique accounts.\nTotal accounts loaded: {len(accounts)}")
        except Exception as e:
            self.append_log("System", "ERROR", f"Failed to import accounts: {str(e)}")



    def clear_accounts_table(self):
        self.account_manager.clear()
        self.account_manager.clear_history()
        self.refresh_table()
        self.stats = {k: 0 for k in self.stats}
        self.update_stats_ui()
        self.append_log("System", "INFO", "Cleared account database and history.")

    def check_accounts_status(self):
        """Count Active / Dead / Idle accounts and show a beautiful summary dialog."""
        accounts = self.account_manager.accounts
        total = len(accounts)
        
        if total == 0:
            QMessageBox.information(self, "Check Accounts", "No accounts loaded yet.\nPlease import or add accounts first.")
            return
        
        active_list  = [a for a in accounts if a.status in ("Active", "Completed", "Logged In")]
        dead_list    = [a for a in accounts if a.status in ("Dead", "Login Failed", "Failed")]
        idle_list    = [a for a in accounts if a.status not in ("Active", "Completed", "Logged In", "Dead", "Login Failed", "Failed")]
        
        n_active = len(active_list)
        n_dead   = len(dead_list)
        n_idle   = len(idle_list)

        pct_active = round(n_active / total * 100) if total else 0
        pct_dead   = round(n_dead   / total * 100) if total else 0
        pct_idle   = round(n_idle   / total * 100) if total else 0

        self.append_log("System", "INFO",
            f"Account Check — Total: {total} | Active: {n_active} | Dead: {n_dead} | Idle/Unknown: {n_idle}")

        # -------- Build beautiful dialog --------
        dlg = QDialog(self)
        dlg.setWindowTitle("Account Status Summary")
        dlg.setFixedSize(480, 420)
        dlg.setStyleSheet(self.styleSheet())

        outer = QVBoxLayout(dlg)
        outer.setContentsMargins(24, 24, 24, 24)
        outer.setSpacing(16)

        # Title
        title_lbl = QLabel("\ud83d\udd0d Account Health Check")
        title_lbl.setStyleSheet(
            "font-size: 17px; font-weight: 800; color: #3b82f6;" if not self.is_dark_mode
            else "font-size: 17px; font-weight: 800; color: #60a5fa;"
        )
        outer.addWidget(title_lbl)

        # Sub-title
        sub_lbl = QLabel(f"Scanned <b>{total}</b> accounts in the current session.")
        sub_lbl.setStyleSheet("font-size: 12px; color: #64748b;" if not self.is_dark_mode else "font-size: 12px; color: #94a3b8;")
        outer.addWidget(sub_lbl)

        # Separator line
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color: #e2e8f0;" if not self.is_dark_mode else "color: #334155;")
        outer.addWidget(sep)

        # Helper to build each stat row with a progress bar
        def make_stat_row(icon, label, count, pct, bar_color, text_color):
            row_widget = QFrame()
            row_widget.setStyleSheet(
                f"QFrame {{ background: {'#f8fafc' if not self.is_dark_mode else '#1e293b'};"
                f" border-radius: 10px; padding: 4px; }}"
            )
            row_layout = QVBoxLayout(row_widget)
            row_layout.setContentsMargins(12, 10, 12, 10)
            row_layout.setSpacing(6)

            # Top line: icon + label + count/pct
            top_layout = QHBoxLayout()
            top_layout.setSpacing(8)

            icon_lbl = QLabel(icon)
            icon_lbl.setStyleSheet("font-size: 20px; background: transparent;")
            icon_lbl.setFixedWidth(28)

            name_lbl = QLabel(f"<b>{label}</b>")
            name_lbl.setStyleSheet(f"font-size: 13px; color: {text_color}; background: transparent;")

            count_lbl = QLabel(f"{count} accounts  ({pct}%)")
            count_lbl.setStyleSheet(
                f"font-size: 13px; font-weight: 700; color: {text_color}; background: transparent;"
            )
            count_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

            top_layout.addWidget(icon_lbl)
            top_layout.addWidget(name_lbl)
            top_layout.addStretch()
            top_layout.addWidget(count_lbl)
            row_layout.addLayout(top_layout)

            # Progress bar (manual via QFrame)
            bar_bg = QFrame()
            bar_bg.setFixedHeight(8)
            bar_bg.setStyleSheet(
                f"QFrame {{ background: {'#e2e8f0' if not self.is_dark_mode else '#334155'};"
                f" border-radius: 4px; }}"
            )
            bar_bg_layout = QHBoxLayout(bar_bg)
            bar_bg_layout.setContentsMargins(0, 0, 0, 0)
            bar_bg_layout.setSpacing(0)

            fill_pct = max(pct, 2) if count > 0 else 0
            bar_fill = QFrame()
            bar_fill.setFixedHeight(8)
            bar_fill.setStyleSheet(
                f"QFrame {{ background: {bar_color}; border-radius: 4px; }}"
            )
            bar_fill.setFixedWidth(int(360 * fill_pct / 100))

            bar_bg_layout.addWidget(bar_fill)
            bar_bg_layout.addStretch()
            row_layout.addWidget(bar_bg)

            return row_widget

        # Active row
        active_color  = "#10b981" if not self.is_dark_mode else "#34d399"
        dead_color    = "#ef4444" if not self.is_dark_mode else "#f87171"
        idle_color    = "#94a3b8" if not self.is_dark_mode else "#64748b"
        active_text   = "#059669" if not self.is_dark_mode else "#34d399"
        dead_text     = "#dc2626" if not self.is_dark_mode else "#f87171"
        idle_text     = "#64748b" if not self.is_dark_mode else "#94a3b8"

        outer.addWidget(make_stat_row("\u2705", "Active (ក្រស់)",  n_active, pct_active, active_color, active_text))
        outer.addWidget(make_stat_row("\u274c", "Dead (ស្លាប់)",    n_dead,   pct_dead,   dead_color,   dead_text))
        outer.addWidget(make_stat_row("\u23f3", "Idle / Unknown",   n_idle,   pct_idle,   idle_color,   idle_text))

        outer.addStretch()

        # Close button
        close_btn = QPushButton("Close")
        close_btn.setObjectName("PrimaryButton")
        close_btn.setMinimumHeight(38)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.clicked.connect(dlg.accept)
        outer.addWidget(close_btn)

        dlg.exec()

    def open_check_account_dialog(self):
        """Open the full CheckAccountDialog where user can paste and check accounts."""
        dlg = CheckAccountDialog(self, self.config, self.is_dark_mode)
        dlg.exec()

    def open_manage_categories_dialog(self):
        """Full dialog to Create / Rename / Delete categories."""
        mgr = self.account_manager
        dark = self.is_dark_mode

        dialog = QDialog(self)
        dialog.setWindowTitle("⚙ Manage Categories")
        dialog.setMinimumSize(420, 480)
        dialog.setStyleSheet(self.styleSheet())

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        # Header
        hdr = QLabel("Manage Categories")
        hdr.setStyleSheet("font-size: 15px; font-weight: 800; color: #3b82f6;")
        layout.addWidget(hdr)

        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        divider.setStyleSheet("background: #334155; max-height:1px; border:none;")
        layout.addWidget(divider)

        # Category list widget
        from PySide6.QtWidgets import QListWidget, QInputDialog
        cat_list = QListWidget()
        cat_list.setAlternatingRowColors(True)
        cat_list.setStyleSheet(
            "QListWidget { border: 1.5px solid #334155; border-radius: 8px; padding: 4px; }"
            "QListWidget::item { padding: 8px 12px; border-radius: 6px; }"
            "QListWidget::item:selected { background: #3b82f6; color: white; }"
        )

        def _reload_list():
            cat_list.clear()
            for c in mgr.get_categories():
                if c != "All":
                    cat_list.addItem(c)

        _reload_list()
        layout.addWidget(cat_list, 1)

        # Add Category row
        add_row = QHBoxLayout()
        add_input = QLineEdit()
        add_input.setPlaceholderText("New category name...")
        add_input.setMinimumHeight(34)
        add_btn = QPushButton("+ Add")
        add_btn.setMinimumHeight(34)
        add_btn.setMinimumWidth(70)
        add_btn.setObjectName("PrimaryButton")
        add_btn.setCursor(Qt.PointingHandCursor)

        def _do_add():
            name = add_input.text().strip()
            if name:
                mgr.add_category(name)
                add_input.clear()
                _reload_list()
                self.update_categories()

        add_btn.clicked.connect(_do_add)
        add_input.returnPressed.connect(_do_add)
        add_row.addWidget(add_input, 1)
        add_row.addWidget(add_btn)
        layout.addLayout(add_row)

        # Action buttons
        action_row = QHBoxLayout()
        action_row.setSpacing(8)

        rename_btn = QPushButton("✏ Rename")
        rename_btn.setMinimumHeight(34)
        rename_btn.setCursor(Qt.PointingHandCursor)

        def _do_rename():
            item = cat_list.currentItem()
            if not item:
                return
            old = item.text()
            new_name, ok = QInputDialog.getText(dialog, "Rename Category", f"New name for '{old}':", text=old)
            if ok and new_name.strip() and new_name.strip() != old:
                mgr.rename_category(old, new_name.strip())
                _reload_list()
                self.update_categories()
                self.refresh_table()

        rename_btn.clicked.connect(_do_rename)

        delete_btn = QPushButton("🗑 Delete")
        delete_btn.setMinimumHeight(34)
        delete_btn.setCursor(Qt.PointingHandCursor)
        delete_btn.setStyleSheet(
            "QPushButton { background:#ef4444; color:white; border:none; border-radius:8px; font-weight:700; }"
            "QPushButton:hover { background:#dc2626; }"
        )

        def _do_delete():
            item = cat_list.currentItem()
            if not item:
                return
            name = item.text()
            reply = QMessageBox.question(
                dialog, "Delete Category",
                f"Delete category '{name}'?\nAccounts in this category will be moved to 'All'.",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                mgr.delete_category(name)
                _reload_list()
                self.update_categories()
                self.refresh_table()

        delete_btn.clicked.connect(_do_delete)

        action_row.addWidget(rename_btn)
        action_row.addWidget(delete_btn)
        action_row.addStretch()

        close_btn = QPushButton("Close")
        close_btn.setMinimumHeight(34)
        close_btn.setMinimumWidth(80)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.clicked.connect(dialog.accept)
        action_row.addWidget(close_btn)
        layout.addLayout(action_row)

        dialog.exec()

    def update_categories(self):
        current = self.category_filter.currentText()
        categories = self.account_manager.get_categories()
        # Replace 'All' with 'All Categories' for the filter label
        display = ["All Categories"] + [c for c in categories if c != 'All']
            
        self.category_filter.blockSignals(True)
        self.category_filter.clear()
        self.category_filter.addItems(display)
        if current in display:
            self.category_filter.setCurrentText(current)
        else:
            self.category_filter.setCurrentIndex(0)
        self.category_filter.blockSignals(False)

    def recalculate_stats(self):
        """Recalculates all statistics dynamically from the current accounts to ensure 100% accuracy on cards."""
        accounts = self.account_manager.accounts
        self.stats["total"] = len(accounts)
        self.stats["running"] = len(self.workers)
        self.stats["success"] = sum(1 for a in accounts if a.status in ("Active", "Completed", "Succeeded", "Logged In"))
        self.stats["failed"] = sum(1 for a in accounts if a.status in ("Dead", "Login Failed", "Error", "Failed"))
        self.stats["sent"] = sum(getattr(a, 'invites_sent', 0) for a in accounts)
        self.stats["inv_failed"] = sum(getattr(a, 'invites_failed', 0) for a in accounts)
        self.update_stats_ui()

    def refresh_table(self):
        self.update_categories()
        category = self.category_filter.currentText()
        if category == "All Categories" or category == "All":
            accounts = self.account_manager.accounts
        else:
            accounts = [acc for acc in self.account_manager.accounts if getattr(acc, 'category', 'All') == category]
            
        self.recalculate_stats()
        
        # Verify and update cookies status for all displayed accounts
        for acc in accounts:
            cookie_path = os.path.join("cookies", f"{acc.username}.json")
            try:
                acc.cookies = os.path.exists(cookie_path) and os.path.getsize(cookie_path) > 0
            except:
                acc.cookies = False
                
        self.account_model.accounts = accounts
        self.account_model.update_data()

    def style_status_cell(self, row, status):
        cell = self.account_table.item(row, 7) # Status is at Column 7
        if not cell:
            return
            
        if self.is_dark_mode:
            color_map = {
                "Idle": "#94a3b8",
                "Logging in": "#fbbf24",
                "Loading cookies...": "#fbbf24",
                "Initializing browser...": "#fbbf24",
                "Active": "#34d399",
                "Logged In": "#34d399",
                "Inviting": "#60a5fa",
                "Running invite loop...": "#60a5fa",
                "Completed": "#34d399",
                "Dead": "#f87171",
                "Login Failed": "#f87171",
                "2FA Verification": "#fb923c",
                "Stopped": "#94a3b8",
                "Chapracters dynamic function": "#f87171",
            }
        else:
            color_map = {
                "Idle": "#64748b",
                "Logging in": "#d97706",
                "Loading cookies...": "#d97706",
                "Initializing browser...": "#d97706",
                "Active": "#059669",
                "Logged In": "#059669",
                "Inviting": "#2563eb",
                "Running invite loop...": "#2563eb",
                "Completed": "#059669",
                "Dead": "#dc2626",
                "Login Failed": "#dc2626",
                "2FA Verification": "#b45309",
                "Stopped": "#64748b",
                "Chapracters dynamic function": "#dc2626",
            }
        
        color_hex = color_map.get(status, "#0f172a" if not self.is_dark_mode else "#cbd5e1")
        cell.setForeground(QColor(color_hex))
        
        # Set font weight bold for active elements & fix QFont pointSize warning
        font = cell.font()
        if font.pointSize() <= 0:
            font.setPointSize(10)
        font.setBold(status not in ["Idle", "Completed", "Active", "Dead", "Stopped"])
        cell.setFont(font)

    # ----------------- Execution / Thread Control -----------------
    def start_automation(self):
        selected_indexes = self.account_table.selectionModel().selectedRows()
        selected_usernames = []
        for index in selected_indexes:
            row = index.row()
            if row < len(self.account_model.accounts):
                username = self.account_model.accounts[row].username
                selected_usernames.append(username)

        if selected_usernames:
            self.append_log("System", "INFO", f"Starting automation for {len(selected_usernames)} selected accounts.")
            self.start_selected_accounts(selected_usernames)
            return

        # Fallback to visible filtered accounts if none are selected
        accounts = self.account_model.accounts
        if not accounts:
            self.append_log("System", "ERROR", "Cannot start. No accounts visible in current category filter.")
            return

        self.append_log("System", "INFO", f"No specific accounts selected. Running automation on {len(accounts)} visible accounts.")
        all_usernames = [acc.username for acc in accounts]
        self.start_selected_accounts(all_usernames)

    def process_queue(self, page_urls, xpath_settings, options_settings):
        while len(self.workers) < self.max_threads and self.pending_queue:
            acc = self.pending_queue.pop(0)
            username = acc.username
            
            # Calculate next available window index for grid positioning
            used_indices = {w.window_index for w in self.workers.values() if hasattr(w, 'window_index')}
            window_index = 0
            while window_index in used_indices:
                window_index += 1

            # Setup worker QThread
            worker = SeleniumWorker(acc, page_urls, xpath_settings, options_settings, window_index=window_index)
            
            # Connect signals
            worker.log_signal.connect(self.handle_worker_log)
            worker.status_signal.connect(self.handle_worker_status)
            worker.stats_signal.connect(self.handle_worker_stats)
            worker.profile_signal.connect(self.handle_worker_profile)
            worker.finished_signal.connect(lambda user, success: self.handle_worker_finished(user, success, page_urls, xpath_settings, options_settings))
            # Safely delete C++ object only after thread fully exits
            worker.finished.connect(worker.deleteLater)
            
            self.workers[username] = worker
            worker.start()
            
            self.stats["running"] = len(self.workers)
            self.update_stats_ui()
            
        if not self.workers and not self.pending_queue:
            if getattr(self, "task_mode_active", False):
                self.task_mode_current_index += 1
                if self.task_mode_current_index < len(self.task_mode_pipeline):
                    current_task = self.task_mode_pipeline[self.task_mode_current_index - 1]
                    next_task = self.task_mode_pipeline[self.task_mode_current_index]
                    
                    self.append_log("System", "SUCCESS", f"Task '{current_task}' completed for all accounts.")
                    self.append_log("System", "INFO", f"Starting Task {self.task_mode_current_index + 1}/{len(self.task_mode_pipeline)}: '{next_task}' for all active accounts.")
                    
                    # Filter active non-dead accounts
                    next_accounts = []
                    for acc in self.account_manager.accounts:
                        if acc.username in self.task_mode_all_target_usernames:
                            if acc.status not in ["Dead", "Check Point", "Error Verify Google", "Error Login Google", "Error", "Chapracters dynamic function"]:
                                next_accounts.append(acc)
                                
                    if not next_accounts:
                        self.append_log("System", "WARNING", "No active accounts remaining to proceed to next task.")
                        self.complete_automation_run()
                        return
                        
                    # Queue remaining active accounts for the next task
                    self.pending_queue = list(next_accounts)
                    for acc in self.pending_queue:
                        acc.status = "Idle"
                    self.refresh_table()
                    
                    # Set the new current task
                    options_settings["tasks"] = ["login", next_task]
                    
                    # Run next task
                    self.process_queue(page_urls, xpath_settings, options_settings)
                else:
                    self.append_log("System", "SUCCESS", "All pipeline tasks completed for all accounts!")
                    self.complete_automation_run()
            else:
                self.complete_automation_run()

    @Slot(str, str, str)
    def handle_worker_log(self, username, level, message):
        self.append_log(username, level, message)
        if "Login Successful!" in message or "Login Confirmed!" in message:
            # Non-blocking modern dialog popup to prevent UI freezing
            dialog = ModernSuccessDialog("Login Success", f"Account '{username}' logged in successfully!", self)
            dialog.setModal(False)
            dialog.setAttribute(Qt.WA_DeleteOnClose)
            dialog.show()

    @Slot(str, str)
    def handle_worker_status(self, username, status):
        # Update model status and dynamically refresh cookie presence
        cookie_path = os.path.join("cookies", f"{username}.json")
        for row, acc in enumerate(self.account_manager.accounts):
            if acc.username == username:
                acc.status = status
                try:
                    acc.cookies = os.path.exists(cookie_path) and os.path.getsize(cookie_path) > 0
                except:
                    pass
                self.account_model.update_row(row)
                break

    @Slot(str, int, int)
    def handle_worker_stats(self, username, sent, failed):
        # Find row in table and update cells
        for row, acc in enumerate(self.account_manager.accounts):
            if acc.username == username:
                acc.invites_sent = sent
                acc.invites_failed = failed
                self.account_model.update_row(row)
                break

        # Calculate dynamic global invites stats
        self.recalculate_stats()

    @Slot(str, str, int)
    def handle_worker_profile(self, username, profile_name, friend_count):
        # Update model
        for row, acc in enumerate(self.account_manager.accounts):
            if acc.username == username:
                acc.profile_name = profile_name
                acc.friend_count = friend_count
                self.account_model.update_row(row)
                break
                
        self.account_manager.save_history()

    def handle_worker_finished(self, username, success, page_urls, xpath_settings, options_settings):
        # Clean up worker reference gracefully to prevent QThread GC crash
        if username in self.workers:
            worker = self.workers.pop(username)
            if not hasattr(self, '_dead_workers'):
                self._dead_workers = []
            # Keep python reference alive until C++ thread finishes.
            self._dead_workers.append(worker)
            # Periodically clean up fully dead python objects
            alive_workers = []
            for w in self._dead_workers:
                try:
                    if w.isRunning():
                        alive_workers.append(w)
                except RuntimeError:
                    pass
            self._dead_workers = alive_workers
            
        if success:
            self.handle_worker_status(username, "Completed")
        else:
            # Preserve specialized error statuses if they were already set by the worker
            current_status = "Dead"
            for acc in self.account_manager.accounts:
                if acc.username == username:
                    if acc.status in ("Check Point", "Error Verify Google", "Error Login Google", "Error", "Chapracters dynamic function"):
                        current_status = acc.status
                    break
            self.handle_worker_status(username, current_status)
            
        self.recalculate_stats()
        
        # Save execution history state
        self.account_manager.save_history()
        
        # Trigger next item in queue
        self.process_queue(page_urls, xpath_settings, options_settings)

    def stop_automation(self):
        self.append_log("System", "WARNING", "Stopping all active automation worker threads. Please wait...")
        self.pending_queue = [] # clear pending list
        
        # Stop all running workers
        for username, worker in list(self.workers.items()):
            worker.stop()
            worker.wait() # Wait for thread shutdown
            self.handle_worker_status(username, "Stopped")
            
        self.workers.clear()
        self.account_manager.save_history() # Save history state upon manual stop
        self.complete_automation_run()

    def complete_automation_run(self):
        self.update_global_status_label_style("FINISHED")
        
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.run_selected_btn.setEnabled(True)
        self.add_acc_btn.setEnabled(True)
        self.import_btn.setEnabled(True)
        self.clear_btn.setEnabled(True)
        
        self.stats["running"] = 0
        self.update_stats_ui()
        self.append_log("System", "SUCCESS", "All automation tasks finalized.")
        
        if self.config.get("auto_backup_enabled", True):
            self.perform_backup()
            
        if self.stats["total"] > 0:
            self.show_success_alert(
                "Automation Finished", 
                f"All automation tasks completed successfully!\n\n"
                f"Total Accounts: {self.stats['total']}\n"
                f"Successful Logins: {self.stats['success']}\n"
                f"Failed Logins: {self.stats['failed']}\n"
                f"Invites Sent: {self.stats['sent']}"
            )

    def show_context_menu(self, pos):
        # Determine clicked row
        index = self.account_table.indexAt(pos)
        if not index.isValid():
            return
        row = index.row()
        if row >= len(self.account_model.accounts):
            return
        
        # Gather all selected usernames
        selected_indexes = self.account_table.selectionModel().selectedRows()
        selected_usernames = []
        for idx in selected_indexes:
            r = idx.row()
            if r < len(self.account_model.accounts):
                selected_usernames.append(self.account_model.accounts[r].username)
                
        # Make sure the right-clicked row is included
        clicked_username = self.account_model.accounts[row].username
        if clicked_username not in selected_usernames:
            selected_usernames.append(clicked_username)
        
        # Build context menu
        menu = QMenu(self)
        
        # Add actions in English
        run_action = menu.addAction("Run This Account" if len(selected_usernames) <= 1 else f"Run Selected Accounts ({len(selected_usernames)})")
        manual_action = menu.addAction("Open in Facebook (Manual)" if len(selected_usernames) <= 1 else f"Open in Facebook (Manual) ({len(selected_usernames)})")
        edit_action = menu.addAction("Edit Account Details")
        category_action = menu.addAction("Change Category")
        delete_action = menu.addAction("Delete Account" if len(selected_usernames) <= 1 else f"Delete Selected Accounts ({len(selected_usernames)})")
        clear_cookies_action = menu.addAction("Clear Cookies" if len(selected_usernames) <= 1 else f"Clear Cookies for Selected ({len(selected_usernames)})")
        
        # Map actions to methods
        action = menu.exec(self.account_table.viewport().mapToGlobal(pos))
        if action == run_action:
            self.start_selected_accounts(selected_usernames)
        elif action == manual_action:
            self.open_manual_browsers(selected_usernames)
        elif action == edit_action:
            self.show_edit_dialog(row)
        elif action == category_action:
            self.show_change_category_dialog()
        elif action == delete_action:
            self.delete_selected_accounts(selected_usernames)
        elif action == clear_cookies_action:
            self.clear_selected_cookies(selected_usernames)

    def show_change_category_dialog(self):
        selected_indexes = self.account_table.selectionModel().selectedRows()
        if not selected_indexes:
            return
            
        categories = self.account_manager.get_categories()
            
        dialog = QDialog(self)
        dialog.setWindowTitle("Change Category")
        dialog.setFixedSize(350, 150)
        layout = QVBoxLayout(dialog)
        
        lbl = QLabel(f"Change category for {len(selected_indexes)} selected account(s):")
        layout.addWidget(lbl)
        
        combo = QComboBox()
        combo.setEditable(False)
        combo.addItems(categories)
        layout.addWidget(combo)
        
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(dialog.accept)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(dialog.reject)
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(save_btn)
        layout.addLayout(btn_layout)
        
        if dialog.exec() == QDialog.Accepted:
            new_cat = combo.currentText().strip() or "All"
            for index in selected_indexes:
                row = index.row()
                if row < len(self.account_model.accounts):
                    self.account_model.accounts[row].category = new_cat
            self.account_manager.save_history(force=True)
            self.refresh_table()

    def start_selected_automation(self):
        """Starts automation only for the selected accounts in the table."""
        selected_indexes = self.account_table.selectionModel().selectedRows()
        if not selected_indexes:
            self.append_log("System", "ERROR", "Please select one or more accounts with the mouse first.")
            return
            
        selected_usernames = []
        for index in selected_indexes:
            row = index.row()
            if row < len(self.account_model.accounts):
                username = self.account_model.accounts[row].username
                selected_usernames.append(username)
                    
        if not selected_usernames:
            self.append_log("System", "ERROR", "No valid accounts selected.")
            return
            
        self.start_selected_accounts(selected_usernames)

    def start_selected_accounts(self, target_usernames):
        """Initializes and runs the automation pipeline only for specified accounts."""
        accounts = [acc for acc in self.account_manager.accounts if acc.username in target_usernames]
        if not accounts:
            self.append_log("System", "ERROR", "Cannot start. Selected accounts not found in memory.")
            return

        self.update_global_status_label_style("RUNNING")
        
        # Read parameters from GUI
        tasks = [k for k, cb in self.tasks_checkboxes.items() if cb.isChecked()]
        
        # Save current configurations and tasks to config
        self.config["tasks"] = tasks
        self.config["group_keyword"] = self.edit_kwd.text()
        self.config["random_reactions"] = self.chk_reaction.isChecked()
        self.config["feed_mins"] = self.spin_feed_mins.value()
        self.config["video_feed_mins"] = self.spin_video_mins.value()
        self.config["story_count"] = self.spin_story.value()
        self.config["invite_count"] = self.spin_invite.value()
        self.config["add_friend_count"] = self.spin_add_friend.value()
        self.config["confirm_friend_count"] = self.spin_confirm.value()
        self.config["join_group_count"] = self.spin_join_group.value()
        self.config["share_group_count"] = self.spin_share_group.value()
        self.config["scrape_limit"] = self.spin_scrape_limit.value()
        self.config["max_invites_per_page"] = self.max_invites_spin.value()
        self.config["delay_min"] = self.delay_min.value()
        self.config["delay_max"] = self.delay_max.value()
        self.config["run_mode"] = self.run_mode_combo.currentText()
        self.save_config()

        target_links = [item.text() for item in self.target_list.selectedItems()]
        target_links = [l for l in target_links if l != "No target links. Click Edit to add."]
        if not target_links:
            target_links = self.config.get("invite_links", [])
        
        xpath_settings = {
            "email_input": self.config.get("xpath_email", "//input[@name='email']"),
            "pass_input": self.config.get("xpath_pass", "//input[@name='pass']"),
            "login_btn": self.config.get("xpath_login_btn", "//button[@name='login']"),
            "invite_btn": self.config.get("xpath_invite_btn", "//button[contains(.,'Invite')] | //span[text()='Invite'] | //div[text()='Invite']")
        }
            
        options_settings = {
            "headless": (self.browser_mode_combo.currentIndex() == 1),
            "login_mode": "auto",
            "mobile_device": self.device_combo.currentText(),
            "delay_range": (self.delay_min.value(), self.delay_max.value()),
            "max_invites_per_page": self.max_invites_spin.value(),
            "page_load_timeout": self.config.get("page_load_timeout", 30),
            "wait_timeout": self.config.get("wait_timeout", 10),
            "max_login_retries": self.config.get("max_login_retries", 2),
            "custom_user_agent": self.config.get("custom_user_agent", ""),
            "locale_lang": self.config.get("locale_lang", "Auto"),
            "enable_invite_task": ("invite" in tasks),
            "enable_profile_scrape": (self.scrape_profile_combo.currentIndex() == 0),
            "tasks": tasks,
            "target_links": target_links,
            "group_keyword": self.edit_kwd.text(),
            "photo_path": self.config.get("photo_path", ""),
            "video_path": self.config.get("video_path", ""),
            "post_caption": self.config.get("post_caption", ""),
            "random_reactions": self.chk_reaction.isChecked(),
            "feed_mins": self.spin_feed_mins.value(),
            "video_feed_mins": self.spin_video_mins.value(),
            "story_count": self.spin_story.value(),
            "invite_count": self.spin_invite.value(),
            "add_friend_count": self.spin_add_friend.value(),
            "confirm_friend_count": self.spin_confirm.value(),
            "join_group_count": self.spin_join_group.value(),
            "share_group_count": self.spin_share_group.value(),
            "scrape_limit": self.spin_scrape_limit.value()
        }
        
        page_urls = target_links
        
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.run_selected_btn.setEnabled(False)
        self.add_acc_btn.setEnabled(False)
        self.import_btn.setEnabled(False)
        self.clear_btn.setEnabled(False)
        
        self.pending_queue = list(accounts)
        self.workers = {}
        
        # Reset statuses for execution for ALL selected accounts in target
        for acc in self.account_manager.accounts:
            if acc.username in target_usernames:
                acc.status = "Idle"
                acc.invites_sent = 0
                acc.invites_failed = 0
        self.refresh_table()
        
        # Queue all selected accounts for execution
        self.pending_queue = list(accounts)
        
        # Re-calc stats for active run
        self.stats = {
            "total": len(self.account_manager.accounts),
            "running": 0,
            "success": sum(1 for acc in self.account_manager.accounts if acc.status in ["Completed", "Succeeded"]),
            "failed": 0,
            "sent": sum(acc.invites_sent for acc in self.account_manager.accounts),
            "inv_failed": sum(acc.invites_failed for acc in self.account_manager.accounts)
        }
        self.update_stats_ui()
        
        # Handle execution mode strategy selection
        run_mode = self.run_mode_combo.currentText()
        if run_mode == "Run by Task":
            self.task_mode_pipeline = [t for t in tasks if t != "login"]
            if not self.task_mode_pipeline:
                self.task_mode_pipeline = ["login"]
            self.task_mode_active = True
            self.task_mode_current_index = 0
            self.task_mode_all_target_usernames = [acc.username for acc in self.pending_queue]
            options_settings["tasks"] = ["login", self.task_mode_pipeline[0]]
            self.append_log("System", "INFO", f"Run by Task mode active. Pipeline: {', '.join(self.task_mode_pipeline)}")
            self.append_log("System", "INFO", f"Starting Task 1/{len(self.task_mode_pipeline)}: '{self.task_mode_pipeline[0]}' for all accounts.")
        else:
            self.task_mode_active = False
            
        if not self.pending_queue:
            self.append_log("System", "WARNING", "Selected accounts are already Completed or Succeeded.")
            self.complete_automation_run()
            return
            
        self.process_queue(page_urls, xpath_settings, options_settings)

    def show_add_account_dialog(self):
        """Displays a note-format dialog to type/paste accounts."""
        dialog = PasteAccountsDialog(self)
        dialog.setWindowTitle("Add Accounts (Note Format)")
        if dialog.exec() == QDialog.Accepted:
            text = dialog.get_text()
            category = dialog.get_category()
            if text.strip():
                old_count = len(self.account_manager.accounts)
                accounts = self.account_manager.load_from_text(text, category=category)
                new_added = len(accounts) - old_count
                
                self.refresh_table()
                self.append_log("System", "SUCCESS", f"Added accounts. Added {new_added} new unique accounts. Total: {len(accounts)}")
                
                if self.config.get("auto_backup_enabled", True):
                    self.perform_backup()
                    
                self.show_success_alert("Accounts Added", f"Successfully added accounts!\n\nAdded: {new_added} new unique accounts.\nTotal accounts loaded: {len(accounts)}")

    def show_edit_dialog(self, row):
        """Displays edit dialog for the account on the specified row."""
        if row < 0 or row >= len(self.account_model.accounts):
            return
        username = self.account_model.accounts[row].username
        
        # Find account in manager
        target_acc = None
        for acc in self.account_manager.accounts:
            if acc.username == username:
                target_acc = acc
                break
                
        if not target_acc:
            return
            
        # Display Dialog
        dialog = AccountDetailsDialog("Edit Account Details", target_acc.username, target_acc.password, target_acc.two_factor_secret, target_acc.proxy, target_acc.category, self)
        if dialog.exec() == QDialog.Accepted:
            new_user, new_pass, new_2fa, new_proxy, new_category = dialog.get_data()
            if not new_user:
                return
                
            # Update memory
            target_acc.username = new_user
            target_acc.password = new_pass
            target_acc.two_factor_secret = new_2fa
            target_acc.proxy = new_proxy
            target_acc.category = new_category
            
            # Save history
            self.account_manager.save_history()
            self.refresh_table()
            self.append_log("System", "SUCCESS", f"Updated account information for {new_user}.")

    def delete_selected_accounts(self, usernames):
        """Deletes selected accounts from table list, memory, and persistence file."""
        if not usernames:
            return
            
        reply = QMessageBox.question(
            self, 'Confirm Delete', 
            f"Are you sure you want to delete {len(usernames)} selected account(s)?", 
            QMessageBox.Yes | QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return
            
        # Remove from account manager
        self.account_manager.accounts = [acc for acc in self.account_manager.accounts if acc.username not in usernames]
        
        # Clean history records
        history = self.account_manager.load_history_dict()
        deleted_any = False
        for username in usernames:
            if username in history:
                del history[username]
                deleted_any = True
                
        if deleted_any:
            try:
                with open(self.account_manager.history_file, 'w', encoding='utf-8') as f:
                    json.dump(history, f, indent=4, ensure_ascii=False)
            except:
                pass
                
        self.refresh_table()
        self.append_log("System", "WARNING", f"Removed {len(usernames)} account(s) from listing and history.")

    def clear_selected_cookies(self, usernames):
        """Deletes session cookies files from local cookies folder for selected accounts."""
        if not usernames:
            return
            
        success_count = 0
        for username in usernames:
            cookie_path = os.path.join("cookies", f"{username}.json")
            if os.path.exists(cookie_path):
                try:
                    os.remove(cookie_path)
                    success_count += 1
                except:
                    pass
                    
        if success_count > 0:
            self.append_log("System", "SUCCESS", f"Deleted saved session cookies for {success_count} account(s).")
        else:
            self.append_log("System", "WARNING", "No session cookies files found to delete.")
        self.refresh_table()



    def open_manual_browser(self, row):
        """Opens a non-headless browser session for the user to manually control the account."""
        if row < 0 or row >= len(self.account_model.accounts):
            return
        username = self.account_model.accounts[row].username
        self.open_manual_browsers([username])

    def open_manual_browsers(self, usernames):
        """Opens non-headless browser sessions for manual control for multiple accounts."""
        for username in usernames:
            # Find account in manager
            target_acc = None
            for acc in self.account_manager.accounts:
                if acc.username == username:
                    target_acc = acc
                    break
                    
            if not target_acc:
                continue
                
            if username in self.workers:
                self.append_log(username, "WARNING", "Account is already running in another task/browser.")
                continue

            self.append_log(username, "INFO", "Opening browser for manual interaction...")
            
            xpath_settings = {
                "email_input": self.config.get("xpath_email", "//input[@name='email']"),
                "pass_input": self.config.get("xpath_pass", "//input[@name='pass']"),
                "login_btn": self.config.get("xpath_login_btn", "//button[@name='login']"),
                "invite_btn": self.config.get("xpath_invite_btn", "//button[contains(.,'Invite')] | //span[text()='Invite'] | //div[text()='Invite']")
            }
            
            tasks = [k for k, cb in self.tasks_checkboxes.items() if cb.isChecked()]
                
            options_settings = {
                "headless": False,
                "login_mode": "auto",
                "mobile_device": self.device_combo.currentText(),
                "delay_range": (self.delay_min.value(), self.delay_max.value()),
                "max_invites_per_page": self.max_invites_spin.value(),
                "page_load_timeout": self.config.get("page_load_timeout", 30),
                "wait_timeout": self.config.get("wait_timeout", 10),
                "max_login_retries": self.config.get("max_login_retries", 2),
                "custom_user_agent": self.config.get("custom_user_agent", ""),
                "locale_lang": self.config.get("locale_lang", "Auto"),
                "enable_invite_task": ("invite" in tasks),
                "enable_profile_scrape": (self.scrape_profile_combo.currentIndex() == 0),
                "tasks": tasks
            }

            # Calculate next available window index for grid positioning
            used_indices = {w.window_index for w in self.workers.values() if hasattr(w, 'window_index')}
            window_index = 0
            while window_index in used_indices:
                window_index += 1
            
            # Start manual thread worker
            manual_worker = SeleniumWorker(target_acc, [], xpath_settings, options_settings, manual_control=True, window_index=window_index)
            manual_worker.log_signal.connect(self.handle_worker_log)
            manual_worker.status_signal.connect(self.handle_worker_status)
            manual_worker.stats_signal.connect(self.handle_worker_stats)
            manual_worker.profile_signal.connect(self.handle_worker_profile)
            
            # When manual session finishes, refresh stats & update history
            manual_worker.finished_signal.connect(lambda user, success: self.handle_manual_finished(user))
            manual_worker.finished.connect(manual_worker.deleteLater)
            
            # Save worker reference
            self.workers[username] = manual_worker
            manual_worker.start()

    def handle_manual_finished(self, username):
        if username in self.workers:
            worker = self.workers.pop(username)
            if not hasattr(self, '_dead_workers'):
                self._dead_workers = []
            self._dead_workers.append(worker)
            alive_workers = []
            for w in self._dead_workers:
                try:
                    if w.isRunning():
                        alive_workers.append(w)
                except RuntimeError:
                    pass
            self._dead_workers = alive_workers
        self.account_manager.save_history()
        self.refresh_table()
        
        # Restore controls if no other active sessions
        if not self.workers:
            self.complete_automation_run()

    # ── Post Media Manager ───────────────────────────────────────────────────
    def open_post_media_manager(self):
        """Open the full-featured per-account Post Video & Image Manager dialog."""
        dlg = PostMediaManagerDialog(
            parent_window=self,
            account_manager=self.account_manager,
            config=self.config,
            is_dark_mode=self.is_dark_mode,
        )
        dlg.exec()

    def closeEvent(self, event):
        # Safeguard: Terminate drivers before closing window
        self.stop_automation()
        if hasattr(self, 'config') and self.config.get("auto_backup_enabled", True):
            self.perform_backup()
        event.accept()

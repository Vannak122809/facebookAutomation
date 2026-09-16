import sys
import json
import os
import time
import shutil
from datetime import datetime

from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                               QLabel, QFrame, QStackedWidget, QLineEdit, QScrollArea, 
                               QFileDialog, QDialog, QGridLayout, QMessageBox, QSpinBox, 
                               QComboBox, QRadioButton, QPlainTextEdit, QRubberBand, 
                               QApplication, QGraphicsOpacityEffect, QCheckBox, QTimeEdit,
                               QListWidget, QAbstractItemView, QTabWidget, QButtonGroup)
from PySide6.QtCore import Qt, QPropertyAnimation, QTimer, QSize, QPoint, QRect, QTime
from PySide6.QtGui import QIcon, QFont, QFontDatabase

from styles import STYLE_DARK, STYLE_LIGHT
from widgets import AccountCard, BrowserThread
from utils import load_data, save_data, load_settings, save_settings

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GoLoginTool Pro-KH v5.0")
        self.setMinimumSize(1200, 800)
        
        # Set App Icon
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app_icon.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        
        # Load Khmer OS Siemreap Font
        self.app_font = QFont("Khmer OS Siemreap")
        self.app_font.setPointSize(10)
        self.setFont(self.app_font)
        
        # Ensure the whole app uses this font as a baseline
        QApplication.instance().setFont(self.app_font)
        
        # App State
        self.app_settings = load_settings()
        self.active_threads = []
        self.pending_launch_queue = []
        self.task_queue_order = ["login"]
        self.success_count = 0
        self.fail_count = 0
        self.rotation_index = 0
        self.current_theme = "dark" # Initial theme state
        self.active_slots = {} # Track which task uses which grid index: {UID: SlotIndex}
        
        self.init_ui()
        self.load_accounts()
        
        # Launch Queue Processor
        self.queue_timer = QTimer()
        self.queue_timer.timeout.connect(self.process_launch_queue)
        self.queue_timer.start(2000)

        self.queue_timer.start(2000)

        # Apply Initial Theme
        self.setStyleSheet(STYLE_DARK)

    def toggle_theme(self):
        """Toggle between Premium Dark and Light modes"""
        if self.current_theme == "dark":
            self.setStyleSheet(STYLE_LIGHT)
            self.btn_theme.setText("🌙 Dark Mode")
            self.current_theme = "light"
        else:
            self.setStyleSheet(STYLE_DARK)
            self.btn_theme.setText("☀️ Light Mode")
            self.current_theme = "dark"

    def get_icon(self, name, fallback_text=""):
        """Helper to get icon from assets or fallback to text"""
        icon_path = os.path.join(os.getcwd(), "assets", f"{name}.png")
        if os.path.exists(icon_path):
            return QIcon(icon_path)
        return QIcon() # Or return a text-based icon if using a font library

    def init_ui(self):
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # 1. Page Stack
        self.pages = QStackedWidget()
        self.page_opacity_effect = QGraphicsOpacityEffect(self.pages)
        self.pages.setGraphicsEffect(self.page_opacity_effect)
        
        self.setup_workspace_page()
        self.setup_settings_page()
        
        self.pages.addWidget(self.page_workspace)
        self.pages.addWidget(self.page_settings)
        
        self.main_layout.addWidget(self.pages)
        
        # 2. Dynamic Overlay / Popup System
        self.overlay_widget = QWidget(self.central_widget)
        self.overlay_layout = QVBoxLayout(self.overlay_widget)
        self.overlay_layout.setAlignment(Qt.AlignCenter)
        self.overlay_widget.setStyleSheet("""
            QWidget { background-color: rgba(18, 18, 18, 200); }
            QFrame#popup_card { 
                background-color: #121212; 
                border: 2px solid #FFD600; 
                border-radius: 10px; 
            }
        """)
        self.overlay_widget.hide()
        self.overlay_widget.raise_()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'overlay_widget'):
            self.overlay_widget.setGeometry(0, 0, self.width(), self.height())

    def show_custom_popup(self, widget, title=""):
        # Clear existing popups
        for i in reversed(range(self.overlay_layout.count())): 
            item = self.overlay_layout.itemAt(i)
            if item.widget():
                item.widget().deleteLater()
                
        # Create Popup Card Structure
        popup_card = QFrame()
        popup_card.setObjectName("popup_card")
        popup_card.setMinimumWidth(350)     # Keep it compact
        popup_card.setMaximumWidth(450)     # Don't let it grow too large
        
        layout = QVBoxLayout(popup_card)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Title & Close Header
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        lbl_title = QLabel(f"<b>{title}</b>")
        lbl_title.setStyleSheet("font-size: 16px; color: #FFFFFF;")
        
        btn_close = QPushButton("✖")
        btn_close.setFixedSize(30, 30)
        btn_close.setObjectName("btn_danger_small")
        btn_close.setStyleSheet("border-radius: 15px;")
        btn_close.clicked.connect(self.hide_custom_popup)
        
        header.addWidget(lbl_title)
        header.addStretch()
        header.addWidget(btn_close)
        
        layout.addLayout(header)
        
        # Add the custom widget payload
        widget.setStyleSheet("background-color: transparent;")
        layout.addWidget(widget)
        
        self.overlay_layout.addWidget(popup_card)
        
        # Fade In Animation
        self.overlay_opacity = QGraphicsOpacityEffect(self.overlay_widget)
        self.overlay_widget.setGraphicsEffect(self.overlay_opacity)
        self.overlay_widget.setGeometry(0, 0, self.width(), self.height())
        self.overlay_widget.show()
        
        self.popup_anim = QPropertyAnimation(self.overlay_opacity, b"opacity")
        self.popup_anim.setDuration(200)
        self.popup_anim.setStartValue(0.0)
        self.popup_anim.setEndValue(1.0)
        self.popup_anim.start()

    def hide_custom_popup(self):
        self.popup_anim = QPropertyAnimation(self.overlay_opacity, b"opacity")
        self.popup_anim.setDuration(150)
        self.popup_anim.setStartValue(1.0)
        self.popup_anim.setEndValue(0.0)
        self.popup_anim.finished.connect(self.overlay_widget.hide)
        self.popup_anim.start()

    def setup_workspace_page(self):
        self.page_workspace = QWidget()
        layout = QVBoxLayout(self.page_workspace)
        layout.setContentsMargins(20, 15, 20, 20)
        layout.setSpacing(15)

        # HEADER SECTION
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(5, 5, 5, 5)
        
        self.lbl_brand = QLabel("🛡️ GOLOGIN PRO")
        self.lbl_brand.setObjectName("brand_title")
        header_layout.addWidget(self.lbl_brand)
        header_layout.addSpacing(30)

        # Stats Ribbon (More compact)
        self.stats_row = QHBoxLayout()
        self.stats_row.setSpacing(10)
        self.stat_profiles = self.create_stat_card("PROFILES", "0", "stat_profiles")
        self.stat_active = self.create_stat_card("ACTIVE", "0", "stat_active")
        self.stat_success = self.create_stat_card("SUCCESS", "0", "stat_success")
        self.stats_row.addWidget(self.stat_profiles)
        self.stats_row.addWidget(self.stat_active)
        self.stats_row.addWidget(self.stat_success)
        header_layout.addLayout(self.stats_row)
        
        header_layout.addStretch()

        self.btn_theme = QPushButton("☀️ Light Mode")
        self.btn_theme.setFixedSize(130, 38)
        self.btn_theme.setObjectName("btn_nav_theme")
        self.btn_theme.clicked.connect(self.toggle_theme)
        header_layout.addWidget(self.btn_theme)
        
        header_layout.addSpacing(10)

        self.btn_settings_nav = QPushButton("⚙️ Settings")
        self.btn_settings_nav.setFixedSize(130, 38)
        self.btn_settings_nav.setObjectName("btn_nav_accent")
        self.btn_settings_nav.clicked.connect(lambda: self.switch_page(1))
        header_layout.addWidget(self.btn_settings_nav)
        
        layout.addLayout(header_layout)

        # MAIN CONTENT (Split)
        content_split = QHBoxLayout()
        content_split.setSpacing(25)

        # LEFT: Manager
        left_panel = QFrame()
        left_panel.setObjectName("panel_main")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(20, 20, 20, 20)
        
        # Search and Category Filter
        filter_layout = QHBoxLayout()
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("🔍 Search accounts, UIDs...")
        self.search_bar.setObjectName("search_bar_main")
        self.search_bar.setFixedHeight(40)
        self.search_bar.textChanged.connect(self.filter_accounts)
        
        self.cat_filter = QComboBox()
        self.cat_filter.setFixedHeight(40)
        self.cat_filter.setFixedWidth(150)
        self.cat_filter.currentIndexChanged.connect(self.filter_accounts)
        
        filter_layout.addWidget(self.search_bar, 7)
        filter_layout.addWidget(self.cat_filter, 3)
        left_layout.addLayout(filter_layout)

        # Toolbars layout
        toolbars_layout = QVBoxLayout()
        toolbars_layout.setSpacing(10)
        
        # Top Toolbar (Account Management)
        toolbar_top = QHBoxLayout()
        toolbar_top.setSpacing(8)
        self.btn_bulk = QPushButton("📥 ADD Account")
        self.btn_sel_all = QPushButton("✅ Select All")
        self.btn_sel_none = QPushButton("⬛ None")
        self.btn_manage_cats = QPushButton("📁 Categories")
        self.btn_del_accounts = QPushButton("🗑️ លុបគណនី (Del)")
        self.btn_set_cat = QPushButton("🏷️ Set Category")
        
        self.btn_bulk.setObjectName("btn_add_account")
        self.btn_sel_all.setObjectName("btn_select_all")
        self.btn_sel_none.setObjectName("btn_select_none")
        self.btn_manage_cats.setObjectName("btn_categories")
        self.btn_del_accounts.setObjectName("btn_delete_accounts")
        self.btn_set_cat.setObjectName("btn_set_category")
        
        for btn in [self.btn_bulk, self.btn_sel_all, self.btn_sel_none, self.btn_manage_cats, self.btn_del_accounts, self.btn_set_cat]:
            btn.setFixedHeight(32)
            toolbar_top.addWidget(btn)
            
        self.btn_bulk.clicked.connect(self.show_bulk_add_dialog)
        self.btn_sel_all.clicked.connect(lambda: self.toggle_selection(True))
        self.btn_sel_none.clicked.connect(lambda: self.toggle_selection(False))
        self.btn_manage_cats.clicked.connect(self.show_manage_cats_dialog)
        self.btn_del_accounts.clicked.connect(self.delete_selected_accounts)
        self.btn_set_cat.clicked.connect(self.show_set_cat_dialog)
        
        toolbar_top.addStretch()
        
        # Stat counters that update dynamically
        self.lbl_sel_count = QLabel("Selected: 0")
        self.lbl_sel_count.setObjectName("card_info")
        toolbar_top.addWidget(self.lbl_sel_count)


        # Bottom Toolbar (Execution controls)
        toolbar_bottom = QHBoxLayout()
        toolbar_bottom.setSpacing(8)
        
        self.spin_threads = QSpinBox(); self.spin_threads.setRange(1, 100); self.spin_threads.setValue(8)
        self.spin_batch = QSpinBox(); self.spin_batch.setRange(1, 50); self.spin_batch.setValue(3)
        for sb in [self.spin_threads, self.spin_batch]:
            sb.setFixedSize(65, 28)

        toolbar_bottom.addWidget(QLabel("🧵 Threads:"))
        toolbar_bottom.addWidget(self.spin_threads)
        toolbar_bottom.addSpacing(10)
        toolbar_bottom.addWidget(QLabel("📦 Batch:"))
        toolbar_bottom.addWidget(self.spin_batch)

        toolbar_bottom.addSpacing(20)
        
        # 🚀 START & 🛑 STOP ALL Buttons
        self.btn_execute = QPushButton("🚀 START")
        self.btn_execute.setObjectName("btn_execute_toolbar")
        self.btn_execute.setFixedSize(110, 32)
        self.btn_execute.clicked.connect(self.run_selected_task)

        self.btn_stop_all = QPushButton("🛑 STOP ALL")
        self.btn_stop_all.setObjectName("btn_stop_all_toolbar")
        self.btn_stop_all.setFixedSize(110, 32)
        self.btn_stop_all.clicked.connect(self.stop_all_active)
        toolbar_bottom.addWidget(self.btn_execute)
        toolbar_bottom.addSpacing(10)
        toolbar_bottom.addWidget(self.btn_stop_all)
        
        toolbar_bottom.addStretch()

        toolbars_layout.addLayout(toolbar_top)
        toolbars_layout.addLayout(toolbar_bottom)
        
        left_layout.addLayout(toolbars_layout)

        # Table Header
        header_table = QFrame()
        header_table.setObjectName("table_head_frame")
        header_table.setFixedHeight(35)
        htl = QHBoxLayout(header_table)
        htl.setContentsMargins(15, 0, 15, 0)
        htl.setSpacing(12)
        
        # Precise alignment columns: [Text, Width]
        cols = [
            ("#", 40), 
            ("🔘", 30), 
            ("USER", 130), 
            ("UID", 180), 
            ("NAME", 220), 
            ("STATUS", 120)
        ]
        for text, w in cols:
            lb = QLabel(text); lb.setObjectName("label_table_head")
            lb.setFixedWidth(w)
            htl.addWidget(lb)
        htl.addStretch()
        left_layout.addWidget(header_table)

        # Scroll Area
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setObjectName("main_scroll")
        
        # New SelectionContainer for Drag-to-Select
        self.scroll_widget = SelectionContainer(self)
        self.accounts_layout = QVBoxLayout(self.scroll_widget)
        self.accounts_layout.setAlignment(Qt.AlignTop)
        self.accounts_layout.setContentsMargins(5, 5, 5, 10)
        self.accounts_layout.setSpacing(8)
        self.scroll.setWidget(self.scroll_widget)
        left_layout.addWidget(self.scroll)
        
        content_split.addWidget(left_panel, 7)
        self.right_panel = QFrame()
        self.right_panel.setFixedWidth(320)
        self.right_panel.setObjectName("panel_main")
        right_panel_layout = QVBoxLayout(self.right_panel)
        right_panel_layout.setContentsMargins(5, 5, 5, 5)

        self.sidebar_tabs = QTabWidget()
        
        # --- TAB 1: AUTO FLOW (Tasks) ---
        tab_flow = QWidget()
        flow_v = QVBoxLayout(tab_flow)
        flow_v.setContentsMargins(5, 5, 5, 5)
        
        flow_scroll = QScrollArea()
        flow_scroll.setWidgetResizable(True)
        flow_scroll.setFrameShape(QFrame.NoFrame)
        flow_container = QWidget()
        flow_layout = QVBoxLayout(flow_container)
        flow_layout.setContentsMargins(5, 5, 5, 5)
        flow_layout.setSpacing(10)

        # Re-using the logic cards for grouping tasks
        # Group 1: Engagement
        c_eng = self.create_config_card("🎭 Engagement", "config_card_eng")
        l_eng = QGridLayout(c_eng)
        
        # Group 2: Growth
        c_grw = self.create_config_card("🚀 Growth", "config_card_grw")
        l_grw = QGridLayout(c_grw)
        
        # Group 3: Content
        c_cnt = self.create_config_card("📝 Content", "config_card_cnt")
        l_cnt = QGridLayout(c_cnt)

        # SpinBoxes
        self.spin_invite = QSpinBox(); self.spin_invite.setRange(1, 500); self.spin_invite.setValue(25)
        self.spin_confirm = QSpinBox(); self.spin_confirm.setRange(1, 1000); self.spin_confirm.setValue(50)
        self.spin_add_friend = QSpinBox(); self.spin_add_friend.setRange(1, 500); self.spin_add_friend.setValue(10)
        self.spin_feed_mins = QSpinBox(); self.spin_feed_mins.setRange(1, 240); self.spin_feed_mins.setValue(5)
        self.spin_video_mins = QSpinBox(); self.spin_video_mins.setRange(1, 240); self.spin_video_mins.setValue(5)
        self.spin_join_group = QSpinBox(); self.spin_join_group.setRange(1, 100); self.spin_join_group.setValue(3)
        self.spin_share_group = QSpinBox(); self.spin_share_group.setRange(1, 100); self.spin_share_group.setValue(3)
        self.spin_story = QSpinBox(); self.spin_story.setRange(1, 500); self.spin_story.setValue(5)
        self.spin_scrape_limit = QSpinBox(); self.spin_scrape_limit.setRange(10, 5000); self.spin_scrape_limit.setValue(100)
        
        for sb in [self.spin_invite, self.spin_confirm, self.spin_add_friend, self.spin_feed_mins, self.spin_video_mins, 
                   self.spin_join_group, self.spin_share_group, self.spin_story, self.spin_scrape_limit]:
            sb.setFixedSize(65, 28)

        self.tasks_check = {
            "login": (QRadioButton("🔑 Login & Run"), None, l_eng, 0),
            "warmup": (QRadioButton("🔥 Warm-Up"), None, l_eng, 1),
            "feeds": (QRadioButton("📰 Scroll Feeds"), self.spin_feed_mins, l_eng, 2),
            "watch_video": (QRadioButton("📺 Watch Video"), self.spin_video_mins, l_eng, 3),
            "watch_stories": (QRadioButton("👀 Story Viewer"), self.spin_story, l_eng, 4),
            
            "invite": (QRadioButton("📨 Invite Friends"), self.spin_invite, l_grw, 0),
            "add_friend": (QRadioButton("👥 Add Friends"), self.spin_add_friend, l_grw, 1),
            "confirm_friend": (QRadioButton("✅ Confirm All"), self.spin_confirm, l_grw, 2),
            "join_groups": (QRadioButton("🫂 Join Groups"), self.spin_join_group, l_grw, 3),
            
            "share_groups": (QRadioButton("🔄 Share Post"), self.spin_share_group, l_cnt, 0),
            "invite_like": (QRadioButton("📡 Invite Like"), None, l_cnt, 1),
            "post_photo": (QRadioButton("📷 Post Photo"), None, l_cnt, 2),
            "post_reel": (QRadioButton("🎬 Post Reel"), None, l_cnt, 3),
            "scrape_uids": (QRadioButton("🧲 Scrape UIDs"), self.spin_scrape_limit, l_cnt, 4)
        }

        for k, (rb, sb, task_layout, row) in self.tasks_check.items():
            rb.setAutoExclusive(False)
            if k == "login": rb.setChecked(True)
            rb.setStyleSheet("font-size: 11px;")
            task_layout.addWidget(rb, row, 0)
            if sb:
                task_layout.addWidget(sb, row, 1)
                unit = "m" if k in ["feeds", "watch_video", "warmup"] else "ct"
                ulbl = QLabel(unit); ulbl.setStyleSheet("font-size: 9px; opacity: 0.5;")
                task_layout.addWidget(ulbl, row, 2)

        flow_layout.addWidget(c_eng)
        flow_layout.addWidget(c_grw)
        flow_layout.addWidget(c_cnt)
        flow_layout.addStretch()
        
        flow_scroll.setWidget(flow_container)
        flow_v.addWidget(flow_scroll)
        self.sidebar_tabs.addTab(tab_flow, "🤖 Tasks")

        # --- TAB 2: PARAMS (Targeting & Post Content) ---
        tab_params = QWidget()
        params_v = QVBoxLayout(tab_params)
        params_v.setContentsMargins(5, 5, 5, 5)
        
        params_scroll = QScrollArea()
        params_scroll.setWidgetResizable(True)
        params_scroll.setFrameShape(QFrame.NoFrame)
        params_container = QWidget()
        params_layout = QVBoxLayout(params_container)
        params_layout.setContentsMargins(5, 5, 5, 5)
        params_layout.setSpacing(10)

        # Target List Card
        c_tgt = self.create_config_card("🔗 Target List", "config_card_tgt")
        l_tgt = QVBoxLayout(c_tgt)
        self.target_list = QListWidget()
        self.target_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.target_list.setFixedHeight(120)
        self.refresh_target_combo()
        
        t_btns = QHBoxLayout()
        btn_manage = QPushButton("⚙️ Edit"); btn_manage.setObjectName("btn_action_small")
        btn_manage.clicked.connect(self.show_links_dialog)
        btn_del_target = QPushButton("🗑️ Del"); btn_del_target.setObjectName("btn_danger_small")
        btn_del_target.clicked.connect(self.delete_selected_targets)
        t_btns.addWidget(btn_manage); t_btns.addWidget(btn_del_target)
        
        l_tgt.addLayout(t_btns)
        l_tgt.addWidget(self.target_list)

        # Content Card (Post Video & Image Settings)
        c_pst = self.create_config_card("🎬 Post Video & Image Settings", "config_card_pst")
        l_pst = QVBoxLayout(c_pst)
        l_pst.setSpacing(12)
        
        # 1. Media Group
        g_media = QGroupBox("📁 Local Media Files")
        form_media = QFormLayout(g_media)
        form_media.setSpacing(10)
        
        self.edit_photo_path = QLineEdit(self.app_settings.get("photo_path", ""))
        self.btn_browse_photo = QPushButton("📁 Browse Image")
        self.btn_browse_photo.setCursor(Qt.PointingHandCursor)
        self.btn_browse_photo.clicked.connect(lambda: self.browse_file(self.edit_photo_path, "Images (*.png *.jpg *.jpeg)"))
        ph_lay = QHBoxLayout(); ph_lay.addWidget(self.edit_photo_path); ph_lay.addWidget(self.btn_browse_photo)
        
        self.edit_video_path = QLineEdit(self.app_settings.get("video_path", ""))
        self.btn_browse_video = QPushButton("📁 Browse Video")
        self.btn_browse_video.setCursor(Qt.PointingHandCursor)
        self.btn_browse_video.clicked.connect(lambda: self.browse_file(self.edit_video_path, "Videos (*.mp4 *.mov *.avi)"))
        vd_lay = QHBoxLayout(); vd_lay.addWidget(self.edit_video_path); vd_lay.addWidget(self.btn_browse_video)
        
        form_media.addRow(QLabel("Photo / Image:"), ph_lay)
        form_media.addRow(QLabel("Video File:"), vd_lay)
        
        # 2. Text Content Group
        g_content = QGroupBox("📝 Post Content & Description")
        layout_content = QVBoxLayout(g_content)
        layout_content.setSpacing(8)
        
        self.edit_caption = QTextEdit()
        self.edit_caption.setPlaceholderText("Write your post caption or description here...")
        self.edit_caption.setFixedHeight(80)
        self.edit_caption.setPlainText(self.app_settings.get("post_caption", ""))
        
        layout_content.addWidget(QLabel("Post Caption:"))
        layout_content.addWidget(self.edit_caption)
        
        # 3. Targeting & Action Group
        g_targeting = QGroupBox("⚙️ Targeting & Actions")
        form_targeting = QFormLayout(g_targeting)
        form_targeting.setSpacing(10)
        
        self.edit_kwd = QLineEdit("Shopping")
        self.chk_reaction = QCheckBox("Auto-Reaction (Random Reaction)")
        
        form_targeting.addRow(QLabel("Search Keyword:"), self.edit_kwd)
        form_targeting.addRow(self.chk_reaction)
        
        l_pst.addWidget(g_media)
        l_pst.addWidget(g_content)
        l_pst.addWidget(g_targeting)

        params_layout.addWidget(c_tgt)
        params_layout.addStretch()
        
        params_scroll.setWidget(params_container)
        params_v.addWidget(params_scroll)
        self.sidebar_tabs.addTab(tab_params, "🎯 Config")

        # --- TAB 3: Post Video & Image ---
        tab_post_scrape = QWidget()
        post_scrape_v = QVBoxLayout(tab_post_scrape)
        post_scrape_v.setContentsMargins(5, 5, 5, 5)
        
        post_scrape_scroll = QScrollArea()
        post_scrape_scroll.setWidgetResizable(True)
        post_scrape_scroll.setFrameShape(QFrame.NoFrame)
        post_scrape_container = QWidget()
        post_scrape_layout = QVBoxLayout(post_scrape_container)
        post_scrape_layout.setContentsMargins(5, 5, 5, 5)
        post_scrape_layout.setSpacing(10)
        
        post_scrape_layout.addWidget(c_pst)
        post_scrape_layout.addStretch()
        
        post_scrape_scroll.setWidget(post_scrape_container)
        post_scrape_v.addWidget(post_scrape_scroll)
        self.sidebar_tabs.addTab(tab_post_scrape, "🎬 Post Video & Image")

        # --- TAB 3: SYSTEM ---
        tab_sys = QWidget()
        sys_v = QVBoxLayout(tab_sys)
        c_sys = self.create_config_card("🛡️ System Tools", "config_card_sys")
        l_sys = QVBoxLayout(c_sys)
        
        btn_backup = QPushButton("💾 Backup Database")
        btn_update = QPushButton("🔄 Check for Update")
        btn_stop = QPushButton("🛑 EMERGENCY STOP")
        btn_backup.setObjectName("btn_action_small")
        btn_update.setObjectName("btn_action_small")
        btn_stop.setObjectName("btn_danger")
        btn_stop.setFixedHeight(45)
        
        btn_backup.clicked.connect(self.backup_entire_database)
        btn_update.clicked.connect(self.auto_update_app)
        btn_stop.clicked.connect(self.stop_all_active)
        
        l_sys.addWidget(btn_backup)
        l_sys.addWidget(btn_update)
        l_sys.addSpacing(20)
        l_sys.addWidget(btn_stop)
        l_sys.addStretch()
        
        sys_v.addWidget(c_sys)
        sys_v.addStretch()
        self.sidebar_tabs.addTab(tab_sys, "⚙️ System")

        # Finally add tabs to right panel
        right_panel_layout.addWidget(self.sidebar_tabs)
        
        # Correctly store just the radio buttons for logic (keeping 100% compatibility)
        self.tasks_check = {k: v[0] for k, v in self.tasks_check.items()}
        
        content_split.addWidget(self.right_panel, 3)
        layout.addLayout(content_split)

    def setup_settings_page(self):
        self.page_settings = QWidget()
        l = QVBoxLayout(self.page_settings)
        l.setContentsMargins(60, 40, 60, 60)
        
        header = QHBoxLayout()
        lbl = QLabel("⚙️ Global System Settings")
        lbl.setObjectName("brand_title")
        header.addWidget(lbl)
        header.addStretch()
        btn_back = QPushButton("🔙 Back to Workspace")
        btn_back.clicked.connect(lambda: self.switch_page(0))
        btn_back.setObjectName("btn_action_small")
        header.addWidget(btn_back)
        l.addLayout(header)
        l.addSpacing(40)
        
        self.ua_edit = QLineEdit(self.app_settings.get("default_ua", ""))
        self.max_threads_edit = QLineEdit(str(self.app_settings.get("max_threads", 8)))
        
        for text, edit in [("Global Default User Agent:", self.ua_edit), 
                           ("Parallel Thread Limit:", self.max_threads_edit)]:
            l.addWidget(QLabel(text))
            l.addWidget(edit)
            l.addSpacing(15)
        
        l.addStretch()
        btn_save = QPushButton("Apply Global Settings")
        btn_save.setFixedHeight(50)
        btn_save.setObjectName("btn_execute_main")
        btn_save.clicked.connect(self.apply_settings)
        l.addWidget(btn_save)

    def create_stat_card(self, title, val, obj_name):
        f = QFrame(); f.setObjectName(f"stat_card_{obj_name}")
        l = QVBoxLayout(f); l.setContentsMargins(20, 12, 20, 12); l.setSpacing(5)
        t = QLabel(title); t.setObjectName("stat_title_label")
        v = QLabel(val); v.setObjectName("stat_value_label")
        v.setProperty("stat_id", obj_name)
        l.addWidget(t); l.addWidget(v)
        return f

    def create_config_card(self, title, obj_name):
        f = QFrame(); f.setObjectName(obj_name)
        return f

    def switch_page(self, index):
        """Standard Dynamic Page Switch with Fade Effect"""
        if self.pages.currentIndex() == index: return
        
        # Setup Animation
        self.anim = QPropertyAnimation(self.page_opacity_effect, b"opacity")
        self.anim.setDuration(250)
        self.anim.setStartValue(1.0)
        self.anim.setEndValue(0.0)
        
        def on_fade_out():
            self.pages.setCurrentIndex(index)
            self.anim2 = QPropertyAnimation(self.page_opacity_effect, b"opacity")
            self.anim2.setDuration(250)
            self.anim2.setStartValue(0.0)
            self.anim2.setEndValue(1.0)
            self.anim2.start()
            
        self.anim.finished.connect(on_fade_out)
        self.anim.start()

    def filter_accounts(self, *args):
        text = self.search_bar.text().lower()
        selected_cat = self.cat_filter.currentText()
        
        for i in range(self.accounts_layout.count()):
            w = self.accounts_layout.itemAt(i).widget()
            if isinstance(w, AccountCard):
                d = w.acc_data
                name_uid_match = (text in d.get('name','').lower() or text in d.get('uid','').lower() or text in d.get('username','').lower())
                cat_match = (selected_cat == "All Categories" or d.get('category', 'No Category') == selected_cat)
                w.setVisible(name_uid_match and cat_match)

    def load_accounts(self):
        self.update_stats()
        data = load_data()
        
        # Update Category Filter dynamically
        self.update_category_filter()

        while self.accounts_layout.count():
            it = self.accounts_layout.takeAt(0)
            if it.widget(): it.widget().deleteLater()
        for i, acc in enumerate(data):
            card = AccountCard(acc, self, i + 1)
            self.accounts_layout.addWidget(card)
        self.filter_accounts()

    def update_stats(self):
        data = load_data()
        active = len([t for t in self.active_threads if t.isRunning()])
        
        stats = {
            "stat_profiles": str(len(data)),
            "stat_active": str(active),
            "stat_success": str(self.success_count)
        }
        
        for lbl in self.findChildren(QLabel):
            if lbl.property("stat_id") in stats:
                lbl.setText(stats[lbl.property("stat_id")])

    def apply_settings(self):
        try:
            self.app_settings.update({"default_ua": self.ua_edit.text(), "max_threads": int(self.max_threads_edit.text())})
            save_settings(self.app_settings); QMessageBox.information(self, "ជោគជ័យ", "រក្សាទុករួចរាល់។")
        except: pass

    def get_window_position(self, index):
        """Pure Grid Tiling System for perfect row/column alignment"""
        # Load EXACT dimensions from settings or standardized defaults
        tile_w = self.app_settings.get("tile_width", 400)
        tile_h = self.app_settings.get("tile_height", 700)
        
        # Gap between windows
        gap = 10
        
        geom = QApplication.primaryScreen().availableGeometry()
        
        # Number of columns and rows that can fit once
        cols = max(1, geom.width() // (tile_w + gap))
        
        # Grid index calculation
        col = index % cols
        row = (index // cols)
        
        # X and Y based on grid, no fancy cascading to keep it level/equal (ស្មើរៗគ្នា)
        x = geom.x() + (col * (tile_w + gap))
        y = geom.y() + (row * 30) # Vertical stacking offset if we run out of space horizontally
        
        # Optional: Reset y to level rows if enough width exists
        rows_per_screen = max(1, geom.height() // (tile_h + gap))
        actual_row = (index // cols) % rows_per_screen
        y = geom.y() + (actual_row * (tile_h + gap))
             
        return x, y

    def toggle_selection(self, state):
        for i in range(self.accounts_layout.count()):
            w = self.accounts_layout.itemAt(i).widget()
            if isinstance(w, AccountCard) and w.isVisible():
                w.chk_select.setChecked(state)

    def run_selected_task(self):
        tasks = [k for k, v in self.tasks_check.items() if v.isChecked()]
        if not tasks: return QMessageBox.warning(self, "No Task", "សូមជ្រើសរើសកិច្ចការយ៉ាងតិចមួយ។")
        self.task_queue_order = tasks
        
        self.app_settings["invite_count"] = self.spin_invite.value()
        self.app_settings["confirm_friend_count"] = self.spin_confirm.value()
        self.app_settings["add_friend_count"] = self.spin_add_friend.value()
        self.app_settings["feed_mins"] = self.spin_feed_mins.value()
        self.app_settings["video_feed_mins"] = self.spin_video_mins.value()
        self.app_settings["join_group_count"] = self.spin_join_group.value()
        self.app_settings["share_group_count"] = self.spin_share_group.value()
        self.app_settings["story_count"] = self.spin_story.value()
        self.app_settings["scrape_limit"] = self.spin_scrape_limit.value()
        self.app_settings["group_keyword"] = self.edit_kwd.text()
        self.app_settings["random_reactions"] = self.chk_reaction.isChecked()
        self.app_settings["photo_path"] = self.edit_photo_path.text()
        self.app_settings["video_path"] = self.edit_video_path.text()
        self.app_settings["post_caption"] = self.edit_caption.toPlainText()
        save_settings(self.app_settings)
        
        selected = [w for i in range(self.accounts_layout.count()) if isinstance(w := self.accounts_layout.itemAt(i).widget(), AccountCard) and w.isVisible() and w.chk_select.isChecked()]
        
        sel_items = self.target_list.selectedItems()
        active_targets = [item.text() for item in sel_items] if sel_items else []
        
        # Fallback to All standard links if user didn't select anything specifically
        if not active_targets:
            all_links = self.app_settings.get("invite_links", [])
            active_targets = all_links if all_links else []
            
        for card in selected:
            if card.current_thread and card.current_thread.isRunning(): continue
            if "invite" in tasks or "share_groups" in tasks or "scrape_uids" in tasks:
                if active_targets:
                    num_links = len(active_targets)
                    card.acc_data["current_invite_url"] = active_targets[self.rotation_index % num_links]
                    self.rotation_index += 1
            self.pending_launch_queue.append((card, list(tasks)))

    def process_launch_queue(self):
        # 1. Refresh Active Processes
        self.active_threads = [t for t in self.active_threads if t.isRunning()]
        self.update_stats()
        
        # 2. Cleanup Slots (Only keep slots for running UIDs)
        running_uids = [t.acc_data.get("uid") for t in self.active_threads]
        self.active_slots = {uid: slot for uid, slot in self.active_slots.items() if uid in running_uids}
        used_indices = set(self.active_slots.values())
        
        # 3. Process Queue with Available Slots
        active_cnt = len(self.active_threads)
        limit = self.spin_threads.value()
        
        while active_cnt < limit and self.pending_launch_queue:
            card, tasks = self.pending_launch_queue.pop(0)
            if card.current_thread and card.current_thread.isRunning(): continue
            
            uid = card.acc_data.get("uid")
            
            # Find the FIRST EMPTY slot index (0, 1, 2, 3...)
            slot_idx = 0
            while slot_idx in used_indices:
                slot_idx += 1
            
            x, y = self.get_window_position(slot_idx)
            
            # Start Browser with determined unique position
            for t in tasks: 
                card.launch_browser(x, y, t)
            
            # Registry the slot
            self.active_slots[uid] = slot_idx
            used_indices.add(slot_idx)
            
            active_cnt += 1

    def show_add_dialog(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        form = QGridLayout()
        form.setSpacing(10)
        inputs = {}
        fields = [("Profile Name:", "name"), ("Login ID/User:", "uid"), ("Password:", "pass"), ("2FA Secret:", "2fa"), ("Proxy Server:", "proxy"), ("Category:", "category")]
        
        for i, (label, key) in enumerate(fields):
            form.addWidget(QLabel(label), i, 0)
            edit = QLineEdit()
            edit.setFixedHeight(35)
            form.addWidget(edit, i, 1)
            inputs[key] = edit
            
        btn_save = QPushButton("💾 Save Profile")
        btn_save.setFixedHeight(40)
        btn_save.setObjectName("btn_execute_toolbar")
        
        layout.addLayout(form)
        layout.addSpacing(15)
        layout.addWidget(btn_save)
        
        def commit_add():
            uid = inputs["uid"].text() or str(int(time.time()))
            p_path = os.path.join(os.getcwd(), "profiles", f"profile_{uid}")
            os.makedirs(p_path, exist_ok=True)
            acc = {k: v.text() for k, v in inputs.items()}
            if not acc.get("category"): acc["category"] = "No Category"
            acc.update({"type": "Facebook Mobile", "ua": self.app_settings.get("default_ua", ""), "profile_path": p_path})
            data = load_data()
            data.append(acc)
            save_data(data)
            self.load_accounts()
            self.hide_custom_popup()
            
        btn_save.clicked.connect(commit_add)
        self.show_custom_popup(widget, "➕ Add New Social Profile")

    def show_bulk_add_dialog(self, default_cat=None):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        txt = QPlainTextEdit()
        txt.setPlaceholderText("UID|PASS|2FA|CATEGORY (Category is optional)")
        txt.setMinimumHeight(150)
        
        btn_import = QPushButton("📥 Import & Save")
        btn_import.setFixedHeight(40)
        btn_import.setObjectName("btn_execute_toolbar")
        
        layout.addWidget(QLabel("Paste your account details in format below:"))
        layout.addWidget(txt)
        
        cat_row = QHBoxLayout()
        self.import_cat_combo = QComboBox()
        user_cats = self.app_settings.get("user_categories", ["No Category", "Personal", "Work"])
        self.import_cat_combo.addItems(user_cats)
        if default_cat and default_cat in user_cats:
            self.import_cat_combo.setCurrentText(default_cat)
            
        cat_row.addWidget(QLabel("Default Category:"))
        cat_row.addWidget(self.import_cat_combo)
        layout.addLayout(cat_row)
        
        layout.addSpacing(10)
        layout.addWidget(btn_import)
        
        def commit_import():
            raw = txt.toPlainText().strip()
            if not raw: return
            default_cat = self.import_cat_combo.currentText()
            all_accs = load_data()
            count = 0
            for line in raw.split("\n"):
                p = line.split("|")
                if len(p) >= 2:
                    uid = p[0].strip()
                    p_path = os.path.join(os.getcwd(), "profiles", f"profile_{uid}")
                    os.makedirs(p_path, exist_ok=True)
                    
                    cat = p[3].strip() if len(p) >= 4 else default_cat
                    
                    all_accs.append({
                        "name": f"FB {uid[-4:]}", 
                        "uid": uid, 
                        "pass": p[1].strip(), 
                        "2fa": p[2].strip() if len(p)>=3 else "", 
                        "category": cat,
                        "profile_path": p_path, 
                        "type": "Facebook Mobile", 
                        "ua": self.app_settings.get("default_ua", "")
                    })
                    count += 1
            save_data(all_accs)
            self.load_accounts()
            self.hide_custom_popup()
            QMessageBox.information(self, "Success", f"បានបន្ថែម {count} គណនីថ្មីដោយជោគជ័យ!")
            
        btn_import.clicked.connect(commit_import)
        self.show_custom_popup(widget, "📥 Bulk Account Import")

    def show_edit_dialog(self, data):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        form = QGridLayout()
        form.setSpacing(10)
        inputs = {}
        fields = [("Name:", "name"), ("UID:", "uid"), ("Password:", "pass"), ("2FA Secret:", "2fa"), ("Proxy:", "proxy"), ("Category:", "category")]
        
        for i, (label, key) in enumerate(fields):
            form.addWidget(QLabel(label), i, 0)
            edit = QLineEdit(data.get(key, ""))
            edit.setFixedHeight(35)
            form.addWidget(edit, i, 1)
            inputs[key] = edit
            
        btn_save = QPushButton("💾 Save Changes")
        btn_save.setFixedHeight(40)
        btn_save.setObjectName("btn_execute_toolbar")
        
        layout.addLayout(form)
        layout.addSpacing(15)
        layout.addWidget(btn_save)
        
        def commit_edit():
            all_d = load_data()
            for a in all_d:
                if a.get('profile_path') == data.get('profile_path'):
                    a.update({k: v.text() for k, v in inputs.items()})
                    if not a.get("category"): a["category"] = "No Category"
            save_data(all_d)
            self.load_accounts()
            self.hide_custom_popup()
            
        btn_save.clicked.connect(commit_edit)
        self.show_custom_popup(widget, f"✏️ Edit Profile: {data.get('uid', '')}")

    def show_links_dialog(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        txt = QPlainTextEdit()
        txt.setPlainText("\n".join(self.app_settings.get("invite_links", [])))
        txt.setMinimumHeight(200)
        txt.setPlaceholderText("Paste one link per line here...")
        
        btn_save = QPushButton("💾 រក្សាទុក (Save Links)")
        btn_save.setFixedHeight(40)
        btn_save.setObjectName("btn_execute_toolbar")
        
        layout.addWidget(QLabel("បញ្ជីទិន្នន័យចំណងជើង Page URLs (Link ១ តម្រង់ជួរ ១ខ្សែបន្ទាត់):"))
        layout.addWidget(txt)
        layout.addSpacing(10)
        layout.addWidget(btn_save)
        
        def commit_links():
            self.app_settings["invite_links"] = [l.strip() for l in txt.toPlainText().split("\n") if l.strip()]
            save_settings(self.app_settings)
            self.refresh_target_combo()
            self.hide_custom_popup()
            
        btn_save.clicked.connect(commit_links)
        self.show_custom_popup(widget, "🔗 គ្រប់គ្រងលេខសម្គាល់គោលដៅ")

    def show_manage_cats_dialog(self):
        from PySide6.QtWidgets import QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(12)
        
        # Category Table (More standard than simple list)
        self.cat_table = QTableWidget(0, 3)
        self.cat_table.setHorizontalHeaderLabels(["Category Name", "Accounts", "Actions"])
        self.cat_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.cat_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.cat_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.cat_table.verticalHeader().setVisible(False)
        self.cat_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.cat_table.setObjectName("main_scroll")
        self.cat_table.setMinimumHeight(250)
        self.cat_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.cat_table.customContextMenuRequested.connect(self.show_cat_table_context_menu)
        
        self.refresh_cat_table()
        
        input_layout = QHBoxLayout()
        self.new_cat_input = QLineEdit()
        self.new_cat_input.setPlaceholderText("Enter new category name...")
        self.new_cat_input.setFixedHeight(35)
        btn_add = QPushButton("➕ Create Category")
        btn_add.setObjectName("btn_execute_toolbar")
        btn_add.setFixedHeight(35)
        btn_add.clicked.connect(self.add_category_item)
        input_layout.addWidget(self.new_cat_input)
        input_layout.addWidget(btn_add)
        
        layout.addWidget(QLabel("<b>Organize Your Folders:</b>"))
        layout.addWidget(self.cat_table)
        layout.addLayout(input_layout)
        
        self.show_custom_popup(widget, "📁 Manage Category Folders")

    def refresh_cat_table(self):
        from PySide6.QtWidgets import QTableWidgetItem, QPushButton, QHBoxLayout, QWidget
        self.cat_table.setRowCount(0)
        user_cats = self.app_settings.get("user_categories", ["No Category"])
        data = load_data()
        
        for name in user_cats:
            row = self.cat_table.rowCount()
            self.cat_table.insertRow(row)
            
            # Name
            self.cat_table.setItem(row, 0, QTableWidgetItem(name))
            
            # Count
            cnt = sum(1 for a in data if a.get('category') == name)
            cnt_item = QTableWidgetItem(str(cnt))
            cnt_item.setTextAlignment(Qt.AlignCenter)
            self.cat_table.setItem(row, 1, cnt_item)
            
            # Actions
            btn_box = QWidget()
            btn_lay = QHBoxLayout(btn_box)
            btn_lay.setContentsMargins(5, 2, 5, 2)
            btn_lay.setSpacing(5)
            
            btn_import = QPushButton("📥 Import")
            btn_import.setObjectName("btn_execute_toolbar")
            btn_import.setFixedSize(70, 24)
            btn_import.clicked.connect(lambda checked, n=name: self.import_into_cat(n))
            
            btn_del = QPushButton("🗑️")
            btn_del.setObjectName("btn_danger_small")
            btn_del.setFixedSize(30, 24)
            btn_del.clicked.connect(lambda checked, n=name: self.delete_cat_by_name(n))
            
            btn_lay.addWidget(btn_import)
            btn_lay.addWidget(btn_del)
            self.cat_table.setCellWidget(row, 2, btn_box)

    def import_into_cat(self, cat_name):
        self.hide_custom_popup()
        QTimer.singleShot(250, lambda: self.show_bulk_add_dialog(cat_name))

    def delete_cat_by_name(self, name):
        if name == "No Category": return QMessageBox.warning(self, "Error", "Can't delete default category.")
        user_cats = self.app_settings.get("user_categories", [])
        if name in user_cats:
            user_cats.remove(name)
            self.app_settings["user_categories"] = user_cats
            save_settings(self.app_settings)
            self.refresh_cat_table()
            self.update_category_filter()

    def show_cat_table_context_menu(self, pos):
        from PySide6.QtWidgets import QMenu
        item = self.cat_table.itemAt(pos)
        if not item: return
        cat_name = self.cat_table.item(item.row(), 0).text()
        
        menu = QMenu()
        import_act = menu.addAction(f"📥 Bulk Import to '{cat_name}'")
        del_act = menu.addAction(f"🗑️ Delete folder '{cat_name}'")
        
        action = menu.exec(self.cat_table.mapToGlobal(pos))
        if action == import_act: self.import_into_cat(cat_name)
        elif action == del_act: self.delete_cat_by_name(cat_name)

    def add_category_item(self):
        name = self.new_cat_input.text().strip()
        if not name: return
        
        managed_cats = self.app_settings.get("user_categories", ["No Category"])
        if name not in managed_cats:
            managed_cats.append(name)
            self.app_settings["user_categories"] = managed_cats
            save_settings(self.app_settings)
            
            self.refresh_cat_table()
            self.update_category_filter()
            self.new_cat_input.clear()
            
            # ASK FOR IMPORT IMMEDIATELY
            reply = QMessageBox.question(self, "Import Now?", f"Category '{name}' ត្រូវបានបង្កើតជោគជ័យ! តើអ្នកចង់ Import account ចូលក្នុង Category នេះឥឡូវទេ?", QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                self.import_into_cat(name)

    def delete_category_item(self):
        it = self.cat_list_widget.currentItem()
        if it:
            self.cat_list_widget.takeItem(self.cat_list_widget.row(it))
            self.save_user_categories()

    def save_user_categories(self):
        cats = [self.cat_list_widget.item(i).text() for i in range(self.cat_list_widget.count())]
        self.app_settings["user_categories"] = cats
        save_settings(self.app_settings)
        # Update main filter and other dropdowns
        self.update_category_filter()

    def update_category_filter(self):
        """Sync main filter dropdown with settings and actual data"""
        current_selection = self.cat_filter.currentText()
        self.cat_filter.blockSignals(True)
        self.cat_filter.clear()
        self.cat_filter.addItem("All Categories")
        
        user_cats = self.app_settings.get("user_categories", ["No Category", "Personal", "Work"])
        data = load_data()
        actual_cats = set(acc.get('category', 'No Category') for acc in data)
        
        # Combine managed list with any specific categories found in data
        all_unique = sorted(list(set(user_cats) | actual_cats))
        if "No Category" in all_unique:
            all_unique.remove("No Category")
            all_unique.insert(0, "No Category")
            
        self.cat_filter.addItems(all_unique)
        
        if current_selection in [self.cat_filter.itemText(i) for i in range(self.cat_filter.count())]:
            self.cat_filter.setCurrentText(current_selection)
        self.cat_filter.blockSignals(False)

    def show_set_cat_dialog(self):
        """Move selected accounts to a specific category (Existing or New)"""
        selected_cards = [w for i in range(self.accounts_layout.count()) if isinstance(w := self.accounts_layout.itemAt(i).widget(), AccountCard) and w.isVisible() and w.chk_select.isChecked()]
        if not selected_cards:
            return QMessageBox.warning(self, "No Selection", "សូមជ្រើសរើសគណនីមុននឹងកំណត់ Category។")
        
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(15)
        
        layout.addWidget(QLabel(f"Assign category to <b>{len(selected_cards)}</b> selected profiles:"))
        
        # Option 1: Choose Existing
        layout.addWidget(QLabel("Choose Existing Category:"))
        combo = QComboBox()
        user_cats = self.app_settings.get("user_categories", ["No Category", "Personal", "Work"])
        combo.addItems(user_cats)
        layout.addWidget(combo)
        
        # Option 2: Create New
        layout.addWidget(QLabel("<b>OR</b> Create New Category:"))
        new_cat_edit = QLineEdit()
        new_cat_edit.setPlaceholderText("Type new category name here...")
        layout.addWidget(new_cat_edit)
        
        btn_apply = QPushButton("🚀 Apply Changes")
        btn_apply.setObjectName("btn_execute_toolbar")
        btn_apply.setFixedHeight(40)
        
        def commit_set_cat():
            new_cat_name = new_cat_edit.text().strip()
            final_cat = new_cat_name if new_cat_name else combo.currentText()
            
            # If it's a new category, save it to the global list too
            if new_cat_name:
                managed_cats = self.app_settings.get("user_categories", [])
                if new_cat_name not in managed_cats:
                    managed_cats.append(new_cat_name)
                    self.app_settings["user_categories"] = managed_cats
                    save_settings(self.app_settings)
            
            all_d = load_data()
            selected_paths = [c.acc_data.get('profile_path') for c in selected_cards]
            for a in all_d:
                if a.get('profile_path') in selected_paths:
                    a['category'] = final_cat
            save_data(all_d)
            self.load_accounts()
            self.hide_custom_popup()
            
        btn_apply.clicked.connect(commit_set_cat)
        layout.addWidget(btn_apply)
        
        self.show_custom_popup(widget, "🏷️ Set Account Category")

    def refresh_target_combo(self):
        self.target_list.clear()
        links = self.app_settings.get("invite_links", [])
        if links: 
            self.target_list.addItems(links)
            # Pre-select all by default if needed
            self.target_list.selectAll()
        else: 
            self.target_list.addItem("មិនទាន់មានទិន្នន័យ (Empty)")

    def delete_selected_targets(self):
        sel_items = self.target_list.selectedItems()
        if not sel_items:
            QMessageBox.warning(self, "Warning", "សូមជ្រើសរើសទិន្នន័យ (Links) យ៉ាងតិចមួយដើម្បីលុប។")
            return
            
        reply = QMessageBox.question(self, 'Confirm Delete', 
                                    f"អ្នកពិតជាចង់លុបទិន្នន័យចំនួន {len(sel_items)} នេះមែនទេ?", 
                                    QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            links = self.app_settings.get("invite_links", [])
            for item in sel_items:
                if item.text() in links:
                    links.remove(item.text())
            
            self.app_settings["invite_links"] = links
            save_settings(self.app_settings)
            self.refresh_target_combo()

    def backup_entire_database(self):
        try:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S"); b_path = os.path.join(os.getcwd(), "backups", f"full_backup_{ts}")
            os.makedirs(b_path, exist_ok=True); shutil.copy2("accounts.json", b_path); shutil.copy2("settings.json", b_path)
            QMessageBox.information(self, "ជោគជ័យ", "បម្រុងទុកទិន្នន័យរួចរាល់។")
        except Exception as e: QMessageBox.critical(self, "កំហុស", str(e))

    def stop_all_active(self):
        for i in range(self.accounts_layout.count()):
            w = self.accounts_layout.itemAt(i).widget()
            if isinstance(w, AccountCard): w.stop_browser()

    def auto_update_app(self):
        reply = QMessageBox.question(self, 'Update App', "តើអ្នកចង់ធ្វើការ Update កម្មវិធីទៅកាន់ Version ថ្មីមែនទេ?\nកម្មវិធីនឹងបិទបើកដោយស្វ័យប្រវត្តិ។", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            import subprocess
            try:
                bat_path = os.path.join(os.getcwd(), "update.bat")
                with open(bat_path, "w") as f:
                    f.write("@echo off\ntimeout /t 2 /nobreak\ngit pull\nstart python dashboard.py\nexit")
                subprocess.Popen(["cmd.exe", "/c", bat_path])
                sys.exit(0)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Update failed: {str(e)}")

    def browse_file(self, line_edit, file_filter):
        path, _ = QFileDialog.getOpenFileName(self, "Select File", "", file_filter)
        if path:
            line_edit.setText(path)

    def delete_selected_accounts(self):
        selected_cards = [self.accounts_layout.itemAt(i).widget() for i in range(self.accounts_layout.count()) 
                          if isinstance(self.accounts_layout.itemAt(i).widget(), AccountCard) 
                          and self.accounts_layout.itemAt(i).widget().chk_select.isChecked()]
        
        if not selected_cards:
            QMessageBox.warning(self, "Warning", "សូមជ្រើសរើស (Select) គណនីយ៉ាងតិចមួយដើម្បីលុប។")
            return
            
        reply = QMessageBox.question(self, 'Confirm Delete', 
                                    f"អ្នកពិតជាចង់លុបគណនីចំនួន {len(selected_cards)} នេះមែនទេ? ទិន្នន័យ Profile នឹងលុបចេញទាំងស្រុង។", 
                                    QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            all_d = load_data()
            paths_to_delete = [c.acc_data.get('profile_path') for c in selected_cards]
            
            # Remove from JSON memory
            all_d = [acc for acc in all_d if acc.get('profile_path') not in paths_to_delete]
            save_data(all_d)
            
            # Remove folders from system
            for path in paths_to_delete:
                try:
                    if os.path.exists(path):
                        import shutil
                        shutil.rmtree(path)
                except Exception as e:
                    print(f"Error deleting path {path}: {e}")
                    
            self.load_accounts()
            # Reset selection count
            self.lbl_sel_count.setText("Selected: 0")
            QMessageBox.information(self, "Deleted", f"បានលុបគណនីចំនួន {len(paths_to_delete)} ចេញដោយជោគជ័យ!")

class SelectionContainer(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.rubber_band = QRubberBand(QRubberBand.Rectangle, self)
        self.origin = QPoint()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.origin = event.position().toPoint()
            self.rubber_band.setGeometry(QRect(self.origin, QSize()))
            self.rubber_band.show()

    def mouseMoveEvent(self, event):
        if self.rubber_band.isVisible():
            self.rubber_band.setGeometry(QRect(self.origin, event.position().toPoint()).normalized())

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            rect = self.rubber_band.geometry()
            self.rubber_band.hide()
            
            if rect.width() < 5 and rect.height() < 5:
                return # Just a click, don't perform box selection

            # Use Local imports to avoid circular issues
            from widgets import AccountCard
            for child in self.findChildren(AccountCard):
                # Ensure we only select visible children (relevant when filtering)
                if child.isVisible() and rect.intersects(child.geometry()):
                    child.chk_select.setChecked(True)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

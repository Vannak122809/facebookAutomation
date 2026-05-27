LIGHT_THEME_STYLE = """
/* Global Styles */
QMainWindow, QDialog {
    background-color: #f8fafc;
}

QWidget {
    color: #0f172a;
    font-family: 'Khmer OS Battambang', 'Segoe UI', 'Roboto', 'Inter', -apple-system, sans-serif;
    font-size: 13px;
}

/* Scrollbars */
QScrollBar:vertical {
    border: none;
    background: #f1f5f9;
    width: 8px;
    margin: 0px;
    border-radius: 4px;
}
QScrollBar::handle:vertical {
    background: #cbd5e1;
    min-height: 25px;
    border-radius: 4px;
}
QScrollBar::handle:vertical:hover {
    background: #3b82f6;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar:horizontal {
    border: none;
    background: #f1f5f9;
    height: 8px;
    margin: 0px;
    border-radius: 4px;
}
QScrollBar::handle:horizontal {
    background: #cbd5e1;
    min-width: 25px;
    border-radius: 4px;
}
QScrollBar::handle:horizontal:hover {
    background: #3b82f6;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}

/* Titles and Labels */
QLabel#AppTitle {
    font-size: 20px;
    font-weight: 800;
    color: #ffffff;
    letter-spacing: 0.5px;
    background: transparent;
}

QLabel#SectionHeader {
    font-size: 15px;
    font-weight: 800;
    color: #0f172a;
    padding-bottom: 6px;
}

/* Form Styling */
QLabel#FormLabel {
    font-weight: 600;
    color: #475569;
    font-size: 12px;
}

/* Header Container */
QFrame#HeaderFrame {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1e3a8a, stop:1 #3b82f6);
    border: none;
    border-radius: 12px;
    padding: 15px;
}

/* Cards / Containers */
QFrame#CardFrame {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
}

QFrame#CardFrame:hover {
    border: 1px solid #3b82f6;
}

QFrame#ConfigCardFrame {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 16px;
}
QFrame#ConfigCardFrame:hover {
    border: 1px solid #cbd5e1;
}

/* Accounts Table Section (Top-right panel) */
QFrame#TableCardFrame {
    background-color: #ffffff;
    border: 1.5px solid #e2e8f0;
    border-radius: 12px;
}
QFrame#TableCardFrame:hover {
    border: 1.5px solid #10b981;
}

/* Logs Section (Bottom-right panel) */
QFrame#LogCardFrame {
    background-color: #ffffff;
    border: 1.5px solid #e2e8f0;
    border-radius: 12px;
}
QFrame#LogCardFrame:hover {
    border: 1.5px solid #8b5cf6;
}

QFrame#NestedCard {
    background-color: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
}

/* Text Inputs / TextEdits */
QLineEdit, QTextEdit {
    background-color: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 8px;
    padding: 6px 12px;
    color: #0f172a;
    selection-background-color: #3b82f6;
    selection-color: #ffffff;
    font-weight: 500;
}
QLineEdit:focus, QTextEdit:focus {
    border: 1px solid #3b82f6;
}

/* SpinBox / Slider */
QSpinBox {
    background-color: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 8px;
    color: #0f172a;
    font-weight: 700;
}
QSpinBox:focus {
    border: 1px solid #3b82f6;
}
QSpinBox QLineEdit {
    background: transparent !important;
    background-color: transparent !important;
    border: none !important;
    padding: 0px !important;
    margin: 0px !important;
    color: #0f172a !important;
    font-weight: 700 !important;
}
QSpinBox::up-button {
    subcontrol-origin: border;
    subcontrol-position: right;
    width: 22px;
    height: 28px;
    border: none;
    background: transparent;
}
QSpinBox::up-arrow {
    image: url("ui/plus.svg");
    width: 18px;
    height: 18px;
}
QSpinBox::up-arrow:hover {
    image: url("ui/plus_hover.svg");
}
QSpinBox::down-button {
    subcontrol-origin: border;
    subcontrol-position: left;
    width: 22px;
    height: 28px;
    border: none;
    background: transparent;
}
QSpinBox::down-arrow {
    image: url("ui/minus.svg");
    width: 18px;
    height: 18px;
}
QSpinBox::down-arrow:hover {
    image: url("ui/minus_hover.svg");
}

/* ComboBox (Dropdown) Styling */
QComboBox {
    background-color: #ffffff;
    border: 1.5px solid #cbd5e1;
    border-radius: 8px;
    padding: 6px 30px 6px 12px; /* Right padding to prevent text overlapping arrow */
    color: #0f172a;
    font-weight: 500;
}
QComboBox:hover {
    border: 1.5px solid #94a3b8;
    background-color: #f8fafc;
}
QComboBox:focus {
    border: 1.5px solid #3b82f6;
    background-color: #ffffff;
}

/* Dropdown arrow container */
QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 30px;
    border-left: none;
    border-top-right-radius: 8px;
    border-bottom-right-radius: 8px;
}

/* Dropdown arrow icon (Modern chevron down) */
QComboBox::down-arrow {
    image: url(data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCIgZmlsbD0ibm9uZSIgc3Ryb2tlPSIjNDc1NTY5IiBzdHJva2Utd2lkdGg9IjIuNSIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIiBzdHJva2UtbGluZWpvaW49InJvdW5kIj48cG9seWxpbmUgcG9pbnRzPSI2IDkgMTIgMTUgMTggOSI+PC9wb2x5bGluZT48L3N2Zz4=);
    width: 14px;
    height: 14px;
}

/* Dropdown Popup Menu (List View) */
QComboBox QAbstractItemView {
    background-color: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 8px;
    outline: none;
    padding: 4px;
}

/* Dropdown Popup Items */
QComboBox QAbstractItemView::item {
    height: 32px;
    border-radius: 6px;
    padding-left: 10px;
    color: #334155;
    background-color: transparent;
}

/* Dropdown Popup Items Hover state */
QComboBox QAbstractItemView::item:hover, QComboBox QAbstractItemView::item:selected {
    background-color: #eff6ff;
    color: #2563eb;
    font-weight: 600;
}

QSlider::groove:horizontal {
    border: 1px solid #e2e8f0;
    height: 6px;
    background: #e2e8f0;
    border-radius: 3px;
}
QSlider::sub-page:horizontal {
    background: #3b82f6;
    border-radius: 3px;
}
QSlider::handle:horizontal {
    background: #ffffff;
    border: 2px solid #3b82f6;
    width: 14px;
    height: 14px;
    margin-top: -5px;
    margin-bottom: -5px;
    border-radius: 8px;
}

/* Buttons */
QPushButton {
    background-color: #f1f5f9;
    border: 1px solid #cbd5e1;
    border-radius: 8px;
    padding: 8px 18px;
    color: #475569;
    font-weight: 600;
}
QPushButton:hover {
    background-color: #eff6ff;
    border: 1px solid #3b82f6;
    color: #2563eb;
}
QPushButton:pressed {
    background-color: #cbd5e1;
}

QPushButton#PrimaryButton {
    background-color: #3b82f6;
    border: none;
    color: #ffffff;
}
QPushButton#PrimaryButton:hover {
    background-color: #2563eb;
}
QPushButton#PrimaryButton:pressed {
    background-color: #1d4ed8;
}

QPushButton#SuccessButton {
    background-color: #10b981;
    border: none;
    color: #ffffff;
    border-radius: 10px;
    font-weight: 700;
    font-size: 13px;
}
QPushButton#SuccessButton:hover {
    background-color: #059669;
}
QPushButton#SuccessButton:pressed {
    background-color: #047857;
}

QPushButton#DangerButton {
    background-color: #ef4444;
    border: none;
    color: #ffffff;
    border-radius: 10px;
    font-weight: 700;
    font-size: 13px;
}
QPushButton#DangerButton:hover {
    background-color: #dc2626;
}
QPushButton#DangerButton:pressed {
    background-color: #b91c1c;
}

/* Settings & Theme Buttons (Header) */
QPushButton#SettingsButton, QPushButton#ThemeButton {
    background-color: rgba(255, 255, 255, 0.15);
    border: 1px solid rgba(255, 255, 255, 0.25);
    color: #ffffff;
    border-radius: 8px;
    padding: 6px 14px;
    font-weight: 600;
}
QPushButton#SettingsButton:hover, QPushButton#ThemeButton:hover {
    background-color: rgba(255, 255, 255, 0.25);
    border-color: rgba(255, 255, 255, 0.40);
}
QPushButton#SettingsButton:pressed, QPushButton#ThemeButton:pressed {
    background-color: rgba(255, 255, 255, 0.10);
}

/* Table View */
QTableWidget, QTableView {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    gridline-color: #f1f5f9;
    selection-background-color: #e2e8f0;
    selection-color: #0f172a;
    outline: none;
}
QTableWidget::item, QTableView::item {
    padding: 10px;
    border-bottom: 1px solid #f1f5f9;
    background-color: transparent;
}
QTableWidget::item:selected, QTableView::item:selected {
    background-color: #e2e8f0;
    color: #0f172a;
    font-weight: 600;
}
QTableWidget::item:hover, QTableView::item:hover {
    background-color: #f1f5f9;
    color: #0f172a;
}
QHeaderView::section {
    background-color: #f8fafc;
    color: #475569;
    font-weight: 700;
    padding: 10px;
    border: none;
    border-bottom: 2px solid #e2e8f0;
}

/* QGroupBox for configurations */
QGroupBox {
    font-weight: 800;
    font-size: 13px;
    color: #1e293b;
    border: none;
    border-top: 1px solid #f1f5f9;
    margin-top: 20px;
    padding: 20px 0px 10px 0px;
    background-color: transparent;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 0px;
    padding: 0;
    color: #3b82f6;
    font-size: 13px;
    font-weight: 800;
    background-color: transparent;
}

QGroupBox::indicator {
    width: 16px;
    height: 16px;
    border: 1.5px solid #cbd5e1;
    border-radius: 4px;
    background-color: #ffffff;
}

QGroupBox::indicator:hover {
    border-color: #3b82f6;
}

QGroupBox::indicator:checked {
    background-color: #3b82f6;
    border-color: #3b82f6;
    image: url(data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCIgZmlsbD0ibm9uZSIgc3Ryb2tlPSJ3aGl0ZSIgc3Ryb2tlLXdpZHRoPSI0IiBzdHJva2UtbGluZWNhcD0icm91bmQiIHN0cm9rZS1saW5lam9pbj0icm91bmQiPjxwb2x5bGluZSBwb2ludHM9IjIwIDYgOSAxNyA0IDEyIj48L3BvbHlsaW5lPjwvc3ZnPg==);
}

/* Dashboard Stat Cards with Left Color Borders */
QFrame#StatCard_total, QFrame#StatCard_running, QFrame#StatCard_success, QFrame#StatCard_failed, QFrame#StatCard_sent, QFrame#StatCard_inv_failed {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    padding: 14px;
}

QFrame#StatCard_total:hover {
    border: 1px solid #64748b;
}
QFrame#StatCard_running:hover {
    border: 1px solid #3b82f6;
}
QFrame#StatCard_success:hover {
    border: 1px solid #10b981;
}
QFrame#StatCard_failed:hover {
    border: 1px solid #ef4444;
}
QFrame#StatCard_sent:hover {
    border: 1px solid #10b981;
}
QFrame#StatCard_inv_failed:hover {
    border: 1px solid #f59e0b;
}
QFrame#StatCard_total {
    border-left: 5px solid #64748b;
}
QFrame#StatCard_running {
    border-left: 5px solid #3b82f6;
}
QFrame#StatCard_success {
    border-left: 5px solid #10b981;
}
QFrame#StatCard_failed {
    border-left: 5px solid #ef4444;
}
QFrame#StatCard_sent {
    border-left: 5px solid #10b981;
}
QFrame#StatCard_inv_failed {
    border-left: 5px solid #f59e0b;
}

QLabel#StatValue {
    font-size: 26px;
    font-weight: 800;
    color: #0f172a;
}
QLabel#StatLabel {
    font-size: 11px;
    color: #64748b;
    text-transform: uppercase;
    font-weight: 700;
    letter-spacing: 0.6px;
}

/* CheckBox */
QCheckBox {
    spacing: 8px;
    outline: none;
    font-size: 12px;
}
QCheckBox#SubCheckBox {
    color: #64748b;
    font-weight: 600;
}
QCheckBox:focus {
    border: none;
    outline: none;
}
QCheckBox::indicator {
    width: 18px;
    height: 18px;
    min-width: 18px;
    min-height: 18px;
    max-width: 18px;
    max-height: 18px;
    border: 1.5px solid #cbd5e1;
    border-radius: 5px;
    background-color: #ffffff;
}
QCheckBox::indicator:unchecked {
    background-color: #ffffff;
    border: 1.5px solid #cbd5e1;
}
QCheckBox::indicator:hover {
    border: 1.5px solid #3b82f6;
}
QCheckBox::indicator:checked {
    background-color: #3b82f6;
    border: 1.5px solid #3b82f6;
    image: url(data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCIgZmlsbD0ibm9uZSIgc3Ryb2tlPSJ3aGl0ZSIgc3Ryb2tlLXdpZHRoPSI0IiBzdHJva2UtbGluZWNhcD0icm91bmQiIHN0cm9rZS1saW5lam9pbj0icm91bmQiPjxwb2x5bGluZSBwb2ludHM9IjIwIDYgOSAxNyA0IDEyIj48L3BvbHlsaW5lPjwvc3ZnPg==);
}

/* RadioButton */
QRadioButton {
    spacing: 8px;
    color: #475569;
    font-weight: 500;
    outline: none;
}
QRadioButton:focus {
    border: none;
    outline: none;
}
QRadioButton::indicator {
    width: 18px;
    height: 18px;
    border: 1.5px solid #cbd5e1;
    border-radius: 9px;
    background-color: #ffffff;
}
QRadioButton::indicator:unchecked {
    background-color: #ffffff;
    border: 1.5px solid #cbd5e1;
}
QRadioButton::indicator:hover {
    border: 1.5px solid #3b82f6;
}
QRadioButton::indicator:checked {
    background-color: #3b82f6;
    border: 1.5px solid #3b82f6;
    image: url(data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCIgZmlsbD0ibm9uZSIgc3Ryb2tlPSJ3aGl0ZSIgc3Ryb2tlLXdpZHRoPSI1IiBzdHJva2UtbGluZWNhcD0icm91bmQiIHN0cm9rZS1saW5lam9pbj0icm91bmQiPjxjaXJjbGUgY3g9IjEyIiBjeT0iMTIiIHI9IjMiIGZpbGw9IndoaXRlIi8+PC9zdmc+);
}

/* ScrollArea */
QScrollArea {
    background-color: transparent;
    border: none;
}

QTabWidget::pane {
    border: none;
    background-color: transparent;
    padding: 10px 0px;
}

QWidget#TabTasks, QWidget#TasksContainer, QWidget#TabConfig, QWidget#ConfigScrollContainer, QWidget#TabPostMedia, QWidget#PostMediaScrollContainer {
    background-color: transparent;
    background: transparent;
}

QTabWidget::tab-bar {
    alignment: left;
}

QTabBar::tab {
    background: transparent;
    color: #64748b;
    border: none;
    border-bottom: 2px solid transparent;
    padding: 8px 16px;
    font-weight: 700;
    font-size: 13px;
    margin-right: 12px;
}

QTabBar::tab:selected {
    color: #3b82f6;
    border-bottom: 2px solid #3b82f6;
}

QTabBar::tab:hover:!selected {
    color: #2563eb;
    background: transparent;
}

/* Tooltips */
QToolTip {
    background-color: #ffffff;
    color: #0f172a;
    border: 1.5px solid #3b82f6;
    border-radius: 6px;
    padding: 6px;
}

/* Table Header Action Buttons */
QPushButton.TableHeaderButton {
    background-color: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    padding: 6px 12px;
    color: #475569;
    font-size: 12px;
    font-weight: 700;
}
QPushButton.TableHeaderButton:hover {
    background-color: #eff6ff;
    border-color: #3b82f6;
    color: #2563eb;
}
QPushButton.TableHeaderButton:pressed {
    background-color: #cbd5e1;
}
QPushButton.TableHeaderButton#Primary {
    background-color: #3b82f6;
    border: none;
    color: #ffffff;
}
QPushButton.TableHeaderButton#Primary:hover {
    background-color: #2563eb;
    color: #ffffff;
}
QPushButton.TableHeaderButton#Primary:pressed {
    background-color: #1d4ed8;
}
QPushButton.TableHeaderButton#Success {
    background-color: #10b981;
    border: none;
    color: #ffffff;
}
QPushButton.TableHeaderButton#Success:hover {
    background-color: #059669;
    color: #ffffff;
}
QPushButton.TableHeaderButton#Success:pressed {
    background-color: #047857;
}
QPushButton.TableHeaderButton#Danger {
    background-color: #fee2e2;
    border: 1px solid #fca5a5;
    color: #b91c1c;
}
QPushButton.TableHeaderButton#Danger:hover {
    background-color: #fecaca;
    border-color: #b91c1c;
    color: #b91c1c;
}
QPushButton.TableHeaderButton#Danger:pressed {
    background-color: #fca5a5;
}

/* Check Accounts Button */
QPushButton#CheckAccountsBtn {
    background-color: #ede9fe;
    border: 1px solid #c4b5fd;
    border-radius: 6px;
    padding: 6px 12px;
    color: #6d28d9;
    font-size: 12px;
    font-weight: 700;
}
QPushButton#CheckAccountsBtn:hover {
    background-color: #ddd6fe;
    border-color: #7c3aed;
    color: #5b21b6;
}
QPushButton#CheckAccountsBtn:pressed {
    background-color: #c4b5fd;
}

/* Context Menu (Right Click Menu) */
QMenu {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 6px 0px;
}
QMenu::item {
    background-color: transparent;
    padding: 8px 26px 8px 16px;
    color: #0f172a;
    font-size: 13px;
    font-weight: 600;
}
QMenu::item:selected {
    background-color: #3b82f6;
    color: #ffffff;
}
QMenu::separator {
    height: 1px;
    background-color: #e2e8f0;
    margin: 4px 8px;
}
"""

DARK_THEME_STYLE = """
/* Global Styles */
QMainWindow, QDialog {
    background-color: #0f172a;
}

QWidget {
    color: #cbd5e1;
    font-family: 'Khmer OS Battambang', 'Segoe UI', 'Roboto', 'Inter', -apple-system, sans-serif;
    font-size: 13px;
}

/* Scrollbars */
QScrollBar:vertical {
    border: none;
    background: #090d16;
    width: 8px;
    margin: 0px;
    border-radius: 4px;
}
QScrollBar::handle:vertical {
    background: #334155;
    min-height: 25px;
    border-radius: 4px;
}
QScrollBar::handle:vertical:hover {
    background: #3b82f6;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar:horizontal {
    border: none;
    background: #090d16;
    height: 8px;
    margin: 0px;
    border-radius: 4px;
}
QScrollBar::handle:horizontal {
    background: #334155;
    min-width: 25px;
    border-radius: 4px;
}
QScrollBar::handle:horizontal:hover {
    background: #3b82f6;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}

/* Titles and Labels */
QLabel#AppTitle {
    font-size: 20px;
    font-weight: 800;
    color: #ffffff;
    letter-spacing: 0.5px;
    background: transparent;
}

QLabel#SectionHeader {
    font-size: 15px;
    font-weight: 800;
    color: #f8fafc;
    padding-bottom: 6px;
}

/* Form Styling */
QLabel#FormLabel {
    font-weight: 600;
    color: #94a3b8;
    font-size: 12px;
}

/* Header Container */
QFrame#HeaderFrame {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1e3a8a, stop:1 #3b82f6);
    border: none;
    border-radius: 12px;
    padding: 15px;
}

/* Cards / Containers */
QFrame#CardFrame {
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 12px;
}

QFrame#CardFrame:hover {
    border: 1px solid #3b82f6;
}

QFrame#ConfigCardFrame {
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 16px;
}
QFrame#ConfigCardFrame:hover {
    border: 1px solid #475569;
}

/* Accounts Table Section (Top-right panel) */
QFrame#TableCardFrame {
    background-color: #1e293b;
    border: 1.5px solid #334155;
    border-radius: 12px;
}
QFrame#TableCardFrame:hover {
    border: 1.5px solid #10b981;
}

/* Logs Section (Bottom-right panel) */
QFrame#LogCardFrame {
    background-color: #1e293b;
    border: 1.5px solid #334155;
    border-radius: 12px;
}
QFrame#LogCardFrame:hover {
    border: 1.5px solid #8b5cf6;
}

QFrame#NestedCard {
    background-color: #0f172a;
    border: 1px solid #334155;
    border-radius: 8px;
}

/* Text Inputs / TextEdits */
QLineEdit, QTextEdit {
    background-color: #0f172a;
    border: 1px solid #334155;
    border-radius: 8px;
    padding: 6px 12px;
    color: #f8fafc;
    selection-background-color: #3b82f6;
    selection-color: #ffffff;
    font-weight: 500;
}
QLineEdit:focus, QTextEdit:focus {
    border: 1px solid #3b82f6;
}

/* SpinBox / Slider */
QSpinBox {
    background-color: #0f172a;
    border: 1px solid #334155;
    border-radius: 8px;
    color: #f8fafc;
    font-weight: 700;
}
QSpinBox:focus {
    border: 1px solid #3b82f6;
}
QSpinBox QLineEdit {
    background: transparent !important;
    background-color: transparent !important;
    border: none !important;
    padding: 0px !important;
    margin: 0px !important;
    color: #f8fafc !important;
    font-weight: 700 !important;
}
QSpinBox::up-button {
    subcontrol-origin: border;
    subcontrol-position: right;
    width: 22px;
    height: 28px;
    border: none;
    background: transparent;
}
QSpinBox::up-arrow {
    image: url("ui/plus.svg");
    width: 18px;
    height: 18px;
}
QSpinBox::up-arrow:hover {
    image: url("ui/plus_hover.svg");
}
QSpinBox::down-button {
    subcontrol-origin: border;
    subcontrol-position: left;
    width: 22px;
    height: 28px;
    border: none;
    background: transparent;
}
QSpinBox::down-arrow {
    image: url("ui/minus.svg");
    width: 18px;
    height: 18px;
}
QSpinBox::down-arrow:hover {
    image: url("ui/minus_hover.svg");
}

/* ComboBox (Dropdown) Styling */
QComboBox {
    background-color: #0f172a;
    border: 1.5px solid #334155;
    border-radius: 8px;
    padding: 6px 30px 6px 12px;
    color: #f8fafc;
    font-weight: 500;
}
QComboBox:hover {
    border: 1.5px solid #475569;
    background-color: #1e293b;
}
QComboBox:focus {
    border: 1.5px solid #3b82f6;
    background-color: #0f172a;
}

/* Dropdown arrow container */
QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 30px;
    border-left: none;
    border-top-right-radius: 8px;
    border-bottom-right-radius: 8px;
}

/* Dropdown arrow icon (Modern chevron down in light gray) */
QComboBox::down-arrow {
    image: url(data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCIgZmlsbD0ibm9uZSIgc3Ryb2tlPSIjY2JkNWUxIiBzdHJva2Utd2lkdGg9IjIuNSIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIiBzdHJva2UtbGluZWpvaW49InJvdW5kIj48cG9seWxpbmUgcG9pbnRzPSI2IDkgMTIgMTUgMTggOSI+PC9wb2x5bGluZT48L3N2Zz4=);
    width: 14px;
    height: 14px;
}

/* Dropdown Popup Menu (List View) */
QComboBox QAbstractItemView {
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 8px;
    outline: none;
    padding: 4px;
}

/* Dropdown Popup Items */
QComboBox QAbstractItemView::item {
    height: 32px;
    border-radius: 6px;
    padding-left: 10px;
    color: #cbd5e1;
    background-color: transparent;
}

/* Dropdown Popup Items Hover state */
QComboBox QAbstractItemView::item:hover, QComboBox QAbstractItemView::item:selected {
    background-color: #1e3a8a;
    color: #ffffff;
    font-weight: 600;
}

QSlider::groove:horizontal {
    border: 1px solid #334155;
    height: 6px;
    background: #334155;
    border-radius: 3px;
}
QSlider::sub-page:horizontal {
    background: #3b82f6;
    border-radius: 3px;
}
QSlider::handle:horizontal {
    background: #ffffff;
    border: 2px solid #3b82f6;
    width: 14px;
    height: 14px;
    margin-top: -5px;
    margin-bottom: -5px;
    border-radius: 8px;
}

/* Buttons */
QPushButton {
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 8px;
    padding: 8px 18px;
    color: #cbd5e1;
    font-weight: 600;
}
QPushButton:hover {
    background-color: #1e3b8b;
    border: 1px solid #3b82f6;
    color: #ffffff;
}
QPushButton:pressed {
    background-color: #0f172a;
}

QPushButton#PrimaryButton {
    background-color: #3b82f6;
    border: none;
    color: #ffffff;
}
QPushButton#PrimaryButton:hover {
    background-color: #2563eb;
}
QPushButton#PrimaryButton:pressed {
    background-color: #1d4ed8;
}

QPushButton#SuccessButton {
    background-color: #10b981;
    border: none;
    color: #ffffff;
    border-radius: 10px;
    font-weight: 700;
    font-size: 13px;
}
QPushButton#SuccessButton:hover {
    background-color: #059669;
}
QPushButton#SuccessButton:pressed {
    background-color: #047857;
}

QPushButton#DangerButton {
    background-color: #ef4444;
    border: none;
    color: #ffffff;
    border-radius: 10px;
    font-weight: 700;
    font-size: 13px;
}
QPushButton#DangerButton:hover {
    background-color: #dc2626;
}
QPushButton#DangerButton:pressed {
    background-color: #b91c1c;
}

/* Settings & Theme Buttons (Header) */
QPushButton#SettingsButton, QPushButton#ThemeButton {
    background-color: rgba(255, 255, 255, 0.15);
    border: 1px solid rgba(255, 255, 255, 0.25);
    color: #ffffff;
    border-radius: 8px;
    padding: 6px 14px;
    font-weight: 600;
}
QPushButton#SettingsButton:hover, QPushButton#ThemeButton:hover {
    background-color: rgba(255, 255, 255, 0.25);
    border-color: rgba(255, 255, 255, 0.40);
}
QPushButton#SettingsButton:pressed, QPushButton#ThemeButton:pressed {
    background-color: rgba(255, 255, 255, 0.10);
}

/* Table View */
QTableWidget, QTableView {
    background-color: #1a1a1a;
    alternate-background-color: #242424;
    border: 1px solid #444444;
    border-radius: 4px;
    gridline-color: #333333;
    selection-background-color: #4b5563;
    selection-color: #ffffff;
    color: #e0e0e0;
    outline: none;
}
QTableWidget::item, QTableView::item {
    padding: 10px;
    border-bottom: 1px solid #333333;
    background-color: transparent;
}
QTableWidget::item:selected, QTableView::item:selected {
    background-color: #4b5563;
    color: #ffffff;
    font-weight: 600;
}
QTableWidget::item:hover, QTableView::item:hover {
    background-color: #374151;
    color: #ffffff;
}
QHeaderView::section {
    background-color: #1a1a1a;
    color: #FFD700;
    font-weight: 800;
    padding: 10px;
    border: none;
    border-bottom: 2px solid #FFD700;
    border-right: 1px solid #333333;
}

/* QGroupBox for configurations */
QGroupBox {
    font-weight: 800;
    font-size: 13px;
    color: #cbd5e1;
    border: none;
    border-top: 1px solid #1e293b;
    margin-top: 20px;
    padding: 20px 0px 10px 0px;
    background-color: transparent;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 0px;
    padding: 0;
    color: #60a5fa;
    font-size: 13px;
    font-weight: 800;
    background-color: transparent;
}

QGroupBox::indicator {
    width: 16px;
    height: 16px;
    border: 1.5px solid #475569;
    border-radius: 4px;
    background-color: #0f172a;
}

QGroupBox::indicator:hover {
    border-color: #3b82f6;
}

QGroupBox::indicator:checked {
    background-color: #3b82f6;
    border-color: #3b82f6;
    image: url(data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCIgZmlsbD0ibm9uZSIgc3Ryb2tlPSJ3aGl0ZSIgc3Ryb2tlLXdpZHRoPSI0IiBzdHJva2UtbGluZWNhcD0icm91bmQiIHN0cm9rZS1saW5lam9pbj0icm91bmQiPjxwb2x5bGluZSBwb2ludHM9IjIwIDYgOSAxNyA0IDEyIj48L3BvbHlsaW5lPjwvc3ZnPg==);
}

/* Dashboard Stat Cards with Left Color Borders */
QFrame#StatCard_total, QFrame#StatCard_running, QFrame#StatCard_success, QFrame#StatCard_failed, QFrame#StatCard_sent, QFrame#StatCard_inv_failed {
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 10px;
    padding: 14px;
}

QFrame#StatCard_total:hover {
    border: 1px solid #94a3b8;
}
QFrame#StatCard_running:hover {
    border: 1px solid #3b82f6;
}
QFrame#StatCard_success:hover {
    border: 1px solid #10b981;
}
QFrame#StatCard_failed:hover {
    border: 1px solid #ef4444;
}
QFrame#StatCard_sent:hover {
    border: 1px solid #10b981;
}
QFrame#StatCard_inv_failed:hover {
    border: 1px solid #f59e0b;
}
QFrame#StatCard_total {
    border-left: 5px solid #64748b;
}
QFrame#StatCard_running {
    border-left: 5px solid #3b82f6;
}
QFrame#StatCard_success {
    border-left: 5px solid #10b981;
}
QFrame#StatCard_failed {
    border-left: 5px solid #ef4444;
}
QFrame#StatCard_sent {
    border-left: 5px solid #10b981;
}
QFrame#StatCard_inv_failed {
    border-left: 5px solid #f59e0b;
}

QLabel#StatValue {
    font-size: 26px;
    font-weight: 800;
    color: #f8fafc;
}
QLabel#StatLabel {
    font-size: 11px;
    color: #94a3b8;
    text-transform: uppercase;
    font-weight: 700;
    letter-spacing: 0.6px;
}

/* CheckBox */
QCheckBox {
    spacing: 8px;
    outline: none;
    font-size: 12px;
}
QCheckBox#SubCheckBox {
    color: #94a3b8;
    font-weight: 600;
}
QCheckBox:focus {
    border: none;
    outline: none;
}
QCheckBox::indicator {
    width: 18px;
    height: 18px;
    min-width: 18px;
    min-height: 18px;
    max-width: 18px;
    max-height: 18px;
    border: 1.5px solid #475569;
    border-radius: 5px;
    background-color: #0f172a;
}
QCheckBox::indicator:unchecked {
    background-color: #0f172a;
    border: 1.5px solid #475569;
}
QCheckBox::indicator:hover {
    border: 1.5px solid #3b82f6;
}
QCheckBox::indicator:checked {
    background-color: #3b82f6;
    border: 1.5px solid #3b82f6;
    image: url(data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCIgZmlsbD0ibm9uZSIgc3Ryb2tlPSJ3aGl0ZSIgc3Ryb2tlLXdpZHRoPSI0IiBzdHJva2UtbGluZWNhcD0icm91bmQiIHN0cm9rZS1saW5lam9pbj0icm91bmQiPjxwb2x5bGluZSBwb2ludHM9IjIwIDYgOSAxNyA0IDEyIj48L3BvbHlsaW5lPjwvc3ZnPg==);
}

/* RadioButton */
QRadioButton {
    spacing: 8px;
    color: #94a3b8;
    font-weight: 500;
    outline: none;
}
QRadioButton:focus {
    border: none;
    outline: none;
}
QRadioButton::indicator {
    width: 18px;
    height: 18px;
    border: 1.5px solid #475569;
    border-radius: 9px;
    background-color: #0f172a;
}
QRadioButton::indicator:unchecked {
    background-color: #0f172a;
    border: 1.5px solid #475569;
}
QRadioButton::indicator:hover {
    border: 1.5px solid #3b82f6;
}
QRadioButton::indicator:checked {
    background-color: #3b82f6;
    border: 1.5px solid #3b82f6;
    image: url(data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCIgZmlsbD0ibm9uZSIgc3Ryb2tlPSJ3aGl0ZSIgc3Ryb2tlLXdpZHRoPSI1IiBzdHJva2UtbGluZWNhcD0icm91bmQiIHN0cm9rZS1saW5lam9pbj0icm91bmQiPjxjaXJjbGUgY3g9IjEyIiBjeT0iMTIiIHI9IjMiIGZpbGw9IndoaXRlIi8+PC9zdmc+);
}

/* ScrollArea */
QScrollArea {
    background-color: transparent;
    border: none;
}

QTabWidget::pane {
    border: none;
    background-color: transparent;
    padding: 10px 0px;
}

QWidget#TabTasks, QWidget#TasksContainer, QWidget#TabConfig, QWidget#ConfigScrollContainer, QWidget#TabPostMedia, QWidget#PostMediaScrollContainer {
    background-color: transparent;
    background: transparent;
}

QTabWidget::tab-bar {
    alignment: left;
}

QTabBar::tab {
    background: transparent;
    color: #94a3b8;
    border: none;
    border-bottom: 2px solid transparent;
    padding: 8px 16px;
    font-weight: 700;
    font-size: 13px;
    margin-right: 12px;
}

QTabBar::tab:selected {
    color: #60a5fa;
    border-bottom: 2px solid #60a5fa;
}

QTabBar::tab:hover:!selected {
    color: #ffffff;
    background: transparent;
}

/* Tooltips */
QToolTip {
    background-color: #1e293b;
    color: #f8fafc;
    border: 1.5px solid #3b82f6;
    border-radius: 6px;
    padding: 6px;
}

/* Table Header Action Buttons */
QPushButton.TableHeaderButton {
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 6px 12px;
    color: #cbd5e1;
    font-size: 12px;
    font-weight: 700;
}
QPushButton.TableHeaderButton:hover {
    background-color: #1e3b8b;
    border-color: #3b82f6;
    color: #ffffff;
}
QPushButton.TableHeaderButton:pressed {
    background-color: #0f172a;
}
QPushButton.TableHeaderButton#Primary {
    background-color: #3b82f6;
    border: none;
    color: #ffffff;
}
QPushButton.TableHeaderButton#Primary:hover {
    background-color: #2563eb;
    color: #ffffff;
}
QPushButton.TableHeaderButton#Primary:pressed {
    background-color: #1d4ed8;
}
QPushButton.TableHeaderButton#Success {
    background-color: #10b981;
    border: none;
    color: #ffffff;
}
QPushButton.TableHeaderButton#Success:hover {
    background-color: #059669;
    color: #ffffff;
}
QPushButton.TableHeaderButton#Success:pressed {
    background-color: #047857;
}
QPushButton.TableHeaderButton#Danger {
    background-color: #3f1e1e;
    border: 1px solid #7f1d1d;
    color: #f87171;
}
QPushButton.TableHeaderButton#Danger:hover {
    background-color: #7f1d1d;
    border-color: #f87171;
    color: #ffffff;
}
QPushButton.TableHeaderButton#Danger:pressed {
    background-color: #991b1b;
}

/* Check Accounts Button - Dark Theme */
QPushButton#CheckAccountsBtn {
    background-color: #2e1065;
    border: 1px solid #5b21b6;
    border-radius: 6px;
    padding: 6px 12px;
    color: #c4b5fd;
    font-size: 12px;
    font-weight: 700;
}
QPushButton#CheckAccountsBtn:hover {
    background-color: #4c1d95;
    border-color: #7c3aed;
    color: #ede9fe;
}
QPushButton#CheckAccountsBtn:pressed {
    background-color: #3b0764;
}

/* Context Menu (Right Click Menu) */
QMenu {
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 8px;
    padding: 6px 0px;
}
QMenu::item {
    background-color: transparent;
    padding: 8px 26px 8px 16px;
    color: #cbd5e1;
    font-size: 13px;
    font-weight: 600;
}
QMenu::item:selected {
    background-color: #3b82f6;
    color: #ffffff;
}
QMenu::separator {
    height: 1px;
    background-color: #334155;
    margin: 4px 8px;
}
"""


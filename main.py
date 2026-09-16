import sys
import os
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFontDatabase, QFont, QIcon
from ui.dashboard import DashboardWindow

def main():
    app = QApplication(sys.argv)
    
    # Load KhmerOSbattambang font
    font_path = os.path.join(os.getcwd(), "fonts", "KhmerOSbattambang.ttf")
    if os.path.exists(font_path):
        font_id = QFontDatabase.addApplicationFont(font_path)
        if font_id != -1:
            font_family = QFontDatabase.applicationFontFamilies(font_id)[0]
            app.setFont(QFont(font_family, 10))
            
    # Set modern app icon
    icon_path = os.path.join(os.getcwd(), "assets", "icon.png")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
            
    window = DashboardWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()

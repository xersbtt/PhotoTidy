"""
About dialog for PhotoTidy.
"""
from pathlib import Path
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QPixmap

from config import APP_NAME, APP_VERSION


class AboutDialog(QDialog):
    """About dialog with app information."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
    
    def _setup_ui(self):
        self.setWindowTitle(f"About {APP_NAME}")
        self.setFixedSize(400, 360)
        self.setStyleSheet("""
            QDialog {
                background-color: #1e1e1e;
            }
            QLabel {
                color: #e0e0e0;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # App icon/logo - use actual icon if available
        icon_label = QLabel()
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_path = Path(__file__).parent.parent / "assets" / "icon.png"
        if icon_path.exists():
            pixmap = QPixmap(str(icon_path))
            icon_label.setPixmap(pixmap.scaled(80, 80, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        else:
            icon_label.setText("📷")
            icon_label.setFont(QFont("Segoe UI", 48))
        layout.addWidget(icon_label)
        
        # App name
        name_label = QLabel(APP_NAME)
        name_label.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(name_label)
        
        # Version
        version_label = QLabel(f"Version {APP_VERSION}")
        version_label.setStyleSheet("color: #888;")
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(version_label)
        
        # Description
        desc_label = QLabel(
            "A modern photo organization tool for sorting,\n"
            "grouping, and managing your photo library."
        )
        desc_label.setWordWrap(True)
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc_label.setStyleSheet("color: #aaa; margin: 10px 0;")
        layout.addWidget(desc_label)
        
        # Credits
        credits_label = QLabel("Built with Python and PySide6")
        credits_label.setStyleSheet("color: #666; font-size: 11px;")
        credits_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(credits_label)
        
        layout.addStretch()
        
        # Close button
        close_btn = QPushButton("Close")
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #4a9eff;
                border: none;
                border-radius: 6px;
                color: white;
                padding: 10px 30px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #5aacff;
            }
        """)
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignCenter)

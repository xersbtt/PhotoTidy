"""
Preview panel for displaying selected photo in larger view.
"""
from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QHBoxLayout, QPushButton, QScrollArea
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap, QFont

from core.photo import Photo
from config import RAW_IMAGE_EXTENSIONS

import rawpy
from PIL import Image
import io


class PreviewPanel(QWidget):
    """Panel for showing large preview of selected photo."""
    
    navigate_previous = Signal()
    navigate_next = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_photo: Optional[Photo] = None
        self._setup_ui()
    
    def _setup_ui(self):
        """Set up the preview panel UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        # Image container
        self.image_container = QWidget()
        self.image_container.setStyleSheet("background-color: #1a1a1a; border-radius: 8px;")
        container_layout = QVBoxLayout(self.image_container)
        
        # Image label
        self.image_label = QLabel("Select a photo to preview")
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet("""
            QLabel {
                color: #666;
                font-size: 14px;
            }
        """)
        self.image_label.setMinimumSize(300, 300)
        container_layout.addWidget(self.image_label)
        
        layout.addWidget(self.image_container, stretch=1)
        
        # Navigation buttons
        nav_layout = QHBoxLayout()
        
        self.prev_btn = QPushButton("◀ Previous")
        self.prev_btn.setStyleSheet(self._button_style())
        self.prev_btn.clicked.connect(self.navigate_previous.emit)
        nav_layout.addWidget(self.prev_btn)
        
        nav_layout.addStretch()
        
        self.next_btn = QPushButton("Next ▶")
        self.next_btn.setStyleSheet(self._button_style())
        self.next_btn.clicked.connect(self.navigate_next.emit)
        nav_layout.addWidget(self.next_btn)
        
        layout.addLayout(nav_layout)
        
        # Filename label
        self.filename_label = QLabel()
        self.filename_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.filename_label.setFont(QFont("Segoe UI", 10))
        self.filename_label.setStyleSheet("color: #888;")
        layout.addWidget(self.filename_label)
    
    def _button_style(self) -> str:
        return """
            QPushButton {
                background-color: #3a3a3a;
                border: 1px solid #555;
                border-radius: 4px;
                color: #e0e0e0;
                padding: 8px 16px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #4a4a4a;
            }
            QPushButton:disabled {
                background-color: #2a2a2a;
                color: #555;
            }
        """
    
    def set_photo(self, photo: Optional[Photo]):
        """Set the photo to preview."""
        self._current_photo = photo
        
        if photo is None:
            self.image_label.setPixmap(QPixmap())
            self.image_label.setText("Select a photo to preview")
            self.filename_label.setText("")
            return
        
        # Load the image
        pixmap = self._load_image(photo.path)
        
        if pixmap:
            # Scale to fit
            scaled = pixmap.scaled(
                self.image_label.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.image_label.setPixmap(scaled)
        else:
            self.image_label.setText("Unable to load image")
        
        self.filename_label.setText(photo.filename)
    
    def _load_image(self, path: Path) -> Optional[QPixmap]:
        """Load image from path, handling RAW formats."""
        try:
            if path.suffix.lower() in RAW_IMAGE_EXTENSIONS:
                return self._load_raw_image(path)
            else:
                return QPixmap(str(path))
        except Exception as e:
            print(f"Error loading image: {e}")
            return None
    
    def _load_raw_image(self, path: Path) -> Optional[QPixmap]:
        """Load a RAW image and convert to QPixmap."""
        try:
            with rawpy.imread(str(path)) as raw:
                rgb = raw.postprocess(
                    use_camera_wb=True,
                    no_auto_bright=False,
                    output_bps=8
                )
                
                # Convert to PIL Image then to QPixmap
                img = Image.fromarray(rgb)
                
                # Save to bytes buffer
                buffer = io.BytesIO()
                img.save(buffer, format='PNG')
                buffer.seek(0)
                
                # Load as QPixmap
                pixmap = QPixmap()
                pixmap.loadFromData(buffer.read())
                return pixmap
                
        except Exception as e:
            print(f"Error loading RAW image: {e}")
            return None
    
    def resizeEvent(self, event):
        """Handle resize to rescale the preview."""
        super().resizeEvent(event)
        if self._current_photo:
            # Reload at new size
            self.set_photo(self._current_photo)
    
    def set_navigation_enabled(self, prev_enabled: bool, next_enabled: bool):
        """Enable/disable navigation buttons."""
        self.prev_btn.setEnabled(prev_enabled)
        self.next_btn.setEnabled(next_enabled)

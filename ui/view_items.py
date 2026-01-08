"""
Photo item widgets for different view modes.
"""
from pathlib import Path
from typing import Optional
from enum import Enum

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QCheckBox, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QPixmap, QMouseEvent, QFont

from core.photo import Photo


class ViewMode(Enum):
    """View mode options similar to Windows Explorer."""
    THUMBNAILS = "thumbnails"  # Large icons with thumbnails
    TILES = "tiles"           # Medium icons with some metadata
    LIST = "list"             # Small icons in compact list
    DETAILS = "details"       # Table-like with columns


class PhotoListItem(QWidget):
    """Compact list item for LIST view mode."""
    
    clicked = Signal(Photo)
    double_clicked = Signal(Photo)
    selection_changed = Signal(Photo, bool)
    
    def __init__(self, photo: Photo, parent=None):
        super().__init__(parent)
        self.photo = photo
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(8)
        
        # Checkbox
        self.checkbox = QCheckBox()
        self.checkbox.setChecked(self.photo.is_selected)
        self.checkbox.stateChanged.connect(self._on_checkbox_changed)
        layout.addWidget(self.checkbox)
        
        # Small icon (32x32)
        self.icon_label = QLabel()
        self.icon_label.setFixedSize(32, 32)
        self.icon_label.setStyleSheet("background-color: #2d2d2d; border-radius: 4px;")
        self._load_icon()
        layout.addWidget(self.icon_label)
        
        # Filename
        name_label = QLabel(self.photo.filename)
        name_label.setStyleSheet("color: #e0e0e0; font-size: 12px;")
        layout.addWidget(name_label, stretch=1)
        
        self.setFixedHeight(40)
        self.setStyleSheet("""
            PhotoListItem {
                background-color: transparent;
            }
            PhotoListItem:hover {
                background-color: #2a2a2a;
            }
        """)
    
    def _load_icon(self):
        if self.photo.thumbnail_path and Path(self.photo.thumbnail_path).exists():
            pixmap = QPixmap(str(self.photo.thumbnail_path))
            scaled = pixmap.scaled(28, 28, Qt.AspectRatioMode.KeepAspectRatio, 
                                   Qt.TransformationMode.SmoothTransformation)
            self.icon_label.setPixmap(scaled)
        else:
            self.icon_label.setText("📷")
            self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    
    def _on_checkbox_changed(self, state):
        self.photo.is_selected = state == Qt.CheckState.Checked.value
        self.selection_changed.emit(self.photo, self.photo.is_selected)
    
    def update_selection_display(self):
        self.checkbox.blockSignals(True)
        self.checkbox.setChecked(self.photo.is_selected)
        self.checkbox.blockSignals(False)
    
    def set_highlight(self, highlighted: bool):
        if highlighted:
            self.setStyleSheet("PhotoListItem { background-color: #3a5070; }")
        else:
            self.setStyleSheet("PhotoListItem { background-color: transparent; } PhotoListItem:hover { background-color: #2a2a2a; }")
    
    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.photo)
        super().mousePressEvent(event)
    
    def mouseDoubleClickEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.double_clicked.emit(self.photo)
        super().mouseDoubleClickEvent(event)


class PhotoDetailItem(QWidget):
    """Detail row for DETAILS view mode with columns."""
    
    clicked = Signal(Photo)
    double_clicked = Signal(Photo)
    selection_changed = Signal(Photo, bool)
    
    def __init__(self, photo: Photo, parent=None):
        super().__init__(parent)
        self.photo = photo
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(4)
        
        # Checkbox
        self.checkbox = QCheckBox()
        self.checkbox.setChecked(self.photo.is_selected)
        self.checkbox.stateChanged.connect(self._on_checkbox_changed)
        self.checkbox.setFixedWidth(24)
        layout.addWidget(self.checkbox)
        
        # Small icon
        self.icon_label = QLabel()
        self.icon_label.setFixedSize(24, 24)
        self._load_icon()
        layout.addWidget(self.icon_label)
        
        # Filename (flexible)
        name_label = QLabel(self.photo.filename)
        name_label.setStyleSheet("color: #e0e0e0; font-size: 11px;")
        name_label.setMinimumWidth(150)
        layout.addWidget(name_label, stretch=2)
        
        # Date
        date_str = self.photo.date_taken.strftime("%Y-%m-%d %H:%M") if self.photo.date_taken else "—"
        date_label = QLabel(date_str)
        date_label.setStyleSheet("color: #888; font-size: 11px;")
        date_label.setFixedWidth(110)
        layout.addWidget(date_label)
        
        # Size
        size_str = self._format_size(self.photo.file_size)
        size_label = QLabel(size_str)
        size_label.setStyleSheet("color: #888; font-size: 11px;")
        size_label.setFixedWidth(70)
        size_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(size_label)
        
        # Camera
        camera = f"{self.photo.camera_make or ''} {self.photo.camera_model or ''}".strip() or "—"
        camera_label = QLabel(camera[:20] + "..." if len(camera) > 20 else camera)
        camera_label.setStyleSheet("color: #888; font-size: 11px;")
        camera_label.setFixedWidth(120)
        layout.addWidget(camera_label)
        
        self.setFixedHeight(32)
        self.setStyleSheet("""
            PhotoDetailItem {
                background-color: transparent;
                border-bottom: 1px solid #333;
            }
            PhotoDetailItem:hover {
                background-color: #2a2a2a;
            }
        """)
    
    def _load_icon(self):
        if self.photo.thumbnail_path and Path(self.photo.thumbnail_path).exists():
            pixmap = QPixmap(str(self.photo.thumbnail_path))
            scaled = pixmap.scaled(20, 20, Qt.AspectRatioMode.KeepAspectRatio,
                                   Qt.TransformationMode.SmoothTransformation)
            self.icon_label.setPixmap(scaled)
        else:
            self.icon_label.setText("📷")
    
    def _format_size(self, size_bytes: int) -> str:
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}" if unit != 'B' else f"{size_bytes} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} TB"
    
    def _on_checkbox_changed(self, state):
        self.photo.is_selected = state == Qt.CheckState.Checked.value
        self.selection_changed.emit(self.photo, self.photo.is_selected)
    
    def update_selection_display(self):
        self.checkbox.blockSignals(True)
        self.checkbox.setChecked(self.photo.is_selected)
        self.checkbox.blockSignals(False)
    
    def set_highlight(self, highlighted: bool):
        if highlighted:
            self.setStyleSheet("PhotoDetailItem { background-color: #3a5070; border-bottom: 1px solid #333; }")
        else:
            self.setStyleSheet("PhotoDetailItem { background-color: transparent; border-bottom: 1px solid #333; } PhotoDetailItem:hover { background-color: #2a2a2a; }")
    
    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.photo)
        super().mousePressEvent(event)
    
    def mouseDoubleClickEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.double_clicked.emit(self.photo)
        super().mouseDoubleClickEvent(event)


class PhotoTileItem(QWidget):
    """Tile item for TILES view mode - medium size with metadata."""
    
    clicked = Signal(Photo)
    double_clicked = Signal(Photo)
    selection_changed = Signal(Photo, bool)
    
    def __init__(self, photo: Photo, parent=None):
        super().__init__(parent)
        self.photo = photo
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(8)
        
        # Checkbox
        self.checkbox = QCheckBox()
        self.checkbox.setChecked(self.photo.is_selected)
        self.checkbox.stateChanged.connect(self._on_checkbox_changed)
        layout.addWidget(self.checkbox, alignment=Qt.AlignmentFlag.AlignTop)
        
        # Thumbnail (80x80)
        self.image_label = QLabel()
        self.image_label.setFixedSize(80, 80)
        self.image_label.setStyleSheet("background-color: #2d2d2d; border-radius: 6px;")
        self._load_thumbnail()
        layout.addWidget(self.image_label)
        
        # Info column
        info_layout = QVBoxLayout()
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(2)
        
        # Filename
        name_label = QLabel(self.photo.filename[:25] + "..." if len(self.photo.filename) > 25 else self.photo.filename)
        name_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        name_label.setStyleSheet("color: #e0e0e0;")
        info_layout.addWidget(name_label)
        
        # Date
        date_str = self.photo.date_taken.strftime("%b %d, %Y") if self.photo.date_taken else "Unknown date"
        date_label = QLabel(f"📅 {date_str}")
        date_label.setStyleSheet("color: #888; font-size: 10px;")
        info_layout.addWidget(date_label)
        
        # Size
        size_str = self._format_size(self.photo.file_size)
        size_label = QLabel(f"📦 {size_str}")
        size_label.setStyleSheet("color: #888; font-size: 10px;")
        info_layout.addWidget(size_label)
        
        info_layout.addStretch()
        layout.addLayout(info_layout, stretch=1)
        
        self.setFixedSize(280, 100)
        self.setStyleSheet("""
            PhotoTileItem {
                background-color: #1e1e1e;
                border: 1px solid #333;
                border-radius: 8px;
            }
            PhotoTileItem:hover {
                background-color: #2a2a2a;
                border-color: #555;
            }
        """)
    
    def _load_thumbnail(self):
        if self.photo.thumbnail_path and Path(self.photo.thumbnail_path).exists():
            pixmap = QPixmap(str(self.photo.thumbnail_path))
            scaled = pixmap.scaled(76, 76, Qt.AspectRatioMode.KeepAspectRatio,
                                   Qt.TransformationMode.SmoothTransformation)
            self.image_label.setPixmap(scaled)
            self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        else:
            self.image_label.setText("📷")
            self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    
    def _format_size(self, size_bytes: int) -> str:
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}" if unit != 'B' else f"{size_bytes} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} TB"
    
    def _on_checkbox_changed(self, state):
        self.photo.is_selected = state == Qt.CheckState.Checked.value
        self.selection_changed.emit(self.photo, self.photo.is_selected)
    
    def update_selection_display(self):
        self.checkbox.blockSignals(True)
        self.checkbox.setChecked(self.photo.is_selected)
        self.checkbox.blockSignals(False)
    
    def set_highlight(self, highlighted: bool):
        if highlighted:
            self.setStyleSheet("PhotoTileItem { background-color: #3a5070; border: 1px solid #4a9eff; border-radius: 8px; }")
        else:
            self.setStyleSheet("PhotoTileItem { background-color: #1e1e1e; border: 1px solid #333; border-radius: 8px; } PhotoTileItem:hover { background-color: #2a2a2a; border-color: #555; }")
    
    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.photo)
        super().mousePressEvent(event)
    
    def mouseDoubleClickEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.double_clicked.emit(self.photo)
        super().mouseDoubleClickEvent(event)

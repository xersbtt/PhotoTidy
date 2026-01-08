"""
Photo thumbnail widget for the grid view.
"""
from pathlib import Path
from typing import Optional
import subprocess
import os

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QCheckBox, QSizePolicy, QMenu
)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QPixmap, QMouseEvent, QAction

from core.photo import Photo


class PhotoThumbnailWidget(QWidget):
    """Widget displaying a single photo thumbnail with selection checkbox."""
    
    clicked = Signal(Photo)
    double_clicked = Signal(Photo)
    selection_changed = Signal(Photo, bool)
    # Context menu actions
    open_file_requested = Signal(Photo)
    open_folder_requested = Signal(Photo)
    rename_requested = Signal(Photo)
    set_location_requested = Signal(Photo)
    delete_requested = Signal(Photo)
    
    def __init__(self, photo: Photo, thumbnail_size: int = 180, parent=None):
        super().__init__(parent)
        self.photo = photo
        self.thumbnail_size = thumbnail_size
        self._setup_ui()
        self._load_thumbnail()
    
    def _setup_ui(self):
        """Set up the widget UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)
        
        # Image label
        self.image_label = QLabel()
        self.image_label.setFixedSize(self.thumbnail_size, self.thumbnail_size)
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet("""
            QLabel {
                background-color: #2d2d2d;
                border: 2px solid transparent;
                border-radius: 8px;
            }
        """)
        layout.addWidget(self.image_label)
        
        # Selection checkbox with filename
        self.checkbox = QCheckBox()
        self.checkbox.setChecked(self.photo.is_selected)
        self.checkbox.setText(self._truncate_filename(self.photo.filename, 20))
        self.checkbox.setStyleSheet("""
            QCheckBox {
                color: #e0e0e0;
                font-size: 11px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
            }
        """)
        self.checkbox.stateChanged.connect(self._on_checkbox_changed)
        layout.addWidget(self.checkbox)
        
        # Set size policy
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setFixedSize(self.thumbnail_size + 8, self.thumbnail_size + 30)
        
        # Style the container
        self.setStyleSheet("""
            PhotoThumbnailWidget {
                background-color: #1e1e1e;
                border-radius: 10px;
            }
            PhotoThumbnailWidget:hover {
                background-color: #2a2a2a;
            }
        """)
    
    def _load_thumbnail(self):
        """Load and display the thumbnail."""
        if self.photo.thumbnail_path and Path(self.photo.thumbnail_path).exists():
            pixmap = QPixmap(str(self.photo.thumbnail_path))
            scaled = pixmap.scaled(
                self.thumbnail_size - 4, 
                self.thumbnail_size - 4,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.image_label.setPixmap(scaled)
        else:
            # Placeholder
            self.image_label.setText("📷")
            self.image_label.setStyleSheet("""
                QLabel {
                    background-color: #2d2d2d;
                    border: 2px solid #444;
                    border-radius: 8px;
                    font-size: 48px;
                }
            """)
    
    def _truncate_filename(self, filename: str, max_length: int) -> str:
        """Truncate filename for display."""
        if len(filename) <= max_length:
            return filename
        return filename[:max_length-3] + "..."
    
    def _on_checkbox_changed(self, state):
        """Handle checkbox state change."""
        self.photo.is_selected = state == Qt.CheckState.Checked.value
        self.selection_changed.emit(self.photo, self.photo.is_selected)
    
    def set_selected(self, selected: bool):
        """Set selection state."""
        self.photo.is_selected = selected
        self.checkbox.setChecked(selected)
    
    def update_selection_display(self):
        """Update the checkbox to match photo's selection state."""
        self.checkbox.blockSignals(True)
        self.checkbox.setChecked(self.photo.is_selected)
        self.checkbox.blockSignals(False)
    
    def set_highlight(self, highlighted: bool):
        """Set highlight state for preview selection."""
        if highlighted:
            self.image_label.setStyleSheet("""
                QLabel {
                    background-color: #2d2d2d;
                    border: 2px solid #4a9eff;
                    border-radius: 8px;
                }
            """)
        else:
            self.image_label.setStyleSheet("""
                QLabel {
                    background-color: #2d2d2d;
                    border: 2px solid transparent;
                    border-radius: 8px;
                }
            """)
    
    def mousePressEvent(self, event: QMouseEvent):
        """Handle mouse press."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.photo)
        super().mousePressEvent(event)
    
    def mouseDoubleClickEvent(self, event: QMouseEvent):
        """Handle double click."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.double_clicked.emit(self.photo)
        super().mouseDoubleClickEvent(event)
    
    def contextMenuEvent(self, event):
        """Show right-click context menu."""
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #2d2d2d;
                border: 1px solid #444;
                border-radius: 6px;
                padding: 4px;
            }
            QMenu::item {
                color: #e0e0e0;
                padding: 8px 20px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #4a9eff;
            }
            QMenu::separator {
                height: 1px;
                background-color: #444;
                margin: 4px 0;
            }
        """)
        
        # Open actions
        open_action = QAction("📂 Open File", self)
        open_action.triggered.connect(self._open_file)
        menu.addAction(open_action)
        
        show_folder_action = QAction("📁 Show in Explorer", self)
        show_folder_action.triggered.connect(self._show_in_explorer)
        menu.addAction(show_folder_action)
        
        menu.addSeparator()
        
        # Selection
        if self.photo.is_selected:
            deselect_action = QAction("☐ Deselect", self)
            deselect_action.triggered.connect(lambda: self.set_selected(False))
            menu.addAction(deselect_action)
        else:
            select_action = QAction("☑ Select", self)
            select_action.triggered.connect(lambda: self.set_selected(True))
            menu.addAction(select_action)
        
        menu.addSeparator()
        
        # Edit actions
        rename_action = QAction("✏️ Rename...", self)
        rename_action.triggered.connect(lambda: self.rename_requested.emit(self.photo))
        menu.addAction(rename_action)
        
        location_action = QAction("📍 Set Location...", self)
        location_action.triggered.connect(lambda: self.set_location_requested.emit(self.photo))
        menu.addAction(location_action)
        
        menu.addSeparator()
        
        # Delete
        delete_action = QAction("🗑️ Delete", self)
        delete_action.triggered.connect(lambda: self.delete_requested.emit(self.photo))
        menu.addAction(delete_action)
        
        menu.exec(event.globalPos())
    
    def _open_file(self):
        """Open the photo with default application."""
        if os.name == 'nt':  # Windows
            os.startfile(str(self.photo.path))
        else:
            subprocess.run(['xdg-open', str(self.photo.path)])
    
    def _show_in_explorer(self):
        """Show the file in Windows Explorer."""
        if os.name == 'nt':
            subprocess.run(['explorer', '/select,', str(self.photo.path)])
        else:
            subprocess.run(['xdg-open', str(self.photo.path.parent)])


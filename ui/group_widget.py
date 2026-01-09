"""
Collapsible group widget for displaying grouped photos.
"""
from typing import List

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QSizePolicy
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from core.photo import Photo
from sorting.grouped import PhotoGroup
from .photo_thumbnail import PhotoThumbnailWidget
from .flow_layout import FlowLayout
from .view_items import ViewMode, PhotoListItem, PhotoDetailItem, PhotoTileItem


class GroupWidget(QWidget):
    """Collapsible widget displaying a group of photos."""
    
    photo_clicked = Signal(Photo)
    photo_double_clicked = Signal(Photo)
    selection_changed = Signal()
    delete_requested = Signal(Photo)
    remove_requested = Signal(Photo)
    
    def __init__(self, group: PhotoGroup, view_mode: str = "thumbnails", parent=None):
        super().__init__(parent)
        self.group = group
        self._view_mode = view_mode
        self._thumbnail_widgets: List = []
        self._setup_ui()
    
    def _setup_ui(self):
        """Set up the group widget UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 8)
        layout.setSpacing(0)
        
        # Header
        self.header = self._create_header()
        layout.addWidget(self.header)
        
        # Content area - layout depends on view mode
        self.content = QWidget()
        if self._view_mode in ("list", "details"):
            # Vertical list layout
            self.content_layout = QVBoxLayout(self.content)
            self.content_layout.setContentsMargins(8, 8, 8, 8)
            self.content_layout.setSpacing(2)
        else:
            # Flow layout for thumbnails/tiles
            self.content_layout = FlowLayout(self.content, margin=8, spacing=8)
        
        self.content.setStyleSheet("background-color: #1a1a1a; border-radius: 0 0 8px 8px;")
        layout.addWidget(self.content)
        
        # Set visibility based on expanded state
        self.content.setVisible(self.group.is_expanded)
        
        self.setStyleSheet("""
            GroupWidget {
                background-color: transparent;
            }
        """)
    
    def _create_header(self) -> QWidget:
        """Create the group header."""
        header = QFrame()
        header.setStyleSheet("""
            QFrame {
                background-color: #2d2d2d;
                border-radius: 8px 8px 0 0;
                padding: 4px;
            }
        """)
        
        layout = QHBoxLayout(header)
        layout.setContentsMargins(12, 8, 12, 8)
        
        # Expand/collapse button
        self.toggle_btn = QPushButton("▼" if self.group.is_expanded else "▶")
        self.toggle_btn.setFixedSize(24, 24)
        self.toggle_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                color: #888;
                font-size: 12px;
            }
            QPushButton:hover {
                color: #fff;
            }
        """)
        self.toggle_btn.clicked.connect(self._toggle_expand)
        layout.addWidget(self.toggle_btn)
        
        # Group name
        self.name_label = QLabel(self.group.display_name)
        self.name_label.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.name_label.setStyleSheet("color: #e0e0e0;")
        layout.addWidget(self.name_label)
        
        # Photo count
        self.count_label = QLabel(f"({self.group.count} photos)")
        self.count_label.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(self.count_label)
        
        layout.addStretch()
        
        # Select all button
        self.select_all_btn = QPushButton("Select All")
        self.select_all_btn.setStyleSheet("""
            QPushButton {
                background-color: #3a3a3a;
                border: 1px solid #555;
                border-radius: 4px;
                color: #e0e0e0;
                padding: 4px 12px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #4a4a4a;
            }
        """)
        self.select_all_btn.clicked.connect(self._toggle_select_all)
        layout.addWidget(self.select_all_btn)
        
        return header
    
    def _toggle_expand(self):
        """Toggle the expanded state."""
        self.group.is_expanded = not self.group.is_expanded
        self.content.setVisible(self.group.is_expanded)
        self.toggle_btn.setText("▼" if self.group.is_expanded else "▶")
        
        # Update header style based on state
        if self.group.is_expanded:
            self.header.setStyleSheet("""
                QFrame {
                    background-color: #2d2d2d;
                    border-radius: 8px 8px 0 0;
                }
            """)
        else:
            self.header.setStyleSheet("""
                QFrame {
                    background-color: #2d2d2d;
                    border-radius: 8px;
                }
            """)
    
    def _toggle_select_all(self):
        """Toggle selection of all photos in this group."""
        self.group.toggle_selection()
        self._update_select_button()
        self._update_thumbnail_selections()
        self.selection_changed.emit()
    
    def _update_select_button(self):
        """Update the select all button text."""
        if self.group.all_selected:
            self.select_all_btn.setText("Deselect All")
        else:
            self.select_all_btn.setText("Select All")
    
    def _update_thumbnail_selections(self):
        """Update all thumbnail checkboxes."""
        for widget in self._thumbnail_widgets:
            widget.update_selection_display()
    
    def add_photos(self, thumbnail_manager):
        """Add photo widgets to this group based on current view mode."""
        for photo in self.group.photos:
            # Generate thumbnail if needed (for all modes)
            if not photo.thumbnail_path:
                photo.thumbnail_path = thumbnail_manager.get_thumbnail(photo.path)
            
            # Create appropriate widget based on view mode
            if self._view_mode == "list":
                item = PhotoListItem(photo)
            elif self._view_mode == "details":
                item = PhotoDetailItem(photo)
            elif self._view_mode == "tiles":
                item = PhotoTileItem(photo)
            else:  # thumbnails (default)
                item = PhotoThumbnailWidget(photo)
            
            item.clicked.connect(self._on_photo_clicked)
            item.double_clicked.connect(self._on_photo_double_clicked)
            item.selection_changed.connect(self._on_selection_changed)
            
            # Connect context menu actions if available
            if hasattr(item, 'delete_requested'):
                item.delete_requested.connect(self.delete_requested.emit)
            if hasattr(item, 'remove_requested'):
                item.remove_requested.connect(self.remove_requested.emit)
            
            self._thumbnail_widgets.append(item)
            self.content_layout.addWidget(item)
    
    def _on_photo_clicked(self, photo: Photo):
        """Handle photo click."""
        self.photo_clicked.emit(photo)
    
    def _on_photo_double_clicked(self, photo: Photo):
        """Handle photo double click."""
        self.photo_double_clicked.emit(photo)
    
    def _on_selection_changed(self, photo: Photo, selected: bool):
        """Handle individual photo selection change."""
        self._update_select_button()
        self.selection_changed.emit()
    
    def highlight_photo(self, photo: Photo):
        """Highlight a specific photo thumbnail."""
        for widget in self._thumbnail_widgets:
            widget.set_highlight(widget.photo == photo)
    
    def clear_highlight(self):
        """Clear all highlights."""
        for widget in self._thumbnail_widgets:
            widget.set_highlight(False)
    
    def update_count_label(self):
        """Update the photo count label."""
        selected = self.group.selected_count
        total = self.group.count
        if selected > 0:
            self.count_label.setText(f"({selected}/{total} selected)")
        else:
            self.count_label.setText(f"({total} photos)")

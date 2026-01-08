"""
Metadata display panel for showing photo information.
"""
from typing import Optional
from datetime import datetime

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QGridLayout, QFrame
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from core.photo import Photo


class MetadataPanel(QWidget):
    """Panel for displaying photo metadata."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
    
    def _setup_ui(self):
        """Set up the metadata panel UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Container
        container = QFrame()
        container.setStyleSheet("""
            QFrame {
                background-color: #1a1a1a;
                border-radius: 8px;
                padding: 8px;
            }
        """)
        container_layout = QVBoxLayout(container)
        
        # Title
        title = QLabel("Photo Details")
        title.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        title.setStyleSheet("color: #e0e0e0; margin-bottom: 8px;")
        container_layout.addWidget(title)
        
        # Metadata grid
        self.grid = QGridLayout()
        self.grid.setSpacing(8)
        container_layout.addLayout(self.grid)
        
        # Create labels for each field
        self._labels = {}
        fields = [
            ('filename', 'Filename'),
            ('date', 'Date Taken'),
            ('location', 'Location'),
            ('camera', 'Camera'),
            ('size', 'File Size'),
            ('dimensions', 'Dimensions'),
            ('gps', 'GPS Coordinates'),
        ]
        
        for row, (key, label) in enumerate(fields):
            label_widget = QLabel(f"{label}:")
            label_widget.setFont(QFont("Segoe UI", 10))
            label_widget.setStyleSheet("color: #888;")
            self.grid.addWidget(label_widget, row, 0, Qt.AlignmentFlag.AlignTop)
            
            value_widget = QLabel("-")
            value_widget.setFont(QFont("Segoe UI", 10))
            value_widget.setStyleSheet("color: #e0e0e0;")
            value_widget.setWordWrap(True)
            self.grid.addWidget(value_widget, row, 1)
            
            self._labels[key] = value_widget
        
        container_layout.addStretch()
        layout.addWidget(container)
    
    def set_photo(self, photo: Optional[Photo]):
        """Update the panel with photo metadata."""
        if photo is None:
            for label in self._labels.values():
                label.setText("-")
            return
        
        # Filename
        self._labels['filename'].setText(photo.filename)
        
        # Date
        if photo.date_taken:
            date_str = photo.date_taken.strftime("%B %d, %Y at %H:%M")
        else:
            date_str = "Unknown"
        self._labels['date'].setText(date_str)
        
        # Location
        if photo.location_name:
            self._labels['location'].setText(photo.location_name)
        elif photo.has_location:
            self._labels['location'].setText("(GPS data available)")
        else:
            self._labels['location'].setText("Unknown")
        
        # Camera
        camera_parts = []
        if photo.camera_make:
            camera_parts.append(photo.camera_make)
        if photo.camera_model:
            camera_parts.append(photo.camera_model)
        self._labels['camera'].setText(" ".join(camera_parts) if camera_parts else "Unknown")
        
        # File size
        size = photo.file_size
        if size >= 1024 * 1024:
            size_str = f"{size / (1024 * 1024):.1f} MB"
        elif size >= 1024:
            size_str = f"{size / 1024:.1f} KB"
        else:
            size_str = f"{size} bytes"
        self._labels['size'].setText(size_str)
        
        # Dimensions (not available from metadata, would need to load image)
        self._labels['dimensions'].setText("-")
        
        # GPS
        if photo.has_location:
            gps_str = f"{photo.gps_latitude:.6f}, {photo.gps_longitude:.6f}"
            self._labels['gps'].setText(gps_str)
        else:
            self._labels['gps'].setText("-")
    
    def clear(self):
        """Clear all metadata."""
        self.set_photo(None)

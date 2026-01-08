"""
Location Tagging Dialog - manually assign locations to photos.
"""
from typing import List, Optional
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QListWidget, QListWidgetItem, QMessageBox,
    QCompleter, QFrame
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from core.photo import Photo
from core.geocoding import GeocodingService


class LocationDialog(QDialog):
    """Dialog for manually tagging photos with a location."""
    
    # Common locations for quick selection
    RECENT_LOCATIONS = []  # Will be populated from history
    
    def __init__(self, photos: List[Photo], geocoding_service: GeocodingService = None, parent=None):
        super().__init__(parent)
        self.photos = photos
        self.geocoding = geocoding_service or GeocodingService()
        self.selected_location: Optional[str] = None
        
        self._setup_ui()
        self._load_recent_locations()
    
    def _setup_ui(self):
        self.setWindowTitle(f"Set Location for {len(self.photos)} Photo(s)")
        self.setMinimumSize(450, 400)
        self.setStyleSheet("""
            QDialog {
                background-color: #1e1e1e;
            }
            QLabel {
                color: #e0e0e0;
            }
            QLineEdit {
                background-color: #2d2d2d;
                border: 1px solid #444;
                border-radius: 6px;
                padding: 10px;
                color: #e0e0e0;
                font-size: 14px;
            }
            QLineEdit:focus {
                border-color: #4a9eff;
            }
            QListWidget {
                background-color: #2d2d2d;
                border: 1px solid #444;
                border-radius: 6px;
                color: #e0e0e0;
                font-size: 12px;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #333;
            }
            QListWidget::item:hover {
                background-color: #3a3a3a;
            }
            QListWidget::item:selected {
                background-color: #4a9eff;
            }
            QPushButton {
                background-color: #3a3a3a;
                border: 1px solid #555;
                border-radius: 6px;
                color: #e0e0e0;
                padding: 10px 20px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #4a4a4a;
            }
            QPushButton:disabled {
                background-color: #2a2a2a;
                color: #555;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Header
        header = QLabel(f"📍 Set Location for {len(self.photos)} Photo(s)")
        header.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        layout.addWidget(header)
        
        # Description
        desc = QLabel("Enter a location name (e.g., 'Sydney, Australia' or 'Tokyo, Japan')")
        desc.setStyleSheet("color: #888;")
        layout.addWidget(desc)
        
        # Location input
        self.location_input = QLineEdit()
        self.location_input.setPlaceholderText("Type location name...")
        self.location_input.textChanged.connect(self._on_text_changed)
        layout.addWidget(self.location_input)
        
        # Recent locations section
        recent_label = QLabel("Recent Locations:")
        recent_label.setStyleSheet("color: #888; margin-top: 8px;")
        layout.addWidget(recent_label)
        
        self.recent_list = QListWidget()
        self.recent_list.itemClicked.connect(self._on_recent_selected)
        layout.addWidget(self.recent_list, stretch=1)
        
        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet("background-color: #444;")
        layout.addWidget(separator)
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        
        self.clear_btn = QPushButton("Clear Location")
        self.clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #5a2a2a;
                border-color: #a44;
            }
            QPushButton:hover {
                background-color: #7a3a3a;
            }
        """)
        self.clear_btn.clicked.connect(self._clear_location)
        btn_layout.addWidget(self.clear_btn)
        
        btn_layout.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        self.apply_btn = QPushButton("Apply Location")
        self.apply_btn.setStyleSheet("""
            QPushButton {
                background-color: #2d5a2d;
                border-color: #3a7a3a;
            }
            QPushButton:hover {
                background-color: #3a7a3a;
            }
        """)
        self.apply_btn.clicked.connect(self._apply_location)
        self.apply_btn.setEnabled(False)
        btn_layout.addWidget(self.apply_btn)
        
        layout.addLayout(btn_layout)
    
    def _load_recent_locations(self):
        """Load recent locations from geocoding cache."""
        self.recent_list.clear()
        
        # Get unique locations from cache
        locations = set()
        for cache_key, address in self.geocoding.cache.items():
            if isinstance(address, dict):
                city = (
                    address.get('city') or 
                    address.get('town') or 
                    address.get('village') or
                    address.get('municipality')
                )
                country = address.get('country')
                if city and country:
                    locations.add(f"{city}, {country}")
                elif country:
                    locations.add(country)
        
        # Add some common defaults
        defaults = [
            "Sydney, Australia",
            "Melbourne, Australia",
            "Brisbane, Australia",
            "Tokyo, Japan",
            "New York, USA",
            "London, UK",
            "Paris, France",
        ]
        
        for loc in defaults:
            locations.add(loc)
        
        # Sort and add to list
        for loc in sorted(locations):
            item = QListWidgetItem(f"📍 {loc}")
            item.setData(Qt.ItemDataRole.UserRole, loc)
            self.recent_list.addItem(item)
    
    def _on_text_changed(self, text: str):
        """Enable apply button when text is entered."""
        self.apply_btn.setEnabled(len(text.strip()) > 0)
    
    def _on_recent_selected(self, item: QListWidgetItem):
        """Fill input with selected recent location."""
        location = item.data(Qt.ItemDataRole.UserRole)
        self.location_input.setText(location)
    
    def _apply_location(self):
        """Apply the location to all selected photos."""
        location = self.location_input.text().strip()
        if not location:
            return
        
        # Apply to all photos
        for photo in self.photos:
            photo.location_name = location
        
        self.selected_location = location
        
        # Add to recent locations class variable
        if location not in LocationDialog.RECENT_LOCATIONS:
            LocationDialog.RECENT_LOCATIONS.insert(0, location)
            LocationDialog.RECENT_LOCATIONS = LocationDialog.RECENT_LOCATIONS[:20]
        
        QMessageBox.information(
            self,
            "Location Set",
            f"Set location to '{location}' for {len(self.photos)} photo(s).\n\n"
            "Note: This only affects sorting within this session.\n"
            "The original files are not modified."
        )
        
        self.accept()
    
    def _clear_location(self):
        """Clear location from all selected photos."""
        reply = QMessageBox.question(
            self,
            "Clear Location",
            f"Clear the location tag from {len(self.photos)} photo(s)?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            for photo in self.photos:
                photo.location_name = None
            self.selected_location = None
            self.accept()

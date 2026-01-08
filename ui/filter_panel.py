"""
Filter Builder Panel - extensible filter management UI.
"""
from typing import List, Dict, Optional
from dataclasses import dataclass

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QSizePolicy, QComboBox
)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QFont


@dataclass
class FilterConfig:
    """Configuration for a single filter."""
    filter_id: str
    display_name: str
    icon: str
    is_active: bool = False


class FilterItem(QFrame):
    """A single filter item in the filter panel."""
    
    removed = Signal(str)  # filter_id
    moved_up = Signal(str)
    moved_down = Signal(str)
    
    def __init__(self, filter_config: FilterConfig, index: int, total: int, parent=None):
        super().__init__(parent)
        self.filter_id = filter_config.filter_id
        self.display_name = filter_config.display_name
        self.icon = filter_config.icon
        self._index = index
        self._total = total
        
        self._setup_ui()
    
    def _setup_ui(self):
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet("""
            FilterItem {
                background-color: #2d2d2d;
                border: 1px solid #444;
                border-radius: 6px;
                margin: 2px;
            }
            FilterItem:hover {
                border-color: #4a9eff;
            }
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(8)
        
        # Order number
        self.order_label = QLabel(f"{self._index + 1}.")
        self.order_label.setStyleSheet("color: #888; font-weight: bold; min-width: 20px;")
        layout.addWidget(self.order_label)
        
        # Icon and name
        name_label = QLabel(f"{self.icon} {self.display_name}")
        name_label.setFont(QFont("Segoe UI", 10))
        name_label.setStyleSheet("color: #e0e0e0;")
        layout.addWidget(name_label, stretch=1)
        
        # Move up button
        self.up_btn = QPushButton("▲")
        self.up_btn.setFixedSize(24, 24)
        self.up_btn.setStyleSheet(self._small_btn_style())
        self.up_btn.clicked.connect(lambda: self.moved_up.emit(self.filter_id))
        self.up_btn.setEnabled(self._index > 0)
        layout.addWidget(self.up_btn)
        
        # Move down button
        self.down_btn = QPushButton("▼")
        self.down_btn.setFixedSize(24, 24)
        self.down_btn.setStyleSheet(self._small_btn_style())
        self.down_btn.clicked.connect(lambda: self.moved_down.emit(self.filter_id))
        self.down_btn.setEnabled(self._index < self._total - 1)
        layout.addWidget(self.down_btn)
        
        # Remove button
        remove_btn = QPushButton("×")
        remove_btn.setFixedSize(24, 24)
        remove_btn.setStyleSheet(self._remove_btn_style())
        remove_btn.clicked.connect(lambda: self.removed.emit(self.filter_id))
        layout.addWidget(remove_btn)
    
    def update_position(self, index: int, total: int):
        """Update position indicators."""
        self._index = index
        self._total = total
        self.order_label.setText(f"{index + 1}.")
        self.up_btn.setEnabled(index > 0)
        self.down_btn.setEnabled(index < total - 1)
    
    def _small_btn_style(self) -> str:
        return """
            QPushButton {
                background-color: #3a3a3a;
                border: 1px solid #555;
                border-radius: 4px;
                color: #888;
                font-size: 10px;
            }
            QPushButton:hover {
                background-color: #4a4a4a;
                color: #e0e0e0;
            }
            QPushButton:disabled {
                color: #444;
            }
        """
    
    def _remove_btn_style(self) -> str:
        return """
            QPushButton {
                background-color: #3a3a3a;
                border: 1px solid #555;
                border-radius: 4px;
                color: #888;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #5a2a2a;
                border-color: #a44;
                color: #faa;
            }
        """


class FilterPanel(QWidget):
    """Panel for building and managing filter combinations."""
    
    filters_changed = Signal(list)  # List of filter_ids in order
    sort_order_changed = Signal(bool)  # ascending
    
    # Available filter types
    AVAILABLE_FILTERS = {
        'date': FilterConfig('date', 'Date', '📅'),
        'location': FilterConfig('location', 'Location', '📍'),
        'camera': FilterConfig('camera', 'Camera', '📷'),
    }
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._active_filters: List[str] = []
        self._filter_items: Dict[str, FilterItem] = {}
        self._sort_ascending = True
        
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        
        # Header
        header = QLabel("Group by")
        header.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        header.setStyleSheet("color: #e0e0e0;")
        layout.addWidget(header)
        
        # Filter list container
        self.filter_container = QWidget()
        self.filter_layout = QVBoxLayout(self.filter_container)
        self.filter_layout.setContentsMargins(0, 0, 0, 0)
        self.filter_layout.setSpacing(4)
        layout.addWidget(self.filter_container)
        
        # Add filter row
        add_row = QHBoxLayout()
        add_row.setSpacing(8)
        
        self.add_combo = QComboBox()
        self.add_combo.setStyleSheet(self._combo_style())
        add_row.addWidget(self.add_combo, stretch=1)
        
        self.add_btn = QPushButton("+ Add")
        self.add_btn.setStyleSheet(self._add_btn_style())
        self.add_btn.clicked.connect(self._add_selected_filter)
        add_row.addWidget(self.add_btn)
        
        # Now update combo (after add_btn exists)
        self._update_add_combo()
        
        layout.addLayout(add_row)
        
        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet("background-color: #444;")
        layout.addWidget(separator)
        
        # Sort order row
        order_row = QHBoxLayout()
        order_row.setSpacing(8)
        
        order_label = QLabel("Order:")
        order_label.setStyleSheet("color: #888;")
        order_row.addWidget(order_label)
        
        self.order_btn = QPushButton("↑ Oldest First")
        self.order_btn.setStyleSheet(self._order_btn_style())
        self.order_btn.clicked.connect(self._toggle_order)
        order_row.addWidget(self.order_btn, stretch=1)
        
        layout.addLayout(order_row)
        
        # Spacer
        layout.addStretch()
        
        # Style the panel
        self.setStyleSheet("""
            FilterPanel {
                background-color: #1a1a1a;
                border-right: 1px solid #333;
            }
        """)
        self.setMinimumWidth(200)
        self.setMaximumWidth(280)
    
    def _update_add_combo(self):
        """Update the add filter combo with available filters."""
        self.add_combo.clear()
        for filter_id, config in self.AVAILABLE_FILTERS.items():
            if filter_id not in self._active_filters:
                self.add_combo.addItem(f"{config.icon} {config.display_name}", filter_id)
        
        self.add_btn.setEnabled(self.add_combo.count() > 0)
        if self.add_combo.count() == 0:
            self.add_combo.addItem("All filters active", None)
    
    def _add_selected_filter(self):
        """Add the currently selected filter."""
        filter_id = self.add_combo.currentData()
        if filter_id:
            self.add_filter(filter_id)
    
    def add_filter(self, filter_id: str):
        """Add a filter to the active list."""
        if filter_id in self._active_filters:
            return
        
        self._active_filters.append(filter_id)
        self._rebuild_filter_list()
        self._update_add_combo()
        self.filters_changed.emit(self._active_filters.copy())
    
    def remove_filter(self, filter_id: str):
        """Remove a filter from the active list."""
        if filter_id in self._active_filters:
            self._active_filters.remove(filter_id)
            self._rebuild_filter_list()
            self._update_add_combo()
            self.filters_changed.emit(self._active_filters.copy())
    
    def move_filter_up(self, filter_id: str):
        """Move a filter up in the order."""
        idx = self._active_filters.index(filter_id)
        if idx > 0:
            self._active_filters[idx], self._active_filters[idx-1] = \
                self._active_filters[idx-1], self._active_filters[idx]
            self._rebuild_filter_list()
            self.filters_changed.emit(self._active_filters.copy())
    
    def move_filter_down(self, filter_id: str):
        """Move a filter down in the order."""
        idx = self._active_filters.index(filter_id)
        if idx < len(self._active_filters) - 1:
            self._active_filters[idx], self._active_filters[idx+1] = \
                self._active_filters[idx+1], self._active_filters[idx]
            self._rebuild_filter_list()
            self.filters_changed.emit(self._active_filters.copy())
    
    def _rebuild_filter_list(self):
        """Rebuild the filter item widgets."""
        # Clear existing
        for item in self._filter_items.values():
            self.filter_layout.removeWidget(item)
            item.deleteLater()
        self._filter_items.clear()
        
        # Create new items
        total = len(self._active_filters)
        for idx, filter_id in enumerate(self._active_filters):
            config = self.AVAILABLE_FILTERS[filter_id]
            item = FilterItem(config, idx, total)
            item.removed.connect(self.remove_filter)
            item.moved_up.connect(self.move_filter_up)
            item.moved_down.connect(self.move_filter_down)
            self._filter_items[filter_id] = item
            self.filter_layout.addWidget(item)
    
    def _toggle_order(self):
        """Toggle sort order."""
        self._sort_ascending = not self._sort_ascending
        if self._sort_ascending:
            self.order_btn.setText("↑ Oldest First")
        else:
            self.order_btn.setText("↓ Newest First")
        self.sort_order_changed.emit(self._sort_ascending)
    
    def get_active_filters(self) -> List[str]:
        """Get list of active filter IDs in order."""
        return self._active_filters.copy()
    
    def set_active_filters(self, filter_ids: List[str]):
        """Set the active filters."""
        self._active_filters = [f for f in filter_ids if f in self.AVAILABLE_FILTERS]
        self._rebuild_filter_list()
        self._update_add_combo()
    
    def _combo_style(self) -> str:
        return """
            QComboBox {
                background-color: #2d2d2d;
                border: 1px solid #444;
                border-radius: 4px;
                color: #e0e0e0;
                padding: 6px 8px;
                font-size: 11px;
            }
            QComboBox:hover {
                border-color: #555;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 5px solid #888;
            }
            QComboBox QAbstractItemView {
                background-color: #2d2d2d;
                border: 1px solid #444;
                color: #e0e0e0;
                selection-background-color: #4a9eff;
            }
        """
    
    def _add_btn_style(self) -> str:
        return """
            QPushButton {
                background-color: #2d5a2d;
                border: 1px solid #3a7a3a;
                border-radius: 4px;
                color: #e0e0e0;
                padding: 6px 12px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #3a7a3a;
            }
            QPushButton:disabled {
                background-color: #2a2a2a;
                color: #555;
            }
        """
    
    def _order_btn_style(self) -> str:
        return """
            QPushButton {
                background-color: #2d2d2d;
                border: 1px solid #444;
                border-radius: 4px;
                color: #e0e0e0;
                padding: 6px 12px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #3a3a3a;
            }
        """

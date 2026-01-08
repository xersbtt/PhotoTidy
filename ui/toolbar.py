"""
Toolbar widget with sorting controls and action buttons.
"""
from typing import List

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QPushButton, QLabel, QSpacerItem, QSizePolicy
)
from PySide6.QtCore import Signal
from PySide6.QtGui import QFont


class ToolBar(QWidget):
    """Toolbar with action buttons."""
    
    open_folder_clicked = Signal()
    rename_clicked = Signal()
    set_location_clicked = Signal()
    rotate_cw_clicked = Signal()
    rotate_ccw_clicked = Signal()
    move_clicked = Signal()
    copy_clicked = Signal()
    undo_clicked = Signal()
    select_all_clicked = Signal()
    deselect_all_clicked = Signal()
    view_mode_changed = Signal(str)  # 'thumbnails', 'tiles', 'list', 'details'
    settings_clicked = Signal()
    about_clicked = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
    
    def _setup_ui(self):
        """Set up the toolbar UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(8)
        
        # Open folder button
        self.open_btn = QPushButton("📁 Open Folder")
        self.open_btn.setStyleSheet(self._primary_button_style())
        self.open_btn.clicked.connect(self.open_folder_clicked.emit)
        layout.addWidget(self.open_btn)
        
        # Separator
        layout.addSpacing(16)
        
        # Selection buttons
        self.select_all_btn = QPushButton("Select All")
        self.select_all_btn.setStyleSheet(self._button_style())
        self.select_all_btn.clicked.connect(self.select_all_clicked.emit)
        layout.addWidget(self.select_all_btn)
        
        self.deselect_btn = QPushButton("Deselect All")
        self.deselect_btn.setStyleSheet(self._button_style())
        self.deselect_btn.clicked.connect(self.deselect_all_clicked.emit)
        layout.addWidget(self.deselect_btn)
        
        # View mode buttons
        layout.addSpacing(12)
        view_label = QLabel("🔍")
        view_label.setStyleSheet("color: #888; font-size: 14px;")
        layout.addWidget(view_label)
        
        self._view_mode = "thumbnails"
        self.view_btns = {}
        for mode, icon, tooltip in [
            ("thumbnails", "▦", "Thumbnails - Large icons"),
            ("tiles", "▨", "Tiles - Medium with info"),
            ("list", "☰", "List - Compact"),
            ("details", "☷", "Details - Table view"),
        ]:
            btn = QPushButton(icon)
            btn.setToolTip(tooltip)
            btn.setFixedSize(28, 28)
            btn.setStyleSheet(self._view_btn_style(mode == self._view_mode))
            btn.clicked.connect(lambda checked, m=mode: self._set_view_mode(m))
            self.view_btns[mode] = btn
            layout.addWidget(btn)
        
        # Spacer
        layout.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        
        # Selection count label
        self.selection_label = QLabel("0 selected")
        self.selection_label.setFont(QFont("Segoe UI", 10))
        self.selection_label.setStyleSheet("color: #888;")
        layout.addWidget(self.selection_label)
        
        # Separator
        layout.addSpacing(16)
        
        # Action buttons
        self.rename_btn = QPushButton("✏️ Rename...")
        self.rename_btn.setStyleSheet(self._button_style())
        self.rename_btn.clicked.connect(self.rename_clicked.emit)
        self.rename_btn.setEnabled(False)
        layout.addWidget(self.rename_btn)
        
        self.location_btn = QPushButton("📍 Set Location...")
        self.location_btn.setToolTip("Manually set location for selected photos")
        self.location_btn.setStyleSheet(self._button_style())
        self.location_btn.clicked.connect(self.set_location_clicked.emit)
        self.location_btn.setEnabled(False)
        layout.addWidget(self.location_btn)
        
        self.rotate_ccw_btn = QPushButton("↺")
        self.rotate_ccw_btn.setToolTip("Rotate counterclockwise")
        self.rotate_ccw_btn.setStyleSheet(self._small_button_style())
        self.rotate_ccw_btn.clicked.connect(self.rotate_ccw_clicked.emit)
        self.rotate_ccw_btn.setEnabled(False)
        layout.addWidget(self.rotate_ccw_btn)
        
        self.rotate_cw_btn = QPushButton("↻")
        self.rotate_cw_btn.setToolTip("Rotate clockwise")
        self.rotate_cw_btn.setStyleSheet(self._small_button_style())
        self.rotate_cw_btn.clicked.connect(self.rotate_cw_clicked.emit)
        self.rotate_cw_btn.setEnabled(False)
        layout.addWidget(self.rotate_cw_btn)
        
        self.move_btn = QPushButton("📦 Move to...")
        self.move_btn.setStyleSheet(self._action_button_style())
        self.move_btn.clicked.connect(self.move_clicked.emit)
        self.move_btn.setEnabled(False)
        layout.addWidget(self.move_btn)
        
        self.copy_btn = QPushButton("📋 Copy to...")
        self.copy_btn.setStyleSheet(self._action_button_style())
        self.copy_btn.clicked.connect(self.copy_clicked.emit)
        self.copy_btn.setEnabled(False)
        layout.addWidget(self.copy_btn)
        
        # Undo button
        self.undo_btn = QPushButton("↩️ Undo")
        self.undo_btn.setStyleSheet(self._button_style())
        self.undo_btn.clicked.connect(self.undo_clicked.emit)
        self.undo_btn.setEnabled(False)
        layout.addWidget(self.undo_btn)
        
        # Spacer before settings/about
        layout.addSpacing(12)
        
        # Settings button
        self.settings_btn = QPushButton("⚙️")
        self.settings_btn.setToolTip("Settings (Ctrl+,)")
        self.settings_btn.setFixedSize(32, 32)
        self.settings_btn.setStyleSheet(self._icon_button_style())
        self.settings_btn.clicked.connect(self.settings_clicked.emit)
        layout.addWidget(self.settings_btn)
        
        # About button
        self.about_btn = QPushButton("ℹ️")
        self.about_btn.setToolTip("About PhotoTidy (F1)")
        self.about_btn.setFixedSize(32, 32)
        self.about_btn.setStyleSheet(self._icon_button_style())
        self.about_btn.clicked.connect(self.about_clicked.emit)
        layout.addWidget(self.about_btn)
        
        # Style the toolbar
        self.setStyleSheet("""
            ToolBar {
                background-color: #252525;
                border-bottom: 1px solid #333;
            }
        """)
    
    def update_selection_count(self, count: int, total: int):
        """Update the selection count label."""
        self.selection_label.setText(f"{count} of {total} selected")
        self.rename_btn.setEnabled(count > 0)
        self.location_btn.setEnabled(count > 0)
        self.rotate_cw_btn.setEnabled(count > 0)
        self.rotate_ccw_btn.setEnabled(count > 0)
        self.move_btn.setEnabled(count > 0)
        self.copy_btn.setEnabled(count > 0)
    
    def set_undo_enabled(self, enabled: bool):
        """Enable/disable the undo button."""
        self.undo_btn.setEnabled(enabled)
    
    def _set_view_mode(self, mode: str):
        """Set the current view mode and emit signal."""
        if mode != self._view_mode:
            self._view_mode = mode
            # Update button styles
            for m, btn in self.view_btns.items():
                btn.setStyleSheet(self._view_btn_style(m == mode))
            self.view_mode_changed.emit(mode)
    
    def _view_btn_style(self, active: bool) -> str:
        """Style for view mode buttons."""
        if active:
            return """
                QPushButton {
                    background-color: #4a9eff;
                    border: none;
                    border-radius: 4px;
                    color: white;
                    font-size: 14px;
                }
            """
        else:
            return """
                QPushButton {
                    background-color: #3a3a3a;
                    border: 1px solid #555;
                    border-radius: 4px;
                    color: #888;
                    font-size: 14px;
                }
                QPushButton:hover {
                    background-color: #4a4a4a;
                    color: #e0e0e0;
                }
            """
    
    def _icon_button_style(self) -> str:
        """Style for icon-only buttons like Settings/About."""
        return """
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 4px;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: #3a3a3a;
            }
        """
    
    def _primary_button_style(self) -> str:
        return """
            QPushButton {
                background-color: #4a9eff;
                border: none;
                border-radius: 6px;
                color: white;
                padding: 8px 16px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #5aacff;
            }
            QPushButton:pressed {
                background-color: #3a8eef;
            }
        """
    
    def _button_style(self) -> str:
        return """
            QPushButton {
                background-color: #3a3a3a;
                border: 1px solid #555;
                border-radius: 6px;
                color: #e0e0e0;
                padding: 8px 12px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #4a4a4a;
            }
            QPushButton:pressed {
                background-color: #333;
            }
            QPushButton:disabled {
                background-color: #2a2a2a;
                color: #555;
            }
        """
    
    def _small_button_style(self) -> str:
        return """
            QPushButton {
                background-color: #3a3a3a;
                border: 1px solid #555;
                border-radius: 6px;
                color: #e0e0e0;
                padding: 8px 10px;
                font-size: 16px;
                font-weight: bold;
                min-width: 32px;
            }
            QPushButton:hover {
                background-color: #4a4a4a;
            }
            QPushButton:pressed {
                background-color: #333;
            }
            QPushButton:disabled {
                background-color: #2a2a2a;
                color: #555;
            }
        """
    
    def _action_button_style(self) -> str:
        return """
            QPushButton {
                background-color: #2d5a2d;
                border: 1px solid #3a7a3a;
                border-radius: 6px;
                color: #e0e0e0;
                padding: 8px 12px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #3a7a3a;
            }
            QPushButton:pressed {
                background-color: #254a25;
            }
            QPushButton:disabled {
                background-color: #2a2a2a;
                color: #555;
            }
        """
    
    def _combo_style(self) -> str:
        return """
            QComboBox {
                background-color: #3a3a3a;
                border: 1px solid #555;
                border-radius: 6px;
                color: #e0e0e0;
                padding: 6px 12px;
                font-size: 12px;
                min-width: 180px;
            }
            QComboBox:hover {
                background-color: #4a4a4a;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #888;
                margin-right: 8px;
            }
            QComboBox QAbstractItemView {
                background-color: #2d2d2d;
                border: 1px solid #555;
                color: #e0e0e0;
                selection-background-color: #4a9eff;
            }
        """

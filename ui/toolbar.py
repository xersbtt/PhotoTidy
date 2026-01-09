"""
Toolbar widget with sorting controls and action buttons.
"""
from typing import List

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QPushButton, QLabel, QSpacerItem, QSizePolicy, QMenu
)
from PySide6.QtCore import Signal
from PySide6.QtGui import QFont


class ToolBar(QWidget):
    """Toolbar with action buttons."""
    
    open_folder_clicked = Signal()
    open_files_clicked = Signal()
    add_folder_clicked = Signal()
    rename_clicked = Signal()
    set_location_clicked = Signal()
    rotate_cw_clicked = Signal()
    rotate_ccw_clicked = Signal()
    resize_clicked = Signal()
    watermark_clicked = Signal()
    convert_clicked = Signal()
    batch_clicked = Signal()
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
        
        # File dropdown menu
        file_btn = QPushButton("📁 File ▼")
        file_btn.setStyleSheet(self._primary_button_style())
        file_menu = QMenu(self)
        file_menu.setStyleSheet(self._menu_style())
        
        open_folder_action = file_menu.addAction("📁 Open Folder")
        open_folder_action.triggered.connect(self.open_folder_clicked.emit)
        open_files_action = file_menu.addAction("📄 Open Files")
        open_files_action.triggered.connect(self.open_files_clicked.emit)
        add_folder_action = file_menu.addAction("➕ Add Folder")
        add_folder_action.triggered.connect(self.add_folder_clicked.emit)
        
        file_btn.setMenu(file_menu)
        layout.addWidget(file_btn)
        
        # Edit dropdown menu
        edit_btn = QPushButton("✏️ Edit ▼")
        edit_btn.setStyleSheet(self._button_style())
        edit_menu = QMenu(self)
        edit_menu.setStyleSheet(self._menu_style())
        
        rename_action = edit_menu.addAction("✏️ Rename...")
        rename_action.triggered.connect(self.rename_clicked.emit)
        location_action = edit_menu.addAction("📍 Set Location...")
        location_action.triggered.connect(self.set_location_clicked.emit)
        edit_menu.addSeparator()
        rotate_ccw_action = edit_menu.addAction("↺ Rotate CCW")
        rotate_ccw_action.triggered.connect(self.rotate_ccw_clicked.emit)
        rotate_cw_action = edit_menu.addAction("↻ Rotate CW")
        rotate_cw_action.triggered.connect(self.rotate_cw_clicked.emit)
        
        edit_btn.setMenu(edit_menu)
        self.edit_btn = edit_btn
        self.edit_btn.setEnabled(False)
        layout.addWidget(edit_btn)
        
        layout.addSpacing(8)
        
        # Image processing buttons
        self.batch_btn = QPushButton("⚡ Batch")
        self.batch_btn.setToolTip("Batch process with multiple operations")
        self.batch_btn.setStyleSheet(self._action_button_style())
        self.batch_btn.clicked.connect(self.batch_clicked.emit)
        self.batch_btn.setEnabled(False)
        layout.addWidget(self.batch_btn)
        
        self.resize_btn = QPushButton("📐 Resize")
        self.resize_btn.setToolTip("Resize selected photos")
        self.resize_btn.setStyleSheet(self._button_style())
        self.resize_btn.clicked.connect(self.resize_clicked.emit)
        self.resize_btn.setEnabled(False)
        layout.addWidget(self.resize_btn)
        
        self.watermark_btn = QPushButton("💧 Watermark")
        self.watermark_btn.setToolTip("Add watermark to selected photos")
        self.watermark_btn.setStyleSheet(self._button_style())
        self.watermark_btn.clicked.connect(self.watermark_clicked.emit)
        self.watermark_btn.setEnabled(False)
        layout.addWidget(self.watermark_btn)
        
        self.convert_btn = QPushButton("🔄 WebP")
        self.convert_btn.setToolTip("Convert selected photos to WebP format")
        self.convert_btn.setStyleSheet(self._button_style())
        self.convert_btn.clicked.connect(self.convert_clicked.emit)
        self.convert_btn.setEnabled(False)
        layout.addWidget(self.convert_btn)
        
        layout.addSpacing(8)
        
        # Organize dropdown menu
        organize_btn = QPushButton("📦 Organize ▼")
        organize_btn.setStyleSheet(self._action_button_style())
        organize_menu = QMenu(self)
        organize_menu.setStyleSheet(self._menu_style())
        
        move_action = organize_menu.addAction("📦 Move to...")
        move_action.triggered.connect(self.move_clicked.emit)
        copy_action = organize_menu.addAction("📋 Copy to...")
        copy_action.triggered.connect(self.copy_clicked.emit)
        
        organize_btn.setMenu(organize_menu)
        self.organize_btn = organize_btn
        self.organize_btn.setEnabled(False)
        layout.addWidget(organize_btn)
        
        # Undo button
        self.undo_btn = QPushButton("↩️ Undo")
        self.undo_btn.setStyleSheet(self._button_style())
        self.undo_btn.clicked.connect(self.undo_clicked.emit)
        self.undo_btn.setEnabled(False)
        layout.addWidget(self.undo_btn)
        
        layout.addSpacing(12)
        
        # Small selection buttons
        self.select_all_btn = QPushButton("✓")
        self.select_all_btn.setToolTip("Select All (Ctrl+A)")
        self.select_all_btn.setFixedSize(28, 28)
        self.select_all_btn.setStyleSheet(self._small_icon_button_style())
        self.select_all_btn.clicked.connect(self.select_all_clicked.emit)
        layout.addWidget(self.select_all_btn)
        
        self.deselect_btn = QPushButton("✗")
        self.deselect_btn.setToolTip("Deselect All")
        self.deselect_btn.setFixedSize(28, 28)
        self.deselect_btn.setStyleSheet(self._small_icon_button_style())
        self.deselect_btn.clicked.connect(self.deselect_all_clicked.emit)
        layout.addWidget(self.deselect_btn)
        
        # View mode buttons
        layout.addSpacing(12)
        
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
        # Enable dropdown menus when photos are selected
        self.edit_btn.setEnabled(count > 0)
        self.organize_btn.setEnabled(count > 0)
        # Enable processing buttons
        self.resize_btn.setEnabled(count > 0)
        self.watermark_btn.setEnabled(count > 0)
        self.convert_btn.setEnabled(count > 0)
        self.batch_btn.setEnabled(count > 0)
    
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
    
    def _menu_style(self) -> str:
        return """
            QMenu {
                background-color: #2d2d2d;
                border: 1px solid #555;
                border-radius: 6px;
                color: #e0e0e0;
                padding: 4px;
            }
            QMenu::item {
                padding: 8px 20px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #4a9eff;
            }
            QMenu::separator {
                height: 1px;
                background-color: #555;
                margin: 4px 8px;
            }
        """
    
    def _small_icon_button_style(self) -> str:
        return """
            QPushButton {
                background-color: #3a3a3a;
                border: 1px solid #555;
                border-radius: 4px;
                color: #e0e0e0;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #4a4a4a;
            }
            QPushButton:pressed {
                background-color: #5a5a5a;
            }
        """

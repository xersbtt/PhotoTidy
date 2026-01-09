"""
Settings dialog for Photo Sorter.
"""
from pathlib import Path
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTabWidget, QWidget, QSpinBox, QComboBox, QCheckBox,
    QLineEdit, QFileDialog, QGroupBox, QFormLayout
)
from PySide6.QtCore import Qt, Signal, QSettings
from PySide6.QtGui import QFont

from config import THUMBNAIL_SIZE, GRID_COLUMNS, LOCATION_FORMAT_OPTIONS, DEFAULT_LOCATION_FORMAT


class SettingsDialog(QDialog):
    """Settings/preferences dialog."""
    
    settings_changed = Signal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = {}
        self._setup_ui()
        self._load_settings()
    
    def _setup_ui(self):
        self.setWindowTitle("Settings")
        self.setMinimumSize(500, 400)
        self.setStyleSheet("""
            QDialog {
                background-color: #1e1e1e;
            }
            QLabel {
                color: #e0e0e0;
            }
            QGroupBox {
                color: #e0e0e0;
                border: 1px solid #444;
                border-radius: 6px;
                margin-top: 12px;
                padding-top: 12px;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            QTabWidget::pane {
                border: 1px solid #444;
                background-color: #252525;
            }
            QTabBar::tab {
                background-color: #2d2d2d;
                color: #e0e0e0;
                padding: 8px 20px;
                border: 1px solid #444;
            }
            QTabBar::tab:selected {
                background-color: #3a3a3a;
                border-bottom: none;
            }
            QSpinBox, QComboBox, QLineEdit {
                background-color: #2d2d2d;
                border: 1px solid #444;
                border-radius: 4px;
                color: #e0e0e0;
                padding: 6px;
            }
            QCheckBox {
                color: #e0e0e0;
            }
            QPushButton {
                background-color: #3a3a3a;
                border: 1px solid #555;
                border-radius: 6px;
                color: #e0e0e0;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #4a4a4a;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Tab widget
        tabs = QTabWidget()
        tabs.addTab(self._create_general_tab(), "General")
        tabs.addTab(self._create_display_tab(), "Display")
        tabs.addTab(self._create_paths_tab(), "Paths")
        layout.addWidget(tabs)
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        apply_btn = QPushButton("Apply")
        apply_btn.setStyleSheet("""
            QPushButton {
                background-color: #4a9eff;
                border: none;
                color: white;
            }
            QPushButton:hover {
                background-color: #5aacff;
            }
        """)
        apply_btn.clicked.connect(self._apply_settings)
        btn_layout.addWidget(apply_btn)
        
        layout.addLayout(btn_layout)
    
    def _create_general_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(16)
        
        # Startup group
        startup_group = QGroupBox("Startup")
        startup_layout = QVBoxLayout(startup_group)
        
        self.remember_folder_cb = QCheckBox("Remember last opened folder")
        self.remember_folder_cb.setChecked(True)
        startup_layout.addWidget(self.remember_folder_cb)
        
        self.load_subfolders_cb = QCheckBox("Include subfolders when loading")
        self.load_subfolders_cb.setChecked(True)
        startup_layout.addWidget(self.load_subfolders_cb)
        
        layout.addWidget(startup_group)
        
        # File operations group
        ops_group = QGroupBox("File Operations")
        ops_layout = QVBoxLayout(ops_group)
        
        self.confirm_move_cb = QCheckBox("Confirm before moving files")
        self.confirm_move_cb.setChecked(True)
        ops_layout.addWidget(self.confirm_move_cb)
        
        self.confirm_delete_cb = QCheckBox("Confirm before deleting files")
        self.confirm_delete_cb.setChecked(True)
        ops_layout.addWidget(self.confirm_delete_cb)
        
        layout.addWidget(ops_group)
        
        # Location group
        location_group = QGroupBox("Location")
        location_layout = QFormLayout(location_group)
        
        self.location_format_combo = QComboBox()
        # Add options from config
        for key, label in LOCATION_FORMAT_OPTIONS.items():
            self.location_format_combo.addItem(label, key)
        # Set default
        default_idx = list(LOCATION_FORMAT_OPTIONS.keys()).index(DEFAULT_LOCATION_FORMAT)
        self.location_format_combo.setCurrentIndex(default_idx)
        location_layout.addRow("Location format:", self.location_format_combo)
        
        layout.addWidget(location_group)
        layout.addStretch()
        
        return widget
    
    def _create_display_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(16)
        
        # Thumbnail group
        thumb_group = QGroupBox("Thumbnails")
        thumb_layout = QFormLayout(thumb_group)
        
        self.thumb_size_spin = QSpinBox()
        self.thumb_size_spin.setRange(100, 300)
        self.thumb_size_spin.setValue(180)
        self.thumb_size_spin.setSuffix(" px")
        thumb_layout.addRow("Thumbnail size:", self.thumb_size_spin)
        
        self.default_view_combo = QComboBox()
        self.default_view_combo.addItems(["Thumbnails", "Tiles", "List", "Details"])
        thumb_layout.addRow("Default view:", self.default_view_combo)
        
        layout.addWidget(thumb_group)
        
        # Preview group
        preview_group = QGroupBox("Preview")
        preview_layout = QVBoxLayout(preview_group)
        
        self.show_metadata_cb = QCheckBox("Show metadata panel by default")
        self.show_metadata_cb.setChecked(True)
        preview_layout.addWidget(self.show_metadata_cb)
        
        layout.addWidget(preview_group)
        layout.addStretch()
        
        return widget
    
    def _create_paths_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(16)
        
        # Default paths group
        paths_group = QGroupBox("Default Paths")
        paths_layout = QFormLayout(paths_group)
        
        # Default open folder
        open_layout = QHBoxLayout()
        self.default_open_edit = QLineEdit()
        self.default_open_edit.setPlaceholderText("Default folder to open...")
        open_layout.addWidget(self.default_open_edit, stretch=1)
        browse_open_btn = QPushButton("Browse...")
        browse_open_btn.clicked.connect(lambda: self._browse_folder(self.default_open_edit))
        open_layout.addWidget(browse_open_btn)
        paths_layout.addRow("Default folder:", open_layout)
        
        # Default export folder
        export_layout = QHBoxLayout()
        self.default_export_edit = QLineEdit()
        self.default_export_edit.setPlaceholderText("Default export location...")
        export_layout.addWidget(self.default_export_edit, stretch=1)
        browse_export_btn = QPushButton("Browse...")
        browse_export_btn.clicked.connect(lambda: self._browse_folder(self.default_export_edit))
        export_layout.addWidget(browse_export_btn)
        paths_layout.addRow("Export folder:", export_layout)
        
        layout.addWidget(paths_group)
        layout.addStretch()
        
        return widget
    
    def _browse_folder(self, line_edit: QLineEdit):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder")
        if folder:
            line_edit.setText(folder)
    
    def _load_settings(self):
        """Load settings from storage."""
        settings = QSettings('PhotoTidy', 'PhotoTidy')
        
        self.remember_folder_cb.setChecked(settings.value('remember_folder', True, type=bool))
        self.load_subfolders_cb.setChecked(settings.value('load_subfolders', True, type=bool))
        self.confirm_move_cb.setChecked(settings.value('confirm_move', True, type=bool))
        self.confirm_delete_cb.setChecked(settings.value('confirm_delete', True, type=bool))
        self.thumb_size_spin.setValue(settings.value('thumbnail_size', 180, type=int))
        self.show_metadata_cb.setChecked(settings.value('show_metadata', True, type=bool))
        self.default_open_edit.setText(settings.value('default_open_path', '', type=str))
        self.default_export_edit.setText(settings.value('default_export_path', '', type=str))
        
        # Location format
        location_format = settings.value('location_format', DEFAULT_LOCATION_FORMAT, type=str)
        idx = list(LOCATION_FORMAT_OPTIONS.keys()).index(location_format) if location_format in LOCATION_FORMAT_OPTIONS else 0
        self.location_format_combo.setCurrentIndex(idx)
    
    def _apply_settings(self):
        """Apply and save settings."""
        self.settings = {
            'remember_folder': self.remember_folder_cb.isChecked(),
            'load_subfolders': self.load_subfolders_cb.isChecked(),
            'confirm_move': self.confirm_move_cb.isChecked(),
            'confirm_delete': self.confirm_delete_cb.isChecked(),
            'location_format': self.location_format_combo.currentData(),
            'thumbnail_size': self.thumb_size_spin.value(),
            'default_view': self.default_view_combo.currentText().lower(),
            'show_metadata': self.show_metadata_cb.isChecked(),
            'default_open_path': self.default_open_edit.text(),
            'default_export_path': self.default_export_edit.text(),
        }
        
        # Save to QSettings
        qsettings = QSettings('PhotoTidy', 'PhotoTidy')
        for key, value in self.settings.items():
            qsettings.setValue(key, value)
        
        self.settings_changed.emit(self.settings)
        self.accept()

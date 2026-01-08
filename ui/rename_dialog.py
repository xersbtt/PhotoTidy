"""
Dialog for previewing and executing photo renames.
"""
from typing import List

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QLineEdit,
    QGroupBox, QMessageBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor

from core.photo import Photo
from utils.renamer import PhotoRenamer, RenamePreview


class RenameDialog(QDialog):
    """Dialog for previewing and executing photo renames."""
    
    def __init__(self, photos: List[Photo], parent=None):
        super().__init__(parent)
        self.photos = photos
        self.renamer = PhotoRenamer()
        self.previews: List[RenamePreview] = []
        
        self._setup_ui()
        self._generate_preview()
    
    def _setup_ui(self):
        """Set up the dialog UI."""
        self.setWindowTitle("Rename Photos")
        self.setMinimumSize(800, 600)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        
        # Pattern group
        pattern_group = QGroupBox("Rename Pattern")
        pattern_layout = QVBoxLayout(pattern_group)
        
        # Pattern input
        pattern_input_layout = QHBoxLayout()
        pattern_label = QLabel("Pattern:")
        pattern_label.setStyleSheet("color: #e0e0e0;")
        self.pattern_input = QLineEdit(self.renamer.pattern)
        self.pattern_input.setStyleSheet("""
            QLineEdit {
                background-color: #3a3a3a;
                border: 1px solid #555;
                border-radius: 4px;
                color: #e0e0e0;
                padding: 8px;
                font-family: monospace;
            }
        """)
        self.pattern_input.textChanged.connect(self._on_pattern_changed)
        
        pattern_input_layout.addWidget(pattern_label)
        pattern_input_layout.addWidget(self.pattern_input, stretch=1)
        pattern_layout.addLayout(pattern_input_layout)
        
        # Pattern help
        help_label = QLabel(
            "Tokens: {YYMMDD}, {YYYY}, {MM}, {DD}, {city}, {country}, {location}, "
            "{camera}, {NNN} (001), {NN} (01), {N} (1), {original}"
        )
        help_label.setStyleSheet("color: #888; font-size: 11px;")
        help_label.setWordWrap(True)
        pattern_layout.addWidget(help_label)
        
        layout.addWidget(pattern_group)
        
        # Miscellaneous info
        misc_info = QLabel(
            "📌 Photos without camera metadata (screenshots, downloads) will be named 'Misc IMG001', etc."
        )
        misc_info.setStyleSheet("color: #f0ad4e; font-size: 11px; padding: 8px;")
        layout.addWidget(misc_info)
        
        # Preview table
        preview_label = QLabel("Preview:")
        preview_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        preview_label.setStyleSheet("color: #e0e0e0;")
        layout.addWidget(preview_label)
        
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Original Name", "→", "New Name"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.setColumnWidth(1, 30)
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #1a1a1a;
                border: 1px solid #333;
                color: #e0e0e0;
                gridline-color: #333;
            }
            QTableWidget::item {
                padding: 4px;
            }
            QHeaderView::section {
                background-color: #2d2d2d;
                color: #e0e0e0;
                padding: 8px;
                border: 1px solid #333;
            }
        """)
        layout.addWidget(self.table, stretch=1)
        
        # Summary label
        self.summary_label = QLabel()
        self.summary_label.setStyleSheet("color: #888;")
        layout.addWidget(self.summary_label)
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setStyleSheet(self._button_style())
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)
        
        self.rename_btn = QPushButton("✏️ Rename Photos")
        self.rename_btn.setStyleSheet(self._action_button_style())
        self.rename_btn.clicked.connect(self._execute_rename)
        btn_layout.addWidget(self.rename_btn)
        
        layout.addLayout(btn_layout)
        
        # Dark theme
        self.setStyleSheet("""
            QDialog {
                background-color: #1e1e1e;
            }
            QGroupBox {
                color: #e0e0e0;
                border: 1px solid #444;
                border-radius: 6px;
                margin-top: 12px;
                padding-top: 12px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 4px;
            }
        """)
    
    def _on_pattern_changed(self, text: str):
        """Handle pattern input change."""
        self.renamer.pattern = text
        self._generate_preview()
    
    def _generate_preview(self):
        """Generate and display rename preview."""
        self.previews = self.renamer.generate_new_names(self.photos)
        
        self.table.setRowCount(len(self.previews))
        
        conflict_count = 0
        misc_count = 0
        
        for row, preview in enumerate(self.previews):
            # Original name
            orig_item = QTableWidgetItem(preview.original_name)
            orig_item.setFlags(orig_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 0, orig_item)
            
            # Arrow
            arrow_item = QTableWidgetItem("→")
            arrow_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            arrow_item.setFlags(arrow_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 1, arrow_item)
            
            # New name
            new_item = QTableWidgetItem(preview.new_name)
            new_item.setFlags(new_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            
            # Color coding
            if preview.has_conflict:
                new_item.setForeground(QColor("#e74c3c"))  # Red for conflicts
                conflict_count += 1
            elif preview.new_name.startswith("Misc"):
                new_item.setForeground(QColor("#f0ad4e"))  # Yellow for misc
                misc_count += 1
            else:
                new_item.setForeground(QColor("#4aff4a"))  # Green for normal
            
            self.table.setItem(row, 2, new_item)
        
        # Update summary
        summary_parts = [f"{len(self.previews)} photos"]
        if misc_count > 0:
            summary_parts.append(f"{misc_count} miscellaneous")
        if conflict_count > 0:
            summary_parts.append(f"⚠️ {conflict_count} conflicts (will be skipped)")
        
        self.summary_label.setText(" • ".join(summary_parts))
    
    def _execute_rename(self):
        """Execute the rename operations."""
        reply = QMessageBox.question(
            self,
            "Confirm Rename",
            f"Are you sure you want to rename {len(self.previews)} photos?\n\nThis cannot be undone!",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        success, skipped, errors = self.renamer.execute_renames(self.previews)
        
        msg = f"Renamed {success} photos successfully."
        if skipped > 0:
            msg += f"\nSkipped {skipped} due to conflicts."
        if errors:
            msg += f"\n\nErrors:\n" + "\n".join(errors[:5])
            if len(errors) > 5:
                msg += f"\n...and {len(errors) - 5} more errors"
        
        QMessageBox.information(self, "Rename Complete", msg)
        self.accept()
    
    def _button_style(self) -> str:
        return """
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
        """
    
    def _action_button_style(self) -> str:
        return """
            QPushButton {
                background-color: #4a9eff;
                border: none;
                border-radius: 6px;
                color: white;
                padding: 10px 20px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #5aacff;
            }
        """

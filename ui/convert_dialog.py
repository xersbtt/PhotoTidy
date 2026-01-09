"""
Dialog for converting photos to WebP format.
"""
from pathlib import Path
from typing import List

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QSlider, QCheckBox, QProgressBar, QMessageBox, QWidget
)
from PySide6.QtCore import Qt, QThread, Signal

from core.photo import Photo
from core.image_processing import convert_to_webp


class ConvertWorker(QThread):
    """Worker thread for batch conversion operations."""
    progress = Signal(int, int)
    finished = Signal(int, int, int)  # success, failed, total_size_saved
    
    def __init__(self, photos: List[Photo], output_folder: Path, settings: dict):
        super().__init__()
        self.photos = photos
        self.output_folder = output_folder
        self.settings = settings
    
    def run(self):
        success = 0
        failed = 0
        original_size = 0
        new_size = 0
        total = len(self.photos)
        
        for i, photo in enumerate(self.photos):
            output_name = photo.path.stem + ".webp"
            output_path = self.output_folder / output_name
            
            # Track original size
            try:
                original_size += photo.path.stat().st_size
            except Exception:
                pass
            
            result = convert_to_webp(
                photo_path=photo.path,
                output_path=output_path,
                quality=self.settings.get('quality', 85),
                lossless=self.settings.get('lossless', False),
                preserve_exif=True
            )
            
            if result:
                success += 1
                try:
                    new_size += output_path.stat().st_size
                except Exception:
                    pass
            else:
                failed += 1
            
            self.progress.emit(i + 1, total)
        
        # Calculate size saved
        size_saved = original_size - new_size if original_size > new_size else 0
        self.finished.emit(success, failed, size_saved)


class ConvertDialog(QDialog):
    """Dialog for converting photos to WebP format."""
    
    def __init__(self, photos: List[Photo], parent=None):
        super().__init__(parent)
        self.photos = photos
        self.worker = None
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Set up the dialog UI."""
        self.setWindowTitle("Convert to WebP")
        self.setMinimumSize(450, 350)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        
        # Info label
        info_label = QLabel(f"📸 {len(self.photos)} photos selected")
        info_label.setStyleSheet("color: #4a9eff; font-size: 14px; font-weight: bold;")
        layout.addWidget(info_label)
        
        # Description
        desc_label = QLabel(
            "WebP is a modern image format that provides superior compression for web use.\n"
            "It typically reduces file size by 25-35% compared to JPEG."
        )
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(desc_label)
        
        # Quality settings
        quality_group = QGroupBox("Compression Settings")
        quality_layout = QVBoxLayout(quality_group)
        
        # Lossless checkbox
        self.lossless_check = QCheckBox("Lossless compression (larger files, perfect quality)")
        self.lossless_check.setStyleSheet("color: #e0e0e0;")
        self.lossless_check.toggled.connect(self._on_lossless_changed)
        quality_layout.addWidget(self.lossless_check)
        
        # Quality slider
        self.quality_widget = QWidget()
        slider_layout = QHBoxLayout(self.quality_widget)
        slider_layout.setContentsMargins(0, 8, 0, 0)
        
        quality_label = QLabel("Quality:")
        quality_label.setStyleSheet("color: #e0e0e0;")
        slider_layout.addWidget(quality_label)
        
        self.quality_slider = QSlider(Qt.Orientation.Horizontal)
        self.quality_slider.setRange(1, 100)
        self.quality_slider.setValue(85)
        self.quality_slider.valueChanged.connect(self._on_quality_changed)
        slider_layout.addWidget(self.quality_slider)
        
        self.quality_label = QLabel("85%")
        self.quality_label.setMinimumWidth(40)
        self.quality_label.setStyleSheet("color: #e0e0e0;")
        slider_layout.addWidget(self.quality_label)
        
        quality_layout.addWidget(self.quality_widget)
        
        # Quality hint
        self.quality_hint = QLabel("💡 80-90 is recommended for web. Lower = smaller files.")
        self.quality_hint.setStyleSheet("color: #888; font-size: 11px;")
        quality_layout.addWidget(self.quality_hint)
        
        layout.addWidget(quality_group)
        
        # Estimated savings (rough estimate)
        self._update_estimate()
        self.estimate_label = QLabel()
        self.estimate_label.setStyleSheet("""
            QLabel {
                background-color: #2d2d2d;
                border: 1px solid #444;
                border-radius: 6px;
                padding: 12px;
                color: #4aff4a;
            }
        """)
        self._update_estimate()
        layout.addWidget(self.estimate_label)
        
        # Output info
        output_info = QLabel("📁 Output: Will be saved to 'WebP/' subfolder")
        output_info.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(output_info)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setStyleSheet(self._button_style())
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)
        
        self.convert_btn = QPushButton("🔄 Convert to WebP")
        self.convert_btn.setStyleSheet(self._action_button_style())
        self.convert_btn.clicked.connect(self._execute_convert)
        btn_layout.addWidget(self.convert_btn)
        
        layout.addLayout(btn_layout)
        
        # Apply dark theme
        self.setStyleSheet("""
            QDialog { background-color: #1e1e1e; }
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
            QSlider::groove:horizontal {
                border: 1px solid #555;
                height: 6px;
                background: #3a3a3a;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #4a9eff;
                border-radius: 7px;
                width: 14px;
                margin: -4px 0;
            }
        """)
    
    def _on_lossless_changed(self, checked: bool):
        """Handle lossless checkbox change."""
        self.quality_widget.setVisible(not checked)
        self.quality_hint.setVisible(not checked)
        self._update_estimate()
    
    def _on_quality_changed(self, value: int):
        """Handle quality slider change."""
        self.quality_label.setText(f"{value}%")
        self._update_estimate()
    
    def _update_estimate(self):
        """Update estimated file size savings."""
        if self.lossless_check.isChecked():
            estimate = "Lossless: File sizes may be similar to or slightly larger than originals"
        else:
            quality = self.quality_slider.value()
            if quality >= 90:
                savings = "10-20%"
            elif quality >= 80:
                savings = "25-35%"
            elif quality >= 70:
                savings = "35-50%"
            else:
                savings = "50-70%"
            estimate = f"Estimated file size reduction: {savings}"
        
        if hasattr(self, 'estimate_label'):
            self.estimate_label.setText(f"📊 {estimate}")
    
    def _execute_convert(self):
        """Execute the batch conversion."""
        if not self.photos:
            return
        
        # Determine output folder
        first_photo_dir = self.photos[0].path.parent
        output_folder = first_photo_dir / "WebP"
        
        settings = {
            'quality': self.quality_slider.value(),
            'lossless': self.lossless_check.isChecked(),
        }
        
        # Start worker
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, len(self.photos))
        self.convert_btn.setEnabled(False)
        
        self.worker = ConvertWorker(self.photos, output_folder, settings)
        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self._on_finished)
        self.worker.start()
    
    def _on_progress(self, current: int, total: int):
        self.progress_bar.setValue(current)
    
    def _on_finished(self, success: int, failed: int, size_saved: int):
        self.progress_bar.setVisible(False)
        self.convert_btn.setEnabled(True)
        
        # Format size saved
        if size_saved > 1024 * 1024:
            saved_str = f"{size_saved / (1024 * 1024):.1f} MB"
        elif size_saved > 1024:
            saved_str = f"{size_saved / 1024:.1f} KB"
        else:
            saved_str = f"{size_saved} bytes"
        
        msg = f"✅ Converted {success} photos to WebP."
        if failed > 0:
            msg += f"\n❌ {failed} photos failed."
        if size_saved > 0:
            msg += f"\n\n💾 Space saved: {saved_str}"
        msg += f"\n\n📁 Saved to 'WebP/' subfolder"
        
        QMessageBox.information(self, "Conversion Complete", msg)
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
            QPushButton:hover { background-color: #4a4a4a; }
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
            QPushButton:hover { background-color: #5aacff; }
            QPushButton:disabled { background-color: #555; }
        """

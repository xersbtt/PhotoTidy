"""
Dialog for batch resizing photos.
"""
from pathlib import Path
from typing import List

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QRadioButton, QSlider, QSpinBox, QCheckBox,
    QProgressBar, QButtonGroup, QMessageBox
)
from PySide6.QtCore import Qt, QThread, Signal

from core.photo import Photo
from core.image_processing import resize_image


class ResizeWorker(QThread):
    """Worker thread for batch resize operations."""
    progress = Signal(int, int)
    finished = Signal(int, int)  # success_count, fail_count
    
    def __init__(self, photos: List[Photo], output_folder: Path, settings: dict):
        super().__init__()
        self.photos = photos
        self.output_folder = output_folder
        self.settings = settings
    
    def run(self):
        success = 0
        failed = 0
        total = len(self.photos)
        
        for i, photo in enumerate(self.photos):
            output_path = self.output_folder / photo.path.name
            
            result = resize_image(
                photo_path=photo.path,
                output_path=output_path,
                mode=self.settings['mode'],
                value=self.settings.get('value', 50),
                width=self.settings.get('width'),
                height=self.settings.get('height'),
                maintain_aspect=self.settings.get('maintain_aspect', True),
                quality=self.settings.get('quality', 85),
                preserve_exif=True
            )
            
            if result:
                success += 1
            else:
                failed += 1
            
            self.progress.emit(i + 1, total)
        
        self.finished.emit(success, failed)


class ResizeDialog(QDialog):
    """Dialog for batch resizing photos."""
    
    def __init__(self, photos: List[Photo], parent=None):
        super().__init__(parent)
        self.photos = photos
        self.worker = None
        
        self._setup_ui()
        self._update_preview()
    
    def _setup_ui(self):
        """Set up the dialog UI."""
        self.setWindowTitle("Resize Photos")
        self.setMinimumSize(500, 450)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        
        # Info label
        info_label = QLabel(f"📸 {len(self.photos)} photos selected")
        info_label.setStyleSheet("color: #4a9eff; font-size: 14px; font-weight: bold;")
        layout.addWidget(info_label)
        
        # Mode selection
        mode_group = QGroupBox("Resize Mode")
        mode_layout = QVBoxLayout(mode_group)
        
        self.mode_group = QButtonGroup(self)
        
        # Percentage mode
        pct_layout = QHBoxLayout()
        self.pct_radio = QRadioButton("By percentage:")
        self.pct_radio.setChecked(True)
        self.mode_group.addButton(self.pct_radio, 0)
        pct_layout.addWidget(self.pct_radio)
        
        self.pct_slider = QSlider(Qt.Orientation.Horizontal)
        self.pct_slider.setRange(10, 200)
        self.pct_slider.setValue(50)
        self.pct_slider.valueChanged.connect(self._update_preview)
        pct_layout.addWidget(self.pct_slider)
        
        self.pct_label = QLabel("50%")
        self.pct_label.setMinimumWidth(50)
        pct_layout.addWidget(self.pct_label)
        mode_layout.addLayout(pct_layout)
        
        # Max dimension mode
        max_layout = QHBoxLayout()
        self.max_radio = QRadioButton("Max dimension:")
        self.mode_group.addButton(self.max_radio, 1)
        max_layout.addWidget(self.max_radio)
        
        self.max_spin = QSpinBox()
        self.max_spin.setRange(100, 10000)
        self.max_spin.setValue(1920)
        self.max_spin.setSuffix(" px")
        self.max_spin.valueChanged.connect(self._update_preview)
        max_layout.addWidget(self.max_spin)
        max_layout.addStretch()
        mode_layout.addLayout(max_layout)
        
        # Exact size mode
        exact_layout = QHBoxLayout()
        self.exact_radio = QRadioButton("Exact size:")
        self.mode_group.addButton(self.exact_radio, 2)
        exact_layout.addWidget(self.exact_radio)
        
        self.width_spin = QSpinBox()
        self.width_spin.setRange(1, 10000)
        self.width_spin.setValue(1920)
        self.width_spin.setPrefix("W: ")
        self.width_spin.setSuffix(" px")
        self.width_spin.valueChanged.connect(self._update_preview)
        exact_layout.addWidget(self.width_spin)
        
        self.height_spin = QSpinBox()
        self.height_spin.setRange(1, 10000)
        self.height_spin.setValue(1080)
        self.height_spin.setPrefix("H: ")
        self.height_spin.setSuffix(" px")
        self.height_spin.valueChanged.connect(self._update_preview)
        exact_layout.addWidget(self.height_spin)
        
        self.aspect_check = QCheckBox("Maintain aspect ratio")
        self.aspect_check.setChecked(True)
        exact_layout.addWidget(self.aspect_check)
        mode_layout.addLayout(exact_layout)
        
        layout.addWidget(mode_group)
        
        # Connect radio buttons
        self.pct_radio.toggled.connect(self._update_preview)
        self.max_radio.toggled.connect(self._update_preview)
        self.exact_radio.toggled.connect(self._update_preview)
        
        # Quality slider
        quality_group = QGroupBox("Output Quality")
        quality_layout = QHBoxLayout(quality_group)
        
        self.quality_slider = QSlider(Qt.Orientation.Horizontal)
        self.quality_slider.setRange(1, 100)
        self.quality_slider.setValue(85)
        self.quality_slider.valueChanged.connect(self._on_quality_changed)
        quality_layout.addWidget(self.quality_slider)
        
        self.quality_label = QLabel("85%")
        self.quality_label.setMinimumWidth(40)
        quality_layout.addWidget(self.quality_label)
        
        layout.addWidget(quality_group)
        
        # Preview
        self.preview_label = QLabel()
        self.preview_label.setStyleSheet("""
            QLabel {
                background-color: #2d2d2d;
                border: 1px solid #444;
                border-radius: 6px;
                padding: 12px;
                color: #e0e0e0;
            }
        """)
        layout.addWidget(self.preview_label)
        
        # Output info
        output_info = QLabel("📁 Output: Will be saved to 'Resized/' subfolder")
        output_info.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(output_info)
        
        # Progress bar (hidden initially)
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
        
        self.resize_btn = QPushButton("📐 Resize Photos")
        self.resize_btn.setStyleSheet(self._action_button_style())
        self.resize_btn.clicked.connect(self._execute_resize)
        btn_layout.addWidget(self.resize_btn)
        
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
            QRadioButton, QCheckBox { color: #e0e0e0; }
            QSpinBox {
                background-color: #3a3a3a;
                border: 1px solid #555;
                border-radius: 4px;
                color: #e0e0e0;
                padding: 4px;
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
    
    def _on_quality_changed(self, value: int):
        self.quality_label.setText(f"{value}%")
    
    def _update_preview(self):
        """Update the preview label with estimated output dimensions."""
        self.pct_label.setText(f"{self.pct_slider.value()}%")
        
        if not self.photos:
            return
        
        # Get first photo dimensions
        photo = self.photos[0]
        if photo.width and photo.height:
            orig_w, orig_h = photo.width, photo.height
        else:
            orig_w, orig_h = 1920, 1080  # Default
        
        # Calculate new dimensions based on mode
        if self.pct_radio.isChecked():
            scale = self.pct_slider.value() / 100.0
            new_w = int(orig_w * scale)
            new_h = int(orig_h * scale)
        elif self.max_radio.isChecked():
            max_dim = self.max_spin.value()
            if orig_w >= orig_h:
                scale = max_dim / orig_w
            else:
                scale = max_dim / orig_h
            new_w = int(orig_w * scale)
            new_h = int(orig_h * scale)
        else:  # exact
            target_w = self.width_spin.value()
            target_h = self.height_spin.value()
            if self.aspect_check.isChecked():
                ratio = min(target_w / orig_w, target_h / orig_h)
                new_w = int(orig_w * ratio)
                new_h = int(orig_h * ratio)
            else:
                new_w = target_w
                new_h = target_h
        
        self.preview_label.setText(
            f"Sample: {photo.path.name}\n"
            f"Original: {orig_w} × {orig_h} px → New: {new_w} × {new_h} px"
        )
    
    def _execute_resize(self):
        """Execute the batch resize operation."""
        if not self.photos:
            return
        
        # Determine output folder
        first_photo_dir = self.photos[0].path.parent
        output_folder = first_photo_dir / "Resized"
        
        # Get settings
        settings = {
            'quality': self.quality_slider.value(),
            'maintain_aspect': self.aspect_check.isChecked(),
        }
        
        if self.pct_radio.isChecked():
            settings['mode'] = 'percentage'
            settings['value'] = self.pct_slider.value()
        elif self.max_radio.isChecked():
            settings['mode'] = 'max_dimension'
            settings['value'] = self.max_spin.value()
        else:
            settings['mode'] = 'exact'
            settings['width'] = self.width_spin.value()
            settings['height'] = self.height_spin.value()
        
        # Start worker
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, len(self.photos))
        self.resize_btn.setEnabled(False)
        
        self.worker = ResizeWorker(self.photos, output_folder, settings)
        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self._on_finished)
        self.worker.start()
    
    def _on_progress(self, current: int, total: int):
        self.progress_bar.setValue(current)
    
    def _on_finished(self, success: int, failed: int):
        self.progress_bar.setVisible(False)
        self.resize_btn.setEnabled(True)
        
        msg = f"✅ Resized {success} photos successfully."
        if failed > 0:
            msg += f"\n❌ {failed} photos failed."
        msg += f"\n\n📁 Saved to 'Resized/' subfolder"
        
        QMessageBox.information(self, "Resize Complete", msg)
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

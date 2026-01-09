"""
Dialog for adding watermarks to photos (text or image).
"""
from pathlib import Path
from typing import List, Optional

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QLineEdit, QSlider, QSpinBox, QComboBox,
    QTabWidget, QWidget, QGridLayout, QFileDialog,
    QProgressBar, QMessageBox, QColorDialog, QFrame
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QColor, QFont, QFontDatabase

from core.photo import Photo
from core.image_processing import (
    add_text_watermark, add_image_watermark,
    POSITION_TOP_LEFT, POSITION_TOP_CENTER, POSITION_TOP_RIGHT,
    POSITION_CENTER_LEFT, POSITION_CENTER, POSITION_CENTER_RIGHT,
    POSITION_BOTTOM_LEFT, POSITION_BOTTOM_CENTER, POSITION_BOTTOM_RIGHT
)


class WatermarkWorker(QThread):
    """Worker thread for batch watermark operations."""
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
            
            if self.settings['mode'] == 'text':
                result = add_text_watermark(
                    photo_path=photo.path,
                    output_path=output_path,
                    text=self.settings['text'],
                    font_name=self.settings.get('font_name'),
                    font_size=self.settings.get('font_size', 36),
                    color=self.settings.get('color', (255, 255, 255)),
                    opacity=self.settings.get('opacity', 128),
                    position=self.settings.get('position', POSITION_BOTTOM_RIGHT),
                    margin=self.settings.get('margin', 20),
                    quality=self.settings.get('quality', 85),
                    preserve_exif=True
                )
            else:  # image
                result = add_image_watermark(
                    photo_path=photo.path,
                    output_path=output_path,
                    watermark_path=Path(self.settings['watermark_path']),
                    opacity=self.settings.get('opacity', 128),
                    position=self.settings.get('position', POSITION_BOTTOM_RIGHT),
                    margin=self.settings.get('margin', 20),
                    scale=self.settings.get('scale', 0.2),
                    quality=self.settings.get('quality', 85),
                    preserve_exif=True
                )
            
            if result:
                success += 1
            else:
                failed += 1
            
            self.progress.emit(i + 1, total)
        
        self.finished.emit(success, failed)


class PositionSelector(QWidget):
    """3x3 grid for selecting watermark position."""
    position_changed = Signal(str)
    
    POSITIONS = [
        [POSITION_TOP_LEFT, POSITION_TOP_CENTER, POSITION_TOP_RIGHT],
        [POSITION_CENTER_LEFT, POSITION_CENTER, POSITION_CENTER_RIGHT],
        [POSITION_BOTTOM_LEFT, POSITION_BOTTOM_CENTER, POSITION_BOTTOM_RIGHT],
    ]
    
    LABELS = [
        ["↖", "↑", "↗"],
        ["←", "●", "→"],
        ["↙", "↓", "↘"],
    ]
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.buttons = {}
        self.current_position = POSITION_BOTTOM_RIGHT
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QGridLayout(self)
        layout.setSpacing(4)
        layout.setContentsMargins(0, 0, 0, 0)
        
        for row in range(3):
            for col in range(3):
                pos = self.POSITIONS[row][col]
                label = self.LABELS[row][col]
                
                btn = QPushButton(label)
                btn.setFixedSize(36, 36)
                btn.setCheckable(True)
                btn.clicked.connect(lambda checked, p=pos: self._on_position_clicked(p))
                
                self.buttons[pos] = btn
                layout.addWidget(btn, row, col)
        
        # Set default selection
        self.buttons[POSITION_BOTTOM_RIGHT].setChecked(True)
        self._update_styles()
    
    def _on_position_clicked(self, position: str):
        self.current_position = position
        self._update_styles()
        self.position_changed.emit(position)
    
    def _update_styles(self):
        for pos, btn in self.buttons.items():
            if pos == self.current_position:
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #4a9eff;
                        border: none;
                        border-radius: 4px;
                        color: white;
                        font-weight: bold;
                    }
                """)
                btn.setChecked(True)
            else:
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #3a3a3a;
                        border: 1px solid #555;
                        border-radius: 4px;
                        color: #e0e0e0;
                    }
                    QPushButton:hover {
                        background-color: #4a4a4a;
                    }
                """)
                btn.setChecked(False)
    
    def get_position(self) -> str:
        return self.current_position


class WatermarkDialog(QDialog):
    """Dialog for adding watermarks to photos."""
    
    def __init__(self, photos: List[Photo], parent=None):
        super().__init__(parent)
        self.photos = photos
        self.worker = None
        self.selected_color = (255, 255, 255)
        self.watermark_image_path: Optional[str] = None
        self._ui_ready = False  # Flag to prevent premature preview updates
        
        self._setup_ui()
        self._ui_ready = True  # UI is now ready
        self._update_preview()  # Initial preview
    
    def _setup_ui(self):
        """Set up the dialog UI."""
        self.setWindowTitle("Add Watermark")
        self.setMinimumSize(750, 600)
        
        layout = QHBoxLayout(self)
        layout.setSpacing(16)
        
        # Left side - settings
        settings_layout = QVBoxLayout()
        
        # Info label
        info_label = QLabel(f"📸 {len(self.photos)} photos selected")
        info_label.setStyleSheet("color: #4a9eff; font-size: 14px; font-weight: bold;")
        settings_layout.addWidget(info_label)
        
        # Tab widget for text vs image watermark
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #444;
                border-radius: 6px;
                background-color: #2d2d2d;
            }
            QTabBar::tab {
                background-color: #3a3a3a;
                color: #e0e0e0;
                padding: 8px 20px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
            }
            QTabBar::tab:selected {
                background-color: #4a9eff;
                color: white;
            }
        """)
        self.tab_widget.currentChanged.connect(self._update_preview)
        
        # Text watermark tab
        text_tab = QWidget()
        self._setup_text_tab(text_tab)
        self.tab_widget.addTab(text_tab, "📝 Text Watermark")
        
        # Image watermark tab
        image_tab = QWidget()
        self._setup_image_tab(image_tab)
        self.tab_widget.addTab(image_tab, "🖼️ Image Watermark")
        
        settings_layout.addWidget(self.tab_widget)
        
        layout.addLayout(settings_layout, stretch=1)
        
        # Common settings
        common_group = QGroupBox("Position && Options")
        common_layout = QHBoxLayout(common_group)
        
        # Position selector
        pos_layout = QVBoxLayout()
        pos_label = QLabel("Position:")
        pos_label.setStyleSheet("color: #e0e0e0;")
        pos_layout.addWidget(pos_label)
        
        self.position_selector = PositionSelector()
        self.position_selector.position_changed.connect(self._update_preview)
        pos_layout.addWidget(self.position_selector)
        pos_layout.addStretch()
        common_layout.addLayout(pos_layout)
        
        # Margin and opacity
        options_layout = QVBoxLayout()
        
        margin_layout = QHBoxLayout()
        margin_label = QLabel("Margin:")
        margin_label.setStyleSheet("color: #e0e0e0;")
        margin_layout.addWidget(margin_label)
        
        self.margin_spin = QSpinBox()
        self.margin_spin.setRange(0, 500)
        self.margin_spin.setValue(20)
        self.margin_spin.setSuffix(" px")
        self.margin_spin.valueChanged.connect(self._update_preview)
        margin_layout.addWidget(self.margin_spin)
        margin_layout.addStretch()
        options_layout.addLayout(margin_layout)
        
        opacity_layout = QHBoxLayout()
        opacity_label = QLabel("Opacity:")
        opacity_label.setStyleSheet("color: #e0e0e0;")
        opacity_layout.addWidget(opacity_label)
        
        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setRange(10, 100)
        self.opacity_slider.setValue(50)
        self.opacity_slider.valueChanged.connect(self._on_opacity_changed)
        opacity_layout.addWidget(self.opacity_slider)
        
        self.opacity_label = QLabel("50%")
        self.opacity_label.setMinimumWidth(40)
        self.opacity_label.setStyleSheet("color: #e0e0e0;")
        opacity_layout.addWidget(self.opacity_label)
        options_layout.addLayout(opacity_layout)
        
        quality_layout = QHBoxLayout()
        quality_label = QLabel("Quality:")
        quality_label.setStyleSheet("color: #e0e0e0;")
        quality_layout.addWidget(quality_label)
        
        self.quality_slider = QSlider(Qt.Orientation.Horizontal)
        self.quality_slider.setRange(1, 100)
        self.quality_slider.setValue(85)
        self.quality_slider.valueChanged.connect(self._on_quality_changed)
        quality_layout.addWidget(self.quality_slider)
        
        self.quality_label = QLabel("85%")
        self.quality_label.setMinimumWidth(40)
        self.quality_label.setStyleSheet("color: #e0e0e0;")
        quality_layout.addWidget(self.quality_label)
        options_layout.addLayout(quality_layout)
        
        options_layout.addStretch()
        common_layout.addLayout(options_layout)
        
        settings_layout.addWidget(common_group)
        
        # Output info
        output_info = QLabel("📁 Output: Will be saved to 'Watermarked/' subfolder")
        output_info.setStyleSheet("color: #888; font-size: 11px;")
        settings_layout.addWidget(output_info)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        settings_layout.addWidget(self.progress_bar)
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setStyleSheet(self._button_style())
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)
        
        self.apply_btn = QPushButton("💧 Add Watermark")
        self.apply_btn.setStyleSheet(self._action_button_style())
        self.apply_btn.clicked.connect(self._execute_watermark)
        btn_layout.addWidget(self.apply_btn)
        
        settings_layout.addLayout(btn_layout)
        
        # Right side - Preview panel
        preview_layout = QVBoxLayout()
        
        preview_label = QLabel("Preview")
        preview_label.setStyleSheet("color: #e0e0e0; font-weight: bold; font-size: 14px;")
        preview_layout.addWidget(preview_label)
        
        self.preview_image = QLabel()
        self.preview_image.setMinimumSize(300, 300)
        self.preview_image.setMaximumSize(400, 400)
        self.preview_image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_image.setStyleSheet("""
            QLabel {
                background-color: #1a1a1a;
                border: 1px solid #444;
                border-radius: 6px;
            }
        """)
        preview_layout.addWidget(self.preview_image, stretch=1)
        
        refresh_btn = QPushButton("🔄 Refresh Preview")
        refresh_btn.setStyleSheet(self._button_style())
        refresh_btn.clicked.connect(self._update_preview)
        preview_layout.addWidget(refresh_btn)
        
        layout.addLayout(preview_layout, stretch=1)
        
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
            QSpinBox, QComboBox {
                background-color: #3a3a3a;
                border: 1px solid #555;
                border-radius: 4px;
                color: #e0e0e0;
                padding: 4px;
            }
            QLineEdit {
                background-color: #3a3a3a;
                border: 1px solid #555;
                border-radius: 4px;
                color: #e0e0e0;
                padding: 8px;
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
    
    def _setup_text_tab(self, tab: QWidget):
        """Set up the text watermark tab."""
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(16, 16, 16, 16)
        
        # Text input
        text_layout = QHBoxLayout()
        text_label = QLabel("Text:")
        text_label.setStyleSheet("color: #e0e0e0;")
        text_layout.addWidget(text_label)
        
        self.text_input = QLineEdit()
        self.text_input.setPlaceholderText("Enter watermark text (e.g., © 2026 Your Name)")
        self.text_input.textChanged.connect(self._update_preview)
        text_layout.addWidget(self.text_input)
        layout.addLayout(text_layout)
        
        # Font selection
        font_layout = QHBoxLayout()
        font_label = QLabel("Font:")
        font_label.setStyleSheet("color: #e0e0e0;")
        font_layout.addWidget(font_label)
        
        self.font_combo = QComboBox()
        fonts = QFontDatabase.families()
        self.font_combo.addItems(fonts)
        # Try to select Arial or a common font
        for default_font in ['Arial', 'Segoe UI', 'Helvetica', 'Verdana']:
            idx = self.font_combo.findText(default_font)
            if idx >= 0:
                self.font_combo.setCurrentIndex(idx)
                break
        self.font_combo.currentTextChanged.connect(self._update_preview)
        font_layout.addWidget(self.font_combo)
        
        size_label = QLabel("Size:")
        size_label.setStyleSheet("color: #e0e0e0;")
        font_layout.addWidget(size_label)
        
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(8, 200)
        self.font_size_spin.setValue(48)
        self.font_size_spin.setSuffix(" px")
        self.font_size_spin.valueChanged.connect(self._update_preview)
        font_layout.addWidget(self.font_size_spin)
        
        layout.addLayout(font_layout)
        
        # Color picker
        color_layout = QHBoxLayout()
        color_label = QLabel("Color:")
        color_label.setStyleSheet("color: #e0e0e0;")
        color_layout.addWidget(color_label)
        
        self.color_btn = QPushButton()
        self.color_btn.setFixedSize(80, 30)
        self.color_btn.setStyleSheet("background-color: white; border: 1px solid #555; border-radius: 4px;")
        self.color_btn.clicked.connect(self._pick_color)
        color_layout.addWidget(self.color_btn)
        
        color_layout.addStretch()
        layout.addLayout(color_layout)
        
        layout.addStretch()
    
    def _setup_image_tab(self, tab: QWidget):
        """Set up the image watermark tab."""
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(16, 16, 16, 16)
        
        # File picker
        file_layout = QHBoxLayout()
        file_label = QLabel("Image:")
        file_label.setStyleSheet("color: #e0e0e0;")
        file_layout.addWidget(file_label)
        
        self.image_path_label = QLabel("No image selected")
        self.image_path_label.setStyleSheet("color: #888;")
        file_layout.addWidget(self.image_path_label, stretch=1)
        
        browse_btn = QPushButton("Browse...")
        browse_btn.setStyleSheet(self._button_style())
        browse_btn.clicked.connect(self._browse_watermark_image)
        file_layout.addWidget(browse_btn)
        
        layout.addLayout(file_layout)
        
        # Scale slider
        scale_layout = QHBoxLayout()
        scale_label = QLabel("Scale:")
        scale_label.setStyleSheet("color: #e0e0e0;")
        scale_layout.addWidget(scale_label)
        
        self.scale_slider = QSlider(Qt.Orientation.Horizontal)
        self.scale_slider.setRange(5, 50)
        self.scale_slider.setValue(20)
        self.scale_slider.valueChanged.connect(self._on_scale_changed)
        scale_layout.addWidget(self.scale_slider)
        
        self.scale_label = QLabel("20%")
        self.scale_label.setMinimumWidth(40)
        self.scale_label.setStyleSheet("color: #e0e0e0;")
        scale_layout.addWidget(self.scale_label)
        
        layout.addLayout(scale_layout)
        
        # Tip
        tip_label = QLabel("💡 Tip: Use PNG images with transparency for best results")
        tip_label.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(tip_label)
        
        layout.addStretch()
    
    def _pick_color(self):
        """Open color picker dialog."""
        color = QColorDialog.getColor(
            QColor(*self.selected_color),
            self,
            "Select Watermark Color"
        )
        if color.isValid():
            self.selected_color = (color.red(), color.green(), color.blue())
            self.color_btn.setStyleSheet(
                f"background-color: {color.name()}; border: 1px solid #555; border-radius: 4px;"
            )
    
    def _browse_watermark_image(self):
        """Browse for watermark image file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Watermark Image",
            "",
            "Images (*.png *.jpg *.jpeg *.gif *.bmp *.webp)"
        )
        if file_path:
            self.watermark_image_path = file_path
            self.image_path_label.setText(Path(file_path).name)
            self.image_path_label.setStyleSheet("color: #4aff4a;")
    
    def _on_opacity_changed(self, value: int):
        self.opacity_label.setText(f"{value}%")
        self._update_preview()
    
    def _on_quality_changed(self, value: int):
        self.quality_label.setText(f"{value}%")
    
    def _on_scale_changed(self, value: int):
        self.scale_label.setText(f"{value}%")
        self._update_preview()
    
    def _update_preview(self, *args):
        """Update the preview image with current watermark settings."""
        # Guard against calls during UI setup
        if not getattr(self, '_ui_ready', False):
            return
            
        if not self.photos:
            self.preview_image.setText("No photos to preview")
            return
        
        try:
            from PIL import Image, ImageDraw, ImageFont, ImageOps
            from PySide6.QtGui import QPixmap
            import io
            import matplotlib.font_manager as fm
            import os
            
            # Load first photo as preview (scaled down for speed)
            first_photo = self.photos[0]
            with Image.open(first_photo.path) as img:
                # Apply EXIF orientation
                img = ImageOps.exif_transpose(img)
                
                # Scale down for preview (max 350px)
                preview_size = 350
                ratio = min(preview_size / img.width, preview_size / img.height)
                new_size = (int(img.width * ratio), int(img.height * ratio))
                img = img.resize(new_size, Image.Resampling.LANCZOS)
                
                # Convert to RGBA
                if img.mode != 'RGBA':
                    img = img.convert('RGBA')
                
                # Apply watermark based on current settings
                is_text_mode = self.tab_widget.currentIndex() == 0
                opacity_value = int(self.opacity_slider.value() * 255 / 100)
                position = self.position_selector.get_position()
                margin = int(self.margin_spin.value() * ratio)  # Scale margin
                
                if is_text_mode:
                    text = self.text_input.text() or "Sample Watermark"
                    font_name = self.font_combo.currentText()
                    font_size = max(8, int(self.font_size_spin.value() * ratio))  # Scale font
                    color = self.selected_color
                    
                    # Create overlay
                    overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
                    draw = ImageDraw.Draw(overlay)
                    
                    # Load font using matplotlib
                    font = None
                    try:
                        font_props = fm.FontProperties(family=font_name)
                        font_path = fm.findfont(font_props, fallback_to_default=False)
                        if font_path:
                            font = ImageFont.truetype(font_path, font_size)
                    except Exception:
                        pass
                    
                    if font is None:
                        windows_fonts = os.path.join(os.environ.get('WINDIR', 'C:\\Windows'), 'Fonts')
                        try:
                            font = ImageFont.truetype(os.path.join(windows_fonts, 'arial.ttf'), font_size)
                        except Exception:
                            font = ImageFont.load_default()
                    
                    # Get text bbox and position
                    bbox = draw.textbbox((0, 0), text, font=font)
                    text_w, text_h = bbox[2] - bbox[0], bbox[3] - bbox[1]
                    x, y = self._calculate_preview_position(img.size, (text_w, text_h), position, margin)
                    
                    # Draw text
                    draw.text((x, y), text, font=font, fill=(*color, opacity_value))
                    
                    # Composite
                    img = Image.alpha_composite(img, overlay)
                
                elif self.watermark_image_path:
                    # Image watermark preview
                    try:
                        wm = Image.open(self.watermark_image_path)
                        if wm.mode != 'RGBA':
                            wm = wm.convert('RGBA')
                        
                        # Scale watermark
                        scale = self.scale_slider.value() / 100.0
                        wm_w = int(img.width * scale)
                        wm_h = int(wm.height * (wm_w / wm.width))
                        wm = wm.resize((wm_w, wm_h), Image.Resampling.LANCZOS)
                        
                        # Apply opacity
                        if opacity_value < 255:
                            r, g, b, a = wm.split()
                            a = a.point(lambda x: int(x * opacity_value / 255))
                            wm = Image.merge('RGBA', (r, g, b, a))
                        
                        x, y = self._calculate_preview_position(img.size, wm.size, position, margin)
                        img.paste(wm, (x, y), wm)
                    except Exception:
                        pass  # Skip image watermark preview if it fails
                
                # Convert to RGB and then to QPixmap
                img = img.convert('RGB')
                buffer = io.BytesIO()
                img.save(buffer, format='PNG')
                buffer.seek(0)
                
                pixmap = QPixmap()
                pixmap.loadFromData(buffer.read())
                self.preview_image.setPixmap(pixmap)
                
        except Exception as e:
            self.preview_image.setText(f"Preview error: {str(e)[:50]}")
    
    def _calculate_preview_position(self, img_size, wm_size, position, margin):
        """Calculate watermark position for preview."""
        img_w, img_h = img_size
        wm_w, wm_h = wm_size
        
        pos_map = {
            'top_left': (margin, margin),
            'top_center': ((img_w - wm_w) // 2, margin),
            'top_right': (img_w - wm_w - margin, margin),
            'center_left': (margin, (img_h - wm_h) // 2),
            'center': ((img_w - wm_w) // 2, (img_h - wm_h) // 2),
            'center_right': (img_w - wm_w - margin, (img_h - wm_h) // 2),
            'bottom_left': (margin, img_h - wm_h - margin),
            'bottom_center': ((img_w - wm_w) // 2, img_h - wm_h - margin),
            'bottom_right': (img_w - wm_w - margin, img_h - wm_h - margin),
        }
        return pos_map.get(position, pos_map['bottom_right'])
    
    def _execute_watermark(self):
        """Execute the batch watermark operation."""
        if not self.photos:
            return
        
        # Validate inputs
        is_text_mode = self.tab_widget.currentIndex() == 0
        
        if is_text_mode:
            if not self.text_input.text().strip():
                QMessageBox.warning(self, "Missing Text", "Please enter watermark text.")
                return
        else:
            if not self.watermark_image_path:
                QMessageBox.warning(self, "Missing Image", "Please select a watermark image.")
                return
        
        # Determine output folder
        first_photo_dir = self.photos[0].path.parent
        output_folder = first_photo_dir / "Watermarked"
        
        # Build settings
        opacity_value = int(self.opacity_slider.value() * 255 / 100)
        
        settings = {
            'mode': 'text' if is_text_mode else 'image',
            'position': self.position_selector.get_position(),
            'margin': self.margin_spin.value(),
            'opacity': opacity_value,
            'quality': self.quality_slider.value(),
        }
        
        if is_text_mode:
            settings['text'] = self.text_input.text()
            settings['font_name'] = self.font_combo.currentText()
            settings['font_size'] = self.font_size_spin.value()
            settings['color'] = self.selected_color
        else:
            settings['watermark_path'] = self.watermark_image_path
            settings['scale'] = self.scale_slider.value() / 100.0
        
        # Start worker
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, len(self.photos))
        self.apply_btn.setEnabled(False)
        
        self.worker = WatermarkWorker(self.photos, output_folder, settings)
        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self._on_finished)
        self.worker.start()
    
    def _on_progress(self, current: int, total: int):
        self.progress_bar.setValue(current)
    
    def _on_finished(self, success: int, failed: int):
        self.progress_bar.setVisible(False)
        self.apply_btn.setEnabled(True)
        
        msg = f"✅ Added watermark to {success} photos."
        if failed > 0:
            msg += f"\n❌ {failed} photos failed."
        msg += f"\n\n📁 Saved to 'Watermarked/' subfolder"
        
        QMessageBox.information(self, "Watermark Complete", msg)
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

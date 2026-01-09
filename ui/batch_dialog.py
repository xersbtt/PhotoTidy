"""
Batch processing dialog for chaining multiple image operations.
"""
from pathlib import Path
from typing import List, Optional, Dict, Any
import io

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QStackedWidget, QWidget,
    QGroupBox, QLineEdit, QSlider, QSpinBox, QComboBox,
    QProgressBar, QMessageBox, QFileDialog, QColorDialog,
    QRadioButton, QButtonGroup, QCheckBox, QFrame
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QColor, QPixmap, QFontDatabase

from PIL import Image, ImageOps

from core.photo import Photo
from core.batch_pipeline import (
    BatchPipeline, PipelineStep, StepConfig, StepType,
    create_step, ResizeStep, RotateStep, RenameStep,
    TextWatermarkStep, ImageWatermarkStep, WebPConvertStep
)


class BatchWorker(QThread):
    """Worker thread for batch processing."""
    progress = Signal(int, int, str)  # current, total, filename
    finished = Signal(int, int)  # success, failed
    
    def __init__(self, photos: List[Photo], pipeline: BatchPipeline, output_folder: Path):
        super().__init__()
        self.photos = photos
        self.pipeline = pipeline
        self.output_folder = output_folder
    
    def run(self):
        success = 0
        failed = 0
        total = len(self.photos)
        
        self.output_folder.mkdir(parents=True, exist_ok=True)
        
        for i, photo in enumerate(self.photos):
            try:
                self.progress.emit(i + 1, total, photo.filename)
                
                # Load image with EXIF orientation
                with Image.open(photo.path) as img:
                    img = ImageOps.exif_transpose(img)
                    if img.mode not in ('RGB', 'RGBA'):
                        img = img.convert('RGB')
                    
                    # Execute pipeline
                    processed, context = self.pipeline.execute_on_image(
                        img.copy(),
                        photo.path,
                        sequence_num=i + 1,
                        photo_date=photo.date_taken
                    )
                    
                    # Determine output format and name
                    output_format = context.get('output_format', 'jpg')
                    output_name = context.get('output_name', photo.path.stem)
                    
                    if output_format == 'webp':
                        output_path = self.output_folder / f"{output_name}.webp"
                        if processed.mode == 'RGBA':
                            processed = processed.convert('RGB')
                        processed.save(
                            output_path, 'WEBP',
                            quality=context.get('quality', 85),
                            lossless=context.get('lossless', False)
                        )
                    else:
                        ext = photo.path.suffix
                        output_path = self.output_folder / f"{output_name}{ext}"
                        if processed.mode == 'RGBA':
                            processed = processed.convert('RGB')
                        processed.save(output_path, quality=context.get('quality', 85))
                    
                    success += 1
                    
            except Exception as e:
                failed += 1
                print(f"Failed to process {photo.filename}: {e}")
        
        self.finished.emit(success, failed)


class StepListItem(QListWidgetItem):
    """List item representing a pipeline step."""
    
    def __init__(self, step: PipelineStep, index: int):
        super().__init__()
        self.step = step
        self.index = index
        self.update_text()
    
    def update_text(self):
        self.setText(f"{self.index + 1}. {self.step.icon} {self.step.name}: {self.step.get_description()}")


class BatchDialog(QDialog):
    """Dialog for batch processing with pipeline steps."""
    
    def __init__(self, photos: List[Photo], parent=None):
        super().__init__(parent)
        self.photos = photos
        self.pipeline = BatchPipeline()
        self.worker = None
        self.step_widgets: Dict[int, QWidget] = {}
        
        self._setup_ui()
    
    def _setup_ui(self):
        self.setWindowTitle("Batch Process")
        self.setMinimumSize(900, 650)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        
        # Header
        header = QLabel(f"⚡ Batch Process - {len(self.photos)} photos selected")
        header.setStyleSheet("color: #4a9eff; font-size: 16px; font-weight: bold;")
        layout.addWidget(header)
        
        # Main content area
        content = QHBoxLayout()
        content.setSpacing(12)
        
        # Left - Add steps panel
        add_panel = QGroupBox("Add Step")
        add_panel.setMaximumWidth(150)
        add_layout = QVBoxLayout(add_panel)
        
        step_buttons = [
            ("📐 Resize", StepType.RESIZE),
            ("🔄 Rotate", StepType.ROTATE),
            ("✏️ Rename", StepType.RENAME),
            ("💧 Text WM", StepType.TEXT_WATERMARK),
            ("🖼️ Image WM", StepType.IMAGE_WATERMARK),
            ("🌐 WebP", StepType.WEBP_CONVERT),
        ]
        
        for label, step_type in step_buttons:
            btn = QPushButton(label)
            btn.setStyleSheet(self._step_button_style())
            btn.clicked.connect(lambda checked, st=step_type: self._add_step(st))
            add_layout.addWidget(btn)
        
        add_layout.addStretch()
        content.addWidget(add_panel)
        
        # Center - Pipeline steps list
        pipeline_panel = QGroupBox("Pipeline Steps")
        pipeline_layout = QVBoxLayout(pipeline_panel)
        
        self.steps_list = QListWidget()
        self.steps_list.setStyleSheet("""
            QListWidget {
                background-color: #2a2a2a;
                border: 1px solid #444;
                border-radius: 4px;
                color: #e0e0e0;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #3a3a3a;
            }
            QListWidget::item:selected {
                background-color: #4a9eff;
            }
        """)
        self.steps_list.currentRowChanged.connect(self._on_step_selected)
        pipeline_layout.addWidget(self.steps_list)
        
        # Reorder buttons
        btn_row = QHBoxLayout()
        
        up_btn = QPushButton("↑ Up")
        up_btn.setStyleSheet(self._small_button_style())
        up_btn.clicked.connect(self._move_step_up)
        btn_row.addWidget(up_btn)
        
        down_btn = QPushButton("↓ Down")
        down_btn.setStyleSheet(self._small_button_style())
        down_btn.clicked.connect(self._move_step_down)
        btn_row.addWidget(down_btn)
        
        remove_btn = QPushButton("❌ Remove")
        remove_btn.setStyleSheet(self._small_button_style())
        remove_btn.clicked.connect(self._remove_step)
        btn_row.addWidget(remove_btn)
        
        pipeline_layout.addLayout(btn_row)
        content.addWidget(pipeline_panel)
        
        # Right - Configuration + Preview
        config_panel = QGroupBox("Configure & Preview")
        config_layout = QVBoxLayout(config_panel)
        
        # Stacked widget for step configuration
        self.config_stack = QStackedWidget()
        
        # Empty placeholder
        empty_label = QLabel("Select a step to configure")
        empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_label.setStyleSheet("color: #888;")
        self.config_stack.addWidget(empty_label)
        
        config_layout.addWidget(self.config_stack)
        
        # Preview
        preview_label = QLabel("Preview:")
        preview_label.setStyleSheet("color: #e0e0e0; font-weight: bold;")
        config_layout.addWidget(preview_label)
        
        self.preview_image = QLabel()
        self.preview_image.setMinimumSize(250, 200)
        self.preview_image.setMaximumSize(350, 280)
        self.preview_image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_image.setStyleSheet("""
            QLabel {
                background-color: #1a1a1a;
                border: 1px solid #444;
                border-radius: 6px;
            }
        """)
        config_layout.addWidget(self.preview_image)
        
        refresh_btn = QPushButton("🔄 Refresh Preview")
        refresh_btn.setStyleSheet(self._small_button_style())
        refresh_btn.clicked.connect(self._update_preview)
        config_layout.addWidget(refresh_btn)
        
        content.addWidget(config_panel, stretch=1)
        
        layout.addLayout(content, stretch=1)
        
        # Output info
        output_label = QLabel("📁 Output: Batch Processed/")
        output_label.setStyleSheet("color: #888;")
        layout.addWidget(output_label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        self.status_label = QLabel()
        self.status_label.setStyleSheet("color: #888;")
        self.status_label.setVisible(False)
        layout.addWidget(self.status_label)
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet(self._button_style())
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        self.process_btn = QPushButton("⚡ Process All")
        self.process_btn.setStyleSheet(self._action_button_style())
        self.process_btn.clicked.connect(self._execute_pipeline)
        btn_layout.addWidget(self.process_btn)
        
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
        """)
    
    def _add_step(self, step_type: StepType):
        """Add a new step to the pipeline."""
        # Create step with default settings
        default_settings = self._get_default_settings(step_type)
        step = create_step(step_type, default_settings)
        self.pipeline.add_step(step)
        
        # Add to list
        item = StepListItem(step, len(self.pipeline.steps) - 1)
        self.steps_list.addItem(item)
        
        # Create config widget
        config_widget = self._create_config_widget(step, len(self.pipeline.steps) - 1)
        self.config_stack.addWidget(config_widget)
        self.step_widgets[len(self.pipeline.steps) - 1] = config_widget
        
        # Select new step
        self.steps_list.setCurrentRow(len(self.pipeline.steps) - 1)
        
        self._update_preview()
    
    def _get_default_settings(self, step_type: StepType) -> Dict[str, Any]:
        """Get default settings for a step type."""
        defaults = {
            StepType.RESIZE: {'mode': 'percentage', 'value': 50, 'maintain_aspect': True},
            StepType.ROTATE: {'angle': 90},
            StepType.RENAME: {'pattern': '{original}_{NNN}'},
            StepType.TEXT_WATERMARK: {
                'text': '© 2026', 'font_name': 'Arial', 'font_size': 48,
                'color': (255, 255, 255), 'opacity': 128, 'position': 'bottom_right', 'margin': 20
            },
            StepType.IMAGE_WATERMARK: {
                'watermark_path': '', 'opacity': 128, 'position': 'bottom_right',
                'margin': 20, 'scale': 0.2
            },
            StepType.WEBP_CONVERT: {'quality': 85, 'lossless': False},
        }
        return defaults.get(step_type, {})
    
    def _create_config_widget(self, step: PipelineStep, index: int) -> QWidget:
        """Create configuration widget for a step."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8, 8, 8, 8)
        
        title = QLabel(f"{step.icon} {step.name} Settings")
        title.setStyleSheet("color: #4a9eff; font-weight: bold; font-size: 14px;")
        layout.addWidget(title)
        
        if step.step_type == StepType.RESIZE:
            self._add_resize_config(layout, step, index)
        elif step.step_type == StepType.ROTATE:
            self._add_rotate_config(layout, step, index)
        elif step.step_type == StepType.RENAME:
            self._add_rename_config(layout, step, index)
        elif step.step_type == StepType.TEXT_WATERMARK:
            self._add_text_watermark_config(layout, step, index)
        elif step.step_type == StepType.IMAGE_WATERMARK:
            self._add_image_watermark_config(layout, step, index)
        elif step.step_type == StepType.WEBP_CONVERT:
            self._add_webp_config(layout, step, index)
        
        layout.addStretch()
        return widget
    
    def _add_resize_config(self, layout: QVBoxLayout, step: PipelineStep, index: int):
        """Add resize configuration controls."""
        # Mode selection
        mode_group = QButtonGroup(self)
        
        pct_radio = QRadioButton("Percentage")
        pct_radio.setStyleSheet("color: #e0e0e0;")
        pct_radio.setChecked(step.config.get('mode') == 'percentage')
        mode_group.addButton(pct_radio, 0)
        layout.addWidget(pct_radio)
        
        pct_slider = QSlider(Qt.Orientation.Horizontal)
        pct_slider.setRange(10, 100)
        pct_slider.setValue(step.config.get('value', 50))
        pct_label = QLabel(f"{pct_slider.value()}%")
        pct_label.setStyleSheet("color: #e0e0e0;")
        
        def on_pct_change(v):
            pct_label.setText(f"{v}%")
            step.config.settings['value'] = v
            step.config.settings['mode'] = 'percentage'
            pct_radio.setChecked(True)
            self._update_step_text(index)
        
        pct_slider.valueChanged.connect(on_pct_change)
        
        pct_row = QHBoxLayout()
        pct_row.addWidget(pct_slider)
        pct_row.addWidget(pct_label)
        layout.addLayout(pct_row)
        
        max_radio = QRadioButton("Max dimension (px)")
        max_radio.setStyleSheet("color: #e0e0e0;")
        max_radio.setChecked(step.config.get('mode') == 'max_dimension')
        mode_group.addButton(max_radio, 1)
        layout.addWidget(max_radio)
        
        max_spin = QSpinBox()
        max_spin.setRange(100, 10000)
        max_spin.setValue(step.config.get('value', 1920) if step.config.get('mode') == 'max_dimension' else 1920)
        max_spin.setSuffix(" px")
        
        def on_max_change(v):
            step.config.settings['value'] = v
            step.config.settings['mode'] = 'max_dimension'
            max_radio.setChecked(True)
            self._update_step_text(index)
        
        max_spin.valueChanged.connect(on_max_change)
        layout.addWidget(max_spin)
    
    def _add_rotate_config(self, layout: QVBoxLayout, step: PipelineStep, index: int):
        """Add rotate configuration controls."""
        angle_group = QButtonGroup(self)
        
        for angle in [90, 180, 270]:
            radio = QRadioButton(f"{angle}° clockwise")
            radio.setStyleSheet("color: #e0e0e0;")
            radio.setChecked(step.config.get('angle') == angle)
            
            def on_angle_change(checked, a=angle):
                if checked:
                    step.config.settings['angle'] = a
                    self._update_step_text(index)
            
            radio.toggled.connect(on_angle_change)
            angle_group.addButton(radio)
            layout.addWidget(radio)
    
    def _add_rename_config(self, layout: QVBoxLayout, step: PipelineStep, index: int):
        """Add rename configuration controls."""
        pattern_label = QLabel("Pattern:")
        pattern_label.setStyleSheet("color: #e0e0e0;")
        layout.addWidget(pattern_label)
        
        pattern_input = QLineEdit(step.config.get('pattern', '{original}_{NNN}'))
        pattern_input.setStyleSheet("background: #3a3a3a; color: #e0e0e0; border: 1px solid #555; padding: 6px;")
        
        def on_pattern_change(text):
            step.config.settings['pattern'] = text
            self._update_step_text(index)
        
        pattern_input.textChanged.connect(on_pattern_change)
        layout.addWidget(pattern_input)
        
        tokens_label = QLabel(
            "Tokens: {original}, {YYMMDD}, {YYYY}, {MM}, {DD}, {NNN}, {NN}, {N}"
        )
        tokens_label.setStyleSheet("color: #888; font-size: 10px;")
        tokens_label.setWordWrap(True)
        layout.addWidget(tokens_label)
    
    def _add_text_watermark_config(self, layout: QVBoxLayout, step: PipelineStep, index: int):
        """Add text watermark configuration controls."""
        # Text
        text_row = QHBoxLayout()
        text_label = QLabel("Text:")
        text_label.setStyleSheet("color: #e0e0e0;")
        text_row.addWidget(text_label)
        
        text_input = QLineEdit(step.config.get('text', '© 2026'))
        text_input.setStyleSheet("background: #3a3a3a; color: #e0e0e0; border: 1px solid #555; padding: 4px;")
        
        def on_text_change(t):
            step.config.settings['text'] = t
            self._update_step_text(index)
            self._update_preview()
        
        text_input.textChanged.connect(on_text_change)
        text_row.addWidget(text_input)
        layout.addLayout(text_row)
        
        # Font selection
        font_row = QHBoxLayout()
        font_label = QLabel("Font:")
        font_label.setStyleSheet("color: #e0e0e0;")
        font_row.addWidget(font_label)
        
        font_combo = QComboBox()
        fonts = QFontDatabase.families()
        font_combo.addItems(fonts)
        # Select current font
        current_font = step.config.get('font_name', 'Arial')
        idx = font_combo.findText(current_font)
        if idx >= 0:
            font_combo.setCurrentIndex(idx)
        
        def on_font_change(font_name):
            step.config.settings['font_name'] = font_name
            self._update_preview()
        
        font_combo.currentTextChanged.connect(on_font_change)
        font_row.addWidget(font_combo)
        layout.addLayout(font_row)
        
        # Font size
        size_row = QHBoxLayout()
        size_label = QLabel("Size:")
        size_label.setStyleSheet("color: #e0e0e0;")
        size_row.addWidget(size_label)
        
        size_spin = QSpinBox()
        size_spin.setRange(8, 200)
        size_spin.setValue(step.config.get('font_size', 48))
        size_spin.setSuffix(" px")
        
        def on_size_change(v):
            step.config.settings['font_size'] = v
            self._update_preview()
        
        size_spin.valueChanged.connect(on_size_change)
        size_row.addWidget(size_spin)
        size_row.addStretch()
        layout.addLayout(size_row)
        
        # Color picker
        color_row = QHBoxLayout()
        color_label = QLabel("Color:")
        color_label.setStyleSheet("color: #e0e0e0;")
        color_row.addWidget(color_label)
        
        current_color = step.config.get('color', (255, 255, 255))
        color_btn = QPushButton()
        color_btn.setFixedSize(40, 24)
        color_btn.setStyleSheet(
            f"background-color: rgb({current_color[0]}, {current_color[1]}, {current_color[2]}); "
            f"border: 1px solid #555; border-radius: 4px;"
        )
        
        def pick_color():
            color = QColorDialog.getColor(
                QColor(*current_color),
                self,
                "Select Watermark Color"
            )
            if color.isValid():
                new_color = (color.red(), color.green(), color.blue())
                step.config.settings['color'] = new_color
                color_btn.setStyleSheet(
                    f"background-color: {color.name()}; border: 1px solid #555; border-radius: 4px;"
                )
                self._update_preview()
        
        color_btn.clicked.connect(pick_color)
        color_row.addWidget(color_btn)
        color_row.addStretch()
        layout.addLayout(color_row)
        
        # Position (simple dropdown for now)
        pos_row = QHBoxLayout()
        pos_label = QLabel("Position:")
        pos_label.setStyleSheet("color: #e0e0e0;")
        pos_row.addWidget(pos_label)
        
        pos_combo = QComboBox()
        positions = [
            ('Top Left', 'top_left'),
            ('Top Center', 'top_center'),
            ('Top Right', 'top_right'),
            ('Center Left', 'center_left'),
            ('Center', 'center'),
            ('Center Right', 'center_right'),
            ('Bottom Left', 'bottom_left'),
            ('Bottom Center', 'bottom_center'),
            ('Bottom Right', 'bottom_right'),
        ]
        for label, value in positions:
            pos_combo.addItem(label, value)
        
        # Select current position
        current_pos = step.config.get('position', 'bottom_right')
        for i, (_, value) in enumerate(positions):
            if value == current_pos:
                pos_combo.setCurrentIndex(i)
                break
        
        def on_pos_change(idx):
            step.config.settings['position'] = pos_combo.itemData(idx)
            self._update_preview()
        
        pos_combo.currentIndexChanged.connect(on_pos_change)
        pos_row.addWidget(pos_combo)
        layout.addLayout(pos_row)
        
        # Margin
        margin_row = QHBoxLayout()
        margin_label = QLabel("Margin:")
        margin_label.setStyleSheet("color: #e0e0e0;")
        margin_row.addWidget(margin_label)
        
        margin_spin = QSpinBox()
        margin_spin.setRange(0, 500)
        margin_spin.setValue(step.config.get('margin', 20))
        margin_spin.setSuffix(" px")
        
        def on_margin_change(v):
            step.config.settings['margin'] = v
            self._update_preview()
        
        margin_spin.valueChanged.connect(on_margin_change)
        margin_row.addWidget(margin_spin)
        margin_row.addStretch()
        layout.addLayout(margin_row)
        
        # Opacity
        opacity_row = QHBoxLayout()
        opacity_label = QLabel("Opacity:")
        opacity_label.setStyleSheet("color: #e0e0e0;")
        opacity_row.addWidget(opacity_label)
        
        opacity_slider = QSlider(Qt.Orientation.Horizontal)
        opacity_slider.setRange(10, 100)
        opacity_slider.setValue(int(step.config.get('opacity', 128) * 100 / 255))
        opacity_value_label = QLabel(f"{opacity_slider.value()}%")
        opacity_value_label.setStyleSheet("color: #e0e0e0;")
        
        def on_opacity_change(v):
            step.config.settings['opacity'] = int(v * 255 / 100)
            opacity_value_label.setText(f"{v}%")
            self._update_preview()
        
        opacity_slider.valueChanged.connect(on_opacity_change)
        opacity_row.addWidget(opacity_slider)
        opacity_row.addWidget(opacity_value_label)
        layout.addLayout(opacity_row)
    
    def _add_image_watermark_config(self, layout: QVBoxLayout, step: PipelineStep, index: int):
        """Add image watermark configuration controls."""
        path_label = QLabel("Watermark image:")
        path_label.setStyleSheet("color: #e0e0e0;")
        layout.addWidget(path_label)
        
        path_row = QHBoxLayout()
        self.wm_path_label = QLabel(Path(step.config.get('watermark_path', '')).name or "None selected")
        self.wm_path_label.setStyleSheet("color: #888;")
        path_row.addWidget(self.wm_path_label)
        
        browse_btn = QPushButton("Browse...")
        browse_btn.setStyleSheet(self._small_button_style())
        
        def browse():
            path, _ = QFileDialog.getOpenFileName(self, "Select Watermark", "", "Images (*.png *.jpg *.jpeg)")
            if path:
                step.config.settings['watermark_path'] = path
                self.wm_path_label.setText(Path(path).name)
                self._update_step_text(index)
        
        browse_btn.clicked.connect(browse)
        path_row.addWidget(browse_btn)
        layout.addLayout(path_row)
        
        # Scale
        scale_row = QHBoxLayout()
        scale_row.addWidget(QLabel("Scale:"))
        scale_slider = QSlider(Qt.Orientation.Horizontal)
        scale_slider.setRange(5, 50)
        scale_slider.setValue(int(step.config.get('scale', 0.2) * 100))
        scale_label = QLabel(f"{scale_slider.value()}%")
        scale_slider.valueChanged.connect(lambda v: (
            step.config.settings.update({'scale': v / 100}),
            scale_label.setText(f"{v}%")
        ))
        scale_row.addWidget(scale_slider)
        scale_row.addWidget(scale_label)
        layout.addLayout(scale_row)
    
    def _add_webp_config(self, layout: QVBoxLayout, step: PipelineStep, index: int):
        """Add WebP conversion configuration controls."""
        lossless_check = QCheckBox("Lossless compression")
        lossless_check.setStyleSheet("color: #e0e0e0;")
        lossless_check.setChecked(step.config.get('lossless', False))
        lossless_check.toggled.connect(lambda c: (
            step.config.settings.update({'lossless': c}),
            self._update_step_text(index)
        ))
        layout.addWidget(lossless_check)
        
        quality_row = QHBoxLayout()
        quality_row.addWidget(QLabel("Quality:"))
        quality_slider = QSlider(Qt.Orientation.Horizontal)
        quality_slider.setRange(1, 100)
        quality_slider.setValue(step.config.get('quality', 85))
        quality_label = QLabel(f"{quality_slider.value()}%")
        quality_slider.valueChanged.connect(lambda v: (
            step.config.settings.update({'quality': v}),
            quality_label.setText(f"{v}%"),
            self._update_step_text(index)
        ))
        quality_row.addWidget(quality_slider)
        quality_row.addWidget(quality_label)
        layout.addLayout(quality_row)
    
    def _on_step_selected(self, row: int):
        """Handle step selection."""
        if row >= 0 and row in self.step_widgets:
            # Find the widget in stack
            widget = self.step_widgets[row]
            idx = self.config_stack.indexOf(widget)
            if idx >= 0:
                self.config_stack.setCurrentIndex(idx)
        else:
            self.config_stack.setCurrentIndex(0)
    
    def _update_step_text(self, index: int):
        """Update the display text for a step."""
        if index < self.steps_list.count():
            item = self.steps_list.item(index)
            if isinstance(item, StepListItem):
                item.update_text()
    
    def _move_step_up(self):
        """Move selected step up."""
        row = self.steps_list.currentRow()
        if row > 0:
            self.pipeline.move_step(row, row - 1)
            self._refresh_steps_list()
            self.steps_list.setCurrentRow(row - 1)
    
    def _move_step_down(self):
        """Move selected step down."""
        row = self.steps_list.currentRow()
        if row >= 0 and row < len(self.pipeline.steps) - 1:
            self.pipeline.move_step(row, row + 1)
            self._refresh_steps_list()
            self.steps_list.setCurrentRow(row + 1)
    
    def _remove_step(self):
        """Remove selected step."""
        row = self.steps_list.currentRow()
        if row >= 0:
            self.pipeline.remove_step(row)
            self._refresh_steps_list()
            self._update_preview()
    
    def _refresh_steps_list(self):
        """Refresh the steps list display."""
        current = self.steps_list.currentRow()
        self.steps_list.clear()
        self.step_widgets.clear()
        
        # Remove all but first widget from stack
        while self.config_stack.count() > 1:
            w = self.config_stack.widget(1)
            self.config_stack.removeWidget(w)
            w.deleteLater()
        
        for i, step in enumerate(self.pipeline.steps):
            item = StepListItem(step, i)
            self.steps_list.addItem(item)
            config_widget = self._create_config_widget(step, i)
            self.config_stack.addWidget(config_widget)
            self.step_widgets[i] = config_widget
        
        if current >= 0 and current < len(self.pipeline.steps):
            self.steps_list.setCurrentRow(current)
    
    
    def _update_preview(self):
        """Update preview with rotation and watermark steps only (resize/webp not visible)."""
        if not self.photos or not self.pipeline.steps:
            self.preview_image.setText("Add steps to preview")
            return
        
        try:
            from core.batch_pipeline import StepType
            
            first_photo = self.photos[0]
            with Image.open(first_photo.path) as img:
                img = ImageOps.exif_transpose(img)
                
                if img.mode not in ('RGB', 'RGBA'):
                    img = img.convert('RGB')
                
                # Execute ONLY rotation and watermark steps at full resolution
                # (resize and WebP aren't visually meaningful in preview)
                context = {
                    'original_path': first_photo.path,
                    'output_name': first_photo.path.stem,
                    'sequence_num': 1,
                    'date': first_photo.date_taken,
                    'output_format': first_photo.path.suffix.lower().lstrip('.'),
                    'quality': 85,
                }
                
                for step in self.pipeline.steps:
                    # Only apply rotation and watermark for preview
                    if step.step_type in (StepType.ROTATE, StepType.TEXT_WATERMARK, StepType.IMAGE_WATERMARK):
                        img, context = step.execute(img, context)
                
                # NOW scale for preview display
                preview_size = 300
                ratio = min(preview_size / img.width, preview_size / img.height)
                new_size = (int(img.width * ratio), int(img.height * ratio))
                img = img.resize(new_size, Image.Resampling.LANCZOS)
                
                # Convert to QPixmap
                if img.mode == 'RGBA':
                    img = img.convert('RGB')
                
                buffer = io.BytesIO()
                img.save(buffer, format='PNG')
                buffer.seek(0)
                
                pixmap = QPixmap()
                pixmap.loadFromData(buffer.read())
                self.preview_image.setPixmap(pixmap)
                
        except Exception as e:
            self.preview_image.setText(f"Preview error")
    
    
    def _execute_pipeline(self):
        """Execute the pipeline on all photos."""
        if not self.photos:
            return
        
        if not self.pipeline.steps:
            QMessageBox.warning(self, "No Steps", "Please add at least one processing step.")
            return
        
        # Determine output folder
        first_photo_dir = self.photos[0].path.parent
        output_folder = first_photo_dir / "Batch Processed"
        
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, len(self.photos))
        self.status_label.setVisible(True)
        self.process_btn.setEnabled(False)
        
        self.worker = BatchWorker(self.photos, self.pipeline, output_folder)
        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self._on_finished)
        self.worker.start()
    
    def _on_progress(self, current: int, total: int, filename: str):
        self.progress_bar.setValue(current)
        self.status_label.setText(f"Processing: {filename}")
    
    def _on_finished(self, success: int, failed: int):
        self.progress_bar.setVisible(False)
        self.status_label.setVisible(False)
        self.process_btn.setEnabled(True)
        
        msg = f"✅ Successfully processed {success} photos."
        if failed > 0:
            msg += f"\n❌ {failed} photos failed."
        msg += "\n\n📁 Saved to 'Batch Processed/' folder"
        
        QMessageBox.information(self, "Batch Complete", msg)
        self.accept()
    
    def _step_button_style(self) -> str:
        return """
            QPushButton {
                background-color: #3a3a3a;
                border: 1px solid #555;
                border-radius: 4px;
                color: #e0e0e0;
                padding: 8px;
                text-align: left;
            }
            QPushButton:hover { background-color: #4a4a4a; }
        """
    
    def _small_button_style(self) -> str:
        return """
            QPushButton {
                background-color: #3a3a3a;
                border: 1px solid #555;
                border-radius: 4px;
                color: #e0e0e0;
                padding: 6px 12px;
            }
            QPushButton:hover { background-color: #4a4a4a; }
        """
    
    def _button_style(self) -> str:
        return """
            QPushButton {
                background-color: #3a3a3a;
                border: 1px solid #555;
                border-radius: 6px;
                color: #e0e0e0;
                padding: 10px 20px;
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
                font-weight: bold;
            }
            QPushButton:hover { background-color: #5aacff; }
            QPushButton:disabled { background-color: #555; }
        """

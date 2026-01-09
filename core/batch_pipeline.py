"""
Batch processing pipeline for chaining multiple image operations.
"""
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from enum import Enum
import logging
from datetime import datetime

from PIL import Image, ImageOps

logger = logging.getLogger(__name__)


class StepType(Enum):
    """Types of pipeline steps."""
    RESIZE = "resize"
    ROTATE = "rotate"
    RENAME = "rename"
    TEXT_WATERMARK = "text_watermark"
    IMAGE_WATERMARK = "image_watermark"
    WEBP_CONVERT = "webp_convert"


@dataclass
class StepConfig:
    """Configuration for a pipeline step."""
    step_type: StepType
    settings: Dict[str, Any] = field(default_factory=dict)
    
    def get(self, key: str, default=None):
        return self.settings.get(key, default)


class PipelineStep(ABC):
    """Base class for pipeline steps."""
    
    step_type: StepType
    name: str
    icon: str
    
    def __init__(self, config: StepConfig):
        self.config = config
    
    @abstractmethod
    def execute(self, img: Image.Image, context: Dict[str, Any]) -> Tuple[Image.Image, Dict[str, Any]]:
        """
        Execute the step on an image.
        
        Args:
            img: PIL Image to process
            context: Dict with 'original_path', 'output_name', 'sequence_num'
            
        Returns:
            Tuple of (processed image, updated context)
        """
        pass
    
    @abstractmethod
    def get_description(self) -> str:
        """Get a short description of current settings."""
        pass


class ResizeStep(PipelineStep):
    """Resize images by percentage, max dimension, or exact size."""
    
    step_type = StepType.RESIZE
    name = "Resize"
    icon = "📐"
    
    def execute(self, img: Image.Image, context: Dict[str, Any]) -> Tuple[Image.Image, Dict[str, Any]]:
        mode = self.config.get('mode', 'percentage')
        value = self.config.get('value', 50)
        width = self.config.get('width')
        height = self.config.get('height')
        maintain_aspect = self.config.get('maintain_aspect', True)
        
        orig_width, orig_height = img.size
        
        if mode == "percentage":
            scale = value / 100.0
            new_width = int(orig_width * scale)
            new_height = int(orig_height * scale)
        elif mode == "max_dimension":
            if orig_width >= orig_height:
                scale = value / orig_width
            else:
                scale = value / orig_height
            new_width = int(orig_width * scale)
            new_height = int(orig_height * scale)
        elif mode == "exact":
            if width and height:
                if maintain_aspect:
                    ratio = min(width / orig_width, height / orig_height)
                    new_width = int(orig_width * ratio)
                    new_height = int(orig_height * ratio)
                else:
                    new_width = width
                    new_height = height
            elif width:
                scale = width / orig_width
                new_width = width
                new_height = int(orig_height * scale)
            elif height:
                scale = height / orig_height
                new_width = int(orig_width * scale)
                new_height = height
            else:
                return img, context
        else:
            return img, context
        
        new_width = max(1, new_width)
        new_height = max(1, new_height)
        
        img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        return img, context
    
    def get_description(self) -> str:
        mode = self.config.get('mode', 'percentage')
        if mode == 'percentage':
            return f"{self.config.get('value', 50)}%"
        elif mode == 'max_dimension':
            return f"Max {self.config.get('value', 1920)}px"
        else:
            return f"{self.config.get('width', 800)}x{self.config.get('height', 600)}"


class RotateStep(PipelineStep):
    """Rotate images by 90°, 180°, or 270°."""
    
    step_type = StepType.ROTATE
    name = "Rotate"
    icon = "🔄"
    
    def execute(self, img: Image.Image, context: Dict[str, Any]) -> Tuple[Image.Image, Dict[str, Any]]:
        angle = self.config.get('angle', 90)
        
        if angle == 90:
            img = img.transpose(Image.Transpose.ROTATE_270)  # CW 90
        elif angle == 180:
            img = img.transpose(Image.Transpose.ROTATE_180)
        elif angle == 270:
            img = img.transpose(Image.Transpose.ROTATE_90)  # CW 270 = CCW 90
        
        return img, context
    
    def get_description(self) -> str:
        return f"{self.config.get('angle', 90)}° CW"


class RenameStep(PipelineStep):
    """Rename files using pattern-based naming."""
    
    step_type = StepType.RENAME
    name = "Rename"
    icon = "✏️"
    
    def execute(self, img: Image.Image, context: Dict[str, Any]) -> Tuple[Image.Image, Dict[str, Any]]:
        pattern = self.config.get('pattern', '{original}_{NNN}')
        original_path = context.get('original_path')
        seq = context.get('sequence_num', 1)
        
        if original_path:
            date = context.get('date') or datetime.now()
            
            tokens = {
                '{original}': original_path.stem,
                '{YYMMDD}': date.strftime('%y%m%d'),
                '{YYYY}': date.strftime('%Y'),
                '{MM}': date.strftime('%m'),
                '{DD}': date.strftime('%d'),
                '{NNN}': f'{seq:03d}',
                '{NN}': f'{seq:02d}',
                '{N}': str(seq),
            }
            
            new_name = pattern
            for token, value in tokens.items():
                new_name = new_name.replace(token, value)
            
            # Sanitize
            invalid_chars = '<>:"/\\|?*'
            for char in invalid_chars:
                new_name = new_name.replace(char, '')
            
            context['output_name'] = new_name.strip()
        
        return img, context  # Image unchanged, just filename
    
    def get_description(self) -> str:
        return self.config.get('pattern', '{original}_{NNN}')


class TextWatermarkStep(PipelineStep):
    """Add text watermark to images."""
    
    step_type = StepType.TEXT_WATERMARK
    name = "Text Watermark"
    icon = "💧"
    
    def execute(self, img: Image.Image, context: Dict[str, Any]) -> Tuple[Image.Image, Dict[str, Any]]:
        from PIL import ImageDraw, ImageFont
        import matplotlib.font_manager as fm
        import os
        
        text = self.config.get('text', 'Watermark')
        font_name = self.config.get('font_name', 'Arial')
        font_size = self.config.get('font_size', 48)
        color = self.config.get('color', (255, 255, 255))
        opacity = self.config.get('opacity', 128)
        position = self.config.get('position', 'bottom_right')
        margin = self.config.get('margin', 20)
        
        # Convert to RGBA
        if img.mode != 'RGBA':
            img = img.convert('RGBA')
        
        overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        
        # Load font
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
        
        # Get text bbox
        bbox = draw.textbbox((0, 0), text, font=font)
        text_w, text_h = bbox[2] - bbox[0], bbox[3] - bbox[1]
        
        # Calculate position
        x, y = self._calc_position(img.size, (text_w, text_h), position, margin)
        
        # Draw text
        draw.text((x, y), text, font=font, fill=(*color, opacity))
        
        # Composite
        img = Image.alpha_composite(img, overlay)
        return img, context
    
    def _calc_position(self, img_size, wm_size, position, margin):
        img_w, img_h = img_size
        wm_w, wm_h = wm_size
        
        positions = {
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
        return positions.get(position, positions['bottom_right'])
    
    def get_description(self) -> str:
        return f'"{self.config.get("text", "Watermark")}"'


class ImageWatermarkStep(PipelineStep):
    """Add image watermark to photos."""
    
    step_type = StepType.IMAGE_WATERMARK
    name = "Image Watermark"
    icon = "🖼️"
    
    def execute(self, img: Image.Image, context: Dict[str, Any]) -> Tuple[Image.Image, Dict[str, Any]]:
        watermark_path = self.config.get('watermark_path')
        if not watermark_path or not Path(watermark_path).exists():
            return img, context
        
        opacity = self.config.get('opacity', 128)
        position = self.config.get('position', 'bottom_right')
        margin = self.config.get('margin', 20)
        scale = self.config.get('scale', 0.2)
        
        # Convert to RGBA
        if img.mode != 'RGBA':
            img = img.convert('RGBA')
        
        # Load watermark
        wm = Image.open(watermark_path)
        if wm.mode != 'RGBA':
            wm = wm.convert('RGBA')
        
        # Scale watermark
        wm_width = int(img.size[0] * scale)
        wm_height = int(wm.size[1] * (wm_width / wm.size[0]))
        wm = wm.resize((wm_width, wm_height), Image.Resampling.LANCZOS)
        
        # Apply opacity
        if opacity < 255:
            r, g, b, a = wm.split()
            a = a.point(lambda x: int(x * opacity / 255))
            wm = Image.merge('RGBA', (r, g, b, a))
        
        # Calculate position
        x, y = TextWatermarkStep._calc_position(None, img.size, wm.size, position, margin)
        
        # Paste
        img.paste(wm, (x, y), wm)
        return img, context
    
    def get_description(self) -> str:
        path = self.config.get('watermark_path', '')
        return Path(path).name if path else "No image"


class WebPConvertStep(PipelineStep):
    """Convert to WebP format."""
    
    step_type = StepType.WEBP_CONVERT
    name = "Convert to WebP"
    icon = "🌐"
    
    def execute(self, img: Image.Image, context: Dict[str, Any]) -> Tuple[Image.Image, Dict[str, Any]]:
        # Mark for WebP output
        context['output_format'] = 'webp'
        context['quality'] = self.config.get('quality', 85)
        context['lossless'] = self.config.get('lossless', False)
        return img, context
    
    def get_description(self) -> str:
        if self.config.get('lossless', False):
            return "Lossless"
        return f"Quality {self.config.get('quality', 85)}%"


# Step factory
STEP_CLASSES = {
    StepType.RESIZE: ResizeStep,
    StepType.ROTATE: RotateStep,
    StepType.RENAME: RenameStep,
    StepType.TEXT_WATERMARK: TextWatermarkStep,
    StepType.IMAGE_WATERMARK: ImageWatermarkStep,
    StepType.WEBP_CONVERT: WebPConvertStep,
}


def create_step(step_type: StepType, settings: Dict[str, Any] = None) -> PipelineStep:
    """Create a pipeline step of the given type."""
    config = StepConfig(step_type=step_type, settings=settings or {})
    step_class = STEP_CLASSES.get(step_type)
    if step_class:
        return step_class(config)
    raise ValueError(f"Unknown step type: {step_type}")


class BatchPipeline:
    """Manages a pipeline of processing steps."""
    
    def __init__(self):
        self.steps: List[PipelineStep] = []
    
    def add_step(self, step: PipelineStep):
        """Add a step to the end of the pipeline."""
        self.steps.append(step)
    
    def remove_step(self, index: int):
        """Remove a step by index."""
        if 0 <= index < len(self.steps):
            self.steps.pop(index)
    
    def move_step(self, from_idx: int, to_idx: int):
        """Move a step from one position to another."""
        if 0 <= from_idx < len(self.steps) and 0 <= to_idx < len(self.steps):
            step = self.steps.pop(from_idx)
            self.steps.insert(to_idx, step)
    
    def execute_on_image(
        self, 
        img: Image.Image, 
        original_path: Path,
        sequence_num: int = 1,
        photo_date: datetime = None
    ) -> Tuple[Image.Image, Dict[str, Any]]:
        """
        Execute all steps on a single image.
        
        Returns:
            Tuple of (processed image, context with output info)
        """
        context = {
            'original_path': original_path,
            'output_name': original_path.stem,
            'sequence_num': sequence_num,
            'date': photo_date or datetime.now(),
            'output_format': original_path.suffix.lower().lstrip('.'),
            'quality': 85,
        }
        
        for step in self.steps:
            try:
                img, context = step.execute(img, context)
            except Exception as e:
                logger.error(f"Step {step.name} failed: {e}")
        
        return img, context

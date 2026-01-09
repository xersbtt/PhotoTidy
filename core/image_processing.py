"""
Image processing operations: resize, watermark, and format conversion.
"""
from pathlib import Path
from typing import Optional, Tuple, Literal
import logging
import io

from PIL import Image, ImageDraw, ImageFont, ImageOps, ExifTags
from PIL.ExifTags import TAGS

# Register HEIC/HEIF support
try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
except ImportError:
    pass

import rawpy

from config import RAW_IMAGE_EXTENSIONS

logger = logging.getLogger(__name__)

# Position constants
POSITION_TOP_LEFT = "top_left"
POSITION_TOP_CENTER = "top_center"
POSITION_TOP_RIGHT = "top_right"
POSITION_CENTER_LEFT = "center_left"
POSITION_CENTER = "center"
POSITION_CENTER_RIGHT = "center_right"
POSITION_BOTTOM_LEFT = "bottom_left"
POSITION_BOTTOM_CENTER = "bottom_center"
POSITION_BOTTOM_RIGHT = "bottom_right"


def _load_image(photo_path: Path) -> Optional[Image.Image]:
    """Load an image from path, handling RAW and standard formats."""
    extension = photo_path.suffix.lower()
    
    try:
        if extension in RAW_IMAGE_EXTENSIONS:
            with rawpy.imread(str(photo_path)) as raw:
                rgb = raw.postprocess(use_camera_wb=True, output_bps=8)
                return Image.fromarray(rgb)
        else:
            img = Image.open(photo_path)
            
            # Apply EXIF orientation to correct rotation
            img = ImageOps.exif_transpose(img)
            
            if img.mode in ('RGBA', 'P'):
                # Convert to RGB with white background for transparency
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                return background
            elif img.mode != 'RGB':
                return img.convert('RGB')
            return img
    except Exception as e:
        logger.error(f"Failed to load image {photo_path}: {e}")
        return None


def _get_exif_data(photo_path: Path) -> Optional[bytes]:
    """
    Extract EXIF data from an image, resetting orientation to normal.
    
    Since we apply exif_transpose when loading, the pixel data is already
    correctly oriented. We must reset the orientation tag to 1 (normal)
    to prevent viewers from applying rotation again.
    """
    try:
        with Image.open(photo_path) as img:
            exif = img.info.get('exif')
            if exif:
                try:
                    import piexif
                    exif_dict = piexif.load(exif)
                    # Reset orientation to 1 (normal)
                    if piexif.ImageIFD.Orientation in exif_dict.get("0th", {}):
                        exif_dict["0th"][piexif.ImageIFD.Orientation] = 1
                    return piexif.dump(exif_dict)
                except ImportError:
                    # piexif not available, don't preserve EXIF to avoid rotation
                    logger.warning("piexif not installed, EXIF data will not be preserved")
                    return None
                except Exception as e:
                    logger.warning(f"Error processing EXIF: {e}")
                    return None
            return None
    except Exception:
        return None


def _save_image(
    img: Image.Image, 
    output_path: Path, 
    quality: int = 85, 
    exif_data: Optional[bytes] = None
) -> bool:
    """Save image with optional EXIF data preservation."""
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        save_kwargs = {'quality': quality}
        if exif_data:
            save_kwargs['exif'] = exif_data
        
        # Handle different output formats
        suffix = output_path.suffix.lower()
        if suffix == '.webp':
            img.save(output_path, 'WEBP', **save_kwargs)
        elif suffix in ('.jpg', '.jpeg'):
            img.save(output_path, 'JPEG', **save_kwargs)
        elif suffix == '.png':
            # PNG doesn't use quality, uses compress_level
            png_kwargs = {'compress_level': 6}
            if exif_data:
                png_kwargs['exif'] = exif_data
            img.save(output_path, 'PNG', **png_kwargs)
        else:
            img.save(output_path, **save_kwargs)
        
        return True
    except Exception as e:
        logger.error(f"Failed to save image {output_path}: {e}")
        return False


def resize_image(
    photo_path: Path,
    output_path: Path,
    mode: Literal["percentage", "max_dimension", "exact"] = "percentage",
    value: int = 50,
    width: Optional[int] = None,
    height: Optional[int] = None,
    maintain_aspect: bool = True,
    quality: int = 85,
    preserve_exif: bool = True
) -> bool:
    """
    Resize an image.
    
    Args:
        photo_path: Path to source image
        output_path: Path to save resized image
        mode: "percentage" (value=50 means 50%), "max_dimension" (longest side), "exact"
        value: Percentage or max dimension in pixels
        width: For exact mode - target width
        height: For exact mode - target height
        maintain_aspect: Keep aspect ratio (for exact mode)
        quality: Output quality (1-100)
        preserve_exif: Keep EXIF metadata
        
    Returns:
        True if successful
    """
    img = _load_image(photo_path)
    if img is None:
        return False
    
    exif_data = _get_exif_data(photo_path) if preserve_exif else None
    orig_width, orig_height = img.size
    
    try:
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
                    # Fit within bounds while maintaining aspect
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
                return False
        else:
            return False
        
        # Ensure minimum dimensions
        new_width = max(1, new_width)
        new_height = max(1, new_height)
        
        resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        return _save_image(resized, output_path, quality, exif_data)
        
    except Exception as e:
        logger.error(f"Failed to resize {photo_path}: {e}")
        return False
    finally:
        img.close()


def _calculate_position(
    img_size: Tuple[int, int],
    watermark_size: Tuple[int, int],
    position: str,
    margin: int = 20
) -> Tuple[int, int]:
    """Calculate x, y coordinates for watermark placement."""
    img_w, img_h = img_size
    wm_w, wm_h = watermark_size
    
    positions = {
        POSITION_TOP_LEFT: (margin, margin),
        POSITION_TOP_CENTER: ((img_w - wm_w) // 2, margin),
        POSITION_TOP_RIGHT: (img_w - wm_w - margin, margin),
        POSITION_CENTER_LEFT: (margin, (img_h - wm_h) // 2),
        POSITION_CENTER: ((img_w - wm_w) // 2, (img_h - wm_h) // 2),
        POSITION_CENTER_RIGHT: (img_w - wm_w - margin, (img_h - wm_h) // 2),
        POSITION_BOTTOM_LEFT: (margin, img_h - wm_h - margin),
        POSITION_BOTTOM_CENTER: ((img_w - wm_w) // 2, img_h - wm_h - margin),
        POSITION_BOTTOM_RIGHT: (img_w - wm_w - margin, img_h - wm_h - margin),
    }
    
    return positions.get(position, positions[POSITION_BOTTOM_RIGHT])


def add_text_watermark(
    photo_path: Path,
    output_path: Path,
    text: str,
    font_name: Optional[str] = None,
    font_size: int = 36,
    color: Tuple[int, int, int] = (255, 255, 255),
    opacity: int = 128,
    position: str = POSITION_BOTTOM_RIGHT,
    margin: int = 20,
    quality: int = 85,
    preserve_exif: bool = True
) -> bool:
    """
    Add text watermark to an image.
    
    Args:
        photo_path: Path to source image
        output_path: Path to save watermarked image
        text: Watermark text
        font_name: System font name (or None for default)
        font_size: Font size in pixels
        color: RGB color tuple
        opacity: 0-255 (0=transparent, 255=opaque)
        position: One of the POSITION_* constants
        margin: Pixels from edge
        quality: Output quality
        preserve_exif: Keep EXIF metadata
        
    Returns:
        True if successful
    """
    img = _load_image(photo_path)
    if img is None:
        logger.error(f"Failed to load image for watermark: {photo_path}")
        return False
    
    exif_data = _get_exif_data(photo_path) if preserve_exif else None
    
    try:
        # Convert to RGBA for transparency support
        img = img.convert('RGBA')
        
        # Create transparent overlay for watermark
        overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        
        # Load font using matplotlib font_manager for reliable lookup
        font = None
        if font_name:
            try:
                import matplotlib.font_manager as fm
                # Find font file path from font name
                font_props = fm.FontProperties(family=font_name)
                font_path = fm.findfont(font_props, fallback_to_default=False)
                if font_path and font_path != fm.findfont(fm.FontProperties()):
                    font = ImageFont.truetype(font_path, font_size)
                    logger.info(f"Loaded font '{font_name}' from: {font_path}")
            except Exception as e:
                logger.warning(f"Failed to find font '{font_name}': {e}")
        
        # Fallback to Arial if not found
        if font is None:
            import os
            windows_fonts = os.path.join(os.environ.get('WINDIR', 'C:\\Windows'), 'Fonts')
            arial_path = os.path.join(windows_fonts, 'arial.ttf')
            try:
                font = ImageFont.truetype(arial_path, font_size)
                logger.info(f"Using fallback font: {arial_path}")
            except Exception as e:
                logger.warning(f"Failed to load Arial: {e}")
                font = ImageFont.load_default()
                logger.warning("Using PIL default font")
        
        # Get text bounding box
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        logger.info(f"Watermark text: '{text}', size: {text_width}x{text_height}, color: {color}, opacity: {opacity}")
        
        # Calculate position
        x, y = _calculate_position(img.size, (text_width, text_height), position, margin)
        logger.info(f"Position: ({x}, {y}) for image size {img.size}")
        
        # Draw text with opacity
        text_color = (*color, opacity)
        draw.text((x, y), text, font=font, fill=text_color)
        
        # Composite overlay onto image
        watermarked = Image.alpha_composite(img, overlay)
        
        # Convert back to RGB for saving
        watermarked = watermarked.convert('RGB')
        
        result = _save_image(watermarked, output_path, quality, exif_data)
        if result:
            logger.info(f"Watermarked image saved to: {output_path}")
        return result
        
    except Exception as e:
        logger.error(f"Failed to add text watermark to {photo_path}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False
    finally:
        img.close()


def add_image_watermark(
    photo_path: Path,
    output_path: Path,
    watermark_path: Path,
    opacity: int = 128,
    position: str = POSITION_BOTTOM_RIGHT,
    margin: int = 20,
    scale: float = 0.2,
    quality: int = 85,
    preserve_exif: bool = True
) -> bool:
    """
    Add image watermark to a photo.
    
    Args:
        photo_path: Path to source image
        output_path: Path to save watermarked image
        watermark_path: Path to watermark image (PNG with transparency recommended)
        opacity: 0-255 (0=transparent, 255=opaque)
        position: One of the POSITION_* constants
        margin: Pixels from edge
        scale: Scale watermark relative to image (0.2 = 20% of image width)
        quality: Output quality
        preserve_exif: Keep EXIF metadata
        
    Returns:
        True if successful
    """
    img = _load_image(photo_path)
    if img is None:
        return False
    
    exif_data = _get_exif_data(photo_path) if preserve_exif else None
    
    try:
        # Load watermark
        watermark = Image.open(watermark_path)
        if watermark.mode != 'RGBA':
            watermark = watermark.convert('RGBA')
        
        # Scale watermark
        wm_width = int(img.size[0] * scale)
        wm_height = int(watermark.size[1] * (wm_width / watermark.size[0]))
        watermark = watermark.resize((wm_width, wm_height), Image.Resampling.LANCZOS)
        
        # Apply opacity
        if opacity < 255:
            r, g, b, a = watermark.split()
            a = a.point(lambda x: int(x * opacity / 255))
            watermark = Image.merge('RGBA', (r, g, b, a))
        
        # Convert main image to RGBA
        img = img.convert('RGBA')
        
        # Calculate position
        x, y = _calculate_position(img.size, watermark.size, position, margin)
        
        # Paste watermark
        img.paste(watermark, (x, y), watermark)
        
        # Convert back to RGB
        img = img.convert('RGB')
        
        return _save_image(img, output_path, quality, exif_data)
        
    except Exception as e:
        logger.error(f"Failed to add image watermark to {photo_path}: {e}")
        return False
    finally:
        img.close()


def convert_to_webp(
    photo_path: Path,
    output_path: Path,
    quality: int = 85,
    lossless: bool = False,
    preserve_exif: bool = True
) -> bool:
    """
    Convert an image to WebP format.
    
    Args:
        photo_path: Path to source image
        output_path: Path to save WebP image (should have .webp extension)
        quality: Quality for lossy compression (1-100)
        lossless: Use lossless compression
        preserve_exif: Keep EXIF metadata
        
    Returns:
        True if successful
    """
    img = _load_image(photo_path)
    if img is None:
        return False
    
    exif_data = _get_exif_data(photo_path) if preserve_exif else None
    
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        save_kwargs = {
            'quality': quality,
            'lossless': lossless,
        }
        if exif_data:
            save_kwargs['exif'] = exif_data
        
        img.save(output_path, 'WEBP', **save_kwargs)
        return True
        
    except Exception as e:
        logger.error(f"Failed to convert {photo_path} to WebP: {e}")
        return False
    finally:
        img.close()


def get_system_fonts() -> list:
    """Get list of available system fonts."""
    import matplotlib.font_manager as fm
    fonts = set()
    for f in fm.findSystemFonts():
        try:
            font = fm.get_font(f)
            fonts.add(font.family_name)
        except Exception:
            pass
    return sorted(fonts)

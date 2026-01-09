"""
Thumbnail generation and caching for photos.
"""
from pathlib import Path
from typing import Optional
import hashlib
import logging

from PIL import Image, ImageOps
import rawpy

# Register HEIC/HEIF support
try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
except ImportError:
    pass  # HEIC support optional

from config import (
    THUMBNAIL_SIZE, 
    THUMBNAIL_QUALITY, 
    THUMBNAIL_CACHE_DIR,
    RAW_IMAGE_EXTENSIONS
)

logger = logging.getLogger(__name__)


class ThumbnailManager:
    """Manages thumbnail generation and caching."""
    
    def __init__(self, cache_dir: Path = THUMBNAIL_CACHE_DIR):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def get_thumbnail(self, photo_path: Path, size: tuple = THUMBNAIL_SIZE) -> Optional[Path]:
        """
        Get or generate a thumbnail for a photo.
        
        Args:
            photo_path: Path to the original photo
            size: Thumbnail size (width, height)
            
        Returns:
            Path to the thumbnail, or None if generation failed
        """
        cache_key = self._get_cache_key(photo_path, size)
        cache_path = self.cache_dir / f"{cache_key}.jpg"
        
        # Return cached thumbnail if it exists
        if cache_path.exists():
            return cache_path
        
        # Generate new thumbnail
        try:
            thumbnail = self._generate_thumbnail(photo_path, size)
            if thumbnail:
                thumbnail.save(cache_path, 'JPEG', quality=THUMBNAIL_QUALITY)
                return cache_path
        except Exception as e:
            logger.error(f"Failed to generate thumbnail for {photo_path}: {e}")
        
        return None
    
    def _generate_thumbnail(self, photo_path: Path, size: tuple) -> Optional[Image.Image]:
        """Generate a thumbnail image."""
        extension = photo_path.suffix.lower()
        
        if extension in RAW_IMAGE_EXTENSIONS:
            return self._generate_raw_thumbnail(photo_path, size)
        else:
            return self._generate_standard_thumbnail(photo_path, size)
    
    def _generate_standard_thumbnail(self, photo_path: Path, size: tuple) -> Optional[Image.Image]:
        """Generate thumbnail for standard image formats."""
        try:
            with Image.open(photo_path) as img:
                # Apply EXIF orientation to correct rotation
                img = ImageOps.exif_transpose(img)
                
                # Convert to RGB if necessary
                if img.mode in ('RGBA', 'P'):
                    img = img.convert('RGB')
                elif img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Use high-quality resampling
                img.thumbnail(size, Image.Resampling.LANCZOS)
                return img.copy()
        except Exception as e:
            logger.error(f"Failed to create standard thumbnail: {e}")
            return None
    
    def _generate_raw_thumbnail(self, photo_path: Path, size: tuple) -> Optional[Image.Image]:
        """Generate thumbnail for RAW image formats."""
        try:
            with rawpy.imread(str(photo_path)) as raw:
                # Try to extract embedded thumbnail first (faster)
                try:
                    thumb = raw.extract_thumb()
                    if thumb.format == rawpy.ThumbFormat.JPEG:
                        import io
                        img = Image.open(io.BytesIO(thumb.data))
                        # Apply EXIF orientation for embedded thumbnails too
                        img = ImageOps.exif_transpose(img)
                        img.thumbnail(size, Image.Resampling.LANCZOS)
                        return img.convert('RGB')
                except rawpy.LibRawNoThumbnailError:
                    pass
                
                # Fall back to full RAW processing
                rgb = raw.postprocess(
                    use_camera_wb=True,
                    half_size=True,  # Faster processing
                    no_auto_bright=False,
                    output_bps=8
                )
                img = Image.fromarray(rgb)
                img.thumbnail(size, Image.Resampling.LANCZOS)
                return img
                
        except Exception as e:
            logger.error(f"Failed to create RAW thumbnail: {e}")
            return None
    
    def _get_cache_key(self, photo_path: Path, size: tuple) -> str:
        """Generate a unique cache key for a photo and size."""
        # Include path and modification time in hash
        stat = photo_path.stat()
        key_data = f"{photo_path}:{stat.st_mtime}:{stat.st_size}:{size}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def clear_cache(self):
        """Clear all cached thumbnails."""
        for thumb_file in self.cache_dir.glob('*.jpg'):
            try:
                thumb_file.unlink()
            except Exception as e:
                logger.warning(f"Failed to delete {thumb_file}: {e}")
    
    def get_cache_size(self) -> int:
        """Get total size of cached thumbnails in bytes."""
        return sum(f.stat().st_size for f in self.cache_dir.glob('*.jpg'))

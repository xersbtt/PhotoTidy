"""
Photo rotation utilities.
"""
from pathlib import Path
from typing import List, Tuple
import logging

from PIL import Image
import rawpy

from config import RAW_IMAGE_EXTENSIONS

logger = logging.getLogger(__name__)


def rotate_photo(photo_path: Path, clockwise: bool = True) -> bool:
    """
    Rotate a photo 90 degrees and save it.
    
    Args:
        photo_path: Path to the photo file
        clockwise: If True, rotate clockwise; otherwise counterclockwise
        
    Returns:
        True if successful, False otherwise
    """
    try:
        extension = photo_path.suffix.lower()
        
        if extension in RAW_IMAGE_EXTENSIONS:
            # RAW files can't be easily rotated - would need to convert
            logger.warning(f"Cannot rotate RAW file: {photo_path}")
            return False
        
        # Open image
        with Image.open(photo_path) as img:
            # Determine rotation angle
            if clockwise:
                angle = -90  # PIL rotates counterclockwise by default
            else:
                angle = 90
            
            # Rotate with expand to avoid cropping
            rotated = img.rotate(angle, expand=True)
            
            # Preserve EXIF data if available
            exif = img.info.get('exif')
            
            # Save back to original path
            if exif:
                rotated.save(photo_path, exif=exif, quality=95)
            else:
                rotated.save(photo_path, quality=95)
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to rotate {photo_path}: {e}")
        return False


def rotate_photos(
    photo_paths: List[Path], 
    clockwise: bool = True,
    progress_callback=None
) -> Tuple[int, int, List[str]]:
    """
    Rotate multiple photos.
    
    Args:
        photo_paths: List of photo file paths
        clockwise: If True, rotate clockwise
        progress_callback: Optional callback(current, total)
        
    Returns:
        Tuple of (success_count, skipped_count, error_messages)
    """
    success_count = 0
    skipped_count = 0
    errors = []
    
    for i, path in enumerate(photo_paths):
        if path.suffix.lower() in RAW_IMAGE_EXTENSIONS:
            skipped_count += 1
            continue
        
        if rotate_photo(path, clockwise):
            success_count += 1
        else:
            errors.append(f"Failed to rotate: {path.name}")
        
        if progress_callback:
            progress_callback(i + 1, len(photo_paths))
    
    return success_count, skipped_count, errors

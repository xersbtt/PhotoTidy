"""
Image hashing utilities for duplicate detection.
"""
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import logging
from collections import defaultdict

from PIL import Image
import imagehash
import rawpy

from config import RAW_IMAGE_EXTENSIONS

logger = logging.getLogger(__name__)


def compute_image_hash(image_path: Path, hash_size: int = 8) -> Optional[str]:
    """
    Compute a perceptual hash for an image.
    
    Args:
        image_path: Path to the image file
        hash_size: Size of the hash (default 8 produces a 64-bit hash)
        
    Returns:
        Hex string of the hash, or None if hashing failed
    """
    try:
        if image_path.suffix.lower() in RAW_IMAGE_EXTENSIONS:
            img = _load_raw_for_hashing(image_path)
        else:
            img = Image.open(image_path)
        
        if img is None:
            return None
        
        # Use average hash for speed, or phash for better accuracy
        hash_value = imagehash.average_hash(img, hash_size=hash_size)
        return str(hash_value)
        
    except Exception as e:
        logger.warning(f"Failed to compute hash for {image_path}: {e}")
        return None


def _load_raw_for_hashing(path: Path) -> Optional[Image.Image]:
    """Load a RAW image for hashing."""
    try:
        with rawpy.imread(str(path)) as raw:
            # Try embedded thumbnail first (faster)
            try:
                thumb = raw.extract_thumb()
                if thumb.format == rawpy.ThumbFormat.JPEG:
                    import io
                    return Image.open(io.BytesIO(thumb.data))
            except rawpy.LibRawNoThumbnailError:
                pass
            
            # Fall back to processing
            rgb = raw.postprocess(
                use_camera_wb=True,
                half_size=True,
                output_bps=8
            )
            return Image.fromarray(rgb)
            
    except Exception as e:
        logger.warning(f"Failed to load RAW for hashing: {e}")
        return None


def find_duplicates(
    image_paths: List[Path],
    threshold: int = 5,
    progress_callback=None
) -> Dict[str, List[Path]]:
    """
    Find duplicate images using perceptual hashing.
    
    Args:
        image_paths: List of image file paths to check
        threshold: Maximum hamming distance to consider as duplicate (0 = exact match)
        progress_callback: Optional callback(current, total) for progress updates
        
    Returns:
        Dictionary mapping hash values to lists of duplicate file paths
    """
    # First pass: compute hashes
    hashes: Dict[Path, Optional[imagehash.ImageHash]] = {}
    
    for i, path in enumerate(image_paths):
        try:
            if path.suffix.lower() in RAW_IMAGE_EXTENSIONS:
                img = _load_raw_for_hashing(path)
            else:
                img = Image.open(path)
            
            if img:
                hashes[path] = imagehash.average_hash(img)
            else:
                hashes[path] = None
                
        except Exception as e:
            logger.warning(f"Failed to hash {path}: {e}")
            hashes[path] = None
        
        if progress_callback:
            progress_callback(i + 1, len(image_paths))
    
    # Second pass: find similar hashes
    duplicates: Dict[str, List[Path]] = defaultdict(list)
    processed = set()
    
    valid_paths = [(p, h) for p, h in hashes.items() if h is not None]
    
    for i, (path1, hash1) in enumerate(valid_paths):
        if path1 in processed:
            continue
        
        group = [path1]
        
        for path2, hash2 in valid_paths[i+1:]:
            if path2 in processed:
                continue
            
            # Compare hashes
            distance = hash1 - hash2
            if distance <= threshold:
                group.append(path2)
                processed.add(path2)
        
        if len(group) > 1:
            # Use first hash as group key
            duplicates[str(hash1)] = group
            processed.add(path1)
    
    return dict(duplicates)


def get_duplicate_groups(
    image_paths: List[Path],
    threshold: int = 5,
    progress_callback=None
) -> List[List[Path]]:
    """
    Find and return groups of duplicate images.
    
    Args:
        image_paths: List of image file paths to check
        threshold: Maximum hamming distance to consider as duplicate
        progress_callback: Optional callback for progress updates
        
    Returns:
        List of lists, where each inner list contains paths of duplicate images
    """
    duplicates = find_duplicates(image_paths, threshold, progress_callback)
    return list(duplicates.values())

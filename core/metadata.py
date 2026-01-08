"""
Metadata extraction for photos.
Handles EXIF data from standard images and RAW files.
"""
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple
import logging

from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
import exifread

# Register HEIC/HEIF support
try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
except ImportError:
    pass  # HEIC support optional

from config import STANDARD_IMAGE_EXTENSIONS, RAW_IMAGE_EXTENSIONS

logger = logging.getLogger(__name__)


def extract_metadata(photo_path: Path) -> dict:
    """
    Extract metadata from a photo file.
    
    Args:
        photo_path: Path to the photo file
        
    Returns:
        Dictionary with extracted metadata
    """
    extension = photo_path.suffix.lower()
    
    if extension in RAW_IMAGE_EXTENSIONS:
        return _extract_raw_metadata(photo_path)
    else:
        return _extract_standard_metadata(photo_path)


def _extract_standard_metadata(photo_path: Path) -> dict:
    """Extract metadata from standard image formats using Pillow."""
    metadata = {
        'date_taken': None,
        'gps_latitude': None,
        'gps_longitude': None,
        'camera_make': None,
        'camera_model': None,
    }
    
    try:
        with Image.open(photo_path) as img:
            # Try getexif() first (works with HEIC), fall back to _getexif()
            exif_data = None
            exif_obj = None
            
            if hasattr(img, 'getexif'):
                exif_obj = img.getexif()
                if exif_obj:
                    exif_data = dict(exif_obj)
            
            if not exif_data and hasattr(img, '_getexif'):
                exif_data = img._getexif()
            
            if not exif_data:
                return metadata
            
            # Parse EXIF tags
            exif = {TAGS.get(k, k): v for k, v in exif_data.items()}
            
            # Extract date taken
            date_str = exif.get('DateTimeOriginal') or exif.get('DateTime')
            if date_str:
                metadata['date_taken'] = _parse_exif_date(date_str)
            
            # Extract camera info
            metadata['camera_make'] = exif.get('Make')
            metadata['camera_model'] = exif.get('Model')
            
            # Extract GPS data - try multiple ways
            gps_info = exif.get('GPSInfo')
            
            # For HEIC/pillow-heif, GPS might be in a different location
            if not gps_info and hasattr(img, 'getexif'):
                exif_obj = img.getexif()
                if exif_obj and hasattr(exif_obj, 'get_ifd'):
                    # GPS IFD is 0x8825
                    try:
                        gps_ifd = exif_obj.get_ifd(0x8825)
                        if gps_ifd:
                            gps_info = dict(gps_ifd)
                    except:
                        pass
            
            if gps_info and isinstance(gps_info, dict):
                gps_data = {GPSTAGS.get(k, k): v for k, v in gps_info.items()}
                coords = _parse_gps_info(gps_data)
                if coords:
                    metadata['gps_latitude'], metadata['gps_longitude'] = coords
                    
    except Exception as e:
        logger.warning(f"Failed to extract metadata from {photo_path}: {e}")
    
    return metadata


def _extract_raw_metadata(photo_path: Path) -> dict:
    """Extract metadata from RAW files using exifread."""
    metadata = {
        'date_taken': None,
        'gps_latitude': None,
        'gps_longitude': None,
        'camera_make': None,
        'camera_model': None,
    }
    
    try:
        with open(photo_path, 'rb') as f:
            tags = exifread.process_file(f, details=False)
            
            # Extract date taken
            date_tag = tags.get('EXIF DateTimeOriginal') or tags.get('Image DateTime')
            if date_tag:
                metadata['date_taken'] = _parse_exif_date(str(date_tag))
            
            # Extract camera info
            make_tag = tags.get('Image Make')
            model_tag = tags.get('Image Model')
            metadata['camera_make'] = str(make_tag) if make_tag else None
            metadata['camera_model'] = str(model_tag) if model_tag else None
            
            # Extract GPS data
            lat = _get_exifread_gps_coord(tags, 'GPS GPSLatitude', 'GPS GPSLatitudeRef')
            lon = _get_exifread_gps_coord(tags, 'GPS GPSLongitude', 'GPS GPSLongitudeRef')
            if lat is not None and lon is not None:
                metadata['gps_latitude'] = lat
                metadata['gps_longitude'] = lon
                
    except Exception as e:
        logger.warning(f"Failed to extract RAW metadata from {photo_path}: {e}")
    
    return metadata


def _parse_exif_date(date_str: str) -> Optional[datetime]:
    """Parse EXIF date string to datetime."""
    if not date_str:
        return None
        
    # Handle string or bytes
    if isinstance(date_str, bytes):
        date_str = date_str.decode('utf-8', errors='ignore')
    
    # EXIF date format: "YYYY:MM:DD HH:MM:SS"
    formats = [
        '%Y:%m:%d %H:%M:%S',
        '%Y-%m-%d %H:%M:%S',
        '%Y:%m:%d',
        '%Y-%m-%d',
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str.strip(), fmt)
        except ValueError:
            continue
    
    return None


def _parse_gps_info(gps_data: dict) -> Optional[Tuple[float, float]]:
    """Parse GPS info dictionary to lat/lon coordinates."""
    try:
        lat = _convert_to_degrees(gps_data.get('GPSLatitude'))
        lat_ref = gps_data.get('GPSLatitudeRef', 'N')
        
        lon = _convert_to_degrees(gps_data.get('GPSLongitude'))
        lon_ref = gps_data.get('GPSLongitudeRef', 'E')
        
        if lat is None or lon is None:
            return None
        
        if lat_ref == 'S':
            lat = -lat
        if lon_ref == 'W':
            lon = -lon
            
        return (lat, lon)
    except Exception:
        return None


def _convert_to_degrees(value) -> Optional[float]:
    """Convert GPS coordinates to degrees."""
    if not value:
        return None
    
    try:
        # Handle IFDRational tuples
        if hasattr(value[0], 'numerator'):
            d = float(value[0].numerator) / float(value[0].denominator)
            m = float(value[1].numerator) / float(value[1].denominator)
            s = float(value[2].numerator) / float(value[2].denominator)
        else:
            d, m, s = float(value[0]), float(value[1]), float(value[2])
        
        return d + (m / 60.0) + (s / 3600.0)
    except Exception:
        return None


def _get_exifread_gps_coord(tags: dict, coord_tag: str, ref_tag: str) -> Optional[float]:
    """Extract GPS coordinate from exifread tags."""
    coord = tags.get(coord_tag)
    ref = tags.get(ref_tag)
    
    if not coord:
        return None
    
    try:
        values = coord.values
        d = float(values[0].num) / float(values[0].den)
        m = float(values[1].num) / float(values[1].den)
        s = float(values[2].num) / float(values[2].den)
        
        result = d + (m / 60.0) + (s / 3600.0)
        
        if ref and str(ref) in ['S', 'W']:
            result = -result
            
        return result
    except Exception:
        return None

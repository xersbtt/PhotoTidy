"""
PhotoTidy - Photo Organization Application
"""
import os
from pathlib import Path

# Application info
APP_NAME = "PhotoTidy"
APP_VERSION = "1.2.0"

# Supported file extensions
STANDARD_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.tiff', '.tif', '.webp', '.heic', '.heif', '.bmp', '.gif'}
RAW_IMAGE_EXTENSIONS = {'.cr2', '.cr3', '.nef', '.arw', '.dng', '.orf', '.rw2', '.raf', '.srw', '.pef', '.raw'}
ALL_SUPPORTED_EXTENSIONS = STANDARD_IMAGE_EXTENSIONS | RAW_IMAGE_EXTENSIONS

# Thumbnail settings
THUMBNAIL_SIZE = (200, 200)
THUMBNAIL_QUALITY = 85

# Cache directory
CACHE_DIR = Path(os.environ.get('LOCALAPPDATA', Path.home())) / 'PhotoTidy' / 'cache'
THUMBNAIL_CACHE_DIR = CACHE_DIR / 'thumbnails'
GEOCODING_CACHE_FILE = CACHE_DIR / 'geocoding_cache.json'

# Geocoding settings
GEOCODING_USER_AGENT = "PhotoTidy/1.2"
GEOCODING_RATE_LIMIT_SECONDS = 1.0  # Nominatim requires 1 request per second

# Date format options for folder naming
DATE_FORMATS = {
    'year': '%Y',
    'year_month': '%Y/%m - %B',
    'year_month_day': '%Y/%m/%d',
    'full_date': '%Y-%m-%d',
}

# Default settings
DEFAULT_DATE_FORMAT = 'year_month'
DEFAULT_LOCATION_FORMAT = 'city_country'

# Location format options (key -> display label)
LOCATION_FORMAT_OPTIONS = {
    'suburb': 'Suburb/Locality only',
    'city': 'City only',
    'suburb_country': 'Suburb + Country',
    'city_country': 'City + Country',
    'full': 'Full (City, State, Country)',
}

# UI settings
GRID_COLUMNS = 4
PREVIEW_SIZE = (600, 600)

# Ensure cache directories exist
CACHE_DIR.mkdir(parents=True, exist_ok=True)
THUMBNAIL_CACHE_DIR.mkdir(parents=True, exist_ok=True)

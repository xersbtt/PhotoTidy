"""
Photo data model for the Photo Sorter application.
"""
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional
import hashlib


@dataclass
class Photo:
    """Represents a photo with its metadata and properties."""
    
    path: Path
    file_size: int = 0
    file_hash: str = ""
    
    # Metadata
    date_taken: Optional[datetime] = None
    gps_latitude: Optional[float] = None
    gps_longitude: Optional[float] = None
    location_name: Optional[str] = None
    camera_make: Optional[str] = None
    camera_model: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    
    # UI state
    thumbnail_path: Optional[Path] = None
    is_selected: bool = False
    
    # Computed properties
    _content_hash: Optional[str] = field(default=None, repr=False)
    
    def __post_init__(self):
        """Initialize computed properties."""
        if isinstance(self.path, str):
            self.path = Path(self.path)
        if self.file_size == 0 and self.path.exists():
            self.file_size = self.path.stat().st_size
    
    @property
    def filename(self) -> str:
        """Get the filename."""
        return self.path.name
    
    @property
    def extension(self) -> str:
        """Get the file extension (lowercase)."""
        return self.path.suffix.lower()
    
    @property
    def has_location(self) -> bool:
        """Check if photo has GPS coordinates."""
        return self.gps_latitude is not None and self.gps_longitude is not None
    
    @property
    def has_date(self) -> bool:
        """Check if photo has date taken."""
        return self.date_taken is not None
    
    @property
    def date_for_sorting(self) -> datetime:
        """Get date for sorting, using file modification time as fallback."""
        if self.date_taken:
            return self.date_taken
        # Fallback to file modification time
        return datetime.fromtimestamp(self.path.stat().st_mtime)
    
    def compute_file_hash(self) -> str:
        """Compute MD5 hash of the first 64KB for quick comparison."""
        if self._content_hash:
            return self._content_hash
        
        hasher = hashlib.md5()
        with open(self.path, 'rb') as f:
            # Read first 64KB for quick hash
            chunk = f.read(65536)
            hasher.update(chunk)
        
        self._content_hash = hasher.hexdigest()
        self.file_hash = self._content_hash
        return self._content_hash
    
    def __hash__(self):
        """Make Photo hashable for use in sets."""
        return hash(str(self.path))
    
    def __eq__(self, other):
        """Compare photos by path."""
        if isinstance(other, Photo):
            return self.path == other.path
        return False

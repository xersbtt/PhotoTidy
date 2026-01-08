"""
Photo renaming utilities with customizable patterns.
"""
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict
import logging

from core.photo import Photo

logger = logging.getLogger(__name__)


@dataclass
class RenamePreview:
    """Preview of a rename operation."""
    photo: Photo
    original_name: str
    new_name: str
    new_path: Path
    has_conflict: bool = False


class PhotoRenamer:
    """
    Handles photo renaming with customizable patterns.
    
    Pattern tokens:
    - {YYMMDD} - Date in YYMMDD format
    - {YYYY} - Full year
    - {MM} - Month (01-12)
    - {DD} - Day (01-31)
    - {city} - City name
    - {country} - Country name
    - {location} - "City, Country" format
    - {camera} - Camera model
    - {NNN} - Sequential number (001, 002, etc.)
    - {NN} - Sequential number (01, 02, etc.)
    - {N} - Sequential number (1, 2, etc.)
    - {original} - Original filename without extension
    """
    
    DEFAULT_PATTERN = "{YYMMDD} {location} IMG{NNN}"
    MISCELLANEOUS_PATTERN = "Misc IMG{NNN}"
    
    def __init__(self, pattern: str = None):
        """
        Initialize renamer with a pattern.
        
        Args:
            pattern: Rename pattern with tokens
        """
        self.pattern = pattern or self.DEFAULT_PATTERN
    
    def generate_new_names(
        self, 
        photos: List[Photo],
        group_by_date_location: bool = True
    ) -> List[RenamePreview]:
        """
        Generate new filenames for a list of photos.
        
        Args:
            photos: List of photos to rename
            group_by_date_location: If True, restart numbering for each date+location combo
            
        Returns:
            List of RenamePreview objects
        """
        previews = []
        
        if group_by_date_location:
            # Group photos by date and location for sequential numbering
            groups = self._group_photos(photos)
            
            for group_key, group_photos in groups.items():
                # Sort by date within group
                sorted_photos = sorted(group_photos, key=lambda p: p.date_for_sorting)
                
                for idx, photo in enumerate(sorted_photos, start=1):
                    preview = self._create_preview(photo, idx)
                    previews.append(preview)
        else:
            # Global sequential numbering
            sorted_photos = sorted(photos, key=lambda p: p.date_for_sorting)
            for idx, photo in enumerate(sorted_photos, start=1):
                preview = self._create_preview(photo, idx)
                previews.append(preview)
        
        # Check for conflicts
        self._check_conflicts(previews)
        
        return previews
    
    def _group_photos(self, photos: List[Photo]) -> Dict[str, List[Photo]]:
        """Group photos by date and location."""
        groups = defaultdict(list)
        
        for photo in photos:
            date = photo.date_for_sorting
            date_key = date.strftime("%y%m%d")
            location_key = photo.location_name or "Unknown"
            
            # Check if miscellaneous (no camera metadata and no date)
            if self._is_miscellaneous(photo):
                group_key = "MISC"
            else:
                group_key = f"{date_key}_{location_key}"
            
            groups[group_key].append(photo)
        
        return dict(groups)
    
    def _is_miscellaneous(self, photo: Photo) -> bool:
        """Check if photo should be classified as Miscellaneous."""
        # No camera metadata AND no EXIF date (likely screenshot or downloaded image)
        has_camera = photo.camera_make or photo.camera_model
        has_exif_date = photo.date_taken is not None
        return not has_camera and not has_exif_date
    
    def _create_preview(self, photo: Photo, sequence_num: int) -> RenamePreview:
        """Create a rename preview for a single photo."""
        # Use different pattern for miscellaneous photos
        if self._is_miscellaneous(photo):
            new_name = self._apply_pattern(photo, sequence_num, self.MISCELLANEOUS_PATTERN)
        else:
            new_name = self._apply_pattern(photo, sequence_num, self.pattern)
        
        # Add original extension
        new_name = new_name + photo.extension
        
        # Sanitize filename
        new_name = self._sanitize_filename(new_name)
        
        new_path = photo.path.parent / new_name
        
        return RenamePreview(
            photo=photo,
            original_name=photo.filename,
            new_name=new_name,
            new_path=new_path
        )
    
    def _apply_pattern(self, photo: Photo, seq_num: int, pattern: str) -> str:
        """Apply pattern to generate new filename."""
        date = photo.date_for_sorting
        
        # Parse location
        location = photo.location_name or "Unknown Location"
        parts = location.split(", ")
        city = parts[0] if parts else "Unknown"
        country = parts[-1] if len(parts) > 1 else ""
        
        # Build token replacements
        tokens = {
            "{YYMMDD}": date.strftime("%y%m%d"),
            "{YYYY}": date.strftime("%Y"),
            "{YY}": date.strftime("%y"),
            "{MM}": date.strftime("%m"),
            "{DD}": date.strftime("%d"),
            "{city}": city,
            "{country}": country,
            "{location}": location if location != "Unknown Location" else "",
            "{camera}": f"{photo.camera_make or ''} {photo.camera_model or ''}".strip(),
            "{NNN}": f"{seq_num:03d}",
            "{NN}": f"{seq_num:02d}",
            "{N}": str(seq_num),
            "{original}": photo.path.stem,
        }
        
        result = pattern
        for token, value in tokens.items():
            result = result.replace(token, value)
        
        # Clean up multiple spaces and trim
        result = " ".join(result.split())
        
        return result
    
    def _sanitize_filename(self, filename: str) -> str:
        """Remove or replace invalid filename characters."""
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '')
        return filename.strip()
    
    def _check_conflicts(self, previews: List[RenamePreview]):
        """Mark any conflicting new names."""
        name_counts = defaultdict(int)
        
        for preview in previews:
            name_counts[preview.new_name.lower()] += 1
        
        for preview in previews:
            if name_counts[preview.new_name.lower()] > 1:
                preview.has_conflict = True
    
    def execute_renames(
        self, 
        previews: List[RenamePreview],
        skip_conflicts: bool = True
    ) -> Tuple[int, int, List[str]]:
        """
        Execute the rename operations.
        
        Args:
            previews: List of rename previews
            skip_conflicts: If True, skip files with naming conflicts
            
        Returns:
            Tuple of (success_count, skipped_count, error_messages)
        """
        success_count = 0
        skipped_count = 0
        errors = []
        
        for preview in previews:
            if preview.has_conflict and skip_conflicts:
                skipped_count += 1
                continue
            
            if preview.original_name == preview.new_name:
                # No change needed
                continue
            
            try:
                # Handle potential conflicts by appending number
                final_path = preview.new_path
                if final_path.exists() and final_path != preview.photo.path:
                    final_path = self._resolve_conflict(preview.new_path)
                
                preview.photo.path.rename(final_path)
                preview.photo.path = final_path
                success_count += 1
                
            except Exception as e:
                errors.append(f"Failed to rename {preview.original_name}: {e}")
                logger.error(f"Rename failed: {e}")
        
        return success_count, skipped_count, errors
    
    def _resolve_conflict(self, path: Path) -> Path:
        """Find a unique filename if conflict exists."""
        stem = path.stem
        suffix = path.suffix
        parent = path.parent
        
        counter = 1
        while True:
            new_path = parent / f"{stem}_{counter}{suffix}"
            if not new_path.exists():
                return new_path
            counter += 1


def is_miscellaneous_photo(photo: Photo) -> bool:
    """
    Check if a photo should be classified as Miscellaneous.
    
    A photo is miscellaneous if it has no camera metadata AND no EXIF date,
    indicating it's likely a screenshot, downloaded image, or edited file.
    """
    has_camera = photo.camera_make or photo.camera_model
    has_exif_date = photo.date_taken is not None
    return not has_camera and not has_exif_date

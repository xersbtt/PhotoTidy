"""
Camera-based sorting strategy.
"""
from typing import Dict, List
from core.photo import Photo
from .base import SortingStrategy


class CameraSorter(SortingStrategy):
    """Sort photos by camera make/model."""
    
    UNKNOWN_CAMERA = "Unknown Camera"
    
    def __init__(self, include_model: bool = True):
        """
        Initialize camera sorter.
        
        Args:
            include_model: If True, include model name; otherwise just make
        """
        self.include_model = include_model
    
    @property
    def name(self) -> str:
        return "Camera"
    
    @property
    def description(self) -> str:
        return "Sort photos by camera make and model"
    
    def get_group_key(self, photo: Photo) -> str:
        """Get camera-based group key."""
        if not photo.camera_make and not photo.camera_model:
            return self.UNKNOWN_CAMERA
        
        if self.include_model:
            parts = []
            if photo.camera_make:
                parts.append(photo.camera_make.strip())
            if photo.camera_model:
                # Avoid duplicating make in model (some cameras do this)
                model = photo.camera_model.strip()
                if photo.camera_make and model.startswith(photo.camera_make):
                    model = model[len(photo.camera_make):].strip()
                if model:
                    parts.append(model)
            return " ".join(parts) if parts else self.UNKNOWN_CAMERA
        else:
            return photo.camera_make.strip() if photo.camera_make else self.UNKNOWN_CAMERA
    
    def get_folder_name(self, group_key: str) -> str:
        """Convert group key to folder name."""
        # Sanitize for filesystem
        return self._sanitize_folder_name(group_key)
    
    def _sanitize_folder_name(self, name: str) -> str:
        """Remove invalid filesystem characters."""
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            name = name.replace(char, '')
        return name.strip()
    
    def get_sorted_group_keys(self, groups: Dict[str, List[Photo]]) -> List[str]:
        """Sort keys alphabetically, with Unknown at end."""
        keys = list(groups.keys())
        
        # Sort alphabetically, but put Unknown at end
        def sort_key(k):
            if k == self.UNKNOWN_CAMERA:
                return (1, k)  # Put at end
            return (0, k.lower())
        
        return sorted(keys, key=sort_key)
    
    def get_display_name(self, group_key: str) -> str:
        """Get display name for the group."""
        return group_key

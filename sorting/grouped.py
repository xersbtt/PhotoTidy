"""
Photo grouping and management.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from core.photo import Photo
from .base import SortingStrategy


@dataclass
class PhotoGroup:
    """A group of photos sharing a common property."""
    key: str
    display_name: str
    folder_name: str
    photos: List[Photo] = field(default_factory=list)
    is_expanded: bool = True
    
    @property
    def count(self) -> int:
        return len(self.photos)
    
    @property
    def selected_count(self) -> int:
        return sum(1 for p in self.photos if p.is_selected)
    
    @property
    def all_selected(self) -> bool:
        return self.count > 0 and self.selected_count == self.count
    
    def select_all(self):
        """Select all photos in this group."""
        for photo in self.photos:
            photo.is_selected = True
    
    def deselect_all(self):
        """Deselect all photos in this group."""
        for photo in self.photos:
            photo.is_selected = False
    
    def toggle_selection(self):
        """Toggle selection of all photos in this group."""
        if self.all_selected:
            self.deselect_all()
        else:
            self.select_all()


class PhotoGrouper:
    """Manages photo grouping using different sorting strategies."""
    
    def __init__(self):
        self._photos: List[Photo] = []
        self._groups: List[PhotoGroup] = []
        self._current_strategy: Optional[SortingStrategy] = None
        self._sort_ascending: bool = True  # Default: oldest first
    
    @property
    def photos(self) -> List[Photo]:
        return self._photos
    
    @property
    def groups(self) -> List[PhotoGroup]:
        return self._groups
    
    @property
    def total_count(self) -> int:
        return len(self._photos)
    
    @property
    def selected_count(self) -> int:
        return sum(1 for p in self._photos if p.is_selected)
    
    @property
    def selected_photos(self) -> List[Photo]:
        return [p for p in self._photos if p.is_selected]
    
    def set_photos(self, photos: List[Photo]):
        """Set the photos to be grouped."""
        self._photos = photos
        self._regroup()
    
    def add_photos(self, photos: List[Photo]):
        """Add more photos to the collection."""
        self._photos.extend(photos)
        self._regroup()
    
    def clear(self):
        """Clear all photos."""
        self._photos.clear()
        self._groups.clear()
    
    def set_strategy(self, strategy: SortingStrategy):
        """Set the sorting strategy and regroup."""
        self._current_strategy = strategy
        self._regroup()
    
    def set_sort_ascending(self, ascending: bool):
        """Set the sort order and regroup."""
        self._sort_ascending = ascending
        self._regroup()
    
    @property
    def sort_ascending(self) -> bool:
        return self._sort_ascending
    
    def _regroup(self):
        """Regroup photos using current strategy."""
        if not self._current_strategy or not self._photos:
            self._groups = []
            return
        
        # Sort photos into groups
        grouped = self._current_strategy.sort(self._photos)
        
        # Get sorted keys
        sorted_keys = self._current_strategy.get_sorted_group_keys(grouped)
        
        # Create PhotoGroup objects
        self._groups = []
        for key in sorted_keys:
            photos = grouped[key]
            
            # Sort photos within group by date
            photos = sorted(photos, key=lambda p: p.date_for_sorting, reverse=not self._sort_ascending)
            
            # Get display name (use get_display_name if available)
            if hasattr(self._current_strategy, 'get_display_name'):
                display_name = self._current_strategy.get_display_name(key)
            else:
                display_name = key
            
            group = PhotoGroup(
                key=key,
                display_name=display_name,
                folder_name=self._current_strategy.get_folder_name(key),
                photos=photos
            )
            self._groups.append(group)
    
    def select_all(self):
        """Select all photos."""
        for photo in self._photos:
            photo.is_selected = True
    
    def deselect_all(self):
        """Deselect all photos."""
        for photo in self._photos:
            photo.is_selected = False
    
    def get_group_for_photo(self, photo: Photo) -> Optional[PhotoGroup]:
        """Find the group containing a photo."""
        for group in self._groups:
            if photo in group.photos:
                return group
        return None

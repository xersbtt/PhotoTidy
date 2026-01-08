"""
Compound sorting strategy - combines multiple sorting criteria.
"""
from typing import Dict, List, Tuple
from core.photo import Photo
from .base import SortingStrategy
from .date_sorter import DateSorter
from .location_sorter import LocationSorter


class CompoundSorter(SortingStrategy):
    """Sort photos by multiple criteria (e.g., location then date or date then location)."""
    
    # Compound modes
    LOCATION_THEN_DATE = 'location_date'  # Sydney, Australia/2024/January
    DATE_THEN_LOCATION = 'date_location'  # 2024/January/Sydney, Australia
    
    def __init__(
        self, 
        mode: str = DATE_THEN_LOCATION,
        date_sorter: DateSorter = None,
        location_sorter: LocationSorter = None
    ):
        """
        Initialize compound sorter.
        
        Args:
            mode: Either LOCATION_THEN_DATE or DATE_THEN_LOCATION
            date_sorter: Optional DateSorter instance
            location_sorter: Optional LocationSorter instance
        """
        self.mode = mode
        self.date_sorter = date_sorter or DateSorter()
        self.location_sorter = location_sorter or LocationSorter()
    
    @property
    def name(self) -> str:
        if self.mode == self.LOCATION_THEN_DATE:
            return "Location → Date"
        else:
            return "Date → Location"
    
    @property
    def description(self) -> str:
        if self.mode == self.LOCATION_THEN_DATE:
            return "Sort by location first, then by date within each location"
        else:
            return "Sort by date first, then by location within each date"
    
    def get_group_key(self, photo: Photo) -> str:
        """Get compound group key."""
        date_key = self.date_sorter.get_group_key(photo)
        location_key = self.location_sorter.get_group_key(photo)
        
        if self.mode == self.LOCATION_THEN_DATE:
            return f"{location_key}|{date_key}"
        else:
            return f"{date_key}|{location_key}"
    
    def get_folder_name(self, group_key: str) -> str:
        """Convert compound group key to folder path."""
        parts = group_key.split('|')
        if len(parts) != 2:
            return group_key
        
        if self.mode == self.LOCATION_THEN_DATE:
            location_folder = self.location_sorter.get_folder_name(parts[0])
            date_folder = self.date_sorter.get_folder_name(parts[1])
            return f"{location_folder}/{date_folder}"
        else:
            date_folder = self.date_sorter.get_folder_name(parts[0])
            location_folder = self.location_sorter.get_folder_name(parts[1])
            return f"{date_folder}/{location_folder}"
    
    def get_display_name(self, group_key: str) -> str:
        """Get display-friendly name for the compound group."""
        parts = group_key.split('|')
        if len(parts) != 2:
            return group_key
        
        if self.mode == self.LOCATION_THEN_DATE:
            location_name = parts[0]
            date_name = self.date_sorter.get_display_name(parts[1])
            return f"{location_name} • {date_name}"
        else:
            date_name = self.date_sorter.get_display_name(parts[0])
            location_name = parts[1]
            return f"{date_name} • {location_name}"
    
    def get_sorted_group_keys(self, groups: Dict[str, List[Photo]]) -> List[str]:
        """Sort compound keys appropriately."""
        keys = list(groups.keys())
        
        # Sort by primary key first, then secondary
        def sort_key(key: str) -> Tuple[str, str]:
            parts = key.split('|')
            if len(parts) != 2:
                return (key, "")
            
            if self.mode == self.LOCATION_THEN_DATE:
                # Location alphabetical, then date reverse chronological
                location = parts[0]
                date = parts[1]
                # Use negative date for reverse chronological
                return (location, self._invert_date_key(date))
            else:
                # Date reverse chronological, then location alphabetical
                date = parts[0]
                location = parts[1]
                return (self._invert_date_key(date), location)
        
        return sorted(keys, key=sort_key)
    
    def _invert_date_key(self, date_key: str) -> str:
        """Invert date key for reverse sorting (newest first)."""
        # Date keys are like "2024/01" - invert for reverse sort
        try:
            parts = date_key.split('/')
            inverted = [str(9999 - int(p)) for p in parts]
            return '/'.join(inverted)
        except (ValueError, AttributeError):
            return date_key
    
    def resolve_all_locations(self, photos: List[Photo], progress_callback=None):
        """Pre-resolve all location names for photos with GPS data."""
        self.location_sorter.resolve_locations(photos, progress_callback)

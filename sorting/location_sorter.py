"""
Location-based sorting strategy.
"""
from typing import Dict, List, Optional
from core.photo import Photo
from core.geocoding import GeocodingService
from .base import SortingStrategy


class LocationSorter(SortingStrategy):
    """Sort photos by GPS location."""
    
    # Format options
    FORMAT_COUNTRY = 'country'
    FORMAT_CITY = 'city'
    FORMAT_CITY_COUNTRY = 'city_country'
    
    UNKNOWN_LOCATION = "Unknown Location"
    
    def __init__(
        self, 
        format_type: str = FORMAT_CITY_COUNTRY,
        geocoding_service: Optional[GeocodingService] = None
    ):
        """
        Initialize location sorter.
        
        Args:
            format_type: One of FORMAT_COUNTRY, FORMAT_CITY, FORMAT_CITY_COUNTRY
            geocoding_service: Optional geocoding service (creates one if not provided)
        """
        self.format_type = format_type
        self._geocoding = geocoding_service or GeocodingService()
    
    @property
    def name(self) -> str:
        return "Location"
    
    @property
    def description(self) -> str:
        return "Sort photos by the location where they were taken"
    
    def get_group_key(self, photo: Photo) -> str:
        """Get location-based group key."""
        # Check manually set location name first (for photos without GPS)
        if photo.location_name:
            return photo.location_name
        
        # No GPS data
        if not photo.has_location:
            return self.UNKNOWN_LOCATION
        
        # Look up location via geocoding
        location = self._geocoding.get_location_name(
            photo.gps_latitude,
            photo.gps_longitude,
            self.format_type
        )
        
        if location:
            # Cache the result on the photo
            photo.location_name = location
            return location
        
        return self.UNKNOWN_LOCATION
    
    def get_folder_name(self, group_key: str) -> str:
        """Convert group key to folder name (sanitized for filesystem)."""
        # Replace characters that are invalid in folder names
        sanitized = group_key.replace('/', '-').replace('\\', '-')
        sanitized = sanitized.replace(':', '-').replace('*', '').replace('?', '')
        sanitized = sanitized.replace('"', '').replace('<', '').replace('>', '')
        sanitized = sanitized.replace('|', '-')
        return sanitized.strip()
    
    def get_sorted_group_keys(self, groups: Dict[str, List[Photo]]) -> List[str]:
        """Sort keys alphabetically, with Unknown Location at the end."""
        keys = list(groups.keys())
        
        # Sort alphabetically
        keys.sort()
        
        # Move Unknown Location to the end
        if self.UNKNOWN_LOCATION in keys:
            keys.remove(self.UNKNOWN_LOCATION)
            keys.append(self.UNKNOWN_LOCATION)
        
        return keys
    
    def resolve_locations(self, photos: List[Photo], progress_callback=None) -> None:
        """
        Pre-resolve location names for all photos with GPS data.
        This is useful for batch processing to show progress.
        
        Args:
            photos: List of photos to process
            progress_callback: Optional callback(current, total) for progress
        """
        photos_with_gps = [p for p in photos if p.has_location and not p.location_name]
        
        for i, photo in enumerate(photos_with_gps):
            location = self._geocoding.get_location_name(
                photo.gps_latitude,
                photo.gps_longitude,
                self.format_type
            )
            if location:
                photo.location_name = location
            
            if progress_callback:
                progress_callback(i + 1, len(photos_with_gps))

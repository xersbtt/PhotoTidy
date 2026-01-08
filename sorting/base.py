"""
Abstract base class for sorting strategies.
"""
from abc import ABC, abstractmethod
from typing import Dict, List
from core.photo import Photo


class SortingStrategy(ABC):
    """Abstract base class for photo sorting strategies."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name of the sorting strategy."""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Description of how this strategy sorts photos."""
        pass
    
    @abstractmethod
    def get_group_key(self, photo: Photo) -> str:
        """
        Get the group key for a photo.
        
        Args:
            photo: The photo to categorize
            
        Returns:
            A string key representing the group
        """
        pass
    
    @abstractmethod
    def get_folder_name(self, group_key: str) -> str:
        """
        Convert a group key to a folder name.
        
        Args:
            group_key: The group key
            
        Returns:
            Folder name/path for this group
        """
        pass
    
    def sort(self, photos: List[Photo]) -> Dict[str, List[Photo]]:
        """
        Sort photos into groups.
        
        Args:
            photos: List of photos to sort
            
        Returns:
            Dictionary mapping group keys to lists of photos
        """
        groups: Dict[str, List[Photo]] = {}
        
        for photo in photos:
            key = self.get_group_key(photo)
            if key not in groups:
                groups[key] = []
            groups[key].append(photo)
        
        return groups
    
    def get_sorted_group_keys(self, groups: Dict[str, List[Photo]]) -> List[str]:
        """
        Get group keys in sorted order.
        Override this for custom sorting (e.g., date descending).
        
        Args:
            groups: Dictionary of groups
            
        Returns:
            List of keys in display order
        """
        return sorted(groups.keys())

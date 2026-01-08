"""
Dynamic compound sorting strategy - combines any number of sorting criteria.
"""
from typing import Dict, List, Optional
from core.photo import Photo
from .base import SortingStrategy


class DynamicCompoundSorter(SortingStrategy):
    """
    Dynamically combine multiple sorting strategies.
    
    Creates hierarchical grouping based on the order of strategies provided.
    For example: [DateSorter, LocationSorter] creates groups like:
    "2024/01/08|Sydney, Australia"
    """
    
    SEPARATOR = " | "
    PATH_SEPARATOR = "/"
    
    def __init__(self, strategies: List[SortingStrategy] = None, ascending: bool = True):
        """
        Initialize with a list of sorting strategies.
        
        Args:
            strategies: List of SortingStrategy instances in priority order
            ascending: Sort order for date-based keys
        """
        self.strategies = strategies or []
        self.ascending = ascending
    
    @property
    def name(self) -> str:
        if not self.strategies:
            return "None"
        return " → ".join(s.name for s in self.strategies)
    
    @property
    def description(self) -> str:
        if not self.strategies:
            return "No grouping applied"
        return f"Group by {self.name}"
    
    def get_group_key(self, photo: Photo) -> str:
        """Get compound group key from all strategies."""
        if not self.strategies:
            return "All Photos"
        
        keys = [s.get_group_key(photo) for s in self.strategies]
        return self.SEPARATOR.join(keys)
    
    def get_folder_name(self, group_key: str) -> str:
        """Convert compound group key to folder path."""
        if not self.strategies:
            return ""
        
        parts = group_key.split(self.SEPARATOR)
        folder_parts = []
        
        for i, strategy in enumerate(self.strategies):
            if i < len(parts):
                folder_name = strategy.get_folder_name(parts[i])
                folder_parts.append(folder_name)
        
        return self.PATH_SEPARATOR.join(folder_parts)
    
    def get_display_name(self, group_key: str) -> str:
        """Get display-friendly name for the compound group."""
        if not self.strategies:
            return "All Photos"
        
        parts = group_key.split(self.SEPARATOR)
        display_parts = []
        
        for i, strategy in enumerate(self.strategies):
            if i < len(parts):
                if hasattr(strategy, 'get_display_name'):
                    display_parts.append(strategy.get_display_name(parts[i]))
                else:
                    display_parts.append(parts[i])
        
        return " • ".join(display_parts)
    
    def get_sorted_group_keys(self, groups: Dict[str, List[Photo]]) -> List[str]:
        """Sort compound keys by primary key, then secondary, etc."""
        keys = list(groups.keys())
        
        def sort_key(key: str):
            parts = key.split(self.SEPARATOR)
            result = []
            
            for i, strategy in enumerate(self.strategies):
                if i < len(parts):
                    part = parts[i]
                    # Check if strategy has ascending attribute
                    if hasattr(strategy, 'ascending'):
                        # For date-like keys, invert for descending
                        if not strategy.ascending:
                            result.append(self._invert_for_descending(part))
                        else:
                            result.append(part)
                    else:
                        result.append(part)
                else:
                    result.append("")
            
            return tuple(result)
        
        return sorted(keys, key=sort_key)
    
    def _invert_for_descending(self, key: str) -> str:
        """Invert a key for descending sort."""
        # Try to invert numeric parts for reverse chronological
        try:
            parts = key.split('/')
            inverted = []
            for p in parts:
                if p.isdigit():
                    inverted.append(str(9999 - int(p)))
                else:
                    inverted.append(p)
            return '/'.join(inverted)
        except:
            return key
    
    def set_strategies(self, strategies: List[SortingStrategy]):
        """Update the list of strategies."""
        self.strategies = strategies
    
    def set_ascending(self, ascending: bool):
        """Set the ascending order for all strategies that support it."""
        self.ascending = ascending
        for strategy in self.strategies:
            if hasattr(strategy, 'ascending'):
                strategy.ascending = ascending

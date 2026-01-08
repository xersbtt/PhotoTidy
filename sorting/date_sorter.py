"""
Date-based sorting strategy.
"""
from typing import Dict, List
from core.photo import Photo
from .base import SortingStrategy


class DateSorter(SortingStrategy):
    """Sort photos by date taken."""
    
    # Format options
    FORMAT_YEAR = 'year'
    FORMAT_YEAR_MONTH = 'year_month'
    FORMAT_YEAR_MONTH_DAY = 'year_month_day'
    
    MONTH_NAMES = [
        '', 'January', 'February', 'March', 'April', 'May', 'June',
        'July', 'August', 'September', 'October', 'November', 'December'
    ]
    
    def __init__(self, format_type: str = FORMAT_YEAR_MONTH, ascending: bool = True):
        """
        Initialize date sorter.
        
        Args:
            format_type: One of FORMAT_YEAR, FORMAT_YEAR_MONTH, FORMAT_YEAR_MONTH_DAY
            ascending: If True, oldest dates first; if False, newest first
        """
        self.format_type = format_type
        self.ascending = ascending
    
    @property
    def name(self) -> str:
        return "Date"
    
    @property
    def description(self) -> str:
        return "Sort photos by the date they were taken"
    
    def get_group_key(self, photo: Photo) -> str:
        """Get date-based group key."""
        date = photo.date_for_sorting
        
        if self.format_type == self.FORMAT_YEAR:
            return str(date.year)
        elif self.format_type == self.FORMAT_YEAR_MONTH:
            return f"{date.year}/{date.month:02d}"
        elif self.format_type == self.FORMAT_YEAR_MONTH_DAY:
            return f"{date.year}/{date.month:02d}/{date.day:02d}"
        else:
            return str(date.year)
    
    def get_folder_name(self, group_key: str) -> str:
        """Convert group key to a human-readable folder name."""
        parts = group_key.split('/')
        
        if len(parts) == 1:
            # Year only
            return parts[0]
        elif len(parts) == 2:
            # Year/Month
            year, month = parts
            month_name = self.MONTH_NAMES[int(month)]
            return f"{year}/{month_name}"
        elif len(parts) == 3:
            # Year/Month/Day
            year, month, day = parts
            month_name = self.MONTH_NAMES[int(month)]
            return f"{year}/{month_name}/{day}"
        else:
            return group_key
    
    def get_sorted_group_keys(self, groups: Dict[str, List[Photo]]) -> List[str]:
        """Sort keys chronologically based on ascending setting."""
        return sorted(groups.keys(), reverse=not self.ascending)
    
    def get_display_name(self, group_key: str) -> str:
        """Get a display-friendly name for the group."""
        parts = group_key.split('/')
        
        if len(parts) == 1:
            return parts[0]
        elif len(parts) == 2:
            year, month = parts
            month_name = self.MONTH_NAMES[int(month)]
            return f"{month_name} {year}"
        elif len(parts) == 3:
            year, month, day = parts
            month_name = self.MONTH_NAMES[int(month)]
            return f"{month_name} {int(day)}, {year}"
        else:
            return group_key

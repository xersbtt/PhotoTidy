"""
Geocoding service for converting GPS coordinates to location names.
Uses Nominatim (OpenStreetMap) with caching.
"""
import json
import time
import logging
from pathlib import Path
from typing import Optional, Tuple
from threading import Lock

from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError

from config import GEOCODING_CACHE_FILE, GEOCODING_USER_AGENT, GEOCODING_RATE_LIMIT_SECONDS

logger = logging.getLogger(__name__)


class GeocodingService:
    """Service for reverse geocoding GPS coordinates to location names."""
    
    def __init__(self, cache_file: Path = GEOCODING_CACHE_FILE):
        self.cache_file = cache_file
        self.cache: dict = {}
        self._lock = Lock()
        self._last_request_time = 0.0
        
        # Initialize Nominatim geocoder
        self.geocoder = Nominatim(user_agent=GEOCODING_USER_AGENT, timeout=10)
        
        # Load cache from disk
        self._load_cache()
    
    def get_location_name(
        self, 
        latitude: float, 
        longitude: float,
        format_type: str = 'city_country'
    ) -> Optional[str]:
        """
        Get location name for GPS coordinates.
        
        Args:
            latitude: GPS latitude
            longitude: GPS longitude
            format_type: 'country', 'city', 'city_country', or 'full'
            
        Returns:
            Formatted location name or None if lookup fails
        """
        # Round coordinates to reduce cache misses (approx 1km precision)
        cache_key = f"{round(latitude, 2)},{round(longitude, 2)}"
        
        # Check cache first
        with self._lock:
            if cache_key in self.cache:
                cached = self.cache[cache_key]
                return self._format_location(cached, format_type)
        
        # Rate limiting for Nominatim
        self._rate_limit()
        
        try:
            location = self.geocoder.reverse(f"{latitude}, {longitude}", language='en')
            
            if location and location.raw.get('address'):
                address = location.raw['address']
                
                # Cache the result
                with self._lock:
                    self.cache[cache_key] = address
                    self._save_cache()
                
                return self._format_location(address, format_type)
                
        except (GeocoderTimedOut, GeocoderServiceError) as e:
            logger.warning(f"Geocoding failed for ({latitude}, {longitude}): {e}")
        except Exception as e:
            logger.error(f"Unexpected geocoding error: {e}")
        
        return None
    
    def _format_location(self, address: dict, format_type: str) -> str:
        """Format address dictionary based on format type."""
        # Suburb/locality first (for Australian addresses), then city, town, village, etc.
        suburb = address.get('suburb') or address.get('neighbourhood') or address.get('locality')
        city = (
            address.get('city') or 
            address.get('town') or 
            address.get('village') or
            address.get('municipality') or
            address.get('county', '')
        )
        state = address.get('state', '')
        country = address.get('country', '')
        
        # Use suburb if available, otherwise fall back to city
        local_area = suburb or city
        
        if format_type == 'country':
            return country or 'Unknown'
        elif format_type == 'suburb':
            return suburb or city or country or 'Unknown'
        elif format_type == 'city':
            return city or suburb or country or 'Unknown'
        elif format_type == 'suburb_country':
            if local_area and country:
                return f"{local_area}, {country}"
            return local_area or country or 'Unknown'
        elif format_type == 'city_country':
            if city and country:
                return f"{city}, {country}"
            return city or country or 'Unknown'
        elif format_type == 'full':
            parts = [p for p in [local_area, state, country] if p]
            return ', '.join(parts) or 'Unknown'
        else:
            return local_area or country or 'Unknown'
    
    def _rate_limit(self):
        """Enforce rate limiting for Nominatim."""
        with self._lock:
            elapsed = time.time() - self._last_request_time
            if elapsed < GEOCODING_RATE_LIMIT_SECONDS:
                time.sleep(GEOCODING_RATE_LIMIT_SECONDS - elapsed)
            self._last_request_time = time.time()
    
    def _load_cache(self):
        """Load geocoding cache from disk."""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    self.cache = json.load(f)
                logger.info(f"Loaded {len(self.cache)} geocoding cache entries")
            except Exception as e:
                logger.warning(f"Failed to load geocoding cache: {e}")
                self.cache = {}
    
    def _save_cache(self):
        """Save geocoding cache to disk."""
        try:
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save geocoding cache: {e}")
    
    def clear_cache(self):
        """Clear the geocoding cache."""
        with self._lock:
            self.cache = {}
            if self.cache_file.exists():
                self.cache_file.unlink()

"""
Pokemon image caching for the GUI.

Downloads and caches Pokemon images locally to avoid
repeated network requests.
"""

import hashlib
import logging
import os
from pathlib import Path
from typing import Dict, Optional
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

from PyQt6.QtGui import QPixmap, QImage
from PyQt6.QtCore import Qt, QByteArray

logger = logging.getLogger(__name__)


class PokemonImageCache:
    """
    Caches Pokemon images locally and provides QPixmap objects for display.
    
    Images are stored in a cache directory and loaded from there on subsequent
    requests. Failed downloads result in None being returned.
    """
    
    def __init__(self, cache_dir: Optional[Path] = None):
        """
        Initialize the image cache.
        
        Args:
            cache_dir: Directory to store cached images. Defaults to 
                       ~/.monopoly_pokemon_cache/
        """
        if cache_dir is None:
            cache_dir = Path.home() / ".monopoly_pokemon_cache"
        
        self._cache_dir = cache_dir
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        
        # In-memory cache of loaded pixmaps
        self._pixmap_cache: Dict[str, QPixmap] = {}
        
        # Track failed URLs to avoid repeated attempts
        self._failed_urls: set = set()
    
    def _url_to_filename(self, url: str) -> str:
        """Convert a URL to a safe filename."""
        # Use hash of URL to create unique filename
        url_hash = hashlib.md5(url.encode()).hexdigest()
        # Extract file extension from URL
        ext = ".png"
        if "." in url.split("/")[-1]:
            ext = "." + url.split(".")[-1]
        return f"{url_hash}{ext}"
    
    def _get_cache_path(self, url: str) -> Path:
        """Get the local cache path for a URL."""
        return self._cache_dir / self._url_to_filename(url)
    
    def _download_image(self, url: str) -> Optional[bytes]:
        """
        Download an image from a URL.
        
        Returns:
            Image bytes if successful, None otherwise.
        """
        try:
            request = Request(
                url,
                headers={"User-Agent": "Pokemon-Monopoly-Client/1.0"}
            )
            with urlopen(request, timeout=10) as response:
                return response.read()
        except (URLError, HTTPError, TimeoutError) as e:
            logger.warning(f"Failed to download image from {url}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error downloading {url}: {e}")
            return None
    
    def get_pixmap(
        self, 
        url: str, 
        width: Optional[int] = None, 
        height: Optional[int] = None
    ) -> Optional[QPixmap]:
        """
        Get a QPixmap for a Pokemon image URL.
        
        Downloads and caches the image if not already cached.
        Optionally scales the image to fit the given dimensions.
        
        Args:
            url: The image URL
            width: Optional width to scale to
            height: Optional height to scale to
            
        Returns:
            QPixmap if successful, None if image couldn't be loaded
        """
        if not url:
            return None
        
        # Check if we've already failed to load this URL
        if url in self._failed_urls:
            return None
        
        # Create cache key including size for in-memory cache
        cache_key = f"{url}_{width}_{height}"
        
        # Check in-memory cache first
        if cache_key in self._pixmap_cache:
            return self._pixmap_cache[cache_key]
        
        # Check disk cache
        cache_path = self._get_cache_path(url)
        
        if not cache_path.exists():
            # Download and save to disk cache
            image_data = self._download_image(url)
            if image_data is None:
                self._failed_urls.add(url)
                return None
            
            try:
                cache_path.write_bytes(image_data)
            except Exception as e:
                logger.warning(f"Failed to cache image to {cache_path}: {e}")
                # Continue anyway, we have the data in memory
        
        # Load from disk cache
        try:
            pixmap = QPixmap(str(cache_path))
            
            if pixmap.isNull():
                logger.warning(f"Failed to load pixmap from {cache_path}")
                self._failed_urls.add(url)
                return None
            
            # Scale if dimensions provided
            if width is not None and height is not None:
                pixmap = pixmap.scaled(
                    width, height,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
            elif width is not None:
                pixmap = pixmap.scaledToWidth(
                    width,
                    Qt.TransformationMode.SmoothTransformation
                )
            elif height is not None:
                pixmap = pixmap.scaledToHeight(
                    height,
                    Qt.TransformationMode.SmoothTransformation
                )
            
            # Store in memory cache
            self._pixmap_cache[cache_key] = pixmap
            
            return pixmap
            
        except Exception as e:
            logger.error(f"Error loading pixmap from {cache_path}: {e}")
            self._failed_urls.add(url)
            return None
    
    def preload(self, urls: list) -> None:
        """
        Preload a list of image URLs into the cache.
        
        This is useful for loading all game images at startup.
        """
        for url in urls:
            if url and url not in self._failed_urls:
                cache_path = self._get_cache_path(url)
                if not cache_path.exists():
                    image_data = self._download_image(url)
                    if image_data:
                        try:
                            cache_path.write_bytes(image_data)
                        except Exception as e:
                            logger.warning(f"Failed to cache {url}: {e}")
    
    def clear_memory_cache(self) -> None:
        """Clear the in-memory pixmap cache."""
        self._pixmap_cache.clear()
    
    def clear_disk_cache(self) -> None:
        """Clear the disk cache directory."""
        try:
            for file in self._cache_dir.iterdir():
                file.unlink()
        except Exception as e:
            logger.error(f"Failed to clear disk cache: {e}")


# Singleton instance
_cache_instance: Optional[PokemonImageCache] = None


def get_image_cache() -> PokemonImageCache:
    """Get the singleton image cache instance."""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = PokemonImageCache()
    return _cache_instance

"""
modules/core/model_manager/cache/embedding_cache.py
Embedding result caching system with TTL and memory management.

Extracted from services.py as part of module refactoring.
"""

import logging
import time
import hashlib
from typing import Dict, Any, List, Union
from core.error_utils import Result

# Module identity for logging
MODULE_ID = "core.model_manager.cache"


class EmbeddingCache:
    """Embedding cache with TTL and memory management."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize embedding cache.
        
        Args:
            config: Configuration dictionary with cache settings
        """
        self.config = config
        self.logger = logging.getLogger(f"{MODULE_ID}.embedding_cache")
        
        # Cache storage
        self._embedding_cache: Dict[str, Any] = {}
        self._cache_timestamps: Dict[str, float] = {}
        
        self.logger.info("Embedding cache initialized")
    
    async def get_embeddings(self, texts: Union[str, List[str]], model_id: str) -> Result:
        """Check if embeddings are cached.
        
        Args:
            texts: Text(s) to check for cached embeddings
            model_id: Model ID for cache key generation
            
        Returns:
            Result with cached embeddings or cache miss error
        """
        try:
            if not self.config.get("embedding_cache.enabled", True):
                return Result.error(code="CACHE_DISABLED", message="Cache is disabled")
            
            # Convert single string to list for uniform processing
            text_list = [texts] if isinstance(texts, str) else texts
            
            cached_embeddings = []
            cache_hits = 0
            
            for text in text_list:
                cache_key = self._get_cache_key(text, model_id)
                if cache_key in self._embedding_cache:
                    # Check if cache entry is still valid
                    if self._is_cache_valid(cache_key):
                        cached_embeddings.append(self._embedding_cache[cache_key])
                        cache_hits += 1
                    else:
                        # Cache expired
                        del self._embedding_cache[cache_key]
                        del self._cache_timestamps[cache_key]
                        return Result.error(code="CACHE_MISS", message="Cache expired")
                else:
                    return Result.error(code="CACHE_MISS", message="Not in cache")
            
            # All texts found in cache
            if len(cached_embeddings) == len(text_list):
                return Result.success(data={
                    "embeddings": cached_embeddings[0] if len(cached_embeddings) == 1 else cached_embeddings,
                    "model_id": model_id,
                    "cached": True,
                    "cache_hits": cache_hits
                })
            
            return Result.error(code="PARTIAL_CACHE_HIT", message="Partial cache hit")
            
        except Exception as e:
            self.logger.error(f"Cache lookup error: {e}")
            return Result.error(code="CACHE_ERROR", message="Cache lookup failed")
    
    async def cache_embeddings(self, texts: Union[str, List[str]], embeddings: Union[List[float], List[List[float]]], model_id: str):
        """Cache embeddings for future use.
        
        Args:
            texts: Text(s) that were embedded
            embeddings: Corresponding embedding results
            model_id: Model ID for cache key generation
        """
        try:
            if not self.config.get("embedding_cache.enabled", True):
                return
            
            current_time = time.time()
            max_cache_size = self.config.get("embedding_cache.max_cache_size", 10000)
            
            # Clean old cache entries if needed
            if len(self._embedding_cache) >= max_cache_size:
                await self._cleanup_cache()
            
            # Convert to lists for uniform processing
            text_list = [texts] if isinstance(texts, str) else texts
            embedding_list = [embeddings] if isinstance(embeddings[0] if embeddings else None, (int, float)) else embeddings
            
            for text, embedding in zip(text_list, embedding_list):
                cache_key = self._get_cache_key(text, model_id)
                self._embedding_cache[cache_key] = embedding
                self._cache_timestamps[cache_key] = current_time
            
            self.logger.debug(f"Cached embeddings for {len(text_list)} texts with model {model_id}")
            
        except Exception as e:
            self.logger.warning(f"Failed to cache embeddings: {e}")
    
    def _get_cache_key(self, text: str, model_id: str) -> str:
        """Generate cache key for text and model.
        
        Args:
            text: Input text
            model_id: Model identifier
            
        Returns:
            Cache key string
        """
        combined = f"{model_id}:{text}"
        return hashlib.md5(combined.encode('utf-8')).hexdigest()
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cache entry is still valid.
        
        Args:
            cache_key: Key to check
            
        Returns:
            True if cache entry is valid
        """
        if cache_key not in self._cache_timestamps:
            return False
        
        ttl = self.config.get("embedding_cache.ttl_seconds", 3600)
        return (time.time() - self._cache_timestamps[cache_key]) < ttl
    
    async def _cleanup_cache(self):
        """Clean up old cache entries."""
        try:
            current_time = time.time()
            ttl = self.config.get("embedding_cache.ttl_seconds", 3600)
            
            # Find expired entries
            expired_keys = [
                key for key, timestamp in self._cache_timestamps.items()
                if (current_time - timestamp) > ttl
            ]
            
            # Remove expired entries
            for key in expired_keys:
                del self._embedding_cache[key]
                del self._cache_timestamps[key]
            
            self.logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")
            
        except Exception as e:
            self.logger.warning(f"Cache cleanup failed: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get cache status information.
        
        Returns:
            Cache status dictionary
        """
        return {
            "enabled": self.config.get("embedding_cache.enabled", True),
            "cache_size": len(self._embedding_cache),
            "max_cache_size": self.config.get("embedding_cache.max_cache_size", 10000),
            "ttl_seconds": self.config.get("embedding_cache.ttl_seconds", 3600)
        }
    
    def clear_cache(self):
        """Clear all cached entries."""
        self._embedding_cache.clear()
        self._cache_timestamps.clear()
        self.logger.info("Embedding cache cleared")
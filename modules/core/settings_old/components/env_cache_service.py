"""
modules/core/settings/components/env_cache_service.py
Updated: April 4, 2025
Provides TTL-based caching for environment variables with standardized error handling
"""

import os
import time
import logging
from typing import Dict, Any, Optional, Union

from core.error_utils import error_message, Result

# Define MODULE_ID matching manifest.json at the top of the file
MODULE_ID = "core.settings"
# Use module hierarchy for component logger
logger = logging.getLogger(f"{MODULE_ID}.env_cache")

class EnvCacheService:
    """
    Service for efficiently caching environment variables with TTL.
    
    This reduces repeated OS calls for environment variables by caching
    values with a configurable time-to-live (TTL) period.
    """
    
    def __init__(self, ttl: int = 300):
        """
        Initialize the environment cache service.
        
        Args:
            ttl: Cache time-to-live in seconds (default: 5 minutes)
        """
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.ttl = ttl
        self.logger = logger
        self.initialized = True  # This service is always initialized upon creation
        
        self.logger.debug(f"Initialized environment cache with TTL of {ttl} seconds")
    
    async def initialize(self, app_context=None, settings=None) -> bool:
        """
        Initialize the environment cache service.
        
        Args:
            app_context: Optional application context
            settings: Optional pre-loaded settings
            
        Returns:
            True if initialization successful, always True for this service
        """
        return self.initialized
    
    async def get_env_var(self, 
                         env_var: str, 
                         default: Any = None) -> Any:
        """
        Get environment variable with TTL-based caching.
        
        Args:
            env_var: Environment variable name
            default: Default value if not found
            
        Returns:
            Environment variable value or default if not found
        """
        try:
            now = time.time()
            
            # Check if in cache and still valid
            if env_var in self.cache:
                cache_entry = self.cache[env_var]
                
                # If entry is still valid, return cached value
                if now - cache_entry["timestamp"] < self.ttl:
                    return cache_entry["value"]
                else:
                    # Log that we're refreshing a stale value
                    self.logger.debug(f"Cache entry for {env_var} is stale, refreshing")
            
            # Get fresh value
            value = os.environ.get(env_var, default)
            
            # Store in cache
            self.cache[env_var] = {
                "value": value,
                "timestamp": now
            }
            
            return value
        except Exception as e:
            self.logger.error(error_message(
                module_id=MODULE_ID,
                error_type="ENV_VAR_ERROR",
                details=f"Error getting environment variable {env_var}: {str(e)}",
                location="get_env_var()"
            ))
            return default
    
    async def get_env_vars_by_prefix(self, 
                                    prefix: str, 
                                    strip_prefix: bool = False) -> Result:
        """
        Get all environment variables with a given prefix.
        
        Args:
            prefix: Prefix to filter environment variables
            strip_prefix: If True, remove prefix from keys in result
            
        Returns:
            Result with dictionary of environment variables with prefix
        """
        try:
            result = {}
            
            # Get all environment variables
            for env_var in os.environ:
                if env_var.startswith(prefix):
                    # Get value with caching
                    value = await self.get_env_var(env_var)
                    
                    # Add to result, optionally stripping prefix
                    if strip_prefix:
                        key = env_var[len(prefix):]
                    else:
                        key = env_var
                        
                    result[key] = value
            
            return Result.success(data=result)
        except Exception as e:
            self.logger.error(error_message(
                module_id=MODULE_ID,
                error_type="ENV_VARS_BY_PREFIX_ERROR",
                details=f"Error getting environment variables with prefix {prefix}: {str(e)}",
                location="get_env_vars_by_prefix()"
            ))
            return Result.error(
                code="ENV_VARS_BY_PREFIX_ERROR",
                message=f"Error getting environment variables with prefix {prefix}",
                details={"error": str(e)}
            )
    
    async def get_by_module_prefix(self, 
                                  module_id: str, 
                                  setting_keys: Optional[list] = None) -> Result:
        """
        Get environment variables for a specific module.
        
        Handles the common pattern of MODULE_ID_SETTING_NAME for environment variables.
        
        Args:
            module_id: Module identifier (e.g., 'core.database')
            setting_keys: Optional list of specific setting keys to check
            
        Returns:
            Result with dictionary of environment variables for the module
        """
        try:
            # Convert module_id to environment variable prefix format
            env_prefix = module_id.replace(".", "_").upper() + "_"
            
            # Get all environment variables with this prefix
            if setting_keys is None:
                # Get all vars with this prefix
                result = await self.get_env_vars_by_prefix(env_prefix, strip_prefix=True)
                return result
            else:
                # Get only specific vars
                result = {}
                for key in setting_keys:
                    env_var = env_prefix + key.upper()
                    value = await self.get_env_var(env_var)
                    if value is not None:
                        result[key] = value
                return Result.success(data=result)
        except Exception as e:
            self.logger.error(error_message(
                module_id=MODULE_ID,
                error_type="MODULE_ENV_VARS_ERROR",
                details=f"Error getting environment variables for module {module_id}: {str(e)}",
                location="get_by_module_prefix()"
            ))
            return Result.error(
                code="MODULE_ENV_VARS_ERROR",
                message=f"Error getting environment variables for module {module_id}",
                details={"error": str(e)}
            )
    
    async def clear_cache(self) -> Result:
        """
        Clear the entire cache.
        
        Useful for testing or when environment variables have changed.
        
        Returns:
            Result indicating success or failure
        """
        try:
            cache_size = len(self.cache)
            self.cache.clear()
            self.logger.debug("Environment variable cache cleared")
            return Result.success(data={"cleared_entries": cache_size})
        except Exception as e:
            self.logger.error(error_message(
                module_id=MODULE_ID,
                error_type="CLEAR_CACHE_ERROR",
                details=f"Error clearing environment variable cache: {str(e)}",
                location="clear_cache()"
            ))
            return Result.error(
                code="CLEAR_CACHE_ERROR",
                message="Error clearing environment variable cache",
                details={"error": str(e)}
            )
    
    async def set_ttl(self, ttl: int) -> Result:
        """
        Update the cache TTL.
        
        Args:
            ttl: New cache time-to-live in seconds
            
        Returns:
            Result indicating success or failure
        """
        try:
            old_ttl = self.ttl
            self.ttl = ttl
            self.logger.debug(f"Environment cache TTL updated from {old_ttl} to {ttl} seconds")
            
            # Clear cache after TTL change to avoid confusion
            await self.clear_cache()
            
            return Result.success(data={"old_ttl": old_ttl, "new_ttl": ttl})
        except Exception as e:
            self.logger.error(error_message(
                module_id=MODULE_ID,
                error_type="SET_TTL_ERROR",
                details=f"Error updating cache TTL: {str(e)}",
                location="set_ttl()"
            ))
            return Result.error(
                code="SET_TTL_ERROR",
                message="Error updating cache TTL",
                details={"error": str(e)}
            )
    
    async def refresh(self, env_var: str) -> Result:
        """
        Force refresh a specific environment variable in the cache.
        
        Args:
            env_var: Environment variable name
            
        Returns:
            Result with fresh environment variable value
        """
        try:
            # Remove from cache if exists
            if env_var in self.cache:
                del self.cache[env_var]
                
            # Get fresh value (which will add to cache)
            value = await self.get_env_var(env_var)
            
            return Result.success(data={"env_var": env_var, "value": value})
        except Exception as e:
            self.logger.error(error_message(
                module_id=MODULE_ID,
                error_type="REFRESH_ERROR",
                details=f"Error refreshing environment variable {env_var}: {str(e)}",
                location="refresh()"
            ))
            return Result.error(
                code="REFRESH_ERROR",
                message=f"Error refreshing environment variable {env_var}",
                details={"env_var": env_var, "error": str(e)}
            )
    
    async def get_stats(self) -> Result:
        """
        Get statistics about the cache.
        
        Returns:
            Result with cache statistics
        """
        try:
            now = time.time()
            
            # Count valid and stale entries
            valid_entries = 0
            stale_entries = 0
            
            for env_var, entry in self.cache.items():
                if now - entry["timestamp"] < self.ttl:
                    valid_entries += 1
                else:
                    stale_entries += 1
                    
            stats = {
                "cache_size": len(self.cache),
                "valid_entries": valid_entries,
                "stale_entries": stale_entries,
                "ttl": self.ttl
            }
            
            return Result.success(data=stats)
        except Exception as e:
            self.logger.error(error_message(
                module_id=MODULE_ID,
                error_type="GET_STATS_ERROR",
                details=f"Error getting cache statistics: {str(e)}",
                location="get_stats()"
            ))
            return Result.error(
                code="GET_STATS_ERROR",
                message="Error getting cache statistics",
                details={"error": str(e)}
            )

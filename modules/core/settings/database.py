"""
modules/core/settings/database.py
Database operations for Settings - User preferences management.

Simple, focused operations for the minimal user_preferences table.
Follows the clean architecture from docs/v2/settings_v2.md
"""

import json
import logging
import contextlib
from typing import Dict, Any, Optional, AsyncGenerator, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from core.error_utils import Result, error_message

from .db_models import UserPreferences

MODULE_ID = "core.settings"
logger = logging.getLogger(f"{MODULE_ID}.database")

class UserPreferencesDatabase:
    """
    Database operations for user preferences.
    
    Simple operations for the single user_preferences table:
    - Get user preferences for a module
    - Set user preference override
    - Clear user preference override
    """
    
    def __init__(self, database_service, crud_service):
        """Initialize with services provided by the module."""
        self.database_service = database_service
        self.crud_service = crud_service
        self.initialized = False
        self.logger = logger
        
    async def initialize(self) -> bool:
        """Initialize database operations."""
        if self.initialized:
            return True
            
        if not self.database_service or not self.database_service.initialized:
            logger.warning(error_message(
                module_id=MODULE_ID,
                error_type="DB_SERVICE_UNAVAILABLE",
                details="Database service not available",
                location="initialize()"
            ))
            return False
        
        if not self.crud_service:
            logger.warning(error_message(
                module_id=MODULE_ID,
                error_type="CRUD_SERVICE_UNAVAILABLE",
                details="CRUD service not available",
                location="initialize()"
            ))
            return False
        
        self.initialized = True
        logger.info("User preferences database operations initialized")
        return True
    
    @contextlib.asynccontextmanager
    async def _db_session(self, database_name: str = "settings") -> AsyncGenerator[AsyncSession, None]:
        """Get database session for specified database using Phase 4 integrity pattern."""
        if not self.initialized and not await self.initialize():
            raise RuntimeError("Database operations not initialized")
        
        # Phase 4: Use new integrity_session pattern via app_context
        # This eliminates deprecation warnings and provides cleaner access
        async with self.database_service.integrity_session(database_name, "user_preferences") as session:
            yield session
    
    async def get_user_preferences(self, module_id: str, database_name: str, user_id: str = 'default') -> Result:
        """
        Get all user preferences for a module.
        
        Args:
            module_id: Module identifier (e.g., "core.model_manager")
            user_id: User identifier (default: 'default')
            database_name: Database to read from (default: 'settings')
            
        Returns:
            Result with dict of setting_key -> value
        """
        try:
            async with self._db_session(database_name) as session:
                # Query user preferences for this module
                stmt = select(UserPreferences).where(
                    UserPreferences.module_id == module_id,
                    UserPreferences.user_id == user_id
                )
                result = await session.execute(stmt)
                preferences = result.scalars().all()
                
                # Convert to dict with JSON deserialization
                user_prefs = {}
                for pref in preferences:
                    try:
                        user_prefs[pref.setting_key] = json.loads(pref.value)
                    except json.JSONDecodeError:
                        logger.warning(f"Invalid JSON for {module_id}.{pref.setting_key}: {pref.value}")
                        user_prefs[pref.setting_key] = pref.value  # Fallback to string
                
                logger.debug(f"Retrieved {len(user_prefs)} user preferences for {module_id}")
                return Result.success(data=user_prefs)
                
        except Exception as e:
            logger.error(error_message(
                module_id=MODULE_ID,
                error_type="GET_PREFERENCES_ERROR",
                details=f"Error getting preferences for {module_id}: {str(e)}",
                location="get_user_preferences()"
            ))
            return Result.error(
                code="GET_PREFERENCES_FAILED",
                message=f"Failed to get user preferences for {module_id}",
                details={"error": str(e)}
            )
    
    async def set_user_preference(self, module_id: str, setting_key: str, value: Any, database_name: str,
                                user_id: str = 'default', changed_by: str = 'user') -> Result:
        """
        Set or update a user preference.
        
        Args:
            module_id: Module identifier
            setting_key: Setting key
            value: Setting value (will be JSON serialized)
            user_id: User identifier
            changed_by: Who made the change
            database_name: Database to write to (default: 'settings')
            
        Returns:
            Result with preference information
        """
        try:
            # JSON serialize the value
            json_value = json.dumps(value)
            
            async with self._db_session(database_name) as session:
                # Check if preference exists
                stmt = select(UserPreferences).where(
                    UserPreferences.module_id == module_id,
                    UserPreferences.setting_key == setting_key,
                    UserPreferences.user_id == user_id
                )
                result = await session.execute(stmt)
                existing = result.scalar_one_or_none()
                
                if existing:
                    # Update existing preference
                    existing.value = json_value
                    existing.changed_by = changed_by
                    # updated_at will be set automatically by onupdate
                    session.add(existing)
                    action = "updated"
                else:
                    # Create new preference
                    preference = UserPreferences(
                        module_id=module_id,
                        setting_key=setting_key,
                        value=json_value,
                        user_id=user_id,
                        changed_by=changed_by
                    )
                    session.add(preference)
                    action = "created"
                
                await session.commit()
                
                logger.info(f"{action.capitalize()} user preference {module_id}.{setting_key} = {value}")
                
                return Result.success(data={
                    "module_id": module_id,
                    "setting_key": setting_key,
                    "value": value,
                    "action": action
                })
                
        except Exception as e:
            logger.error(error_message(
                module_id=MODULE_ID,
                error_type="SET_PREFERENCE_ERROR",
                details=f"Error setting {module_id}.{setting_key}: {str(e)}",
                location="set_user_preference()"
            ))
            return Result.error(
                code="SET_PREFERENCE_FAILED",
                message=f"Failed to set user preference {module_id}.{setting_key}",
                details={"error": str(e)}
            )
    
    async def clear_user_preference(self, module_id: str, setting_key: str, database_name: str,
                                  user_id: str = 'default') -> Result:
        """
        Clear a user preference (delete the override).
        
        Args:
            module_id: Module identifier
            setting_key: Setting key
            user_id: User identifier
            database_name: Database to delete from (default: 'settings')
            
        Returns:
            Result with success information
        """
        try:
            async with self._db_session(database_name) as session:
                # Delete the preference
                stmt = delete(UserPreferences).where(
                    UserPreferences.module_id == module_id,
                    UserPreferences.setting_key == setting_key,
                    UserPreferences.user_id == user_id
                )
                result = await session.execute(stmt)
                await session.commit()
                
                deleted_count = result.rowcount
                
                if deleted_count > 0:
                    logger.info(f"Cleared user preference {module_id}.{setting_key}")
                    return Result.success(data={
                        "module_id": module_id,
                        "setting_key": setting_key,
                        "cleared": True
                    })
                else:
                    logger.info(f"No user preference found to clear: {module_id}.{setting_key}")
                    return Result.success(data={
                        "module_id": module_id,
                        "setting_key": setting_key,
                        "cleared": False,
                        "reason": "not_found"
                    })
                
        except Exception as e:
            logger.error(error_message(
                module_id=MODULE_ID,
                error_type="CLEAR_PREFERENCE_ERROR",
                details=f"Error clearing {module_id}.{setting_key}: {str(e)}",
                location="clear_user_preference()"
            ))
            return Result.error(
                code="CLEAR_PREFERENCE_FAILED",
                message=f"Failed to clear user preference {module_id}.{setting_key}",
                details={"error": str(e)}
            )
    
    async def get_all_user_preferences(self, database_name: str, user_id: str = 'default') -> Result:
        """
        Get all user preferences across all modules.
        
        Args:
            user_id: User identifier
            database_name: Database to read from (default: 'settings')
            
        Returns:
            Result with dict of module_id -> {setting_key: value}
        """
        try:
            async with self._db_session(database_name) as session:
                stmt = select(UserPreferences).where(UserPreferences.user_id == user_id)
                result = await session.execute(stmt)
                preferences = result.scalars().all()
                
                # Group by module_id
                all_prefs = {}
                for pref in preferences:
                    if pref.module_id not in all_prefs:
                        all_prefs[pref.module_id] = {}
                    
                    try:
                        all_prefs[pref.module_id][pref.setting_key] = json.loads(pref.value)
                    except json.JSONDecodeError:
                        logger.warning(f"Invalid JSON for {pref.module_id}.{pref.setting_key}: {pref.value}")
                        all_prefs[pref.module_id][pref.setting_key] = pref.value
                
                logger.debug(f"Retrieved user preferences for {len(all_prefs)} modules")
                return Result.success(data=all_prefs)
                
        except Exception as e:
            logger.error(error_message(
                module_id=MODULE_ID,
                error_type="GET_ALL_PREFERENCES_ERROR",
                details=f"Error getting all preferences: {str(e)}",
                location="get_all_user_preferences()"
            ))
            return Result.error(
                code="GET_ALL_PREFERENCES_FAILED",
                message="Failed to get all user preferences",
                details={"error": str(e)}
            )
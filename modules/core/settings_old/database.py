"""
modules/core/settings/database.py
Updated: April 4, 2025
Database operations for settings module with standardized error handling
"""

import logging
import asyncio
import contextlib
import traceback
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, AsyncGenerator, TypeVar, Type, Union, Callable
from sqlalchemy.ext.asyncio import AsyncSession

from .db_models import SettingsBackup, SettingsEvent, ScheduledBackup
from core.database import execute_with_retry
from core.error_utils import error_message, Result

# Define MODULE_ID matching manifest.json at the top of the file
MODULE_ID = "core.settings"
# Use MODULE_ID directly for the logger name
logger = logging.getLogger(f"{MODULE_ID}.database")

T = TypeVar('T')  # For generic type hints

class SettingsDatabaseOperations:
    """Database operations for the settings module."""
    
    def __init__(self, app_context):
        """Phase 1: Basic setup only - no service access."""
        self.app_context = app_context
        self.db_service = None      # Will be set in Phase 2
        self.crud_service = None    # Will be set in Phase 2
        self.initialized = False
        self.backup_scheduler_task = None
        self.logger = logger
        
        # Track background tasks for proper shutdown
        self._background_tasks = []
    
    async def initialize(self, app_context=None, settings=None) -> bool:
        """
        Phase 2: Initialize database operations with service access.
        
        Args:
            app_context: Optional application context
            settings: Optional pre-loaded settings
            
        Returns:
            True if initialization successful, False otherwise
        """
        if self.initialized:
            return True
            
        if app_context:
            self.app_context = app_context
        
        # Phase 2: Now it's safe to access other services
        self.db_service = self.app_context.get_service("core.database.service")
        self.crud_service = self.app_context.get_service("core.database.crud_service")
        
        if not self.db_service:
            self.logger.warning(error_message(
                module_id=MODULE_ID,
                error_type="DB_SERVICE_UNAVAILABLE",
                details="Database service not available - backup features disabled",
                location="initialize()"
            ))
            return False
        
        if not self.db_service.initialized:
            self.logger.warning(error_message(
                module_id=MODULE_ID,
                error_type="DB_NOT_INITIALIZED",
                details="Database not initialized - backup features disabled",
                location="initialize()"
            ))
            return False
        
        if not self.crud_service:
            self.logger.warning(error_message(
                module_id=MODULE_ID,
                error_type="CRUD_SERVICE_UNAVAILABLE",
                details="CRUD service not available - backup features disabled",
                location="initialize()"
            ))
            return False
        
        self.initialized = True
        self.logger.info("Settings database operations initialized")
        return True
    
    async def shutdown(self):
        """
        Graceful async shutdown when event loop is available.
        
        Returns:
            None
        """
        self.logger.info(f"Shutting down {MODULE_ID}.database service gracefully...")
        
        # Stop backup scheduler if running
        if self.backup_scheduler_task and not self.backup_scheduler_task.done():
            self.backup_scheduler_task.cancel()
            try:
                await asyncio.wait_for(asyncio.shield(self.backup_scheduler_task), timeout=2.0)
            except (asyncio.TimeoutError, asyncio.CancelledError):
                pass
                
        # Cancel background tasks
        for task in self._background_tasks:
            if not task.done():
                task.cancel()
                try:
                    await asyncio.wait_for(asyncio.shield(task), timeout=2.0)
                except (asyncio.TimeoutError, asyncio.CancelledError):
                    pass
        
        self.logger.info(f"{MODULE_ID}.database service shutdown complete")
    
    def _create_background_task(self, coroutine, name=None):
        """Create a tracked background task with cleanup handling."""
        task = asyncio.create_task(coroutine, name=name)
        
        # Register cleanup callback
        def _task_done_callback(task):
            # Handle task completion
            if task in self._background_tasks:
                self._background_tasks.remove(task)
        
        task.add_done_callback(_task_done_callback)
        self._background_tasks.append(task)
        return task
    
    @contextlib.asynccontextmanager
    async def _db_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Get a database session with initialization check.
        
        Yields:
            Database session
        
        Raises:
            RuntimeError: If database operations not initialized
        """
        if not await self.initialize():
            self.logger.error(error_message(
                module_id=MODULE_ID,
                error_type="DB_NOT_INITIALIZED_SESSION",
                details="Database operations not initialized - cannot create session",
                location="_db_session()"
            ))
            raise RuntimeError("Database operations not initialized")
            
        async with AsyncSession(self.db_service.engine) as session:
            yield session
    
    async def _db_op(self, op: Callable, default: T = None) -> T:
        """
        Execute a database operation with standard error handling.
        
        Args:
            op: Async function to execute
            default: Default value to return on error
            
        Returns:
            Result of operation or default on error
        """
        try:
            return await op()
        except RuntimeError as e:
            self.logger.error(error_message(
                module_id=MODULE_ID,
                error_type="DB_RUNTIME_ERROR",
                details=f"Database runtime error: {str(e)}",
                location="_db_op()"
            ))
            return default
        except Exception as e:
            self.logger.error(error_message(
                module_id=MODULE_ID,
                error_type="DB_OPERATION_ERROR",
                details=f"Database operation error: {str(e)}",
                location="_db_op()"
            ))
            logger.error(traceback.format_exc())
            return default
    
    async def create_backup(self, settings_data: Dict[str, Any], description: Optional[str] = None) -> Result:
        """
        Create a settings backup in the database.
        
        Args:
            settings_data: Settings data to backup
            description: Optional description for backup
            
        Returns:
            Result with backup ID if successful, error if not
        """
        # Check initialization
        if not self.initialized and not await self.initialize():
            return Result.error(
                code="SERVICE_NOT_INITIALIZED",
                message=f"{MODULE_ID}.database service not initialized",
                details={"operation": "create_backup"}
            )
            
        # Prepare version string
        version = "unknown"
        if "_versions" in settings_data:
            version_parts = [f"{m_id}@{ver}" for m_id, ver in settings_data["_versions"].items()]
            if version_parts:
                version = ",".join(version_parts)
        
        # Create backup data
        backup_data = {
            "date_created": datetime.now(),
            "version": version,
            "settings_data": settings_data,
            "description": description or f"Automatic backup - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        }
        
        try:
            async def _create():
                try:
                    async with self._db_session() as session:
                        # Add explicit example of awaiting a session method for validation
                        count = await session.scalar(
                            f"SELECT COUNT(*) FROM settings_backups WHERE version = '{version}'"
                        )
                        self.logger.debug(f"Found {count} existing backups with same version")
                        
                        backup = await execute_with_retry(
                            lambda: self.crud_service.create(session, SettingsBackup, backup_data)
                        )
                        if backup:
                            self.logger.info(f"Created settings backup with ID {backup.id}")
                            return backup.id
                        else:
                            self.logger.error(error_message(
                                module_id=MODULE_ID,
                                error_type="BACKUP_CREATION_FAILED",
                                details="Failed to create backup record",
                                location="create_backup()"
                            ))
                            return None
                except Exception as e:
                    self.logger.error(error_message(
                        module_id=MODULE_ID,
                        error_type="BACKUP_CREATION_ERROR",
                        details=f"Error creating backup: {str(e)}",
                        location="create_backup()._create()"
                    ))
                    logger.error(traceback.format_exc())
                    return None
            
            backup_id = await self._db_op(_create)
            
            if backup_id is None:
                return Result.error(
                    code="BACKUP_CREATION_FAILED",
                    message="Failed to create settings backup",
                    details={"version": version}
                )
                
            return Result.success(data={"backup_id": backup_id, "version": version})
            
        except Exception as e:
            self.logger.error(error_message(
                module_id=MODULE_ID,
                error_type="BACKUP_CREATION_ERROR",
                details=f"Error creating backup: {str(e)}",
                location="create_backup()"
            ))
            logger.error(traceback.format_exc())
            
            return Result.error(
                code="BACKUP_CREATION_ERROR",
                message="Failed to create settings backup",
                details={"error": str(e)}
            )
    
    async def record_setting_change(self, module_id: str, setting_key: str, 
                                   old_value: Any, new_value: Any, 
                                   source: str = "user") -> Result:
        """
        Record a setting change in the database.
        
        Args:
            module_id: Module identifier
            setting_key: Setting key
            old_value: Previous value
            new_value: New value
            source: Source of the change
            
        Returns:
            Result with event ID if successful, error if not
        """
        # Check initialization
        if not self.initialized and not await self.initialize():
            return Result.error(
                code="SERVICE_NOT_INITIALIZED",
                message=f"{MODULE_ID}.database service not initialized",
                details={"operation": "record_setting_change"}
            )
            
        # Skip recording if values are identical
        if old_value == new_value:
            return Result.success(data={"status": "no_change"})
            
        event_data = {
            "date_created": datetime.now(),
            "module_id": module_id,
            "setting_key": setting_key,
            "old_value": old_value,
            "new_value": new_value,
            "source": source
        }
        
        try:
            async def _record():
                try:
                    async with self._db_session() as session:
                        event = await execute_with_retry(
                            lambda: self.crud_service.create(session, SettingsEvent, event_data)
                        )
                        if event:
                            self.logger.debug(f"Recorded setting change for {module_id}.{setting_key} with ID {event.id}")
                            return event.id
                        else:
                            self.logger.error(error_message(
                                module_id=MODULE_ID,
                                error_type="SETTING_CHANGE_RECORD_FAILED",
                                details=f"Failed to record change for {module_id}.{setting_key}",
                                location="record_setting_change()"
                            ))
                            return None
                except Exception as e:
                    self.logger.error(error_message(
                        module_id=MODULE_ID,
                        error_type="SETTING_CHANGE_RECORD_ERROR",
                        details=f"Error recording setting change for {module_id}.{setting_key}: {str(e)}",
                        location="record_setting_change()._record()"
                    ))
                    logger.error(traceback.format_exc())
                    return None
            
            event_id = await self._db_op(_record)
            
            if event_id is None:
                return Result.error(
                    code="SETTING_CHANGE_RECORD_FAILED",
                    message=f"Failed to record setting change for {module_id}.{setting_key}",
                    details={"module_id": module_id, "setting_key": setting_key}
                )
                
            return Result.success(data={"event_id": event_id})
            
        except Exception as e:
            self.logger.error(error_message(
                module_id=MODULE_ID,
                error_type="SETTING_CHANGE_RECORD_ERROR",
                details=f"Error recording setting change for {module_id}.{setting_key}: {str(e)}",
                location="record_setting_change()"
            ))
            logger.error(traceback.format_exc())
            
            return Result.error(
                code="SETTING_CHANGE_RECORD_ERROR",
                message=f"Error recording setting change",
                details={"module_id": module_id, "setting_key": setting_key, "error": str(e)}
            )
    
    async def get_backup(self, backup_id: int) -> Result:
        """
        Get a specific backup by ID.
        
        Args:
            backup_id: Backup ID
            
        Returns:
            Result with backup data if found, error if not
        """
        # Check initialization
        if not self.initialized and not await self.initialize():
            return Result.error(
                code="SERVICE_NOT_INITIALIZED",
                message=f"{MODULE_ID}.database service not initialized",
                details={"operation": "get_backup", "backup_id": backup_id}
            )
            
        try:
            async def _get():
                try:
                    async with self._db_session() as session:
                        backup = await execute_with_retry(
                            lambda: self.crud_service.read(session, SettingsBackup, backup_id)
                        )
                        if not backup:
                            self.logger.warning(error_message(
                                module_id=MODULE_ID,
                                error_type="BACKUP_NOT_FOUND",
                                details=f"Backup with ID {backup_id} not found",
                                location="get_backup()"
                            ))
                            return None
                            
                        return {
                            "id": backup.id,
                            "date_created": backup.date_created,
                            "version": backup.version,
                            "settings_data": backup.settings_data,
                            "description": backup.description
                        }
                except Exception as e:
                    self.logger.error(error_message(
                        module_id=MODULE_ID,
                        error_type="GET_BACKUP_ERROR",
                        details=f"Error retrieving backup {backup_id}: {str(e)}",
                        location="get_backup()._get()"
                    ))
                    logger.error(traceback.format_exc())
                    return None
            
            backup = await self._db_op(_get)
            
            if backup is None:
                return Result.error(
                    code="BACKUP_NOT_FOUND",
                    message=f"Backup with ID {backup_id} not found",
                    details={"backup_id": backup_id}
                )
                
            return Result.success(data=backup)
            
        except Exception as e:
            self.logger.error(error_message(
                module_id=MODULE_ID,
                error_type="GET_BACKUP_ERROR",
                details=f"Error retrieving backup {backup_id}: {str(e)}",
                location="get_backup()"
            ))
            logger.error(traceback.format_exc())
            
            return Result.error(
                code="GET_BACKUP_ERROR",
                message=f"Error retrieving backup {backup_id}",
                details={"backup_id": backup_id, "error": str(e)}
            )
    
    async def get_backups(self, limit: int = 10, offset: int = 0) -> Result:
        """
        Get a list of backups.
        
        Args:
            limit: Maximum number of backups to return
            offset: Pagination offset
            
        Returns:
            Result with list of backup information
        """
        # Check initialization
        if not self.initialized and not await self.initialize():
            return Result.error(
                code="SERVICE_NOT_INITIALIZED",
                message=f"{MODULE_ID}.database service not initialized",
                details={"operation": "get_backups"}
            )
            
        try:
            async def _list():
                try:
                    async with self._db_session() as session:
                        backups = await execute_with_retry(
                            lambda: self.crud_service.read_many(
                                session, SettingsBackup, 
                                skip=offset, limit=limit,
                                order_by=["date_created DESC"]
                            )
                        )
                        
                        return [{
                            "id": b.id,
                            "date_created": b.date_created,
                            "version": b.version,
                            "description": b.description
                        } for b in backups]
                except Exception as e:
                    self.logger.error(error_message(
                        module_id=MODULE_ID,
                        error_type="LIST_BACKUPS_ERROR",
                        details=f"Error listing backups: {str(e)}",
                        location="get_backups()._list()"
                    ))
                    logger.error(traceback.format_exc())
                    return []
            
            backups = await self._db_op(_list, [])
            return Result.success(data=backups)
            
        except Exception as e:
            self.logger.error(error_message(
                module_id=MODULE_ID,
                error_type="LIST_BACKUPS_ERROR",
                details=f"Error listing backups: {str(e)}",
                location="get_backups()"
            ))
            logger.error(traceback.format_exc())
            
            return Result.error(
                code="LIST_BACKUPS_ERROR",
                message="Error retrieving backup list",
                details={"error": str(e)}
            )
    
    async def restore_backup(self, backup_id: int) -> Result:
        """
        Restore settings from a backup.
        
        Args:
            backup_id: Backup ID to restore
            
        Returns:
            Result with settings data if successful, error if not
        """
        # Check initialization
        if not self.initialized and not await self.initialize():
            return Result.error(
                code="SERVICE_NOT_INITIALIZED",
                message=f"{MODULE_ID}.database service not initialized",
                details={"operation": "restore_backup", "backup_id": backup_id}
            )
            
        self.logger.info(f"Restoring settings from backup {backup_id}")
        
        try:
            async def _restore():
                try:
                    async with self._db_session() as session:
                        backup = await execute_with_retry(
                            lambda: self.crud_service.read(session, SettingsBackup, backup_id)
                        )
                        if not backup:
                            self.logger.error(error_message(
                                module_id=MODULE_ID,
                                error_type="RESTORE_BACKUP_NOT_FOUND",
                                details=f"Backup {backup_id} not found",
                                location="restore_backup()"
                            ))
                            return None
                            
                        self.logger.info(f"Successfully restored settings from backup {backup_id} (created: {backup.date_created})")
                        return backup.settings_data
                except Exception as e:
                    self.logger.error(error_message(
                        module_id=MODULE_ID,
                        error_type="RESTORE_BACKUP_ERROR",
                        details=f"Error restoring from backup {backup_id}: {str(e)}",
                        location="restore_backup()._restore()"
                    ))
                    logger.error(traceback.format_exc())
                    return None
            
            settings_data = await self._db_op(_restore)
            
            if settings_data is None:
                return Result.error(
                    code="BACKUP_NOT_FOUND",
                    message=f"Backup with ID {backup_id} not found",
                    details={"backup_id": backup_id}
                )
                
            return Result.success(data=settings_data)
            
        except Exception as e:
            self.logger.error(error_message(
                module_id=MODULE_ID,
                error_type="RESTORE_BACKUP_ERROR",
                details=f"Error restoring from backup {backup_id}: {str(e)}",
                location="restore_backup()"
            ))
            logger.error(traceback.format_exc())
            
            return Result.error(
                code="RESTORE_BACKUP_ERROR",
                message=f"Error restoring from backup {backup_id}",
                details={"backup_id": backup_id, "error": str(e)}
            )
    
    async def delete_backup(self, backup_id: int) -> Result:
        """
        Delete a backup.
        
        Args:
            backup_id: Backup ID to delete
            
        Returns:
            Result indicating success or failure
        """
        # Check initialization
        if not self.initialized and not await self.initialize():
            return Result.error(
                code="SERVICE_NOT_INITIALIZED",
                message=f"{MODULE_ID}.database service not initialized",
                details={"operation": "delete_backup", "backup_id": backup_id}
            )
            
        try:
            async def _delete():
                try:
                    async with self._db_session() as session:
                        success = await execute_with_retry(
                            lambda: self.crud_service.delete(session, SettingsBackup, backup_id)
                        )
                        
                        if success:
                            self.logger.info(f"Deleted backup {backup_id}")
                            return True
                        else:
                            self.logger.warning(error_message(
                                module_id=MODULE_ID,
                                error_type="DELETE_BACKUP_FAILED",
                                details=f"Failed to delete backup {backup_id}",
                                location="delete_backup()"
                            ))
                            return False
                except Exception as e:
                    self.logger.error(error_message(
                        module_id=MODULE_ID,
                        error_type="DELETE_BACKUP_ERROR",
                        details=f"Error deleting backup {backup_id}: {str(e)}",
                        location="delete_backup()._delete()"
                    ))
                    logger.error(traceback.format_exc())
                    return False
            
            success = await self._db_op(_delete, False)
            
            if not success:
                return Result.error(
                    code="DELETE_BACKUP_FAILED",
                    message=f"Failed to delete backup {backup_id}",
                    details={"backup_id": backup_id}
                )
                
            return Result.success(data={"backup_id": backup_id})
            
        except Exception as e:
            self.logger.error(error_message(
                module_id=MODULE_ID,
                error_type="DELETE_BACKUP_ERROR",
                details=f"Error deleting backup {backup_id}: {str(e)}",
                location="delete_backup()"
            ))
            logger.error(traceback.format_exc())
            
            return Result.error(
                code="DELETE_BACKUP_ERROR",
                message=f"Error deleting backup {backup_id}",
                details={"backup_id": backup_id, "error": str(e)}
            )
    
    async def cleanup_old_backups(self, max_backups: int = None, max_days: int = None) -> Result:
        """
        Clean up old backups based on count or age.
        
        Args:
            max_backups: Maximum number of backups to keep
            max_days: Maximum age of backups in days
            
        Returns:
            Result with number of deleted backups
        """
        # Check initialization
        if not self.initialized and not await self.initialize():
            return Result.error(
                code="SERVICE_NOT_INITIALIZED",
                message=f"{MODULE_ID}.database service not initialized",
                details={"operation": "cleanup_old_backups"}
            )
            
        # Use module settings if not specified
        if max_backups is None or max_days is None:
            settings = await self.app_context.get_module_settings(MODULE_ID)
            max_backups = max_backups or settings.get("backup_retention_count", 5)
            max_days = max_days or settings.get("retention_days", 30)
        
        try:
            async def _cleanup():
                try:
                    deleted_count = 0
                    
                    # Delete old backups based on date
                    if max_days:
                        async with self._db_session() as session:
                            cutoff_date = datetime.now() - timedelta(days=max_days)
                            filters = {"date_created": {"lt": cutoff_date}}
                            deleted_count_days = await execute_with_retry(
                                lambda: self.crud_service.bulk_delete(
                                    session, SettingsBackup, filters
                                )
                            )
                            deleted_count += deleted_count_days
                            self.logger.info(f"Deleted {deleted_count_days} backups older than {max_days} days")
                    
                    # Yield control to prevent long transactions
                    await asyncio.sleep(0)
                    
                    # Delete excess backups
                    if max_backups:
                        async with self._db_session() as session:
                            total_count = await execute_with_retry(
                                lambda: self.crud_service.count(session, SettingsBackup)
                            )
                            
                            if total_count > max_backups:
                                excess_count = total_count - max_backups
                                oldest_backups = await execute_with_retry(
                                    lambda: self.crud_service.read_many(
                                        session, SettingsBackup,
                                        limit=excess_count, order_by=["date_created"]
                                    )
                                )
                                
                                if oldest_backups:
                                    # Process in smaller batches to avoid long transactions
                                    batch_size = 5
                                    for i in range(0, len(oldest_backups), batch_size):
                                        batch = oldest_backups[i:i+batch_size]
                                        
                                        # Use a new session for each batch
                                        async with self._db_session() as batch_session:
                                            for backup in batch:
                                                await execute_with_retry(
                                                    lambda b=backup: self.crud_service.delete(
                                                        batch_session, SettingsBackup, b.id
                                                    )
                                                )
                                        
                                        # Yield control between batches
                                        await asyncio.sleep(0)
                                        deleted_count += len(batch)
                                        
                                    self.logger.info(f"Deleted {len(oldest_backups)} excess backups")
                    
                    return deleted_count
                except Exception as e:
                    self.logger.error(error_message(
                        module_id=MODULE_ID,
                        error_type="CLEANUP_BACKUPS_ERROR",
                        details=f"Error cleaning up old backups: {str(e)}",
                        location="cleanup_old_backups()._cleanup()"
                    ))
                    logger.error(traceback.format_exc())
                    return 0
            
            deleted_count = await self._db_op(_cleanup, 0)
            return Result.success(data={"deleted_count": deleted_count})
            
        except Exception as e:
            self.logger.error(error_message(
                module_id=MODULE_ID,
                error_type="CLEANUP_BACKUPS_ERROR",
                details=f"Error cleaning up old backups: {str(e)}",
                location="cleanup_old_backups()"
            ))
            logger.error(traceback.format_exc())
            
            return Result.error(
                code="CLEANUP_BACKUPS_ERROR",
                message="Error cleaning up old backups",
                details={"max_backups": max_backups, "max_days": max_days, "error": str(e)}
            )
    
    async def schedule_backup(self, frequency_days: int, retention_count: int) -> Result:
        """
        Schedule automatic backups.
        
        Args:
            frequency_days: Days between backups
            retention_count: Number of backups to retain
            
        Returns:
            Result with schedule ID if successful, error if not
        """
        # Check initialization
        if not self.initialized and not await self.initialize():
            return Result.error(
                code="SERVICE_NOT_INITIALIZED",
                message=f"{MODULE_ID}.database service not initialized",
                details={"operation": "schedule_backup"}
            )
            
        schedule_data = {
            "date_created": datetime.now(),
            "next_backup_time": datetime.now() + timedelta(days=frequency_days),
            "frequency_days": frequency_days,
            "retention_count": retention_count,
            "enabled": True
        }
        
        try:
            async def _schedule():
                try:
                    async with self._db_session() as session:
                        schedule = await execute_with_retry(
                            lambda: self.crud_service.create(session, ScheduledBackup, schedule_data)
                        )
                        
                        if schedule:
                            self.logger.info(f"Created backup schedule: every {frequency_days} days, keep {retention_count} backups")
                            return schedule.id
                        else:
                            self.logger.error(error_message(
                                module_id=MODULE_ID,
                                error_type="SCHEDULE_BACKUP_FAILED",
                                details="Failed to create backup schedule",
                                location="schedule_backup()"
                            ))
                            return None
                except Exception as e:
                    self.logger.error(error_message(
                        module_id=MODULE_ID,
                        error_type="SCHEDULE_BACKUP_ERROR",
                        details=f"Error scheduling backup: {str(e)}",
                        location="schedule_backup()._schedule()"
                    ))
                    logger.error(traceback.format_exc())
                    return None
            
            schedule_id = await self._db_op(_schedule)
            
            if schedule_id is None:
                return Result.error(
                    code="SCHEDULE_BACKUP_FAILED",
                    message="Failed to create backup schedule",
                    details={"frequency_days": frequency_days, "retention_count": retention_count}
                )
                
            return Result.success(data={"schedule_id": schedule_id})
            
        except Exception as e:
            self.logger.error(error_message(
                module_id=MODULE_ID,
                error_type="SCHEDULE_BACKUP_ERROR",
                details=f"Error scheduling backup: {str(e)}",
                location="schedule_backup()"
            ))
            logger.error(traceback.format_exc())
            
            return Result.error(
                code="SCHEDULE_BACKUP_ERROR",
                message="Error scheduling backup",
                details={"error": str(e)}
            )
    
    async def get_setting_history(self, module_id: str, setting_key: str, limit: int = 10) -> Result:
        """
        Get history of changes for a specific setting.
        
        Args:
            module_id: Module identifier
            setting_key: Setting key
            limit: Maximum number of history entries
            
        Returns:
            Result with list of setting change events
        """
        # Check initialization
        if not self.initialized and not await self.initialize():
            return Result.error(
                code="SERVICE_NOT_INITIALIZED",
                message=f"{MODULE_ID}.database service not initialized",
                details={"operation": "get_setting_history"}
            )
            
        try:
            async def _history():
                try:
                    async with self._db_session() as session:
                        filters = {"module_id": module_id, "setting_key": setting_key}
                        events = await execute_with_retry(
                            lambda: self.crud_service.read_many(
                                session, SettingsEvent,
                                filters=filters, limit=limit,
                                order_by=["date_created DESC"]
                            )
                        )
                        
                        return [{
                            "id": e.id,
                            "date_created": e.date_created,
                            "old_value": e.old_value,
                            "new_value": e.new_value,
                            "source": e.source
                        } for e in events]
                except Exception as e:
                    self.logger.error(error_message(
                        module_id=MODULE_ID,
                        error_type="SETTING_HISTORY_ERROR",
                        details=f"Error retrieving setting history for {module_id}.{setting_key}: {str(e)}",
                        location="get_setting_history()._history()"
                    ))
                    logger.error(traceback.format_exc())
                    return []
            
            history = await self._db_op(_history, [])
            return Result.success(data=history)
            
        except Exception as e:
            self.logger.error(error_message(
                module_id=MODULE_ID,
                error_type="SETTING_HISTORY_ERROR",
                details=f"Error retrieving setting history for {module_id}.{setting_key}: {str(e)}",
                location="get_setting_history()"
            ))
            logger.error(traceback.format_exc())
            
            return Result.error(
                code="SETTING_HISTORY_ERROR",
                message=f"Error retrieving setting history for {module_id}.{setting_key}",
                details={"error": str(e)}
            )
    
    async def start_backup_scheduler(self) -> Result:
        """
        Start the backup scheduler background task.
        
        Returns:
            Result indicating success or failure
        """
        # Check initialization
        if not self.initialized and not await self.initialize():
            self.logger.error(error_message(
                module_id=MODULE_ID,
                error_type="SCHEDULER_INIT_FAILED",
                details="Cannot start backup scheduler - database not initialized",
                location="start_backup_scheduler()"
            ))
            return Result.error(
                code="SERVICE_NOT_INITIALIZED",
                message=f"{MODULE_ID}.database service not initialized",
                details={"operation": "start_backup_scheduler"}
            )
        
        if self.backup_scheduler_task and not self.backup_scheduler_task.done():
            self.logger.warning(error_message(
                module_id=MODULE_ID,
                error_type="SCHEDULER_ALREADY_RUNNING",
                details="Backup scheduler is already running",
                location="start_backup_scheduler()"
            ))
            return Result.success(data={"status": "already_running"})
        
        try:
            # Use _create_background_task to properly track task
            self.backup_scheduler_task = self._create_background_task(
                self._backup_scheduler_loop(),
                name="backup_scheduler"
            )
            
            self.logger.info("Started backup scheduler")
            return Result.success(data={"status": "started"})
            
        except Exception as e:
            self.logger.error(error_message(
                module_id=MODULE_ID,
                error_type="START_SCHEDULER_ERROR",
                details=f"Error starting backup scheduler: {str(e)}",
                location="start_backup_scheduler()"
            ))
            logger.error(traceback.format_exc())
            
            return Result.error(
                code="START_SCHEDULER_ERROR",
                message="Error starting backup scheduler",
                details={"error": str(e)}
            )
    
    async def stop_backup_scheduler(self) -> Result:
        """
        Stop the backup scheduler background task.
        
        Returns:
            Result indicating success or failure
        """
        if not self.backup_scheduler_task:
            self.logger.warning(error_message(
                module_id=MODULE_ID,
                error_type="SCHEDULER_NOT_RUNNING",
                details="Backup scheduler is not running",
                location="stop_backup_scheduler()"
            ))
            return Result.success(data={"status": "not_running"})
        
        try:
            if not self.backup_scheduler_task.done():
                self.backup_scheduler_task.cancel()
                try:
                    # Wait for task to be cancelled
                    await asyncio.wait_for(asyncio.shield(self.backup_scheduler_task), timeout=2.0)
                except (asyncio.TimeoutError, asyncio.CancelledError):
                    pass
            
            self.backup_scheduler_task = None
            self.logger.info("Stopped backup scheduler")
            return Result.success(data={"status": "stopped"})
            
        except Exception as e:
            self.logger.error(error_message(
                module_id=MODULE_ID,
                error_type="STOP_SCHEDULER_ERROR",
                details=f"Error stopping backup scheduler: {str(e)}",
                location="stop_backup_scheduler()"
            ))
            logger.error(traceback.format_exc())
            
            return Result.error(
                code="STOP_SCHEDULER_ERROR",
                message="Error stopping backup scheduler",
                details={"error": str(e)}
            )
    
    async def _backup_scheduler_loop(self):
        """Background task that handles scheduled backups."""
        try:
            while True:
                await self._execute_due_backups()
                await asyncio.sleep(3600)  # Check hourly
        except asyncio.CancelledError:
            self.logger.info("Backup scheduler task cancelled")
            raise
        except Exception as e:
            self.logger.error(error_message(
                module_id=MODULE_ID,
                error_type="SCHEDULER_LOOP_ERROR",
                details=f"Error in backup scheduler loop: {str(e)}",
                location="_backup_scheduler_loop()"
            ))
            logger.error(traceback.format_exc())
    
    async def _execute_due_backups(self):
        """Execute any backups that are due."""
        if not await self.initialize():
            self.logger.error(error_message(
                module_id=MODULE_ID,
                error_type="EXECUTE_BACKUPS_INIT_FAILED",
                details="Cannot execute backups - database not initialized",
                location="_execute_due_backups()"
            ))
            return
        
        try:
            # Get due backups
            now = datetime.now()
            
            async with self._db_session() as session:
                filters = {"enabled": True, "next_backup_time": {"lte": now}}
                due_backups = await execute_with_retry(
                    lambda: self.crud_service.read_many(session, ScheduledBackup, filters=filters)
                )
            
            # Process each due backup
            for schedule in due_backups:
                try:
                    # Get settings data and create backup
                    settings_service = self.app_context.get_service(f"{MODULE_ID}.service")
                    if not settings_service:
                        self.logger.error(error_message(
                            module_id=MODULE_ID,
                            error_type="SETTINGS_SERVICE_UNAVAILABLE",
                            details="Settings service not available for scheduled backup",
                            location="_execute_due_backups()"
                        ))
                        continue
                        
                    result = await self.create_backup(
                        settings_service.settings,
                        f"Scheduled backup (ID: {schedule.id})"
                    )
                    
                    # Yield control between operations
                    await asyncio.sleep(0)
                    
                    # Update schedule and clean up if successful
                    async with self._db_session() as session:
                        if result.success:
                            await self.cleanup_old_backups(max_backups=schedule.retention_count)
                            next_time = now + timedelta(days=schedule.frequency_days)
                            await execute_with_retry(
                                lambda: self.crud_service.update(
                                    session, ScheduledBackup, schedule.id,
                                    {"next_backup_time": next_time, "last_error": None}
                                )
                            )
                            self.logger.info(f"Executed scheduled backup {schedule.id}, next run: {next_time}")
                        else:
                            self.logger.error(error_message(
                                module_id=MODULE_ID,
                                error_type="SCHEDULED_BACKUP_FAILED",
                                details=f"Failed to create scheduled backup for ID {schedule.id}",
                                location="_execute_due_backups()"
                            ))
                            await execute_with_retry(
                                lambda: self.crud_service.update(
                                    session, ScheduledBackup, schedule.id,
                                    {"last_error": result.error.get("message", "Failed to create backup")}
                                )
                            )
                except Exception as e:
                    # Record error but continue with other backups
                    self.logger.error(error_message(
                        module_id=MODULE_ID,
                        error_type="SCHEDULED_BACKUP_ERROR",
                        details=f"Error executing scheduled backup {schedule.id}: {str(e)}",
                        location="_execute_due_backups()"
                    ))
                    logger.error(traceback.format_exc())
                    try:
                        async with self._db_session() as session:
                            await execute_with_retry(
                                lambda: self.crud_service.update(
                                    session, ScheduledBackup, schedule.id,
                                    {"last_error": str(e)}
                                )
                            )
                    except Exception as e2:
                        self.logger.error(error_message(
                            module_id=MODULE_ID,
                            error_type="ERROR_RECORD_FAILED",
                            details=f"Could not record error for backup {schedule.id}: {str(e2)}",
                            location="_execute_due_backups()"
                        ))
                
                # Yield control between backups
                await asyncio.sleep(0)
                
        except Exception as e:
            self.logger.error(error_message(
                module_id=MODULE_ID,
                error_type="EXECUTE_DUE_BACKUPS_ERROR",
                details=f"Error processing due backups: {str(e)}",
                location="_execute_due_backups()"
            ))
            logger.error(traceback.format_exc())

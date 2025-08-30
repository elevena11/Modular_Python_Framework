"""
modules/core/settings/storage/db_storage.py
Updated: April 5, 2025
Database operations for settings module with standardized error handling
"""

import logging
import asyncio
import contextlib
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, AsyncGenerator, TypeVar, Type, Union, Callable

from sqlalchemy.ext.asyncio import AsyncSession

from core.database import execute_with_retry
from core.error_utils import error_message, Result
from ..db_models import SettingsBackup, SettingsEvent, ScheduledBackup
from ..utils.error_helpers import handle_result_operation, check_initialization

# Define component identity
MODULE_ID = "core.settings"
COMPONENT_ID = f"{MODULE_ID}.db_storage"
# Use component ID for the logger
logger = logging.getLogger(COMPONENT_ID)

T = TypeVar('T')  # For generic type hints

class DatabaseStorageService:
    """
    Service for storing settings in the database.
    
    Handles database operations for settings module:
    - Setting backups
    - Change history
    - Scheduled backups
    """
    
    def __init__(self, app_context, database_service=None, crud_service=None):
        """
        Initialize database storage service with services from parent module.
        
        NEW PATTERN: Services are passed from parent module that acquired them
        via @require_services decorator, eliminating fragile service fetching.
        
        Args:
            app_context: Application context
            database_service: Database service from parent module (optional)
            crud_service: CRUD service from parent module (optional)
        """
        self.app_context = app_context
        self.db_service = database_service
        self.crud_service = crud_service
        self.initialized = False
        self.logger = logger
        
        # Track background tasks for proper shutdown
        self._background_tasks = []
    
    async def initialize(self, database_service=None, crud_service=None, **kwargs) -> bool:
        """
        Initialize database storage service with services from parent module.
        
        NEW PATTERN: Services provided by parent module that acquired them
        via @require_services decorator, no independent service fetching.
        
        Args:
            database_service: Database service from parent settings module
            crud_service: CRUD service from parent settings module
            
        Returns:
            True if initialization successful, False otherwise
        """
        if self.initialized:
            return True
        
        # Use services passed from parent module if provided
        if database_service:
            self.db_service = database_service
        if crud_service:
            self.crud_service = crud_service
            
        if not self.db_service:
            self.logger.warning(error_message(
                module_id=COMPONENT_ID,
                error_type="DB_SERVICE_UNAVAILABLE",
                details="Database service not provided by parent module - database storage features disabled",
                location="initialize()"
            ))
            return False
        
        if not self.db_service.initialized:
            self.logger.warning(error_message(
                module_id=COMPONENT_ID,
                error_type="DB_NOT_INITIALIZED",
                details="Database not initialized - database storage features disabled",
                location="initialize()"
            ))
            return False
        
        if not self.crud_service:
            self.logger.warning(error_message(
                module_id=COMPONENT_ID,
                error_type="CRUD_SERVICE_UNAVAILABLE",
                details="CRUD service not provided by parent module - database storage features disabled",
                location="initialize()"
            ))
            return False
        
        self.initialized = True
        self.logger.info("Database storage service initialized with services from parent module")
        return True
    
    async def shutdown(self):
        """
        Graceful async shutdown when event loop is available.
        
        Returns:
            None
        """
        self.logger.info(f"{COMPONENT_ID}: Shutting down service gracefully...")
        
        # Cancel background tasks
        for task in self._background_tasks:
            if not task.done():
                task.cancel()
                try:
                    await asyncio.wait_for(asyncio.shield(task), timeout=2.0)
                except (asyncio.TimeoutError, asyncio.CancelledError):
                    pass
        
        self.logger.info(f"{COMPONENT_ID}: Service shutdown complete")
    
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
    async def _db_session(self, purpose: str = "settings_operation") -> AsyncGenerator[AsyncSession, None]:
        """
        Get a database session with initialization check using new integrity pattern.
        
        Args:
            purpose: Description of the database operation purpose
        
        Yields:
            Database session
        
        Raises:
            RuntimeError: If database operations not initialized
        """
        if not check_initialization(self, COMPONENT_ID, "_db_session"):
            raise RuntimeError("Database operations not initialized")
            
        # NEW PATTERN: Use integrity_session via app_context (Phase 4 compatibility)
        async with self.app_context.database.integrity_session("framework", purpose) as session:
            yield session
    
    async def create_backup(self, 
                           settings_data: Dict[str, Any], 
                           description: Optional[str] = None,
                           params: Optional[Dict[str, Any]] = None) -> Result:
        """
        Create a settings backup in the database.
        
        Args:
            settings_data: Settings data to backup
            description: Optional description for the backup
            
        Returns:
            Result with backup ID if successful, error if not
        """
        # Check initialization
        if not check_initialization(self, COMPONENT_ID, "create_backup"):
            return Result.error(
                code=f"{COMPONENT_ID}_SERVICE_NOT_INITIALIZED",
                message=f"{COMPONENT_ID} service not initialized",
                details={"operation": "create_backup"}
            )
            
        
        
        async def _create_backup():
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
            
            async with self._db_session("create_backup") as session:
                # Use execute_with_retry for database operations
                # crud_service.create returns a Result object
                backup_result = await execute_with_retry(
                    lambda: self.crud_service.create(session, SettingsBackup, backup_data)
                )
                
                # Check if the operation was successful and get the data
                if backup_result and backup_result.success:
                    backup = backup_result.data # Extract the actual SettingsBackup instance
                    self.logger.info(f"Created settings backup with ID {backup.id}")
                    
                    
                    return {"backup_id": backup.id, "version": version}
                    
                
                self.logger.error(error_message(
                    module_id=COMPONENT_ID,
                    error_type="BACKUP_CREATION_FAILED",
                    details="Failed to create backup record in database",
                    location="create_backup()"
                ))
                
                return None
        
        result = await handle_result_operation(
            _create_backup,
            COMPONENT_ID,
            "BACKUP_CREATION_ERROR",
            "Error creating settings backup",
            "create_backup()"
        )
        
        # Handle special case for None result
        if result.success and result.data is None:
            
            return Result.error(
                code=f"{COMPONENT_ID}_BACKUP_CREATION_FAILED",
                message="Failed to create settings backup",
                details={}
            )
        return result
    
    async def record_setting_change(self, 
                                   module_id: str, 
                                   setting_key: str, 
                                   old_value: Any, 
                                   new_value: Any, 
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
        if not check_initialization(self, COMPONENT_ID, "record_setting_change"):
            return Result.error(
                code=f"{COMPONENT_ID}_SERVICE_NOT_INITIALIZED",
                message=f"{COMPONENT_ID} service not initialized",
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
        
        async def _record_change():
            async with self._db_session("record_setting_change") as session:
                # crud_service.create returns a Result object
                event_result = await execute_with_retry(
                    lambda: self.crud_service.create(session, SettingsEvent, event_data)
                )
                
                # Check if the operation was successful and get the data
                if event_result and event_result.success:
                    event = event_result.data # Extract the actual SettingsEvent instance
                    self.logger.debug(f"Recorded setting change for {module_id}.{setting_key} with ID {event.id}")
                    return {"event_id": event.id}
                else:
                    self.logger.error(error_message(
                        module_id=COMPONENT_ID,
                        error_type="SETTING_CHANGE_RECORD_FAILED",
                        details=f"Failed to record change for {module_id}.{setting_key}",
                        location="record_setting_change()"
                    ))
                    return None
        
        result = await handle_result_operation(
            _record_change,
            COMPONENT_ID,
            "SETTING_CHANGE_RECORD_ERROR",
            f"Error recording setting change for {module_id}.{setting_key}",
            "record_setting_change()",
            {"module_id": module_id, "setting_key": setting_key}
        )
        
        # Handle special case for None result
        if result.success and result.data is None:
            return Result.error(
                code=f"{COMPONENT_ID}_SETTING_CHANGE_RECORD_FAILED",
                message=f"Failed to record setting change for {module_id}.{setting_key}",
                details={"module_id": module_id, "setting_key": setting_key}
            )
            
        return result
    
    async def get_backup(self, backup_id: int, params: Optional[Dict[str, Any]] = None) -> Result:
        """
        Get a specific backup by ID.
        
        Args:
            backup_id: Backup ID
            
        Returns:
            Result with backup data if found, error if not
        """
        # Check initialization
        if not check_initialization(self, COMPONENT_ID, "get_backup"):
            return Result.error(
                code=f"{COMPONENT_ID}_SERVICE_NOT_INITIALIZED",
                message=f"{COMPONENT_ID} service not initialized",
                details={"operation": "get_backup", "backup_id": backup_id}
            )
                    
        async def _get_backup():
            async with self._db_session("get_backup") as session:
                backup = await execute_with_retry(
                    lambda: self.crud_service.read(session, SettingsBackup, backup_id)
                )
                
                if not backup:
                    return None
                    
                return {
                    "id": backup.id,
                    "date_created": backup.date_created,
                    "version": backup.version,
                    "settings_data": backup.settings_data,
                    "description": backup.description
                }
        
        result = await handle_result_operation(
            _get_backup,
            COMPONENT_ID,
            "GET_BACKUP_ERROR",
            f"Error retrieving backup {backup_id}",
            "get_backup()",
            {"backup_id": backup_id}
        )
        
        # Handle special case for None result
        if result.success and result.data is None:
            self.logger.warning(error_message(
                module_id=COMPONENT_ID,
                error_type="BACKUP_NOT_FOUND",
                details=f"Backup with ID {backup_id} not found",
                location="get_backup()"
            ))
            
            return Result.error(
                code=f"{COMPONENT_ID}_BACKUP_NOT_FOUND",
                message=f"Backup with ID {backup_id} not found",
                details={"backup_id": backup_id}
            )
            
        return result
    
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
        if not check_initialization(self, COMPONENT_ID, "get_backups"):
            return Result.error(
                code=f"{COMPONENT_ID}_SERVICE_NOT_INITIALIZED",
                message=f"{COMPONENT_ID} service not initialized",
                details={"operation": "get_backups"}
            )
            
        async def _list_backups():
            async with self._db_session("list_backups") as session:
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
        
        return await handle_result_operation(
            _list_backups,
            COMPONENT_ID,
            "LIST_BACKUPS_ERROR",
            "Error retrieving backup list",
            "get_backups()"
        )
    
    async def restore_backup(self, 
                            backup_id: int, 
                            params: Optional[Dict[str, Any]] = None) -> Result:
        """
        Restore settings from a backup.
        
        Args:
            backup_id: Backup ID to restore
            
        Returns:
            Result with settings data if successful, error if not
        """
        # Check initialization
        if not check_initialization(self, COMPONENT_ID, "restore_backup"):
            return Result.error(
                code=f"{COMPONENT_ID}_SERVICE_NOT_INITIALIZED",
                message=f"{COMPONENT_ID} service not initialized",
                details={"operation": "restore_backup", "backup_id": backup_id}
            )
            
        
        self.logger.info(f"Restoring settings from backup {backup_id}")
        
        
        async def _restore_backup():
            async with self._db_session("restore_backup") as session:
                backup = await execute_with_retry(
                    lambda: self.crud_service.read(session, SettingsBackup, backup_id)
                )

                if not backup:
                    return None
                    
                return backup.settings_data
        
        result = await handle_result_operation(
            _restore_backup,
            COMPONENT_ID,
            "RESTORE_BACKUP_ERROR",
            f"Error restoring from backup {backup_id}",
            "restore_backup()",
            {"backup_id": backup_id}
        )
        
        # Handle special case for None result
        if result.success and result.data is None:
            self.logger.error(error_message(
                module_id=COMPONENT_ID,
                error_type="RESTORE_BACKUP_NOT_FOUND",
                details=f"Backup {backup_id} not found",
                location="restore_backup()"
            ))
            
            
            return Result.error(
                code=f"{COMPONENT_ID}_BACKUP_NOT_FOUND",
                message=f"Backup with ID {backup_id} not found",
                details={"backup_id": backup_id}
            )
        
        # On successful restore
        if result.success:
            self.logger.info(f"Successfully restored settings from backup {backup_id}")
            
        return result
    
    async def delete_backup(self, backup_id: int) -> Result:
        """
        Delete a backup.
        
        Args:
            backup_id: Backup ID to delete
            
        Returns:
            Result indicating success or failure
        """
        # Check initialization
        if not check_initialization(self, COMPONENT_ID, "delete_backup"):
            return Result.error(
                code=f"{COMPONENT_ID}_SERVICE_NOT_INITIALIZED",
                message=f"{COMPONENT_ID} service not initialized",
                details={"operation": "delete_backup", "backup_id": backup_id}
            )
            
        async def _delete_backup():
            async with self._db_session("delete_backup") as session:
                success = await execute_with_retry(
                    lambda: self.crud_service.delete(session, SettingsBackup, backup_id)
                )
                
                if not success:
                    return None
                    
                return {"backup_id": backup_id}
        
        result = await handle_result_operation(
            _delete_backup,
            COMPONENT_ID,
            "DELETE_BACKUP_ERROR",
            f"Error deleting backup {backup_id}",
            "delete_backup()",
            {"backup_id": backup_id}
        )
        
        # Handle special case for None result
        if result.success and result.data is None:
            self.logger.warning(error_message(
                module_id=COMPONENT_ID,
                error_type="DELETE_BACKUP_FAILED",
                details=f"Failed to delete backup {backup_id}",
                location="delete_backup()"
            ))
            
            return Result.error(
                code=f"{COMPONENT_ID}_DELETE_BACKUP_FAILED",
                message=f"Failed to delete backup {backup_id}",
                details={"backup_id": backup_id}
            )
            
        return result
    
    async def cleanup_old_backups(self, max_backups: Optional[int] = None, max_days: Optional[int] = None) -> Result:
        """
        Clean up old backups based on count or age.
        
        Args:
            max_backups: Maximum number of backups to keep
            max_days: Maximum age of backups in days
            
        Returns:
            Result with number of deleted backups
        """
        # Check initialization
        if not check_initialization(self, COMPONENT_ID, "cleanup_old_backups"):
            return Result.error(
                code=f"{COMPONENT_ID}_SERVICE_NOT_INITIALIZED",
                message=f"{COMPONENT_ID} service not initialized",
                details={"operation": "cleanup_old_backups"}
            )
            
        # Use module settings if not specified
        if max_backups is None or max_days is None:
            settings = await self.app_context.get_module_settings(MODULE_ID)
            max_backups = max_backups or settings.get("backup_retention_count", 5)
            max_days = max_days or settings.get("retention_days", 30)
        
        async def _cleanup():
            deleted_count = 0
            
            # Delete old backups based on date
            if max_days:
                async with self._db_session("cleanup_old_backups_by_date") as session:
                    cutoff_date = datetime.now() - timedelta(days=max_days)
                    filters = {"date_created": {"lt": cutoff_date}}
                    # crud_service.bulk_delete returns a Result object with the count
                    delete_result = await execute_with_retry(
                        lambda: self.crud_service.bulk_delete(
                            session, SettingsBackup, filters
                        )
                    )
                    # Check success and add the count from result.data
                    if delete_result and delete_result.success:
                        deleted_count_days = delete_result.data
                        deleted_count += deleted_count_days
                    self.logger.info(f"Deleted {deleted_count_days} backups older than {max_days} days")
            
            # Yield control to avoid long-running transactions
            await asyncio.sleep(0)
            
            # Delete excess backups
            if max_backups:
                async with self._db_session("cleanup_old_backups_by_count") as session:
                    # crud_service.count returns a Result object
                    count_result = await execute_with_retry(
                        lambda: self.crud_service.count(session, SettingsBackup)
                    )
                    
                    # Check success and extract the count before comparing
                    if count_result and count_result.success:
                        total_count = count_result.data
                        if total_count > max_backups:
                            # Indent the following block
                            excess_count = total_count - max_backups
                            # crud_service.read_many returns a Result object
                            oldest_backups_result = await execute_with_retry(
                                lambda: self.crud_service.read_many(
                                    session, SettingsBackup,
                                    limit=excess_count, order_by=["date_created"]
                                )
                            )
                            
                            # Check success and extract the list before using it
                            if oldest_backups_result and oldest_backups_result.success:
                                oldest_backups = oldest_backups_result.data
                                if oldest_backups: # Check if the extracted list is not empty
                                    batch_size = 5
                                    for i in range(0, len(oldest_backups), batch_size):
                                        # Process in small batches
                                        batch = oldest_backups[i:i+batch_size]
                                async with self._db_session("cleanup_batch_delete") as batch_session:
                                    for backup in batch:
                                        await execute_with_retry(
                                            lambda: self.crud_service.delete(
                                                batch_session, SettingsBackup, backup.id
                                            )
                                        )
                                
                                # Yield control between batches
                                await asyncio.sleep(0)
                                
                                deleted_count += len(batch)
                                
                            self.logger.info(f"Deleted {len(oldest_backups)} excess backups")
            
            return {"deleted_count": deleted_count}
        
        return await handle_result_operation(
            _cleanup,
            COMPONENT_ID,
            "CLEANUP_BACKUPS_ERROR",
            "Error cleaning up old backups",
            "cleanup_old_backups()",
            {"max_backups": max_backups, "max_days": max_days}
        )
    
    async def get_setting_history(self, 
                                 module_id: str, 
                                 setting_key: str, 
                                 limit: int = 10) -> Result:
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
        if not check_initialization(self, COMPONENT_ID, "get_setting_history"):
            return Result.error(
                code=f"{COMPONENT_ID}_SERVICE_NOT_INITIALIZED",
                message=f"{COMPONENT_ID} service not initialized",
                details={"operation": "get_setting_history"}
            )
            
        async def _get_history():
            async with self._db_session("get_setting_history") as session:
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
        
        return await handle_result_operation(
            _get_history,
            COMPONENT_ID,
            "SETTING_HISTORY_ERROR",
            f"Error retrieving setting history for {module_id}.{setting_key}",
            "get_setting_history()",
            {"module_id": module_id, "setting_key": setting_key}
        )

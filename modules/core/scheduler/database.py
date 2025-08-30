"""
modules/core/scheduler/database.py
Updated: April 6, 2025
Database operations for scheduler module with standardized error handling
"""

import logging
import contextlib
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union, Callable, Awaitable, TypeVar, Type

from core.error_utils import Result, error_message

# Import database models
from .db_models import ScheduledEvent, EventExecution, CleanupConfig

# Module identity - must match manifest.json
MODULE_ID = "core.scheduler"
# Use a hierarchical logger name for the database component
COMPONENT_ID = f"{MODULE_ID}.database"
logger = logging.getLogger(COMPONENT_ID)

T = TypeVar('T')  # For generic type hints

class SchedulerDatabaseOperations:
    """
    Database operations for the scheduler module.
    
    This class provides database access methods for the scheduler module,
    following the standard database operations pattern for the framework.
    """
    
    def __init__(self, app_context):
        """Initialize database operations."""
        self.app_context = app_context
        self.db_service = app_context.get_service("core.database.service")
        self.crud_service = app_context.get_service("core.database.crud_service")
        self.initialized = False
        self.logger = logger
    
    async def initialize(self) -> bool:
        """
        Initialize database operations.
        
        Returns:
            bool: Whether initialization was successful
        """
        if self.initialized:
            return True
            
        if not self.db_service:
            self.logger.warning(error_message(
                module_id=COMPONENT_ID,
                error_type="DB_SERVICE_UNAVAILABLE",
                details="Database service not available - features disabled"
            ))
            return False
        
        if not hasattr(self.db_service, "initialized") or not self.db_service.initialized:
            self.logger.warning(error_message(
                module_id=COMPONENT_ID,
                error_type="DB_NOT_INITIALIZED",
                details="Database not initialized - features disabled"
            ))
            return False
        
        if not self.crud_service:
            self.logger.warning(error_message(
                module_id=COMPONENT_ID,
                error_type="CRUD_SERVICE_UNAVAILABLE",
                details="CRUD service not available - features disabled"
            ))
            return False
        
        self.initialized = True
        self.logger.info("Scheduler database operations initialized")
        return True
    
    @contextlib.asynccontextmanager
    async def _db_session(self):
        """
        Get a database session with initialization check.
        
        Yields:
            AsyncSession: SQLAlchemy async session
            
        Raises:
            RuntimeError: If database operations not initialized
        """
        if not await self.initialize():
            raise RuntimeError(error_message(
                module_id=COMPONENT_ID,
                error_type="DB_NOT_INITIALIZED",
                details="Database operations not initialized"
            ))
        async with self.app_context.db_session() as session:
            yield session
    
    async def _db_op(self, op_func: Callable[[], Awaitable[T]], default=None) -> T:
        """
        Execute a database operation with standard error handling.
        
        Args:
            op_func: Async function to execute (must return a coroutine)
            default: Default return value on error
            
        Returns:
            Result of the operation or default on error
        """
        try:
            return await op_func()
        except RuntimeError as e:
            self.logger.warning(error_message(
                module_id=COMPONENT_ID,
                error_type="DB_NOT_INITIALIZED",
                details=f"Database operations not initialized: {str(e)}"
            ))
            return default
        except Exception as e:
            self.logger.error(error_message(
                module_id=COMPONENT_ID,
                error_type="DB_OPERATION_ERROR",
                details=f"Database operation error: {str(e)}"
            ))
            import traceback
            self.logger.error(traceback.format_exc())
            return default
    
    # Event operations
    
    async def create_event(
        self,
        id: str,
        name: str,
        function_name: str,
        next_execution: datetime,
        module_id: str,
        recurring: bool = False,
        interval_type: Optional[str] = None,
        interval_value: Optional[int] = None,
        parameters: Optional[Dict[str, Any]] = None,
        description: str = ""
    ) -> bool:
        """
        Create a new scheduled event.
        
        Args:
            id: Unique ID for the event
            name: Name of the event
            function_name: Name of the function to execute
            next_execution: When to execute the event
            module_id: ID of the module scheduling the event
            recurring: Whether this is a recurring event
            interval_type: For recurring events: minutes, hours, days, weeks, months
            interval_value: For recurring events: number of interval units
            parameters: Parameters to pass to the function
            description: Optional description of the event
            
        Returns:
            bool: Whether creation was successful
        """
        event_data = {
            "id": id,
            "name": name,
            "description": description,
            "function_name": function_name,
            "next_execution": next_execution,
            "module_id": module_id,
            "recurring": recurring,
            "interval_type": interval_type,
            "interval_value": interval_value,
            "parameters": parameters or {},
            "status": "pending",
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
        
        async def _create():
            async with self._db_session() as session:
                # Create a coroutine directly instead of using a lambda
                create_coro = self.crud_service.create(session, ScheduledEvent, event_data)
                result = await self.db_service.execute_with_retry(create_coro)
                return result is not None
        
        return await self._db_op(_create, False)
    
    async def get_event(self, event_id: str) -> Result:
        """
        Get a scheduled event by ID.
        
        Args:
            event_id: ID of the event
            
        Returns:
            Result: Success with event data or error information
        """
        async def _get():
            async with self._db_session() as session:
                # Create a coroutine directly instead of using a lambda
                read_coro = self.crud_service.read(session, ScheduledEvent, event_id, as_dict=True)
                result = await self.db_service.execute_with_retry(read_coro)
                if result is None:
                    return Result.error(
                        code="ITEM_NOT_FOUND",
                        message=f"Event with ID {event_id} not found"
                    )
                # Check if result is already a Result object
                if hasattr(result, 'success') and hasattr(result, 'data'):
                    return result  # It's already a Result object
                return Result.success(data=result)
        
        result = await self._db_op(_get)
        if result is None:
            return Result.error(
                code="DB_OPERATION_FAILED",
                message=f"Database operation failed when fetching event {event_id}"
            )
        return result
    
    async def get_events(
        self,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 50
    ) -> Result:
        """
        Get scheduled events with filtering.
        
        Args:
            filters: Optional filters to apply
            limit: Maximum number of events to return
            
        Returns:
            Result: Success with list of events or error information
        """
        async def _get():
            async with self._db_session() as session:
                # Create a coroutine directly instead of using a lambda
                read_many_coro = self.crud_service.read_many(
                    session, ScheduledEvent, 
                    filters=filters,
                    limit=limit,
                    order_by=["next_execution"],
                    as_dict=True
                )
                result = await self.db_service.execute_with_retry(read_many_coro)
                # Don't wrap the result again if it's already a Result object
                if isinstance(result, list):
                    return Result.success(data=result)
                return result  # If the result is already a Result object, return it directly
        
        result = await self._db_op(_get)
        if result is None:
            return Result.error(
                code="DB_OPERATION_FAILED",
                message="Database operation failed when fetching events"
            )
        return result
    
    async def get_due_events(
        self,
        reference_time: datetime,
        limit: int = 10
    ) -> Result:
        """
        Get events that are due for execution.
        
        Args:
            reference_time: Current time reference
            limit: Maximum number of events to return
            
        Returns:
            Result: Success with list of due events or error information
        """
        async def _get():
            async with self._db_session() as session:
                # Find events where next_execution <= reference_time and status is pending
                filters = {
                    "next_execution": {"lte": reference_time},
                    "status": "pending"
                }
                
                # Create a coroutine directly instead of using a lambda
                read_many_coro = self.crud_service.read_many(
                    session, ScheduledEvent, 
                    filters=filters,
                    limit=limit,
                    order_by=["next_execution"],
                    as_dict=True
                )
                result = await self.db_service.execute_with_retry(read_many_coro)
                # Don't wrap the result again if it's already a Result object
                if isinstance(result, list):
                    return Result.success(data=result)
                return result  # If the result is already a Result object, return it directly
        
        result = await self._db_op(_get)
        if result is None:
            return Result.error(
                code="DB_OPERATION_FAILED",
                message="Database operation failed when fetching due events"
            )
        return result
    
    async def update_event(
        self,
        event_id: str,
        updates: Dict[str, Any]
    ) -> bool:
        """
        Update a scheduled event.
        
        Args:
            event_id: ID of the event
            updates: Dictionary of fields to update
            
        Returns:
            bool: Whether update was successful
        """
        # Always update the updated_at timestamp
        updates["updated_at"] = datetime.now()
        
        async def _update():
            async with self._db_session() as session:
                # Create a coroutine directly instead of using a lambda
                update_coro = self.crud_service.update(
                    session, ScheduledEvent, event_id, updates
                )
                result = await self.db_service.execute_with_retry(update_coro)
                return result is not None
        
        return await self._db_op(_update, False)
    
    async def delete_event(self, event_id: str) -> bool:
        """
        Delete a scheduled event.
        
        Args:
            event_id: ID of the event
            
        Returns:
            bool: Whether deletion was successful
        """
        async def _delete():
            async with self._db_session() as session:
                # Create a coroutine directly instead of using a lambda
                delete_coro = self.crud_service.delete(
                    session, ScheduledEvent, event_id
                )
                result = await self.db_service.execute_with_retry(delete_coro)
                return result
        
        return await self._db_op(_delete, False)
    
    # Execution operations
    
    async def create_execution(
        self,
        id: str,
        event_id: str,
        start_time: datetime,
        trace_session_id: Optional[str] = None
    ) -> bool:
        """
        Create a new execution record.
        
        Args:
            id: Unique ID for the execution
            event_id: ID of the event being executed
            start_time: When execution started
            trace_session_id: Optional ID of the trace session
            
        Returns:
            bool: Whether creation was successful
        """
        execution_data = {
            "id": id,
            "event_id": event_id,
            "start_time": start_time,
            "trace_session_id": trace_session_id
        }
        
        async def _create():
            async with self._db_session() as session:
                # Create a coroutine directly instead of using a lambda
                create_coro = self.crud_service.create(session, EventExecution, execution_data)
                result = await self.db_service.execute_with_retry(create_coro)
                return result is not None
        
        return await self._db_op(_create, False)
    
    async def update_execution(
        self,
        execution_id: str,
        updates: Dict[str, Any]
    ) -> bool:
        """
        Update an execution record.
        
        Args:
            execution_id: ID of the execution
            updates: Dictionary of fields to update
            
        Returns:
            bool: Whether update was successful
        """
        async def _update():
            async with self._db_session() as session:
                # Create a coroutine directly instead of using a lambda
                update_coro = self.crud_service.update(
                    session, EventExecution, execution_id, updates
                )
                result = await self.db_service.execute_with_retry(update_coro)
                return result is not None
        
        return await self._db_op(_update, False)
    
    async def get_executions(
        self,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 50
    ) -> Result:
        """
        Get execution records with filtering.
        
        Args:
            filters: Optional filters to apply
            limit: Maximum number of executions to return
            
        Returns:
            Result: Success with list of executions or error information
        """
        async def _get():
            async with self._db_session() as session:
                # Create a coroutine directly instead of using a lambda
                read_many_coro = self.crud_service.read_many(
                    session, EventExecution, 
                    filters=filters,
                    limit=limit,
                    order_by=["start_time DESC"],
                    as_dict=True
                )
                result = await self.db_service.execute_with_retry(read_many_coro)
                # Don't wrap the result again if it's already a Result object
                if isinstance(result, list):
                    return Result.success(data=result)
                return result  # If the result is already a Result object, return it directly
        
        result = await self._db_op(_get)
        if result is None:
            return Result.error(
                code="DB_OPERATION_FAILED",
                message="Database operation failed when fetching executions"
            )
        return result
    
    async def cleanup_old_executions(self, days: int) -> int:
        """
        Delete execution records older than specified days.
        
        Args:
            days: Age in days to delete
            
        Returns:
            int: Number of records deleted
        """
        if days <= 0:
            return 0
            
        cutoff_date = datetime.now() - timedelta(days=days)
        
        async def _cleanup():
            async with self._db_session() as session:
                # Find execution records to delete
                read_many_coro = self.crud_service.read_many(
                    session, EventExecution,
                    filters={"start_time": {"lt": cutoff_date}},
                    columns=["id"]
                )
                executions_result = await self.db_service.execute_with_retry(read_many_coro)

                # Check success and data before proceeding
                if not executions_result.success or not executions_result.data:
                    if not executions_result.success:
                         self.logger.warning(error_message(
                            module_id=COMPONENT_ID,
                            error_type="DB_READ_ERROR",
                            details=f"Failed to read executions for cleanup: {executions_result.error}"
                         ))
                    # If success is true but data is empty/None, it's not an error, just nothing to delete
                    return 0

                # Get IDs to delete from the data attribute
                execution_ids = [e.id for e in executions_result.data]
                
                # Delete in batches to avoid locking issues
                batch_size = 100
                deleted_count = 0
                
                for i in range(0, len(execution_ids), batch_size):
                    batch = execution_ids[i:i+batch_size]
                    
                    # Delete batch using a coroutine directly
                    bulk_delete_coro = self.crud_service.bulk_delete(
                        session, EventExecution, {"id": {"in": batch}}
                    )
                    count = await self.db_service.execute_with_retry(bulk_delete_coro)
                    
                    deleted_count += count
                    
                    # Commit each batch separately
                    await session.commit()
                    
                    # Yield control
                    await asyncio.sleep(0)
                
                return deleted_count
        
        return await self._db_op(_cleanup, 0)
    
    # Cleanup configuration operations
    
    async def create_cleanup_config(
        self,
        id: str,
        directory: str,
        pattern: str,
        module_id: str,
        retention_days: Optional[int] = None,
        max_files: Optional[int] = None,
        max_size_mb: Optional[int] = None,
        priority: int = 100,
        description: Optional[str] = None
    ) -> bool:
        """
        Create a new cleanup configuration.
        
        Args:
            id: Unique ID for the configuration
            directory: Path to directory containing files to clean
            pattern: File matching pattern
            module_id: ID of the registering module
            retention_days: Maximum age of files to keep
            max_files: Maximum number of files to keep
            max_size_mb: Maximum total size in MB
            priority: Cleanup priority
            description: Optional description
            
        Returns:
            bool: Whether creation was successful
        """
        config_data = {
            "id": id,
            "directory": directory,
            "pattern": pattern,
            "module_id": module_id,
            "retention_days": retention_days,
            "max_files": max_files,
            "max_size_mb": max_size_mb,
            "priority": priority,
            "description": description,
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
        
        async def _create():
            async with self._db_session() as session:
                # Create a coroutine directly instead of using a lambda
                create_coro = self.crud_service.create(session, CleanupConfig, config_data)
                result = await self.db_service.execute_with_retry(create_coro)
                return result is not None
        
        return await self._db_op(_create, False)
    
    async def update_cleanup_config(
        self,
        id: str,
        **updates
    ) -> bool:
        """
        Update a cleanup configuration.
        
        Args:
            id: ID of the configuration
            **updates: Fields to update
            
        Returns:
            bool: Whether update was successful
        """
        # Always update the updated_at timestamp
        updates["updated_at"] = datetime.now()
        
        async def _update():
            async with self._db_session() as session:
                # Create a coroutine directly instead of using a lambda
                update_coro = self.crud_service.update(
                    session, CleanupConfig, id, updates
                )
                result = await self.db_service.execute_with_retry(update_coro)
                return result is not None
        
        return await self._db_op(_update, False)
    
    async def delete_cleanup_config(self, id: str) -> bool:
        """
        Delete a cleanup configuration.
        
        Args:
            id: ID of the configuration
            
        Returns:
            bool: Whether deletion was successful
        """
        async def _delete():
            async with self._db_session() as session:
                # Create a coroutine directly instead of using a lambda
                delete_coro = self.crud_service.delete(
                    session, CleanupConfig, id
                )
                result = await self.db_service.execute_with_retry(delete_coro)
                return result
        
        return await self._db_op(_delete, False)
    
    async def get_cleanup_config(self, id: str) -> Result:
        """
        Get a cleanup configuration by ID.
        
        Args:
            id: ID of the configuration
            
        Returns:
            Result: Success with configuration data or error information
        """
        async def _get():
            async with self._db_session() as session:
                # Create a coroutine directly instead of using a lambda
                read_coro = self.crud_service.read(session, CleanupConfig, id, as_dict=True)
                result = await self.db_service.execute_with_retry(read_coro)
                if result is None:
                    return Result.error(
                        code="CONFIG_NOT_FOUND",
                        message=f"Cleanup configuration with ID {id} not found"
                    )
                return Result.success(data=result)
        
        result = await self._db_op(_get)
        if result is None:
            return Result.error(
                code="DB_OPERATION_FAILED",
                message=f"Database operation failed when fetching cleanup config {id}"
            )
        return result
    
    async def get_cleanup_configs(
        self,
        filters: Optional[Dict[str, Any]] = None
    ) -> Result:
        """
        Get cleanup configurations with filtering.
        
        Args:
            filters: Optional filters to apply
            
        Returns:
            Result: Success with list of configurations or error information
        """
        async def _get():
            async with self._db_session() as session:
                # Create a coroutine directly instead of using a lambda
                read_many_coro = self.crud_service.read_many(
                    session, CleanupConfig, 
                    filters=filters,
                    order_by=["priority"],
                    as_dict=True
                )
                result = await self.db_service.execute_with_retry(read_many_coro)
                # Don't wrap the result again if it's already a Result object
                if isinstance(result, list):
                    return Result.success(data=result)
                return result  # If the result is already a Result object, return it directly
        
        result = await self._db_op(_get)
        if result is None:
            return Result.error(
                code="DB_OPERATION_FAILED",
                message="Database operation failed when fetching cleanup configs"
            )
        return result

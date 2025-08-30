"""
modules/core/scheduler/services.py
Updated: April 6, 2025
Core service for Scheduler module - migrated to Hybrid Service Pattern
"""

import logging
import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

from core.error_utils import Result, error_message

# Import components
from .database import SchedulerDatabaseOperations
from .components.job_manager import JobManager
from .components.trigger_manager import TriggerManager
from .components.housekeeper import Housekeeper

# Module identity - must match manifest.json
MODULE_ID = "core.scheduler"
logger = logging.getLogger(MODULE_ID)

class SchedulerService:
    """
    Manages scheduled tasks and periodic maintenance operations.
    
    The SchedulerService provides capabilities for scheduling one-time and recurring
    tasks, managing their execution, and handling centralized cleanup operations
    through the Housekeeper component.
    
    This class has been refactored to delegate most functionality to specialized
    components, making it primarily a coordination layer.
    """
    
    def __init__(self, app_context):
        """
        Initialize the scheduler service.
        
        Args:
            app_context: Application context
        """
        self.app_context = app_context
        self.logger = logger
        self.initialized = False
        
        # Database operations
        self.db_ops = SchedulerDatabaseOperations(app_context)
        
        # Create components
        self.job_manager = JobManager(app_context, self)
        self.trigger_manager = TriggerManager(app_context)
        
        # Import here to avoid circular imports
        # The Housekeeper component is implemented in its own file
        self.housekeeper = None
        
        # Background task
        self._scheduler_task = None
        self._is_running = False
        self._shutdown_event = asyncio.Event()
        
        # Track background tasks for proper cleanup
        self._background_tasks = []
        
        self.logger.info(f"{MODULE_ID} service created (pre-Phase 2)")
    
    async def initialize(self, app_context=None, settings=None) -> bool:
        """
        Initialize the scheduler service (Phase 2).
        
        This initializes database operations, components, and starts
        the scheduler background task if enabled.
        
        Args:
            app_context: Optional application context (uses self.app_context if None)
            settings: Optional pre-loaded settings
            
        Returns:
            bool: Whether initialization was successful
        """
        if self.initialized:
            return True
        
        # Use provided app_context or self.app_context
        context = app_context or self.app_context
        
        # Log initialization start
        self.logger.debug(f"{MODULE_ID} service initialization starting")
            
        # Initialize database operations
        if not await self.db_ops.initialize():
            self.logger.error(error_message(
                module_id=MODULE_ID,
                error_type="DB_OPS_INITIALIZATION_FAILED",
                details="Failed to initialize database operations"
            ))
            return False
        
        # Clean up jobs that were left in "running" state from previous shutdown
        try:
            self.logger.debug("Attempting to get running events for cleanup...")
            events_result = await self.db_ops.get_events({"status": "running"})
            # Use repr() for potentially more detailed object info
            self.logger.debug(f"Got events_result for cleanup: type={type(events_result)}, value={repr(events_result)}")
            cleaned_count = 0
            if events_result.success:
                running_events_list = events_result.data
                # Use repr() for potentially more detailed object info
                self.logger.debug(f"Cleanup: events_result successful. Data type={type(running_events_list)}, value={repr(running_events_list)}")
                if isinstance(running_events_list, list):
                    for event in running_events_list:
                        await self.db_ops.update_event(
                            event_id=event.get("id"),
                            updates={
                                "status": "failed",
                                "last_error": "Application shutdown while job was running",
                                "updated_at": datetime.now()
                            }
                        )
                    cleaned_count = len(running_events_list)
                    self.logger.debug(f"Cleanup: Successfully processed {cleaned_count} running events.")
                else:
                     self.logger.error(error_message(
                        module_id=MODULE_ID,
                        error_type="DB_DATA_MISMATCH",
                        details=f"get_events returned success but data is not a list: {type(running_events_list)}"
                     ))
            elif events_result.error:
                 # Use repr() for potentially more detailed error info
                 self.logger.error(error_message(
                    module_id=MODULE_ID,
                    error_type="DB_READ_ERROR",
                    details=f"Failed to get running events: {repr(events_result.error)}"
                 ))

            if cleaned_count > 0:
                self.logger.info(f"Cleaned up {cleaned_count} jobs that were left in 'running' state")
        except Exception as e:
            self.logger.error(error_message(
                module_id=MODULE_ID,
                error_type="EVENT_CLEANUP_ERROR",
                details=f"Error cleaning up running jobs: {str(e)}"
            ))
        
        # Initialize job manager
        if not await self.job_manager.initialize(self.db_ops):
            self.logger.error(error_message(
                module_id=MODULE_ID,
                error_type="JOB_MANAGER_INITIALIZATION_FAILED",
                details="Failed to initialize job manager"
            ))
            return False
            
        # Initialize trigger manager
        if not await self.trigger_manager.initialize():
            self.logger.error(error_message(
                module_id=MODULE_ID,
                error_type="TRIGGER_MANAGER_INITIALIZATION_FAILED",
                details="Failed to initialize trigger manager"
            ))
            return False
        
        # Initialize housekeeper (if not already created, create it now)
        if not self.housekeeper:
            from .components.housekeeper import Housekeeper
            self.housekeeper = Housekeeper(self.app_context, self.job_manager)
        
        if not await self.housekeeper.initialize(self.db_ops):
            self.logger.warning(error_message(
                module_id=MODULE_ID,
                error_type="HOUSEKEEPER_INITIALIZATION_FAILED",
                details="Failed to initialize housekeeper - cleanup functionality will be limited"
            ))
            # Non-critical, continue
        
        # Load settings if not provided
        if settings is None:
            settings = await context.get_module_settings(MODULE_ID)
        
        # Start scheduler if enabled
        if settings.get("enabled", True):
            self._is_running = True
            self.logger.debug(f"Settings fetched, enabled={settings.get('enabled', True)}. Creating scheduler loop task...")
            self._scheduler_task = self._create_background_task(self._scheduler_loop(), "scheduler_loop")
            self.logger.info("Started scheduler background task")
        else:
            self.logger.info("Scheduler disabled in settings - not starting background task")
        
        self.initialized = True
        self.logger.info(f"{MODULE_ID} service initialized successfully")
        return True
    
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
    
    async def shutdown(self) -> None:
        """
        Shut down the scheduler service gracefully.
        
        This stops the background task and cleans up resources.
        Handles the case where the event loop might already be closed.
        """
        if self._is_running and self._scheduler_task:
            self.logger.info(f"Shutting down {MODULE_ID} service")
            self._is_running = False
            self._shutdown_event.set()
            
            try:
                # Check if event loop is still running
                try:
                    loop = asyncio.get_running_loop()
                    if not loop.is_running():
                        raise RuntimeError("Event loop is not running")
                except RuntimeError:
                    # If we can't get the event loop or it's not running,
                    # forcibly cancel the task and return
                    self.logger.warning(error_message(
                        module_id=MODULE_ID,
                        error_type="SHUTDOWN_ERROR",
                        details="Event loop is not available for clean shutdown"
                    ))
                    if not self._scheduler_task.done():
                        self._scheduler_task.cancel()
                    self.logger.info(f"{MODULE_ID} service shut down (forced)")
                    return
                    
                # Try to wait for the task to complete with timeout
                try:
                    await asyncio.wait_for(self._scheduler_task, timeout=5.0)
                except asyncio.TimeoutError:
                    self.logger.warning(error_message(
                        module_id=MODULE_ID,
                        error_type="SHUTDOWN_TIMEOUT",
                        details="Scheduler task didn't shut down cleanly within timeout"
                    ))
                    # Actively cancel the task if it times out
                    self._scheduler_task.cancel()
                except asyncio.CancelledError:
                    self.logger.info("Scheduler task was cancelled")
                except Exception as e:
                    self.logger.warning(error_message(
                        module_id=MODULE_ID,
                        error_type="SHUTDOWN_ERROR",
                        details=f"Error waiting for scheduler task: {str(e)}"
                    ))
                    if not self._scheduler_task.done():
                        self._scheduler_task.cancel()
                
                # Cancel all tracked background tasks
                for task in self._background_tasks:
                    if not task.done():
                        task.cancel()
                
                self.logger.info(f"{MODULE_ID} service shut down")
            except Exception as e:
                # Handle any unexpected errors during shutdown
                self.logger.error(error_message(
                    module_id=MODULE_ID,
                    error_type="SHUTDOWN_ERROR",
                    details=f"Error during scheduler shutdown: {str(e)}"
                ))
                # Make a best effort to cancel the task
                if self._scheduler_task and not self._scheduler_task.done():
                    try:
                        self._scheduler_task.cancel()
                    except Exception:
                        pass
                self.logger.info(f"{MODULE_ID} service shut down (with errors)")
    
    def force_shutdown(self):
        """
        Force shutdown of the scheduler service when the event loop is closing or closed.
        This is a synchronous method that can be called in any context.
        """
        if hasattr(self, '_scheduler_task') and self._scheduler_task:
            self.logger.info(f"Force shutting down {MODULE_ID} service")
            self._is_running = False
            
            try:
                if hasattr(self._scheduler_task, 'cancel') and not self._scheduler_task.done():
                    self._scheduler_task.cancel()
                    self.logger.info("Scheduler task cancelled during force shutdown")
            except Exception as e:
                self.logger.warning(error_message(
                    module_id=MODULE_ID,
                    error_type="FORCE_SHUTDOWN_ERROR",
                    details=f"Error during force scheduler shutdown: {str(e)}"
                ))
                
            self.logger.info(f"{MODULE_ID} service force shut down")
    
    async def _scheduler_loop(self) -> None:
        """
        Main scheduler loop that checks for due events and executes them.
        
        This runs as a background task until shutdown is requested.
        """
        # Get settings
        settings = await self.app_context.get_module_settings(MODULE_ID)
        check_interval = settings.get("check_interval", 1.0)
        
        self.logger.info(f"Scheduler loop started with check interval: {check_interval}s")
        
        while self._is_running:
            try:
                # Check for due events
                await self._check_due_events()
                
                # Perform periodic cleanup if enabled
                if (
                    settings.get("auto_cleanup_enabled", True) and 
                    self.db_ops
                ):
                    # Only run cleanup occasionally (not every cycle)
                    # Use event count as a simple counter
                    events_result = await self.db_ops.get_events({"status": "pending"}, limit=1)
                    if events_result.success:
                        events_list = events_result.data
                        # Check if data is a list and not empty before using len
                        if isinstance(events_list, list) and events_list:
                            # Use a simple counter based on whether we got any event
                            # The modulo check was arbitrary, let's simplify
                            # We can use a class attribute as a counter if needed,
                            # but for now, just run cleanup if an event was found.
                            # if len(events_list) % 100 == 0: # Original logic
                            
                            # Simplified: Run cleanup if we found a pending event
                            retention_days = settings.get("retention_days", 30)
                            await self.db_ops.cleanup_old_executions(retention_days)
                    elif events_result.error:
                         self.logger.warning(error_message(
                            module_id=MODULE_ID,
                            error_type="DB_READ_ERROR",
                            details=f"Failed to get pending events for cleanup check: {events_result.error}"
                        ))
                
                # Wait for next check or shutdown
                try:
                    # Use wait_for with timeout to allow for shutdown
                    await asyncio.wait_for(
                        self._shutdown_event.wait(),
                        timeout=check_interval
                    )
                    if self._shutdown_event.is_set():
                        break  # Exit the loop if shutdown was requested
                except asyncio.TimeoutError:
                    # Timeout is expected, continue the loop
                    pass
                
                # Yield control to other tasks
                await asyncio.sleep(0)
            
            except Exception as e:
                self.logger.error(error_message(
                    module_id=MODULE_ID,
                    error_type="SCHEDULER_LOOP_ERROR",
                    details=f"Error in scheduler loop: {str(e)}"
                ))
                # Continue running despite errors
                await asyncio.sleep(check_interval)
        
        self.logger.info("Scheduler loop stopped")
    
    async def _check_due_events(self) -> None:
        """
        Check for events that are due for execution and run them.
        """
        if not self.db_ops:
            return
        
        # Get settings
        settings = await self.app_context.get_module_settings(MODULE_ID)
        max_concurrent = settings.get("max_concurrent_executions", 10)
        
        # Get currently running executions
        running_executions_result = await self.db_ops.get_executions(
            filters={"end_time": None}  # Null end_time means still running
        )

        num_running = 0
        if running_executions_result.success:
            running_executions_list = running_executions_result.data
            if isinstance(running_executions_list, list):
                num_running = len(running_executions_list)
            else:
                 self.logger.warning(error_message(
                    module_id=MODULE_ID,
                    error_type="DB_DATA_MISMATCH",
                    details=f"get_executions returned success but data is not a list: {type(running_executions_list)}"
                ))
        elif running_executions_result.error:
            self.logger.warning(error_message(
                module_id=MODULE_ID,
                error_type="DB_READ_ERROR",
                details=f"Failed to get running executions: {running_executions_result.error}"
            ))
            # If we can't check running executions, maybe don't proceed? Or assume 0?
            # For now, let's assume 0 and log the error, allowing due events check to proceed.
            num_running = 0

        # Skip if at max concurrent executions
        if num_running >= max_concurrent:
            return
        
        # Calculate how many more we can start
        available_slots = max_concurrent - num_running
        
        # Get due events
        now = datetime.now()
        due_events_result = await self.db_ops.get_due_events(now, limit=available_slots)
        
        due_events_list = []
        if due_events_result.success:
            if isinstance(due_events_result.data, list):
                due_events_list = due_events_result.data
            elif due_events_result.data is not None:
                self.logger.warning(error_message(
                    module_id=MODULE_ID,
                    error_type="DB_DATA_MISMATCH",
                    details=f"get_due_events returned success but data is not a list: {type(due_events_result.data)}"
                ))
        elif due_events_result.error:
            self.logger.warning(error_message(
                module_id=MODULE_ID,
                error_type="DB_READ_ERROR",
                details=f"Failed to get due events: {due_events_result.error}"
            ))
            # If we failed to get due events, return early
            return

        if not due_events_list:
            return
        
        # Start task for each due event
        for event in due_events_list:
            # Skip if already running
            if event.get("status") == "running":
                continue
                
            # Update event status to running
            await self.db_ops.update_event(
                event_id=event.get("id"),
                updates={"status": "running"}
            )
            
            # Start execution in background task
            self._create_background_task(self._execute_event(event), f"event_{event.get('id')}")
    
    async def _execute_event(self, event: Dict[str, Any]) -> None:
        """
        Execute a scheduled event.
        
        Args:
            event: Event data dictionary
        """
        # Create execution record
        execution_id = str(uuid.uuid4())
        
        # Get settings for retry and recurring logic
        settings = await self.app_context.get_module_settings(MODULE_ID)
        
        # Log execution start
        self.logger.debug(f"Executing event {event.get('id')}: {event.get('name')}")
        
        # Create execution record
        await self.db_ops.create_execution(
            id=execution_id,
            event_id=event.get("id"),
            start_time=datetime.now(),
            trace_session_id=None
        )
        
        try:
            # Execute the job using job manager
            result = await self.job_manager.execute_job(event.get("id"))
            
            # Check execution result - handle both Result objects and legacy dict format
            if hasattr(result, 'success'):
                # New Result object format
                success = result.success
                error = result.error if not result.success else {}
            else:
                # Legacy dict format for backwards compatibility
                success = result.get("success", False)
                error = result.get("error", {})
            
            # Update event status
            updates = {
                "status": "completed" if success else "failed",
                "last_execution": datetime.now(),
                "execution_count": event.get("execution_count", 0) + 1
            }
            
            # For failed events
            if not success:
                updates["last_error"] = str(error)
                
                # Handle retry if enabled
                if settings.get("retry_failed_events", True):
                    max_retries = settings.get("max_retry_attempts", 3)
                    retry_delay = settings.get("retry_delay", 300)  # seconds
                    
                    # Check if we should retry
                    if event.get("execution_count", 0) < max_retries:
                        # Calculate next execution time with delay
                        next_execution = datetime.now() + timedelta(seconds=retry_delay)
                        updates["status"] = "pending"
                        updates["next_execution"] = next_execution
            
            # For recurring events
            if event.get("recurring", False) and (success or not settings.get("retry_failed_events", True)):
                # Calculate next execution time using trigger manager
                interval_type = event.get("interval_type")
                interval_value = event.get("interval_value", 1)
                
                if interval_type == "cron":
                    # Special handling for cron - need to use parameters
                    parameters = event.get("parameters", {})
                    cron_expression = parameters.get("_cron_expression")
                    
                    if cron_expression:
                        next_execution = self.trigger_manager.get_next_execution_time(
                            "cron",
                            {"cron_expression": cron_expression},
                            event.get("next_execution", datetime.now())
                        )
                    else:
                        # Fallback if cron expression not found
                        next_execution = datetime.now() + timedelta(days=1)
                else:
                    # Standard interval
                    next_execution = self.trigger_manager.get_next_execution_time(
                        "interval",
                        {
                            "interval": interval_value,
                            "interval_unit": interval_type,
                            "start_date": event.get("next_execution", datetime.now())
                        },
                        event.get("next_execution", datetime.now())
                    )
                
                # Update next execution time and status
                if next_execution:
                    updates["next_execution"] = next_execution
                    updates["status"] = "pending"
            
            # Check max executions limit
            max_executions = event.get("max_executions")
            if max_executions is not None and event.get("execution_count", 0) + 1 >= max_executions:
                updates["status"] = "completed"
            
            # Update the event
            await self.db_ops.update_event(
                event_id=event.get("id"),
                updates=updates
            )
            
            # Log execution completion
            status = "completed" if success else "failed"
            next_exec = updates.get("next_execution")
            self.logger.debug(f"Event {event.get('id')} execution {status}, next: {next_exec}")
            
        except Exception as e:
            # Log the error
            self.logger.error(error_message(
                module_id=MODULE_ID,
                error_type="EVENT_EXECUTION_ERROR",
                details=f"Error executing event {event.get('id')}: {str(e)}"
            ))
            
            # Update execution record with error
            await self.db_ops.update_execution(
                execution_id=execution_id,
                updates={
                    "end_time": datetime.now(),
                    "success": False,
                    "error": str(e)
                }
            )
            
            # Update event status
            await self.db_ops.update_event(
                event_id=event.get("id"),
                updates={
                    "status": "failed",
                    "last_execution": datetime.now(),
                    "execution_count": event.get("execution_count", 0) + 1,
                    "last_error": str(e)
                }
            )
    
    # Public API methods - These methods need to use Result objects consistently
    
    async def schedule_event(
        self,
        name: str,
        function_name: str,
        next_execution: datetime,
        module_id: str,
        recurring: bool = False,
        interval_type: Optional[str] = None,
        interval_value: Optional[int] = None,
        parameters: Optional[Dict[str, Any]] = None,
        description: Optional[str] = None
    ) -> Result:
        """
        Schedule a new event.
        
        Args:
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
            Result: Success with event_id or error information
        """
        if not self.initialized:
            self.logger.warning(error_message(
                module_id=MODULE_ID,
                error_type="NOT_INITIALIZED",
                details="Scheduler service not initialized"
            ))
            return Result.error(
                code="NOT_INITIALIZED",
                message="Scheduler service not initialized"
            )
        
        try:
            # Validate parameters
            if recurring and (not interval_type or not interval_value):
                return Result.error(
                    code="INVALID_PARAMETERS",
                    message="Recurring events require interval_type and interval_value"
                )
            
            if recurring and interval_type not in ("minutes", "hours", "days", "weeks", "months", "cron"):
                return Result.error(
                    code="INVALID_PARAMETERS",
                    message="interval_type must be one of: minutes, hours, days, weeks, months, cron"
                )
            
            # Check if we allow scheduling in the past
            settings = await self.app_context.get_module_settings(MODULE_ID)
            allow_past = settings.get("allow_past_events", False)
            
            if not allow_past and next_execution < datetime.now():
                return Result.error(
                    code="PAST_SCHEDULING_NOT_ALLOWED",
                    message="Cannot schedule events in the past"
                )
            
            # Generate ID
            event_id = str(uuid.uuid4())
            
            # Create event
            if recurring:
                if interval_type == "cron":
                    # Special handling for cron
                    cron_expression = parameters.get("_cron_expression") if parameters else None
                    if not cron_expression:
                        return Result.error(
                            code="MISSING_CRON_EXPRESSION",
                            message="Cron events require _cron_expression parameter"
                        )
                        
                    event_id = await self.job_manager._schedule_cron_event(
                        name=name,
                        description=description or "",
                        function_name=function_name,
                        next_execution=next_execution,
                        cron_expression=cron_expression,
                        parameters=parameters or {}
                    )
                else:
                    # Standard recurring event
                    event_id = await self.job_manager._schedule_recurring_event(
                        name=name,
                        description=description or "",
                        function_name=function_name,
                        start_time=next_execution,
                        interval_type=interval_type,
                        interval_value=interval_value,
                        parameters=parameters or {}
                    )
            else:
                # One-time event
                event_id = await self.job_manager._schedule_one_time_event(
                    name=name,
                    description=description or "",
                    function_name=function_name,
                    execution_time=next_execution,
                    parameters=parameters or {}
                )
            
            return Result.success(data={"event_id": event_id})
            
        except ValueError as e:
            self.logger.error(error_message(
                module_id=MODULE_ID,
                error_type="VALIDATION_ERROR",
                details=f"Parameter validation error: {str(e)}"
            ))
            return Result.error(
                code="VALIDATION_ERROR",
                message=str(e)
            )
        except Exception as e:
            self.logger.error(error_message(
                module_id=MODULE_ID,
                error_type="SCHEDULING_ERROR",
                details=f"Error scheduling event: {str(e)}"
            ))
            return Result.error(
                code="SCHEDULING_ERROR",
                message=f"Failed to schedule event: {str(e)}"
            )
    
    async def get_event(self, event_id: str) -> Result:
        """
        Get a scheduled event by ID.
        
        Args:
            event_id: ID of the event
            
        Returns:
            Result: Success with event data or error information
        """
        if not self.initialized or not self.db_ops:
            self.logger.warning(error_message(
                module_id=MODULE_ID,
                error_type="NOT_INITIALIZED",
                details="Scheduler service not initialized"
            ))
            return Result.error(
                code="NOT_INITIALIZED",
                message="Scheduler service not initialized"
            )
        
        try:
            event = await self.db_ops.get_event(event_id)
            if not event:
                return Result.error(
                    code="EVENT_NOT_FOUND",
                    message=f"Event with ID {event_id} not found"
                )
            
            return Result.success(data=event)
        except Exception as e:
            self.logger.error(error_message(
                module_id=MODULE_ID,
                error_type="EVENT_FETCH_ERROR",
                details=f"Error fetching event {event_id}: {str(e)}"
            ))
            return Result.error(
                code="EVENT_FETCH_ERROR",
                message=f"Failed to fetch event: {str(e)}"
            )
    
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
        if not self.initialized or not self.db_ops:
            self.logger.warning(error_message(
                module_id=MODULE_ID,
                error_type="NOT_INITIALIZED",
                details="Scheduler service not initialized"
            ))
            return Result.error(
                code="NOT_INITIALIZED",
                message="Scheduler service not initialized"
            )
        
        try:
            events = await self.db_ops.get_events(filters, limit)
            return Result.success(data=events)
        except Exception as e:
            self.logger.error(error_message(
                module_id=MODULE_ID,
                error_type="EVENT_FETCH_ERROR",
                details=f"Error fetching events: {str(e)}"
            ))
            return Result.error(
                code="EVENT_FETCH_ERROR",
                message=f"Failed to fetch events: {str(e)}"
            )
    
    async def update_event(
        self,
        event_id: str,
        updates: Dict[str, Any]
    ) -> Result:
        """
        Update a scheduled event.
        
        Args:
            event_id: ID of the event
            updates: Dictionary of fields to update
            
        Returns:
            Result: Success or error information
        """
        if not self.initialized or not self.db_ops:
            self.logger.warning(error_message(
                module_id=MODULE_ID,
                error_type="NOT_INITIALIZED",
                details="Scheduler service not initialized"
            ))
            return Result.error(
                code="NOT_INITIALIZED",
                message="Scheduler service not initialized"
            )
        
        try:
            # First check if event exists
            event = await self.db_ops.get_event(event_id)
            if not event:
                return Result.error(
                    code="EVENT_NOT_FOUND",
                    message=f"Event with ID {event_id} not found"
                )
                
            success = await self.db_ops.update_event(event_id, updates)
            if not success:
                return Result.error(
                    code="UPDATE_FAILED",
                    message=f"Failed to update event {event_id}"
                )
                
            return Result.success(data={"updated": True})
        except Exception as e:
            self.logger.error(error_message(
                module_id=MODULE_ID,
                error_type="EVENT_UPDATE_ERROR",
                details=f"Error updating event {event_id}: {str(e)}"
            ))
            return Result.error(
                code="EVENT_UPDATE_ERROR",
                message=f"Failed to update event: {str(e)}"
            )
    
    async def delete_event(self, event_id: str) -> Result:
        """
        Delete a scheduled event.
        
        Args:
            event_id: ID of the event
            
        Returns:
            Result: Success or error information
        """
        if not self.initialized or not self.db_ops:
            self.logger.warning(error_message(
                module_id=MODULE_ID,
                error_type="NOT_INITIALIZED",
                details="Scheduler service not initialized"
            ))
            return Result.error(
                code="NOT_INITIALIZED",
                message="Scheduler service not initialized"
            )
        
        try:
            # First check if event exists
            event = await self.db_ops.get_event(event_id)
            if not event:
                return Result.error(
                    code="EVENT_NOT_FOUND",
                    message=f"Event with ID {event_id} not found"
                )
                
            success = await self.db_ops.delete_event(event_id)
            if not success:
                return Result.error(
                    code="DELETE_FAILED",
                    message=f"Failed to delete event {event_id}"
                )
                
            return Result.success(data={"deleted": True})
        except Exception as e:
            self.logger.error(error_message(
                module_id=MODULE_ID,
                error_type="EVENT_DELETE_ERROR",
                details=f"Error deleting event {event_id}: {str(e)}"
            ))
            return Result.error(
                code="EVENT_DELETE_ERROR",
                message=f"Failed to delete event: {str(e)}"
            )
    
    async def pause_event(self, event_id: str) -> Result:
        """
        Pause a scheduled event.
        
        Args:
            event_id: ID of the event
            
        Returns:
            Result: Success or error information
        """
        if not self.initialized or not self.db_ops:
            self.logger.warning(error_message(
                module_id=MODULE_ID,
                error_type="NOT_INITIALIZED",
                details="Scheduler service not initialized"
            ))
            return Result.error(
                code="NOT_INITIALIZED",
                message="Scheduler service not initialized"
            )
        
        try:
            # First check if event exists and get current status
            event_result = await self.get_event(event_id)
            if not event_result.success:
                return event_result  # Propagate error
                
            event = event_result.data
            if event.get("status") == "paused":
                return Result.error(
                    code="ALREADY_PAUSED",
                    message=f"Event {event_id} is already paused"
                )
                
            success = await self.db_ops.update_event(
                event_id=event_id,
                updates={"status": "paused"}
            )
            
            if not success:
                return Result.error(
                    code="PAUSE_FAILED",
                    message=f"Failed to pause event {event_id}"
                )
                
            return Result.success(data={"paused": True})
        except Exception as e:
            self.logger.error(error_message(
                module_id=MODULE_ID,
                error_type="EVENT_PAUSE_ERROR",
                details=f"Error pausing event {event_id}: {str(e)}"
            ))
            return Result.error(
                code="EVENT_PAUSE_ERROR",
                message=f"Failed to pause event: {str(e)}"
            )
    
    async def resume_event(self, event_id: str) -> Result:
        """
        Resume a paused event.
        
        Args:
            event_id: ID of the event
            
        Returns:
            Result: Success or error information
        """
        if not self.initialized or not self.db_ops:
            self.logger.warning(error_message(
                module_id=MODULE_ID,
                error_type="NOT_INITIALIZED",
                details="Scheduler service not initialized"
            ))
            return Result.error(
                code="NOT_INITIALIZED",
                message="Scheduler service not initialized"
            )
        
        try:
            # First check if event exists and get current status
            event_result = await self.get_event(event_id)
            if not event_result.success:
                return event_result  # Propagate error
                
            event = event_result.data
            if event.get("status") != "paused":
                return Result.error(
                    code="NOT_PAUSED",
                    message=f"Event {event_id} is not paused (current status: {event.get('status')})"
                )
                
            success = await self.db_ops.update_event(
                event_id=event_id,
                updates={"status": "pending"}
            )
            
            if not success:
                return Result.error(
                    code="RESUME_FAILED",
                    message=f"Failed to resume event {event_id}"
                )
                
            return Result.success(data={"resumed": True})
        except Exception as e:
            self.logger.error(error_message(
                module_id=MODULE_ID,
                error_type="EVENT_RESUME_ERROR",
                details=f"Error resuming event {event_id}: {str(e)}"
            ))
            return Result.error(
                code="EVENT_RESUME_ERROR",
                message=f"Failed to resume event: {str(e)}"
            )
    
    async def execute_event_now(self, event_id: str) -> Result:
        """
        Execute an event immediately, regardless of its scheduled time.
        
        Args:
            event_id: ID of the event
            
        Returns:
            Result: Success with execution information or error information
        """
        if not self.initialized:
            self.logger.warning(error_message(
                module_id=MODULE_ID,
                error_type="NOT_INITIALIZED",
                details="Scheduler service not initialized"
            ))
            return Result.error(
                code="NOT_INITIALIZED",
                message="Scheduler service not initialized"
            )
        
        try:
            # First check if event exists
            event_result = await self.get_event(event_id)
            if not event_result.success:
                return event_result  # Propagate error
                
            event = event_result.data
            if event.get("status") == "running":
                return Result.error(
                    code="ALREADY_RUNNING",
                    message=f"Event {event_id} is already running"
                )
                
            # Delegate to job manager
            return await self.job_manager.execute_job(event_id)
        except Exception as e:
            self.logger.error(error_message(
                module_id=MODULE_ID,
                error_type="EVENT_EXECUTION_ERROR",
                details=f"Error executing event {event_id}: {str(e)}"
            ))
            return Result.error(
                code="EVENT_EXECUTION_ERROR",
                message=f"Failed to execute event: {str(e)}"
            )
    
    # Housekeeper methods - delegate to housekeeper component
    
    async def register_cleanup(
        self,
        directory: str,
        pattern: str = "*",
        retention_days: Optional[int] = None,
        max_files: Optional[int] = None,
        max_size_mb: Optional[int] = None,
        priority: int = 100,
        description: Optional[str] = None,
        module_id: Optional[str] = None
    ) -> str:
        """
        Register a directory for periodic cleanup.
        
        Delegates to the Housekeeper component.
        
        Returns:
            str: Registration ID or raises an exception
        """
        if not self.initialized or not self.housekeeper:
            self.logger.warning(error_message(
                module_id=MODULE_ID,
                error_type="NOT_INITIALIZED",
                details="Scheduler service or housekeeper not initialized"
            ))
            raise RuntimeError("Scheduler service or housekeeper not initialized")
        
        return await self.housekeeper.register_cleanup(
            directory=directory,
            pattern=pattern,
            retention_days=retention_days,
            max_files=max_files,
            max_size_mb=max_size_mb,
            priority=priority,
            description=description,
            module_id=module_id
        )
    
    async def get_cleanup_configs(self, module_id: Optional[str] = None) -> Result:
        """
        Get all registered cleanup configurations.
        
        Delegates to the Housekeeper component.
        
        Args:
            module_id: Optional module ID to filter by
            
        Returns:
            Result: Success with list of configs or error information
        """
        if not self.initialized or not self.housekeeper:
            self.logger.warning(error_message(
                module_id=MODULE_ID,
                error_type="NOT_INITIALIZED",
                details="Scheduler service or housekeeper not initialized"
            ))
            return Result.error(
                code="NOT_INITIALIZED",
                message="Scheduler service or housekeeper not initialized"
            )
        
        try:
            configs = await self.housekeeper.get_cleanup_configs(module_id)
            return Result.success(data=configs)
        except Exception as e:
            self.logger.error(error_message(
                module_id=MODULE_ID,
                error_type="CONFIG_FETCH_ERROR",
                details=f"Error fetching cleanup configs: {str(e)}"
            ))
            return Result.error(
                code="CONFIG_FETCH_ERROR", 
                message=f"Failed to fetch cleanup configs: {str(e)}"
            )
    
    async def run_cleanup(self, registration_id: Optional[str] = None, dry_run: bool = False) -> Result:
        """
        Run cleanup operations manually.
        
        Delegates to the Housekeeper component.
        
        Args:
            registration_id: Optional ID of specific config to run
            dry_run: If true, only report what would be deleted
            
        Returns:
            Result: Success with cleanup results or error information
        """
        if not self.initialized or not self.housekeeper:
            self.logger.warning(error_message(
                module_id=MODULE_ID,
                error_type="NOT_INITIALIZED",
                details="Scheduler service or housekeeper not initialized"
            ))
            return Result.error(
                code="NOT_INITIALIZED",
                message="Scheduler service or housekeeper not initialized"
            )
        
        try:
            result = await self.housekeeper.run_cleanup(registration_id, dry_run)
            
            # If result already has success field, wrap it as a Result object
            if isinstance(result, dict) and "success" in result:
                if result.get("success", False):
                    return Result.success(data=result)
                else:
                    return Result.error(
                        code=result.get("error", {}).get("code", "CLEANUP_ERROR"),
                        message=result.get("error", {}).get("message", "Cleanup operation failed"),
                        details=result.get("error", {}).get("details")
                    )
            
            # Otherwise return success with the result as data
            return Result.success(data=result)
        except Exception as e:
            self.logger.error(error_message(
                module_id=MODULE_ID, 
                error_type="CLEANUP_ERROR",
                details=f"Error running cleanup: {str(e)}"
            ))
            return Result.error(
                code="CLEANUP_ERROR",
                message=f"Failed to run cleanup: {str(e)}"
            )

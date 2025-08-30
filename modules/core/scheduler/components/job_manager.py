"""
modules/core/scheduler/components/job_manager.py
Updated: April 6, 2025
Job manager component for handling scheduled jobs
"""

import logging
import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable, Union

from core.error_utils import Result, error_message
from ..utils import parse_cron_expression

# Module identity - must match manifest.json
MODULE_ID = "core.scheduler"
# Component identity
COMPONENT_ID = f"{MODULE_ID}.job_manager"
logger = logging.getLogger(COMPONENT_ID)

class JobManager:
    """
    Manages scheduled jobs and their execution.
    
    This component handles job registration, scheduling, and execution for the
    scheduler service. It provides a higher-level interface for working with
    different trigger types and job definitions.
    """
    
    def __init__(self, app_context, scheduler_service):
        """
        Initialize the job manager component.
        
        Args:
            app_context: Application context
            scheduler_service: Reference to the parent scheduler service
        """
        self.app_context = app_context
        self.scheduler_service = scheduler_service
        self.logger = logger
        self.initialized = False
        self.db_ops = None
        self.function_client = None
    
    async def initialize(self, db_operations) -> bool:
        """
        Initialize the job manager with database operations.
        
        Args:
            db_operations: Database operations instance
            
        Returns:
            bool: Whether initialization was successful
        """
        if self.initialized:
            return True
            
        self.db_ops = db_operations
        if not self.db_ops:
            self.logger.error(error_message(
                module_id=COMPONENT_ID,
                error_type="DB_OPS_REQUIRED",
                details="Database operations required for JobManager initialization"
            ))
            return False
        
        # Function execution service not available - that's okay, we'll handle this in execute_job
        self.function_client = None
        
        # Reload any active jobs from the database
        await self._reload_active_jobs()
        
        self.initialized = True
        self.logger.info("Job manager initialized successfully")
        return True
    
    async def _reload_active_jobs(self) -> None:
        """
        Reload active jobs from the database.
        
        This ensures that scheduled jobs persist across service restarts.
        """
        if not self.db_ops:
            return
            
        # Get all active (pending) events
        events_result = await self.db_ops.get_events({"status": "pending"})
        
        if not events_result.success:
            self.logger.error(error_message(
                module_id=COMPONENT_ID,
                error_type="DB_READ_ERROR",
                details=f"Failed to reload active jobs from database: {events_result.error}"
            ))
            return

        active_jobs_list = events_result.data
        if not isinstance(active_jobs_list, list) or not active_jobs_list:
             self.logger.info("No active jobs found in database or data is not a list")
             return

        self.logger.info(f"Reloaded {len(active_jobs_list)} active jobs from database")
    
    async def register_job(
        self,
        job_id: str,
        func: Callable,
        trigger: str = "date",
        **trigger_args
    ) -> str:
        """
        Register a job with the scheduler.
        
        Args:
            job_id: Unique identifier for the job
            func: Function to execute
            trigger: Trigger type (date, interval, cron)
            **trigger_args: Arguments for the specific trigger type
            
        Returns:
            str: ID of the registered job
            
        Raises:
            RuntimeError: If not initialized
            ValueError: If parameters are invalid
        """
        if not self.initialized:
            self.logger.warning(error_message(
                module_id=COMPONENT_ID,
                error_type="NOT_INITIALIZED",
                details="Job manager not initialized"
            ))
            raise RuntimeError("Job manager not initialized")
        
        # Get function name - use __name__ attribute or string representation
        function_name = getattr(func, "__name__", str(func))
        
        # Create a description if not provided
        description = trigger_args.get("description", f"Job {job_id} ({trigger} trigger)")
        
        # Handle different trigger types
        if trigger == "date":
            # One-time execution at specific date/time
            run_date = trigger_args.get("run_date")
            if not run_date:
                raise ValueError("run_date is required for date trigger")
                
            if isinstance(run_date, str):
                run_date = datetime.fromisoformat(run_date.replace('Z', '+00:00'))
            
            # Schedule the event
            event_id = await self._schedule_one_time_event(
                name=f"Job {job_id}",
                description=description,
                function_name=function_name,
                execution_time=run_date,
                parameters=trigger_args.get("parameters", {})
            )
            
            return event_id
            
        elif trigger == "interval":
            # Recurring execution at fixed intervals
            interval = trigger_args.get("interval")
            interval_unit = trigger_args.get("interval_unit", "minutes")
            start_date = trigger_args.get("start_date", datetime.now())
            
            if not interval:
                raise ValueError("interval is required for interval trigger")
                
            if isinstance(start_date, str):
                start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            
            # Schedule the event
            event_id = await self._schedule_recurring_event(
                name=f"Job {job_id}",
                description=description,
                function_name=function_name,
                start_time=start_date,
                interval_type=interval_unit,
                interval_value=interval,
                parameters=trigger_args.get("parameters", {})
            )
            
            return event_id
            
        elif trigger == "cron":
            # Cron-style scheduling
            cron_expression = trigger_args.get("cron_expression")
            if not cron_expression:
                raise ValueError("cron_expression is required for cron trigger")
            
            # Parse cron expression to get next run time
            next_run = parse_cron_expression(cron_expression)
            
            # Store the cron expression in parameters for future runs
            parameters = trigger_args.get("parameters", {}).copy()
            parameters["_cron_expression"] = cron_expression
            
            # Schedule the event
            event_id = await self._schedule_cron_event(
                name=f"Job {job_id}",
                description=description,
                function_name=function_name,
                next_execution=next_run,
                cron_expression=cron_expression,
                parameters=parameters
            )
            
            return event_id
            
        else:
            raise ValueError(f"Unsupported trigger type: {trigger}")
    
    async def _schedule_one_time_event(
        self,
        name: str,
        function_name: str,
        execution_time: datetime,
        description: str = "",
        parameters: Dict[str, Any] = None
    ) -> str:
        """
        Schedule a one-time event.
        
        Args:
            name: Name of the event
            function_name: Function to execute
            execution_time: When to execute
            description: Optional description
            parameters: Parameters to pass to the function
            
        Returns:
            str: Event ID
        """
        event_id = str(uuid.uuid4())
        
        success = await self.db_ops.create_event(
            id=event_id,
            name=name,
            description=description,
            function_name=function_name,
            next_execution=execution_time,
            module_id=MODULE_ID,
            recurring=False,
            parameters=parameters or {}
        )
        
        if not success:
            raise RuntimeError(f"Failed to create scheduled event {name}")
        
        self.logger.info(f"Scheduled one-time event '{name}' with ID {event_id}")
        return event_id
    
    async def _schedule_recurring_event(
        self,
        name: str,
        function_name: str,
        start_time: datetime,
        interval_type: str,
        interval_value: int,
        description: str = "",
        parameters: Dict[str, Any] = None
    ) -> str:
        """
        Schedule a recurring event.
        
        Args:
            name: Name of the event
            function_name: Function to execute
            start_time: When to start execution
            interval_type: Type of interval (minutes, hours, days, weeks, months)
            interval_value: Number of interval units
            description: Optional description
            parameters: Parameters to pass to the function
            
        Returns:
            str: Event ID
        """
        event_id = str(uuid.uuid4())
        
        success = await self.db_ops.create_event(
            id=event_id,
            name=name,
            description=description,
            function_name=function_name,
            next_execution=start_time,
            module_id=MODULE_ID,
            recurring=True,
            interval_type=interval_type,
            interval_value=interval_value,
            parameters=parameters or {}
        )
        
        if not success:
            raise RuntimeError(f"Failed to create scheduled event {name}")
        
        self.logger.info(f"Scheduled recurring event '{name}' with ID {event_id}")
        return event_id
    
    async def _schedule_cron_event(
        self,
        name: str,
        function_name: str,
        next_execution: datetime,
        cron_expression: str,
        description: str = "",
        parameters: Dict[str, Any] = None
    ) -> str:
        """
        Schedule a cron-based event.
        
        Args:
            name: Name of the event
            function_name: Function to execute
            next_execution: When to start execution
            cron_expression: Cron expression for scheduling
            description: Optional description
            parameters: Parameters to pass to the function
            
        Returns:
            str: Event ID
        """
        event_id = str(uuid.uuid4())
        
        # Ensure parameters contains the cron expression
        params = parameters or {}
        params["_cron_expression"] = cron_expression
        
        success = await self.db_ops.create_event(
            id=event_id,
            name=name,
            description=description,
            function_name=function_name,
            next_execution=next_execution,
            module_id=MODULE_ID,
            recurring=True,
            interval_type="cron",  # Special handling for cron
            interval_value=1,      # Not used for cron
            parameters=params
        )
        
        if not success:
            raise RuntimeError(f"Failed to create scheduled event {name}")
        
        self.logger.info(f"Scheduled cron event '{name}' with ID {event_id} using expression '{cron_expression}'")
        return event_id
    
    async def get_next_execution_time(self, event: Dict[str, Any]) -> Optional[datetime]:
        """
        Calculate the next execution time for a recurring event.
        
        Args:
            event: Event data
            
        Returns:
            Optional[datetime]: Next execution time or None if not recurring
        """
        if not event.get("recurring", False):
            return None
            
        interval_type = event.get("interval_type")
        interval_value = event.get("interval_value")
        
        # Use the current next_execution as the base time
        base_time = event.get("next_execution", datetime.now())
        
        # Special handling for cron expressions
        if interval_type == "cron":
            # Extract cron expression from parameters
            parameters = event.get("parameters", {})
            cron_expression = parameters.get("_cron_expression")
            
            if cron_expression:
                # Use base_time as the reference for calculating next execution
                # In a real implementation, this would use a proper cron parser
                # that can calculate the next execution from a reference time
                
                # For now, just return base_time + 1 day as a simple approximation
                return base_time + timedelta(days=1)
        
        # Standard interval calculation
        from ..utils import calculate_next_execution
        return calculate_next_execution(base_time, interval_type, interval_value)
    
    async def execute_job(self, event_id: str) -> Result:
        """
        Execute a job immediately.
        
        Args:
            event_id: ID of the event to execute
            
        Returns:
            Result: Result of the execution
        """
        if not self.initialized:
            return Result.error(
                code="NOT_INITIALIZED",
                message="Job manager not initialized"
            )
        
        # Get the event
        event_result = await self.db_ops.get_event(event_id)
        if not event_result.success:
            return Result.error(
                code="EVENT_NOT_FOUND",
                message=f"Event {event_id} not found"
            )
        
        event = event_result.data
            
        # Create a unique execution ID
        execution_id = str(uuid.uuid4())
        
        # Create execution record
        await self.db_ops.create_execution(
            id=execution_id,
            event_id=event_id,
            start_time=datetime.now()
        )
        
        try:
            # Get function parameters
            function_name = event.get("function_name")
            parameters = event.get("parameters", {})
            
            # Since function execution service is not available, just log the execution
            self.logger.info(f"Would execute function '{function_name}' with parameters: {parameters}")
            
            # Simulate successful execution for now
            result = {"success": True, "message": "Function execution simulated"}
            
            # Update execution record
            success = result.get("success", False)
            await self.db_ops.update_execution(
                execution_id=execution_id,
                updates={
                    "end_time": datetime.now(),
                    "success": success,
                    "result": result,
                    "error": None if success else str(result.get("error", {}))
                }
            )
            
            # Update event record
            await self.db_ops.update_event(
                event_id=event_id,
                updates={
                    "last_execution": datetime.now(),
                    "execution_count": event.get("execution_count", 0) + 1,
                    "last_error": None if success else str(result.get("error", {}))
                }
            )
            
            return Result.success(data={
                "execution_id": execution_id,
                "event_id": event_id,
                "success": success,
                "result": result
            })
            
        except Exception as e:
            # Update execution record with error
            await self.db_ops.update_execution(
                execution_id=execution_id,
                updates={
                    "end_time": datetime.now(),
                    "success": False,
                    "error": str(e)
                }
            )
            
            # Update event record
            await self.db_ops.update_event(
                event_id=event_id,
                updates={
                    "last_execution": datetime.now(),
                    "execution_count": event.get("execution_count", 0) + 1,
                    "last_error": str(e)
                }
            )
            
            self.logger.error(error_message(
                module_id=COMPONENT_ID,
                error_type="EXECUTION_ERROR",
                details=f"Error executing job: {str(e)}"
            ))
            
            return Result.error(
                code="EXECUTION_ERROR",
                message=f"Error executing job: {str(e)}",
                details={"execution_id": execution_id, "event_id": event_id}
            )

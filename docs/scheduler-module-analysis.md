# Core Scheduler Module Analysis

**Location**: `modules/core/scheduler/`  
**Purpose**: Centralized system for scheduling tasks and background maintenance operations  
**Version**: 1.1.0  
**Created**: Based on analysis of actual code on 2025-06-17

## Overview

The Scheduler Module provides a comprehensive task scheduling and management system for the Modular Framework. It enables scheduling one-time and recurring tasks, managing their execution lifecycle, and includes a Housekeeper component for centralized cleanup operations across all framework modules.

## Core Architecture

### Service-Oriented Design

The scheduler follows a clean, component-based architecture:

**Main Service Layer**:
- **SchedulerService**: Central coordination service managing the complete lifecycle
- **Database Operations**: Persistent storage for events, executions, and configurations

**Component Layer**:
- **JobManager**: Handles job registration, scheduling, and execution
- **TriggerManager**: Manages different trigger types (intervals, cron expressions)
- **Housekeeper**: Centralized cleanup functionality for file management

### Two-Phase Initialization

**Phase 1** (`api.py:initialize`):
```python
async def initialize(app_context):
    """Phase 1: Register models, services, and hooks"""
    # Register database models
    await app_context.register_model(ScheduledEvent)
    await app_context.register_model(EventExecution)
    await app_context.register_model(CleanupConfig)
    
    # Register the scheduler service
    scheduler_service = SchedulerService(app_context)
    await app_context.register_service("scheduler_service", scheduler_service)
    
    # Register settings
    await register_settings(app_context)
```

**Phase 2** (`services.py:initialize`):
```python
async def initialize(self, app_context=None, settings=None) -> bool:
    """Phase 2: Initialize database operations and start background tasks"""
    # Initialize database operations
    await self.db_ops.initialize()
    
    # Initialize components
    await self.job_manager.initialize(self.db_ops)
    await self.trigger_manager.initialize()
    await self.housekeeper.initialize(self.db_ops)
    
    # Start scheduler loop if enabled
    if settings.get("enabled", True):
        self._scheduler_task = self._create_background_task(self._scheduler_loop())
```

## Database Schema

### ScheduledEvent Model

**Table**: `scheduler_events`

```python
class ScheduledEvent(Base):
    id = Column(String(36), primary_key=True)              # UUID
    name = Column(String(100), nullable=False)             # Human-readable name
    description = Column(Text, nullable=True)              # Optional description
    module_id = Column(String(100), nullable=False)        # Source module
    function_name = Column(String(100), nullable=False)    # Function to execute
    parameters = Column(SQLiteJSON, nullable=False)        # Execution parameters
    
    # Scheduling configuration
    recurring = Column(Boolean, default=False)             # One-time vs recurring
    interval_type = Column(String(20), nullable=True)      # minutes, hours, days, weeks, months, cron
    interval_value = Column(Integer, nullable=True)        # Interval multiplier
    next_execution = Column(DateTime, nullable=False)      # When to run next
    
    # Status tracking
    status = Column(String(20), default="pending")         # pending, running, completed, failed, paused
    execution_count = Column(Integer, default=0)           # Total executions
    max_executions = Column(Integer, nullable=True)        # Optional execution limit
    last_execution = Column(DateTime, nullable=True)       # Last execution time
    last_error = Column(Text, nullable=True)              # Most recent error
```

### EventExecution Model

**Table**: `scheduler_executions`

```python
class EventExecution(Base):
    id = Column(String(36), primary_key=True)              # UUID
    event_id = Column(String(36), ForeignKey(...))         # Parent event
    start_time = Column(DateTime, nullable=False)          # Execution start
    end_time = Column(DateTime, nullable=True)             # Execution end (null = running)
    success = Column(Boolean, nullable=True)               # Success status
    result = Column(SQLiteJSON, nullable=True)             # Execution result
    error = Column(Text, nullable=True)                    # Error details
    trace_session_id = Column(String(36), nullable=True)   # Trace logging link
```

### CleanupConfig Model

**Table**: `scheduler_cleanup_configs`

```python
class CleanupConfig(Base):
    id = Column(String(36), primary_key=True)              # UUID
    directory = Column(String(512), nullable=False)        # Target directory
    pattern = Column(String(128), default="*")             # File pattern
    retention_days = Column(Integer, nullable=True)        # Age-based retention
    max_files = Column(Integer, nullable=True)             # Count-based retention
    max_size_mb = Column(Integer, nullable=True)          # Size-based retention
    priority = Column(Integer, default=100)                # Cleanup priority
    module_id = Column(String(100), nullable=False)        # Registering module
    last_run = Column(DateTime, nullable=True)             # Last cleanup time
```

## Core Functionality

### Task Scheduling

**One-Time Events**:
```python
await scheduler_service.schedule_event(
    name="Database backup",
    function_name="backup_database",
    next_execution=datetime.now() + timedelta(hours=1),
    module_id="core.database",
    parameters={"compress": True}
)
```

**Recurring Events**:
```python
await scheduler_service.schedule_event(
    name="Daily maintenance",
    function_name="cleanup_temporary_files",
    next_execution=datetime.now().replace(hour=3, minute=0),
    recurring=True,
    interval_type="days",
    interval_value=1,
    module_id="core.maintenance"
)
```

**Cron-Based Scheduling**:
```python
await scheduler_service.schedule_event(
    name="Weekly report",
    function_name="generate_weekly_report",
    next_execution=next_monday_9am,
    recurring=True,
    interval_type="cron",
    module_id="core.reports",
    parameters={"_cron_expression": "0 9 * * 1"}  # Monday at 9 AM
)
```

### Scheduler Loop Architecture

**Background Execution**:
```python
async def _scheduler_loop(self) -> None:
    """Main scheduler loop checking for due events"""
    while self._is_running:
        try:
            # Check for due events
            await self._check_due_events()
            
            # Periodic cleanup if enabled
            if settings.get("auto_cleanup_enabled", True):
                await self.db_ops.cleanup_old_executions(retention_days)
            
            # Wait for next check cycle
            await asyncio.wait_for(
                self._shutdown_event.wait(),
                timeout=check_interval
            )
        except asyncio.TimeoutError:
            # Expected timeout, continue loop
            pass
```

**Due Event Processing**:
```python
async def _check_due_events(self) -> None:
    """Check for events due for execution"""
    # Respect concurrency limits
    running_count = await self._get_running_executions_count()
    if running_count >= max_concurrent:
        return
    
    # Get due events
    due_events = await self.db_ops.get_due_events(datetime.now())
    
    # Start background execution for each
    for event in due_events:
        await self.db_ops.update_event(event["id"], {"status": "running"})
        self._create_background_task(self._execute_event(event))
```

### Event Execution Lifecycle

**Execution Process**:
```python
async def _execute_event(self, event: Dict[str, Any]) -> None:
    """Execute a scheduled event with full lifecycle management"""
    execution_id = str(uuid.uuid4())
    
    # Create execution record
    await self.db_ops.create_execution(
        id=execution_id,
        event_id=event["id"],
        start_time=datetime.now()
    )
    
    try:
        # Execute job through job manager
        result = await self.job_manager.execute_job(event["id"])
        
        # Handle execution result
        success = result.success if hasattr(result, 'success') else result.get("success", False)
        
        # Update event status and calculate next execution for recurring events
        updates = {
            "status": "completed" if success else "failed",
            "execution_count": event.get("execution_count", 0) + 1,
            "last_execution": datetime.now()
        }
        
        # Handle recurring events
        if event.get("recurring", False) and success:
            next_execution = self.trigger_manager.get_next_execution_time(...)
            updates["next_execution"] = next_execution
            updates["status"] = "pending"
        
        await self.db_ops.update_event(event["id"], updates)
        
    except Exception as e:
        # Handle execution errors with proper logging and status updates
        await self._handle_execution_error(event, execution_id, e)
```

## Component Analysis

### JobManager Component

**Purpose**: Manages job registration, scheduling, and execution

**Key Responsibilities**:
- Job function discovery and validation
- Parameter handling and validation
- Integration with function execution system
- Job result processing and error handling

**Initialization**:
```python
async def initialize(self, db_operations) -> bool:
    """Initialize with database operations and reload active jobs"""
    self.db_ops = db_operations
    await self._reload_active_jobs()  # Restore state from database
    return True
```

### TriggerManager Component

**Purpose**: Handles different trigger types and next execution calculations

**Trigger Types**:
- **Interval-based**: Minutes, hours, days, weeks, months
- **Cron-based**: Full cron expression support for complex schedules
- **One-time**: Single execution at specified time

**Next Execution Calculation**:
```python
def get_next_execution_time(self, trigger_type: str, config: Dict, current_time: datetime) -> datetime:
    """Calculate next execution time based on trigger configuration"""
    if trigger_type == "interval":
        return self._calculate_interval_next(config, current_time)
    elif trigger_type == "cron":
        return self._calculate_cron_next(config, current_time)
```

### Housekeeper Component

**Purpose**: Centralized cleanup functionality for file management across modules

**Key Features**:
- **Directory Registration**: Modules register directories for cleanup
- **Policy-Based Cleanup**: Age, count, and size-based retention policies
- **Safe Operations**: Atomic file operations with dry-run capability
- **Priority Management**: Control cleanup order through priority settings
- **Detailed Reporting**: Comprehensive cleanup operation reports

**Cleanup Registration**:
```python
async def register_cleanup(
    self,
    directory: str,
    pattern: str = "*",
    retention_days: Optional[int] = None,
    max_files: Optional[int] = None,
    max_size_mb: Optional[int] = None,
    priority: int = 100,
    module_id: Optional[str] = None
) -> str:
    """Register a directory for periodic cleanup"""
    config_id = str(uuid.uuid4())
    
    await self.db_ops.create_cleanup_config(
        id=config_id,
        directory=directory,
        pattern=pattern,
        retention_days=retention_days,
        max_files=max_files,
        max_size_mb=max_size_mb,
        priority=priority,
        module_id=module_id
    )
    
    return config_id
```

## Configuration System

### Module Settings

**Scheduler Configuration**:
```python
DEFAULT_SETTINGS = {
    "enabled": True,                        # Enable/disable scheduler
    "check_interval": 1.0,                 # Check frequency (seconds)
    "max_concurrent_executions": 10,       # Concurrency limit
    "execution_timeout": 300,              # Default timeout (seconds)
    "retry_failed_events": True,           # Enable retry logic
    "max_retry_attempts": 3,               # Maximum retries
    "retry_delay": 300,                    # Retry delay (seconds)
    "retention_days": 30,                  # History retention
    "auto_cleanup_enabled": True,          # Auto-cleanup old executions
    "allow_past_events": False,            # Prevent past scheduling
}
```

**Housekeeper Configuration**:
```python
DEFAULT_SETTINGS = {
    "housekeeper_enabled": True,           # Enable housekeeper
    "housekeeper_schedule": "0 3 * * *",   # Daily at 3 AM
    "housekeeper_default_retention": 30,   # Default retention (days)
    "housekeeper_dry_run": False,          # Dry-run mode
    "housekeeper_concurrent_cleanups": 3,  # Max concurrent operations
    "housekeeper_report_enabled": True,    # Generate reports
}
```

### Settings Validation

**Type Safety**:
```python
VALIDATION_SCHEMA = {
    "check_interval": {
        "type": "float",
        "min": 0.1,
        "max": 60.0,
        "description": "How often to check for due events (seconds)"
    },
    "max_concurrent_executions": {
        "type": "int",
        "min": 1,
        "max": 100,
        "description": "Maximum concurrent event executions"
    }
    # ... additional validation rules
}
```

## API Integration

### REST Endpoints

**Event Listing**:
```
GET /api/v1/scheduler/events
Query Parameters:
  - status: Filter by event status
  - module_id: Filter by source module
  - function_name: Filter by function
  - recurring: Filter by recurring status
  - limit: Maximum events to return
```

**Response Schema**:
```python
class EventListResponse(BaseModel):
    success: bool
    data: List[Dict[str, Any]]
    total_count: int
    filtered_count: int
```

### Service Interface

**Service Access Pattern**:
```python
# Get scheduler service
scheduler_service = app_context.get_service("scheduler_service")

# Schedule event
result = await scheduler_service.schedule_event(...)
if result.success:
    event_id = result.data["event_id"]
else:
    logger.error(f"Scheduling failed: {result.error}")
```

**Result Pattern Compliance**:
All service methods return `Result` objects for consistent error handling:
```python
async def schedule_event(...) -> Result:
    """Schedule a new event"""
    try:
        # Validation and processing
        return Result.success(data={"event_id": event_id})
    except Exception as e:
        return Result.error(
            code="SCHEDULING_ERROR",
            message=f"Failed to schedule event: {str(e)}"
        )
```

## Framework Integration Points

### Error Handling Integration

**Layered Error Handling**:
- **API Layer**: Uses `create_error_response` for HTTP exceptions
- **Service Layer**: Uses `Result` pattern for operation results
- **Database Layer**: Uses `error_message` for structured logging

**Error Message Structure**:
```python
self.logger.error(error_message(
    module_id=MODULE_ID,
    error_type="SCHEDULING_ERROR",
    details=f"Error scheduling event: {str(e)}"
))
```

### Database Integration

**Multi-Database Support**: Scheduler defines its own database schema through `db_models.py`
**Async Operations**: Full async/await pattern throughout database operations
**Transaction Safety**: Proper transaction handling for complex operations

### Function Call System Integration

**AI Agent Functions**: Scheduler exposes functions for AI agent interaction:
- `schedule_task`: Schedule new tasks
- `list_tasks`: Query scheduled tasks
- `cancel_task`: Cancel scheduled tasks
- `execute_task_now`: Manual execution
- `register_cleanup`: Register cleanup configurations
- `run_cleanup`: Manual cleanup execution

## Advanced Features

### Retry Logic

**Automatic Retry**: Failed events are automatically retried based on configuration
**Exponential Backoff**: Configurable delay between retry attempts
**Retry Limits**: Maximum retry attempts to prevent infinite loops

### Concurrency Management

**Execution Limits**: Configurable maximum concurrent executions
**Background Tasks**: Proper async task management with cleanup
**Resource Protection**: Prevents resource exhaustion through limits

### Graceful Shutdown

**Clean Termination**:
```python
async def shutdown(self) -> None:
    """Graceful shutdown with proper cleanup"""
    if self._is_running:
        self._is_running = False
        self._shutdown_event.set()
        
        # Wait for scheduler task completion
        await asyncio.wait_for(self._scheduler_task, timeout=5.0)
        
        # Cancel background tasks
        for task in self._background_tasks:
            if not task.done():
                task.cancel()
```

### State Recovery

**Persistence**: All state persisted to database for recovery
**Startup Cleanup**: Cleans up jobs left in "running" state from previous shutdown
**Active Job Reload**: Restores scheduled jobs from database on startup

## Use Cases and Examples

### Maintenance Tasks

**Database Optimization**:
```python
await scheduler_service.schedule_event(
    name="Weekly database optimization",
    function_name="optimize_database",
    next_execution=next_sunday_2am,
    recurring=True,
    interval_type="weeks",
    interval_value=1,
    module_id="core.database"
)
```

### File Cleanup

**Log Rotation**:
```python
await scheduler_service.register_cleanup(
    directory="/var/log/app",
    pattern="*.log",
    retention_days=30,
    description="Application log cleanup",
    module_id="core.logging"
)
```

### User Notifications

**Reminder System**:
```python
await scheduler_service.schedule_event(
    name="User reminder",
    function_name="send_reminder",
    next_execution=reminder_time,
    module_id="core.notifications",
    parameters={"user_id": user_id, "message": "Your subscription expires soon"}
)
```

## Performance Considerations

### Efficient Polling

**Configurable Intervals**: Balance between responsiveness and resource usage
**Due Event Queries**: Optimized database queries with proper indexing
**Concurrency Control**: Prevents resource exhaustion through execution limits

### Memory Management

**Background Task Tracking**: Proper cleanup of completed tasks
**Result Storage**: Configurable retention for execution history
**Resource Cleanup**: Automatic cleanup of old execution records

### Database Optimization

**Indexed Queries**: Proper indexing on `next_execution` and `status` columns
**Cascade Deletes**: Automatic cleanup of related execution records
**JSON Parameter Storage**: Efficient storage of execution parameters

## Best Practices

### When to Use Scheduler

- **Periodic Maintenance**: Database optimization, log rotation, cache cleanup
- **Scheduled Reports**: Generate reports at specific times
- **Data Synchronization**: Regular imports/exports
- **User Notifications**: Time-based alerts and reminders
- **Session Management**: Cleanup expired sessions

### When to Use Housekeeper

- **Log Management**: Automatic log file rotation and cleanup
- **Temporary Files**: Cleanup of cached or temporary data
- **Generated Content**: Management of user-generated files
- **Export Files**: Cleanup of old exported data

### Configuration Guidelines

- **Check Interval**: Balance between responsiveness and CPU usage
- **Concurrency**: Set based on system resources and task characteristics
- **Retry Logic**: Configure based on task failure characteristics
- **Retention**: Balance between audit trail needs and storage usage

## Conclusion

The Scheduler Module represents a sophisticated task scheduling and management system that provides essential infrastructure for time-based operations in the Modular Framework. Its component-based architecture, comprehensive error handling, and integration with framework patterns make it a robust foundation for scheduled operations while maintaining the framework's commitment to reliability and developer experience.

**Key Strengths**:
- **Comprehensive Scheduling**: Support for one-time, recurring, and cron-based scheduling
- **Robust Execution**: Proper error handling, retry logic, and concurrency management
- **Centralized Cleanup**: Housekeeper component for unified file management
- **Framework Integration**: Full compliance with framework patterns and standards
- **State Management**: Proper persistence and recovery capabilities
- **Performance**: Efficient polling and resource management
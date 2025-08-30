# Scheduler Module Documentation

**Version: 1.0.0**  
**Updated: March 24, 2025**

## Overview

The Scheduler Module provides a centralized system for managing time-based operations across the framework. Instead of each module implementing its own time-based execution logic, the Scheduler Module offers a standardized approach for scheduling, persisting, executing, and monitoring scheduled tasks.

## Core Purpose

The primary purpose of the Scheduler Module is to:

1. **Centralize Scheduling Logic**: Eliminate duplicated scheduling code across modules
2. **Provide Persistence**: Ensure scheduled tasks survive application restarts
3. **Enable Monitoring**: Track execution history and status
4. **Support Recurring Tasks**: Handle repeating tasks with various interval patterns
5. **Integrate with Framework**: Leverage existing framework capabilities like tracing and function_call

## Key Features

- **One-Time and Recurring Events**: Schedule tasks to run once or repeatedly at specified intervals
- **Persistence**: Store scheduled events in the database to survive application restarts
- **Execution History**: Track execution attempts, results, and errors
- **Trace Integration**: Automatically trace event executions for debugging
- **Flexible Scheduling**: Schedule by specific date/time or relative intervals
- **UI Components**: Provide UI for viewing and managing scheduled events

## Architecture

### Core Components

#### 1. SchedulerService

The central service responsible for:
- Managing the scheduler lifecycle (start/stop)
- Providing the API for scheduling events
- Executing events at the scheduled time
- Updating event status and handling recurrence
- Maintaining execution history

#### 2. Database Models

Two primary models:
- **ScheduledEvent**: Stores event metadata, scheduling information, and status
- **EventExecution**: Records individual execution attempts and results

#### 3. Scheduler Engine

A background task that:
- Periodically checks for due events
- Executes due events in separate tasks
- Updates event status
- Handles recurring event rescheduling

#### 4. Database Operations

Provides database access with:
- CRUD operations for events and executions
- Filtering capabilities for finding due events
- Clean error handling and retry mechanisms

## Integration with Two-Phase Initialization

The scheduler module follows the framework's two-phase initialization pattern:

### Phase 1: Registration

During Phase 1, the module:
- Registers the SchedulerService with the application context
- Registers database models for migrations
- Registers API endpoints
- Registers UI components

```python
async def initialize(app_context):
    """Initialize the scheduler module."""
    logger.info("Initializing scheduler module")
    
    # Create and register scheduler service
    scheduler_service = SchedulerService(app_context)
    await scheduler_service.initialize()
    app_context.register_service("scheduler_service", scheduler_service)
    
    # Register database models
    from .db_models import ScheduledEvent, EventExecution
    app_context.register_models([ScheduledEvent, EventExecution])
    
    # Register for Phase 2 initialization
    app_context.register_module_setup_hook(
        module_id="core.scheduler",
        setup_method=setup_module
    )
    
    # Register module settings
    from .module_settings import register_settings
    await register_settings(app_context)
    
    return True
```

### Phase 2: Setup

During Phase 2, the module:
- Loads scheduled events from database
- Starts the scheduler background task

```python
async def setup_module(app_context):
    """Phase 2 initialization for scheduler module."""
    logger.info("Setting up scheduler module")
    
    # Get scheduler service
    scheduler_service = app_context.get_service("scheduler_service")
    if not scheduler_service:
        logger.error("Scheduler service not available")
        return False
    
    # Set up the scheduler
    success = await scheduler_service.setup()
    if not success:
        logger.error("Failed to set up scheduler")
        return False
    
    logger.info("Scheduler module setup complete")
    return True
```

## Database Schema

### ScheduledEvent

| Field | Type | Description |
|-------|------|-------------|
| id | String | Primary key (UUID) |
| name | String | Descriptive name |
| description | String | Optional description |
| module_id | String | Source module identifier |
| function_name | String | Name of function to execute |
| parameters | JSON | Parameters to pass to function |
| schedule_time | DateTime | When event was initially scheduled |
| created_at | DateTime | When event was created |
| updated_at | DateTime | When event was last updated |
| recurring | Boolean | Whether event repeats |
| interval_type | String | 'minutes', 'hours', 'days', 'weeks', 'months' |
| interval_value | Integer | Number of interval units |
| last_execution | DateTime | When event was last executed |
| next_execution | DateTime | When event will next execute |
| execution_count | Integer | Number of times executed |
| max_executions | Integer | Optional limit on executions |
| status | String | 'pending', 'running', 'completed', 'failed', 'cancelled' |
| last_error | String | Most recent error message |
| trace_enabled | Boolean | Whether execution tracing is enabled |
| metadata | JSON | Additional metadata |

### EventExecution

| Field | Type | Description |
|-------|------|-------------|
| id | String | Primary key (UUID) |
| event_id | String | Foreign key to ScheduledEvent |
| start_time | DateTime | When execution started |
| end_time | DateTime | When execution completed |
| success | Boolean | Whether execution succeeded |
| result | JSON | Execution result data |
| error | String | Error message if failed |
| trace_session_id | String | TraceLogger session ID |

## Usage Examples

### Scheduling a One-Time Event

```python
async def schedule_backup(app_context):
    # Get scheduler service
    scheduler_service = app_context.get_service("scheduler_service")
    if not scheduler_service:
        return False
        
    # Schedule a backup in 1 hour
    from datetime import datetime, timedelta
    
    backup_time = datetime.now() + timedelta(hours=1)
    
    await scheduler_service.schedule_event(
        name="Daily Settings Backup",
        function_name="settings_backup",
        parameters={"description": "Scheduled backup"},
        schedule_time=backup_time,
        module_id="core.settings"
    )
```

### Scheduling a Recurring Event

```python
async def schedule_maintenance(app_context):
    # Get scheduler service
    scheduler_service = app_context.get_service("scheduler_service")
    if not scheduler_service:
        return False
        
    # Schedule weekly database maintenance
    from datetime import datetime
    
    # Start next Sunday at midnight
    from datetime import datetime, timedelta
    now = datetime.now()
    days_until_sunday = 6 - now.weekday()
    next_sunday = now.replace(hour=0, minute=0, second=0) + timedelta(days=days_until_sunday)
    
    await scheduler_service.schedule_event(
        name="Weekly Database Maintenance",
        function_name="database_maintenance",
        parameters={"optimize": True, "vacuum": True},
        schedule_time=next_sunday,
        module_id="core.database",
        recurring=True,
        interval_type="days",
        interval_value=7
    )
```

### Cancelling an Event

```python
async def cancel_event(app_context, event_id):
    scheduler_service = app_context.get_service("scheduler_service")
    if not scheduler_service:
        return False
        
    return await scheduler_service.cancel_event(event_id)
```

### Executing an Event Immediately

```python
async def run_now(app_context, event_id):
    scheduler_service = app_context.get_service("scheduler_service")
    if not scheduler_service:
        return False
        
    return await scheduler_service.execute_event_now(event_id)
```

## Execution Flow

1. **Scheduling Phase**:
   - Module calls `schedule_event()` with function name, parameters, and timing
   - Event is stored in database with 'pending' status
   - Next execution time is calculated

2. **Discovery Phase**:
   - Scheduler loop periodically checks for due events
   - Events with `next_execution <= now` and status 'pending' are retrieved

3. **Execution Phase**:
   - For each due event, execution task is created
   - Execution record is created in database
   - Event status is updated to 'running'
   - Function is executed through function_call system
   - Results or errors are recorded

4. **Completion Phase**:
   - Execution record is updated with results/errors
   - For non-recurring events, status is set to 'completed' or 'failed'
   - For recurring events, next execution time is calculated and status reset to 'pending'

## Integration with Other Modules

The Scheduler Module integrates with several framework components:

### 1. Function Call System

Uses the function_call system to execute scheduled functions:

```python
result = await self.function_client.execute_function(
    function_name=event["function_name"],
    parameters=event["parameters"],
    trace_info=trace_info
)
```

### 2. Trace Logger

Integrates with the trace logger for execution tracking:

```python
session_id = TraceLogger.create_session("scheduler")
trace_info = {"session_id": session_id, "enabled": True}

TraceLogger.trace_event(
    {"trace_info": trace_info},
    "scheduler_event_execute",
    {"event_id": event_id, "name": event["name"]}
)
```

### 3. Database System

Uses the database system for persistent storage:

```python
async with self._db_session() as session:
    events = await execute_with_retry(
        lambda: self.crud_service.read_many(
            session, ScheduledEvent,
            filters=filters,
            limit=limit,
            as_dict=True
        )
    )
```

## Module Settings

The module provides configurable settings:

| Setting | Description | Default |
|---------|-------------|---------|
| check_interval | How often to check for due events (seconds) | 1.0 |
| max_concurrent_executions | Maximum concurrent event executions | 10 |
| execution_timeout | Default timeout for event execution (seconds) | 300 |
| retry_failed_events | Whether to retry failed events | true |
| max_retry_attempts | Maximum retry attempts for failed events | 3 |
| retry_delay | Delay before retrying failed events (seconds) | 300 |
| retention_days | How long to keep execution history (days) | 30 |
| auto_cleanup_enabled | Whether to automatically clean up old executions | true |
| cleanup_interval_hours | How often to run cleanup (hours) | 24 |
| allow_past_events | Whether to allow scheduling events in the past | false |
| trace_enabled_by_default | Whether to enable tracing by default | true |

## Use Cases

The Scheduler Module can be used for various time-based operations:

1. **Maintenance Tasks**: Database optimization, log rotation, cache cleanup
2. **User Notifications**: Scheduled alerts or reminders
3. **Reports Generation**: Periodic reports or analytics
4. **Data Synchronization**: Regular data imports or exports
5. **Session Management**: Cleanup of expired sessions
6. **System Monitoring**: Regular health checks and status reports
7. **Backup Operations**: Scheduled backups of settings, files, or databases

## Benefits Over Individual Module Scheduling

1. **Consistency**: Standard approach for all scheduled operations
2. **Monitoring**: Central view of all scheduled tasks
3. **Persistence**: All scheduled tasks survive application restarts
4. **Resource Management**: Control over concurrent executions
5. **Error Handling**: Consistent tracking and handling of failures
6. **UI Management**: Single interface for managing all scheduled tasks

## Conclusion

The Scheduler Module provides a robust, centralized system for handling time-based operations across the framework. By adopting this module, the framework can eliminate duplicated scheduling logic, ensure consistent handling of scheduled tasks, and provide better visibility and control over time-based operations.

This module aligns with the framework's architectural principles by following the two-phase initialization pattern, integrating with other core systems, and providing a clean service interface for other modules to use.

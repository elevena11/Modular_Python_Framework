# Scheduler Module

**Version: 1.0.0**  
**Updated: March 30, 2025**

## Overview

The Scheduler Module provides a centralized system for managing time-based operations across the framework. It enables scheduling tasks to run at specific times or intervals, and includes a Housekeeper component for centralized cleanup of temporary files and logs.

## Features

### Task Scheduling

- **One-Time Events**: Schedule tasks to run once at a specific date and time
- **Recurring Events**: Schedule tasks to repeat at regular intervals (minutes, hours, days, weeks, months)
- **Cron Scheduling**: Schedule tasks using cron expressions for complex schedules
- **Execution Management**: Track execution history, success/failure status, and results
- **Runtime Controls**: Pause, resume, cancel, or run tasks immediately

### Housekeeper Component

- **Centralized Cleanup**: Single interface for managing cleanup across all modules
- **Flexible Policies**: Support age-based, count-based, and size-based retention
- **Safe Operation**: Atomic file operations, dry-run mode, and detailed reporting
- **Pattern Matching**: Target specific file patterns for cleanup
- **Priority Management**: Control cleanup order through priority settings

## Architecture

The Scheduler Module follows a clean, service-oriented architecture:

1. **SchedulerService**: Central service managing scheduling and execution
2. **JobManager**: Handles job registration, triggers, and execution
3. **Housekeeper**: Provides centralized cleanup functionality
4. **SchedulerDatabaseOperations**: Handles database persistence

The module integrates with:
- **Database System**: For storing events, executions, and configurations
- **Trace Logger**: For execution tracking and debugging
- **Function Call System**: For executing functions and discovery by AI Agent

## Functions for AI Agent

The module exposes several functions to the AI Agent via the function_call system:

- `schedule_task`: Schedule a new task to run once or repeatedly
- `list_tasks`: Get a list of scheduled tasks with filtering
- `cancel_task`: Cancel a scheduled task
- `pause_resume_task`: Pause or resume a scheduled task
- `execute_task_now`: Run a task immediately
- `register_cleanup`: Register a directory for periodic cleanup
- `run_cleanup`: Run cleanup operations manually

## Integration

### Service Interface

Other modules can access the Scheduler Module through the `scheduler_service`:

```python
# Get the scheduler service
scheduler_service = app_context.get_service("scheduler_service")

# Schedule a task
event_id = await scheduler_service.schedule_event(
    name="Daily backup",
    function_name="backup_database",
    next_execution=datetime.now() + timedelta(days=1),
    recurring=True,
    interval_type="days",
    interval_value=1,
    module_id="core.database",
    parameters={"compress": True}
)

# Register a directory for cleanup
registration_id = await scheduler_service.register_cleanup(
    directory="/path/to/logs",
    pattern="*.log",
    retention_days=30,
    module_id="core.logging"
)
```

### UI Integration

The module provides a single API endpoint for UI access to scheduled events:

```
GET /api/v1/scheduler/events
```

This endpoint supports filtering by status, module_id, function_name, and recurring status.

## Configuration

The module's behavior can be configured through settings:

- **Scheduler Settings**: Control check interval, concurrency, retries, etc.
- **Housekeeper Settings**: Configure cleanup schedule, policies, and reporting

## Best Practices

### When to Use the Scheduler

- **Maintenance Tasks**: Database optimization, log rotation, cache cleanup
- **User Notifications**: Scheduled alerts or reminders
- **Reports Generation**: Periodic reports or analytics
- **Data Synchronization**: Regular data imports or exports
- **Session Management**: Cleanup of expired sessions

### When to Use the Housekeeper

- **Log Files**: Rotation and cleanup of application logs
- **Temporary Files**: Cleanup of cached or temporary data
- **Generated Content**: Management of user-generated content
- **Exported Reports**: Cleanup of exported reports or data dumps

## Example Usage

### Scheduling a Recurring Task

```python
await scheduler_service.schedule_event(
    name="Daily Database Backup",
    function_name="backup_database",
    next_execution=datetime.now().replace(hour=3, minute=0, second=0) + timedelta(days=1),
    recurring=True,
    interval_type="days",
    interval_value=1,
    module_id="core.database",
    parameters={"compress": True, "include_attachments": True}
)
```

### Registering for Cleanup

```python
await scheduler_service.register_cleanup(
    directory="/path/to/exports",
    pattern="*.csv",
    retention_days=7,
    description="Exported data files",
    module_id="core.exports"
)
```

## Error Handling

The module follows the framework's layered error handling approach:

- **API Layer**: Uses `create_error_response` for HTTP exceptions
- **Service Layer**: Uses `Result` pattern for service returns
- **Database Layer**: Uses `error_message` for consistent logging

## Implementation Notes

The Scheduler Module follows the framework's two-phase initialization pattern:

1. **Phase 1**: Registers models, services, and hooks
2. **Phase 2**: Initializes database operations and starts background tasks

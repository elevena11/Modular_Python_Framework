# Scheduler Module - Usage Guide

**Version: 1.0.0**  
**Updated: March 30, 2025**

## Introduction

The Scheduler Module provides a centralized system for time-based operations across the Modular AI Framework. It enables you to schedule tasks, manage their execution, and handle temporary file cleanup through a unified interface.

This guide explains how to integrate with and use the Scheduler Module in your own modules.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Scheduling Tasks](#scheduling-tasks)
3. [Managing Tasks](#managing-tasks)
4. [Using the Housekeeper](#using-the-housekeeper)
5. [Integration Examples](#integration-examples)
6. [API Reference](#api-reference)
7. [Troubleshooting](#troubleshooting)

## Getting Started

### Module Dependencies

The Scheduler Module has the following dependencies:
- `core.database`
- `core.settings`
- `core.function_call`
- `core.trace_logger`

Ensure these modules are loaded before using the scheduler.

### Accessing the Scheduler Service

To use the scheduler, first get a reference to the scheduler service from the app context:

```python
# Get the scheduler service
scheduler_service = app_context.get_service("scheduler_service")

# Check if service is available
if not scheduler_service:
    logger.warning("Scheduler service not available")
    return
```

### Checking Initialization

The scheduler service implements a two-phase initialization pattern. Always check if it's initialized before usage:

```python
if not scheduler_service.initialized:
    logger.warning("Scheduler service not initialized")
    return
```

## Scheduling Tasks

### One-time Tasks

To schedule a task to execute once at a specific time:

```python
import uuid
from datetime import datetime, timedelta

# Schedule a task to run tomorrow at 3 AM
event_id = await scheduler_service.schedule_event(
    name="Database Backup",
    description="Daily backup of the application database",
    function_name="backup_database",
    next_execution=datetime.now().replace(hour=3, minute=0, second=0) + timedelta(days=1),
    recurring=False,
    module_id="your.module.id",
    parameters={"compress": True, "include_attachments": True}
)

logger.info(f"Scheduled one-time backup with ID: {event_id}")
```

### Recurring Tasks

For tasks that need to execute repeatedly:

```python
# Schedule a daily task
event_id = await scheduler_service.schedule_event(
    name="Daily Log Cleanup",
    description="Remove old log files",
    function_name="cleanup_logs",
    next_execution=datetime.now().replace(hour=1, minute=0, second=0) + timedelta(days=1),
    recurring=True,
    interval_type="days",
    interval_value=1,
    module_id="your.module.id",
    parameters={"retention_days": 7}
)

# Schedule an hourly task
event_id = await scheduler_service.schedule_event(
    name="Cache Refresh",
    description="Refresh application cache",
    function_name="refresh_cache",
    next_execution=datetime.now() + timedelta(hours=1),
    recurring=True,
    interval_type="hours",
    interval_value=1,
    module_id="your.module.id",
    parameters={}
)
```

### Supported Interval Types

The following interval types are supported:
- `"minutes"` - Every X minutes
- `"hours"` - Every X hours
- `"days"` - Every X days
- `"weeks"` - Every X weeks
- `"months"` - Every X months (approximated)
- `"cron"` - Advanced scheduling using cron expressions

### Using Cron Expressions

For more complex scheduling needs, use cron expressions:

```python
# Parameters must include the _cron_expression value
parameters = {
    "_cron_expression": "0 3 * * MON",  # Every Monday at 3 AM
    "other_param": "value"
}

event_id = await scheduler_service.schedule_event(
    name="Weekly Report Generation",
    description="Generate weekly reports",
    function_name="generate_reports",
    next_execution=datetime.now() + timedelta(days=1),  # Initial execution time
    recurring=True,
    interval_type="cron",
    interval_value=1,  # Not used for cron but required
    module_id="your.module.id",
    parameters=parameters
)
```

## Managing Tasks

### Listing Tasks

To retrieve scheduled tasks:

```python
# Get all tasks for your module
tasks = await scheduler_service.get_events({"module_id": "your.module.id"}, limit=50)

# Get tasks by status
pending_tasks = await scheduler_service.get_events({"status": "pending"}, limit=10)

# Get recurring tasks
recurring_tasks = await scheduler_service.get_events({"recurring": True}, limit=20)

# Multiple filters
specific_tasks = await scheduler_service.get_events({
    "module_id": "your.module.id",
    "status": "pending",
    "recurring": True
}, limit=10)
```

### Getting Task Details

To get details for a specific task:

```python
task = await scheduler_service.get_event(event_id)
if task:
    logger.info(f"Task: {task['name']}, Next execution: {task['next_execution']}")
else:
    logger.warning(f"Task {event_id} not found")
```

### Controlling Task Execution

Tasks can be paused, resumed, cancelled, or executed immediately:

```python
# Pause a task
await scheduler_service.pause_event(event_id)

# Resume a paused task
await scheduler_service.resume_event(event_id)

# Execute a task immediately (doesn't affect schedule)
result = await scheduler_service.execute_event_now(event_id)

# Cancel a task permanently
await scheduler_service.delete_event(event_id)
```

### Updating Task Parameters

To modify a task's parameters:

```python
updates = {
    "parameters": {
        "compression_level": "high",
        "include_archives": True
    }
}
success = await scheduler_service.update_event(event_id, updates)
```

## Using the Housekeeper

The Housekeeper component provides centralized management of temporary files and logs that require periodic cleanup.

### Registering for Cleanup

To register a directory for cleanup:

```python
registration_id = await scheduler_service.register_cleanup(
    directory="/path/to/logs",
    pattern="*.log",
    retention_days=30,
    max_files=1000,  # Optional: keep at most 1000 files
    max_size_mb=500,  # Optional: keep total size under 500 MB
    description="Application logs",
    module_id="your.module.id"  # Optional: auto-detected if possible
)

logger.info(f"Registered for cleanup with ID: {registration_id}")
```

### Cleanup Policies

You can use one or more of these policies:

- **Age-based**: `retention_days` - Delete files older than X days
- **Count-based**: `max_files` - Keep only the newest X files
- **Size-based**: `max_size_mb` - Keep total size under X megabytes

If you specify multiple policies, they are combined (files are deleted if ANY policy is violated).

### Managing Cleanup Configurations

To view or manage cleanup configurations:

```python
# Get all cleanup configurations for your module
configs = await scheduler_service.get_cleanup_configs("your.module.id")

# Update a cleanup configuration
await scheduler_service.housekeeper.update_cleanup_config(
    registration_id,
    retention_days=60,  # New retention period
    max_files=2000      # New max files limit
)

# Remove a cleanup configuration
await scheduler_service.housekeeper.remove_cleanup_config(registration_id)
```

### Running Cleanup Manually

To trigger cleanup operations manually:

```python
# Run all cleanup operations
result = await scheduler_service.run_cleanup()

# Run a specific cleanup configuration
result = await scheduler_service.run_cleanup(registration_id)

# Run in dry-run mode (no files deleted)
result = await scheduler_service.run_cleanup(registration_id, dry_run=True)

# Check results
logger.info(f"Cleanup completed: {result['total_files_deleted']} files deleted")
```

## Integration Examples

### Module Initialization with Scheduler

Add these snippets to your module's code:

```python
# In your module's api.py file
async def setup_module(app_context):
    """Phase 2: Execute complex initialization operations."""
    # Get scheduler service
    scheduler_service = app_context.get_service("scheduler_service")
    if scheduler_service and scheduler_service.initialized:
        # Register for cleanup
        await scheduler_service.register_cleanup(
            directory=os.path.join(app_context.config.DATA_DIR, "your_module", "temp"),
            pattern="*",
            retention_days=7,
            description="Temporary files for your module"
        )
        
        # Schedule recurring maintenance task
        await scheduler_service.schedule_event(
            name="Module Maintenance",
            function_name="your_module.maintenance",
            next_execution=datetime.now() + timedelta(days=1),
            recurring=True,
            interval_type="days",
            interval_value=1,
            module_id="your.module.id"
        )
    
    return True
```

### Creating a Schedulable Function

To create a function that can be scheduled:

```python
# In your module's functions/maintenance.py file
FUNCTION_NAME = "your_module.maintenance"
FUNCTION_DESCRIPTION = "Perform maintenance tasks for your module"
FUNCTION_PARAMETERS = {
    "full_maintenance": {
        "type": "boolean",
        "description": "Whether to perform full maintenance",
        "default": False
    }
}

async def execute(app_context, parameters, trace_info=None):
    """
    Perform maintenance for your module.
    
    Args:
        app_context: Application context
        parameters: Function parameters
        trace_info: Optional trace information
    
    Returns:
        Dict with execution results
    """
    # Your maintenance code here
    full_maintenance = parameters.get("full_maintenance", False)
    
    # Perform maintenance...
    
    return {
        "success": True,
        "message": "Maintenance completed successfully",
        "details": {
            "full_maintenance": full_maintenance,
            "items_processed": 42
        }
    }
```

## API Reference

### SchedulerService Methods

| Method | Description | Parameters |
|--------|-------------|------------|
| `schedule_event()` | Schedule a new event | name, function_name, next_execution, module_id, recurring, interval_type, interval_value, parameters, description |
| `get_event()` | Get a scheduled event by ID | event_id |
| `get_events()` | Get scheduled events with filtering | filters, limit |
| `update_event()` | Update a scheduled event | event_id, updates |
| `delete_event()` | Delete a scheduled event | event_id |
| `pause_event()` | Pause a scheduled event | event_id |
| `resume_event()` | Resume a paused event | event_id |
| `execute_event_now()` | Execute an event immediately | event_id |
| `register_cleanup()` | Register a directory for cleanup | directory, pattern, retention_days, max_files, max_size_mb, priority, description, module_id |
| `get_cleanup_configs()` | Get cleanup configurations | module_id |
| `run_cleanup()` | Run cleanup operations | registration_id, dry_run |

### Event Status Values

- `"pending"` - Waiting for execution
- `"running"` - Currently executing
- `"completed"` - One-time event completed
- `"failed"` - Execution failed
- `"paused"` - Temporarily paused

## Troubleshooting

### Common Issues

#### "Scheduler service not initialized"
- Ensure the scheduler module is properly loaded
- Check if database service is available and initialized
- Verify the scheduler service is registered in app_context

#### "Failed to schedule event"
- Verify all required parameters are provided
- Ensure function_name refers to a valid function
- Check if next_execution is a valid datetime object
- For recurring events, ensure interval_type and interval_value are provided

#### "Database operation error"
- Check database connectivity
- Verify database tables exist and are properly migrated
- Look for specific error messages in the logs

#### "Task not executing"
- Verify task status is "pending" (not "paused" or "completed")
- Check if next_execution time is in the future
- Ensure the scheduler background task is running
- Verify the function referenced by function_name exists and is registered

### Logging and Debugging

The scheduler module integrates with the trace_logger for debugging:

```python
# Enable tracing for your scheduled tasks
parameters = {
    "enable_tracing": True,
    # other parameters...
}

# The trace logs will be available in the trace logs directory
```

### Getting Help

For more assistance:
- Check the scheduler module's readme.md file
- Review the scheduler's code for implementation details
- File an issue report with detailed error information

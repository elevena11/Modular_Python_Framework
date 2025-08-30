# Scheduler Module

The Scheduler Module (`modules/core/scheduler/`) provides centralized task scheduling and background maintenance operations for the framework. It enables modules to schedule one-time and recurring tasks, manage their execution, and handle cleanup operations through an integrated housekeeper system.

## Overview

The Scheduler Module is a core framework component that handles all time-based operations. It provides:

- **Task Scheduling**: One-time and recurring task execution
- **Background Processing**: Asynchronous task execution with proper resource management
- **Execution Tracking**: Complete history of task executions with success/failure tracking
- **Housekeeper Integration**: Centralized cleanup and maintenance operations
- **Trigger Management**: Flexible scheduling triggers (interval, cron-like, event-based)
- **Job Management**: Task lifecycle management with pause/resume capabilities

## Key Features

### 1. Task Scheduling
- **One-time Tasks**: Execute tasks at specific times
- **Recurring Tasks**: Execute tasks on regular intervals
- **Flexible Intervals**: Minutes, hours, days, weeks, months
- **Execution Limits**: Optional maximum execution counts
- **Pause/Resume**: Control task execution dynamically

### 2. Background Processing
- **Async Execution**: Non-blocking task execution
- **Resource Management**: Proper cleanup of background tasks
- **Concurrent Tasks**: Multiple tasks can run simultaneously
- **Error Handling**: Graceful handling of task failures
- **Session Tracking**: Link tasks to framework sessions

### 3. Execution Monitoring
- **Execution History**: Complete record of all task executions
- **Success Tracking**: Success/failure status for each execution
- **Error Logging**: Detailed error information for failed tasks
- **Performance Metrics**: Execution time and resource usage
- **Status Management**: Real-time task status updates

### 4. Housekeeper System
- **Cleanup Operations**: Centralized cleanup task management
- **Maintenance Tasks**: Regular system maintenance operations
- **Configurable Schedules**: Flexible cleanup scheduling
- **Module Integration**: Modules can register cleanup tasks
- **Resource Management**: Automatic cleanup of expired data

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   Scheduler Module                          │
├─────────────────────────────────────────────────────────────┤
│ Core Components                                             │
│ ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐ │
│ │ Scheduler       │ │ Job Manager     │ │ Trigger         │ │
│ │ Service         │ │                 │ │ Manager         │ │
│ └─────────────────┘ └─────────────────┘ └─────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│ Specialized Components                                      │
│ ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐ │
│ │ Housekeeper     │ │ Database        │ │ Background      │ │
│ │ (Cleanup)       │ │ Operations      │ │ Task Runner     │ │
│ └─────────────────┘ └─────────────────┘ └─────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│ Data Models                                                 │
│ ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐ │
│ │ Scheduled       │ │ Event           │ │ Cleanup         │ │
│ │ Event           │ │ Execution       │ │ Config          │ │
│ └─────────────────┘ └─────────────────┘ └─────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## Database Models

### 1. ScheduledEvent Model
```python
class ScheduledEvent(Base):
    """Model for scheduled events."""
    __tablename__ = "scheduler_events"
    
    # Basic information
    id = Column(String(36), primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    module_id = Column(String(100), nullable=False)
    function_name = Column(String(100), nullable=False)
    parameters = Column(SQLiteJSON, nullable=False, default=dict)
    
    # Scheduling information
    recurring = Column(Boolean, nullable=False, default=False)
    interval_type = Column(String(20), nullable=True)  # minutes, hours, days
    interval_value = Column(Integer, nullable=True)
    next_execution = Column(DateTime, nullable=False)
    
    # Status tracking
    status = Column(String(20), nullable=False, default="pending")
    last_execution = Column(DateTime, nullable=True)
    execution_count = Column(Integer, nullable=False, default=0)
    max_executions = Column(Integer, nullable=True)
    last_error = Column(Text, nullable=True)
```

### 2. EventExecution Model
```python
class EventExecution(Base):
    """Model for event execution records."""
    __tablename__ = "scheduler_executions"
    
    id = Column(String(36), primary_key=True)
    event_id = Column(String(36), ForeignKey("scheduler_events.id"))
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=True)
    success = Column(Boolean, nullable=True)  # Null = still running
    result = Column(SQLiteJSON, nullable=True)
    error = Column(Text, nullable=True)
    trace_session_id = Column(String(36), nullable=True)
```

### 3. CleanupConfig Model
```python
class CleanupConfig(Base):
    """Model for cleanup configuration."""
    __tablename__ = "scheduler_cleanup_config"
    
    id = Column(String(36), primary_key=True)
    module_id = Column(String(100), nullable=False)
    cleanup_type = Column(String(50), nullable=False)
    config = Column(SQLiteJSON, nullable=False)
    enabled = Column(Boolean, nullable=False, default=True)
    last_run = Column(DateTime, nullable=True)
    next_run = Column(DateTime, nullable=True)
```

## Core Components

### 1. SchedulerService
```python
class SchedulerService:
    """Main scheduler service coordinating all scheduling operations."""
    
    def __init__(self, app_context):
        self.app_context = app_context
        self.job_manager = JobManager(app_context, self)
        self.trigger_manager = TriggerManager(app_context)
        self.housekeeper = Housekeeper(app_context)
        
    async def schedule_task(self, task_config):
        """Schedule a new task."""
        
    async def cancel_task(self, task_id):
        """Cancel a scheduled task."""
        
    async def pause_task(self, task_id):
        """Pause task execution."""
        
    async def resume_task(self, task_id):
        """Resume task execution."""
```

### 2. JobManager
```python
class JobManager:
    """Manages job lifecycle and execution."""
    
    async def create_job(self, name, function_name, parameters, schedule_info):
        """Create a new scheduled job."""
        
    async def execute_job(self, job_id):
        """Execute a scheduled job."""
        
    async def update_job_status(self, job_id, status, result=None, error=None):
        """Update job execution status."""
        
    async def cleanup_completed_jobs(self):
        """Clean up old completed jobs."""
```

### 3. TriggerManager
```python
class TriggerManager:
    """Manages scheduling triggers and timing."""
    
    def calculate_next_execution(self, interval_type, interval_value, last_execution):
        """Calculate next execution time."""
        
    def is_execution_due(self, next_execution):
        """Check if execution is due."""
        
    def create_recurring_schedule(self, interval_type, interval_value):
        """Create recurring schedule configuration."""
```

### 4. Housekeeper
```python
class Housekeeper:
    """Manages cleanup and maintenance operations."""
    
    async def register_cleanup_task(self, module_id, cleanup_type, config):
        """Register a cleanup task."""
        
    async def run_cleanup(self, cleanup_type=None):
        """Run cleanup operations."""
        
    async def schedule_maintenance(self):
        """Schedule regular maintenance tasks."""
```

## Usage Examples

### 1. Scheduling a One-Time Task
```python
# In a module service
async def schedule_data_export():
    scheduler = app_context.get_service("core.scheduler.service")
    
    # Schedule task to run in 1 hour
    result = await scheduler.schedule_task({
        "name": "Export User Data",
        "description": "Export all user data to CSV",
        "module_id": "standard.data_export",
        "function_name": "export_users_to_csv",
        "parameters": {
            "format": "csv",
            "include_deleted": False
        },
        "schedule_time": datetime.now() + timedelta(hours=1),
        "recurring": False
    })
    
    if result.success:
        task_id = result.data["task_id"]
        logger.info(f"Data export scheduled: {task_id}")
    else:
        logger.error(f"Failed to schedule export: {result.error}")
```

### 2. Scheduling a Recurring Task
```python
# Schedule daily cleanup task
async def schedule_daily_cleanup():
    scheduler = app_context.get_service("core.scheduler.service")
    
    result = await scheduler.schedule_task({
        "name": "Daily Log Cleanup",
        "description": "Clean up old log files",
        "module_id": "core.scheduler",
        "function_name": "cleanup_old_logs",
        "parameters": {
            "days_to_keep": 30,
            "log_types": ["error", "debug", "info"]
        },
        "recurring": True,
        "interval_type": "days",
        "interval_value": 1,
        "schedule_time": datetime.now().replace(hour=2, minute=0, second=0)
    })
    
    if result.success:
        logger.info("Daily cleanup scheduled")
```

### 3. Module Task Implementation
```python
# Task function that can be scheduled
async def export_users_to_csv(parameters):
    """Export users to CSV - can be called by scheduler."""
    try:
        format_type = parameters.get("format", "csv")
        include_deleted = parameters.get("include_deleted", False)
        
        # Perform export
        users = await get_users(include_deleted=include_deleted)
        file_path = await export_to_csv(users, format_type)
        
        return Result.success(data={
            "file_path": file_path,
            "record_count": len(users),
            "export_time": datetime.now().isoformat()
        })
    except Exception as e:
        return Result.error(
            code="EXPORT_FAILED",
            message=f"Failed to export users: {str(e)}",
            details={"error": str(e)}
        )
```

### 4. Cleanup Task Registration
```python
# Register cleanup task in module initialization
async def register_module_cleanup():
    scheduler = app_context.get_service("core.scheduler.service")
    
    # Register cleanup for old user sessions
    await scheduler.register_cleanup_task(
        module_id="standard.user_auth",
        cleanup_type="expired_sessions",
        config={
            "table_name": "user_sessions",
            "date_column": "expires_at",
            "cleanup_interval": "1 hour",
            "batch_size": 100
        }
    )
    
    # Register cleanup for temporary files
    await scheduler.register_cleanup_task(
        module_id="standard.file_upload",
        cleanup_type="temp_files",
        config={
            "directory": "/tmp/uploads",
            "max_age_hours": 24,
            "cleanup_interval": "6 hours"
        }
    )
```

## API Endpoints

### 1. Task Management
```python
# List scheduled tasks
GET /api/v1/scheduler/tasks
Response: {
    "tasks": [
        {
            "id": "task-123",
            "name": "Daily Cleanup",
            "status": "pending",
            "next_execution": "2025-07-17T02:00:00Z",
            "recurring": true,
            "interval_type": "days",
            "interval_value": 1
        }
    ]
}

# Get task details
GET /api/v1/scheduler/tasks/{task_id}
Response: {
    "id": "task-123",
    "name": "Daily Cleanup",
    "description": "Clean up old log files",
    "module_id": "core.scheduler",
    "function_name": "cleanup_old_logs",
    "parameters": {"days_to_keep": 30},
    "status": "pending",
    "created_at": "2025-07-16T10:00:00Z",
    "next_execution": "2025-07-17T02:00:00Z",
    "execution_count": 15,
    "last_execution": "2025-07-16T02:00:00Z"
}

# Schedule new task
POST /api/v1/scheduler/tasks
Request: {
    "name": "Data Export",
    "module_id": "standard.data_export",
    "function_name": "export_users",
    "parameters": {"format": "csv"},
    "schedule_time": "2025-07-17T10:00:00Z",
    "recurring": false
}
Response: {
    "task_id": "task-456",
    "status": "scheduled"
}
```

### 2. Task Control
```python
# Cancel task
DELETE /api/v1/scheduler/tasks/{task_id}
Response: {"status": "cancelled"}

# Pause task
POST /api/v1/scheduler/tasks/{task_id}/pause
Response: {"status": "paused"}

# Resume task
POST /api/v1/scheduler/tasks/{task_id}/resume
Response: {"status": "resumed"}

# Execute task immediately
POST /api/v1/scheduler/tasks/{task_id}/execute
Response: {
    "execution_id": "exec-789",
    "status": "running"
}
```

### 3. Execution History
```python
# Get task execution history
GET /api/v1/scheduler/tasks/{task_id}/executions
Response: {
    "executions": [
        {
            "id": "exec-789",
            "start_time": "2025-07-16T02:00:00Z",
            "end_time": "2025-07-16T02:01:30Z",
            "success": true,
            "result": {"processed": 100},
            "error": null
        }
    ]
}

# Get specific execution
GET /api/v1/scheduler/executions/{execution_id}
Response: {
    "id": "exec-789",
    "task_id": "task-123",
    "start_time": "2025-07-16T02:00:00Z",
    "end_time": "2025-07-16T02:01:30Z",
    "success": true,
    "result": {"processed": 100, "errors": 0},
    "error": null,
    "trace_session_id": "session-456"
}
```

## Configuration

### 1. Module Settings
```python
# module_settings.py
SCHEDULER_SETTINGS = {
    "max_concurrent_tasks": {
        "type": "int",
        "default": 10,
        "description": "Maximum number of concurrent tasks"
    },
    "cleanup_interval": {
        "type": "int",
        "default": 3600,
        "description": "Cleanup interval in seconds"
    },
    "execution_timeout": {
        "type": "int",
        "default": 300,
        "description": "Task execution timeout in seconds"
    },
    "keep_execution_history": {
        "type": "int",
        "default": 30,
        "description": "Days to keep execution history"
    }
}
```

### 2. Environment Variables
```bash
# Scheduler configuration
CORE_SCHEDULER_MAX_CONCURRENT_TASKS=20
CORE_SCHEDULER_CLEANUP_INTERVAL=1800
CORE_SCHEDULER_EXECUTION_TIMEOUT=600
CORE_SCHEDULER_KEEP_EXECUTION_HISTORY=60
```

## Background Processing

### 1. Task Execution Flow
```python
# Task execution process
async def execute_task(task_id):
    # 1. Load task configuration
    task = await self.db_ops.get_task(task_id)
    
    # 2. Create execution record
    execution = await self.db_ops.create_execution(task_id)
    
    # 3. Execute task
    try:
        # Import and call task function
        module = importlib.import_module(task.module_id)
        function = getattr(module, task.function_name)
        result = await function(task.parameters)
        
        # 4. Record success
        await self.db_ops.complete_execution(execution.id, success=True, result=result)
        
    except Exception as e:
        # 5. Record failure
        await self.db_ops.complete_execution(execution.id, success=False, error=str(e))
```

### 2. Background Task Management
```python
class SchedulerService:
    async def start_background_processing(self):
        """Start background task processing."""
        if self._is_running:
            return
            
        self._is_running = True
        self._scheduler_task = asyncio.create_task(self._scheduler_loop())
        
    async def _scheduler_loop(self):
        """Main scheduler loop."""
        while self._is_running:
            try:
                # Check for due tasks
                due_tasks = await self.db_ops.get_due_tasks()
                
                # Execute due tasks
                for task in due_tasks:
                    if len(self._background_tasks) < self.max_concurrent_tasks:
                        task_coro = self._execute_task_safely(task)
                        background_task = asyncio.create_task(task_coro)
                        self._background_tasks.append(background_task)
                
                # Clean up completed tasks
                self._background_tasks = [
                    task for task in self._background_tasks 
                    if not task.done()
                ]
                
                # Sleep until next check
                await asyncio.sleep(self.check_interval)
                
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                await asyncio.sleep(5)  # Error backoff
```

## Error Handling

### 1. Task Execution Errors
```python
async def _execute_task_safely(self, task):
    """Execute task with error handling."""
    execution_id = None
    try:
        # Create execution record
        execution = await self.db_ops.create_execution(task.id)
        execution_id = execution.id
        
        # Execute task
        result = await self._execute_task_function(task)
        
        # Record success
        await self.db_ops.complete_execution(
            execution_id, 
            success=True, 
            result=result
        )
        
    except Exception as e:
        # Record failure
        if execution_id:
            await self.db_ops.complete_execution(
                execution_id, 
                success=False, 
                error=str(e)
            )
        
        # Log error
        logger.error(error_message(
            module_id=MODULE_ID,
            error_type="TASK_EXECUTION_FAILED",
            details=f"Task {task.name} failed: {str(e)}"
        ))
```

### 2. Scheduler Service Errors
```python
async def schedule_task(self, task_config) -> Result:
    """Schedule a task with error handling."""
    try:
        # Validate task configuration
        validation_result = self._validate_task_config(task_config)
        if not validation_result.success:
            return validation_result
        
        # Create task
        task = await self.db_ops.create_task(task_config)
        
        return Result.success(data={"task_id": task.id})
        
    except Exception as e:
        return Result.error(
            code="TASK_SCHEDULING_FAILED",
            message=f"Failed to schedule task: {str(e)}",
            details={"config": task_config}
        )
```

## Best Practices

### 1. Task Function Design
```python
# ✅ CORRECT: Task function with Result pattern
async def cleanup_old_logs(parameters):
    """Clean up old log files."""
    try:
        days_to_keep = parameters.get("days_to_keep", 30)
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        
        # Perform cleanup
        deleted_count = await delete_old_logs(cutoff_date)
        
        return Result.success(data={
            "deleted_count": deleted_count,
            "cutoff_date": cutoff_date.isoformat()
        })
    except Exception as e:
        return Result.error(
            code="CLEANUP_FAILED",
            message=f"Log cleanup failed: {str(e)}"
        )

# ❌ WRONG: Task function without Result pattern
async def cleanup_old_logs(parameters):
    days_to_keep = parameters.get("days_to_keep", 30)
    # ... cleanup logic
    return deleted_count  # Inconsistent return type
```

### 2. Error Resilience
```python
# ✅ CORRECT: Resilient task scheduling
async def schedule_with_retry(task_config, max_retries=3):
    """Schedule task with retry logic."""
    for attempt in range(max_retries):
        result = await scheduler.schedule_task(task_config)
        if result.success:
            return result
        
        if attempt < max_retries - 1:
            await asyncio.sleep(2 ** attempt)  # Exponential backoff
    
    return result  # Return last failed result
```

### 3. Resource Management
```python
# ✅ CORRECT: Proper resource cleanup
async def long_running_task(parameters):
    """Task that manages resources properly."""
    resources = []
    try:
        # Acquire resources
        db_connection = await get_db_connection()
        resources.append(db_connection)
        
        file_handle = await open_file(parameters["file_path"])
        resources.append(file_handle)
        
        # Process data
        result = await process_data(db_connection, file_handle)
        
        return Result.success(data=result)
        
    except Exception as e:
        return Result.error(
            code="PROCESSING_FAILED",
            message=str(e)
        )
    finally:
        # Clean up resources
        for resource in resources:
            await safe_close(resource)
```

## Performance Considerations

### 1. Concurrent Task Limits
```python
# Configure concurrent task limits
SCHEDULER_SETTINGS = {
    "max_concurrent_tasks": {
        "type": "int",
        "default": 10,  # Adjust based on system capacity
        "description": "Maximum concurrent tasks"
    }
}
```

### 2. Execution History Cleanup
```python
# Automatic cleanup of old execution records
async def cleanup_execution_history(self):
    """Clean up old execution records."""
    cutoff_date = datetime.now() - timedelta(days=self.keep_execution_history)
    
    deleted_count = await self.db_ops.delete_old_executions(cutoff_date)
    
    logger.info(f"Cleaned up {deleted_count} old execution records")
```

### 3. Database Optimization
```python
# Optimize database queries
async def get_due_tasks(self):
    """Get tasks due for execution with optimized query."""
    query = """
        SELECT * FROM scheduler_events 
        WHERE status = 'pending' 
        AND next_execution <= ?
        ORDER BY next_execution ASC
        LIMIT 100
    """
    
    return await self.db_ops.execute_query(query, [datetime.now()])
```

## Related Documentation

- [Two-Phase Initialization](../patterns/two-phase-initialization.md) - Scheduler initialization patterns
- [Result Pattern](../patterns/result-pattern.md) - Task execution result handling
- [Database Module](database-module.md) - Database integration patterns
- [Error Handler Module](error-handler-module.md) - Error handling in scheduled tasks
- [Settings Module](settings-module.md) - Scheduler configuration management

---

The Scheduler Module provides a comprehensive task scheduling system that enables modules to execute time-based operations reliably while maintaining proper error handling, resource management, and execution tracking throughout the framework.
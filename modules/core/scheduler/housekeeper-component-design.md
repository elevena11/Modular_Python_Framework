# Housekeeper Component Design for Scheduler Module

**Version: 1.0.0**  
**Updated: March 25, 2025**

## Overview

The Housekeeper component provides centralized management of temporary files, logs, and other resources that require periodic cleanup. It's implemented as a specialized component within the Scheduler module, leveraging the scheduling infrastructure while providing a focused API for cleanup tasks.

## Organization

The Housekeeper will be organized as a component within the Scheduler module:

```
modules/
  core/
    scheduler/
      api.py                # Exposes scheduler and housekeeper endpoints
      services.py           # SchedulerService with Housekeeper integration
      database.py           # Database operations for both components
      db_models.py          # Database models for both components
      module_settings.py    # Combined settings for the module
      components/
        __init__.py
        job_manager.py      # Core scheduling functionality
        trigger_manager.py  # Handles different trigger types
        housekeeper.py      # Implements housekeeping functionality
```

## Core Functionality

The Housekeeper component maintains all the functionality described previously:

1. **Centralized Cleanup Registry**
   - Modules register their cleanup needs once
   - Configuration stored in database for persistence
   - Consistent interface across all modules

2. **Flexible Cleanup Policies**
   - Age-based retention (delete files older than X days)
   - Count-based retention (keep only the newest X files)
   - Size-based retention (keep only up to X MB)
   - Pattern matching for file selection

3. **Safe Operation**
   - Read-only option for testing cleanup logic
   - Dry-run capability with detailed reports
   - Atomicity guarantees for file operations
   - Error handling and recovery

4. **Monitoring and Reporting**
   - Cleanup operation statistics
   - Space reclamation metrics
   - Failure notifications
   - Audit trail of cleanup operations

## Architecture

### Component Structure

1. **Housekeeper Class**
   - Implements cleanup logic
   - Manages the registry of cleanup tasks
   - Provides API for registration and management
   - Integrates with JobManager for scheduling

2. **Cleanup Registry**
   - Database table for storing cleanup configurations
   - Stores paths, patterns, policies, priorities
   - Managed through the scheduler's database access

3. **File Processor**
   - Handles file matching and operations
   - Implements safe delete operations
   - Calculates file statistics

4. **Scheduler Integration**
   - Uses the Scheduler's job manager directly
   - Registers cleanup tasks as scheduled jobs
   - Leverages the scheduler's trigger system

## API Design

The Housekeeper component will expose its API through the SchedulerService:

### Implementation in Housekeeper Component

```python
class Housekeeper:
    """
    Provides centralized management of temporary files and logs that require periodic cleanup.
    """
    
    def __init__(self, app_context, job_manager):
        """
        Initialize the housekeeper component.
        
        Args:
            app_context: Application context
            job_manager: Scheduler's job manager component
        """
        self.app_context = app_context
        self.job_manager = job_manager
        self.logger = logging.getLogger("modular.scheduler.housekeeper")
        self.db_ops = None  # Will be set during initialization
    
    async def initialize(self, db_operations):
        """
        Initialize the housekeeper with database operations.
        
        Args:
            db_operations: Database operations instance
        """
        self.db_ops = db_operations
        
        # Register the cleanup job
        settings = await self.app_context.get_module_settings("core.scheduler")
        schedule = settings.get("housekeeper_schedule", "0 3 * * *")  # Default: 3 AM daily
        
        # Register the main cleanup job
        await self.job_manager.register_job(
            job_id="system_housekeeping",
            func=self.run_scheduled_cleanup,
            trigger="cron",
            cron_expression=schedule,
            description="System-wide cleanup of temporary files"
        )
    
    async def register_cleanup(
        self,
        directory: str,
        pattern: str = "*",
        retention_days: int = None,
        max_files: int = None,
        max_size_mb: int = None,
        priority: int = 100,
        description: str = None
    ) -> str:
        """
        Register a directory for periodic cleanup.
        
        Args:
            directory: Path to directory containing files to clean
            pattern: File matching pattern (e.g., "*.log", "temp_*")
            retention_days: Maximum age of files to keep (None = no limit)
            max_files: Maximum number of files to keep (None = no limit)
            max_size_mb: Maximum total size in MB (None = no limit)
            priority: Cleanup priority (lower = higher priority)
            description: Human-readable description
            
        Returns:
            Registration ID for reference
        """
        # Implementation details...
        pass
    
    # Other methods...
```

### Exposure through SchedulerService

```python
class SchedulerService:
    """
    Manages scheduled jobs and periodic cleanup tasks.
    """
    
    def __init__(self, app_context):
        """Initialize the scheduler service."""
        self.app_context = app_context
        self.job_manager = JobManager(app_context)
        self.trigger_manager = TriggerManager(app_context)
        self.housekeeper = Housekeeper(app_context, self.job_manager)
        # ...
    
    # Job management methods...
    
    # Housekeeper methods
    async def register_cleanup(self, directory, pattern="*", retention_days=None, **kwargs):
        """
        Register a directory for periodic cleanup.
        See Housekeeper.register_cleanup for full documentation.
        """
        return await self.housekeeper.register_cleanup(
            directory, pattern, retention_days, **kwargs
        )
    
    async def update_cleanup_config(self, registration_id, **config_updates):
        """Update an existing cleanup configuration."""
        return await self.housekeeper.update_cleanup_config(registration_id, **config_updates)
    
    async def remove_cleanup_config(self, registration_id):
        """Remove a cleanup configuration from the registry."""
        return await self.housekeeper.remove_cleanup_config(registration_id)
    
    async def get_cleanup_configs(self):
        """Get all registered cleanup configurations."""
        return await self.housekeeper.get_cleanup_configs()
    
    async def run_cleanup(self, registration_id=None, dry_run=False):
        """
        Run cleanup operations manually.
        
        Args:
            registration_id: Optional ID to clean specific registration only
            dry_run: If True, report what would be deleted without deleting
            
        Returns:
            Report of cleanup operation results
        """
        return await self.housekeeper.run_cleanup(registration_id, dry_run)
```

## Database Model

The cleanup registry will be stored in the database using this model:

```python
class CleanupConfig(Base):
    """Configuration for scheduled cleanup tasks."""
    __tablename__ = "scheduler_cleanup_configs"
    
    id = Column(String(36), primary_key=True)
    directory = Column(String(512), nullable=False)
    pattern = Column(String(128), nullable=False, default="*")
    retention_days = Column(Integer, nullable=True)
    max_files = Column(Integer, nullable=True)
    max_size_mb = Column(Integer, nullable=True)
    priority = Column(Integer, nullable=False, default=100)
    description = Column(String(256), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_run = Column(DateTime, nullable=True)
```

## Module Settings

The Scheduler module's settings will include Housekeeper configuration:

```python
DEFAULT_SETTINGS = {
    # Scheduler settings
    "job_history_retention_days": 30,
    "max_concurrent_jobs": 5,
    "default_timeout": 300,  # 5 minutes
    
    # Housekeeper settings
    "housekeeper_schedule": "0 3 * * *",  # Daily at 3 AM (cron format)
    "housekeeper_default_retention": 30,
    "housekeeper_dry_run": False,
    "housekeeper_read_only": False,
    "housekeeper_concurrent_cleanups": 3,
    "housekeeper_report_enabled": True,
    "housekeeper_report_directory": "",  # Empty = use default in DATA_DIR
}
```

## Usage Examples

Modules will register for cleanup during their Phase 2 initialization:

```python
async def setup_module(app_context):
    """Phase 2 initialization for a module."""
    # Get the scheduler service
    scheduler = app_context.get_service("scheduler_service")
    if scheduler:
        # Register log directory for cleanup
        await scheduler.register_cleanup(
            directory=log_dir,
            pattern="*.log",
            retention_days=30,
            description="Module log files"
        )
```

For the TraceLogger specifically:

```python
@classmethod
async def _register_with_housekeeper(cls):
    """Register trace logs with the Scheduler's Housekeeper component."""
    if cls.APP_CONTEXT:
        scheduler = cls.APP_CONTEXT.get_service("scheduler_service")
        if scheduler:
            try:
                logger.info("Registering trace logs with Scheduler's Housekeeper")
                await scheduler.register_cleanup(
                    directory=cls.TRACEFILE_DIR,
                    pattern="trace_*",
                    retention_days=cls.SETTINGS.get("retention_days", 7),
                    max_files=cls.SETTINGS.get("max_trace_files", 100),
                    description="Trace logger files"
                )
            except Exception as e:
                logger.error(f"Error registering with Housekeeper: {str(e)}")
        else:
            logger.info("Scheduler service not available - log cleanup will be handled externally")
```

## Advantages of the Component Approach

1. **Natural Integration**: Housekeeping tasks are inherently scheduled
2. **Shared Infrastructure**: Uses existing scheduling mechanisms
3. **Reduced Complexity**: One fewer module in the system
4. **Cleaner Dependencies**: Modules only need to depend on scheduler
5. **Unified Management**: Job scheduling and housekeeping managed together

## Implementation Phases

1. **Phase 1: Core Implementation**
   - Basic registry functionality within Scheduler
   - Scheduled cleanup job infrastructure
   - File matching and deletion logic

2. **Phase 2: Advanced Features**
   - Count-based and size-based cleanup policies
   - Improved reporting and monitoring
   - API for manual cleanup operations

3. **Phase 3: Optimization**
   - Performance improvements for large directories
   - Better concurrency management
   - Enhanced error recovery mechanisms

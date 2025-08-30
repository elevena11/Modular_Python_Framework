# Scheduler Module Refactoring Plan

## Current Structure Analysis

The current `services.py` (50KB) contains the following major functional areas:
- Service initialization and setup (~5KB)
- Scheduler loop implementation (~7KB)
- Event management (create, get, update, delete) (~10KB)
- Execution tracking and management (~12KB)
- Task execution logic (~8KB)
- Housekeeper integration (~4KB)
- Utility functions and helpers (~4KB)

## Proposed Component-Based Architecture

### New Components Structure

```
modules/core/scheduler/
├── components/
│   ├── __init__.py
│   ├── job_manager.py        # (existing) Job definition and registration
│   ├── trigger_manager.py    # (existing) Scheduling time calculations
│   ├── housekeeper.py        # (existing) File cleanup operations
│   ├── event_manager.py      # (new) Event CRUD operations
│   ├── execution_tracker.py  # (new) Execution history and tracking
│   └── scheduler_loop.py     # (new) Main scheduling loop
```

### Component Responsibilities

#### 1. EventManager
- Event CRUD operations (create, get, update, delete)
- Event filtering and querying
- Validation of event parameters
- Event status management

#### 2. ExecutionTracker
- Tracking event executions
- Creating and updating execution records
- Execution history management
- Execution status tracking and reporting

#### 3. SchedulerLoop
- Main scheduling loop implementation
- Due event detection
- Event execution orchestration
- Background task management

### Revised services.py Structure

The refactored `services.py` would focus on:
- Component initialization and coordination
- Service-level configuration
- Public API for external modules to interact with
- Shutdown handling
- High-level tracing and error handling

This would reduce it to approximately 15-20KB.

## Implementation Plan

### Phase 1: Preparation

1. Create interface definitions for each component
2. Document interaction patterns between components
3. Identify shared utility code and dependencies

### Phase 2: Component Implementation

1. Create `event_manager.py`:
   - Extract event-related methods from `services.py`
   - Add proper initialization and integration with database
   - Implement full CRUD operations for events

2. Create `execution_tracker.py`:
   - Extract execution tracking code from `services.py`
   - Implement methods for tracking event executions
   - Add execution history management

3. Create `scheduler_loop.py`:
   - Extract scheduling loop implementation from `services.py`
   - Make loop configurable and testable
   - Add proper background task management

### Phase 3: Service Integration

1. Refactor `services.py` to:
   - Initialize and manage components
   - Expose a cohesive public API
   - Forward calls to appropriate components
   - Handle shutdown and cleanup properly

2. Update initialization to properly create and connect components:
   ```python
   # Initialization sequence
   self.event_manager = EventManager(app_context, self.db_ops)
   self.execution_tracker = ExecutionTracker(app_context, self.db_ops)
   self.scheduler_loop = SchedulerLoop(app_context, self.event_manager, 
                                      self.execution_tracker, self.job_manager)
   ```

### Phase 4: Testing and Validation

1. Unit test each component individually
2. Integration test component interactions
3. System test full scheduler functionality
4. Verify backward compatibility for API users

## Migration Approach

To minimize risk, we'll use the following migration approach:

1. **Parallel Implementation**: Create new components while maintaining the existing service
2. **Gradual Transition**: Move functionality one component at a time while keeping tests passing
3. **Service Proxy**: Initially have `services.py` proxy calls to components before full refactoring
4. **Single Commit Point**: Combine final changes into a single cohesive commit

## Code Example: Refactored Services.py

Here's an example of what the refactored `services.py` might look like:

```python
"""
modules/core/scheduler/services.py
Updated: [Future Date]
Core service for Scheduler module - refactored to use component architecture
"""

import logging
from modules.core.error_handler.utils import Result, error_message
from modules.core.trace_logger.services import TraceLogger

# Import components
from .components.event_manager import EventManager
from .components.execution_tracker import ExecutionTracker
from .components.scheduler_loop import SchedulerLoop
from .components.job_manager import JobManager
from .components.trigger_manager import TriggerManager
from .components.housekeeper import Housekeeper
from .database import SchedulerDatabaseOperations

# Module identity
MODULE_ID = "core.scheduler"
logger = logging.getLogger(MODULE_ID)

class SchedulerService:
    """
    Manages scheduled tasks and periodic maintenance operations.
    
    This service coordinates components that handle specific aspects of scheduling:
    - EventManager: Manages event definitions and storage
    - ExecutionTracker: Tracks execution history and status
    - SchedulerLoop: Runs the main scheduling loop that executes events
    - JobManager: Handles job registration and execution
    - TriggerManager: Calculates execution times based on triggers
    - Housekeeper: Performs cleanup operations
    """
    
    def __init__(self, app_context):
        """Initialize the scheduler service."""
        self.app_context = app_context
        self.logger = logger
        self.initialized = False
        
        # Components will be initialized in Phase 2
        self.db_ops = SchedulerDatabaseOperations(app_context)
        self.event_manager = None
        self.execution_tracker = None
        self.scheduler_loop = None
        self.job_manager = None
        self.trigger_manager = None
        self.housekeeper = None
        
        # Background tasks tracking
        self._background_tasks = []
        
        self.logger.info(f"{MODULE_ID} service created (pre-Phase 2)")
    
    async def initialize(self, app_context=None, settings=None) -> bool:
        """Phase 2 initialization."""
        if self.initialized:
            return True
        
        context = app_context or self.app_context
        
        # Initialize database operations
        if not await self.db_ops.initialize():
            self.logger.error(error_message(
                module_id=MODULE_ID,
                error_type="DB_OPS_INITIALIZATION_FAILED",
                details="Failed to initialize database operations"
            ))
            return False
        
        # Initialize components
        self.event_manager = EventManager(context, self.db_ops)
        if not await self.event_manager.initialize():
            return False
            
        self.execution_tracker = ExecutionTracker(context, self.db_ops)
        if not await self.execution_tracker.initialize():
            return False
            
        self.job_manager = JobManager(context, self)
        if not await self.job_manager.initialize(self.db_ops):
            return False
            
        self.trigger_manager = TriggerManager(context)
        if not await self.trigger_manager.initialize():
            return False
            
        # Initialize housekeeper
        self.housekeeper = Housekeeper(context, self.job_manager)
        await self.housekeeper.initialize(self.db_ops)  # Non-critical
        
        # Load settings if not provided
        if settings is None:
            settings = await context.get_module_settings(MODULE_ID)
        
        # Initialize scheduler loop last
        self.scheduler_loop = SchedulerLoop(
            context,
            self.event_manager,
            self.execution_tracker,
            self.job_manager,
            settings
        )
        if not await self.scheduler_loop.initialize():
            return False
            
        # Start scheduler if enabled
        if settings.get("enabled", True):
            await self.scheduler_loop.start()
        
        self.initialized = True
        self.logger.info(f"{MODULE_ID} service initialized successfully")
        return True
    
    async def shutdown(self) -> None:
        """Graceful shutdown of the scheduler service."""
        if not self.initialized:
            return
            
        self.logger.info(f"Shutting down {MODULE_ID} service")
        
        # Stop scheduler loop
        if self.scheduler_loop:
            await self.scheduler_loop.stop()
        
        # Cancel all tracked background tasks
        for task in self._background_tasks:
            if not task.done():
                task.cancel()
        
        self.logger.info(f"{MODULE_ID} service shutdown complete")
    
    # Public API methods - delegate to components
    
    async def schedule_event(self, *args, **kwargs) -> Result:
        """Schedule a new event (delegates to EventManager)."""
        if not self.initialized or not self.event_manager:
            return Result.error(
                code="NOT_INITIALIZED",
                message="Scheduler service not initialized"
            )
        return await self.event_manager.create_event(*args, **kwargs)
    
    async def get_event(self, event_id: str) -> Result:
        """Get an event by ID (delegates to EventManager)."""
        if not self.initialized or not self.event_manager:
            return Result.error(
                code="NOT_INITIALIZED",
                message="Scheduler service not initialized"
            )
        return await self.event_manager.get_event(event_id)
    
    # Other API methods with similar delegation pattern...
```

## Key Benefits

1. **Improved maintainability**: Each component has a single responsibility
2. **Better testability**: Components can be tested independently
3. **Easier collaboration**: Team members can work on different components
4. **Clearer code organization**: Logical grouping of related functionality
5. **Reduced file sizes**: All files under 20KB for better readability

This refactoring maintains all existing functionality while making the code more maintainable and extensible for future development.
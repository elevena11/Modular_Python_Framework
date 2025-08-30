# Complete Guide: Decorator-Based Shutdown Architecture

**Status**: PRODUCTION READY - Successfully Deployed  
**Version**: v3.0.0 Extended Architecture  
**Implementation Date**: August 10, 2025

## Overview

The **Decorator-Based Shutdown Architecture** extends the Reality Anchor Hub's v3.0.0 centralized registration philosophy to shutdown handling. This system eliminates shutdown logging duplication across all framework services by providing centralized, declarative shutdown management.

## Architecture Philosophy

### The Problem We Solved

**Before**: Every service duplicated identical shutdown logging patterns:
```python
async def shutdown(self):
    self.logger.info(f"{MODULE_ID}: Shutting down service gracefully...")
    # ... actual cleanup code ...
    self.logger.info(f"{MODULE_ID}: Service shutdown complete")

def force_shutdown(self):
    self.logger.info(f"{MODULE_ID}: Force shutting down service...")
    # ... actual cleanup code ...  
    self.logger.info(f"{MODULE_ID}: Service force shutdown complete")
```

**Result**: 60+ duplicated logging statements across the framework.

### The Solution: Declarative Shutdown

**After**: Services focus only on cleanup logic, framework handles all logging:
```python
@graceful_shutdown(method="cleanup_resources", timeout=30, priority=10)
@force_shutdown(method="force_cleanup", timeout=5)
class DatabaseModule(DataIntegrityModule):
    
    async def cleanup_resources(self):
        # Only cleanup logic - NO LOGGING NEEDED
        await self.close_connections()
        self.stop_background_tasks()
    
    def force_cleanup(self):
        # Only cleanup logic - NO LOGGING NEEDED
        self.force_close_connections()
```

## Core Components

### 1. Shutdown Decorators

#### `@graceful_shutdown()`
Configures graceful async shutdown for normal application termination.

**Parameters:**
- `method` (str): Method name to call for cleanup (default: "shutdown")
- `timeout` (int): Max seconds to wait for shutdown (default: 30)
- `priority` (int): Shutdown order priority (lower = earlier, default: 100)
- `dependencies` (List[str]): Modules that must shutdown after this one

**Example:**
```python
@graceful_shutdown(method="cleanup_resources", timeout=30, priority=10)
class DatabaseModule(DataIntegrityModule):
    async def cleanup_resources(self):
        await self.close_database_connections()
        await self.flush_pending_transactions()
```

#### `@force_shutdown()`
Configures force synchronous shutdown for emergency termination.

**Parameters:**
- `method` (str): Method name to call for force cleanup (default: "force_shutdown")
- `timeout` (int): Max seconds to wait for force shutdown (default: 5)

**Example:**
```python
@force_shutdown(method="force_cleanup", timeout=5)
class ModelManagerModule(DataIntegrityModule):
    def force_cleanup(self):
        self.force_stop_gpu_workers()
        self.clear_model_memory()
```

#### `@shutdown_dependencies()`
Declares shutdown dependency order for proper service coordination.

**Example:**
```python
@shutdown_dependencies("standard.module1", "standard.module2")
class CoreModule(DataIntegrityModule):
    # This module shuts down BEFORE module1 and module2
```

### 2. Centralized Processing

#### ModuleProcessor Enhancement
The ModuleProcessor automatically discovers and registers shutdown metadata during module loading:

```python
# ModuleProcessor detects decorators and registers shutdown handlers
INFO - core.module_processor - core.database: Centralized registration - Graceful shutdown method 'cleanup_resources' (timeout: 30s, priority: 10)
INFO - core.module_processor - core.database: Centralized registration - Force shutdown method 'force_cleanup' (timeout: 5s)
INFO - core.module_processor - core.database: Registered 2 shutdown handlers via decorators
```

#### ApplicationContext Execution
The ApplicationContext executes shutdown handlers with centralized logging:

```python
# Framework provides ALL logging automatically
INFO - app.context - Executing decorator-based shutdown for 5 modules
INFO - app.context - core.database: Shutting down service gracefully...
INFO - app.context - core.database: Service shutdown complete
INFO - app.context - core.settings: Shutting down service gracefully...
INFO - app.context - core.settings: Service shutdown complete
```

### 3. Priority-Based Execution

Services shutdown in priority order (lower number = higher priority = shutdown earlier):

| Priority | Module | Shutdown Order |
|----------|---------|----------------|
| 10 | core.database, core.settings | 1st (Foundation services) |
| 20 | core.error_handler | 2nd |
| 40 | core.model_manager | 3rd |
| 100 | core.framework | 4th (Application services) |

## Implementation Guide

### Step 1: Add Shutdown Decorators

```python
# In your module's api.py
from core.decorators import (
    register_service,
    graceful_shutdown,
    force_shutdown
)

@register_service("my_module.service", priority=50)
@graceful_shutdown(method="cleanup_resources", timeout=30, priority=50)
@force_shutdown(method="force_cleanup", timeout=5)
class MyModule(DataIntegrityModule):
    MODULE_ID = "standard.my_module"
```

### Step 2: Implement Cleanup Methods

```python
# In your service class
class MyService:
    
    async def cleanup_resources(self):
        """
        Graceful resource cleanup - logging handled by decorator.
        Called during normal application shutdown.
        """
        # Close connections
        await self.close_network_connections()
        
        # Stop background tasks
        for task in self._background_tasks:
            task.cancel()
            try:
                await asyncio.wait_for(task, timeout=2.0)
            except (asyncio.TimeoutError, asyncio.CancelledError):
                pass
        
        # Save state
        await self.save_persistent_state()
    
    def force_cleanup(self):
        """
        Force cleanup of resources - logging handled by decorator.
        Called during emergency shutdown.
        """
        # Synchronous cleanup only
        try:
            self.force_close_connections()
            self.clear_memory_caches()
        except Exception:
            pass  # Ignore errors during force cleanup
```

### Step 3: Remove Manual Logging

**Remove all shutdown logging from your services:**
- Remove `self.logger.info(f"{MODULE_ID}: Shutting down...")`
- Remove `self.logger.info(f"{MODULE_ID}: Shutdown complete")`
- Remove `self.logger.error(f"Shutdown failed: {e}")`

**The framework handles ALL logging automatically.**

## Production Results

### Core Modules Successfully Converted

All 5 core framework modules have been converted to decorator-based shutdown:

1. **core.database** - Priority 10, 30s timeout
2. **core.settings** - Priority 10, 30s timeout  
3. **core.error_handler** - Priority 20, 30s timeout
4. **core.model_manager** - Priority 40, 30s timeout (10s force timeout)
5. **core.framework** - Priority 100, 30s timeout

### Test Results

**Successful shutdown execution with all modules:**
```
INFO - app.context - Executing decorator-based shutdown for 5 modules
INFO - app.context - core.database: Shutting down service gracefully...
INFO - app.context - core.database: Service shutdown complete
INFO - app.context - core.settings: Shutting down service gracefully...
INFO - app.context - core.settings: Service shutdown complete
INFO - app.context - core.error_handler: Shutting down service gracefully...
INFO - app.context - core.error_handler: Service shutdown complete
INFO - app.context - core.model_manager: Shutting down service gracefully...
INFO - app.context - core.model_manager: Service shutdown complete
INFO - app.context - core.framework: Shutting down service gracefully...
INFO - app.context - core.framework: Service shutdown complete
INFO - app.context - Decorator-based shutdown handlers completed
```

## Advanced Features

### Timeout Management

Each shutdown method can have custom timeouts:
```python
@graceful_shutdown(timeout=60)  # 60 seconds for complex cleanup
class ComplexModule(DataIntegrityModule):
    pass
```

The framework automatically handles timeouts:
```python
# Framework logs timeout errors automatically
INFO - app.context - core.module: Service shutdown timed out after 30s
```

### Dependency Management

Ensure proper shutdown ordering:
```python
@shutdown_dependencies("dependent.module1", "dependent.module2")
@graceful_shutdown(priority=10)
class CoreModule(DataIntegrityModule):
    # This shuts down BEFORE dependent modules
```

### Error Handling

The framework provides automatic error handling:
```python
# Framework catches and logs all shutdown errors
ERROR - app.context - core.module: Service shutdown failed - Connection timeout
```

## Migration Checklist

### For Existing Modules

- [ ] Add `graceful_shutdown` import to decorators
- [ ] Add `force_shutdown` import to decorators
- [ ] Add `@graceful_shutdown()` decorator to module class
- [ ] Add `@force_shutdown()` decorator to module class
- [ ] Create `cleanup_resources()` method (async)
- [ ] Create `force_cleanup()` method (sync)
- [ ] Remove ALL logging from shutdown methods
- [ ] Test shutdown behavior
- [ ] Remove legacy `shutdown()` methods (optional)

### For New Modules

- [ ] Include shutdown decorators from the start
- [ ] Design cleanup methods without logging
- [ ] Set appropriate priority levels
- [ ] Consider timeout requirements
- [ ] Plan dependency relationships

## Best Practices

### Cleanup Method Design

**DO:**
- Focus only on cleanup logic
- Handle exceptions gracefully in force_cleanup()
- Use async operations in cleanup_resources()
- Use sync operations in force_cleanup()
- Clear all state and resources

**DON'T:**
- Add any logging statements
- Block indefinitely in cleanup methods
- Raise exceptions in force_cleanup()
- Depend on other services during shutdown

### Priority Guidelines

**Priority Levels:**
- **1-10**: Core infrastructure (database, settings)
- **11-50**: Foundation services (error_handler, security)
- **51-100**: Application services (business logic)
- **100+**: UI and presentation services

### Timeout Guidelines

**Timeout Values:**
- **5 seconds**: Simple cleanup (memory clearing, flag setting)
- **30 seconds**: Standard cleanup (connections, background tasks)
- **60+ seconds**: Complex cleanup (file operations, model unloading)

## Troubleshooting

### Common Issues

**1. "Method not found" errors:**
```
WARNING - app.context - core.module: Shutdown method 'cleanup_resources' not found on service
```
**Solution**: Ensure your service class has the method specified in the decorator.

**2. "Service not found" errors:**
```
WARNING - app.context - core.module: Service not found for shutdown
```
**Solution**: Verify the service is registered with the correct name in `@register_service()`.

**3. Timeout errors:**
```
ERROR - app.context - core.module: Service shutdown timed out after 30s
```
**Solution**: Increase timeout in `@graceful_shutdown(timeout=60)` or optimize cleanup method.

### Debug Mode

Enable shutdown debugging by checking module processor logs:
```
INFO - core.module_processor - core.module: Registered 2 shutdown handlers via decorators
```

## Architectural Benefits

### Developer Experience
- **Zero Boilerplate**: No logging code needed in services
- **Declarative Configuration**: `@graceful_shutdown(timeout=30, priority=10)`
- **Automatic Registration**: Framework handles everything
- **Consistent Patterns**: Same pattern as all other framework features

### Framework Quality
- **60+ Fewer Lines**: Eliminated all duplicated logging code
- **Centralized Control**: Single point for shutdown behavior changes
- **Priority Management**: Automatic dependency-aware shutdown ordering
- **Timeout Protection**: Prevents hanging shutdowns

### Architectural Consistency
- **Perfect Consistency**: Shutdown uses same decorator pattern as service registration
- **centralized registration**: All framework features use declarative decorators
- **Maintainability**: Changes to shutdown logic benefit all modules instantly

## Future Enhancements

### Planned Features
- **Health Check Integration**: Shutdown health monitoring
- **Metrics Collection**: Automatic shutdown timing and success rate tracking
- **Advanced Dependencies**: Complex dependency resolution with circular detection
- **Conditional Shutdown**: Context-aware shutdown behavior

### Extension Points
The decorator system can be extended for additional shutdown behaviors:
- Pre-shutdown hooks
- Post-shutdown validation
- Custom shutdown strategies
- Integration with external systems

## Conclusion

The Decorator-Based Shutdown Architecture represents a major advancement in framework design, extending the v3.0.0 centralized registration philosophy to shutdown handling. By eliminating code duplication and providing centralized, declarative shutdown management, it dramatically improves both developer experience and framework maintainability.

**The result**: A shutdown system that is as declarative and centralized as every other framework feature, completing the vision of perfect architectural consistency across the entire Reality Anchor Hub framework.
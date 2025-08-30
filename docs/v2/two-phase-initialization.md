# Two-Phase Initialization

**Version: v3.0.0**  
**Updated: August 10, 2025**

## Overview

The Modular Framework uses a **two-phase initialization pattern** that separates lightweight registration from complex setup operations. This ensures fast, reliable startup while maintaining proper dependency ordering and error handling.

## Why Two-Phase Initialization?

### Problems with Single-Phase Init
- **Circular dependencies** - services needing each other during startup
- **Timing issues** - complex operations before infrastructure is ready
- **Failure cascades** - one module failure brings down the entire system
- **Slow startup** - all operations happen sequentially

### Benefits of Two-Phase
- **Fast Phase 1** - quick registration, cannot fail
- **Reliable startup** - infrastructure ready before complex operations
- **Priority ordering** - complex operations run in dependency order
- **Graceful errors** - Phase 2 failures don't prevent other modules from working
- **Parallel execution** - Phase 2 operations can run concurrently

## Phase Overview

### Phase 1: Registration
- **Fast and lightweight** - no complex operations
- **Cannot fail** - only registration and simple assignments
- **Synchronous** - runs immediately during module loading
- **Service registration** - add services to container
- **Hook registration** - register Phase 2 callbacks
- **Metadata setup** - store module information

### Phase 2: Complex Initialization  
- **Async operations** - database connections, file I/O, network calls
- **Can fail gracefully** - errors don't affect other modules
- **Priority ordered** - dependencies resolve first
- **Post-init hooks** - registered callbacks executed by priority
- **Full service access** - all Phase 1 services available

## Phase 1: Registration

### What Goes in Phase 1
```python
class MyModule(DataIntegrityModule):
    def __init__(self):
        """Phase 1: Light initialization only."""
        
        # ✅ Good - Light operations
        self.service = MyModuleService()           # Create service instance
        self.config = {}                          # Initialize simple data structures
        self.initialized = False                  # Set flags
        
        # ✅ Good - Store globally for API access
        global my_module_service
        my_module_service = self.service
        
        # ✅ Good - Basic logging
        logger.info(f"{self.MODULE_ID} Phase 1 complete")
```

### What NOT to do in Phase 1
```python  
class MyModule(DataIntegrityModule):
    def __init__(self):
        """Phase 1: Light initialization only."""
        
        # ❌ Bad - Database operations
        # await self.create_database_tables()
        
        # ❌ Bad - File I/O operations  
        # self.load_config_from_file()
        
        # ❌ Bad - Network calls
        # self.connect_to_external_api()
        
        # ❌ Bad - Accessing other services
        # other_service = app_context.get_service("other.service")
        
        # ❌ Bad - Complex validation
        # self.validate_external_dependencies()
        
        # ❌ Bad - Async operations
        # await self.async_setup()
```

### Service Registration
```python
class MyModule(DataIntegrityModule):
    def __init__(self):
        # Phase 1: Register the service
        # This happens automatically via @register_service decorator
        
        # Service is immediately available for other modules
        # app_context.get_service("standard.my_module.service") returns self.service
        pass
```

### Hook Registration for Phase 2
```python
class MyModule(DataIntegrityModule):  
    def __init__(self):
        # Register Phase 2 initialization
        # This happens automatically via decorator system
        # The framework calls initialize() in Phase 2
        pass
        
    async def initialize(self, app_context):
        """This runs in Phase 2."""
        return await self.service.initialize(app_context)
```

## Phase 2: Complex Initialization

### Automatic Hook Registration
The decorator system automatically registers `initialize()` as a Phase 2 hook:

```python
@register_service("standard.my_module.service", priority=100)
class MyModule(DataIntegrityModule):
    async def initialize(self, app_context):
        """Automatically called in Phase 2."""
        return True
```

### Manual Hook Registration
For custom Phase 2 operations:

```python
class MyModule(DataIntegrityModule):
    def __init__(self):
        # Custom Phase 2 hook
        app_context.register_post_init_hook(
            f"{self.MODULE_ID}.custom_setup",
            self.custom_setup,
            priority=150,
            dependencies=["core.database.setup"]
        )
    
    async def custom_setup(self, app_context):
        """Custom Phase 2 initialization."""
        # Complex operations here
        return True
```

### Phase 2 Implementation Pattern
```python
async def initialize(self, app_context):
    """Phase 2: Complex initialization."""
    try:
        logger.info(f"Initializing {self.MODULE_ID} (Phase 2)")
        
        # ✅ Get other services (they're all registered now)
        settings_service = app_context.get_service("core.settings.service") 
        database_service = app_context.get_service("core.database.service")
        
        # ✅ Load configuration
        settings = await self._load_settings(settings_service)
        
        # ✅ Initialize database connections
        await self._setup_database(database_service)
        
        # ✅ Connect to external services
        await self._connect_external_apis(settings)
        
        # ✅ Start background tasks
        await self._start_background_tasks()
        
        # ✅ Validate everything is working
        await self._validate_setup()
        
        self.initialized = True
        logger.info(f"{self.MODULE_ID} Phase 2 initialization complete")
        return True
        
    except Exception as e:
        logger.error(error_message(
            self.MODULE_ID,
            "INITIALIZATION_FAILED", 
            f"Phase 2 initialization failed: {str(e)}",
            "initialize()"
        ))
        return False
```

## Priority System

### Default Priorities
- **Phase 1**: All modules load at same priority (immediate)
- **Phase 2**: Priority-based execution (lower numbers first)

### Core Module Priorities
```python
# Infrastructure (0-10)
core.database.setup         # priority=0  - Foundation
database_register_settings  # priority=5  - Before settings service
core.error_handler.register_settings # priority=5 - Before settings service

# Core Services (10-50)  
core.settings.setup         # priority=10 - Configuration system
core.database.setup         # priority=20 - Database operations
core.error_handler.setup    # priority=30 - Error processing

# Application Services (100+)
standard.my_module.setup     # priority=100 - Default
```

### Setting Custom Priorities
```python
# For critical infrastructure
@register_service("core.logging.service", priority=5)

# For services that depend on many others
@register_service("standard.reporting.service", priority=200)

# Custom post-init hooks
app_context.register_post_init_hook(
    "my_module.late_setup", 
    self.late_setup,
    priority=250,
    dependencies=["core.settings.setup"]
)
```

## Dependency Management

### Declaring Dependencies
```python
class MyModule(DataIntegrityModule):
    MODULE_DEPENDENCIES = ["core.settings", "core.database"]
```

### Hook Dependencies
```python
app_context.register_post_init_hook(
    "my_module.setup",
    self.setup,
    priority=150,
    dependencies=["core.settings.setup", "core.database.setup"]
)
```

### Service Access in Phase 2
```python
async def initialize(self, app_context):
    # All declared dependencies are guaranteed to be available
    settings_service = app_context.get_service("core.settings.service")
    database_service = app_context.get_service("core.database.service")
    
    if not settings_service:
        logger.error("Settings service not available - check dependencies")
        return False
    
    # Service is guaranteed to exist due to dependency declaration
    config = await settings_service.get_module_settings(self.MODULE_ID)
    return True
```

## Real-World Example

Here's how the core modules implement two-phase initialization:

### Database Module
```python
@register_service("core.database.service", priority=0)
class DatabaseModule(DataIntegrityModule):
    def __init__(self):
        """Phase 1: Create service, discover databases."""
        self.database_service = DatabaseService()
        
        # Immediate database discovery (file-based)
        self.database_service.discover_databases()
        
        # Register settings hook (runs before settings service init)
        app_context.register_post_init_hook(
            "database_register_settings",
            register_database_settings,
            priority=5,  # Before settings.setup (priority=10)
            dependencies=[]
        )
    
    async def initialize(self, app_context):
        """Phase 2: Complex database operations."""
        return await self.database_service.initialize(app_context)
```

### Settings Module  
```python
@register_service("core.settings.service", priority=10)
class SettingsModule(DataIntegrityModule):
    def __init__(self):
        """Phase 1: Create settings service."""
        self.settings_service = SettingsService()
    
    async def initialize(self, app_context):
        """Phase 2: Load all module settings."""
        # Database and settings registration already complete
        # Can now load all registered settings
        return await self.settings_service.initialize(app_context)
```

### Application Module
```python
@register_service("standard.document_processor.service", priority=100)
class DocumentProcessorModule(DataIntegrityModule):
    MODULE_DEPENDENCIES = ["core.settings", "core.database"]
    
    def __init__(self):
        """Phase 1: Create service instance."""
        self.doc_service = DocumentProcessorService()
    
    async def initialize(self, app_context):
        """Phase 2: Connect to services and external APIs."""
        # All dependencies guaranteed available
        settings = await self._get_settings(app_context)
        database = await self._setup_database(app_context)
        
        # Connect to external services
        await self.doc_service.initialize(app_context, settings)
        return True
```

## Execution Flow

### Framework Startup Sequence
1. **Module Discovery** - Find all modules with decorators
2. **Phase 1 Execution** - Create module instances (all modules)
3. **Service Container Ready** - All services registered and available
4. **Database Creation** - File-based discovery creates databases
5. **Phase 2 Scheduling** - Sort hooks by priority and dependencies  
6. **Phase 2 Execution** - Run post-init hooks in order
7. **Application Ready** - All modules initialized and ready

### Detailed Phase 2 Flow
```
Priority 5:  database_register_settings, error_handler.register_settings
Priority 10: core.settings.setup (can access all registered settings)
Priority 20: core.database.setup, core.error_handler.setup
Priority 100: standard.my_module.setup (all infrastructure ready)
```

## Error Handling

### Phase 1 Errors
```python
def __init__(self):
    try:
        # Phase 1 operations
        self.service = MyService()
    except Exception as e:
        # Phase 1 errors are critical - framework cannot continue
        logger.critical(f"Phase 1 initialization failed: {str(e)}")
        raise  # Re-raise to stop framework startup
```

### Phase 2 Errors
```python
async def initialize(self, app_context):
    try:
        # Complex Phase 2 operations
        await self.setup_database()
        return True
    except Exception as e:
        # Phase 2 errors are isolated - other modules continue
        logger.error(error_message(
            self.MODULE_ID,
            "INITIALIZATION_FAILED",
            f"Phase 2 failed: {str(e)}",
            "initialize()"
        ))
        return False  # Module marked as failed, others continue
```

### Graceful Degradation
```python
async def initialize(self, app_context):
    """Initialize with graceful degradation."""
    
    # Critical components - must succeed
    try:
        await self.setup_core_functionality()
    except Exception as e:
        logger.error(f"Core functionality failed: {str(e)}")
        return False
    
    # Optional components - can fail without stopping module
    try:
        await self.setup_optional_features()
    except Exception as e:
        logger.warning(f"Optional features disabled: {str(e)}")
        # Continue without optional features
    
    # Background tasks - can fail without stopping module
    try:
        await self.start_background_tasks()
    except Exception as e:
        logger.warning(f"Background tasks disabled: {str(e)}")
        # Module works without background tasks
    
    return True  # Module is functional
```

## Best Practices

### Phase 1 Best Practices
✅ **Keep it simple** - only registration and basic setup  
✅ **No async operations** - Phase 1 is synchronous
✅ **No external dependencies** - services may not be ready
✅ **No complex validation** - defer to Phase 2
✅ **Store service globally** - for API endpoint access
✅ **Use decorators** - let framework handle registration

### Phase 2 Best Practices
✅ **Check service availability** - handle missing dependencies gracefully
✅ **Use proper error handling** - log errors, return boolean status
✅ **Implement graceful degradation** - optional features can fail
✅ **Follow dependency order** - use priorities for complex dependencies
✅ **Initialize background tasks last** - after core functionality works
✅ **Validate setup** - ensure everything works before returning True

### Common Mistakes
❌ **Complex operations in Phase 1** - causes startup failures
❌ **Not checking service availability** - leads to None reference errors
❌ **Ignoring initialization failures** - always check return values
❌ **Wrong priority ordering** - causes timing issues
❌ **Missing error handling** - crashes affect other modules
❌ **Forgetting async/await** - Phase 2 methods are async

## Debugging Initialization

### Enable Detailed Logging
```python
# Check module_loader.log for Phase 1 issues
# Check app.log for Phase 2 issues

# Look for these patterns:
"Phase 1 complete"                    # Phase 1 success
"Phase 2 initialization complete"     # Phase 2 success
"Post-initialization hook completed"  # Hook execution
"INITIALIZATION_FAILED"               # Phase 2 errors
```

### Common Issues and Solutions

**Issue**: Service not available in Phase 2
```python
# Problem
other_service = app_context.get_service("other.service")  # Returns None

# Solution: Check dependencies
MODULE_DEPENDENCIES = ["other.module"]  # Add missing dependency
```

**Issue**: Database not ready
```python
# Problem  
await self.database_operations()  # Fails because DB not created

# Solution: Use proper priority
priority=50  # After database setup (priority=20)
```

**Issue**: Settings not registered
```python
# Problem
settings = await settings_service.get_module_settings("my.module")  # None

# Solution: Register settings before settings service setup
app_context.register_post_init_hook(
    "my_module.register_settings",
    self.register_settings,
    priority=5  # Before settings.setup (priority=10)
)
```

The two-phase initialization pattern provides a robust foundation for complex application startup while maintaining clean separation of concerns and proper error handling.
# Two-Phase Initialization Pattern

The Two-Phase Initialization pattern is the cornerstone of the framework's module loading system. It separates simple service registration from complex dependency-aware setup operations, ensuring that all modules can be loaded in the correct order regardless of their dependencies.

## Overview

The Two-Phase Initialization pattern addresses the challenge of module dependencies by splitting initialization into two distinct phases:

1. **Phase 1**: Service registration and basic setup
2. **Phase 2**: Complex initialization with full dependency access

This pattern ensures that all modules can register their services before any module attempts to use services from other modules, eliminating initialization order dependencies.

## The Problem

Without two-phase initialization, modules would need to be loaded in a specific order based on their dependencies, which becomes complex and error-prone as the system grows:

```python
# PROBLEMATIC: Direct dependency during initialization
def initialize(app_context):
    # This fails if database module isn't loaded first
    db_service = app_context.get_service("core.database.service")  # May be None
    
    # This fails if settings module isn't loaded first
    settings = app_context.get_module_settings("my_module")  # May fail
    
    # Complex setup that depends on other modules
    self.setup_complex_operations()
```

## The Solution

Two-phase initialization solves this by deferring complex operations until all modules are loaded:

```python
# SOLUTION: Two-phase initialization
def initialize(app_context):
    """Phase 1: Register services only"""
    # Create service (no dependencies)
    service = MyModuleService(app_context)
    
    # Register service for others to use
    app_context.register_service("my_module.service", service)
    
    # Register Phase 2 initialization
    app_context.register_post_init_hook(
        "my_module.setup",
        service.initialize,
        dependencies=["core.database.setup", "core.settings.setup"]
    )

class MyModuleService:
    async def initialize(self):
        """Phase 2: Complex initialization with dependencies"""
        # Now safe to access other services
        self.db_service = self.app_context.get_service("core.database.service")
        self.settings = await self.app_context.get_module_settings("my_module")
        
        # Complex setup operations
        await self.setup_database()
        await self.start_background_tasks()
```

## Phase 1: Service Registration

### Purpose
- Register services in the service container
- Prepare for Phase 2 initialization
- Establish module presence in the system

### Characteristics
- **Synchronous or async**: Can be either
- **No dependencies**: Cannot access other module services
- **Lightweight**: Should be fast and simple
- **Error-free**: Should not fail under normal conditions

### What to Do in Phase 1
```python
async def initialize(app_context):
    """Phase 1: Service registration and basic setup"""
    
    # ✅ Create service instances
    service = MyModuleService(app_context)
    
    # ✅ Register services
    app_context.register_service("my_module.service", service)
    
    # ✅ Register database models
    from .db_models import MyModel
    app_context.register_models([MyModel])
    
    # ✅ Register settings
    await app_context.register_module_settings("my_module", MODULE_SETTINGS)
    
    # ✅ Register post-init hooks
    app_context.register_post_init_hook(
        "my_module.setup",
        service.initialize,
        priority=100,
        dependencies=["core.database.setup"]
    )
    
    # ✅ Register shutdown handlers
    app_context.register_shutdown_handler(service.shutdown)
```

### What NOT to Do in Phase 1
```python
async def initialize(app_context):
    """Phase 1: What NOT to do"""
    
    # ❌ Access other module services
    db_service = app_context.get_service("core.database.service")  # May be None
    
    # ❌ Access module settings
    settings = await app_context.get_module_settings("my_module")  # May fail
    
    # ❌ Perform database operations
    await db_service.create_tables()  # Service may not exist
    
    # ❌ Start background tasks
    asyncio.create_task(self.background_worker())  # Too early
    
    # ❌ Complex initialization
    await self.setup_complex_operations()  # Dependencies not ready
```

## Phase 2: Complex Initialization

### Purpose
- Access services from other modules
- Perform complex initialization operations
- Set up inter-module dependencies

### Characteristics
- **Async required**: Must be async
- **Dependency-aware**: Can access other module services
- **Order-aware**: Executes in dependency order
- **Can fail**: May fail and should handle errors gracefully

### Post-Init Hook Registration
```python
# Register post-init hook with dependencies
app_context.register_post_init_hook(
    name="my_module.setup",           # Unique hook name
    hook=service.initialize,          # Async function to call
    priority=100,                     # Lower number = higher priority
    dependencies=[                    # Must wait for these hooks
        "core.database.setup",
        "core.settings.setup"
    ]
)
```

### What to Do in Phase 2
```python
class MyModuleService:
    async def initialize(self):
        """Phase 2: Complex initialization"""
        
        # ✅ Access other module services
        self.db_service = self.app_context.get_service("core.database.service")
        self.settings_service = self.app_context.get_service("core.settings.service")
        
        # ✅ Load module settings
        self.settings = await self.app_context.get_module_settings("my_module")
        
        # ✅ Perform database operations
        await self.setup_database()
        
        # ✅ Start background tasks
        await self.start_background_tasks()
        
        # ✅ Initialize complex components
        await self.setup_integrations()
        
        # ✅ Mark as ready
        self.initialized = True
```

## Dependency Management

### Hook Dependencies
Dependencies are declared when registering post-init hooks:

```python
# Module A depends on core services
app_context.register_post_init_hook(
    "module_a.setup",
    service_a.initialize,
    dependencies=["core.database.setup", "core.settings.setup"]
)

# Module B depends on Module A
app_context.register_post_init_hook(
    "module_b.setup",
    service_b.initialize,
    dependencies=["module_a.setup"]
)
```

### Dependency Resolution
The framework automatically resolves dependencies using topological sorting:

```python
# Execution order based on dependencies:
1. core.database.setup
2. core.settings.setup
3. module_a.setup      # Depends on core services
4. module_b.setup      # Depends on module_a
```

### Priority System
Hooks can have priorities to control execution order within the same dependency level:

```python
# Higher priority (lower number) executes first
app_context.register_post_init_hook(
    "important_module.setup",
    service.initialize,
    priority=50,                    # High priority
    dependencies=["core.database.setup"]
)

app_context.register_post_init_hook(
    "regular_module.setup",
    service.initialize,
    priority=100,                   # Normal priority
    dependencies=["core.database.setup"]
)
```

## Common Patterns

### 1. Database-Dependent Module
```python
async def initialize(app_context):
    """Module that needs database access"""
    
    # Phase 1: Register service
    service = MyModuleService(app_context)
    app_context.register_service("my_module.service", service)
    
    # Register database models
    from .db_models import MyModel
    app_context.register_models([MyModel])
    
    # Phase 2: Database setup
    app_context.register_post_init_hook(
        "my_module.setup",
        service.initialize,
        dependencies=["core.database.setup"]
    )

class MyModuleService:
    async def initialize(self):
        """Phase 2: Database initialization"""
        self.db_service = self.app_context.get_service("core.database.service")
        
        # Database is now ready
        await self.create_initial_data()
```

### 2. Settings-Dependent Module
```python
async def initialize(app_context):
    """Module that needs settings"""
    
    # Phase 1: Register service and settings
    service = MyModuleService(app_context)
    app_context.register_service("my_module.service", service)
    
    # Register module settings
    await app_context.register_module_settings("my_module", MODULE_SETTINGS)
    
    # Phase 2: Settings-based initialization
    app_context.register_post_init_hook(
        "my_module.setup",
        service.initialize,
        dependencies=["core.settings.setup"]
    )

class MyModuleService:
    async def initialize(self):
        """Phase 2: Settings-based initialization"""
        # Load settings
        self.settings = await self.app_context.get_module_settings("my_module")
        
        # Configure based on settings
        self.timeout = self.settings.get("timeout", 30)
        self.enabled = self.settings.get("enabled", True)
```

### 3. Service-Dependent Module
```python
async def initialize(app_context):
    """Module that depends on another module's service"""
    
    # Phase 1: Register service
    service = MyModuleService(app_context)
    app_context.register_service("my_module.service", service)
    
    # Phase 2: Service integration
    app_context.register_post_init_hook(
        "my_module.setup",
        service.initialize,
        dependencies=["other_module.setup"]
    )

class MyModuleService:
    async def initialize(self):
        """Phase 2: Service integration"""
        # Access other module's service
        self.other_service = self.app_context.get_service("other_module.service")
        
        # Integrate with other service
        await self.other_service.register_callback(self.handle_events)
```

## Error Handling

### Phase 1 Error Handling
```python
async def initialize(app_context):
    """Phase 1: Handle errors gracefully"""
    try:
        # Service registration
        service = MyModuleService(app_context)
        app_context.register_service("my_module.service", service)
        
        # Register post-init hook
        app_context.register_post_init_hook(
            "my_module.setup",
            service.initialize,
            dependencies=["core.database.setup"]
        )
        
        return True
    except Exception as e:
        logger.error(f"Phase 1 initialization failed: {e}")
        return False
```

### Phase 2 Error Handling
```python
class MyModuleService:
    async def initialize(self):
        """Phase 2: Handle errors and report status"""
        try:
            # Complex initialization
            await self.setup_database()
            await self.start_background_tasks()
            
            self.initialized = True
            return True
        except Exception as e:
            logger.error(f"Phase 2 initialization failed: {e}")
            self.initialized = False
            return False
```

## Best Practices

### 1. Keep Phase 1 Simple
```python
# ✅ GOOD: Simple Phase 1
async def initialize(app_context):
    service = MyModuleService(app_context)
    app_context.register_service("my_module.service", service)
    
    app_context.register_post_init_hook(
        "my_module.setup",
        service.initialize,
        dependencies=["core.database.setup"]
    )

# ❌ BAD: Complex Phase 1
async def initialize(app_context):
    service = MyModuleService(app_context)
    await service.setup_database()  # Too complex for Phase 1
    await service.start_workers()   # Too complex for Phase 1
    app_context.register_service("my_module.service", service)
```

### 2. Declare Dependencies Explicitly
```python
# ✅ GOOD: Explicit dependencies
app_context.register_post_init_hook(
    "my_module.setup",
    service.initialize,
    dependencies=["core.database.setup", "core.settings.setup"]
)

# ❌ BAD: Implicit dependencies
app_context.register_post_init_hook(
    "my_module.setup",
    service.initialize
    # Missing dependencies - may fail if services not ready
)
```

### 3. Use Appropriate Priorities
```python
# ✅ GOOD: Logical priorities
app_context.register_post_init_hook(
    "core_module.setup",
    service.initialize,
    priority=10  # High priority for core modules
)

app_context.register_post_init_hook(
    "extension_module.setup",
    service.initialize,
    priority=200  # Lower priority for extensions
)
```

### 4. Handle Initialization Failures
```python
class MyModuleService:
    async def initialize(self):
        """Handle failures gracefully"""
        try:
            # Attempt initialization
            await self.setup_components()
            self.initialized = True
            return True
        except Exception as e:
            # Log error and mark as failed
            logger.error(f"Module initialization failed: {e}")
            self.initialized = False
            
            # Optionally add warning to app context
            self.app_context.add_warning(
                f"Module failed to initialize: {e}",
                level="warning",
                module_id="my_module"
            )
            return False
```

## Testing Two-Phase Initialization

### Testing Phase 1
```python
async def test_phase_1_initialization():
    """Test Phase 1 initialization"""
    app_context = MockAppContext()
    
    # Test Phase 1
    result = await initialize(app_context)
    assert result is True
    
    # Verify service registration
    service = app_context.get_service("my_module.service")
    assert service is not None
    
    # Verify hook registration
    hooks = app_context.post_init_hooks
    assert "my_module.setup" in hooks
```

### Testing Phase 2
```python
async def test_phase_2_initialization():
    """Test Phase 2 initialization"""
    app_context = MockAppContext()
    
    # Set up dependencies
    app_context.register_service("core.database.service", MockDatabaseService())
    
    # Test Phase 2
    service = MyModuleService(app_context)
    result = await service.initialize()
    assert result is True
    assert service.initialized is True
```

## Common Pitfalls

### 1. Accessing Services in Phase 1
```python
# ❌ WRONG: Accessing services in Phase 1
async def initialize(app_context):
    # This may fail if database module not loaded yet
    db_service = app_context.get_service("core.database.service")
    
    service = MyModuleService(app_context, db_service)
    app_context.register_service("my_module.service", service)
```

### 2. Forgetting Dependencies
```python
# ❌ WRONG: Missing dependencies
app_context.register_post_init_hook(
    "my_module.setup",
    service.initialize
    # Missing dependencies - service may not be ready
)
```

### 3. Circular Dependencies
```python
# ❌ WRONG: Circular dependencies
# Module A depends on Module B
app_context.register_post_init_hook(
    "module_a.setup",
    service_a.initialize,
    dependencies=["module_b.setup"]
)

# Module B depends on Module A
app_context.register_post_init_hook(
    "module_b.setup",
    service_b.initialize,
    dependencies=["module_a.setup"]  # Circular dependency!
)
```

## Related Patterns

- **[Service Registration](service-registration.md)**: How to register services in Phase 1
- **[Result Pattern](result-pattern.md)**: Error handling in Phase 2
- **[Database Patterns](database-patterns.md)**: Database initialization patterns
- **[Error Handling](error-handling-patterns.md)**: Handling initialization errors

---

The Two-Phase Initialization pattern is fundamental to the framework's modularity and ensures that all modules can be loaded successfully regardless of their dependencies. Following this pattern is essential for creating robust, maintainable modules.
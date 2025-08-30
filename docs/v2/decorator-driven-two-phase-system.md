# Decorator-Driven Two-Phase Initialization System

## Overview

The Decorator-Driven Two-Phase System preserves the proven two-phase initialization pattern while eliminating all manual boilerplate code through decorators. This combines the reliability of the battle-tested two-phase pattern with the consistency and simplicity of decorator-based module definition.

## The Problem with Manual Two-Phase Code

The original two-phase system worked perfectly but required repetitive manual boilerplate in every module:

```python
# OLD: Manual boilerplate (repetitive and error-prone)
async def initialize(app_context):
    """Phase 1: Manual service registration"""
    
    # Manual service creation
    service = MyModuleService(app_context)
    
    # Manual service registration  
    app_context.register_service("my_module.service", service)
    
    # Manual database model registration
    from .db_models import MyModel
    app_context.register_models([MyModel])
    
    # Manual settings registration
    await app_context.register_module_settings("my_module", MODULE_SETTINGS)
    
    # Manual post-init hook registration
    app_context.register_post_init_hook(
        "my_module.setup",
        service.initialize,
        priority=100,
        dependencies=["core.database.setup"]
    )
    
    # Manual shutdown handler registration
    app_context.register_shutdown_handler(service.shutdown)
```

**Problems:**
- ❌ Repetitive boilerplate in every module
- ❌ Easy to forget registration steps
- ❌ Inconsistent patterns between modules
- ❌ Error-prone manual registration

## The Decorator Solution

Decorators eliminate ALL the boilerplate while preserving the exact same two-phase behavior:

```python
# NEW: Decorators handle all boilerplate automatically
@register_service("my_module.service")
@auto_service_creation(service_class="MyModuleService")
@register_models(["MyModel"], database="my_module")
@define_settings(MyModuleSettings)
@phase2_operations("initialize", dependencies=["core.database.setup"], priority=100)
@graceful_shutdown(method="shutdown", timeout=30)
class MyModule(DataIntegrityModule):
    """Phase 1 and Phase 2 handled automatically by decorators!"""
    
    MODULE_ID = "standard.my_module"
    MODULE_NAME = "My Module"
    MODULE_DESCRIPTION = "Example module with decorator system"
    
    # No boilerplate code needed - decorators handle everything!
```

**Benefits:**
- ✅ Zero boilerplate code
- ✅ Impossible to forget registration steps
- ✅ Consistent pattern across all modules
- ✅ Same proven two-phase behavior

## How Decorators Map to Two-Phase Pattern

### Phase 1 Registration (Automatic via Decorators)

Each decorator automatically performs the equivalent manual registration:

| Decorator | Equivalent Manual Code |
|-----------|------------------------|
| `@register_service("name")` | `app_context.register_service("name", service)` |
| `@auto_service_creation(service_class="Service")` | `service = Service(app_context)` |
| `@register_models(["Model"])` | `app_context.register_models([Model])` |
| `@define_settings(Settings)` | `app_context.register_module_settings("module", settings)` |
| `@phase2_operations("method")` | `app_context.register_post_init_hook("module.setup", service.method)` |
| `@graceful_shutdown(method="shutdown")` | `app_context.register_shutdown_handler(service.shutdown)` |

### Phase 2 Execution (Automatic via Framework)

The framework automatically calls the methods specified in decorators:

```python
class MyModuleService:
    async def initialize(self):
        """Phase 2: Called automatically by @phase2_operations decorator"""
        
        # Safe to access other services (Phase 1 complete)
        self.db_service = self.app_context.get_service("core.database.service")
        self.settings = await self.app_context.get_module_settings("my_module")
        
        # Complex initialization
        await self.setup_database()
        await self.start_background_tasks()
        
        self.initialized = True
```

## Complete Decorator Reference

### Core Service Decorators

#### `@register_service(service_name, priority=100)`
**Purpose**: Register a service with the framework service container
**Phase**: 1 (Registration)
**Equivalent Manual Code**: `app_context.register_service(service_name, service_instance)`

```python
@register_service("my_module.service", priority=50)
@register_service("my_module.cache", priority=60)  # Multiple services per module
class MyModule(DataIntegrityModule):
    pass
```

#### `@auto_service_creation(service_class, attribute="service_instance")`
**Purpose**: Automatically create service instances during Phase 1
**Phase**: 1 (Registration)  
**Equivalent Manual Code**: `service = ServiceClass(app_context)`

```python
@auto_service_creation(service_class="MyModuleService")
@auto_service_creation(service_class="CacheService", attribute="cache_service")  # Multiple services
class MyModule(DataIntegrityModule):
    pass
```

### Initialization Decorators

#### `@phase2_operations(method_name, dependencies=[], priority=100)`
**Purpose**: Register methods to be called in Phase 2
**Phase**: 1 (Registration of hook), 2 (Method execution)
**Equivalent Manual Code**: `app_context.register_post_init_hook(name, method, dependencies, priority)`

```python
@phase2_operations("initialize", dependencies=["core.database.setup", "core.settings.setup"], priority=100)
class MyModule(DataIntegrityModule):
    async def initialize(self):
        """Called automatically in Phase 2"""
        # Complex initialization here
        pass
```

### Database Decorators

#### `@register_models(model_list, database="framework")`
**Purpose**: Register database models with the framework
**Phase**: 1 (Registration)
**Equivalent Manual Code**: `app_context.register_models(model_list)`

```python
@register_models(["User", "Document"], database="my_module")
class MyModule(DataIntegrityModule):
    pass
```

### Settings Decorators

#### `@define_settings(settings_class)`
**Purpose**: Register module settings schema
**Phase**: 1 (Registration)
**Equivalent Manual Code**: `app_context.register_module_settings(module_id, settings)`

```python
@define_settings(MyModuleSettings)
class MyModule(DataIntegrityModule):
    pass
```

### Lifecycle Decorators

#### `@graceful_shutdown(method, timeout=30, priority=100)`
**Purpose**: Register graceful shutdown handler
**Phase**: 1 (Registration)
**Equivalent Manual Code**: `app_context.register_shutdown_handler(service.method)`

```python
@graceful_shutdown(method="cleanup", timeout=30, priority=100)
class MyModule(DataIntegrityModule):
    async def cleanup(self):
        """Called during graceful shutdown"""
        pass
```

#### `@force_shutdown(method, timeout=5)`
**Purpose**: Register force shutdown handler
**Phase**: 1 (Registration)
**Equivalent Manual Code**: `app_context.register_force_shutdown_handler(service.method)`

```python
@force_shutdown(method="force_cleanup", timeout=5)
class MyModule(DataIntegrityModule):
    def force_cleanup(self):
        """Called during force shutdown"""
        pass
```

## Framework Execution Order

### Phase 1: Decorator Processing (Framework Automatic)
1. **Module Discovery**: Framework finds all modules with decorators
2. **Decorator Metadata Extraction**: Extract all decorator configurations
3. **Priority Ordering**: Sort modules by service priorities
4. **Service Creation**: Execute `@auto_service_creation` decorators
5. **Service Registration**: Execute `@register_service` decorators  
6. **Model Registration**: Execute `@register_models` decorators
7. **Settings Registration**: Execute `@define_settings` decorators
8. **Hook Registration**: Execute `@phase2_operations` decorators
9. **Shutdown Registration**: Execute `@graceful_shutdown`/`@force_shutdown` decorators

### Phase 2: Method Execution (Framework Automatic)
10. **Dependency Resolution**: Sort Phase 2 operations by dependencies
11. **Method Execution**: Call methods specified in `@phase2_operations` decorators
12. **Completion**: All modules fully initialized and ready

## Module Examples

### Simple Module (No Dependencies)
```python
@register_service("utils.service")
@auto_service_creation(service_class="UtilsService")
@graceful_shutdown(method="cleanup")
class UtilsModule(DataIntegrityModule):
    MODULE_ID = "standard.utils"
    MODULE_NAME = "Utilities Module"
    MODULE_DESCRIPTION = "Utility functions and helpers"
```

### Database-Dependent Module
```python
@register_service("processor.service") 
@auto_service_creation(service_class="ProcessorService")
@register_models(["ProcessingJob", "ProcessingResult"], database="processor")
@phase2_operations("initialize", dependencies=["core.database.setup"], priority=150)
@graceful_shutdown(method="shutdown", timeout=30)
class ProcessorModule(DataIntegrityModule):
    MODULE_ID = "standard.processor"
    MODULE_NAME = "Data Processor"
    MODULE_DESCRIPTION = "Background data processing"
    
    async def initialize(self):
        """Phase 2: Database setup after core.database is ready"""
        self.db_service = self.app_context.get_service("core.database.service")
        await self.setup_processing_tables()
        await self.start_background_workers()
```

### Multi-Service Module
```python
@register_service("api.service", priority=100)
@register_service("api.cache", priority=110)  
@auto_service_creation(service_class="APIService")
@auto_service_creation(service_class="CacheService", attribute="cache_service")
@define_settings(APISettings)
@phase2_operations("initialize", dependencies=["core.settings.setup"], priority=200)
@provides_api_endpoints(router_name="router", prefix="/api/v1")
@graceful_shutdown(method="shutdown")
class APIModule(DataIntegrityModule):
    MODULE_ID = "standard.api"
    MODULE_NAME = "API Module" 
    MODULE_DESCRIPTION = "REST API endpoints"
    
    async def initialize(self):
        """Phase 2: Settings-based initialization"""
        self.settings = await self.app_context.get_module_settings("api")
        await self.configure_rate_limiting()
        await self.start_cache_cleanup_task()
```

## Decorator Combinations

### Core Foundation Module
```python
@register_service("core.database.service", priority=10)
@register_service("core.database.crud", priority=15)
@auto_service_creation(service_class="DatabaseService") 
@auto_service_creation(service_class="CRUDService", attribute="crud_service")
@phase2_operations("setup_databases", dependencies=[], priority=5)  # No dependencies - runs first
@provides_api_endpoints(router_name="router", prefix="/db")
@graceful_shutdown(method="cleanup", priority=10)  # High priority shutdown
class DatabaseModule(DataIntegrityModule):
    MODULE_ID = "core.database"
    MODULE_NAME = "Database Module"
    MODULE_DESCRIPTION = "Core database management"
```

### Extension Module
```python
@register_service("extensions.analytics.service")
@auto_service_creation(service_class="AnalyticsService")
@register_models(["Event", "Metric"], database="analytics") 
@define_settings(AnalyticsSettings)
@phase2_operations("initialize", dependencies=["core.database.setup", "core.settings.setup"], priority=200)
@provides_api_endpoints(router_name="router", prefix="/analytics")
@module_health_check(interval=300)
@graceful_shutdown(method="shutdown")
class AnalyticsModule(DataIntegrityModule):
    MODULE_ID = "extensions.analytics"
    MODULE_NAME = "Analytics Extension"
    MODULE_DESCRIPTION = "Usage analytics and metrics"
```

## Migration from Manual to Decorator System

### Step 1: Identify Manual Code
Find all manual registration code in existing modules:
- `app_context.register_service()`
- `app_context.register_models()`
- `app_context.register_module_settings()`
- `app_context.register_post_init_hook()`
- `app_context.register_shutdown_handler()`

### Step 2: Add Decorators
Replace manual code with equivalent decorators:

```python
# BEFORE: Manual registration
async def initialize(app_context):
    service = MyService(app_context)
    app_context.register_service("my.service", service)
    app_context.register_post_init_hook("my.setup", service.init, dependencies=["core.database.setup"])

# AFTER: Decorator registration  
@register_service("my.service")
@auto_service_creation(service_class="MyService")
@phase2_operations("init", dependencies=["core.database.setup"])
class MyModule(DataIntegrityModule):
    pass
```

### Step 3: Remove Manual Code
Delete the entire manual `initialize()` function - decorators handle everything.

### Step 4: Verify Behavior
Ensure the module behaves identically to the manual version.

## Benefits of Decorator System

### For Module Developers
- ✅ **Zero boilerplate**: No repetitive registration code
- ✅ **Impossible to forget**: Decorators ensure all registrations happen
- ✅ **Consistent pattern**: Same decorator pattern for all modules
- ✅ **Self-documenting**: Decorators clearly show module capabilities
- ✅ **IDE support**: Better autocomplete and validation

### For Framework Maintainers  
- ✅ **Centralized logic**: All registration logic in one place
- ✅ **Easier debugging**: Clear execution order and logging
- ✅ **Better validation**: Framework can validate decorator combinations
- ✅ **Future extensibility**: Easy to add new decorator types

### For Framework Users
- ✅ **Reliable**: Same proven two-phase pattern behavior
- ✅ **Predictable**: Consistent module loading across all modules
- ✅ **Maintainable**: Easier to understand and modify modules

## Comparison: Manual vs Decorator

| Aspect | Manual System | Decorator System |
|--------|---------------|------------------|
| **Lines of code** | 20-30 per module | 5-10 per module |
| **Error potential** | High (easy to forget steps) | Low (automatic) |
| **Consistency** | Varies by developer | Always consistent |
| **Readability** | Verbose boilerplate | Clear declarations |
| **Maintainability** | Requires discipline | Self-maintaining |
| **Learning curve** | Must memorize all steps | Just learn decorator names |

## Implementation Guidelines

### Decorator Order
Apply decorators in this recommended order for readability:
1. Service decorators (`@register_service`, `@auto_service_creation`)
2. Data decorators (`@register_models`, `@define_settings`) 
3. Lifecycle decorators (`@phase2_operations`)
4. API decorators (`@provides_api_endpoints`)
5. Monitoring decorators (`@module_health_check`)
6. Shutdown decorators (`@graceful_shutdown`, `@force_shutdown`)

### Priority Guidelines
Use these priority ranges:
- **Core foundation (0-50)**: database, logging, error handling
- **Core services (51-100)**: settings, model management 
- **Standard modules (101-200)**: business logic modules
- **Extensions (201-300)**: optional features and integrations

### Naming Conventions
- Service names: `"module_category.module_name.service"`
- Hook names: Auto-generated as `"module_id.method_name"`
- Model databases: Use module name or `"framework"` for shared

---

**The Decorator-Driven Two-Phase System preserves all the benefits of the proven two-phase initialization pattern while eliminating boilerplate and ensuring consistency across all modules.**
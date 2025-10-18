# Module Decorator System - Complete Reference

## Overview

The framework uses a **decorator-driven architecture** where all module initialization, registration, and lifecycle management is controlled through decorators. The `ModuleProcessor` reads decorator metadata and handles all registration automatically.

**IMPORTANT: Settings are MANDATORY for all modules.** Every module must have a `settings.py` file with a Pydantic v2 model, a `setup_infrastructure()` method, and the `@initialization_sequence("setup_infrastructure", phase="phase1")` decorator. This is enforced by the scaffold tool and framework architecture.

## Available Decorators

### 1. Service Registration
```python
@register_service(service_name: str, methods: List[ServiceMethod], priority: int = 100)
```
- **Purpose**: Register services with full method documentation for discovery
- **Required**: Yes, for all modules that provide services
- **Example**: `@register_service("my_module.service", methods=[...], priority=100)`

### 2. Dependency Injection
```python
@inject_dependencies(*dependency_names: str, optional: List[str] = None)
```
- **Purpose**: Automatic dependency injection into module constructor
- **Required**: Yes, if module needs app_context or other services
- **Example**: `@inject_dependencies('app_context')`

### 3. Service Creation
```python
@auto_service_creation(service_class: str = None, constructor_args: Dict = None)
```
- **Purpose**: Automatically create service instance with injected dependencies
- **Required**: Yes, for all modules
- **Example**: `@auto_service_creation(service_class="MyModuleService")`

### 4. Initialization Sequence
```python
@initialization_sequence(*method_names: str, phase: str = "phase1")
```
- **Purpose**: Define methods to call during Phase 1/Phase 2
- **Required**: Yes, ALL modules MUST use this for settings registration
- **Example**: `@initialization_sequence("setup_infrastructure", phase="phase1")`
- **Critical**: Every module must register its Pydantic settings model during Phase 1

### 5. Phase 2 Operations
```python
@phase2_operations(*method_names: str, dependencies: List[str] = None, priority: int = 100)
```
- **Purpose**: Define methods to call during Phase 2 initialization
- **Required**: Yes, for complex initialization after all services are available
- **Example**: `@phase2_operations("initialize_phase2", priority=100)`

### 6. API Endpoints
```python
@register_api_endpoints(router_name: str = "router")
```
- **Purpose**: Register FastAPI routes automatically
- **Required**: Only if module has API endpoints
- **Example**: `@register_api_endpoints(router_name="router")`

### 7. Data Integrity
```python
@enforce_data_integrity(strict_mode: bool = True, anti_mock: bool = True)
```
- **Purpose**: Enforce data integrity requirements
- **Required**: Yes, for all modules
- **Example**: `@enforce_data_integrity(strict_mode=True, anti_mock=True)`

### 8. Health Checks
```python
@module_health_check(check_function: Callable = None, interval: int = 300)
```
- **Purpose**: Register periodic health check
- **Required**: Optional (recommended for production)
- **Example**: `@module_health_check(interval=300)`

### 9. Graceful Shutdown
```python
@graceful_shutdown(method: str = "cleanup_resources", timeout: int = 30, priority: int = 100)
```
- **Purpose**: Register async cleanup method
- **Required**: Yes, for proper resource cleanup
- **Example**: `@graceful_shutdown(method="cleanup_resources", timeout=30)`

### 10. Force Shutdown
```python
@force_shutdown(method: str = "force_cleanup", timeout: int = 5)
```
- **Purpose**: Register sync force cleanup
- **Required**: Yes, for emergency shutdown
- **Example**: `@force_shutdown(method="force_cleanup", timeout=5)`

### 11. Service Requirements
```python
@require_services(service_names: List[str])
```
- **Purpose**: Declare required services from other modules
- **Required**: Only if module depends on other module services
- **Example**: `@require_services(["core.database.service"])`

### 12. Database Registration
```python
@register_database(database_name: str, auto_create: bool = True, models: List[str] = None)
```
- **Purpose**: Register database requirements
- **Required**: Only if module has dedicated database
- **Example**: `@register_database("my_module", models=["User", "Document"])`

## Module Processing Flow (14 Steps)

The `ModuleProcessor` executes these steps when processing each module:

1. **Validate decorator metadata** - Ensure decorators are properly applied
2. **Enforce data integrity** - Check integrity requirements
3. **Process dependencies** - Resolve module dependencies
4. **Store service metadata** - Save service definitions for later
5. **Process Settings V2** - Handle Pydantic settings (future)
6. **Register databases/models** - Set up database access
7. **Register API endpoints** - Configure FastAPI routes
8. **Setup health checks** - Initialize monitoring
9. **Process shutdown metadata** - Register cleanup handlers
10. **Process dependency injection** - Store injection config
11. **Process initialization sequences** - Store Phase 1/2 methods
12. **Process Phase 2 operations** - Register post-init hooks
13. **Process auto service creation** - Store service creation config
14. **Record success** - Mark module as processed

## Complete Decorator Stack

### Standard Module (Complete)
All modules must include these decorators:
```python
@inject_dependencies('app_context')
@register_service("module_id.service", methods=[...], priority=100)
@initialization_sequence("setup_infrastructure", phase="phase1")  # CRITICAL for settings!
@phase2_operations("initialize_phase2")
@auto_service_creation(service_class="ModuleService")
@register_api_endpoints(router_name="router")
@enforce_data_integrity(strict_mode=True, anti_mock=True)
@graceful_shutdown(method="cleanup_resources", timeout=30)
@force_shutdown(method="force_cleanup", timeout=5)
class MyModule(DataIntegrityModule):
    MODULE_ID = "standard.my_module"
    MODULE_VERSION = "1.0.0"
    MODULE_DESCRIPTION = "Module description"
```

### Core Module Example (database)
```python
@register_service("core.database.service", methods=[...])
@register_service("core.database.crud_service", methods=[...])
@inject_dependencies("app_context")
@auto_service_creation(service_class="DatabaseService")
@initialization_sequence("setup_foundation", "create_crud_service", phase="phase1")
@phase2_operations("initialize_phase2", priority=5)
@register_api_endpoints(router_name="router")
@enforce_data_integrity(strict_mode=True, anti_mock=True)
@module_health_check(interval=300)
@graceful_shutdown(method="cleanup_resources", timeout=30, priority=10)
@force_shutdown(method="force_cleanup", timeout=5)
class DatabaseModule(DataIntegrityModule):
```

## Critical Patterns

### Settings Registration Pattern (MANDATORY)
**ALL modules MUST include Phase 1 initialization to register settings:**

```python
@initialization_sequence("setup_infrastructure", phase="phase1")
class MyModule(DataIntegrityModule):
    def setup_infrastructure(self):
        """Phase 1: Register Pydantic settings model (NO service access)."""
        try:
            from .settings import MyModuleSettings
            self.app_context.register_pydantic_model(self.MODULE_ID, MyModuleSettings)
            logger.info(f"{self.MODULE_ID}: Pydantic settings model registered")
        except Exception as e:
            logger.warning(f"{self.MODULE_ID}: Error registering Pydantic model: {e}")
```

**WHY THIS IS MANDATORY:**
- Every module must have a `settings.py` file with a Pydantic v2 model
- Without `@initialization_sequence`, the framework won't call `setup_infrastructure()`
- Without calling `setup_infrastructure()`, Pydantic models aren't registered
- Without registration, `core.settings` can't load the module's settings
- The scaffold tool enforces this pattern - all generated modules include it

### Service Creation Pattern
```python
@inject_dependencies('app_context')  # Inject dependencies
@auto_service_creation(service_class="MyService")  # Auto-create service
class MyModule(DataIntegrityModule):
    def __init__(self):
        super().__init__()
        self.service_instance = None  # Will be set by auto_service_creation
```

### Phase 2 Pattern
```python
@phase2_operations("initialize_phase2")
class MyModule(DataIntegrityModule):
    async def initialize_phase2(self):
        """Phase 2: Initialize with guaranteed service access."""
        # All services are available here
        settings_service = self.app_context.get_service("core.settings.service")
        # ... complex initialization
```

## Decorator Order

Decorators are applied bottom-to-top, so order matters:

1. `@inject_dependencies` - MUST be first (closest to class)
2. `@register_service` - Service definitions
3. `@require_services` - Service dependencies (if needed)
4. `@initialization_sequence` - Phase 1 setup
5. `@phase2_operations` - Phase 2 setup
6. `@auto_service_creation` - Service instance creation
7. `@register_api_endpoints` - API routes
8. `@enforce_data_integrity` - Integrity checks
9. `@module_health_check` - Health monitoring
10. `@graceful_shutdown` - Cleanup
11. `@force_shutdown` - Force cleanup

## Startup Sequence

1. **Framework Discovery** - Scans modules/
2. **Decorator Processing** - ModuleProcessor reads metadata
3. **Module Instantiation** - Creates module instance
4. **Auto Service Creation** - Creates service instance
5. **Phase 1 Methods** - Executes `@initialization_sequence(phase="phase1")` methods
6. **Service Registration** - Registers services with app_context
7. **Phase 2 Hooks** - Executes `@phase2_operations` methods
8. **Application Ready** - All modules initialized

## Common Mistakes

### Missing Phase 1 Decorator
❌ **Wrong:**
```python
class MyModule(DataIntegrityModule):
    def setup_infrastructure(self):  # Won't be called!
        self.app_context.register_pydantic_model(...)
```

✅ **Correct:**
```python
@initialization_sequence("setup_infrastructure", phase="phase1")
class MyModule(DataIntegrityModule):
    def setup_infrastructure(self):  # Will be called automatically
        self.app_context.register_pydantic_model(...)
```

### Missing Service Creation
❌ **Wrong:**
```python
class MyModule(DataIntegrityModule):
    def __init__(self):
        super().__init__()
        self.service_instance = MyService(self.app_context)  # Manual creation
```

✅ **Correct:**
```python
@auto_service_creation(service_class="MyService")
class MyModule(DataIntegrityModule):
    def __init__(self):
        super().__init__()
        self.service_instance = None  # Auto-created by decorator
```

### Missing Dependency Injection
❌ **Wrong:**
```python
class MyModule(DataIntegrityModule):
    def __init__(self, app_context):  # app_context won't be provided
        self.app_context = app_context
```

✅ **Correct:**
```python
@inject_dependencies('app_context')
class MyModule(DataIntegrityModule):
    def __init__(self):  # app_context injected automatically
        super().__init__()
```

## References

- Decorator definitions: `core/decorators.py`
- Processing logic: `core/module_processor.py`
- Module manager: `core/module_manager.py`
- Example modules: `modules/core/database/`, `modules/core/framework/`

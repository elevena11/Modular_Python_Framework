# Module Decorator System - Complete Reference

## Overview

The framework uses a **mandatory-all-decorators architecture** where ALL modules must include ALL all mandatory decorators. This enforces consistency, prevents configuration drift, and ensures the framework can process every module through the same processing pipeline.

**CRITICAL: MANDATORY-ALL-DECORATORS ARCHITECTURE**
- Every module MUST have ALL all mandatory decorators
- Use `None` or empty values for unused features (e.g., `@register_database(database_name=None)`)
- No exceptions - all modules follow the same pattern
- The scaffolding tool enforces this by generating all decorators automatically
- Missing decorators will trigger MODULE COMPLIANCE warnings

**WHY MANDATORY?**
- **Consistency**: All modules follow identical patterns
- **Predictability**: Framework processing is uniform across all modules
- **Discovery**: Services can enumerate all module capabilities
- **No Configuration Drift**: Can't accidentally forget decorators
- **Clean Architecture**: No special cases or exceptions

## Available Decorators

### 1. Dependency Injection
```python
@inject_dependencies(*dependency_names: str, optional: List[str] = None)
```
- **Purpose**: Automatic dependency injection into module constructor
- **Required**: MANDATORY - All modules need app_context
- **Pattern**: Always use `@inject_dependencies('app_context')`
- **Example**: `@inject_dependencies('app_context')`

### 2. Service Registration
```python
@register_service(service_name: str, methods: List[ServiceMethod], priority: int = 100)
```
- **Purpose**: Register services with full method documentation for discovery
- **Required**: MANDATORY - All modules must define service interface
- **Pattern**: Always include `initialize`, `get_status`, and feature-specific methods
- **Example**: `@register_service("my_module.service", methods=[...], priority=100)`

### 3. Service Requirements
```python
@require_services(service_names: List[str])
```
- **Purpose**: Declare required services from other modules
- **Required**: MANDATORY - Use empty list `[]` if no external services needed
- **Pattern**: List all external services module depends on
- **Example**: `@require_services(["core.database.service"])` or `@require_services([])`

### 4. Initialization Sequence
```python
@initialization_sequence(*method_names: str, phase: str = "phase1")
```
- **Purpose**: Define methods to call during Phase 1 (settings registration)
- **Required**: MANDATORY - ALL modules MUST register Pydantic settings
- **Pattern**: Always use `@initialization_sequence("setup_infrastructure", phase="phase1")`
- **Example**: `@initialization_sequence("setup_infrastructure", phase="phase1")`
- **Critical**: Every module must register its Pydantic settings model during Phase 1

### 5. Phase 2 Operations
```python
@phase2_operations(*method_names: str, dependencies: List[str] = None, priority: int = 100)
```
- **Purpose**: Define methods to call during Phase 2 (complex initialization)
- **Required**: MANDATORY - All modules use this for service initialization
- **Pattern**: Always use `@phase2_operations("initialize_phase2")`
- **Example**: `@phase2_operations("initialize_phase2", priority=100)`

### 6. Service Creation
```python
@auto_service_creation(service_class: str = None, constructor_args: Dict = None)
```
- **Purpose**: Automatically create service instance with injected dependencies
- **Required**: MANDATORY - All modules must have service instance
- **Pattern**: Always provide service class name matching your services.py
- **Example**: `@auto_service_creation(service_class="MyModuleService")`

### 7. API Endpoints
```python
@register_api_endpoints(router_name: str = "router")
```
- **Purpose**: Register FastAPI routes automatically
- **Required**: MANDATORY - Use `router_name="router"` even if router is empty
- **Pattern**: Always define `router` in api.py with at least `/status` and `/info` endpoints
- **Example**: `@register_api_endpoints(router_name="router")`

### 8. Database Registration
```python
@register_database(database_name: str, auto_create: bool = True, models: List[str] = None)
```
- **Purpose**: Register database requirements
- **Required**: MANDATORY - Use `database_name=None` if no database needed
- **Pattern**: Provide database name if module has database, otherwise None
- **Example**: `@register_database(database_name="my_module")` or `@register_database(database_name=None)`

### 9. Data Integrity
```python
@enforce_data_integrity(strict_mode: bool = True, anti_mock: bool = True)
```
- **Purpose**: Enforce data integrity requirements
- **Required**: MANDATORY - All modules must declare integrity mode
- **Pattern**: Always use `@enforce_data_integrity(strict_mode=True, anti_mock=True)`
- **Example**: `@enforce_data_integrity(strict_mode=True, anti_mock=True)`

### 10. Health Checks
```python
@module_health_check(check_function: Callable = None, interval: int = 300)
```
- **Purpose**: Register periodic health check
- **Required**: MANDATORY - Use `check_function=None` or custom function
- **Pattern**: Use None for basic health check or provide custom function
- **Example**: `@module_health_check(check_function=None)` or `@module_health_check(interval=300)`

### 11. Graceful Shutdown
```python
@graceful_shutdown(method: str = "cleanup_resources", timeout: int = 30, priority: int = 100)
```
- **Purpose**: Register async cleanup method
- **Required**: MANDATORY - All modules must define cleanup
- **Pattern**: Always implement `cleanup_resources()` async method
- **Example**: `@graceful_shutdown(method="cleanup_resources", timeout=30)`

### 12. Force Shutdown
```python
@force_shutdown(method: str = "force_cleanup", timeout: int = 5)
```
- **Purpose**: Register sync force cleanup
- **Required**: MANDATORY - All modules must define emergency cleanup
- **Pattern**: Always implement `force_cleanup()` sync method
- **Example**: `@force_shutdown(method="force_cleanup", timeout=5)`

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

### Standard Module (all mandatory DECORATORS - MANDATORY)
Every module must include ALL all mandatory decorators in this exact order:
```python
@inject_dependencies('app_context')
@register_service("standard.my_module.service", methods=[
    ServiceMethod(
        name="initialize",
        description="Initialize module service with optional settings",
        params=[ServiceParam("settings", "Dict[str, Any]", required=False)],
        returns=ServiceReturn("Result", "Result indicating initialization success"),
        examples=[ServiceExample("initialize()", "Result.success(...)")],
        tags=["phase2", "initialization"]
    ),
    ServiceMethod(
        name="get_status",
        description="Get current service status and health information",
        params=[],
        returns=ServiceReturn("Result", "Result with service status"),
        examples=[ServiceExample("get_status()", "Result.success(...)")],
        tags=["status", "monitoring"]
    )
], priority=100)
@require_services([])  # Empty list if no external services needed
@initialization_sequence("setup_infrastructure", phase="phase1")
@phase2_operations("initialize_phase2")
@auto_service_creation(service_class="MyModuleService")
@register_api_endpoints(router_name="router")
@register_database(database_name=None)  # None if no database
@enforce_data_integrity(strict_mode=True, anti_mock=True)
@module_health_check(check_function=None)
@graceful_shutdown(method="cleanup_resources", timeout=30)
@force_shutdown(method="force_cleanup", timeout=5)
class MyModule(DataIntegrityModule):
    MODULE_ID = "standard.my_module"
    MODULE_VERSION = "1.0.0"
    MODULE_DESCRIPTION = "Module description"
```

### Module with Database (all mandatory DECORATORS)
```python
@inject_dependencies('app_context')
@register_service("standard.my_db_module.service", methods=[...], priority=100)
@require_services(["core.database.service", "core.database.crud_service"])
@initialization_sequence("setup_infrastructure", phase="phase1")
@phase2_operations("initialize_phase2")
@auto_service_creation(service_class="MyDbModuleService")
@register_api_endpoints(router_name="router")
@register_database(database_name="my_db_module")  # Actual database name
@enforce_data_integrity(strict_mode=True, anti_mock=True)
@module_health_check(interval=300)
@graceful_shutdown(method="cleanup_resources", timeout=30)
@force_shutdown(method="force_cleanup", timeout=5)
class MyDbModule(DataIntegrityModule):
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

## Decorator Order (MANDATORY - all mandatory DECORATORS)

Decorators are applied bottom-to-top, so order matters. ALL modules MUST have ALL all mandatory decorators in this exact order:

1. `@inject_dependencies('app_context')` - MUST be first (closest to class)
2. `@register_service(...)` - Service definitions with methods
3. `@require_services([...])` - Service dependencies (use `[]` if none)
4. `@initialization_sequence("setup_infrastructure", phase="phase1")` - Phase 1 setup
5. `@phase2_operations("initialize_phase2")` - Phase 2 setup
6. `@auto_service_creation(service_class="...")` - Service instance creation
7. `@register_api_endpoints(router_name="router")` - API routes
8. `@register_database(database_name=...)` - Database registration (use `None` if no database)
9. `@enforce_data_integrity(strict_mode=True, anti_mock=True)` - Integrity checks
10. `@module_health_check(check_function=None)` - Health monitoring
11. `@graceful_shutdown(method="cleanup_resources", timeout=30)` - Async cleanup
12. `@force_shutdown(method="force_cleanup", timeout=5)` - Sync force cleanup

## Startup Sequence

1. **Framework Discovery** - Scans modules/
2. **Decorator Processing** - ModuleProcessor reads metadata
3. **Module Instantiation** - Creates module instance
4. **Auto Service Creation** - Creates service instance
5. **Phase 1 Methods** - Executes `@initialization_sequence(phase="phase1")` methods
6. **Service Registration** - Registers services with app_context
7. **Phase 2 Hooks** - Executes `@phase2_operations` methods
8. **Application Ready** - All modules initialized

## Mandatory-All-Decorators Enforcement

### What Happens When Decorators Are Missing?

The framework actively monitors decorator compliance and will log MODULE COMPLIANCE warnings:

```
WARNING - core.module_processor - MODULE COMPLIANCE: standard.my_module is missing decorators:
  - @require_services (empty list [] if no external services)
  - @register_database (None if no database)
  - @module_health_check (None for default behavior)
```

**Detection**: Missing decorators are detected during module processing (processing pipeline)
**Impact**: Module may fail to initialize properly or lack expected functionality
**Resolution**: Add ALL all mandatory decorators - use scaffolding tool to generate compliant modules

### Benefits of Mandatory-All-Decorators

1. **Uniform Processing**: All modules go through identical processing pipeline
2. **Complete Discovery**: Services can enumerate all module capabilities
3. **Predictable Behavior**: No special cases or conditional logic
4. **Easy Migration**: Adding features just requires changing decorator values, not adding decorators
5. **Clear Documentation**: Every module has the same structure
6. **Tooling Support**: Scaffolding tool generates 100% compliant modules automatically
7. **No Configuration Drift**: Can't accidentally forget critical decorators over time

### Scaffolding Tool Compliance

The scaffolding tool (`tools/scaffold_module.py`) automatically generates ALL all mandatory decorators:
- Creates modules with 100% decorator compliance
- Uses `None` or empty values for unused features
- Ensures 14/14 processing steps complete
- No manual decorator addition required

## Common Mistakes

### Missing Decorators (CRITICAL)
❌ **Wrong - Missing required decorators:**
```python
@inject_dependencies('app_context')
@register_service("my_module.service", methods=[...])
# Missing @require_services, @register_database, @module_health_check
class MyModule(DataIntegrityModule):
    pass
```

✅ **Correct - ALL all mandatory decorators present:**
```python
@inject_dependencies('app_context')
@register_service("my_module.service", methods=[...], priority=100)
@require_services([])  # Empty list required
@initialization_sequence("setup_infrastructure", phase="phase1")
@phase2_operations("initialize_phase2")
@auto_service_creation(service_class="MyModuleService")
@register_api_endpoints(router_name="router")
@register_database(database_name=None)  # None required
@enforce_data_integrity(strict_mode=True, anti_mock=True)
@module_health_check(check_function=None)  # None for default
@graceful_shutdown(method="cleanup_resources", timeout=30)
@force_shutdown(method="force_cleanup", timeout=5)
class MyModule(DataIntegrityModule):
    pass
```

### Incorrect Decorator Values
❌ **Wrong - Omitting None for unused features:**
```python
@register_database()  # Missing required parameter
@module_health_check()  # Missing required parameter
```

✅ **Correct - Explicit None for unused features:**
```python
@register_database(database_name=None)  # Explicitly no database
@module_health_check(check_function=None)  # Default health check
```

### Using Scaffolding Tool (RECOMMENDED)
✅ **Best Practice - Let the tool generate compliant modules:**
```bash
python tools/scaffold_module.py --name my_module --type standard --features api,settings
```
This automatically generates:
- ALL all mandatory decorators with correct values
- Proper decorator ordering
- Complete implementation patterns
- 100% framework compliance

## References

- Decorator definitions: `core/decorators.py`
- Processing logic: `core/module_processor.py`
- Module manager: `core/module_manager.py`
- Example modules: `modules/core/database/`, `modules/core/framework/`

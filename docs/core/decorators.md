# Decorator Patterns

The framework uses a **mandatory-all-decorators architecture** where ALL modules must include ALL mandatory decorators. This provides clean, declarative module registration with consistent processing across all modules.

## CRITICAL: Mandatory-All-Decorators Architecture

**Every module MUST have ALL 11 mandatory decorators in the specified order:**
1. `@inject_dependencies('app_context')`
2. `@register_service(...)`
3. `@require_services([...])`
4. `@initialization_sequence("setup_infrastructure", phase="phase1")`
5. `@phase2_operations("initialize_phase2")`
6. `@auto_service_creation(service_class="...")`
7. `@register_api_endpoints(router_name="router")`
8. `@register_database(database_name=...)`
9. `@module_health_check(check_function=None)`
10. `@graceful_shutdown(method="cleanup_resources", timeout=30)`
11. `@force_shutdown(method="force_cleanup", timeout=5)`

**Use `None` or empty values for unused features** - e.g., `@register_database(database_name=None)` if the module doesn't use a database.

## The 11 Mandatory Decorators

### 1. @inject_dependencies
**Required:** MANDATORY - All modules need app_context

Automatically injects dependencies into module constructor.

```python
@inject_dependencies('app_context')
class MyModule(DataIntegrityModule):
    def __init__(self):
        super().__init__()
        # self.app_context is automatically injected
```

**Parameters:**
- `*dependency_names` (str): Dependencies to inject (always use `'app_context'`)

### 2. @register_service
**Required:** MANDATORY - All modules must define service interface

Registers service with full method documentation for discovery.

```python
@register_service("standard.my_module.service", methods=[
    ServiceMethod(
        name="initialize",
        description="Initialize module service",
        params=[],
        returns=ServiceReturn("bool", "Initialization success"),
        examples=[ServiceExample("initialize()", "True")],
        tags=["initialization"]
    )
], priority=100)
```

**Parameters:**
- `service_name` (str): Unique service identifier
- `methods` (List[ServiceMethod]): Full service interface documentation
- `priority` (int): Service priority (default: 100)

### 3. @require_services
**Required:** MANDATORY - Use empty list `[]` if no external services needed

Declares required services from other modules.

```python
@require_services(["core.database.service"])  # With dependencies
# or
@require_services([])  # No dependencies
```

**Parameters:**
- `service_names` (List[str]): Required service names (empty list if none)

### 4. @initialization_sequence
**Required:** MANDATORY - ALL modules MUST register Pydantic settings

Defines Phase 1 initialization for settings registration.

```python
@initialization_sequence("setup_infrastructure", phase="phase1")
class MyModule(DataIntegrityModule):
    def setup_infrastructure(self):
        from .settings import MyModuleSettings
        self.app_context.register_pydantic_model(self.MODULE_ID, MyModuleSettings)
```

**Parameters:**
- `*method_names` (str): Method names to call (use `"setup_infrastructure"`)
- `phase` (str): Initialization phase (use `"phase1"`)

### 5. @phase2_operations
**Required:** MANDATORY - All modules use this for service initialization

Defines Phase 2 complex initialization methods.

```python
@phase2_operations("initialize_phase2")
class MyModule(DataIntegrityModule):
    async def initialize_phase2(self):
        # Complex initialization with service access
        pass
```

**Parameters:**
- `*method_names` (str): Method names to call (use `"initialize_phase2"`)
- `priority` (int): Initialization order (default: 100)

### 6. @auto_service_creation
**Required:** MANDATORY - All modules must have service instance

Automatically creates service instance with injected dependencies.

```python
@auto_service_creation(service_class="MyModuleService")
class MyModule(DataIntegrityModule):
    def __init__(self):
        super().__init__()
        self.service_instance = None  # Auto-created by decorator
```

**Parameters:**
- `service_class` (str): Service class name from services.py

### 7. @register_api_endpoints
**Required:** MANDATORY - Use `router_name="router"` even if router is empty

Registers FastAPI routes automatically.

```python
@register_api_endpoints(router_name="router")
class MyModule(DataIntegrityModule):
    pass

# In api.py, define router
router = APIRouter(prefix="/my_module", tags=["my_module"])
```

**Parameters:**
- `router_name` (str): Router attribute name (always use `"router"`)

### 8. @register_database
**Required:** MANDATORY - Use `database_name=None` if no database needed

Registers database requirements.

```python
@register_database(database_name="my_module")  # With database
# or
@register_database(database_name=None)  # No database
```

**Parameters:**
- `database_name` (str): Database name or None

### 9. @module_health_check
**Required:** MANDATORY - Use `check_function=None` or custom function

Registers periodic health check.

```python
@module_health_check(check_function=None)  # Default
# or
@module_health_check(interval=300)  # Custom interval
```

**Parameters:**
- `check_function` (Callable): Custom health check or None
- `interval` (int): Check interval in seconds (default: 300)

### 10. @graceful_shutdown
**Required:** MANDATORY - All modules must define cleanup

Registers async cleanup method.

```python
@graceful_shutdown(method="cleanup_resources", timeout=30)
class MyModule(DataIntegrityModule):
    async def cleanup_resources(self):
        # Async cleanup
        pass
```

**Parameters:**
- `method` (str): Cleanup method name (use `"cleanup_resources"`)
- `timeout` (int): Timeout in seconds (default: 30)

### 11. @force_shutdown
**Required:** MANDATORY - All modules must define emergency cleanup

Registers sync force cleanup.

```python
@force_shutdown(method="force_cleanup", timeout=5)
class MyModule(DataIntegrityModule):
    def force_cleanup(self):
        # Sync emergency cleanup
        pass
```

**Parameters:**
- `method` (str): Force cleanup method name (use `"force_cleanup"`)
- `timeout` (int): Timeout in seconds (default: 5)

## Module Constants

Every module must define these constants:

```python
class MyModule(DataIntegrityModule):
    # Required module metadata
    MODULE_ID = "standard.my_module"        # Unique module identifier
    MODULE_VERSION = "1.0.0"               # Semantic version
    MODULE_DESCRIPTION = "Module purpose"   # Brief description
```

**MODULE_ID Format:**
- `standard.module_name` - Application modules
- `core.module_name` - Framework modules
- `extensions.module_name` - Extension modules

## Complete Module Example (ALL 11 DECORATORS)

```python
# modules/standard/my_module/api.py
from fastapi import APIRouter, Request, HTTPException
from core.decorators import (
    inject_dependencies,
    register_service,
    ServiceMethod,
    ServiceParam,
    ServiceReturn,
    ServiceExample,
    require_services,
    auto_service_creation,
    phase2_operations,
    initialization_sequence,
    register_api_endpoints,
    register_database,
    module_health_check,
    graceful_shutdown,
    force_shutdown
)
from core.module_base import DataIntegrityModule
from core.logging import get_framework_logger

logger = get_framework_logger("standard.my_module")

# MANDATORY: ALL 11 DECORATORS IN CORRECT ORDER
@inject_dependencies('app_context')
@register_service("standard.my_module.service", methods=[
    ServiceMethod(
        name="initialize",
        description="Initialize module service",
        params=[],
        returns=ServiceReturn("bool", "Initialization success"),
        examples=[ServiceExample("initialize()", "True")],
        tags=["initialization"]
    ),
    ServiceMethod(
        name="get_status",
        description="Get service status",
        params=[],
        returns=ServiceReturn("Result", "Status information"),
        examples=[ServiceExample("get_status()", "Result.success(...)")],
        tags=["status"]
    )
], priority=100)
@require_services([])  # Empty list if no external services
@initialization_sequence("setup_infrastructure", phase="phase1")
@phase2_operations("initialize_phase2")
@auto_service_creation(service_class="MyModuleService")
@register_api_endpoints(router_name="router")
@register_database(database_name=None)  # None if no database
@module_health_check(check_function=None)
@graceful_shutdown(method="cleanup_resources", timeout=30)
@force_shutdown(method="force_cleanup", timeout=5)
class MyModuleModule(DataIntegrityModule):
    MODULE_ID = "standard.my_module"
    MODULE_VERSION = "1.0.0"
    MODULE_DESCRIPTION = "My application module"

    def __init__(self):
        super().__init__()
        self.service_instance = None
        # app_context injected by @inject_dependencies

    def setup_infrastructure(self):
        """Phase 1: Register Pydantic settings (MANDATORY)"""
        try:
            from .settings import MyModuleSettings
            self.app_context.register_pydantic_model(self.MODULE_ID, MyModuleSettings)
            logger.info(f"{self.MODULE_ID}: Settings registered")
        except Exception as e:
            logger.warning(f"{self.MODULE_ID}: Settings error: {e}")

    async def initialize_phase2(self):
        """Phase 2: Complex initialization with service access"""
        if self.service_instance:
            return await self.service_instance.initialize()
        return False

    async def cleanup_resources(self):
        """Graceful shutdown cleanup"""
        if self.service_instance:
            await self.service_instance.cleanup_resources()

    def force_cleanup(self):
        """Emergency shutdown cleanup"""
        if self.service_instance:
            self.service_instance.force_cleanup()

# FastAPI Routes
router = APIRouter(prefix="/my_module", tags=["my_module"])

@router.get("/status")
async def get_status(request: Request):
    """Get module status"""
    service = request.app.state.app_context.get_service("standard.my_module.service")
    if not service:
        raise HTTPException(status_code=503, detail="Service unavailable")
    result = await service.get_status()
    return result.data if result.success else {"error": result.message}

@router.get("/info")
async def get_info():
    """Get module information"""
    return {
        "name": "my_module",
        "version": "1.0.0",
        "status": "active"
    }
```

## Two-Phase Initialization

Modules automatically participate in two-phase initialization:

### Phase 1: setup_infrastructure()
- **Infrastructure only** - No service dependencies
- Create directories, configure logging
- Register settings schemas
- Prepare for service registration

```python
def setup_infrastructure(self):
    """Phase 1 - Infrastructure setup."""
    self.logger.info("Setting up module infrastructure")
    
    # OK: Basic setup
    os.makedirs("data/my_module", exist_ok=True)
    
    # NOT OK: Accessing other services (they don't exist yet)
    # settings = self.app_context.get_service("core.settings")  # Will fail!
```

### Phase 2: initialize_phase2()
- **Full framework access** - All services available
- Database operations, external connections
- Complex initialization logic

```python
@require_services(["core.settings.service", "core.database.service"])
async def initialize_phase2(self):
    """Phase 2 - Complex initialization."""
    # OK: Access other services via @require_services pattern
    settings_service = self.get_required_service("core.settings.service")
    database_service = self.get_required_service("core.database.service")

    # OK: Database operations
    await self.create_database_tables()

    # OK: External connections
    await self.connect_to_external_api()
```

## Service Access Patterns

### In API Endpoints
Use FastAPI's dependency injection:

```python
@self.router.get("/data")
async def get_data(request: Request):
    service = request.app.state.app_context.get_service("my_module.service")
    result = await service.get_data()
    return result.data
```

### In Other Services
Access via app_context:

```python
async def some_method(self):
    other_service = self.app_context.get_service("other_module.service")
    result = await other_service.do_something()
    return result
```

## Settings Integration

Register Pydantic settings in your module:

```python
# settings.py
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings

class MyModuleSettings(BaseModel):
    timeout_seconds: int = Field(default=30)
    max_connections: int = Field(default=10)

# api.py
def register_settings(self):
    """Register Pydantic settings schema."""
    self.app_context.register_pydantic_model(self.MODULE_ID, MyModuleSettings)

async def get_module_settings(self):
    """Access typed settings in Phase 2."""
    settings_service = self.app_context.get_service("core.settings.service")
    return await settings_service.get_typed_settings(self.MODULE_ID, MyModuleSettings)
```

## Database Integration

Use the database system in your service:

```python
# services.py
from core.error_utils import Result

class UserService:
    def __init__(self, app_context):
        self.app_context = app_context
    
    async def create_user(self, name: str, email: str) -> Result:
        try:
            async with self.app_context.database.integrity_session("user_manager", "create_user") as session:
                user = User(name=name, email=email)
                session.add(user)
                await session.commit()
                
                return Result.success(data={"id": user.id, "name": user.name})
                
        except Exception as e:
            return Result.error(
                code="USER_CREATION_FAILED",
                message="Failed to create user",
                details={"error": str(e)}
            )
```

## Using the Scaffolding Tool (RECOMMENDED)

The easiest way to create modules with all 12 decorators is using the scaffolding tool:

```bash
python tools/scaffold_module.py --name my_module --type standard --features api,settings
```

This automatically generates:
- ALL mandatory decorators in correct order
- Proper decorator values and parameters
- Complete implementation patterns
- settings.py, services.py, api.py files
- 100% framework compliance

**NEVER manually create modules from scratch** - always use the scaffolding tool to ensure compliance.

## Mandatory-All-Decorators Compliance

### MODULE COMPLIANCE Warnings

The framework actively monitors decorator compliance during module processing:

```
WARNING - core.module_processor - MODULE COMPLIANCE: standard.my_module is missing decorators:
  - @require_services (empty list [] if no external services)
  - @register_database (None if no database)
  - @module_health_check (None for default behavior)
```

**Detection:** Missing decorators are detected during module processing
**Impact:** Module may fail to initialize or lack expected functionality
**Resolution:** Add ALL mandatory decorators using the scaffolding tool

### Best Practices

1. **Always Use Scaffolding Tool** - Generate 100% compliant modules automatically
2. **Never Skip Decorators** - All mandatory decorators are required, use None/empty values for unused features
3. **Follow Exact Order** - Decorators must be in the specified order
4. **Phase 1 Required** - ALL modules must register Pydantic settings
5. **Cleanup Methods Required** - Implement both async and sync cleanup

### Module Organization
- **One module per feature** - Keep modules focused
- **Clear naming** - Use descriptive MODULE_ID values
- **Consistent structure** - Follow scaffolding tool output

### Initialization Phases
- **Phase 1: setup_infrastructure()** - Settings registration ONLY, no service access
- **Phase 2: initialize_phase2()** - Complex initialization with full service access
- **Use async methods** - For Phase 2, database, and external operations

### Service Design
- **Return Result objects** - Consistent error handling pattern
- **Use typed settings** - Pydantic v2 validation
- **Database via integrity_session** - Automatic lifecycle management
- **Implement cleanup methods** - Both `cleanup_resources()` and `force_cleanup()`

## Troubleshooting

### Missing Decorators Warning
```
WARNING - MODULE COMPLIANCE: standard.my_module is missing decorators
```

**Solution:** Use the scaffolding tool to generate compliant modules:
```bash
python tools/scaffold_module.py --name my_module --type standard
```

### Service Not Found
```python
# Error: Service 'my_module.service' not found
service = app_context.get_service("my_module.service")
```

**Causes:**
- Missing or incorrect `@register_service` decorator
- Typo in service name
- Module failed to load (check error logs)

### Module Not Loading
```python
# Error: Module 'standard.my_module' failed to initialize
```

**Causes:**
- Missing required decorators (check MODULE COMPLIANCE warnings)
- Syntax error in decorator parameters
- Missing `setup_infrastructure()` method
- Missing `initialize_phase2()` method

### Phase 1 Service Access Error
```python
# Error: Service not available in setup_infrastructure
def setup_infrastructure(self):
    service = self.app_context.get_service("other.service")  # WRONG!
```

**Solution:** NEVER access services in Phase 1. Move service access to `initialize_phase2()`.

The mandatory-all-decorators architecture ensures consistent module processing while providing clean, declarative registration patterns.
# Decorator Patterns

The framework uses decorators to provide clean, declarative module registration. This document covers all decorator patterns and their usage.

## Core Decorators

### @register_service

Registers a service with the framework's service discovery system.

```python
from core.decorators import register_service
from core.module_base import DataIntegrityModule

@register_service("my_module.service")
class MyModule(DataIntegrityModule):
    MODULE_ID = "standard.my_module"
    MODULE_VERSION = "1.0.0" 
    MODULE_DESCRIPTION = "My application module"
```

**Parameters:**
- `service_name` (str): Unique service identifier in format `module_name.service`

**Behavior:**
- Registers the class as a service during framework initialization
- Makes the service available via `app_context.get_service(service_name)`
- Enables dependency injection in other modules

### @register_api_endpoints

Registers FastAPI router endpoints for automatic discovery.

```python
from fastapi import APIRouter
from core.decorators import register_api_endpoints

@register_service("my_module.service")
@register_api_endpoints("router")
class MyModule(DataIntegrityModule):
    def __init__(self):
        # Router automatically gets standard path: /api/v1/standard/my_module
        self.router = APIRouter(tags=["my-module"])
        
        @self.router.get("/status")
        async def get_status():
            return {"status": "active"}
```

**Parameters:**
- `router_name` (str): Name of the router attribute (default: "router")

**Behavior:**
- Automatically generates API path based on module ID
- Standard path pattern: `/api/v1/{module_type}/{module_name}`
- Integrates with FastAPI's automatic documentation
- No manual route registration needed

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

## Complete Module Example

```python
# modules/standard/user_manager/api.py
from fastapi import APIRouter, Request, HTTPException
from core.decorators import register_service, register_api_endpoints  
from core.module_base import DataIntegrityModule
from .services import UserService
from .api_schemas import CreateUserRequest, UserResponse

@register_service("user_manager.service")
@register_api_endpoints("router")
class UserManagerModule(DataIntegrityModule):
    MODULE_ID = "standard.user_manager"
    MODULE_VERSION = "1.0.0"
    MODULE_DESCRIPTION = "User management and authentication"
    
    def __init__(self):
        super().__init__()
        self.router = APIRouter(tags=["user-management"])
        self.setup_routes()
    
    def setup_routes(self):
        @self.router.post("/users", response_model=UserResponse)
        async def create_user(request: CreateUserRequest, http_request: Request):
            service = http_request.app.state.app_context.get_service("user_manager.service")
            result = await service.create_user(request.name, request.email)
            
            if not result.success:
                raise HTTPException(status_code=400, detail=result.message)
                
            return UserResponse(id=result.data["id"], name=result.data["name"])
    
    def setup_infrastructure(self):
        """Phase 1: Infrastructure setup only."""
        self.logger.info(f"{self.MODULE_ID}: Setting up infrastructure")
        # Create directories, configure logging, etc.
    
    async def initialize_service(self):
        """Phase 2: Complex initialization with service access."""
        # Access other services, setup database, etc.
        settings_service = self.app_context.get_service("core.settings.service")
        await self.setup_database_tables()
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

### Phase 2: initialize_service()
- **Full framework access** - All services available
- Database operations, external connections
- Complex initialization logic

```python
async def initialize_service(self):
    """Phase 2 - Complex initialization."""
    # OK: Access other services
    settings_service = self.app_context.get_service("core.settings.service")
    database_service = self.app_context.get_service("core.database.service")
    
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

## Common Patterns

### Service with Database
```python
@register_service("data_manager.service")
class DataManagerModule(DataIntegrityModule):
    MODULE_ID = "standard.data_manager"
    
    async def initialize_service(self):
        # Set up database tables
        async with self.app_context.database.integrity_session("data_manager", "setup") as session:
            # Create tables, initial data, etc.
            pass
```

### API-Only Module
```python
@register_api_endpoints("router")  # No @register_service needed
class ApiOnlyModule(DataIntegrityModule):
    MODULE_ID = "standard.api_only"
    
    def __init__(self):
        self.router = APIRouter(tags=["api-only"])
        
        @self.router.get("/health")
        async def health_check():
            return {"status": "healthy"}
```

### Service-Only Module (No API)
```python
@register_service("background_processor.service")  # No @register_api_endpoints
class BackgroundProcessorModule(DataIntegrityModule):
    MODULE_ID = "standard.background_processor"
    
    async def initialize_service(self):
        # Start background tasks, connect to queues, etc.
        pass
```

## Error Handling in Decorators

The framework handles decorator errors gracefully:

```python
# If decorator fails, module loading continues but errors are logged
@register_service("invalid.service.name")  # Bad service name format
class BadModule(DataIntegrityModule):
    pass  # Framework will log error and skip this registration
```

## Best Practices

### Module Organization
- **One module per feature** - Keep modules focused
- **Clear naming** - Use descriptive MODULE_ID values
- **Consistent structure** - Follow the standard file layout

### Decorator Usage
- **Apply decorators to the module class** - Not individual methods
- **Use standard service names** - `module_name.service` format
- **Keep router names simple** - Usually just "router"

### Initialization
- **Phase 1: Infrastructure only** - No service dependencies
- **Phase 2: Everything else** - Database, services, external connections
- **Use async methods** - For database and external operations

### Service Design  
- **Return Result objects** - Consistent error handling
- **Use typed settings** - Pydantic validation and environment overrides
- **Database operations via integrity_session** - Automatic lifecycle management

## Troubleshooting

### Service Not Found
```python
# Error: Service 'my_module.service' not found
service = app_context.get_service("my_module.service")
```

**Causes:**
- Missing `@register_service` decorator
- Typo in service name
- Module not loaded (check logs)

### API Endpoints Not Working
```python
# Error: 404 Not Found for /api/v1/standard/my_module/status
```

**Causes:**
- Missing `@register_api_endpoints` decorator
- Router not defined in `__init__`
- Wrong router attribute name in decorator

### Phase 1 Service Access Error
```python
# Error: Service not available in setup_infrastructure
def setup_infrastructure(self):
    service = self.app_context.get_service("other.service")  # Fails!
```

**Solution:** Move service access to `initialize_service()` (Phase 2)

The decorator system provides clean, declarative module registration while handling the complex framework integration automatically.
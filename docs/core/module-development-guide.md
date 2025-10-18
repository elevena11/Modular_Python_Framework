# Module Development Guide

This guide covers everything you need to know about creating modules for the Modular Python Framework.

## Quick Start

The fastest way to create a new module is using the scaffolding tool:

```bash
python tools/scaffold_module.py --name my_module --type standard --features database,api,settings
```

This creates a complete module structure with all necessary files.

## Module Structure

Every module follows this standard structure:

```
modules/standard/my_module/
├── api.py                 # Module entry point and API routes
├── services.py            # Business logic and service class
├── settings.py            # Pydantic configuration model
├── database.py           # Database operations (optional)
├── db_models.py          # SQLAlchemy models (optional)
└── api_schemas.py        # Request/response models (optional)
```

## Core Module Files

### 1. api.py - Module Entry Point

This is the main file that defines your module with **all mandatory MANDATORY DECORATORS**:

```python
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
    enforce_data_integrity,
    module_health_check,
    graceful_shutdown,
    force_shutdown
)
from core.module_base import DataIntegrityModule
from core.logging import get_framework_logger

logger = get_framework_logger("standard.my_module")

# MANDATORY: all mandatory DECORATORS IN CORRECT ORDER
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
class MyModuleModule(DataIntegrityModule):
    MODULE_ID = "standard.my_module"
    MODULE_VERSION = "1.0.0"
    MODULE_DESCRIPTION = "My application module"

    def __init__(self):
        super().__init__()
        self.service_instance = None
        # app_context injected automatically by @inject_dependencies

    def setup_infrastructure(self):
        """Phase 1: Register Pydantic settings model (MANDATORY)"""
        try:
            from .settings import MyModuleSettings
            self.app_context.register_pydantic_model(self.MODULE_ID, MyModuleSettings)
            logger.info(f"{self.MODULE_ID}: Pydantic settings model registered")
        except Exception as e:
            logger.warning(f"{self.MODULE_ID}: Error registering Pydantic model: {e}")

    async def initialize_phase2(self):
        """Phase 2: Initialize with guaranteed service access"""
        # Services guaranteed available via @require_services decorator
        # Service is available as self.service_instance (created by @auto_service_creation)
        if self.service_instance:
            result = await self.service_instance.initialize()
            return result
        return False

    async def cleanup_resources(self):
        """Graceful shutdown - cleanup resources"""
        if self.service_instance and hasattr(self.service_instance, 'cleanup_resources'):
            await self.service_instance.cleanup_resources()

    def force_cleanup(self):
        """Force shutdown - emergency cleanup"""
        if self.service_instance and hasattr(self.service_instance, 'force_cleanup'):
            self.service_instance.force_cleanup()
```

**CRITICAL: all mandatory DECORATORS ARE MANDATORY**
1. `@inject_dependencies('app_context')` - Injects app_context into constructor
2. `@register_service(...)` - Registers service with full method documentation
3. `@require_services([...])` - Declares service dependencies (empty list if none)
4. `@initialization_sequence("setup_infrastructure", phase="phase1")` - Phase 1 settings registration
5. `@phase2_operations("initialize_phase2")` - Phase 2 complex initialization
6. `@auto_service_creation(service_class="...")` - Automatically creates service instance
7. `@register_api_endpoints(router_name="router")` - Registers API routes
8. `@register_database(database_name=...)` - Database registration (None if no database)
9. `@enforce_data_integrity(strict_mode=True, anti_mock=True)` - Integrity checks
10. `@module_health_check(check_function=None)` - Health monitoring
11. `@graceful_shutdown(method="cleanup_resources", timeout=30)` - Async cleanup
12. `@force_shutdown(method="force_cleanup", timeout=5)` - Sync force cleanup

**Framework Standards:**
- **Mandatory-All-Decorators**: Every module must have all all mandatory decorators
- **Phase 1 Required**: Must implement `setup_infrastructure()` for settings registration
- **Service Methods**: Define comprehensive service interface with ServiceMethod
- **Cleanup Methods**: Must implement both `cleanup_resources()` and `force_cleanup()`
- **Use Scaffolding Tool**: Generate compliant modules automatically

### 2. services.py - Business Logic

Contains your module's main service class with proper lifecycle methods:

```python
from core.error_utils import Result, error_message
from core.logging import get_framework_logger
from typing import Dict, Any

MODULE_ID = "standard.my_module"
logger = get_framework_logger(MODULE_ID)

class MyModuleService:
    """Main service for the my_module module."""

    def __init__(self, app_context=None):
        """Initialize with dependency injection."""
        self.app_context = app_context
        self.initialized = False
        self.logger = logger

        logger.info(f"{MODULE_ID} service created")

    async def initialize(self) -> bool:
        """Phase 2 initialization - set up with provided services"""
        if self.initialized:
            return True

        logger.info(f"Initializing {MODULE_ID} service")

        try:
            # Your initialization logic here
            # Example: Load settings, setup connections, etc.

            self.initialized = True
            logger.info(f"{MODULE_ID} service initialized")
            return True

        except Exception as e:
            logger.error(error_message(
                module_id=MODULE_ID,
                error_type="INIT_ERROR",
                details=f"Error during initialization: {str(e)}",
                location="initialize()"
            ))
            return False

    async def get_status(self) -> Result:
        """Get current service status"""
        return Result.success(data={
            "status": "active" if self.initialized else "not_initialized",
            "module": "my_module"
        })

    async def cleanup_resources(self):
        """Graceful shutdown - cleanup resources"""
        # Close connections, cancel tasks, save state
        logger.info(f"{MODULE_ID}: Graceful cleanup")
        self.initialized = False

    def force_cleanup(self):
        """Force shutdown - emergency cleanup (synchronous)"""
        # Ignore errors during force cleanup
        try:
            logger.info(f"{MODULE_ID}: Force cleanup")
            self.initialized = False
        except Exception:
            pass  # Ignore errors during emergency shutdown
```

### 3. settings.py - Configuration

Use Pydantic for type-safe configuration:

```python
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings
from typing import Optional

class MyModuleSettings(BaseSettings):
    model_config = {
        "env_prefix": "MY_MODULE_",
        "use_enum_values": True,
        "validate_assignment": True,
        "extra": "forbid"
    }
    
    enabled: bool = Field(default=True, description="Enable MyModule")
    max_connections: int = Field(default=10, description="Maximum connections")
    api_timeout: int = Field(default=30, description="API timeout in seconds")
    debug_mode: bool = Field(default=False, description="Enable debug logging")
```

**Environment variable override:**
- Setting `enabled` can be overridden with `MY_MODULE_ENABLED=false`
- Setting `max_connections` can be overridden with `MY_MODULE_MAX_CONNECTIONS=20`

## Adding Database Support

### 1. Database Models (db_models.py)

```python
from sqlalchemy import Column, Integer, String, DateTime, Boolean
from core.database import get_database_base
from datetime import datetime

# Required: Define database name for auto-discovery
DATABASE_NAME = "my_module"

# Create base class for this module's models
MyModuleBase = get_database_base(DATABASE_NAME)

class MyRecord(MyModuleBase):
    __tablename__ = "my_records"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    active = Column(Boolean, default=True)
```

### 2. Database Operations (database.py)

```python
from core.app_context import app_context
from core.error_utils import Result
from .db_models import MyRecord

class MyModuleDatabase:
    def __init__(self):
        self.database_name = "my_module"
    
    async def create_record(self, name: str) -> Result:
        """Create a new record"""
        try:
            async with app_context.database.integrity_session(
                self.database_name, "create_record"
            ) as session:
                record = MyRecord(name=name)
                session.add(record)
                await session.commit()
                
                return Result.success(data={"id": record.id, "name": record.name})
                
        except Exception as e:
            return Result.error(
                code="CREATE_FAILED",
                message="Failed to create record",
                details={"error": str(e)}
            )
    
    async def get_all_records(self) -> Result:
        """Get all records"""
        try:
            async with app_context.database.integrity_session(
                self.database_name, "get_all_records"
            ) as session:
                records = await session.execute(
                    select(MyRecord).where(MyRecord.active == True)
                )
                results = [
                    {"id": r.id, "name": r.name, "created_at": r.created_at.isoformat()}
                    for r in records.scalars()
                ]
                
                return Result.success(data=results)
                
        except Exception as e:
            return Result.error(
                code="FETCH_FAILED", 
                message="Failed to fetch records",
                details={"error": str(e)}
            )
```

## Adding API Endpoints

Add FastAPI routes to api.py:

```python
from fastapi import APIRouter, HTTPException
from .api_schemas import CreateRecordRequest, RecordResponse

# Create router - this gets auto-registered by @register_api_endpoints
router = APIRouter()

@router.get("/status")
async def get_status():
    """Get module status"""
    service = app_context.get_service("standard.my_module.service")
    result = await service.get_status()
    
    if result.success:
        return result.data
    else:
        raise HTTPException(status_code=500, detail=result.message)

@router.post("/records", response_model=RecordResponse)
async def create_record(request: CreateRecordRequest):
    """Create a new record"""
    service = app_context.get_service("standard.my_module.service")
    result = await service.create_record(request.name)
    
    if result.success:
        return RecordResponse(**result.data)
    else:
        raise HTTPException(status_code=400, detail=result.message)
```

### API Schemas (api_schemas.py)

```python
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class CreateRecordRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Record name")

class RecordResponse(BaseModel):
    id: int = Field(..., description="Record ID")
    name: str = Field(..., description="Record name")
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")
    active: bool = Field(True, description="Whether record is active")

class StatusResponse(BaseModel):
    status: str = Field(..., description="Module status")
    module: str = Field(..., description="Module name")
```

## Module Lifecycle

### Phase 1: Registration
- Module class is instantiated
- Dependencies are injected by `@inject_dependencies`
- Services are registered with framework
- Infrastructure is set up

### Phase 2: Initialization
- `@phase2_operations` methods are called
- Access to other services is available
- Complex initialization can be performed
- Database connections, external APIs, etc.

## Best Practices

### 1. Error Handling
Always use the Result pattern:

```python
async def risky_operation(self) -> Result:
    try:
        # Your logic here
        return Result.success(data=result)
    except SpecificException as e:
        return Result.error(
            code="SPECIFIC_ERROR",
            message="User-friendly message", 
            details={"error": str(e), "context": "additional_info"}
        )
```

### 2. Logging
Use the framework logger:

```python
self.logger = self.app_context.get_logger("standard.my_module")
self.logger.info("Operation completed successfully")
self.logger.error("Operation failed", extra={"context": additional_data})
```

### 3. Database Sessions
Always use integrity_session pattern:

```python
async with app_context.database.integrity_session("my_module", "operation_name") as session:
    # Database operations here
    await session.commit()
```

### 4. Settings Access
Access your module settings through the settings service:

```python
settings_service = self.app_context.get_service("core.settings.service")
result = await settings_service.get_typed_settings("standard.my_module", MyModuleSettings)
if result.success:
    settings = result.data
    if settings.enabled:
        # Module is enabled
        pass
```

## Testing Your Module

### 1. Compliance Check
Validate your module follows framework patterns:

```bash
python tools/compliance/compliance.py validate --module standard.my_module
```

### 2. Manual Testing
Start the framework and test your endpoints:

```bash
python app.py

# Test API endpoints
curl http://localhost:8000/api/v1/my_module/status
curl -X POST http://localhost:8000/api/v1/my_module/records \
  -H "Content-Type: application/json" \
  -d '{"name": "test record"}'
```

### 3. Check Logs
Monitor logs for your module:

```bash
tail -f data/logs/app.log | grep "standard.my_module"
```

## Advanced Features

### Custom Dependencies
Require other modules or services:

```python
@requires_modules([
    {"modules": ["standard.other_module"], "optional": False}
])
@phase2_operations(
    methods=["initialize_service"],
    dependencies=["standard.other_module.service"]
)
```

### Health Checks
Add monitoring:

```python
@module_health_check(interval=300, function="check_health")
class MyModuleAPI(DataIntegrityModule):
    async def check_health(self) -> bool:
        """Health check - return True if healthy"""
        # Check database, external APIs, etc.
        return True
```

### Graceful Shutdown
Handle cleanup:

```python
@graceful_shutdown(method="cleanup", timeout=30)
class MyModuleAPI(DataIntegrityModule):
    async def cleanup(self):
        """Clean up resources during shutdown"""
        # Close connections, save state, etc.
        pass
```

## Common Patterns

### 1. External API Integration
```python
import aiohttp

class ExternalAPIService:
    def __init__(self, app_context):
        self.app_context = app_context
        self.session = None
    
    async def initialize(self):
        """Create HTTP session"""
        self.session = aiohttp.ClientSession()
        return Result.success()
    
    async def cleanup(self):
        """Close HTTP session"""
        if self.session:
            await self.session.close()
```

### 2. Background Tasks
```python
import asyncio

class BackgroundWorkerService:
    def __init__(self, app_context):
        self.app_context = app_context
        self.task = None
        self.running = False
    
    async def start_background_task(self):
        """Start background processing"""
        self.running = True
        self.task = asyncio.create_task(self._worker())
        return Result.success()
    
    async def _worker(self):
        """Background worker loop"""
        while self.running:
            # Do background work
            await asyncio.sleep(60)  # Run every minute
    
    async def stop_background_task(self):
        """Stop background processing"""
        self.running = False
        if self.task:
            await self.task
```

### 3. Caching
```python
from functools import lru_cache
import time

class CacheService:
    def __init__(self, app_context):
        self.app_context = app_context
        self.cache = {}
    
    async def get_cached_data(self, key: str, ttl_seconds: int = 300) -> Result:
        """Get data with TTL cache"""
        if key in self.cache:
            data, timestamp = self.cache[key]
            if time.time() - timestamp < ttl_seconds:
                return Result.success(data=data)
        
        # Cache miss - fetch fresh data
        fresh_data = await self._fetch_fresh_data(key)
        if fresh_data.success:
            self.cache[key] = (fresh_data.data, time.time())
        
        return fresh_data
```

## Module Distribution

When your module is ready for distribution:

### 1. Create requirements.txt
If your module has specific dependencies:

```
modules/standard/my_module/requirements.txt
```

### 2. Add Documentation
Create module-specific README:

```
modules/standard/my_module/README.md
```

### 3. Export Module
The framework will automatically include your module in releases if it's in the `modules/standard/` directory.

## Troubleshooting

### Common Issues

**Module not loading:**
- Check `MODULE_ID` matches directory structure
- Ensure all required decorators are present
- Check for Python syntax errors

**Service not registered:**
- Verify `@register_service` decorator
- Check service class name in `@auto_service_creation`
- Ensure Phase 1 completes successfully

**Database errors:**
- Verify `DATABASE_NAME` constant exists
- Check database models inherit from correct base
- Use `integrity_session` pattern consistently

**API endpoints not working:**
- Ensure `router` variable exists in api.py
- Check `@register_api_endpoints` decorator
- Verify FastAPI route decorations

### Debug Mode
Enable detailed logging:

```python
# In your settings.py
debug_mode: bool = Field(default=True)

# In your service
if self.settings.debug_mode:
    self.logger.setLevel(logging.DEBUG)
```

## Summary

This guide covers the essential patterns for module development in the Modular Python Framework. Key points:

- Use the scaffolding tool for quick setup
- Follow the decorator-based patterns consistently  
- Always use the Result pattern for error handling
- Use integrity_session for database operations
- Implement proper Phase 1/Phase 2 lifecycle
- Add comprehensive logging and error handling

For more examples, examine the existing modules in `modules/core/` and use the compliance tools to validate your implementation.
# Decorator Quick Reference - Working System

**Status**: Production Ready ✅  
**All examples tested and working**

## Basic Module Template

```python
from core.decorators import register_service, auto_service_creation
from core.module_base import DataIntegrityModule

@register_service("my_module.service")
@auto_service_creation(service_class="MyService")
class MyModule(DataIntegrityModule):
    MODULE_ID = "standard.my_module"
    MODULE_NAME = "My Module"
    MODULE_DESCRIPTION = "Description of my module"
    
    # Framework handles everything automatically!
    # No manual registration code needed
```

## Complete Feature Stack

```python
@register_service("complex.primary", priority=10)
@register_service("complex.secondary", priority=20)
@require_services(["core.database.service", "core.settings.service"])
@inject_dependencies("app_context")
@auto_service_creation(service_class="ComplexService")
@initialization_sequence("setup", "configure", phase="phase1")
@phase2_operations("initialize_with_dependencies", dependencies=["core.database.setup"])
@provides_api_endpoints(router_name="router", prefix="/complex")
@enforce_data_integrity(strict_mode=True, anti_mock=True)
@module_health_check(interval=60)
@graceful_shutdown(method="cleanup", timeout=30)
@force_shutdown(method="force_cleanup", timeout=5)
class ComplexModule(DataIntegrityModule):
    MODULE_ID = "standard.complex"
    
    def initialize_with_dependencies(self):
        # Services from @require_services guaranteed available
        self.database_service = self.get_required_service("core.database.service")
        self.settings_service = self.get_required_service("core.settings.service")
```

## Decorator Reference

### **Service Registration**
```python
@register_service("module.service", priority=10)
# Registers service for automatic creation and app_context registration
# Lower priority = higher importance (10 = high priority)
```

### **Automatic Service Creation**  
```python
@auto_service_creation(service_class="MyService")
# Automatically creates service_instance = MyService(app_context)
# Service class must be in module's services.py file
```

### **Multiple Services**
```python
@register_service("module.primary", priority=10)
@register_service("module.secondary", priority=20)
# Register multiple services from one module
```

### **Phase 1 Methods (Foundation Setup)**
```python
@initialization_sequence("method1", "method2", phase="phase1")
# Called during module loading, before dependencies
# Methods run in specified order
```

### **Phase 2 Methods (Complex Setup)**
```python
@phase2_operations("finalize", dependencies=["core.database.setup"], priority=10)
# Called after all modules loaded, dependencies available
# Can access other module services
```

### **Inter-Module Service Communication (NEW)**
```python
@require_services(["core.database.service", "core.settings.service"])
@phase2_operations("initialize_with_dependencies")
class MyModule(DataIntegrityModule):
    def initialize_with_dependencies(self):
        # Services guaranteed to be available here
        self.database_service = self.get_required_service("core.database.service")
        self.settings_service = self.get_required_service("core.settings.service")
        
# Key Benefits:
# - Explicit dependency declaration
# - Guaranteed service availability in phase2_operations  
# - Clean service access pattern
# - LLM-friendly readable code
```

### **Dependency Injection**
```python
@inject_dependencies("app_context")
# Framework injects app_context into module constructor
# Access via self.app_context
```

### **API Endpoints**
```python
@provides_api_endpoints(router_name="router", prefix="/my-api")
# Registers FastAPI router with specified prefix
# Router must be defined in module as 'router = APIRouter()'
```

### **Health Monitoring**
```python
@module_health_check(interval=300)
# Calls module.health_check() method every 300 seconds
# Method should return bool (True = healthy)
```

### **Shutdown Handling**
```python
@graceful_shutdown(method="cleanup", timeout=30, priority=10)
@force_shutdown(method="force_cleanup", timeout=5)
# Graceful: Normal shutdown with timeout
# Force: Emergency shutdown (sync only)
```

### **Data Integrity**
```python
@enforce_data_integrity(strict_mode=True, anti_mock=True)
# Validates against mock/fake data patterns
# Enforces production-ready patterns
```

## Method Patterns

### **Phase 1 Methods**
```python
def setup_foundation(self):
    """Called automatically by framework in Phase 1"""
    # Basic setup, no dependencies on other modules
    # self.service_instance is available (auto-created)
    
def configure_module(self):
    """Called automatically after setup_foundation"""  
    # Additional Phase 1 configuration
```

### **Phase 2 Methods**
```python
def finalize_setup(self):
    """Called automatically in Phase 2"""
    # Complex setup with dependencies available
    # All other module services accessible via app_context
    db_service = self.app_context.get_service("core.database.service")
```

### **Health Check**
```python
async def health_check(self) -> bool:
    """Called automatically by health monitoring"""
    try:
        # Check if service is working
        return self.service_instance.is_healthy()
    except:
        return False
```

### **Shutdown Methods**
```python
async def cleanup(self):
    """Graceful shutdown - called automatically"""
    if self.service_instance:
        await self.service_instance.shutdown()

def force_cleanup(self):
    """Force shutdown - called automatically (sync only)"""
    if self.service_instance:
        self.service_instance.force_close()
```

## File Structure

```
modules/standard/my_module/
├── api.py              # Module class with decorators
├── services.py         # MyService class definition
├── api_schemas.py      # Pydantic request/response models (optional)
├── module_settings.py  # Settings definitions (optional)
```

## Service Class Template

```python
# services.py
class MyService:
    def __init__(self, app_context):
        self.app_context = app_context
        self.initialized = False
    
    def initialize(self):
        """Called by module during Phase 1"""
        self.initialized = True
        return True
    
    def is_healthy(self):
        """Called by health check"""
        return self.initialized
    
    async def shutdown(self):
        """Called during graceful shutdown"""
        self.initialized = False
```

## Common Patterns

### **Database Module Pattern**
```python
@register_service("module.service", priority=10)
@auto_service_creation(service_class="DatabaseEnabledService")
@initialization_sequence("create_database", phase="phase1")
class DatabaseModule(DataIntegrityModule):
    def create_database(self):
        # Database setup in Phase 1
        pass
```

### **API Module Pattern**
```python
@register_service("module.service")
@auto_service_creation(service_class="APIService")
@provides_api_endpoints(router_name="router", prefix="/my-api")
class APIModule(DataIntegrityModule):
    pass

# Also define: router = APIRouter() in same file
```

### **API Schema Standards**
**All endpoints must have response_model for OpenAPI compliance:**

```python
# api_schemas.py
from pydantic import BaseModel, Field

class StatusResponse(BaseModel):
    """Standard status endpoint response."""
    status: str = Field(..., description="Module status")
    module: str = Field(..., description="Module name")
    
    model_config = {
        "json_schema_extra": {
            "example": {"status": "active", "module": "my_module"}
        }
    }

class InfoResponse(BaseModel):
    """Standard info endpoint response."""
    name: str = Field(..., description="Module name")
    version: str = Field(..., description="Module version")
    description: str = Field(..., description="Module description")

# api.py
from .api_schemas import StatusResponse, InfoResponse

@router.get("/status", response_model=StatusResponse)
async def get_status():
    return {"status": "active", "module": "my_module"}

@router.get("/info", response_model=InfoResponse)  
async def get_info():
    return {
        "name": "my_module",
        "version": "1.0.0", 
        "description": "My module description"
    }
```

**Benefits:**
- **Type-safe APIs** with runtime validation
- **Auto-generated OpenAPI documentation**  
- **Consistent UI integration** (all modules have `/status` endpoint)
- **Framework compliance** with established patterns

### **Complex Integration Pattern**
```python
@register_service("integration.service")
@auto_service_creation(service_class="IntegrationService")
@initialization_sequence("basic_setup", phase="phase1")
@phase2_operations("connect_services", dependencies=["core.database.setup", "core.settings.setup"])
class IntegrationModule(DataIntegrityModule):
    def basic_setup(self):
        # Phase 1: Basic module setup
        pass
        
    def connect_services(self):
        # Phase 2: Connect to other services
        db_service = self.app_context.get_service("core.database.service")
        settings_service = self.app_context.get_service("core.settings.service")
```

## Testing Your Module

```python
# Test service registration
from core.app_context import AppContext
from core.module_loader import ModuleLoader
from core.config import Config

async def test_my_module():
    config = Config()
    app_context = AppContext(config)
    app_context.initialize()
    
    module_loader = ModuleLoader(app_context)
    success, failed = await module_loader.load_modules()
    
    # Check if service is available
    my_service = app_context.get_service("my_module.service")
    print(f"Service available: {my_service is not None}")
```

## Troubleshooting

**Service Not Available**:
1. Check service class exists in `services.py`
2. Verify `@auto_service_creation(service_class="CorrectName")`
3. Ensure module loaded without errors

**Module Not Loading**:
1. Check `MODULE_ID` matches directory structure
2. Verify decorator syntax is correct
3. Check imports are available

**Phase 1/2 Methods Not Called**:
1. Verify `@initialization_sequence` or `@phase2_operations` decorators
2. Check method names match decorator parameters
3. Ensure no exceptions in method execution

---

**Document Status**: CURRENT (August 2025)  
**All examples tested**: ✅ Working in production
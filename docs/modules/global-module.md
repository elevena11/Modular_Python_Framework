# Global Module

The Global Module (`modules/core/global/`) serves as the framework's standards enforcement and global configuration hub. It maintains framework-wide standards, provides access to global settings, and ensures consistent implementation patterns across all modules.

## Overview

The Global Module is a core framework component that maintains consistency and standards across the entire framework. It provides:

- **Standards Enforcement**: Defines and enforces framework-wide standards
- **Global Configuration**: Framework-wide settings and configuration management
- **Session Information**: Access to application session data
- **Framework Utilities**: Common utilities used across modules
- **Compliance Validation**: Ensures modules follow framework standards
- **Documentation Standards**: Maintains documentation consistency

## Key Features

### 1. Standards Management
- **Module Structure**: Standardized file organization and naming conventions
- **API Schema Validation**: Consistent API request/response patterns
- **Two-Phase Initialization**: Enforcement of initialization patterns
- **Service Registration**: Standardized service naming and registration
- **Error Handling**: Consistent error patterns and responses

### 2. Framework Configuration
- **Global Settings**: Framework-wide configuration values
- **Session Management**: Application session information access
- **Environment Integration**: Global environment variable handling
- **Configuration Validation**: Ensures configuration consistency

### 3. Standards Documentation
- **Pattern Documentation**: Comprehensive documentation of framework patterns
- **Implementation Guides**: Step-by-step guides for standard implementations
- **Compliance Checking**: Automated validation of standard compliance
- **Best Practices**: Framework-wide best practices documentation

### 4. Utilities and Services
- **Global Service**: Access to framework-wide utilities
- **Session Information**: Application session data access
- **Framework Metadata**: Information about framework status and health
- **Common Utilities**: Shared utilities used across modules

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Global Module                            │
├─────────────────────────────────────────────────────────────┤
│ Standards Management                                        │
│ ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐ │
│ │ Module          │ │ API Schema      │ │ Service         │ │
│ │ Structure       │ │ Validation      │ │ Registration    │ │
│ └─────────────────┘ └─────────────────┘ └─────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│ Configuration Management                                    │
│ ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐ │
│ │ Global          │ │ Session         │ │ Framework       │ │
│ │ Settings        │ │ Information     │ │ Metadata        │ │
│ └─────────────────┘ └─────────────────┘ └─────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│ Standards Documentation                                     │
│ ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐ │
│ │ Pattern         │ │ Implementation  │ │ Compliance      │ │
│ │ Documentation   │ │ Guides          │ │ Validation      │ │
│ └─────────────────┘ └─────────────────┘ └─────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## Framework Standards

### 1. Module Structure Standard
```
modules/[type]/[module_name]/
├── api.py              # Module initialization and API routes
├── services.py         # Core business logic and services
├── manifest.json       # Module metadata and dependencies
├── module_settings.py  # Module-specific settings
├── db_models.py        # Database models (if needed)
├── readme.md           # Module documentation
└── ui/                 # UI components (if needed)
    ├── __init__.py
    ├── ui_streamlit.py
    └── services.py
```

### 2. API Schema Validation Standard
```python
# Standardized API request/response patterns
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

class StandardRequest(BaseModel):
    """Base request model for all API endpoints."""
    request_id: Optional[str] = None
    timestamp: Optional[str] = None

class StandardResponse(BaseModel):
    """Base response model for all API endpoints."""
    success: bool
    message: Optional[str] = None
    data: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None
    timestamp: str
```

### 3. Two-Phase Initialization Standard
```python
# Phase 1: Service registration
async def initialize(app_context):
    """Phase 1: Register services and hooks only."""
    # Create service
    service = ModuleService(app_context)
    
    # Register service
    app_context.register_service("module.service", service)
    
    # Register post-init hook
    app_context.register_post_init_hook(
        "module.setup",
        service.initialize,
        dependencies=["core.database.setup"]
    )

# Phase 2: Complex initialization
class ModuleService:
    async def initialize(self):
        """Phase 2: Complex initialization with dependencies."""
        # Access other services
        self.db_service = self.app_context.get_service("core.database.service")
        
        # Perform complex setup
        await self.setup_database()
        await self.start_background_tasks()
```

### 4. Service Registration Standard
```python
# Standardized service naming and registration
MODULE_ID = "core.module_name"

async def initialize(app_context):
    service = ModuleService(app_context)
    
    # Register with fully qualified name
    app_context.register_service(f"{MODULE_ID}.service", service)
    
    # Register additional services if needed
    app_context.register_service(f"{MODULE_ID}.crud_service", crud_service)
```

## Global Service

### 1. GlobalService Class
```python
class GlobalService:
    """Service for global framework concerns."""
    
    def __init__(self, app_context):
        self.app_context = app_context
        self.initialized = False
        self.config = {}
    
    async def initialize(self, app_context=None, settings=None):
        """Initialize global service."""
        if settings:
            self.config = settings
        
        self.initialized = True
        return True
    
    def get_config(self) -> Result:
        """Get global configuration."""
        if not self.initialized:
            return Result.error(
                code="SERVICE_NOT_INITIALIZED",
                message="Global service not initialized"
            )
        
        return Result.success(data=self.config)
```

### 2. Session Information Access
```python
# Access session information through global service
async def get_session_info():
    """Get current application session information."""
    global_service = app_context.get_service("core.global.service")
    
    if not global_service:
        raise HTTPException(
            status_code=503,
            detail="Global service not available"
        )
    
    # Get session info from app context
    session_info = global_service.app_context.get_session_info()
    return session_info
```

## Standards Documentation

### 1. Module Structure Documentation
The global module maintains comprehensive documentation for all framework standards:

```markdown
# Module Structure Standard

## Required Files
- **api.py**: Module initialization and API routes
- **manifest.json**: Module metadata and dependencies

## Recommended Files
- **services.py**: Core business logic
- **module_settings.py**: Module settings and validation
- **readme.md**: Module documentation

## Optional Files
- **db_models.py**: Database models
- **ui/**: UI components
- **utils.py**: Utility functions
```

### 2. API Schema Standards
```python
# API endpoint standards
@router.get("/endpoint", response_model=StandardResponse)
async def get_endpoint():
    """Standard API endpoint implementation."""
    try:
        # Process request
        data = await process_request()
        
        return StandardResponse(
            success=True,
            data=data,
            timestamp=datetime.now().isoformat()
        )
    except Exception as e:
        return StandardResponse(
            success=False,
            error={
                "code": "PROCESSING_ERROR",
                "message": str(e)
            },
            timestamp=datetime.now().isoformat()
        )
```

### 3. Compliance Validation
```python
# Standards compliance checking
def validate_module_structure(module_path):
    """Validate module follows structure standards."""
    required_files = ["api.py", "manifest.json"]
    
    for file in required_files:
        if not os.path.exists(os.path.join(module_path, file)):
            return False, f"Missing required file: {file}"
    
    return True, "Module structure is compliant"

def validate_api_schema(module_path):
    """Validate API schema follows standards."""
    # Check for proper request/response models
    # Validate endpoint naming conventions
    # Ensure error handling patterns
    pass
```

## API Endpoints

### 1. Session Information
```python
# Get application session information
GET /api/v1/global/session-info
Response: {
    "session_id": "20250716_202514_97373810",
    "session_uuid": "uuid4-string",
    "session_start_time": "2025-07-16T20:25:14.375000",
    "uptime_seconds": 1234,
    "uptime_human": "0:20:34"
}
```

### 2. Framework Status
```python
# Get framework health and status
GET /api/v1/global/framework-status
Response: {
    "status": "healthy",
    "version": "1.0.0",
    "modules_loaded": 15,
    "services_registered": 20,
    "initialization_complete": true,
    "uptime": "0:20:34"
}
```

### 3. Standards Compliance
```python
# Check module compliance with standards
GET /api/v1/global/compliance/{module_id}
Response: {
    "module_id": "standard.user_management",
    "compliant": true,
    "standards_checked": [
        "module_structure",
        "api_schema_validation",
        "service_registration",
        "two_phase_initialization"
    ],
    "violations": []
}
```

## Configuration Management

### 1. Global Settings
```python
# module_settings.py
GLOBAL_SETTINGS = {
    "framework_version": {
        "type": "str",
        "default": "1.0.0",
        "description": "Framework version"
    },
    "debug_mode": {
        "type": "bool",
        "default": False,
        "description": "Enable debug mode"
    },
    "max_concurrent_requests": {
        "type": "int",
        "default": 100,
        "description": "Maximum concurrent API requests"
    },
    "session_timeout": {
        "type": "int",
        "default": 1800,
        "description": "Session timeout in seconds"
    }
}
```

### 2. Environment Integration
```bash
# Global environment variables
CORE_GLOBAL_DEBUG_MODE=true
CORE_GLOBAL_MAX_CONCURRENT_REQUESTS=200
CORE_GLOBAL_SESSION_TIMEOUT=3600
```

## Standards Implementation

### 1. Module Standards
```python
# Standards for module implementation
class ModuleStandards:
    REQUIRED_FILES = ["api.py", "manifest.json"]
    RECOMMENDED_FILES = ["services.py", "module_settings.py", "readme.md"]
    
    MANIFEST_SCHEMA = {
        "id": {"type": "str", "required": True},
        "name": {"type": "str", "required": True},
        "version": {"type": "str", "required": True},
        "description": {"type": "str", "required": True},
        "dependencies": {"type": "list", "required": False}
    }
    
    NAMING_CONVENTIONS = {
        "module_id": r"^[a-z][a-z0-9_]*$",
        "service_name": r"^[A-Z][a-zA-Z0-9]*Service$",
        "function_name": r"^[a-z][a-z0-9_]*$"
    }
```

### 2. API Standards
```python
# Standards for API implementation
class APIStandards:
    ENDPOINT_PATTERNS = {
        "get_resource": r"^/[a-z-]+/[a-z-]+$",
        "post_resource": r"^/[a-z-]+$",
        "put_resource": r"^/[a-z-]+/[a-z-]+$",
        "delete_resource": r"^/[a-z-]+/[a-z-]+$"
    }
    
    STATUS_CODES = {
        "success": 200,
        "created": 201,
        "no_content": 204,
        "bad_request": 400,
        "unauthorized": 401,
        "forbidden": 403,
        "not_found": 404,
        "internal_error": 500
    }
    
    RESPONSE_FORMAT = {
        "success": {"type": "bool", "required": True},
        "data": {"type": "any", "required": False},
        "error": {"type": "dict", "required": False},
        "timestamp": {"type": "str", "required": True}
    }
```

## Best Practices

### 1. Standards Compliance
```python
# ✅ CORRECT: Follow module structure standards
modules/standard/user_management/
├── api.py                  # Required
├── manifest.json           # Required
├── services.py             # Recommended
├── module_settings.py      # Recommended
├── readme.md              # Recommended
└── db_models.py           # Optional

# ❌ WRONG: Non-standard structure
modules/standard/user_management/
├── main.py                # Should be api.py
├── config.py              # Should be module_settings.py
└── database.py            # Should be db_models.py
```

### 2. Service Registration
```python
# ✅ CORRECT: Follow service registration standards
MODULE_ID = "standard.user_management"

async def initialize(app_context):
    service = UserManagementService(app_context)
    app_context.register_service(f"{MODULE_ID}.service", service)

# ❌ WRONG: Non-standard service naming
async def initialize(app_context):
    service = UserManagementService(app_context)
    app_context.register_service("user_service", service)  # Missing module prefix
```

### 3. API Implementation
```python
# ✅ CORRECT: Follow API standards
from .api_schemas import UserResponse, ErrorResponse

@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(user_id: int):
    try:
        result = await user_service.get_user(user_id)
        if result.success:
            return UserResponse(
                success=True,
                data=result.data,
                timestamp=datetime.now().isoformat()
            )
        else:
            raise HTTPException(
                status_code=404,
                detail=ErrorResponse(
                    success=False,
                    error=result.error,
                    timestamp=datetime.now().isoformat()
                )
            )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                success=False,
                error={"code": "INTERNAL_ERROR", "message": str(e)},
                timestamp=datetime.now().isoformat()
            )
        )
```

## Standards Validation

### 1. Automated Compliance Checking
```python
# Compliance validation functions
def validate_module_compliance(module_path):
    """Validate module follows all standards."""
    results = {}
    
    # Check module structure
    results["module_structure"] = validate_module_structure(module_path)
    
    # Check API schema compliance
    results["api_schema"] = validate_api_schema(module_path)
    
    # Check service registration
    results["service_registration"] = validate_service_registration(module_path)
    
    # Check two-phase initialization
    results["two_phase_init"] = validate_two_phase_init(module_path)
    
    return results
```

### 2. CI/CD Integration
```yaml
# GitHub Actions workflow for standards validation
name: Standards Compliance Check
on: [push, pull_request]

jobs:
  validate-standards:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Validate Framework Standards
        run: |
          python tools/compliance/validate_standards.py
          python tools/compliance/check_module_structure.py
          python tools/compliance/validate_api_schemas.py
```

## Performance Considerations

### 1. Standards Caching
```python
# Cache standards validation results
class StandardsCache:
    def __init__(self):
        self.cache = {}
        self.cache_ttl = 300  # 5 minutes
    
    def get_validation_result(self, module_id):
        """Get cached validation result."""
        if module_id in self.cache:
            result, timestamp = self.cache[module_id]
            if time.time() - timestamp < self.cache_ttl:
                return result
        return None
    
    def set_validation_result(self, module_id, result):
        """Cache validation result."""
        self.cache[module_id] = (result, time.time())
```

### 2. Lazy Loading
```python
# Lazy load standards documentation
class StandardsLoader:
    def __init__(self):
        self._standards = {}
    
    def get_standard(self, standard_name):
        """Get standard with lazy loading."""
        if standard_name not in self._standards:
            self._standards[standard_name] = self._load_standard(standard_name)
        return self._standards[standard_name]
```

## Related Documentation

- [Two-Phase Initialization](../patterns/two-phase-initialization.md) - Initialization pattern standards
- [Result Pattern](../patterns/result-pattern.md) - Result pattern standards
- [Service Registration](../patterns/service-registration.md) - Service registration standards
- [Module Creation Guide](../module-creation-guide-v2.md) - Module development standards
- [API Design Patterns](../patterns/api-design-patterns.md) - API implementation standards

---

The Global Module serves as the foundation for framework consistency, ensuring that all modules follow established standards and patterns while providing access to global framework utilities and configuration. It plays a crucial role in maintaining code quality and consistency across the entire framework ecosystem.
# Modular Framework - Architecture Overview

**Version: v3.0.0 (Decorator Pattern)**  
**Updated: August 10, 2025**

## System Overview

The Modular Framework is a **generic Python framework** built on clean architecture principles for building complex, maintainable applications. It uses a **decorator-based pattern** for module registration and follows **two-phase initialization** for reliable startup.

## Core Architectural Principles

### 1. centralized registration
All module registration happens through **centralized decorators**:
```python
@register_service("module.service", priority=100)
@provides_api_endpoints(router_name="router", prefix="/api")
@enforce_data_integrity(strict_mode=True, anti_mock=True)
@module_health_check(interval=300)
class MyModule(DataIntegrityModule):
    MODULE_ID = "standard.my_module"
    MODULE_NAME = "My Module"
    MODULE_DEPENDENCIES = ["core.settings"]
```

**Benefits:**
- **Single source of truth** - No separate manifest.json files
- **Compile-time validation** - Decorators catch errors early
- **Centralized processing** - ModuleProcessor handles all registration
- **Automatic discovery** - Framework finds and processes modules

### 2. Two-Phase Initialization

**Phase 1: Registration**
- Modules register services, databases, API endpoints
- No complex operations or external connections
- Fast, reliable, cannot fail

**Phase 2: Setup**
- Complex initialization via post-init hooks
- External connections, database operations
- Priority-ordered execution
- Dependency-aware scheduling

### 3. Clean Separation Architecture

**Core Utilities vs. Module Services:**
```
core/
├── error_utils.py        # Pure utilities, zero dependencies
├── paths.py             # Path management utilities
└── app_context.py       # Framework core

modules/core/
├── error_handler/       # Service module (processes JSONL files)
├── settings/           # Service module (manages configuration)
└── database/           # Service module (database operations)
```

**Data Flow Pattern:**
```
Application Code → core/error_utils.py → JSONL Files → modules/core/error_handler/
```

This prevents circular dependencies by using **file-based data flow**.

## Framework Components

### Core Framework (`core/`)
- `app_context.py` - Service container and module management
- `module_loader.py` - Module discovery and loading
- `module_processor.py` - Centralized decorator processing
- `decorators.py` - Module registration decorators
- `error_utils.py` - Pure error utilities
- `paths.py` - Path management

### Core Modules (`modules/core/`)
- `database` - SQLite database management
- `settings` - Configuration management  
- `error_handler` - Error processing and analytics
- `model_manager` - AI model management
- `framework` - Framework utilities

### Standard Modules (`modules/standard/`)
- Application-specific functionality
- Business logic modules
- Optional extensions

## Module Structure

### Decorator-Based Module (Current)
```
modules/standard/my_module/
├── api.py                    # Decorator-based registration
├── services.py              # Business logic
├── module_settings.py       # Configuration schema
├── db_models.py             # Database models (optional)
├── api_schemas.py           # Pydantic models (optional)
└── readme.md                # Module documentation
```

### Key Files

**`api.py`** - Module entry point:
```python
@register_service("my_module.service", priority=100)
@provides_api_endpoints(router_name="router", prefix="/my-module")
class MyModule(DataIntegrityModule):
    MODULE_ID = "standard.my_module"
    MODULE_DEPENDENCIES = ["core.settings"]
    
    def __init__(self):
        # Phase 1: Light initialization only
        self.service = MyModuleService()
```

**`services.py`** - Business logic:
```python
from core.error_utils import Result, error_message

class MyModuleService:
    async def initialize(self, app_context):
        # Phase 2: Complex initialization
        return True
        
    async def my_operation(self) -> Result:
        try:
            # Business logic here
            return Result.success(data=result)
        except Exception as e:
            logger.error(error_message(
                "standard.my_module",
                "OPERATION_FAILED",
                f"Operation failed: {str(e)}"
            ))
            return Result.error("OPERATION_FAILED", "Operation failed")
```

## Database Architecture

### Framework Database
- **Name**: `framework.db`
- **Purpose**: Core system data (modules, settings, logs)
- **Managed by**: `core.database` module

### Module Databases  
- **Pattern**: Each module can create its own database
- **Naming**: `{module_name}.db`
- **Discovery**: Automatic via `DATABASE_NAME` constant in `db_models.py`

### Database Creation Pattern
```python
# In db_models.py
DATABASE_NAME = "my_module"  # Required for discovery
ModuleBase = get_database_base(DATABASE_NAME)

class MyTable(ModuleBase):
    __tablename__ = "my_table"
    id = Column(Integer, primary_key=True)
```

## Error Handling Architecture

### v3.0.0 Clean Separation
- **`core/error_utils.py`**: Pure utilities, no framework dependencies
- **`modules/core/error_handler/`**: Service module for error processing
- **Data flow**: Utilities write JSONL → Service processes files
- **No circular dependencies**: Clean file-based interface

### Error Patterns
```python
# Service layer
from core.error_utils import Result, error_message

return Result.error("ERROR_CODE", "Human readable message")

# API layer  
from core.error_utils import create_error_response

raise create_error_response("ERROR_CODE", "Message", status_code=400)
```

## Service Container

### Service Registration
```python
# Automatic via decorators
@register_service("my_module.service", priority=100)

# Manual registration (Phase 1)
app_context.register_service("service_name", service_instance)

# Service access (Phase 2)
service = app_context.get_service("service_name")
```

### Priority System
- **Lower numbers run first** (0, 10, 50, 100, 150)
- **Default priority**: 100
- **Core infrastructure**: 0-20
- **Application services**: 100+

## API System

### Automatic Registration
```python
@provides_api_endpoints(router_name="router", prefix="/api/v1/my-module")
class MyModule(DataIntegrityModule):
    pass
```

The framework automatically:
1. Discovers the router in the module
2. Registers it with FastAPI
3. Applies the specified prefix
4. Handles route conflicts

### Manual API Routes
```python
# In api.py
from fastapi import APIRouter
router = APIRouter()

@router.get("/endpoint")
async def my_endpoint():
    return {"status": "success"}
```

## Data Integrity

### Anti-Mock Protection
```python
@enforce_data_integrity(strict_mode=True, anti_mock=True)
```

Prevents modules from:
- Using test/mock data in production
- Bypassing data validation
- Operating without proper initialization

### Health Monitoring
```python
@module_health_check(interval=300)  # Check every 5 minutes
```

Automatic monitoring of:
- Service availability
- Database connectivity
- Resource usage
- Error rates

## Configuration Management

### Module Settings
```python
# In module_settings.py
from pydantic import BaseSettings

class MyModuleSettings(BaseSettings):
    api_key: str
    timeout: int = 30
    
    class Config:
        env_prefix = "MY_MODULE_"

def get_settings() -> MyModuleSettings:
    return MyModuleSettings()
```

### Settings Integration
- Automatic discovery and registration
- Environment variable override
- UI configuration support
- Validation and type checking

## Development Workflow

### 1. Create New Module
```bash
python tools/scaffold_module.py --name my_module --type standard --features database,api,settings
```

### 2. Implement Core Logic
1. Edit `api.py` - Add decorators and MODULE_* constants
2. Edit `services.py` - Implement business logic
3. Edit `module_settings.py` - Define configuration
4. Edit `db_models.py` - Add database models (if needed)

### 3. Test and Validate
```bash
python tools/compliance/compliance.py validate --module standard.my_module
python app.py  # Test integration
```

## Key Differences from v1 Architecture

**Removed:**
- `manifest.json` files
- Manual `register_routes()` methods  
- Legacy `initialize()` patterns
- Complex dependency chains
- Circular dependencies

**Added:**
- Decorator-based registration
- Centralized processing
- Clean separation patterns
- Automatic discovery
- Priority management
- Data integrity enforcement

## Benefits of v3.0.0 Architecture

1. **Reliability**: No circular dependencies, clean initialization
2. **Simplicity**: Single point of control, automatic discovery  
3. **Performance**: Fast Phase 1, priority-ordered Phase 2
4. **Maintainability**: Clear patterns, centralized logic
5. **Scalability**: Modular design, clean interfaces
6. **Developer Experience**: Scaffolding tools, automatic validation

This architecture provides a solid foundation for building complex, reliable applications while maintaining clean code and clear separation of concerns.
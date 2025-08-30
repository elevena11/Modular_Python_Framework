# Core Framework Guide for Module Development

**Target Audience:** Module developers  
**Purpose:** Understanding core framework patterns and requirements

## Overview

This guide covers the core framework files (`app_context.py` and `module_loader.py`) and the patterns your modules must follow to integrate properly with the VeritasForma Framework.

## AppContext - Dependency Injection Container

### What AppContext Provides

The `AppContext` is the central dependency injection container that provides modules with:

- **Service Registry** - Register and access services from other modules
- **Database Access** - Async database sessions and engines  
- **API Integration** - Route registration for FastAPI
- **Configuration** - Framework-wide configuration access
- **Shutdown Management** - Graceful cleanup on framework shutdown

### Key Methods for Modules

#### Service Management
```python
# Register your service (Phase 1)
app_context.register_service("my.module.service", my_service_instance)

# Access other services (Phase 2+)
db_service = app_context.get_service("core.database.service")
settings_service = app_context.get_service("core.settings.service")
```

#### Database Access
```python
# Recommended pattern - use the session factory
async with app_context.db_session() as session:
    result = await session.execute(stmt)
    await session.commit()

# Alternative - direct engine access (if needed)
engine = app_context.db_engine  # AsyncEngine instance
```

#### Database Model Registration
```python
# Register SQLAlchemy models with specific database (Phase 1 only)
from .db_models import MyModel, AnotherModel

# For framework database (core modules: settings, error_handler, etc.)
app_context.register_models([MyModel, AnotherModel], database="framework")

# For module-specific database (standard/extension modules)
app_context.register_models([MyModel, AnotherModel], database="my_module_db")
```

**Multi-Database Architecture:**
- **Framework Database** (`framework.db`): Core framework tables, settings, error logs
- **Module Databases** (`module_name.db`): Module-specific tables, completely isolated
- **Database Parameter Required**: Must specify which database your models belong to

#### Shutdown Handlers
```python
# Register cleanup function
app_context.register_shutdown_handler(my_cleanup_function)

def my_cleanup_function():
    """Called during framework shutdown"""
    # Close connections, save state, etc.
    pass
```

## ModuleLoader - Two-Phase Loading System

### Module Discovery

The `ModuleLoader` automatically discovers modules by scanning:
```
modules/
├── core/           # Phase: Always loaded first  
├── standard/       # Phase: General modules
└── extensions/     # Phase: Custom modules
```

**Requirements for Discovery:**
1. Module must have `manifest.json`
2. Module must have `services.py` with `async def initialize(app_context)`

### Two-Phase Initialization Pattern

The framework uses a two-phase initialization to ensure proper dependency resolution and database setup.

#### Phase 1: Registration (Fast & Synchronous)
**Purpose:** Register services, models, and hooks - establish the module's presence
**Timing:** During application startup, before database creation
**What's Allowed:** 
- ✅ Service registration
- ✅ Database model registration (with database specification)
- ✅ Hook registration for Phase 2
- ✅ Shutdown handler registration
- ✅ Basic settings registration
**What's NOT Allowed:**
- ❌ Complex database operations
- ❌ Calling other module services (they may not exist yet)
- ❌ Heavy initialization work

```python
# In your services.py
async def initialize(app_context):
    """Phase 1: Registration only"""
    # 1. Register your service
    my_service = MyService(app_context)
    app_context.register_service("my.module.service", my_service)
    
    # 2. Register database models with target database
    from .db_models import MyModel, AnotherModel
    
    # Core modules register with framework database
    app_context.register_models([MyModel, AnotherModel], database="framework")
    
    # Standard/extension modules create their own database
    # app_context.register_models([MyModel, AnotherModel], database="my_module_db")
    
    # 3. Register for Phase 2 (if complex initialization needed)
    app_context.register_module_setup_hook(
        module_id="my.module",
        setup_method=setup_module,
        priority=100  # Lower numbers run first
    )
    
    # 4. Register shutdown cleanup
    app_context.register_shutdown_handler(cleanup)
    
    return True
```

**Database Registration Rules:**
- **Core modules** (`core.*`): Use `database="framework"` 
- **Standard/Extension modules**: Use `database="your_module_name"`
- **Database parameter is required** - no default to prevent accidents

#### Phase 2: Setup (Complex Operations)
**Purpose:** Complex initialization after all modules loaded and databases created
**Timing:** After Phase 1 complete, databases ready, other services available
**What's Allowed:**
- ✅ Database operations (tables are created)
- ✅ Settings access and complex configuration
- ✅ Calling other module services
- ✅ Heavy initialization work
- ✅ External system connections
**When to Use Phase 2:**
- Database operations beyond simple model registration
- Initialization that depends on other modules
- Complex setup that takes time

```python
async def setup_module(app_context):
    """Phase 2: Complex initialization"""
    # Now safe to access other services
    db_service = app_context.get_service("core.database.service")
    settings_service = app_context.get_service("core.settings.service")
    
    # Database operations are now safe
    await create_initial_data()
    
    # Complex initialization
    await initialize_external_connections()
    
    return True
```

**Execution Order:**
1. All Phase 1 registrations complete
2. Databases created using registered models  
3. Phase 2 hooks execute by priority (lower numbers first)
4. Framework ready for use
- [CORRECT] External connections
- [CORRECT] Service interactions

```python
# In your services.py
async def setup_module(app_context):
    """Phase 2: Complex initialization"""
    # Get required services
    db_service = app_context.get_service("core.database.service")
    if not db_service or not db_service.is_initialized():
        return False
    
    # Load module settings
    settings = await app_context.get_module_settings("my.module")
    
    # Initialize complex services
    my_service = app_context.get_service("my.module.service")
    await my_service.initialize_complex_features(settings)
    
    return True
```

## Module Requirements and Standards

### Mandatory Files

#### manifest.json
```json
{
    "id": "my.module",
    "name": "My Module", 
    "version": "1.0.0",
    "description": "What this module does",
    "dependencies": ["core.database", "core.settings"],
    "entry_point": "services.py"
}
```

#### services.py
```python
"""
Module main service implementation
"""
import logging
from modules.core.error_handler.utils import Result, error_message

MODULE_ID = "my.module"
logger = logging.getLogger(MODULE_ID)

class MyService:
    def __init__(self, app_context):
        self.app_context = app_context
        self.initialized = False
        # Only basic initialization here
    
    async def initialize_complex_features(self, settings):
        """Called during Phase 2"""
        # Complex initialization here
        self.initialized = True

# Framework integration
async def initialize(app_context):
    """Required: Phase 1 initialization"""
    logger.info(f"Initializing {MODULE_ID} module (Phase 1)")
    
    try:
        # Register service
        service = MyService(app_context)
        app_context.register_service(f"{MODULE_ID}.service", service)
        
        # Register for Phase 2 if needed
        app_context.register_module_setup_hook(
            module_id=MODULE_ID,
            setup_method=setup_module
        )
        
        return True
    except Exception as e:
        logger.error(f"Error initializing {MODULE_ID}: {e}")
        return False

async def setup_module(app_context):
    """Optional: Phase 2 setup"""
    logger.info(f"Setting up {MODULE_ID} module (Phase 2)")
    # Complex initialization here
    return True
```

### Optional Files

#### module_settings.py
```python
"""Module configuration"""

# Default settings
MODULE_SETTINGS = {
    "feature_enabled": True,
    "timeout": 30,
    "api_key": None
}

# Validation schema
VALIDATION_SCHEMA = {
    "feature_enabled": {"type": "boolean"},
    "timeout": {"type": "integer", "min": 1, "max": 300},
    "api_key": {"type": "string", "optional": True}
}

# UI metadata  
UI_METADATA = {
    "feature_enabled": {
        "display_name": "Enable Feature",
        "input_type": "checkbox",
        "category": "General"
    }
}

async def register_settings(app_context):
    """Register with framework settings system"""
    settings_service = app_context.get_service("core.settings.service")
    if settings_service:
        return await settings_service.register_module_settings(
            module_id="my.module",
            default_settings=MODULE_SETTINGS,
            validation_schema=VALIDATION_SCHEMA,
            ui_metadata=UI_METADATA,
            version="1.0.0"
        )
    return False
```

## Error Handling Patterns

### Import Error Handler Utilities
```python
# Always import these for proper error handling
from modules.core.error_handler.utils import Result, error_message, create_error_response
```

### Service Method Returns
```python
def my_service_method(self, data):
    """Service methods should return Result objects"""
    try:
        # Business logic
        result = self.process_data(data)
        return Result.success(data=result)
    except Exception as e:
        # Log structured error
        logger.error(error_message(
            module_id=MODULE_ID,
            error_type="PROCESSING_FAILED",
            details=f"Failed to process data: {str(e)}",
            location="my_service_method()"
        ))
        return Result.error(
            code="PROCESSING_FAILED",
            message="Data processing failed"
        )
```

### API Error Handling
```python
# In api.py
from modules.core.error_handler.utils import create_error_response

@router.post("/endpoint")
async def my_endpoint(data: MySchema):
    if not validate_data(data):
        raise create_error_response(
            module_id=MODULE_ID,
            code="VALIDATION_ERROR",
            message="Invalid input data",
            status_code=422
        )
```

## Database Integration

### Model Registration (Phase 1)
```python
# In db_models.py
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class MyModel(Base):
    __tablename__ = "my_table"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    created_at = Column(DateTime, nullable=False)

# In services.py initialize()
app_context.register_models([MyModel])
```

### Database Operations (Phase 2+)
```python
async def get_records(self):
    """Example database operation"""
    try:
        async with self.app_context.db_session() as session:
            stmt = select(MyModel).where(MyModel.active == True)
            result = await session.execute(stmt)
            records = result.scalars().all()
            return Result.success(data=[r.to_dict() for r in records])
    except Exception as e:
        logger.error(error_message(
            module_id=MODULE_ID,
            error_type="DB_QUERY_FAILED",
            details=str(e),
            location="get_records()"
        ))
        return Result.error(code="DB_ERROR", message="Database query failed")
```

## API Integration

### Route Registration
```python
# In api.py
from fastapi import APIRouter, HTTPException
from .api_schemas import MyRequest, MyResponse
from .services import get_my_service

router = APIRouter()

@router.post("/process", response_model=MyResponse)
async def process_data(request: MyRequest):
    service = get_my_service()
    result = service.process(request.data)
    
    if result.success:
        return MyResponse(data=result.data)
    else:
        raise HTTPException(
            status_code=400,
            detail=result.message
        )

# Framework will auto-discover and register routes
```

## UI Integration

### Streamlit Components
```python
# In ui/ui_streamlit.py
import streamlit as st

def register_components(ui_context):
    """Register UI components with framework"""
    ui_context.register_element({
        "id": "my_module_tab",
        "type": "tab",
        "display_name": "My Module",
        "description": "My module interface",
        "render_function": render_my_tab,
        "order": 100
    })

def render_my_tab(ui_context):
    """Render the module's UI tab"""
    st.title("My Module")
    
    # Get service instance
    try:
        from ..services import get_my_service
        service = get_my_service()
        
        if st.button("Do Something"):
            result = service.do_something()
            if result.success:
                st.success("Operation completed!")
                st.json(result.data)
            else:
                st.error(f"Error: {result.message}")
                
    except Exception as e:
        st.error(f"Failed to load service: {str(e)}")
```

## Common Patterns and Best Practices

### Service Singleton Pattern
```python
# Global service instance
_service_instance = None

def get_my_service():
    """Get the global service instance"""
    global _service_instance
    if _service_instance is None:
        raise RuntimeError("Service not initialized")
    return _service_instance

def cleanup_service():
    """Cleanup function for shutdown"""
    global _service_instance
    if _service_instance:
        _service_instance.cleanup()
        _service_instance = None

# In initialize()
_service_instance = MyService(app_context)
app_context.register_service(f"{MODULE_ID}.service", _service_instance)
app_context.register_shutdown_handler(cleanup_service)
```

### Settings Access Pattern
```python
async def load_module_settings(self):
    """Load settings from framework"""
    try:
        settings = await self.app_context.get_module_settings(MODULE_ID)
        self.config.update(settings)
        logger.info(f"Loaded settings for {MODULE_ID}")
        return True
    except Exception as e:
        logger.error(f"Failed to load settings: {e}")
        return False
```

### Dependency Checking Pattern
```python
async def setup_module(app_context):
    """Phase 2 with dependency checking"""
    # Check required services
    db_service = app_context.get_service("core.database.service")
    if not db_service or not db_service.is_initialized():
        logger.error("Database service not available")
        return False
    
    settings_service = app_context.get_service("core.settings.service")
    if not settings_service:
        logger.warning("Settings service not available")
    
    # Continue with setup
    return True
```

## Module Lifecycle Summary

1. **Discovery**: Framework scans for `manifest.json`
2. **Phase 1**: Call `initialize(app_context)` - register only
3. **Phase 2**: Call `setup_module(app_context)` - complex operations
4. **Runtime**: Module services available via `app_context.get_service()`
5. **Shutdown**: Call registered shutdown handlers

## Debugging and Logging

### Module-Specific Logging
```python
import logging
MODULE_ID = "my.module"
logger = logging.getLogger(MODULE_ID)

# Logs go to data/logs/app.log
logger.info("Module operation completed")
logger.error("Module error occurred")
```

### Framework Debugging
- **Module Loading**: `data/logs/module_loader.log`
- **Application**: `data/logs/app.log` 
- **UI**: `data/logs/ui.log`

This guide provides the foundation for building modules that integrate properly with the VeritasForma Framework's core systems.
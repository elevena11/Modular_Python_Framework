# VeritasForma Framework: Complete Module Creation Guide

**Version: 2.0**  
**Updated: June 9, 2025**  
**Status: Current Implementation Guide**

## Overview

This guide provides the definitive approach for creating modules in the VeritasForma Framework, incorporating mandatory error handling patterns, two-phase initialization, and proper resource management. All patterns are based on successfully implemented modules in the framework.

## Table of Contents

1. [Required Module Components](#required-module-components)
2. [Optional Module Components](#optional-module-components)
3. [Module Foundation Implementation](#module-foundation-implementation)
4. [Error Handling Patterns (Mandatory)](#error-handling-patterns-mandatory)
5. [Service Layer Implementation](#service-layer-implementation)
6. [Data Layer Implementation](#data-layer-implementation)
7. [API Layer Implementation](#api-layer-implementation)
8. [Settings Management](#settings-management)
9. [Resource Management and Shutdown](#resource-management-and-shutdown)
10. [Implementation Checklist](#implementation-checklist)

## Required Module Components

Every module MUST implement these three core components:

### 1. `manifest.json` - Module Identity
- **Purpose**: Defines module identity, dependencies, and metadata
- **Location**: Module root directory
- **Critical Requirements**:
  - Unique `id` using dot notation (e.g., `standard.my_module`)
  - Only list modules providing SERVICES you directly consume
  - DO NOT list `core.error_handler` or `core.trace_logger` as dependencies

```json
{
  "id": "standard.my_module",
  "name": "My Module",
  "version": "1.0.0",
  "description": "Brief description of module purpose",
  "author": "VeritasForma Framework",
  "entry_point": "api.py",
  "dependencies": [
    "core.database",
    "core.settings"
  ]
}
```

**Naming Conventions for manifest.json:**
- **`id`**: Use snake_case (e.g., `llm_agent`, `user_analytics`)
- **`name`**: Use Title Case for display names (e.g., "LLM Agent", "User Analytics")
- **`description`**: Use proper capitalization (e.g., "LLM agent module" not "llm agent module")
- **Acronyms**: Always uppercase in display text (LLM, API, UI, etc.)

### 2. `api.py` - Module Initialization and API
- **Purpose**: Two-phase initialization and API endpoint registration
- **Critical Functions**:
  - `async def initialize(app_context)` - Phase 1 registration
  - `async def setup_module(app_context)` - Phase 2 activation
  - `def register_routes(api_router)` - Route registration
- **Must include**: `MODULE_ID` constant matching manifest.json

### 3. `services.py` - Business Logic
- **Purpose**: Core service implementation with Result pattern
- **Critical Requirements**:
  - Service class with sync `__init__` and async `initialize`
  - All service methods return `Result` objects
  - Proper error handling with `error_message` utility
  - `MODULE_ID` constant for error attribution

## Optional Module Components

Implement these components based on your module's needs:

### 4. `database.py` - Database Operations (if data persistence needed)
- Database operations class with standardized patterns
- `_db_session()` async context manager
- `_db_op()` error handling wrapper

### 5. `db_models.py` - Database Models (if database.py used)
- SQLAlchemy models inheriting from framework Base
- Use `SQLiteJSON` for complex data types

### 6. `api_schemas.py` - API Validation (if API endpoints needed)
- Pydantic request/response models
- Separate schemas for requests and responses

### 7. `module_settings.py` - Configuration (if settings needed)
- Default settings, validation schema, UI metadata
- Settings registration function

### 8. `components/` - Complex Logic Breakdown (for large modules)
- Separate focused service classes
- Each component defines `COMPONENT_ID`
- Hierarchical service registration

### 9. `ui/` - User Interface (if UI needed)
- `ui_streamlit.py` and/or `ui_gradio.py`
- Framework-agnostic UI logic

## Module Foundation Implementation

### Directory Structure
```
modules/standard/my_module/
├── manifest.json              # Required
├── api.py                     # Required  
├── services.py                # Required
├── database.py                # Optional
├── db_models.py               # Optional
├── api_schemas.py             # Optional
├── module_settings.py         # Optional
├── components/                # Optional
│   ├── __init__.py
│   └── specialized_logic.py
└── ui/                        # Optional
    ├── __init__.py
    └── ui_streamlit.py
```

### Module Identity Pattern
Every Python file in your module must define `MODULE_ID`:

```python
# At top of every Python file (api.py, services.py, database.py, etc.)
MODULE_ID = "standard.my_module"  # Must match manifest.json
logger = logging.getLogger(MODULE_ID)
```

For component files, also define `COMPONENT_ID`:

```python
# In components/specialized_logic.py
MODULE_ID = "standard.my_module"
COMPONENT_ID = f"{MODULE_ID}.specialized_logic"
logger = logging.getLogger(COMPONENT_ID)
```

## Error Handling Patterns (Mandatory)

The framework requires consistent error handling across all modules. This pattern was successfully implemented in the LLM agent module and is now mandatory.

### Import Error Handling Utilities

```python
# In all module files
from modules.core.error_handler.utils import Result, error_message, create_error_response
import logging

MODULE_ID = "standard.my_module"  # Define at top of file
logger = logging.getLogger(MODULE_ID)
```

### Service Layer Error Handling

**All service methods MUST return Result objects:**

```python
async def process_data(self, data: dict) -> Result:
    """Example service method with proper error handling."""
    try:
        # Validate input
        if not data:
            return Result.error(
                code="EMPTY_DATA",  # Base error code
                message="No data provided for processing"
            )
        
        # Perform operation
        result = await self._perform_operation(data)
        
        # Return success
        return Result.success(data=result)
        
    except Exception as e:
        # Log error with proper attribution
        logger.error(error_message(
            module_id=MODULE_ID,  # Pass MODULE_ID explicitly
            error_type="PROCESSING_ERROR",  # Base error type
            details=f"Error processing data: {str(e)}",
            location="process_data()"
        ))
        
        # Return error result
        return Result.error(
            code="PROCESSING_ERROR",  # Base error code
            message="Failed to process data",
            details={"error_type": type(e).__name__}
        )
```

### API Layer Error Handling

**API endpoints must convert Result objects to HTTP responses:**

```python
@router.post("/process", response_model=ProcessResponse)
async def process_endpoint(request: ProcessRequest):
    """Example API endpoint with proper error handling."""
    global service_instance
    
    try:
        # Check service availability
        if not service_instance:
            raise HTTPException(
                status_code=503,
                detail=create_error_response(
                    module_id=MODULE_ID,  # Pass MODULE_ID explicitly
                    code="SERVICE_UNAVAILABLE",  # Base error code
                    message="Service is not available"
                )
            )
        
        # Call service method
        result = await service_instance.process_data(request.model_dump())
        
        # Check service result
        if not result.success:
            error = result.error
            base_error_code = error.get("code", "UNKNOWN_ERROR")
            
            # Determine HTTP status code
            status_code = 400  # Default
            if base_error_code == "NOT_FOUND":
                status_code = 404
            
            raise HTTPException(
                status_code=status_code,
                detail=create_error_response(
                    module_id=MODULE_ID,  # Pass MODULE_ID explicitly
                    code=base_error_code,  # Pass base code from service
                    message=error.get("message", "Operation failed"),
                    details=error.get("details")
                )
            )
        
        # Return success response
        return ProcessResponse(**result.data)
        
    except HTTPException:
        raise  # Re-raise HTTP exceptions
        
    except Exception as e:
        # Handle unexpected errors
        logger.error(error_message(
            module_id=MODULE_ID,
            error_type="UNEXPECTED_ERROR",
            details=f"Unexpected error in process_endpoint: {str(e)}",
            location="process_endpoint()"
        ))
        
        raise HTTPException(
            status_code=500,
            detail=create_error_response(
                module_id=MODULE_ID,
                code="INTERNAL_ERROR",
                message="An unexpected error occurred"
            )
        )
```

### Error Code Conventions

1. **Define MODULE_ID** at the top of each file
2. **Use base error codes** in Result.error() and create_error_response()
3. **Pass module_id explicitly** to all error utilities
4. **Log with error_message()** for consistent attribution

**Example Error Codes:**
- Service layer: `"VALIDATION_ERROR"`, `"NOT_FOUND"`, `"PROCESSING_ERROR"`
- Logged codes: `standard_my_module_VALIDATION_ERROR` (constructed by utilities)

## Service Layer Implementation

### Hybrid Service Pattern (Recommended)

```python
"""
modules/standard/my_module/services.py
Service implementation with proper patterns
"""

import logging
from typing import Dict, Any, Optional
from modules.core.error_handler.utils import Result, error_message

# Module identity
MODULE_ID = "standard.my_module"
logger = logging.getLogger(MODULE_ID)

class MyModuleService:
    """Main service for my module."""
    
    def __init__(self, app_context):
        """Sync initialization - NO complex operations."""
        self.app_context = app_context
        self.logger = logger
        self.initialized = False
        self.config = {}
        
        # Lazy loading references
        self._dependency_service = None
        
        logger.info(f"{MODULE_ID} service created")
    
    @property
    def dependency_service(self):
        """Lazy load dependency service."""
        if self._dependency_service is None:
            self._dependency_service = self.app_context.get_service("core.settings.service")
            if not self._dependency_service:
                logger.error(error_message(
                    module_id=MODULE_ID,
                    error_type="DEPENDENCY_UNAVAILABLE",
                    details="Settings service not available",
                    location="dependency_service property"
                ))
        return self._dependency_service
    
    async def initialize(self, app_context=None, settings=None) -> bool:
        """Phase 2 initialization - Load settings and complex setup."""
        if self.initialized:
            return True
        
        logger.info(f"Initializing {MODULE_ID} service")
        
        try:
            # Load settings
            if settings:
                self.config = settings
            else:
                context = app_context or self.app_context
                self.config = await context.get_module_settings(MODULE_ID)
            
            # Perform complex initialization
            # Check dependencies, setup state, etc.
            
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
    
    async def example_method(self, data: Dict[str, Any]) -> Result:
        """Example service method returning Result."""
        # Check initialization
        if not self.initialized and not await self.initialize():
            return Result.error(
                code="SERVICE_NOT_INITIALIZED",
                message=f"{MODULE_ID} service not initialized"
            )
        
        try:
            # Validate input
            if not data:
                return Result.error(
                    code="INVALID_INPUT",
                    message="No data provided"
                )
            
            # Process data
            result = {"processed": True, "data": data}
            
            return Result.success(data=result)
            
        except Exception as e:
            logger.error(error_message(
                module_id=MODULE_ID,
                error_type="PROCESSING_ERROR",
                details=f"Error in example_method: {str(e)}",
                location="example_method()"
            ))
            
            return Result.error(
                code="PROCESSING_ERROR",
                message="Failed to process data"
            )
```

## Data Layer Implementation

### Database Models (db_models.py)

**IMPORTANT: Table-Driven Database Discovery**
The framework automatically discovers and creates databases by scanning `db_models.py` files.

**For complete database documentation, see: `docs/modules/database-module.md`**

```python
"""
modules/standard/my_module/db_models.py
Database models for my_module.
"""

# Database configuration for file-based discovery
DATABASE_NAME = "my_module"

from sqlalchemy import Column, Integer, String, Text, DateTime
from modules.core.database.db_models import get_database_base, SQLiteJSON
from sqlalchemy.sql import func

# Get database base for this module - creates my_module.db
MyModuleBase = get_database_base(DATABASE_NAME)

class MyModel(MyModuleBase):
    """Database model for my module."""
    
    __tablename__ = "my_module_items"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    metadata = Column(SQLiteJSON, nullable=False, default=dict)
    created_at = Column(DateTime, default=func.now())
```

**Key Requirements:**
1. **`DATABASE_NAME` constant** - Required for automatic discovery
2. **Use `get_database_base(DATABASE_NAME)`** - Creates module-specific base
3. **Framework handles creation** - Database created automatically during startup

**Database File Locations:**
- Framework: `/data/database/framework.db` (core framework tables)
- Module-specific: `/data/database/{DATABASE_NAME}.db` (your module's tables only)

### Database Operations (database.py)

```python
import logging
import contextlib
from typing import Dict, Any, Optional, AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from modules.core.error_handler.utils import Result, error_message

from .db_models import MyModel

MODULE_ID = "standard.my_module"
logger = logging.getLogger(f"{MODULE_ID}.database")

class MyModuleDatabaseOperations:
    """Database operations for my module."""
    
    def __init__(self, app_context):
        self.app_context = app_context
        self.db_service = app_context.get_service("core.database.service")
        self.crud_service = app_context.get_service("core.database.crud_service")
        self.initialized = False
        self.logger = logger
    
    async def initialize(self) -> bool:
        """Initialize database operations."""
        if self.initialized:
            return True
        
        if not self.db_service or not self.db_service.initialized:
            logger.warning(error_message(
                module_id=MODULE_ID,
                error_type="DB_SERVICE_UNAVAILABLE",
                details="Database service not available",
                location="initialize()"
            ))
            return False
        
        if not self.crud_service:
            logger.warning(error_message(
                module_id=MODULE_ID,
                error_type="CRUD_SERVICE_UNAVAILABLE",
                details="CRUD service not available",
                location="initialize()"
            ))
            return False
        
        self.initialized = True
        logger.info("Database operations initialized")
        return True
    
    @contextlib.asynccontextmanager
    async def _db_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Provides async database session."""
        if not self.initialized and not await self.initialize():
            raise RuntimeError("Database operations not initialized")
        
        async with AsyncSession(self.db_service.engine) as session:
            yield session
    
    async def _db_op(self, op_func, default=None):
        """Execute DB operation with error handling."""
        try:
            return await op_func()
        except RuntimeError as e:
            logger.error(error_message(
                module_id=MODULE_ID,
                error_type="DB_INIT_ERROR",
                details=f"DB operations not ready: {str(e)}",
                location="_db_op"
            ))
            return default
        except Exception as e:
            logger.error(error_message(
                module_id=MODULE_ID,
                error_type="DB_OPERATION_ERROR",
                details=f"Database operation failed: {str(e)}",
                location="_db_op"
            ), exc_info=True)
            return default
    
    async def create_item(self, item_data: Dict[str, Any]) -> Result:
        """Create a new item."""
        async def _create():
            async with self._db_session() as session:
                item = await self.db_service.execute_with_retry(
                    self.crud_service.create(session, MyModel, item_data)
                )
                return {"id": item.id, "name": item.name}
        
        result = await self._db_op(_create)
        if result is None:
            return Result.error(
                code="DB_CREATE_FAILED",
                message="Failed to create item",
                details={"item_data": item_data}
            )
        return Result.success(data=result)
    
    async def get_item(self, item_id: int) -> Result:
        """Get item by ID."""
        async def _get():
            async with self._db_session() as session:
                item = await self.db_service.execute_with_retry(
                    self.crud_service.read(session, MyModel, item_id, as_dict=True)
                )
                return item
        
        item = await self._db_op(_get)
        if item is None:
            return Result.error(
                code="ITEM_NOT_FOUND",
                message=f"Item with ID {item_id} not found",
                details={"item_id": item_id}
            )
        return Result.success(data=item)
```

## API Layer Implementation

### API Schemas (api_schemas.py)

```python
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional

class ItemCreateRequest(BaseModel):
    """Request schema for creating an item."""
    
    name: str = Field(..., min_length=1, description="Item name")
    description: Optional[str] = Field(None, description="Item description")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Item metadata")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "Example Item",
                "description": "This is an example",
                "metadata": {"key": "value"}
            }
        }
    }

class ItemResponse(BaseModel):
    """Response schema for an item."""
    
    id: int = Field(..., description="Item ID")
    name: str = Field(..., description="Item name")
    description: Optional[str] = Field(None, description="Item description")
    metadata: Dict[str, Any] = Field(..., description="Item metadata")
```

### Two-Phase Initialization (api.py)

```python
"""
modules/standard/my_module/api.py
Module initialization and API endpoints
"""

import logging
from fastapi import APIRouter, HTTPException
from modules.core.error_handler.utils import create_error_response, error_message

from .services import MyModuleService
from .api_schemas import ItemCreateRequest, ItemResponse

# Module identity
MODULE_ID = "standard.my_module"
logger = logging.getLogger(MODULE_ID)

# Global service instance
service_instance = None

# API router
router = APIRouter(prefix="/my-module", tags=["My Module"])

async def initialize(app_context):
    """Phase 1: Registration ONLY."""
    global service_instance
    
    logger.info(f"Initializing {MODULE_ID} (Phase 1)")
    
    try:
        # 1. Create service instance (sync __init__)
        service_instance = MyModuleService(app_context)
        
        # 2. Register service
        app_context.register_service(f"{MODULE_ID}.service", service_instance)
        
        # 3. Database models are automatically discovered (if db_models.py exists)
        # Framework scans for DATABASE_NAME and creates databases automatically
        # No manual registration needed - see docs/modules/database-module.md
        
        # 4. Register settings (if applicable)
        # from .module_settings import register_settings
        # await register_settings(app_context)
        
        # 5. Register for Phase 2 (REQUIRED)
        app_context.register_module_setup_hook(
            module_id=MODULE_ID,
            setup_method=setup_module
        )
        
        logger.info(f"{MODULE_ID} Phase 1 complete")
        return True
        
    except Exception as e:
        logger.error(error_message(
            module_id=MODULE_ID,
            error_type="INIT_ERROR",
            details=f"Error in Phase 1: {str(e)}",
            location="initialize()"
        ))
        return False

async def setup_module(app_context):
    """Phase 2: Activation."""
    global service_instance
    
    logger.info(f"Setting up {MODULE_ID} (Phase 2)")
    
    try:
        # Load settings
        settings = await app_context.get_module_settings(MODULE_ID)
        
        # Initialize service explicitly
        if service_instance:
            initialized = await service_instance.initialize(
                app_context=app_context,
                settings=settings
            )
            if not initialized:
                logger.error(f"Failed to initialize {MODULE_ID} service")
                return False
        else:
            logger.error(f"{MODULE_ID} service not created in Phase 1")
            return False
        
        logger.info(f"{MODULE_ID} Phase 2 complete")
        return True
        
    except Exception as e:
        logger.error(error_message(
            module_id=MODULE_ID,
            error_type="SETUP_ERROR",
            details=f"Error in Phase 2: {str(e)}",
            location="setup_module()"
        ))
        return False

def register_routes(api_router):
    """Register module routes."""
    api_router.include_router(router)

# API Endpoints

@router.post("/items", response_model=ItemResponse)
async def create_item(request: ItemCreateRequest):
    """Create a new item."""
    global service_instance
    
    try:
        # Check service availability
        if not service_instance:
            raise HTTPException(
                status_code=503,
                detail=create_error_response(
                    module_id=MODULE_ID,
                    code="SERVICE_UNAVAILABLE",
                    message="Service is not available"
                )
            )
        
        # Call service method
        result = await service_instance.create_item(request.model_dump())
        
        # Check result
        if not result.success:
            error = result.error
            base_error_code = error.get("code", "UNKNOWN_ERROR")
            
            # Determine status code
            status_code = 400
            if base_error_code == "DUPLICATE_ITEM":
                status_code = 409
            
            raise HTTPException(
                status_code=status_code,
                detail=create_error_response(
                    module_id=MODULE_ID,
                    code=base_error_code,
                    message=error.get("message", "Failed to create item"),
                    details=error.get("details")
                )
            )
        
        # Return response model instance
        return ItemResponse(**result.data)
        
    except HTTPException:
        raise
        
    except Exception as e:
        logger.error(error_message(
            module_id=MODULE_ID,
            error_type="UNEXPECTED_ERROR",
            details=f"Unexpected error creating item: {str(e)}",
            location="create_item()"
        ))
        
        raise HTTPException(
            status_code=500,
            detail=create_error_response(
                module_id=MODULE_ID,
                code="INTERNAL_ERROR",
                message="An unexpected error occurred"
            )
        )
```

## Settings Management

### Module Settings (module_settings.py)

```python
"""
modules/standard/my_module/module_settings.py
Settings definition for my module
"""

import logging
from modules.core.error_handler.utils import error_message

MODULE_ID = "standard.my_module"
logger = logging.getLogger(MODULE_ID)

# Default settings
DEFAULT_SETTINGS = {
    "feature_enabled": True,
    "max_items": 100,
    "timeout_seconds": 30.0
}

# Validation schema - use correct type names
VALIDATION_SCHEMA = {
    "feature_enabled": {
        "type": "bool",  # Use "bool", not "boolean"
        "required": False
    },
    "max_items": {
        "type": "int",   # Use "int", not "integer"
        "required": False,
        "min": 1,
        "max": 1000
    },
    "timeout_seconds": {
        "type": "float", # Use "float", not "number"
        "required": False,
        "min": 0.1,
        "max": 300.0
    }
}

# UI metadata
UI_METADATA = {
    "feature_enabled": {
        "display_name": "Enable Feature",
        "description": "Turn this feature on or off",
        "type": "checkbox",  # UI type
        "category": "General"
    },
    "max_items": {
        "display_name": "Maximum Items",
        "description": "Maximum number of items",
        "type": "number",    # UI type
        "category": "Limits"
    },
    "timeout_seconds": {
        "display_name": "Timeout (seconds)",
        "description": "Operation timeout",
        "type": "number",    # UI type
        "category": "Performance"
    }
}

async def register_settings(app_context):
    """Register module settings."""
    logger.info(f"Registering settings for {MODULE_ID}")
    
    try:
        success = await app_context.register_module_settings(
            module_id=MODULE_ID,
            default_settings=DEFAULT_SETTINGS,
            validation_schema=VALIDATION_SCHEMA,
            ui_metadata=UI_METADATA
        )
        
        if success:
            logger.info(f"Successfully registered settings for {MODULE_ID}")
        else:
            logger.error(error_message(
                module_id=MODULE_ID,
                error_type="SETTINGS_REGISTRATION_FAILED",
                details=f"Failed to register settings for {MODULE_ID}",
                location="register_settings()"
            ))
        
        return success
        
    except Exception as e:
        logger.error(error_message(
            module_id=MODULE_ID,
            error_type="SETTINGS_REGISTRATION_ERROR",
            details=f"Error registering settings: {str(e)}",
            location="register_settings()"
        ), exc_info=True)
        return False
```

## Resource Management and Shutdown

### Graceful Shutdown Implementation

```python
# In your service class (services.py)
async def shutdown(self):
    """Graceful async shutdown."""
    logger.info(f"Shutting down {MODULE_ID} service...")
    
    # Cancel background tasks
    for task in getattr(self, '_background_tasks', []):
        if not task.done():
            task.cancel()
            try:
                await asyncio.wait_for(task, timeout=2.0)
            except (asyncio.TimeoutError, asyncio.CancelledError):
                pass
    
    # Close async resources
    for resource in getattr(self, '_resources', []):
        if hasattr(resource, 'close'):
            try:
                await resource.close()
            except Exception as e:
                logger.warning(f"Error closing resource: {str(e)}")
    
    logger.info(f"{MODULE_ID} service shutdown complete")

def force_shutdown(self):
    """Forced synchronous shutdown."""
    logger.info(f"Force shutting down {MODULE_ID} service...")
    
    # Signal tasks to stop
    self._is_running = False
    
    # Close resources directly
    for resource in getattr(self, '_resources', []):
        if hasattr(resource, 'close'):
            try:
                resource.close()
            except Exception as e:
                logger.warning(f"Error closing resource: {str(e)}")
    
    logger.info(f"{MODULE_ID} service force shutdown complete")
```

### Register Shutdown Handler

```python
# In api.py initialize() function
async def initialize(app_context):
    # ... other initialization code ...
    
    # Register shutdown handler
    app_context.register_shutdown_handler(service_instance.shutdown)
    
    # ... rest of initialization ...
```

## Implementation Checklist

### Required Components ✓
- [ ] `manifest.json` with correct ID and dependencies
- [ ] `api.py` with two-phase initialization
- [ ] `services.py` with Result pattern and error handling
- [ ] `MODULE_ID` constants in all Python files
- [ ] Error handling with `error_message`, `Result`, `create_error_response`

### Optional Components (as needed)
- [ ] `database.py` with standardized operations
- [ ] `db_models.py` with SQLAlchemy models
- [ ] `api_schemas.py` with Pydantic schemas
- [ ] `module_settings.py` with proper validation types
- [ ] `components/` for complex logic breakdown
- [ ] `ui/` for user interface components

### Error Handling Verification ✓
- [ ] All service methods return `Result` objects
- [ ] API endpoints use `create_error_response`
- [ ] Logging uses `error_message` with `module_id`
- [ ] Base error codes used consistently

### Resource Management ✓
- [ ] Shutdown handlers registered
- [ ] Background tasks properly managed
- [ ] Resources cleaned up on shutdown

### Testing ✓
- [ ] Module loads successfully in both phases
- [ ] API endpoints return proper responses
- [ ] Error handling works correctly
- [ ] Settings registration works (if applicable)
- [ ] Shutdown cleanup works properly

## Success Example

This guide is based on the successful implementation of error handling patterns in the LLM agent module (`modules/standard/llm_agent/`). Refer to that module for working examples of all patterns described in this guide.

The LLM agent module demonstrates:
- Proper error handling with Result pattern
- Two-phase initialization with settings loading
- Component-based architecture with hierarchical service registration
- API endpoints with proper error responses
- Resource management and cleanup

Follow these patterns for consistent, maintainable modules that integrate seamlessly with the VeritasForma Framework.
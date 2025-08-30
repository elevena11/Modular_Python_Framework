# Decorator Pattern - Centralized Registration System

**Version: v3.0.0**  
**Updated: August 10, 2025**

## Overview

The Modular Framework uses a **decorator-based registration system** that eliminates the need for separate `manifest.json` files and centralizes all module metadata in the module's `api.py` file.

## Core Philosophy

**Single Source of Truth**: All module registration happens in one place - the module class decorators and constants in `api.py`.

**Before (Legacy):**
```
manifest.json     # Module metadata
api.py           # Module code  
initialize()     # Manual registration
register_routes() # Manual route setup
```

**After (Decorator Pattern):**
```
api.py           # Everything in one file with decorators
```

## Available Decorators

### 1. `@register_service`

**Purpose**: Register the module as a service in the framework's service container.

```python
@register_service(service_name, priority=100, dependencies=None)
```

**Parameters:**
- `service_name` (str): Unique service identifier (e.g., `"standard.my_module.service"`)
- `priority` (int): Initialization priority (lower = earlier, default: 100)
- `dependencies` (List[str]): Service dependencies (optional)

**Example:**
```python
@register_service("standard.document_processor.service", priority=100)
class DocumentProcessorModule(DataIntegrityModule):
    pass
```

**Priority Guidelines:**
- **0-10**: Core infrastructure (database, storage)
- **10-20**: Configuration and settings
- **20-50**: Security, logging, utilities  
- **50-100**: Business logic services
- **100+**: Application-specific services (default)

### 2. `@provides_api_endpoints`

**Purpose**: Automatically register API routes with the framework.

```python
@provides_api_endpoints(router_name, prefix=None)
```

**Parameters:**
- `router_name` (str): Name of the FastAPI router variable in the module
- `prefix` (str): URL prefix for all routes (optional)

**Example:**
```python
from fastapi import APIRouter
router = APIRouter()

@router.get("/process")
async def process_document():
    return {"status": "processing"}

@provides_api_endpoints(router_name="router", prefix="/api/v1/docs")
class DocumentProcessorModule(DataIntegrityModule):
    pass
```

**Result**: Routes automatically available at `/api/v1/docs/process`

### 3. `@enforce_data_integrity`

**Purpose**: Enable data integrity validation and anti-mock protection.

```python
@enforce_data_integrity(strict_mode=True, anti_mock=True)
```

**Parameters:**
- `strict_mode` (bool): Enable strict validation
- `anti_mock` (bool): Prevent mock/test data in production

**Example:**
```python
@enforce_data_integrity(strict_mode=True, anti_mock=True)
class DocumentProcessorModule(DataIntegrityModule):
    pass
```

**What it prevents:**
- Test data in production environments
- Bypassing validation checks
- Operating without proper initialization

### 4. `@module_health_check`

**Purpose**: Enable automatic health monitoring for the module.

```python
@module_health_check(interval=300)
```

**Parameters:**
- `interval` (int): Check interval in seconds

**Example:**
```python
@module_health_check(interval=300)  # Check every 5 minutes
class DocumentProcessorModule(DataIntegrityModule):
    pass
```

**Monitors:**
- Service availability
- Database connectivity  
- Resource usage
- Error rates

## Module Base Classes

### `DataIntegrityModule`

**Purpose**: Base class for modules that need data integrity protection.

```python
from core.module_base import DataIntegrityModule

class MyModule(DataIntegrityModule):
    pass
```

**Features:**
- Built-in data integrity validation
- Anti-mock protection
- Automatic compliance checking

### `DatabaseEnabledModule`

**Purpose**: Base class for modules that use databases.

```python  
from core.module_base import DatabaseEnabledModule

class MyModule(DatabaseEnabledModule):
    pass
```

**Features:**
- All DataIntegrityModule features
- Database connectivity validation
- Automatic schema management

## Module Constants

### Required Constants

Every module **must** define these constants:

```python
class MyModule(DataIntegrityModule):
    MODULE_ID = "standard.my_module"           # Unique module identifier
    MODULE_NAME = "My Module"                  # Human-readable name
    MODULE_DEPENDENCIES = ["core.settings"]   # List of required services
    MODULE_ENTRY_POINT = "api.py"            # Entry point file (always api.py)
```

### Optional Constants

```python
class MyModule(DataIntegrityModule):
    MODULE_VERSION = "1.0.0"                  # Module version
    MODULE_DESCRIPTION = "Processes documents" # Description
    MODULE_AUTHOR = "Framework Team"           # Author info
```

## Complete Example

Here's a full example showing all patterns:

```python
# modules/standard/document_processor/api.py

import logging
from fastapi import APIRouter

# Import framework decorators
from core.decorators import (
    register_service,
    provides_api_endpoints,
    enforce_data_integrity,
    module_health_check
)
from core.module_base import DataIntegrityModule
from core.error_utils import Result, create_error_response

# Import module services
from .services import DocumentProcessorService

# Module logger
logger = logging.getLogger("standard.document_processor")

# API Router
router = APIRouter()

@router.get("/process/{document_id}")
async def process_document(document_id: int):
    """Process a document by ID."""
    service = get_service()
    if not service:
        raise create_error_response(
            "SERVICE_NOT_AVAILABLE",
            "Document processor service not available",
            status_code=503
        )
    
    result = await service.process_document(document_id)
    if not result.success:
        raise create_error_response(
            result.error["code"],
            result.error["message"],
            status_code=400
        )
    
    return {"document_id": document_id, "status": "processed"}

@router.get("/health")
async def health_check():
    """Module health check endpoint."""
    return {"status": "healthy", "module": "document_processor"}

# Module registration with decorators
@register_service("standard.document_processor.service", priority=100)
@provides_api_endpoints(router_name="router", prefix="/api/v1/docs")
@enforce_data_integrity(strict_mode=True, anti_mock=True)
@module_health_check(interval=300)
class DocumentProcessorModule(DataIntegrityModule):
    """
    Document Processing Module
    
    Processes various document formats and extracts content.
    """
    
    # Required module constants
    MODULE_ID = "standard.document_processor"
    MODULE_NAME = "Document Processor"
    MODULE_DEPENDENCIES = ["core.settings", "core.database"]
    MODULE_ENTRY_POINT = "api.py"
    
    # Optional constants
    MODULE_VERSION = "1.0.0"
    MODULE_DESCRIPTION = "Processes documents and extracts content"
    
    def __init__(self):
        """Phase 1: Light initialization only."""
        logger.info(f"{self.MODULE_ID} created with decorator-based registration")
        
        # Initialize service (light initialization)
        self.document_service = DocumentProcessorService()
        
        # Store service globally for API access
        global document_processor_service
        document_processor_service = self.document_service
        
        logger.info(f"{self.MODULE_ID} Phase 1 initialization complete")
    
    async def initialize(self, app_context):
        """Phase 2: Complex initialization."""
        logger.info(f"Initializing {self.MODULE_ID} (Phase 2)")
        
        # Pass app_context to service for Phase 2 setup
        success = await self.document_service.initialize(app_context)
        
        if success:
            logger.info(f"{self.MODULE_ID} Phase 2 initialization complete")
        else:
            logger.error(f"{self.MODULE_ID} Phase 2 initialization failed")
        
        return success

# Global service access for API routes
document_processor_service = None

def get_service():
    """Get the document processor service instance."""
    return document_processor_service
```

## Framework Processing

### Automatic Discovery

The framework automatically:

1. **Scans** for modules with decorators
2. **Extracts** metadata from decorators and constants
3. **Registers** services in the service container
4. **Connects** API routes to FastAPI
5. **Schedules** initialization by priority
6. **Monitors** health checks

### Processing Flow

```
Module Discovery → Decorator Processing → Service Registration → API Setup → Health Monitoring
```

### Centralized Logic

All registration logic is handled by `core.module_processor.ModuleProcessor`:

- **Service Registration**: Registers services with priorities
- **API Registration**: Connects routers to FastAPI
- **Database Registration**: Discovers and creates databases
- **Health Monitoring**: Sets up monitoring schedules
- **Data Integrity**: Enforces validation rules

## Migration from Legacy Pattern

### Before (Legacy)
```python
# manifest.json
{
  "module_id": "standard.document_processor",
  "dependencies": ["core.settings"]
}

# api.py
def register_routes(api_router):
    api_router.include_router(router)

async def initialize(app_context):
    # Manual initialization
    pass
```

### After (Decorator Pattern)
```python
# api.py only
@register_service("standard.document_processor.service")
@provides_api_endpoints(router_name="router", prefix="/api/v1/docs")
class DocumentProcessorModule(DataIntegrityModule):
    MODULE_ID = "standard.document_processor"
    MODULE_DEPENDENCIES = ["core.settings"]
```

## Best Practices

### 1. Use Descriptive Service Names
```python
# Good
@register_service("standard.document_processor.service")

# Bad  
@register_service("doc_proc")
```

### 2. Set Appropriate Priorities
```python
# Core infrastructure
@register_service("core.database.service", priority=0)

# Application services (most modules)
@register_service("standard.my_module.service", priority=100)
```

### 3. Declare Dependencies
```python
class MyModule(DataIntegrityModule):
    MODULE_DEPENDENCIES = ["core.settings", "core.database"]
```

### 4. Use Consistent Prefixes
```python
# Good - versioned API
@provides_api_endpoints(router_name="router", prefix="/api/v1/docs")

# Good - no prefix for simple modules
@provides_api_endpoints(router_name="router")
```

### 5. Enable Data Integrity
```python
# Always enable for production modules
@enforce_data_integrity(strict_mode=True, anti_mock=True)
```

### 6. Set Reasonable Health Check Intervals
```python
# Every 5 minutes for most modules
@module_health_check(interval=300)

# More frequent for critical services
@module_health_check(interval=60)
```

## Benefits of Decorator Pattern

### 1. **Single Source of Truth**
- All module metadata in one place
- No separate manifest files to maintain
- Compile-time validation

### 2. **Automatic Processing** 
- Framework handles all registration
- No manual route setup
- No manual service registration

### 3. **Clean Code**
- Declarative module definition
- Clear separation of concerns
- Reduced boilerplate

### 4. **Better Error Handling**
- Early validation of decorator parameters
- Clear error messages
- Dependency checking

### 5. **Enhanced Maintainability**
- Easy to see module configuration
- Centralized logic in framework
- Consistent patterns across modules

The decorator pattern provides a powerful, clean way to define modules while maintaining all the flexibility of the underlying framework systems.
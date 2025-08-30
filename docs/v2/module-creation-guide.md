# Module Creation Guide

**Version: v3.0.0**  
**Updated: August 10, 2025**

## Quick Start

### 1. Use the Scaffolding Tool
```bash
python tools/scaffold_module.py --name my_module --type standard --features database,api,settings
```

### 2. Customize the Generated Module
The tool creates a complete module structure - you just need to customize the business logic.

### 3. Test and Validate
```bash
python tools/compliance/compliance.py validate --module standard.my_module
python app.py  # Test integration
```

## Manual Module Creation

If you prefer to create modules manually or want to understand the structure:

### Step 1: Create Directory Structure

```bash
mkdir -p modules/standard/my_module
cd modules/standard/my_module
```

Create these files:
```
modules/standard/my_module/
├── api.py                    # Module entry point with decorators
├── services.py              # Business logic
├── module_settings.py       # Configuration schema
├── db_models.py             # Database models (optional)
├── api_schemas.py           # Pydantic models (optional)
└── readme.md                # Module documentation
```

### Step 2: Create the Module Entry Point

**`api.py`** - The heart of your module:

```python
"""
modules/standard/my_module/api.py
Module entry point for My Module
"""

import logging
from fastapi import APIRouter, Depends
from typing import Optional

# Import framework decorators
from core.decorators import (
    register_service,
    provides_api_endpoints,
    enforce_data_integrity,
    module_health_check
)
from core.module_base import DataIntegrityModule
from core.error_utils import Result, create_error_response

# Import module components
from .services import MyModuleService
from .module_settings import get_settings, MyModuleSettings

# Module logger
logger = logging.getLogger("standard.my_module")

# API Router
router = APIRouter()

# IMPORTANT: All endpoints must have response_model for OpenAPI compliance
from .api_schemas import StatusResponse, InfoResponse

@router.get("/status", response_model=StatusResponse)
async def get_status():
    """Get module status - REQUIRED for UI service detection."""
    service = get_service()
    if not service:
        raise create_error_response(
            "SERVICE_NOT_AVAILABLE", 
            "My Module service not available",
            status_code=503
        )
    
    return {"status": "active", "module": "my_module"}

@router.get("/info", response_model=InfoResponse)
async def get_info():
    """Get module information - REQUIRED for UI integration."""
    return {
        "name": "my_module",
        "version": "1.0.0",
        "description": "My module description"
    }

@router.post("/process")
async def process_data(data: dict):
    """Process some data."""
    service = get_service()
    if not service:
        raise create_error_response(
            "SERVICE_NOT_AVAILABLE",
            "My Module service not available",
            status_code=503
        )
    
    result = await service.process(data)
    if not result.success:
        raise create_error_response(
            result.error["code"],
            result.error["message"],
            status_code=400
        )
    
    return {"status": "processed", "result": result.data}

# Module registration with decorators
@register_service("standard.my_module.service", priority=100)
@provides_api_endpoints(router_name="router", prefix="/api/v1/my-module")
@enforce_data_integrity(strict_mode=True, anti_mock=True)
@module_health_check(interval=300)
class MyModule(DataIntegrityModule):
    """
    My Module
    
    Description of what this module does.
    """
    
    # Required module constants
    MODULE_ID = "standard.my_module"
    MODULE_NAME = "My Module"
    MODULE_DEPENDENCIES = ["core.settings"]  # Add dependencies as needed
    MODULE_ENTRY_POINT = "api.py"
    
    # Optional constants
    MODULE_VERSION = "1.0.0"
    MODULE_DESCRIPTION = "My module description"
    MODULE_AUTHOR = "Your Name"
    
    def __init__(self):
        """Phase 1: Light initialization only."""
        logger.info(f"{self.MODULE_ID} created with decorator-based registration")
        
        # Initialize service (light initialization)
        self.my_service = MyModuleService()
        
        # Store service globally for API access
        global my_module_service
        my_module_service = self.my_service
        
        logger.info(f"{self.MODULE_ID} Phase 1 initialization complete")
    
    async def initialize(self, app_context):
        """Phase 2: Complex initialization."""
        logger.info(f"Initializing {self.MODULE_ID} (Phase 2)")
        
        try:
            # Get module settings
            settings = get_settings()
            
            # Pass app_context and settings to service for Phase 2 setup
            success = await self.my_service.initialize(app_context, settings)
            
            if success:
                logger.info(f"{self.MODULE_ID} Phase 2 initialization complete")
            else:
                logger.error(f"{self.MODULE_ID} Phase 2 initialization failed")
            
            return success
            
        except Exception as e:
            logger.error(f"Error initializing {self.MODULE_ID}: {str(e)}")
            return False

# Global service access for API routes
my_module_service: Optional[MyModuleService] = None

def get_service() -> Optional[MyModuleService]:
    """Get the module service instance."""
    return my_module_service
```

### Step 3: Implement Business Logic

**`services.py`** - Your module's core functionality:

```python
"""
modules/standard/my_module/services.py
Business logic for My Module
"""

import logging
import asyncio
from typing import Dict, Any, Optional

from core.error_utils import Result, error_message

# Module identity
MODULE_ID = "standard.my_module"
logger = logging.getLogger(MODULE_ID)

class MyModuleService:
    """
    Service class for My Module.
    
    Implements the core business logic and operations.
    """
    
    def __init__(self):
        """Initialize service (Phase 1 - light initialization only)."""
        self.initialized = False
        self.settings = None
        self.app_context = None
        logger.info(f"{MODULE_ID} service created")
    
    async def initialize(self, app_context, settings) -> bool:
        """
        Phase 2 initialization.
        
        Args:
            app_context: Application context for accessing services
            settings: Module settings
            
        Returns:
            bool: True if initialization successful
        """
        if self.initialized:
            return True
        
        logger.info(f"Initializing {MODULE_ID} service")
        
        try:
            # Store context and settings
            self.app_context = app_context
            self.settings = settings
            
            # Get required services
            # settings_service = app_context.get_service("core.settings.service")
            # database_service = app_context.get_service("core.database.service")
            
            # Perform complex initialization here
            await self._setup_resources()
            await self._validate_configuration()
            
            self.initialized = True
            logger.info(f"{MODULE_ID} service initialization complete")
            return True
            
        except Exception as e:
            logger.error(error_message(
                MODULE_ID,
                "INITIALIZATION_FAILED",
                f"Failed to initialize service: {str(e)}",
                "initialize()"
            ))
            return False
    
    async def _setup_resources(self):
        """Set up module resources (databases, connections, etc.)."""
        # Example: Initialize database connections
        # Example: Set up external API clients
        # Example: Create working directories
        pass
    
    async def _validate_configuration(self):
        """Validate module configuration."""
        # Example: Check required settings
        # Example: Test external connections
        # Example: Validate file permissions
        pass
    
    async def get_status(self) -> Result:
        """
        Get module status.
        
        Returns:
            Result: Status information
        """
        if not self.initialized:
            return Result.error(
                "SERVICE_NOT_INITIALIZED",
                "Service not initialized"
            )
        
        try:
            status = {
                "module": MODULE_ID,
                "status": "running",
                "initialized": self.initialized,
                "settings_loaded": self.settings is not None
            }
            
            return Result.success(data=status)
            
        except Exception as e:
            logger.error(error_message(
                MODULE_ID,
                "STATUS_CHECK_FAILED",
                f"Failed to get status: {str(e)}",
                "get_status()"
            ))
            return Result.error(
                "STATUS_CHECK_FAILED",
                "Failed to get module status"
            )
    
    async def process(self, data: Dict[str, Any]) -> Result:
        """
        Process some data.
        
        Args:
            data: Data to process
            
        Returns:
            Result: Processing result
        """
        if not self.initialized:
            return Result.error(
                "SERVICE_NOT_INITIALIZED",
                "Service not initialized"
            )
        
        try:
            # Validate input
            if not data:
                return Result.error(
                    "INVALID_INPUT",
                    "No data provided"
                )
            
            # Process the data (implement your logic here)
            result = {
                "processed": True,
                "input_keys": list(data.keys()),
                "timestamp": "2025-08-10T10:00:00Z"  # Use actual timestamp
            }
            
            logger.info(f"Processed data with {len(data)} keys")
            return Result.success(data=result)
            
        except Exception as e:
            logger.error(error_message(
                MODULE_ID,
                "PROCESSING_FAILED",
                f"Failed to process data: {str(e)}",
                "process()"
            ))
            return Result.error(
                "PROCESSING_FAILED",
                "Failed to process data"
            )
    
    async def shutdown(self):
        """Graceful shutdown of the service."""
        logger.info(f"Shutting down {MODULE_ID} service")
        
        try:
            # Clean up resources
            await self._cleanup_resources()
            
            self.initialized = False
            logger.info(f"{MODULE_ID} service shutdown complete")
            
        except Exception as e:
            logger.error(f"Error during {MODULE_ID} shutdown: {str(e)}")
    
    async def _cleanup_resources(self):
        """Clean up module resources."""
        # Example: Close database connections
        # Example: Clean up temporary files
        # Example: Cancel background tasks
        pass
```

### Step 4: Define Configuration

**`module_settings.py`** - Configuration schema and defaults:

```python
"""
modules/standard/my_module/module_settings.py
Configuration schema for My Module
"""

from pydantic import BaseSettings, Field
from typing import Optional, List

class MyModuleSettings(BaseSettings):
    """Settings for My Module."""
    
    # Required settings
    api_key: str = Field(..., description="API key for external service")
    
    # Optional settings with defaults
    timeout: int = Field(30, description="Request timeout in seconds")
    max_retries: int = Field(3, description="Maximum number of retries")
    batch_size: int = Field(100, description="Batch processing size")
    
    # Feature flags
    enable_caching: bool = Field(True, description="Enable response caching")
    enable_metrics: bool = Field(True, description="Enable metrics collection")
    
    # Lists and complex types
    allowed_sources: List[str] = Field(
        default=["internal", "external"], 
        description="Allowed data sources"
    )
    
    # Optional advanced settings
    worker_pool_size: Optional[int] = Field(
        None, 
        description="Worker pool size (None = auto-detect)"
    )
    
    class Config:
        env_prefix = "MY_MODULE_"  # Environment variables: MY_MODULE_API_KEY, etc.
        env_file = ".env"
        case_sensitive = False

def get_settings() -> MyModuleSettings:
    """Get module settings instance."""
    return MyModuleSettings()

def register_settings(app_context) -> bool:
    """
    Register settings with the framework.
    
    Args:
        app_context: Application context
        
    Returns:
        bool: True if registration successful
    """
    try:
        # Get settings service
        settings_service = app_context.get_service("core.settings.service")
        if not settings_service:
            return False
        
        # Register module settings
        success = settings_service.register_module_settings(
            module_id="standard.my_module",
            settings_class=MyModuleSettings,
            version="1.0.0"
        )
        
        return success
        
    except Exception:
        return False
```

### Step 5: Add Database Models (Optional)

**`db_models.py`** - Database schema (if your module needs a database):

```python
"""
modules/standard/my_module/db_models.py
Database models for My Module
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from core.database.db_models_util import get_database_base

# Important: This constant is required for automatic database discovery
DATABASE_NAME = "my_module"

# Get the database base for this module
MyModuleBase = get_database_base(DATABASE_NAME)

class ProcessedItem(MyModuleBase):
    """Stores processed items."""
    __tablename__ = "processed_items"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    content = Column(Text)
    processed_at = Column(DateTime, default=datetime.now)
    status = Column(String(50), default="pending")
    is_active = Column(Boolean, default=True)
    
    # Relationships
    results = relationship("ProcessingResult", back_populates="item", cascade="all, delete-orphan")

class ProcessingResult(MyModuleBase):
    """Stores processing results."""
    __tablename__ = "processing_results"
    
    id = Column(Integer, primary_key=True)
    item_id = Column(Integer, ForeignKey("processed_items.id"), nullable=False)
    result_data = Column(Text)
    created_at = Column(DateTime, default=datetime.now)
    
    # Relationships
    item = relationship("ProcessedItem", back_populates="results")
```

### Step 6: Add API Schemas (Optional)

**`api_schemas.py`** - Pydantic models for API validation:

```python
"""
modules/standard/my_module/api_schemas.py
API request/response schemas for My Module
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

# Request schemas
class ProcessDataRequest(BaseModel):
    """Request schema for processing data."""
    
    data: Dict[str, Any] = Field(..., description="Data to process")
    options: Optional[Dict[str, str]] = Field(None, description="Processing options")
    priority: int = Field(1, ge=1, le=5, description="Processing priority (1-5)")

class ItemCreateRequest(BaseModel):
    """Request schema for creating items."""
    
    name: str = Field(..., min_length=1, max_length=200, description="Item name")
    content: Optional[str] = Field(None, description="Item content")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Item metadata")

# Response schemas
class StatusResponse(BaseModel):
    """Standard status endpoint response - REQUIRED for all modules."""
    status: str = Field(..., description="Module status")
    module: str = Field(..., description="Module name")
    
    model_config = {
        "json_schema_extra": {
            "example": {"status": "active", "module": "my_module"}
        }
    }

class InfoResponse(BaseModel):
    """Standard info endpoint response - REQUIRED for all modules."""
    name: str = Field(..., description="Module name")
    version: str = Field(..., description="Module version") 
    description: str = Field(..., description="Module description")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "my_module",
                "version": "1.0.0",
                "description": "My module description"
            }
        }
    }

class ProcessDataResponse(BaseModel):
    """Response schema for process endpoint."""
    status: str = Field(..., description="Processing status")
    result: Dict[str, Any] = Field(..., description="Processing result")
    processed_at: datetime = Field(default_factory=datetime.now, description="Processing timestamp")

class ItemResponse(BaseModel):
    """Response schema for item data."""
    
    id: int
    name: str
    content: Optional[str]
    processed_at: datetime
    status: str
    is_active: bool

class ItemListResponse(BaseModel):
    """Response schema for item lists."""
    
    items: List[ItemResponse]
    total_count: int
    page: int
    per_page: int

# Error schemas
class ErrorResponse(BaseModel):
    """Standard error response schema."""
    
    status: str = "error"
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None
```

### Step 7: Create Documentation

**`readme.md`** - Module documentation:

```markdown
# My Module

**Version: 1.0.0**  
**Type: Standard Module**  
**Dependencies**: core.settings

## Purpose

Brief description of what this module does and why it exists.

## Features

- Feature 1: Description
- Feature 2: Description
- Feature 3: Description

## Configuration

### Environment Variables

- `MY_MODULE_API_KEY`: API key for external service (required)
- `MY_MODULE_TIMEOUT`: Request timeout in seconds (default: 30)
- `MY_MODULE_MAX_RETRIES`: Maximum retries (default: 3)

### Settings

See `module_settings.py` for complete configuration options.

## API Endpoints

### GET /api/v1/my-module/status
Get module status.

**Response:**
```json
{
  "module": "standard.my_module",
  "status": "running",
  "initialized": true,
  "settings_loaded": true
}
```

### POST /api/v1/my-module/process
Process data.

**Request:**
```json
{
  "data": {"key": "value"},
  "priority": 1
}
```

**Response:**
```json
{
  "status": "processed",
  "result": {"processed": true},
  "processed_at": "2025-08-10T10:00:00Z"
}
```

## Database Schema

### Tables

- `processed_items`: Stores items for processing
- `processing_results`: Stores processing results

### Relationships

- One ProcessedItem can have many ProcessingResults

## Development

### Testing
```bash
python tools/compliance/compliance.py validate --module standard.my_module
```

### Deployment
Module is automatically discovered and loaded by the framework.
```

## Testing Your Module

### 1. Validate Compliance
```bash
python tools/compliance/compliance.py validate --module standard.my_module
```

### 2. Test Framework Integration
```bash
python app.py
```

Check the logs for:
- Module discovery
- Service registration  
- API endpoint registration
- Database creation (if using databases)
- Initialization success

### 3. Test API Endpoints
```bash
# Check module status
curl -X GET "http://localhost:8000/api/v1/my-module/status"

# Test processing
curl -X POST "http://localhost:8000/api/v1/my-module/process" \
     -H "Content-Type: application/json" \
     -d '{"data": {"test": "value"}, "priority": 1}'
```

### 4. Check Health Monitoring
The framework automatically monitors your module's health every 300 seconds (or your configured interval).

## Common Patterns

### Database Operations
```python
# In services.py
async def get_items(self, limit: int = 100) -> Result:
    try:
        database_service = self.app_context.get_service("core.database.service")
        session_factory = database_service.get_database_session("my_module")
        
        async with session_factory() as session:
            # Database operations here
            items = await session.execute(select(ProcessedItem).limit(limit))
            return Result.success(data=items.scalars().all())
            
    except Exception as e:
        logger.error(error_message(MODULE_ID, "DATABASE_ERROR", str(e)))
        return Result.error("DATABASE_ERROR", "Failed to get items")
```

### Service Dependencies
```python
# In services.py initialize() method
settings_service = app_context.get_service("core.settings.service")
database_service = app_context.get_service("core.database.service")
other_service = app_context.get_service("standard.other_module.service")
```

### Background Tasks
```python
# In services.py
async def _setup_resources(self):
    # Create background task
    self._background_task = asyncio.create_task(self._periodic_cleanup())

async def _periodic_cleanup(self):
    while self.initialized:
        try:
            # Cleanup logic
            await asyncio.sleep(3600)  # Run hourly
        except asyncio.CancelledError:
            break

async def shutdown(self):
    if hasattr(self, '_background_task'):
        self._background_task.cancel()
        try:
            await self._background_task
        except asyncio.CancelledError:
            pass
```

## Module Lifecycle

1. **Discovery**: Framework finds module with decorators
2. **Registration**: Decorators processed, services registered
3. **Phase 1 Init**: Module `__init__()` called (light setup)
4. **Phase 2 Init**: Module `initialize()` called (complex setup)  
5. **Running**: Module serves requests and performs work
6. **Shutdown**: Module `shutdown()` called (cleanup)

## Best Practices

### Do:
- ✅ Use the Result pattern for all service methods
- ✅ Implement proper error handling and logging
- ✅ Validate input data in API endpoints
- ✅ Use environment variables for configuration
- ✅ Write documentation and tests
- ✅ Follow the two-phase initialization pattern

### Don't:
- ❌ Perform complex operations in `__init__()`
- ❌ Skip error handling in service methods
- ❌ Hardcode configuration values
- ❌ Import framework modules in global scope unnecessarily
- ❌ Forget to handle service dependencies

Your module is now ready to be integrated into the Modular Framework!
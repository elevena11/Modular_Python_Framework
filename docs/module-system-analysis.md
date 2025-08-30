# Module System Analysis - Loading and Manifest Patterns

## Overview

The Modular Framework uses a manifest-based module system with two-phase initialization, dependency resolution, and service registration patterns.

**Location**: Module definitions in `modules/`

## Module Structure Pattern

### Standard Module Directory Layout
```
modules/
├── core/                    # Core framework modules
│   ├── database/
│   │   ├── manifest.json   # Module metadata
│   │   ├── api.py         # Entry point with initialize() function
│   │   ├── services.py    # Business logic services
│   │   ├── db_models.py   # Database schema (if needed)
│   │   └── utils.py       # Helper functions
│   └── settings/
└── standard/               # Application-specific modules
    ├── data_collector/
    ├── data_analyzer/
    ├── notification_system/
    └── user_interface/
```

## Manifest.json Pattern

### Core Module Examples

**core.database manifest**:
```json
{
  "id": "database",
  "name": "Database",
  "version": "1.1.0",
  "description": "Core database module with SQLite support, two-phase initialization",
  "author": "Modular Framework",
  "dependencies": [],
  "requirements": ["sqlalchemy>=2.0.0", "aiosqlite>=0.18.0"]
}
```

**core.settings manifest**:
```json
{
  "id": "settings",
  "name": "Settings Manager", 
  "version": "1.1.0",
  "description": "Core settings management functionality",
  "author": "Modular Framework",
  "dependencies": ["core.database"],
  "entry_point": "api.py"
}
```

### Manifest Schema Definition
```json
{
  "id": "string",                    // Short identifier (used in dependencies)
  "name": "string",                  // Display name  
  "version": "string",               // Semantic version
  "description": "string",           // Module description
  "author": "string",                // Author information
  "dependencies": ["array"],         // Other modules this depends on
  "entry_point": "string",          // Main file (defaults to api.py)
  "requirements": ["array"]          // Python package dependencies
}
```

## Module Loading Sequence

### 1. Discovery Phase
```python
# module_loader.py scans for modules
modules_found = []
for module_dir in ["modules/core", "modules/standard"]:
    for subdir in os.listdir(module_dir):
        manifest_path = f"{module_dir}/{subdir}/manifest.json"
        if os.path.exists(manifest_path):
            modules_found.append(load_manifest(manifest_path))
```

### 2. Dependency Resolution
```python
# Sort modules by dependencies (topological sort)
# core.database loads first (no dependencies)
# core.settings loads after core.database
# other modules load after their dependencies
```

### 3. Two-Phase Loading

**Phase 1: Service Registration**
- Load module's entry point file (api.py)
- Call `initialize(app_context)` function
- Register services in app_context
- Register database models (if any)
- NO database operations allowed

**Phase 2: Complex Initialization**  
- Call registered setup hooks
- Database operations allowed
- Inter-module communication
- Complete service initialization

## Entry Point Pattern (api.py)

### Required Functions

**1. initialize() - Phase 1**
```python
async def initialize(app_context):
    """
    Phase 1: Initialize the module.
    Register services and hooks only - NO database operations.
    """
    global module_service
    
    logger.info(f"Initializing {MODULE_ID} module (Phase 1)")
    
    try:
        # Create module service
        module_service = CryptoDataCollectorService(app_context)
        
        # Register service with FULL module name
        app_context.register_service(f"{MODULE_ID}.service", module_service)
        
        # Register database models (if needed)
        from .db_models import DataRecord, ProcessedData
        app_context.register_models([DataRecord, ProcessedData], database="example_module")
        
        # Register for Phase 2 initialization
        app_context.register_module_setup_hook(
            module_id=MODULE_ID,
            setup_method=setup_module,
            priority=20
        )
        
        # Register module settings
        await register_module_settings(app_context)
        
        logger.info(f"{MODULE_ID} module Phase 1 initialization complete")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize {MODULE_ID}: {str(e)}")
        return False
```

**2. setup_module() - Phase 2**
```python
async def setup_module(app_context):
    """
    Phase 2: Complete module initialization.
    Now it's safe to perform database operations.
    """
    global module_service
    
    logger.info(f"Starting {MODULE_ID} Phase 2 initialization")
    
    try:
        # Initialize service with database operations
        if module_service:
            success = await module_service.initialize(app_context)
            if not success:
                return False
        
        # Get database utilities
        db_service = app_context.get_service("core.database.service")
        if db_service:
            # Create module-specific database
            db_url = db_service.get_database_url("example_module")
            engines = db_service.create_database_engine("example_module", db_url)
            
            # Store engines in service
            module_service.set_database_engines(engines)
            
            # Create tables
            async with engines["engine"].begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
        
        logger.info(f"{MODULE_ID} module Phase 2 initialization complete")
        return True
    except Exception as e:
        logger.error(f"Error during {MODULE_ID} Phase 2 initialization: {str(e)}")
        return False
```

**3. register_routes() - Optional**
```python
def register_routes(api_router):
    """Register module routes."""
    logger.info(f"Registering {MODULE_ID} routes")
    api_router.include_router(router)
```

**4. register_ui_components() - Optional**
```python
def register_ui_components(ui_context):
    """Register UI components."""
    from . import ui
    ui.register_components(ui_context)
```

## Service Registration Pattern

### Naming Convention Issue
**Critical Distinction**: Manifest `id` vs Service Registry name

- **Manifest id**: Short name (`"database"`, `"settings"`)
- **Service registry**: Full name (`"core.database.service"`, `"core.settings.service"`)

```python
# In manifest.json
{"id": "database"}

# In dependencies array  
{"dependencies": ["core.database"]}

# In service registration
app_context.register_service("core.database.service", database_service)

# In service access
db_service = app_context.get_service("core.database.service")
```

### Service Access Pattern
```python
# Getting services from other modules
settings_service = app_context.get_service("core.settings.service")
database_service = app_context.get_service("core.database.service")
error_handler = app_context.get_service("core.error_handler.service")

# Via app_context convenience methods (recommended)
settings = await app_context.get_module_settings("module_id")
```

## Application Module Template

### Example: example_module/manifest.json
```json
{
  "id": "example_module",
  "name": "Example Data Module",
  "version": "1.0.0", 
  "description": "Processes and analyzes data from external sources",
  "author": "Application Team",
  "dependencies": ["core.database", "core.settings"],
  "entry_point": "api.py",
  "requirements": [
    "aiohttp>=3.8.0",
    "pandas>=1.5.0",
    "requests>=2.28.0"
  ]
}
```

### Example: example_module/api.py Structure
```python
"""
modules/standard/example_module/api.py
Entry point for example data processing module
"""

import logging
import traceback
from fastapi import APIRouter

# Import module components
from .services import ExampleModuleService
from .db_models import DataRecord, ProcessedData
from modules.core.error_handler.utils import error_message

# Define MODULE_ID matching directory structure
MODULE_ID = "standard.example_module"
logger = logging.getLogger(MODULE_ID)

# Initialize module-level variables
data_service = None

async def initialize(app_context):
    """Phase 1: Register services and models"""
    # Implementation as shown above
    
async def setup_module(app_context):
    """Phase 2: Complete initialization with database operations"""
    # Implementation as shown above

def register_routes(api_router):
    """Register API routes"""
    # Implementation as shown above
```

## Bootstrap Dependencies

### Special Priority Modules
1. **core.database** - Always loads first (priority 0)
2. **core.error_handler** - Uses direct imports, depends only on database

### Error Handler Special Case
```python
# error_handler uses direct imports instead of service registry
from modules.core.database.db_models import get_database_base
from modules.core.database.utils import execute_with_retry

# Other modules use service registry
database_service = app_context.get_service("core.database.service")
```

## Module Dependencies Graph

```
core.database (priority 0)
├── core.error_handler (priority 5)  
├── core.settings (priority 10)
│   └── core.scheduler (priority 20)
└── standard.* (priority 20+)
    ├── standard.data_collector
    ├── standard.data_analyzer  
    │   └── depends on data_collector
    ├── standard.notification_system
    │   └── depends on data_analyzer
    └── standard.user_interface
        └── depends on notification_system
```

## Key Integration Points

### For New Application Modules

1. **Create manifest.json** with proper dependencies
2. **Implement api.py** with initialize() and setup_module()
3. **Define db_models.py** if database needed
4. **Create services.py** with business logic
5. **Register with proper naming convention**
6. **Use service registry for inter-module communication**

This module system provides a robust, dependency-aware loading mechanism for building modular applications on the framework.
# Core Framework Components Analysis

## Overview

Analysis of the `/core/` directory components that form the foundation of the Framework framework.

**Location**: `core/`

## Core Components

### 1. app_context.py
**Purpose**: Central application context and service registry for the entire framework

**Key Class**: `AppContext` - Shared application state and service container

**Core Responsibilities**:
- **Service Registration & Discovery**: Central registry for all module services
- **Database Management**: SQLite engine and session management  
- **Configuration Integration**: Settings management through core.settings service
- **Lifecycle Management**: Post-initialization hooks, shutdown handlers
- **Session Tracking**: Unique session IDs and application state

**Database Integration**:
- Creates async SQLite engine and session factory
- Provides database connection pooling and retry logic
- Supports database directory auto-creation
- Handles database URL resolution from config

**Service Registry Pattern**:
```python
# Service Registration (by modules)
app_context.register_service("core.database", database_service)
app_context.register_service("standard.crypto_data_collector", collector_service)

# Service Access (by other modules)  
db_service = app_context.get_service("core.database")
collector = app_context.get_service("standard.crypto_data_collector")
```

**Post-Initialization Hooks**:
- Allows modules to register complex setup after all modules load
- Dependency-aware hook execution (with priorities)
- Used for Phase 2 initialization pattern

**Settings Integration**:
- Async settings management through core.settings service
- Module settings registration and retrieval
- Settings validation and UI metadata support
- Settings migrations between versions

**Crypto Integration**:
- Our crypto modules will register services: `standard.crypto_data_collector`, etc.
- Access database service: `app_context.get_service("core.database")`
- Register settings: `await app_context.register_module_settings(module_id, defaults)`
- Use post-init hooks for complex database setup

---

### 2. module_loader.py  
**Purpose**: Module discovery, loading, and lifecycle management

**Key Classes**:
- `ModuleLoader` - Main class for module management

**Key Responsibilities**:
- **Module Discovery**: Searches `modules/core/`, `modules/standard/`, `modules/extensions/` 
- **Dependency Resolution**: Topological sort for load order
- **Two-Phase Initialization**: Phase 1 (service registration), Phase 2 (complex operations)
- **Async Loading**: Fully async module loading pattern
- **Error Handling**: Comprehensive logging and error tracking
- **Auto-Install**: Can automatically install missing dependencies

**Module Discovery Process**:
1. Scans module directories for `manifest.json` files
2. Skips modules with `.disabled` files  
3. Builds module ID: `{module_type}.{manifest_id}` where:
   - `module_type` = directory name (`core`, `standard`, `extensions`)
   - `manifest_id` = the `"id"` field from `manifest.json`
   - Example: `core.database` (from `modules/core/database/` + `"id": "database"`)
4. Supports one level of nesting: `{module_type}.{group}.{manifest_id}`

**Important**: In `manifest.json`, the `"id"` field should NOT include the module type prefix. The framework adds `core.`, `standard.`, etc. automatically based on the directory structure.

**⚠️ Critical Service Access Pattern**:
- **Manifest ID**: `"id": "database"` (no prefix)
- **Module Registration**: Framework registers as `core.database`
- **Service Access**: Must use full name `core.database` or `core.database.services`

```python
# In crypto module, accessing database services:
database_service = app_context.get_service("core.database")
# OR
database_service = app_context.get_service("core.database.services")
```

**Dependency System**:
- Uses topological sort to resolve dependencies
- **Special Priority Handling**:
  - `core.database` gets highest priority - loads first, before all other modules
  - All `core.*` modules load before `standard.*` and `extensions.*` 
  - If `core.database` fails to load, entire application aborts
- Detects circular dependencies
- Continues loading if non-core modules fail

**Actual Startup Sequence** (from `/home/dnt242/github/framework/data/logs/app.log`):
1. **App Context Initialize** - Database engine, session factory created
2. **core.database** - Special priority, loads first
3. **core.settings** - Loads second (needed by other modules for configuration)
4. **core.error_handler** - Direct import pattern, uses `core.database` only
5. **Other core modules** - core.global, core.scheduler, core.model_manager
6. **Standard modules** - standard.llm_*, our crypto modules would load here
7. **Post-initialization hooks** - Phase 2 complex setup

**Error Handler Special Pattern**:
- Uses direct import for utilities: `from modules.core.error_handler.utils import Result, error_message`
- Only depends on `core.database` being active
- Available immediately for other modules via direct import
- Does NOT require service registry access for basic error handling

**Phase 2 Preparation**:
- After all modules complete Phase 1, framework runs post-initialization hooks
- All core services (`core.database`, `core.settings`, `core.error_handler`) fully available
- This ensures crypto modules can access all framework utilities during Phase 2

**Two-Phase Initialization**:
```python
# Phase 1 (during module loading)
async def initialize(app_context):
    # Register services, hooks, simple setup only
    pass

# Phase 2 (post-initialization hooks) 
# Complex database operations, external connections
```

**Module Requirements**:
- Must have `manifest.json` with module metadata
- Must have async `initialize(app_context)` function
- Can optionally have `register_routes(router)` function
- Can specify package requirements in manifest

**Crypto Integration Notes**:
- Our crypto modules will go in `modules/standard/crypto_*` (standard functionality, not extensions)
- Each module needs `manifest.json` with `"id"` field (e.g., `"id": "crypto_data_collector"`)
- Framework builds full ID: `standard.crypto_data_collector`
- Must implement `async def initialize(app_context)`
- Dependencies reference full IDs: `["core.database", "standard.crypto_data_collector"]`
- Dependency chain: `core.database` -> `standard.crypto_data_collector` -> `standard.crypto_analyzer` -> `standard.crypto_alerts` -> `standard.telegramBot`

---

### 3. config.py
**Purpose**: Framework configuration management

**File Analysis**:
```python
# Need to examine actual implementation  
```

**Key Responsibilities**:
- Framework-level configuration
- Environment variable handling
- Configuration validation
- Integration with core.settings module

**Crypto Integration**: Needs to handle crypto-specific framework settings

---

### 4. paths.py
**Purpose**: Path management and resolution

**File Analysis**:
```python
# Need to examine actual implementation
```

**Key Responsibilities**:
- Framework directory structure
- Module path resolution
- Data directory management
- Configuration file paths

**Crypto Integration**: Needs to handle crypto module paths and data directories

## Analysis Priority

1. **module_loader.py** - Critical for understanding how to create crypto modules
2. **app_context.py** - Essential for service registration and module integration
3. **paths.py** - Important for understanding directory structure
4. **config.py** - Needed for framework configuration

## Next Steps

1. Examine each file's actual implementation
2. Document key classes and methods
3. Identify integration points for crypto modules
4. Create usage examples for crypto project
# Bootstrap Phase - Framework Infrastructure Preparation

## Overview

The Bootstrap Phase is a dedicated pre-module initialization step that ensures all critical infrastructure is in place before any modules load. This phase handles "cold boot" scenarios where essential files, databases, or configurations need to be created from scratch.

## Philosophy

**Modules should "just work"** - they should never need special code to handle missing infrastructure or cold boot scenarios. The Bootstrap Phase ensures that when modules initialize, all their dependencies already exist.

## Bootstrap Phase Position in Startup Sequence

```
App Context Initialization
         ↓
    BOOTSTRAP PHASE  ← NEW PHASE
         ↓
    Module Discovery
         ↓
    Module Loading (Phase 1)
         ↓
    Module Initialization (Phase 2)
         ↓
    Application Ready
```

## Bootstrap Responsibilities

### 1. Database Infrastructure Bootstrap

**Problem Solved**: Modules need databases to exist before they can operate, but someone needs to create those databases initially.

**Bootstrap Action**:
- Scan all `modules/*/db_models.py` files for `DATABASE_NAME` declarations
- Create all SQLite database files with their required tables
- Close all connections (no handoff needed)

**Module Benefit**: Database modules can assume their target databases already exist as files and simply open connections.

### 2. Directory Structure Bootstrap

**Problem Solved**: Modules expect certain directories to exist (logs, data, cache, etc.).

**Bootstrap Action**:
- Create standard directory structure (`data/`, `logs/`, `cache/`, etc.)
- Create module-specific directories based on manifest requirements
- Set proper permissions

**Module Benefit**: Modules can write to directories without checking if they exist first.

### 3. Configuration Bootstrap

**Problem Solved**: Some modules need basic configuration files to exist before they can start.

**Bootstrap Action**:
- Create missing configuration files from templates
- Initialize default values for required settings
- Validate critical configuration consistency

**Module Benefit**: Modules can load configuration without handling missing file scenarios.

### 4. Dependency File Bootstrap

**Problem Solved**: Some modules depend on external files (models, assets, schemas) that need to be present.

**Bootstrap Action**:
- Download or create required dependency files
- Verify file integrity and versions
- Create placeholder files where appropriate

**Module Benefit**: Modules can access required files without download/creation logic.

## Bootstrap Implementation Architecture

### Location
- **Primary**: `core/bootstrap.py` - Main bootstrap orchestrator
- **Handlers**: `core/bootstrap/` - Specific bootstrap handlers for different concerns

### Integration Point
```python
# In app.py lifespan():
app_context = AppContext(settings)
app_context.initialize()           # Basic framework setup

await run_bootstrap_phase(app_context)  # ← NEW STEP

module_loader = ModuleLoader(app_context)
success, failed = await module_loader.load_modules()
```

### Bootstrap Handler Pattern
```python
class BootstrapHandler:
    """Base class for bootstrap handlers."""
    
    async def should_run(self, app_context) -> bool:
        """Check if this bootstrap step is needed."""
        pass
    
    async def execute(self, app_context) -> bool:
        """Perform the bootstrap action."""
        pass
    
    def get_priority(self) -> int:
        """Return execution priority (lower = earlier)."""
        return 100
```

### Specific Handlers

#### DatabaseBootstrapHandler
```python
class DatabaseBootstrapHandler(BootstrapHandler):
    async def should_run(self, app_context) -> bool:
        # Check if any required database files are missing
        discovered = self.discover_databases_from_models()
        return any(not os.path.exists(db_path) for db_path in discovered.keys())
    
    async def execute(self, app_context) -> bool:
        # 1. Discover all databases from db_models.py files
        # 2. Create missing SQLite files with tables
        # 3. Close all connections
        return True
    
    def get_priority(self) -> int:
        return 10  # Very high priority - databases needed by many things
```

#### DirectoryBootstrapHandler
```python
class DirectoryBootstrapHandler(BootstrapHandler):
    async def should_run(self, app_context) -> bool:
        required_dirs = ['data/logs', 'data/cache', 'data/temp']
        return any(not os.path.exists(d) for d in required_dirs)
    
    async def execute(self, app_context) -> bool:
        # Create missing directories
        return True
    
    def get_priority(self) -> int:
        return 5  # Highest priority - directories needed by logging etc.
```

## Bootstrap Execution Flow

### 1. Discovery Phase
```python
async def run_bootstrap_phase(app_context):
    handlers = discover_bootstrap_handlers()
    needed_handlers = []
    
    for handler in handlers:
        if await handler.should_run(app_context):
            needed_handlers.append(handler)
    
    if not needed_handlers:
        logger.info("Bootstrap phase: No bootstrap actions needed")
        return True
```

### 2. Execution Phase
```python
    # Sort by priority (lower number = higher priority)
    needed_handlers.sort(key=lambda h: h.get_priority())
    
    logger.info(f"Bootstrap phase: Running {len(needed_handlers)} bootstrap actions")
    
    for handler in needed_handlers:
        handler_name = handler.__class__.__name__
        logger.info(f"Bootstrap: Executing {handler_name}")
        
        success = await handler.execute(app_context)
        if not success:
            logger.error(f"Bootstrap: {handler_name} failed - aborting startup")
            return False
    
    logger.info("Bootstrap phase: All bootstrap actions completed successfully")
    return True
```

## Bootstrap Benefits

### For Framework
- **Clean Startup**: Clear separation between infrastructure setup and module logic
- **Reliability**: Handles cold boot scenarios consistently
- **Extensibility**: Easy to add new bootstrap concerns without touching modules
- **Debugging**: Bootstrap failures are isolated and clearly logged

### for Modules
- **Simplicity**: Modules assume their infrastructure exists
- **No Special Cases**: No need for "first run" or "cold boot" code paths
- **Consistent Environment**: All modules operate in a fully prepared environment
- **Focus**: Modules focus on their core functionality, not infrastructure setup

### For Development
- **Predictable**: Same environment every time, regardless of cold/warm boot
- **Testable**: Bootstrap can be tested independently of modules
- **Maintainable**: Infrastructure logic centralized, not scattered across modules

## Example: Database Bootstrap Implementation

### Current Problem
```python
# Database module currently has to handle:
def initialize(self):
    # Check if databases exist
    # If not, discover all modules' database needs
    # Create databases and tables
    # Then proceed with normal database operations
```

### After Bootstrap
```python
# Bootstrap phase handles database creation:
# - All SQLite files created before modules load
# - Tables created with proper schemas
# - Connections closed cleanly

# Database module becomes much simpler:
def initialize(self):
    # Just open connections to existing databases
    # No special cold boot logic needed
```

## Bootstrap Configuration

### Module Manifest Bootstrap Requirements
```json
{
  "id": "example.module",
  "bootstrap_requirements": {
    "directories": ["data/module_cache", "logs/module_logs"],
    "files": ["config/module_config.json"],
    "database": "module_database"
  }
}
```

### Bootstrap Settings
```python
# In framework settings
BOOTSTRAP_ENABLED = True
BOOTSTRAP_TIMEOUT = 30  # seconds
BOOTSTRAP_RETRY_ATTEMPTS = 3
BOOTSTRAP_FAIL_FAST = True  # Stop on first failure
```

## Future Bootstrap Extensions

The Bootstrap Phase architecture supports future extensions:

### Cache Bootstrap
- Pre-populate critical caches
- Download and prepare cached data
- Initialize cache directories with proper structure

### Network Bootstrap  
- Verify network connectivity to required services
- Download required external dependencies
- Initialize API client configurations

### Security Bootstrap
- Generate missing security certificates
- Initialize encryption keys
- Set up secure communication channels

### Performance Bootstrap
- Pre-compile frequently used templates
- Initialize performance monitoring
- Warm up critical code paths

## Bootstrap vs Phase 1 vs Phase 2

### Bootstrap Phase
- **Purpose**: Infrastructure preparation
- **Timing**: Before any modules load
- **Scope**: Framework-wide concerns
- **Failure**: Aborts application startup

### Module Phase 1 (Decorator Processing)
- **Purpose**: Service registration and metadata processing  
- **Timing**: During module loading
- **Scope**: Per-module registration
- **Failure**: Module excluded from application

### Module Phase 2 (Complex Initialization)
- **Purpose**: Business logic initialization
- **Timing**: After all modules loaded
- **Scope**: Per-module complex setup
- **Failure**: Module may have degraded functionality

## Implementation Priority

### Phase 1: Database Bootstrap (Critical)
- Implement `DatabaseBootstrapHandler`
- Integrate with existing discovery logic
- Test with current modules

### Phase 2: Directory Bootstrap (High Priority)  
- Implement `DirectoryBootstrapHandler`
- Cover standard framework directories
- Support module-specific directories

### Phase 3: Framework Integration (Medium Priority)
- Complete bootstrap orchestrator
- Add configuration support
- Add proper error handling and retry logic

### Phase 4: Extensions (Low Priority)
- Configuration bootstrap
- Cache bootstrap
- Network bootstrap

## Success Criteria

1. **Database Module Simplification**: Database module no longer needs discovery/creation logic
2. **Cold Boot Reliability**: Application starts successfully on completely fresh systems
3. **Module Simplification**: Other modules can assume infrastructure exists
4. **Clear Logging**: Bootstrap phase clearly logs what infrastructure it creates
5. **Fast Execution**: Bootstrap phase completes quickly (< 5 seconds typical)
6. **Extensible**: Easy to add new bootstrap handlers for future needs

---

This Bootstrap Phase represents a significant architectural improvement that will make the framework more reliable, modules simpler, and the entire system easier to maintain and extend.
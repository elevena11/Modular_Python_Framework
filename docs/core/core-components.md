# Core Components Reference

The `core/` directory contains the essential infrastructure that powers the Modular Python Framework. These components provide the foundation for module management, database operations, error handling, and application lifecycle.

## Core Files Overview

### Application Foundation

**`app_context.py`** - Application Context Manager
- **Purpose**: Shared application state and service registry
- **Key Features**: 
  - Service registration and discovery system
  - Database session management (integrity_session pattern)
  - Router collection and API endpoint registration
  - Unique session identification for logging and debugging
  - Shutdown handler coordination
- **Used By**: All modules for accessing services and shared resources

**`bootstrap.py`** - Database Bootstrap Phase
- **Purpose**: Standalone database creation before module loading
- **Key Features**:
  - Scans for `db_models.py` files using text parsing (no imports)
  - Extracts database names and creates SQLite databases
  - Independent from database module to avoid circular dependencies
  - Creates database structure before modules initialize
- **Architecture**: Self-contained logic that runs before any modules load

**`config.py`** - Framework Configuration
- **Purpose**: Centralized configuration using Pydantic BaseSettings
- **Key Features**:
  - Application settings (name, version, debug mode)
  - Network configuration (host, port, Streamlit port)
  - Project identification for multi-project deployments
  - Data directory configuration
- **Environment**: Supports environment variable overrides

### Module System

**`decorators.py`** - Decorator Registration System (MANDATORY-ALL-DECORATORS)
- **Purpose**: Centralized module registration using all mandatory decorators
- **Architecture**: ALL modules MUST have ALL all mandatory decorators in specified order
- **The 12 Mandatory Decorators**:
  1. `@inject_dependencies('app_context')` - Dependency injection
  2. `@register_service(...)` - Service registration with methods
  3. `@require_services([...])` - Service dependencies (empty list if none)
  4. `@initialization_sequence("setup_infrastructure", phase="phase1")` - Phase 1 setup
  5. `@phase2_operations("initialize_phase2")` - Phase 2 initialization
  6. `@auto_service_creation(service_class="...")` - Service instance creation
  7. `@register_api_endpoints(router_name="router")` - API route registration
  8. `@register_database(database_name=...)` - Database registration (None if no database)
  9. `@enforce_data_integrity(strict_mode=True, anti_mock=True)` - Integrity validation
  10. `@module_health_check(check_function=None)` - Health monitoring
  11. `@graceful_shutdown(method="cleanup_resources", timeout=30)` - Async cleanup
  12. `@force_shutdown(method="force_cleanup", timeout=5)` - Sync force cleanup
- **Philosophy**: Uniform processing, no configuration drift, predictable behavior

**`module_base.py`** - Base Module Classes
- **Purpose**: Foundation classes with built-in integrity enforcement
- **Classes**:
  - `DataIntegrityModule` - Base class for all modules
  - `DatabaseEnabledModule` - For modules requiring database access
- **Features**:
  - Mandatory data integrity validation
  - Anti-mock protection (hard failure enforcement)
  - Database integrity verification
  - Two-phase initialization support

**`module_manager.py`** - Module Discovery and Management
- **Purpose**: Discovers and manages module lifecycle
- **Key Features**:
  - Scans `modules/core/` and `modules/standard/` directories
  - Processes decorator metadata for registration
  - Manages module dependencies and initialization order
  - Coordinates two-phase initialization (registration → complex setup)

**`module_processor.py`** - Module Processing Engine
- **Purpose**: Processes modules through centralized processing pipeline
- **Processing Steps**:
  - Validate decorator metadata
  - Process dependencies
  - Store service metadata
  - Process Settings V2
  - Register databases/models
  - Register API endpoints
  - Setup health checks
  - Process shutdown metadata
  - Process dependency injection
  - Process initialization sequences
  - Process Phase 2 operations
  - Process auto service creation
  - Record success
- **Key Features**:
  - Uniform processing for all modules (all processing steps)
  - MODULE COMPLIANCE warnings for missing decorators
  - Phase 1: `setup_infrastructure()` for settings registration
  - Phase 2: `initialize_phase2()` for complex initialization
  - Error handling and rollback capabilities

### Database System

**`database.py`** - Database Infrastructure
- **Purpose**: Core database utilities and base classes
- **Key Features**:
  - `get_database_base()` - Creates SQLAlchemy Base for databases
  - Database path utilities and configuration
  - Integration with multi-database architecture
- **Pattern**: Used by modules to define their database models

### Error and Logging

**`error_utils.py`** - Result Pattern Implementation
- **Purpose**: Standardized error handling using Result pattern
- **Key Features**:
  - `Result.success()` and `Result.error()` for explicit error handling
  - Structured error responses with codes and details
  - API error response formatting
  - Replaces exceptions for business logic error handling

**`logging.py`** - Framework Logging System
- **Purpose**: Centralized logging configuration
- **Key Features**:
  - Structured logging with module identification
  - File and console output configuration
  - Log rotation and cleanup
  - Integration with framework session tracking

### Utilities

**`paths.py`** - Path Management
- **Purpose**: Consistent path handling across the framework
- **Key Functions**:
  - `get_framework_root()` - Framework root directory
  - `get_data_path()` - Data directory paths  
  - `get_module_data_path()` - Module-specific data directories
  - `ensure_data_path()` - Create directories if needed

## Architecture Patterns

### Two-Phase Initialization

1. **Phase 1: setup_infrastructure() (MANDATORY)**: Settings registration
   - ALL modules MUST register Pydantic settings models
   - NO access to other services (services don't exist yet)
   - Handled by `setup_infrastructure()` method
   - Synchronous only

   ```python
   def setup_infrastructure(self):
       """Phase 1: MANDATORY settings registration"""
       from .settings import MyModuleSettings
       self.app_context.register_pydantic_model(self.MODULE_ID, MyModuleSettings)
   ```

2. **Phase 2: initialize_phase2() (MANDATORY)**: Complex initialization
   - Full framework access - all services available
   - Database operations and external connections
   - Service dependencies available via `@require_services`
   - Handled by `initialize_phase2()` method
   - Async operations allowed

   ```python
   async def initialize_phase2(self):
       """Phase 2: Complex initialization with service access"""
       if self.service_instance:
           return await self.service_instance.initialize()
       return False
   ```

### Service Discovery System (MANDATORY-ALL-DECORATORS)

```python
# ALL modules must have ALL all mandatory decorators
@inject_dependencies('app_context')
@register_service("standard.my_module.service", methods=[...], priority=100)
@require_services([])  # Empty list if no external services
@initialization_sequence("setup_infrastructure", phase="phase1")
@phase2_operations("initialize_phase2")
@auto_service_creation(service_class="MyModuleService")
@register_api_endpoints(router_name="router")
@register_database(database_name=None)  # None if no database
@enforce_data_integrity(strict_mode=True, anti_mock=True)
@module_health_check(check_function=None)
@graceful_shutdown(method="cleanup_resources", timeout=30)
@force_shutdown(method="force_cleanup", timeout=5)
class MyModule(DataIntegrityModule):
    MODULE_ID = "standard.my_module"
    MODULE_VERSION = "1.0.0"
    MODULE_DESCRIPTION = "My application module"

# Other modules access via app_context
service = app_context.get_service("standard.my_module.service")
```

### Database Access Pattern

```python
# Current Phase 4 pattern - integrity_session
async with app_context.database.integrity_session("database_name", "purpose") as session:
    # Database operations with automatic lifecycle management
    result = await session.execute(query)
    await session.commit()
```

### Result Pattern Usage

```python
# Business logic uses Result pattern instead of exceptions
async def some_operation() -> Result:
    try:
        data = await process_something()
        return Result.success(data=data)
    except Exception as e:
        return Result.error("OPERATION_FAILED", str(e))
```

## Module Integration Flow

1. **Discovery**: `module_manager.py` scans for modules in `modules/` directories
2. **Load Decorators**: `decorators.py` processes ALL all mandatory decorators
3. **Validate Compliance**: Check all all mandatory decorators are present (MODULE COMPLIANCE warnings)
4. **Centralized Processing**: `module_processor.py` executes processing pipeline
5. **Phase 1 Execution**: Call `setup_infrastructure()` for settings registration
6. **Service Creation**: `@auto_service_creation` creates service instances
7. **Phase 2 Execution**: Call `initialize_phase2()` for complex initialization
8. **Runtime**: Services available via `app_context.get_service()`

**Success Indicator**: Module shows "processing completed" in logs

## Development Guidelines

### For Framework Development
- **Never modify core files casually** - They affect all modules
- **Test changes thoroughly** - Core changes impact entire framework
- **Maintain processing pipeline** - All modules must complete all processing steps
- **Follow mandatory-all-decorators** - No exceptions or special cases
- **Document architectural changes** - Core modifications need documentation

### For Application Development
- **ALWAYS use scaffolding tool** - `python tools/scaffold_module.py`
- **ALL all mandatory decorators required** - No skipping decorators (use None/empty for unused)
- **Use base classes** - `DataIntegrityModule` for all modules
- **Follow two-phase pattern**:
  - Phase 1: `setup_infrastructure()` for settings registration ONLY
  - Phase 2: `initialize_phase2()` for complex initialization
- **Use Result pattern** - For explicit error handling in business logic
- **Implement cleanup methods** - Both `cleanup_resources()` and `force_cleanup()`

The core system provides a solid, tested foundation with **mandatory-all-decorators architecture** that ensures consistent processing across all modules. The processing pipeline eliminates configuration drift and guarantees uniform behavior.
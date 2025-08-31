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

**`decorators.py`** - Decorator Registration System
- **Purpose**: Centralized module registration using decorators
- **Key Features**:
  - `@register_service` - Register services with automatic discovery
  - `@register_api_endpoints` - Automatic API route registration
  - `@enforce_data_integrity` - Data integrity validation
  - `@module_health_check` - Automatic health monitoring
  - Eliminates boilerplate registration code
- **Philosophy**: Single point of control for all module behavior

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
- **Purpose**: Processes modules through their lifecycle phases
- **Key Features**:
  - Phase 1: Infrastructure setup and service registration
  - Phase 2: Complex initialization with service dependencies
  - Error handling and rollback capabilities
  - Service instantiation and app_context integration

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

1. **Phase 1 (Registration)**: Infrastructure setup only
   - Services register with app_context
   - Settings schemas registered
   - No access to other services
   - Handled by `setup_infrastructure()` methods

2. **Phase 2 (Complex Operations)**: Full framework access  
   - Database operations and external connections
   - Service dependencies available
   - Handled by `initialize_service()` methods

### Service Discovery System

```python
# Services register via decorators
@register_service("module_name.service")
class MyModule(DataIntegrityModule):
    pass

# Other modules access via app_context
service = app_context.get_service("module_name.service")
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

1. **Discovery**: `module_manager.py` scans for modules
2. **Registration**: Decorators in `decorators.py` process module metadata
3. **Phase 1**: `module_processor.py` calls `setup_infrastructure()`
4. **Phase 2**: `module_processor.py` calls `initialize_service()`
5. **Runtime**: Services available via `app_context.get_service()`

## Development Guidelines

### For Framework Development
- **Never modify core files casually** - They affect all modules
- **Test changes thoroughly** - Core changes impact entire framework
- **Follow existing patterns** - Consistency is critical for infrastructure
- **Document architectural changes** - Core modifications need documentation

### For Application Development
- **Use base classes** - `DataIntegrityModule` for all custom modules  
- **Use decorators** - `@register_service` and `@register_api_endpoints`
- **Follow two-phase pattern** - Phase 1 for registration, Phase 2 for complex operations
- **Use Result pattern** - For explicit error handling in business logic

The core system provides a solid, tested foundation that handles the complex infrastructure so modules can focus on their specific functionality. The decorator-based registration system ensures consistency and eliminates common integration errors.
# Core Framework Directory

This directory contains the **core framework components** that power the Modular Framework v3.0.0. These files implement the fundamental infrastructure that all modules depend on.

## Core Files Overview

### Application Context & Service Container
- **`app_context.py`** - Central service container and application lifecycle management
  - Service registration and retrieval
  - Post-initialization hook system
  - Module setup coordination
  - Shutdown handler management

### Module System
- **`module_loader.py`** - Module discovery and loading
  - Scans for modules with decorator patterns
  - Loads modules in dependency order
  - Handles both decorator-based and legacy modules
  - Two-phase initialization orchestration

- **`module_processor.py`** - Centralized module processing (centralized registration)
  - Processes decorator metadata
  - Registers services, databases, and API endpoints
  - Sets up health checks and data integrity
  - Centralizes all module registration logic

- **`decorators.py`** - Module registration decorators
  - `@register_service` - Service container registration
  - `@provides_api_endpoints` - Automatic API route setup
  - `@enforce_data_integrity` - Data validation and anti-mock protection
  - `@module_health_check` - Automatic health monitoring

- **`module_base.py`** - Base classes for modules
  - `DataIntegrityModule` - Base with integrity validation
  - `DatabaseEnabledModule` - Base for database-enabled modules
  - Common module functionality and patterns

### Utilities
- **`error_utils.py`** - Pure error handling utilities (v3.0.0)
  - Result pattern for consistent error handling
  - Standardized error logging to JSONL files
  - HTTP error response creation
  - **Zero framework dependencies** - prevents circular imports

- **`paths.py`** - Path management utilities
  - Framework directory discovery
  - Data path management
  - Database and log path utilities
  - Cross-platform path handling

- **`logging.py`** - Framework logging configuration
  - Centralized logging setup
  - Module-aware log formatting
  - Log rotation and management

## Architecture Pattern

### Decorator-Based Registration
The core implements the **centralized registration** pattern:
1. **Module Discovery** (`module_loader.py`) - Find modules with decorators
2. **Decorator Processing** (`module_processor.py`) - Extract metadata from decorators
3. **Service Registration** (`app_context.py`) - Register services in container
4. **Two-Phase Init** (`module_loader.py`) - Phase 1 registration, Phase 2 complex setup

### Clean Separation
- **`error_utils.py`** - Pure utilities, no framework dependencies
- **Framework modules** - Use error_utils, never import each other
- **File-based communication** - JSONL logs prevent circular dependencies

## Key Design Principles

### 1. Single Point of Control
All module registration happens through centralized decorators and processors, eliminating the need for separate manifest files.

### 2. Two-Phase Initialization
- **Phase 1**: Fast registration (synchronous, cannot fail)
- **Phase 2**: Complex setup (asynchronous, priority-ordered, graceful failures)

### 3. Circular Dependency Prevention
- Pure utilities with zero framework dependencies
- File-based data flow where needed
- Clean separation between utilities and services

### 4. Service Container Pattern
Central registry for all services, with dependency injection and lifecycle management.

## Usage Examples

### Service Registration (decorators.py)
```python
from core.decorators import register_service, provides_api_endpoints

@register_service("my_module.service", priority=100)
@provides_api_endpoints(router_name="router", prefix="/api/v1")
class MyModule(DataIntegrityModule):
    pass
```

### Service Access (app_context.py)
```python
# In Phase 2 initialization
service = app_context.get_service("other_module.service")
```

### Error Handling (error_utils.py)
```python
from core.error_utils import Result, error_message

# Service method
def my_operation() -> Result:
    try:
        # Business logic
        return Result.success(data=result)
    except Exception as e:
        logger.error(error_message("my_module", "OPERATION_FAILED", str(e)))
        return Result.error("OPERATION_FAILED", "Operation failed")
```

### Path Management (paths.py)
```python
from core.paths import get_data_path, get_module_data_path

config_path = get_data_path("config", "settings.json")
module_db = get_module_data_path("my_module", "data.db")
```

## Dependencies

### External Dependencies
- **FastAPI** - Web framework and API routing
- **SQLAlchemy** - Database ORM and async support
- **Pydantic** - Data validation and settings management
- **asyncio** - Asynchronous programming support

### Internal Dependencies
- **Minimal coupling** - Core files avoid importing each other
- **Well-defined interfaces** - Clear contracts between components
- **Dependency injection** - Services accessed through app_context

## Development Guidelines

### Adding New Core Functionality
1. **Consider the separation of concerns** - utilities vs. framework services
2. **Avoid circular imports** - use file-based communication if needed
3. **Follow the service container pattern** - register services, don't import directly
4. **Maintain backward compatibility** - core changes affect all modules

### Modifying Existing Core Files
1. **Test thoroughly** - core changes affect the entire framework
2. **Update documentation** - especially if interfaces change
3. **Consider migration impact** - how will existing modules be affected?
4. **Maintain clean architecture** - don't introduce new dependencies

## Files You Probably Don't Need to Modify

Unless you're working on framework internals, most development happens in `modules/` directories. The core framework is designed to be stable and rarely requires changes:

- **`app_context.py`** - Stable service container
- **`module_loader.py`** - Mature module discovery
- **`decorators.py`** - Complete decorator set
- **`error_utils.py`** - Stable utility functions

## Files You Might Extend

- **`module_base.py`** - Add new base classes for specialized module types
- **`paths.py`** - Add new path utilities as needed
- **`decorators.py`** - Add new decorators for specialized functionality

The core framework provides a solid, stable foundation for building modular applications with clean architecture and reliable initialization patterns.
# Core Framework Directory

This directory contains the **core framework components** that power the Modular Framework v3.0.0. These files implement the fundamental infrastructure that all modules depend on.

## Core Files Overview

### Application Context & Service Container
- **`app_context.py`** - Central service container and application lifecycle management
  - Service registration and retrieval
  - Pydantic settings model registration
  - Post-initialization hook system
  - Module setup coordination
  - Shutdown handler management

### Module System
- **`module_manager.py`** - Module discovery and orchestration
  - Scans for modules with decorator patterns
  - Loads modules in dependency order
  - Handles decorator-based module registration
  - Two-phase initialization orchestration (Phase 1 → Phase 2)

- **`module_processor.py`** - Centralized module processing (14-step registration)
  - Processes decorator metadata from module classes
  - Registers services, databases, and API endpoints
  - Sets up health checks and data integrity enforcement
  - Executes Phase 1 initialization sequences
  - Registers Phase 2 operations and post-init hooks
  - Centralizes all module registration logic

- **`decorators.py`** - Module registration decorators (complete decorator system)
  - `@register_service` - Service container registration with method documentation
  - `@inject_dependencies` - Automatic dependency injection
  - `@initialization_sequence` - Phase 1 method registration (CRITICAL for settings)
  - `@phase2_operations` - Phase 2 method registration
  - `@auto_service_creation` - Automatic service instance creation
  - `@register_api_endpoints` - Automatic API route setup
  - `@module_health_check` - Automatic health monitoring
  - `@graceful_shutdown` - Async cleanup registration
  - `@force_shutdown` - Sync force cleanup registration
  - `@require_services` - Service dependency declaration
  - `@register_database` - Database registration

- **`module_base.py`** - Base classes for modules
  - `DataIntegrityModule` - Base with integrity validation
  - Common module functionality and patterns

### Bootstrap & Configuration
- **`bootstrap.py`** - Framework initialization bootstrap
  - Environment setup
  - Core module loading
  - Application context initialization

- **`config.py`** - Framework configuration management
  - Core configuration constants
  - Environment-based settings

- **`version.py`** - Framework version management
  - Version information
  - Release metadata

### Database Infrastructure
- **`database.py`** - Core database utilities
  - Database base class generation
  - SQLite JSON type support
  - Database utility functions

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
1. **Module Discovery** (`module_manager.py`) - Find modules with decorators
2. **Decorator Processing** (`module_processor.py`) - Extract metadata from decorators (14-step flow)
3. **Service Registration** (`app_context.py`) - Register services in container
4. **Two-Phase Init** (`module_manager.py`) - Phase 1 registration, Phase 2 complex setup

### 14-Step Module Processing Flow
See `docs/module_decorator_system.md` for complete documentation.

The `ModuleProcessor` executes these steps:
1. Validate decorator metadata
2. Enforce data integrity
3. Process dependencies
4. Store service metadata
5. Process Settings V2 (Pydantic model registration)
6. Register databases/models
7. Register API endpoints
8. Setup health checks
9. Process shutdown metadata
10. Process dependency injection
11. Process initialization sequences (Phase 1 methods)
12. Process Phase 2 operations
13. Process auto service creation
14. Record success

### Clean Separation
- **`error_utils.py`** - Pure utilities, no framework dependencies
- **Framework modules** - Use error_utils, never import each other
- **File-based communication** - JSONL logs prevent circular dependencies

## Key Design Principles

### 1. Single Point of Control
All module registration happens through centralized decorators and processors, eliminating the need for separate manifest files.

### 2. Two-Phase Initialization
- **Phase 1**: Infrastructure setup (synchronous, NO service access)
  - Register Pydantic settings models
  - Set up basic infrastructure
  - Execute methods from `@initialization_sequence(phase="phase1")`
- **Phase 2**: Complex setup (asynchronous, priority-ordered, with service access)
  - Execute methods from `@phase2_operations()`
  - Access other services safely
  - Graceful failure handling

### 3. Mandatory Settings Pattern
ALL modules MUST have:
- `settings.py` with Pydantic v2 model
- `setup_infrastructure()` method to register settings
- `@initialization_sequence("setup_infrastructure", phase="phase1")` decorator

### 4. Circular Dependency Prevention
- Pure utilities with zero framework dependencies
- File-based data flow where needed
- Clean separation between utilities and services

### 5. Service Container Pattern
Central registry for all services, with dependency injection and lifecycle management.

## Usage Examples

### Complete Module Decorator Stack
See `docs/module_decorator_system.md` for comprehensive examples.

```python
from core.decorators import (
    inject_dependencies,
    register_service,
    ServiceMethod,
    ServiceParam,
    ServiceReturn,
    ServiceExample,
    initialization_sequence,
    phase2_operations,
    auto_service_creation,
    register_api_endpoints,
    graceful_shutdown,
    force_shutdown
)
from core.module_base import DataIntegrityModule

@inject_dependencies('app_context')
@register_service("module_id.service", methods=[
    ServiceMethod(
        name="example_method",
        description="Example service method",
        params=[],
        returns=ServiceReturn("Result", "Result with data"),
        examples=[ServiceExample("example_method()", "Result.success(...)")],
        tags=["example"]
    )
], priority=100)
@initialization_sequence("setup_infrastructure", phase="phase1")
@phase2_operations("initialize_phase2")
@auto_service_creation(service_class="MyModuleService")
@register_api_endpoints(router_name="router")
@graceful_shutdown(method="cleanup_resources", timeout=30)
@force_shutdown(method="force_cleanup", timeout=5)
class MyModule(DataIntegrityModule):
    MODULE_ID = "standard.my_module"
    MODULE_VERSION = "1.0.0"
    MODULE_DESCRIPTION = "Example module"

    def setup_infrastructure(self):
        """Phase 1: Register Pydantic settings model (NO service access)."""
        from .settings import MyModuleSettings
        self.app_context.register_pydantic_model(self.MODULE_ID, MyModuleSettings)

    async def initialize_phase2(self):
        """Phase 2: Complex initialization with service access."""
        settings_service = self.app_context.get_service("core.settings.service")
        # ... complex initialization
        return True
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
async def my_operation() -> Result:
    try:
        # Business logic
        return Result.success(data=result)
    except Exception as e:
        logger.error(error_message(
            module_id="my_module",
            error_type="OPERATION_FAILED",
            details=str(e),
            location="my_operation()"
        ))
        return Result.error(
            code="OPERATION_FAILED",
            message="Operation failed"
        )
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
- **Pydantic** - Data validation and settings management (v2)
- **asyncio** - Asynchronous programming support

### Internal Dependencies
- **Minimal coupling** - Core files avoid importing each other
- **Well-defined interfaces** - Clear contracts between components
- **Dependency injection** - Services accessed through app_context

## Documentation References

- **`docs/core/module_decorator_system.md`** - Complete decorator system documentation
- **`docs/database.md`** - Database architecture and patterns
- **`CLAUDE.md`** - Framework overview and development guidelines

The core framework provides a solid, stable foundation for building modular applications with clean architecture, enforced patterns, and reliable initialization.

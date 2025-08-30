# Core Modules Documentation

This directory contains documentation for the core framework modules that provide essential services for the modular framework.

## Core Modules Overview

Core modules are framework-provided modules that offer essential services to all other modules. They follow the same module structure as standard modules but provide foundational capabilities.

### [Database Module](database-module.md)
**Location**: `modules/core/database/`
- Multi-database architecture with SQLite support
- Automatic database discovery and creation
- Table-driven and manager-based patterns
- Connection pooling and retry logic
- Comprehensive CRUD operations and API endpoints

### [Settings Module](settings-module.md)
**Location**: `modules/core/settings/`
- Hierarchical configuration management (Environment → Client → Defaults)
- Schema-based validation with type checking
- UI metadata for automatic interface generation
- Database-backed backup and restoration
- Module-specific settings integration

### [Error Handler Module](error-handler-module.md)
**Location**: `modules/core/error_handler/`
- Result pattern for consistent error handling
- Standardized HTTP error response generation
- Structured JSON-based error logging
- Automatic location detection and context preservation
- Error registry and documentation system

### [Scheduler Module](scheduler-module.md)
**Location**: `modules/core/scheduler/`
- One-time and recurring task scheduling
- Background processing with resource management
- Complete execution history and monitoring
- Housekeeper integration for cleanup operations
- Flexible triggers and job lifecycle management

### [Global Module](global-module.md)
**Location**: `modules/core/global/`
- Framework standards enforcement and compliance validation
- Global configuration and session management
- Comprehensive standards documentation
- Module structure and API schema validation
- Framework-wide utilities and metadata access

### [Model Manager Module](model-manager-module.md)
**Location**: `modules/core/model_manager/`
- Centralized AI model management and lifecycle
- Multi-model support (embedding, text generation, custom types)
- Reference-counted model sharing across modules
- GPU/CPU device management with memory optimization
- Embedding cache with TTL and performance monitoring

## Module Architecture

All core modules follow the standard module structure:

```
modules/core/module_name/
├── api.py                 # Module entry point and API routes
├── services.py            # Main service implementation
├── manifest.json          # Module metadata and dependencies
├── module_settings.py     # Module configuration schema
├── db_models.py          # Database models (if applicable)
├── api_schemas.py        # API request/response schemas
├── compliance.md         # Module compliance documentation
├── readme.md             # Module-specific documentation
└── standards/            # Module standards and patterns
    ├── *.json            # Standard definitions
    └── *.md              # Standard documentation
```

## Service Registration

Core modules register their services with the application context during initialization:

```python
# In api.py
def initialize(app_context):
    """Initialize the module and register services."""
    service = ModuleService(app_context)
    app_context.register_service("module.service", service)
    
    # Register post-initialization hook
    app_context.register_post_init_hook(
        "module.setup",
        service.initialize,
        dependencies=["core.database.setup"]
    )
```

## Core Module Dependencies

Core modules have specific dependency relationships:

```
┌─────────────────────────────────────────────────────────────┐
│                    Module Dependencies                       │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│ database (foundation)                                       │
│  ↓                                                          │
│ error_handler (depends on database)                        │
│  ↓                                                          │
│ settings (depends on database, error_handler)              │
│  ↓                                                          │
│ global (depends on settings, error_handler)                │
│  ↓                                                          │
│ scheduler (depends on database, settings)                  │
│  ↓                                                          │
│ model_manager (depends on database, settings)              │
└─────────────────────────────────────────────────────────────┘
```

## Common Patterns

### Result Pattern
All core modules use the Result pattern for consistent error handling:

```python
from modules.core.error_handler.utils import Result

async def operation() -> Result:
    try:
        # Operation logic
        return Result.success(data=result)
    except Exception as e:
        return Result.error(
            code="OPERATION_FAILED",
            message="Operation description",
            details={"error": str(e)}
        )
```

### Service Integration
Modules access other core services through the application context:

```python
class ModuleService:
    def __init__(self, app_context):
        self.app_context = app_context
        
    async def initialize(self):
        # Access other services
        self.database = self.app_context.get_service("core.database.service")
        self.settings = self.app_context.get_service("core.settings.service")
        return True
```

### Two-Phase Initialization
Core modules follow two-phase initialization:

```python
# Phase 1: Service registration (in api.py)
def initialize(app_context):
    service = ModuleService(app_context)
    app_context.register_service("module.service", service)

# Phase 2: Complex initialization (in services.py)
async def initialize(self):
    # Access dependencies and perform complex setup
    await self.setup_database()
    await self.load_configuration()
    return True
```

## Development Guidelines

### Adding New Core Modules
1. Follow the standard module structure
2. Implement proper dependency management
3. Use the Result pattern for error handling
4. Document all public interfaces
5. Include compliance documentation

### Modifying Core Modules
1. Maintain backward compatibility
2. Update documentation
3. Run compliance checks
4. Test with dependent modules
5. Update dependency graphs

### Testing Core Modules
1. Unit tests for individual components
2. Integration tests with other core modules
3. End-to-end tests with standard modules
4. Performance tests for critical paths

## Related Documentation

- [Core Framework](../core/README.md) - Framework foundation components
- [Framework Patterns](../patterns/README.md) - Common patterns and practices
- [Module Creation Guide](../module-creation-guide-v2.md) - Creating new modules

---

Core modules provide the essential services that make the modular framework powerful and easy to use. They handle the complex infrastructure so that standard modules can focus on business logic.
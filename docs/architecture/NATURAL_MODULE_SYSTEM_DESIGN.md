# Natural Module System Design

**Status**: Design Phase  
**Goal**: Pain-free module development with natural Python patterns  
**Date**: 2025-08-11

## Current System Analysis

### Core Components Inventory

**Essential Framework Components:**
- `core/app_context.py` - Application context and service container
- `core/bootstrap.py` - Database and directory creation before modules load
- `core/paths.py` - Consistent path handling utilities
- `core/config.py` - Application configuration
- `core/logging.py` - Framework-wide logging setup
- `core/error_utils.py` - Result pattern and error handling

**Module System Components (NEEDS REDESIGN):**
- `core/decorators.py` - Decorator definitions (mixed patterns)
- `core/module_loader.py` - Module discovery and loading (complex)
- `core/module_processor.py` - Module processing (14-step complexity)
- `core/module_base.py` - Base classes (unclear purpose)

### Current Startup Sequence

```
1. Framework Logging Setup
2. Basic App Configuration  
3. Bootstrap Phase
   - Directory creation
   - Database discovery and creation
4. Module Discovery
   - Scan directories for api.py files
   - Extract decorator metadata
   - Validate MODULE_ID and decorators
5. Module Loading (Phase 1)
   - Create module instances
   - Register services
   - Store hooks for Phase 2
6. Post-Init Hooks (Phase 2)
   - Execute by priority order
   - Complex dependency resolution
7. FastAPI Server Start
```

## Problems with Current System

### 1. **Unnatural Module Patterns**
```python
# What scaffolding generates (UNNATURAL):
def __init__(self):  # No app_context? Confusing!
    self.app_context = None  # Magic injection later?

# What developers naturally write:
def __init__(self, app_context):  # Clear and explicit
    self.app_context = app_context
```

### 2. **Complex Dependency Injection**
- Current: Magic `@inject_dependencies` with complex metadata
- Natural: Explicit `app_context.get_service()` calls

### 3. **14-Step Module Processing**
- Over-engineered: Settings V2, database registration, health checks, etc.
- Most modules need: Service registration + Phase 2 setup

### 4. **Mixed Legacy Patterns**
- Some decorators work, others don't
- Framework expects old patterns in new modules

## Natural Module System Design

### Core Principle: **Developer Ergonomics First**

**Natural Module Pattern:**
```python
import logging
from core.decorators import register_service, requires_services, phase2_setup

MODULE_ID = "standard.my_module"
logger = logging.getLogger(MODULE_ID)

@register_service(f"{MODULE_ID}.service")
@requires_services(["core.database.service", "core.settings.service"])
@phase2_setup("initialize")
class MyModule:
    MODULE_ID = MODULE_ID  # Required for discovery
    
    def __init__(self, app_context):
        """Natural Python constructor."""
        self.app_context = app_context
        self.logger = logger
        logger.info(f"{MODULE_ID}: Created")
    
    async def initialize(self):
        """Phase 2: Use services."""
        db_service = self.app_context.get_service("core.database.service")
        settings_service = self.app_context.get_service("core.settings.service")
        
        # Do actual initialization
        logger.info(f"{MODULE_ID}: Initialized")
        return True

# Clean service class
class MyModuleService:
    def __init__(self, app_context):
        self.app_context = app_context
    
    def do_work(self):
        return "Working"
```

### Simplified Framework Components

**1. Simple Decorators (core/decorators.py)**
```python
@register_service(name: str, priority: int = 100)
@requires_services(service_names: List[str]) 
@phase2_setup(method_name: str)
# That's it! No complex dependency injection magic
```

**2. Simple Module Loader**
```python
class ModuleLoader:
    async def discover_modules(self) -> List[Module]:
        # Find api.py files with MODULE_ID and decorators
    
    async def load_modules(self, modules: List[Module]):
        # Phase 1: Create instances with app_context
        # Phase 2: Call setup methods in dependency order
```

**3. Clean Service Container**
```python
class AppContext:
    def register_service(self, name: str, instance: Any):
        # Simple service storage
    
    def get_service(self, name: str) -> Any:
        # Simple service retrieval
```

### Startup Sequence (Simplified)

```
1. Framework Setup (logging, config, paths)
2. Bootstrap Phase (directories, databases)
3. Module Discovery (scan for natural pattern modules)
4. Phase 1: Create Modules
   - module = ModuleClass(app_context)
   - app_context.register_service(name, service)
5. Phase 2: Initialize Modules  
   - await module.initialize() (in dependency order)
6. Server Start
```

## Implementation Plan

### Step 1: Create New Core Framework
- `core/natural_decorators.py` - Simple decorator system
- `core/natural_loader.py` - Simple module loader  
- `core/simple_context.py` - Clean service container

### Step 2: Update Bootstrap and App
- Modify `app.py` to use natural system
- Keep `bootstrap.py` (works well)
- Keep `paths.py`, `config.py`, `logging.py` (essential utilities)

### Step 3: Validate with Clean Module
- Use our decorator_validation module as template
- Should work immediately with natural system

### Step 4: Update Scaffolding Tool
- Generate natural pattern modules
- No more unnatural constructors or magic injection

## Success Criteria

1. **Natural Development**: New modules follow standard Python patterns
2. **No Magic**: Explicit service access, clear constructors
3. **Simple Core**: Framework code that's easy to understand and debug
4. **Pain-Free**: Module creation should be straightforward, not frustrating

## Key Insight

**The core framework should adapt to natural Python patterns, not force developers to use unnatural patterns.**

Current approach: Make modules conform to complex framework
Natural approach: Make framework support natural module patterns
# Module Loader System

The Module Loader (`core/module_loader.py`) is responsible for discovering, loading, and managing modules within the framework. It provides automatic module discovery, dependency resolution, and two-phase initialization.

## Overview

The Module Loader implements a sophisticated module management system that handles:

- **Module Discovery**: Automatic discovery of modules in the filesystem
- **Dependency Resolution**: Topological sorting of modules based on dependencies
- **Two-Phase Initialization**: Service registration followed by complex setup
- **Error Handling**: Graceful handling of module loading failures
- **Requirement Management**: Automatic installation of module dependencies

## Key Features

### 1. Module Discovery
- **Automatic Detection**: Scans `modules/` directory for valid modules
- **Multi-Level Support**: Supports core, standard, and extension modules
- **Manifest-Based**: Uses `manifest.json` to identify modules
- **Selective Loading**: Can disable modules via configuration

### 2. Dependency Resolution
- **Topological Sort**: Ensures modules load in correct dependency order
- **Circular Detection**: Detects and prevents circular dependencies
- **Missing Dependencies**: Warns about missing dependencies
- **Priority Loading**: Core modules load first

### 3. Two-Phase Initialization
- **Phase 1**: Service registration and basic setup
- **Phase 2**: Complex initialization via post-init hooks
- **Async Support**: Full async/await support for modern Python

### 4. Error Management
- **Graceful Failures**: Continues loading other modules on failure
- **Detailed Logging**: Comprehensive logging to dedicated file
- **Warning System**: Collects and displays startup warnings

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Module Loader                            │
├─────────────────────────────────────────────────────────────┤
│ Module Discovery                                            │
│ ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐ │
│ │ core/           │ │ standard/       │ │ extensions/     │ │
│ │ modules         │ │ modules         │ │ modules         │ │
│ └─────────────────┘ └─────────────────┘ └─────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│ Dependency Resolution                                       │
│ ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐ │
│ │ Graph Building  │ │ Topological     │ │ Circular        │ │
│ │                 │ │ Sort            │ │ Detection       │ │
│ └─────────────────┘ └─────────────────┘ └─────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│ Two-Phase Initialization                                    │
│ ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐ │
│ │ Phase 1:        │ │ Phase 2:        │ │ Post-Init       │ │
│ │ Service Reg     │ │ Complex Setup   │ │ Hooks           │ │
│ └─────────────────┘ └─────────────────┘ └─────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## Module Discovery Process

### 1. Directory Structure
The loader scans the following directories:
```
modules/
├── core/           # Core framework modules
├── standard/       # Standard application modules
└── extensions/     # Extension modules
```

### 2. Module Identification
```python
# Module must have a manifest.json file
{
    "id": "module_name",
    "name": "Module Display Name",
    "version": "1.0.0",
    "dependencies": ["core.database", "core.settings"],
    "entry_point": "api.py"
}
```

### 3. Module Filtering
```python
# Disabled modules are skipped
# 1. .disabled file in module directory
# 2. Module ID in DISABLE_MODULES config
# 3. Missing required dependencies
```

## Dependency Resolution

### 1. Graph Building
```python
# Build dependency graph from manifests
graph = {
    "core.database": [],
    "core.settings": ["core.database"],
    "standard.my_module": ["core.database", "core.settings"]
}
```

### 2. Topological Sort
```python
# Ensure dependencies load before dependents
async def resolve_dependencies(modules):
    # Build graph
    graph = {}
    for module in modules:
        graph[module["id"]] = module["manifest"].get("dependencies", [])
    
    # Perform topological sort
    order = []
    visited = set()
    
    async def visit(node):
        if node not in visited:
            for dependency in graph.get(node, []):
                await visit(dependency)
            visited.add(node)
            order.append(node)
    
    return order
```

### 3. Circular Dependency Detection
```python
# Detect cycles in dependency graph
temp_mark = set()

async def visit(node):
    if node in temp_mark:
        raise ValueError(f"Circular dependency detected involving {node}")
    
    temp_mark.add(node)
    # ... process dependencies
    temp_mark.remove(node)
```

## Two-Phase Initialization

### Phase 1: Service Registration
```python
# Module's initialize() method is called
async def initialize(app_context):
    # Create service instance
    service = MyService(app_context)
    
    # Register service with app_context
    app_context.register_service("my_module.service", service)
    
    # Register post-init hook for Phase 2
    app_context.register_post_init_hook(
        "my_module.setup",
        service.complex_initialization,
        priority=100,
        dependencies=["core.database.setup"]
    )
```

### Phase 2: Complex Setup
```python
# Post-init hooks run after all modules are loaded
async def complex_initialization(self):
    # Database operations
    await self.setup_database()
    
    # Service integrations
    self.other_service = self.app_context.get_service("other.service")
    
    # Background tasks
    await self.start_background_tasks()
```

## Module Loading Process

### 1. Database Module Priority
```python
# Database module loads first (special handling)
database_module = next((m for m in all_modules if m["id"] == "core.database"), None)
if database_module:
    await self.load_module(database_module)
    # Remove from general loading queue
    all_modules = [m for m in all_modules if m["id"] != "core.database"]
```

### 2. General Module Loading
```python
# Load modules in dependency order
for module_id in module_order:
    module = module_map[module_id]
    
    # Check requirements
    if not await self._check_module_requirements(module["manifest"]):
        continue
    
    # Load the module
    await self.load_module(module)
```

### 3. Module Import and Initialization
```python
async def load_module(self, module):
    # Import the module
    import_path = await self._get_module_import_path(module)
    module_obj = importlib.import_module(import_path)
    
    # Verify async initialize method exists
    if not hasattr(module_obj, "initialize"):
        return False
    
    if not inspect.iscoroutinefunction(module_obj.initialize):
        return False
    
    # Call Phase 1 initialization
    await module_obj.initialize(self.app_context)
    
    # Register API routes if present
    if hasattr(module_obj, "register_routes"):
        module_obj.register_routes(self.app_context.api_router)
    
    return True
```

## Error Handling and Logging

### 1. Dedicated Logging
```python
# Module loader uses dedicated log file
def _setup_module_loader_logger():
    logger = logging.getLogger("module.loader")
    
    # File handler for module_loader.log
    file_handler = logging.FileHandler("data/logs/module_loader.log")
    logger.addHandler(file_handler)
    
    # No terminal output (propagate=False)
    logger.propagate = False
    
    return logger
```

### 2. Warning System
```python
# Collect warnings during loading
async def add_warning(self, message, level="warning", module_id=None):
    self.app_context.startup_warnings.append({
        "message": message,
        "level": level,
        "module_id": module_id or "system"
    })
```

### 3. Failure Recovery
```python
# Continue loading other modules on failure
async def load_modules(self):
    failed_modules = []
    
    for module_id in module_order:
        try:
            if not await self.load_module(module):
                failed_modules.append(module_id)
        except Exception as e:
            failed_modules.append(module_id)
            # Continue with other modules
    
    return len(failed_modules) == 0, failed_modules
```

## Requirement Management

### 1. Dependency Check
```python
async def _check_module_requirements(self, manifest):
    if "requirements" not in manifest:
        return True
    
    missing_packages = []
    for requirement in manifest["requirements"]:
        package_name = requirement.split(">=")[0].split("==")[0].strip()
        try:
            importlib.import_module(package_name)
        except ImportError:
            missing_packages.append(requirement)
    
    return len(missing_packages) == 0
```

### 2. Auto-Installation
```python
# Install missing packages if auto-install enabled
if missing_packages and auto_install:
    try:
        subprocess.check_call([
            sys.executable, "-m", "pip", "install"
        ] + missing_packages)
        return True
    except Exception as e:
        return False
```

## Configuration

### 1. Module Discovery Configuration
```python
# config.py settings
MODULES_DIR: str = "modules"
DISABLE_MODULES: List[str] = []
AUTO_INSTALL_DEPENDENCIES: bool = True
```

### 2. Environment Variables
```bash
# Override module directory
MODULES_DIR="/custom/modules"

# Disable specific modules
DISABLE_MODULES="module1,module2,module3"

# Disable auto-install
AUTO_INSTALL_DEPENDENCIES=false
```

## Usage Examples

### 1. Basic Module Loading
```python
# In app.py
module_loader = ModuleLoader(app_context)
success, failed_modules = await module_loader.load_modules()

if not success:
    print(f"Failed to load modules: {failed_modules}")
```

### 2. Module Context Access
```python
# Access module context
module_context = await module_loader.get_module_context("core.database")
if module_context:
    # Module is loaded and context is available
    pass
```

### 3. Service Registration
```python
# In module's api.py
async def initialize(app_context):
    service = MyService(app_context)
    app_context.register_service("my_module.service", service)
    
    # Register for Phase 2 initialization
    app_context.register_post_init_hook(
        "my_module.setup",
        service.setup_database,
        priority=100,
        dependencies=["core.database.setup"]
    )
```

## Best Practices

### 1. Module Structure
- **Use manifest.json** for module metadata
- **Implement async initialize()** method
- **Register services early** in Phase 1
- **Use post-init hooks** for complex setup

### 2. Dependency Management
- **Declare dependencies** explicitly in manifest
- **Use semantic versioning** for requirements
- **Handle missing dependencies** gracefully
- **Test with different dependency versions**

### 3. Error Handling
- **Return boolean** from initialize() method
- **Log errors** with detailed context
- **Handle exceptions** in module code
- **Provide meaningful error messages**

### 4. Performance Considerations
- **Minimize Phase 1 work** (service registration only)
- **Use async operations** for I/O-bound tasks
- **Lazy load** heavy resources in Phase 2
- **Profile module loading** for bottlenecks

## Common Patterns

### 1. Service Module Pattern
```python
# Module that provides a service
async def initialize(app_context):
    service = MyService(app_context)
    app_context.register_service("my_module.service", service)
    
    # Register complex setup
    app_context.register_post_init_hook(
        "my_module.setup",
        service.initialize,
        dependencies=["core.database.setup"]
    )
```

### 2. Database Module Pattern
```python
# Module that needs database access
async def initialize(app_context):
    service = MyService(app_context)
    app_context.register_service("my_module.service", service)
    
    # Depend on database being ready
    app_context.register_post_init_hook(
        "my_module.setup",
        service.setup_database,
        dependencies=["core.database.setup"]
    )
```

### 3. Extension Module Pattern
```python
# Extension module that enhances existing functionality
async def initialize(app_context):
    extension = MyExtension(app_context)
    app_context.register_service("my_extension.service", extension)
    
    # Depend on modules being extended
    app_context.register_post_init_hook(
        "my_extension.setup",
        extension.enhance_modules,
        dependencies=["target_module.setup"]
    )
```

## Troubleshooting

### 1. Module Not Loading
```python
# Check module discovery
discovered = await module_loader.discover_modules()
module_ids = [m["id"] for m in discovered]

# Check if module is in the list
if "my_module" not in module_ids:
    # Module not discovered - check manifest.json
    pass
```

### 2. Dependency Issues
```python
# Check dependency resolution
try:
    order = await module_loader.resolve_dependencies(modules)
except ValueError as e:
    # Circular dependency detected
    print(f"Dependency error: {e}")
```

### 3. Initialization Failures
```python
# Check module logs
# data/logs/module_loader.log contains detailed information
# Look for async/sync initialization issues
```

## Related Documentation

- [Application Context](app-context.md) - Service container and dependency injection
- [Configuration System](config-system.md) - Module configuration management
- [Two-Phase Initialization](../patterns/two-phase-initialization.md) - Initialization patterns
- [Module Creation Guide](../module-creation-guide-v2.md) - Creating new modules
- [Database Module](../modules/database-module.md) - Database integration

---

The Module Loader is the foundation of the framework's modularity, providing automatic discovery, dependency resolution, and initialization management that enables clean, maintainable application architecture.
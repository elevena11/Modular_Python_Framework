# Async Programming Patterns in VeritasForma Framework

**Version: 1.0**  
**Updated: June 10, 2025**  
**Status: Current Implementation Guide**

## [CRITICAL] **CRITICAL: Async is Mandatory**

**The VeritasForma Framework is fully async.** All functions, methods, and operations MUST use async/await patterns. 

**There are no exceptions** - only Python language limitations where async is not possible.

This guide documents the async patterns used throughout the framework, based on working implementations in core modules.

## [ARCHITECTURE] **Framework Async Architecture**

The VeritasForma Framework is built on a fully asynchronous foundation to support:
- **Non-blocking module initialization** - Modules load concurrently
- **Efficient resource management** - Database and I/O operations don't block
- **Scalable service architecture** - Services handle concurrent requests
- **Responsive UI integration** - UI frameworks remain responsive during operations

## [PROCESS] **Module Async Lifecycle**

All modules follow a standardized two-phase async lifecycle that enables proper dependency management and resource initialization.

### Phase 1: Registration (`async def initialize`)

**Function Signature**: `async def initialize(app_context)` - **MUST be async**  
**Purpose**: Register services and prepare for later initialization  
**Constraints**: No database operations, no complex resource creation  
**Timing**: All modules run Phase 1 concurrently

```python
# modules/core/global/api.py - Real example
async def initialize(app_context):
    """Phase 1: Registration ONLY."""
    global service_instance
    
    # 1. Create service instance (sync __init__)
    service_instance = GlobalService(app_context)
    
    # 2. Register service
    app_context.register_service(f"{MODULE_ID}.service", service_instance)
    
    # 3. Register settings (but don't load them yet)
    await register_settings(app_context)
    
    # 4. Register for Phase 2 (REQUIRED for complex modules)
    app_context.register_module_setup_hook(
        module_id=MODULE_ID,
        setup_method=setup_module
    )
    
    return True
```

### Phase 2: Activation (`async def setup_module`)

**Function Signature**: `async def setup_module(app_context)` - **MUST be async**  
**Purpose**: Complex initialization after all dependencies are available  
**Capabilities**: Database operations, external resources, settings loading  
**Timing**: After all Phase 1 completions, in dependency order

```python
# modules/core/global/api.py - Real example
async def setup_module(app_context):
    """Phase 2: Activation."""
    global service_instance
    
    try:
        # Load settings (safe in Phase 2)
        settings = await app_context.get_module_settings(MODULE_ID)
        
        # Initialize service with complex operations
        if service_instance:
            initialized = await service_instance.initialize(
                app_context=app_context,
                settings=settings
            )
            if not initialized:
                return False
        
        return True
        
    except Exception as e:
        logger.error(f"Error in Phase 2: {str(e)}")
        return False
```

## [TOOLS] **Service Implementation**

### All Service Methods Must Be Async

**Every service method MUST be async** - no exceptions. All database operations, I/O, and business logic must use async/await patterns.

```python
# modules/core/database/services.py - Real implementation
class DatabaseService:
    def __init__(self, app_context):
        """
        Python language limitation: constructors cannot be async.
        ONLY basic variable assignment allowed here.
        """
        self.app_context = app_context
        self.initialized = False
        self.config = {}
        
        # Lazy loading references - NO complex operations
        self._db_operations = None
        self._migration_manager = None
    
    async def initialize(self, app_context=None, settings=None):
        """ALL service methods MUST be async."""
        if self.initialized:
            return True
        
        try:
            # Load settings
            if settings:
                self.config = settings
            else:
                context = app_context or self.app_context
                self.config = await context.get_module_settings(MODULE_ID)
            
            # Perform complex async operations
            await self._setup_database_connections()
            await self._run_migrations()
            
            self.initialized = True
            return True
            
        except Exception as e:
            logger.error(f"Initialization failed: {str(e)}")
            return False
```

### Lazy Loading Properties

Use properties for expensive resources that may not always be needed:

```python
# modules/core/database/services.py - Real pattern
@property
def db_operations(self):
    """Lazy load database operations."""
    if self._db_operations is None:
        self._db_operations = DatabaseOperations(self.app_context)
    return self._db_operations

@property  
def migration_manager(self):
    """Lazy load migration manager."""
    if self._migration_manager is None:
        self._migration_manager = MigrationManager(self.app_context)
    return self._migration_manager
```

## [CONNECTION] **App Context Integration**

The `AppContext` provides the async foundation for all module operations:

### Module Setup Hooks

```python
# core/app_context.py - Real implementation
def register_module_setup_hook(self, module_id: str, setup_method):
    """Register a module for Phase 2 initialization."""
    self.post_init_hooks[module_id] = setup_method

async def execute_post_init_hooks(self):
    """Execute all Phase 2 setup methods."""
    for module_id, setup_method in self.post_init_hooks.items():
        try:
            result = await setup_method(self)
            if not result:
                self.logger.error(f"Module {module_id} Phase 2 failed")
        except Exception as e:
            self.logger.error(f"Error in {module_id} Phase 2: {str(e)}")
```

### Async Settings Loading

```python
# core/app_context.py - Real pattern
async def get_module_settings(self, module_id: str) -> Dict[str, Any]:
    """Async settings loading for modules."""
    settings_service = self.get_service("core.settings.service")
    if settings_service and settings_service.initialized:
        result = await settings_service.get_module_settings(module_id)
        if result.success:
            return result.data
    return {}
```

## [LIBRARY] **Module Loader Async Patterns**

The module loader orchestrates the entire async module lifecycle:

```python
# core/module_loader.py - Real implementation
class ModuleLoader:
    async def discover_and_load_modules(self) -> Dict[str, Any]:
        """Main async module loading orchestration."""
        
        # 1. Discover all modules
        module_manifests = await self._discover_modules()
        
        # 2. Resolve dependencies  
        load_order = self._resolve_dependencies(module_manifests)
        
        # 3. Phase 1: Load all modules
        for module_path in load_order:
            await self._load_module_from_path(module_path)
        
        # 4. Phase 2: Execute setup hooks
        await self.app_context.execute_post_init_hooks()
        
        return self.modules
    
    async def _load_module_from_path(self, module_path: str):
        """Load individual module asynchronously."""
        try:
            # Import module
            module = importlib.import_module(module_path)
            
            # Call async initialize function
            if hasattr(module, 'initialize'):
                await module.initialize(self.app_context)
                
        except Exception as e:
            self.logger.error(f"Failed to load {module_path}: {str(e)}")
```

## [PERFORMANCE] **Async Best Practices**

### 1. **Always Use Result Objects**

```python
# From modules/core/database/services.py
async def create_item(self, data: Dict[str, Any]) -> Result:
    \"\"\"Service method returning Result object.\"\"\"
    try:
        # Async database operation
        item = await self.db_operations.create(data)
        return Result.success(data=item)
    except Exception as e:
        return Result.error(
            code="CREATE_FAILED",
            message="Failed to create item"
        )
```

### 2. **Proper Error Handling**

```python
# Always wrap async operations in try/except
try:
    result = await async_operation()
    if not result.success:
        # Handle service-level errors
        logger.error(f"Operation failed: {result.error}")
        return result
except Exception as e:
    # Handle unexpected errors
    logger.error(f"Unexpected error: {str(e)}")
    return Result.error(code="UNEXPECTED_ERROR", message=str(e))
```

### 3. **Initialization State Management**

```python
class MyService:
    def __init__(self, app_context):
        self.initialized = False
    
    async def any_method(self):
        # Check initialization before operations
        if not self.initialized and not await self.initialize():
            return Result.error(code="NOT_INITIALIZED")
        
        # Proceed with operation
```

### 4. **Concurrent Operations**

```python
# Use asyncio.gather for concurrent operations
async def process_multiple_items(self, items):
    tasks = [self.process_item(item) for item in items]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return results
```

## [ALERT] **Mandatory Async Requirements**

### **Everything MUST Be Async**
- [CORRECT] **Module functions**: `async def initialize()`, `async def setup_module()`
- [CORRECT] **Service methods**: `async def method_name()` - NO sync methods allowed
- [CORRECT] **Database operations**: Async sessions, `await` all operations
- [CORRECT] **I/O operations**: File access, network calls, external APIs
- [CORRECT] **Business logic**: All application logic must be async

### **Python Language Limitations Note**
*Where Python doesn't support async (rare cases):*
- `def __init__(self)` - Python constructors cannot be async  
- `@property def name(self)` - Property getters cannot be async

*These are not "exceptions" to async requirements - async simply isn't available in these specific Python constructs.*

### **Async Development Rules**

#### 1. **Never Block the Event Loop**
```python
# [INCORRECT] BAD - Blocking operation
time.sleep(5)

# [CORRECT] GOOD - Non-blocking
await asyncio.sleep(5)
```

#### 2. **Always Use await**
```python
# [INCORRECT] BAD - Returns coroutine object
result = async_function()

# [CORRECT] GOOD - Actually executes
result = await async_function()
```

#### 3. **Respect Module Lifecycle**
```python
# [INCORRECT] WRONG - Complex operations in Phase 1
async def initialize(app_context):
    other_service = app_context.get_service("other.service")
    await other_service.do_something()  # Not guaranteed to exist yet!

# [CORRECT] CORRECT - Complex operations in Phase 2
async def setup_module(app_context):
    other_service = app_context.get_service("other.service")
    if other_service and other_service.initialized:
        await other_service.do_something()
```

#### 4. **No Sync Alternatives**
```python
# [INCORRECT] WRONG - Using sync alternatives
def process_data(self, data):  # Sync method
    return requests.get(url)   # Sync HTTP call

# [CORRECT] CORRECT - Everything async
async def process_data(self, data):  # Async method
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.json()
```

## [LIBRARY] **Real Code Examples**

All patterns in this guide are taken from working implementations:

- **Module Lifecycle**: `modules/core/global/api.py`
- **Service Pattern**: `modules/core/database/services.py`
- **App Context**: `core/app_context.py`
- **Module Loader**: `core/module_loader.py`

For complete examples, refer to any core module implementation.

---

## [DOCS] **Summary: Async is Non-Negotiable**

**The VeritasForma Framework is async-first:**
- [CRITICAL] **ALL functions must be async** - `async def` everywhere
- [CRITICAL] **ALL database operations must be async** - no sync database calls
- [CRITICAL] **ALL I/O operations must be async** - files, network, external APIs
- [CRITICAL] **ALL service methods must be async** - no sync business logic

**Python language limitations are noted but rare:**
- Class constructors (`__init__`) - Python limitation, not framework choice
- Property getters (`@property`) - For simple lazy loading only

**When in doubt: use async.** There are no valid reasons to use sync operations in the VeritasForma Framework.

---

**Next**: See [module-creation-guide-v2.md](../module-creation-guide-v2.md) for applying these patterns in new modules.
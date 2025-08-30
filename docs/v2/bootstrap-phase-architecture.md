# Bootstrap Phase Architecture

## Overview

The Bootstrap Phase is a critical pre-module initialization step that ensures all essential infrastructure exists before any modules load. This phase handles "cold boot" scenarios where databases, directories, or other critical resources need to be created from scratch.

**Core Philosophy**: Modules should "just work" - they should never need special code to handle missing infrastructure or cold boot scenarios.

## Current Implementation (v1.0)

### Architecture Position

```
Application Startup Sequence:
1. App Context Initialization
2. BOOTSTRAP PHASE          ← Infrastructure preparation
3. Module Discovery  
4. Module Loading (Phase 1)   ← Service registration
5. Module Initialization (Phase 2) ← Complex initialization
6. Application Ready
```

### Current Bootstrap Handlers

#### DirectoryBootstrapHandler (Priority: 5)
- **Purpose**: Creates all required framework directories
- **Scope**: Framework-level directory structure
- **Directories Created**:
  - `data/logs`, `data/cache`, `data/temp`
  - `data/database`, `data/config`, `data/error_logs`
  - `data/logs/modules`, `data/models`, `data/exports`, `data/imports`

#### DatabaseBootstrapHandler (Priority: 10)  
- **Purpose**: Discovers and creates all SQLite databases
- **Scope**: All modules with `db_models.py` files
- **Process**:
  1. Scans `modules/*/db_models.py` for `DATABASE_NAME` declarations
  2. Discovers table schemas from `__tablename__` declarations
  3. Creates SQLite database files with all required tables
  4. Sets SQLite pragmas for optimal performance

### Handler Discovery (Current Limitation)

**Hard-Coded Discovery**:
```python
def discover_bootstrap_handlers() -> List[BootstrapHandler]:
    # Static list - only knows about core handlers
    from core.database_bootstrap import DatabaseBootstrapHandler
    from core.directory_bootstrap import DirectoryBootstrapHandler
    
    return [
        DirectoryBootstrapHandler(),
        DatabaseBootstrapHandler(),
    ]
```

**Limitations**:
- ❌ Only discovers core framework handlers
- ❌ Cannot find third-party module bootstrap needs
- ❌ Requires manual modification for new handlers
- ❌ No extensibility for custom modules

## Future Enhancement: Dynamic Bootstrap System (v2.0)

### Decorator-Based Bootstrap Registration

**Proposed Decorator**:
```python
@bootstrap_handler(
    name="semantic_model_preparation",
    priority=25,
    dependencies=["database", "directories"],
    scope="infrastructure_only"  # Enforces constraints
)
async def prepare_semantic_models(app_context) -> bool:
    """
    Prepare embedding models required for semantic operations.
    
    BOOTSTRAP GUIDELINES:
    - Only infrastructure preparation code
    - Must be self-contained (no external module dependencies)
    - Should handle missing resources gracefully
    - Must return True on success, False on failure
    """
    try:
        # Download required models
        await download_embedding_models()
        # Verify model integrity  
        await validate_model_files()
        # Create model index cache
        await initialize_model_cache()
        return True
    except Exception as e:
        logger.error(f"Semantic model preparation failed: {e}")
        return False
```

### Bootstrap Handler Constraints

**CRITICAL REQUIREMENTS** for bootstrap handlers:

#### 1. Infrastructure-Only Code
```python
# ✅ ALLOWED - Infrastructure preparation
await download_required_models()
await create_cache_directories()
await validate_external_dependencies()

# ❌ FORBIDDEN - Business logic
await process_user_documents()
await generate_analytics_reports()  
await send_notification_emails()
```

#### 2. Self-Contained Operations
```python
# ✅ ALLOWED - Self-contained operations
import requests
model_data = requests.get("https://models.example.com/embedding.bin")

# ❌ FORBIDDEN - Inter-module dependencies
other_service = app_context.get_service("other.module")  # Module not loaded yet!
result = other_service.process_data()  # Will fail!
```

#### 3. Graceful Failure Handling
```python
# ✅ REQUIRED - Graceful error handling
try:
    await prepare_infrastructure()
    return True
except NetworkError:
    logger.warning("Network unavailable - using offline mode")
    return True  # Non-fatal, module can function with degraded features
except CriticalError:
    logger.error("Critical infrastructure failed")  
    return False  # Fatal, module cannot function
```

#### 4. Idempotent Operations
```python
# ✅ REQUIRED - Idempotent (safe to run multiple times)
if not os.path.exists(model_path):
    await download_model(model_path)
    
if not cache_is_valid():
    await rebuild_cache()
```

### Dynamic Handler Discovery

**Automatic Discovery Process**:
```python
def discover_bootstrap_handlers() -> List[BootstrapHandler]:
    """
    Dynamically discover bootstrap handlers from all modules.
    """
    handlers = []
    
    # 1. Discover from decorators (scan loaded modules)
    handlers.extend(discover_decorated_bootstrap_handlers())
    
    # 2. Discover from manifest declarations  
    handlers.extend(discover_manifest_bootstrap_handlers())
    
    # 3. Add core framework handlers
    handlers.extend(get_core_bootstrap_handlers())
    
    return handlers
```

**Module Manifest Integration**:
```json
{
  "id": "standard.semantic_analysis",
  "bootstrap_requirements": {
    "handler_function": "prepare_semantic_infrastructure",
    "priority": 25,
    "dependencies": ["database", "directories"],
    "timeout": 300,
    "failure_mode": "degrade"  // "degrade" or "abort"
  }
}
```

### Bootstrap Execution Engine

**Enhanced Execution with Constraints**:
```python
async def execute_bootstrap_handler(handler: BootstrapHandler, app_context) -> BootstrapResult:
    """Execute a bootstrap handler with safety constraints."""
    
    # Validate handler constraints
    if not validate_bootstrap_constraints(handler):
        return BootstrapResult.constraint_violation()
    
    # Execute with timeout
    try:
        async with asyncio.timeout(handler.get_timeout()):
            success = await handler.execute(app_context)
            return BootstrapResult.success() if success else BootstrapResult.failure()
    except asyncio.TimeoutError:
        return BootstrapResult.timeout()
    except Exception as e:
        return BootstrapResult.exception(e)
```

### Bootstrap Handler Validation

**Constraint Enforcement**:
```python
def validate_bootstrap_constraints(handler: BootstrapHandler) -> bool:
    """Validate that handler follows bootstrap constraints."""
    
    # Check for forbidden patterns
    source_code = inspect.getsource(handler.execute)
    
    forbidden_patterns = [
        r'app_context\.get_service\(',  # No service dependencies
        r'import.*modules\.',           # No module imports
        r'\.process_.*\(',             # No business logic patterns  
    ]
    
    for pattern in forbidden_patterns:
        if re.search(pattern, source_code):
            logger.error(f"Bootstrap handler {handler.get_name()} violates constraints")
            return False
    
    return True
```

## Best Practices for Bootstrap Handlers

### DO: Infrastructure Preparation
```python
@bootstrap_handler(name="ml_model_prep", priority=30)
async def prepare_ml_infrastructure(app_context) -> bool:
    """Prepare ML model infrastructure."""
    
    # ✅ Download required models
    await download_embedding_models()
    
    # ✅ Create cache directories  
    ensure_directory_exists("data/models/cache")
    
    # ✅ Verify external dependencies
    if not await verify_gpu_availability():
        logger.info("GPU unavailable - enabling CPU fallback")
    
    # ✅ Initialize resource pools
    await initialize_model_pool()
    
    return True
```

### DON'T: Business Logic
```python
@bootstrap_handler(name="bad_example", priority=50)
async def bad_bootstrap_example(app_context) -> bool:
    """EXAMPLE OF WHAT NOT TO DO."""
    
    # ❌ Processing user data
    documents = await load_user_documents()
    await analyze_documents(documents)
    
    # ❌ Sending notifications
    await send_startup_notification_email()
    
    # ❌ Depending on other modules
    semantic_service = app_context.get_service("semantic.analysis")
    await semantic_service.process_embeddings()
    
    return True
```

### Handler Categories

**Infrastructure Bootstrap (Allowed)**:
- File/directory creation
- External resource downloads (models, data, schemas)  
- Cache initialization
- External service connectivity verification
- Resource pool initialization
- Configuration file generation

**Business Logic Bootstrap (Forbidden)**:
- Data processing operations
- User notification sending
- Report generation
- Inter-module communication
- Business rule execution
- User-facing feature initialization

## Migration Path

### Phase 1: Current Implementation (Complete)
- ✅ Core bootstrap handlers (directory, database)
- ✅ Manual handler registration
- ✅ Basic priority and dependency support

### Phase 2: Dynamic Discovery (Future)  
- ⏳ Decorator-based handler registration
- ⏳ Automatic handler discovery from modules
- ⏳ Manifest-based bootstrap declarations

### Phase 3: Advanced Features (Future)
- ⏳ Constraint validation and enforcement
- ⏳ Bootstrap handler timeout management
- ⏳ Failure mode handling (degrade vs. abort)
- ⏳ Bootstrap performance monitoring

## Technical Implementation Notes

### Handler Base Class
```python
class BootstrapHandler(ABC):
    @abstractmethod
    async def should_run(self, app_context) -> bool:
        """Check if this bootstrap step is needed."""
        pass
    
    @abstractmethod  
    async def execute(self, app_context) -> bool:
        """Perform the bootstrap action."""
        pass
    
    @abstractmethod
    def get_priority(self) -> int:
        """Execution priority (lower = earlier)."""
        pass
    
    def get_timeout(self) -> int:
        """Handler timeout in seconds."""
        return 60
    
    def get_failure_mode(self) -> str:
        """How to handle failure: 'abort' or 'degrade'."""
        return "abort"
```

### Bootstrap Result Types
```python
class BootstrapResult:
    SUCCESS = "success"
    FAILURE = "failure"
    TIMEOUT = "timeout"
    CONSTRAINT_VIOLATION = "constraint_violation"
    SKIPPED = "skipped"
```

## Benefits of Enhanced Bootstrap System

### For Framework
- **Extensible**: Any module can declare bootstrap needs
- **Reliable**: Constraint enforcement prevents misuse  
- **Fast**: Parallel execution where possible
- **Debuggable**: Clear failure modes and logging

### For Module Developers
- **Simple**: Decorator-based registration
- **Safe**: Constraint validation prevents common mistakes
- **Flexible**: Multiple declaration methods (decorator, manifest)
- **Predictable**: Clear guidelines on what belongs in bootstrap

### for System Reliability  
- **Cold Boot**: Handles fresh deployments reliably
- **Resource Management**: Ensures infrastructure exists before use
- **Failure Isolation**: Bootstrap failures don't affect other modules
- **Performance**: Infrastructure ready before module loading begins

---

This Bootstrap Phase architecture provides a solid foundation for reliable application startup while maintaining clear boundaries between infrastructure preparation and business logic execution.
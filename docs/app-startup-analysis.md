# App Startup Process and AppContext Initialization

**Location**: `app.py` and `core/app_context.py`  
**Purpose**: Main application entry point with lifecycle management and central context initialization  
**Created**: Based on analysis of actual code on 2025-06-17

## Overview

The Modular Framework uses a sophisticated application startup sequence that follows a two-phase initialization pattern. The main entry point (`app.py`) coordinates the entire startup process, while `AppContext` serves as the central nervous system for the application, managing services, configuration, and inter-module communication.

## Architecture Principles

### FastAPI Lifespan Management

**Lifespan Context Manager**:
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application startup and shutdown events."""
    # Startup code
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}...")
    
    # ... initialization sequence ...
    
    yield  # This is where FastAPI serves the application
    
    # Shutdown code
    logger.info(f"{settings.APP_NAME} v{settings.APP_VERSION} shutting down")
```

**Benefits of Lifespan Pattern**:
- **Clean Separation**: Startup and shutdown logic clearly separated
- **Resource Management**: Proper initialization and cleanup of resources
- **Error Handling**: Centralized error handling for application lifecycle
- **Async Support**: Full async/await support throughout startup process

### Two-Phase Initialization

**Phase 1 - Service Registration**:
- Modules register their services with `app_context`
- Post-initialization hooks are registered
- Basic module functionality is established
- No complex database operations or external connections

**Phase 2 - Complex Operations**:
- Database operations and schema creation
- External service connections
- Data initialization and migration
- Complex inter-module dependencies

## Startup Sequence Analysis

### 1. Application Bootstrap (`app.py:132-167`)

```python
# Startup code in lifespan manager
logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}...")

# Ensure data directory exists
os.makedirs(settings.DATA_DIR, exist_ok=True)
logger.info(f"Data directory: {os.path.abspath(settings.DATA_DIR)}")

# Create application context
app.state.app_context = AppContext(settings)
app.state.app_context.initialize()

# Create module loader
module_loader = ModuleLoader(app.state.app_context)

# Load modules - Now awaiting async module loader
success, failed_modules = await module_loader.load_modules()
```

**Key Steps**:
1. **Environment Setup**: Ensure data directories exist
2. **Context Creation**: Initialize central `AppContext` 
3. **Context Initialization**: Setup database and API router
4. **Module Loading**: Discover and load all framework modules
5. **Error Assessment**: Check for module loading failures

### 2. AppContext Initialization (`core/app_context.py:49-78`)

```python
def initialize(self):
    """Initialize the application context."""
    # Setup SQLite database
    self._initialize_sqlite()
    
    # Create API router
    self.api_router = APIRouter(prefix=self.config.API_PREFIX)
```

**Database Initialization Process**:
```python
def _initialize_sqlite(self):
    """Initialize SQLite database with async engine."""
    # Check if database URL is empty and load from config or set default
    if not self.config.DATABASE_URL:
        self.config.DATABASE_URL = self._load_db_url_from_config()
    
    # Ensure database directory exists
    if self.config.DATABASE_URL.startswith("sqlite:///"):
        db_path = self.config.DATABASE_URL[10:]  # Remove 'sqlite:///' prefix
        db_dir = os.path.dirname(db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
    
    # Set up async engine for the FastAPI application
    self._setup_sqlite_async_engine()
```

**Async Engine Configuration**:
```python
def _setup_sqlite_async_engine(self):
    """Set up the asynchronous SQLite engine."""
    # Convert URL to aiosqlite format
    async_url = self.config.DATABASE_URL.replace('sqlite:///', 'sqlite+aiosqlite:///')
    
    # Create async engine with proper pool configuration
    self.db_engine = create_async_engine(
        async_url,
        echo=False,               # Don't log all SQL
        future=True,
        # Connection pool configuration
        pool_size=20,             # Allow many concurrent connections
        max_overflow=10,          # Allow temporary overflow beyond pool_size
        pool_timeout=30,          # Wait up to 30 seconds for connection
        pool_recycle=3600,        # Recycle connections after an hour
        pool_pre_ping=True,       # Check connection health before using
        connect_args={
            "check_same_thread": False  # Allow multi-threaded access
        }
    )
```

### 3. Module Discovery and Loading (`core/module_loader.py:266-337`)

**Module Loading Process**:
```python
async def load_modules(self) -> tuple[bool, list[str]]:
    """Load all modules with dependency resolution."""
    # Discover available modules
    all_modules = await self.discover_modules()
    
    # Prioritize database module first
    database_module = next((m for m in all_modules if m["id"] == "core.database"), None)
    if database_module:
        logger.info("Loading database module first (Phase 1 only)")
        await self.load_module(database_module)
    
    # Get dependency order for remaining modules
    module_order = await self.resolve_dependencies(all_modules)
    
    # Load modules in order
    for module_id in module_order:
        if module_id in module_map:
            await self.load_module(module)
```

**Bootstrap Priority Pattern**:
- **Core Database**: Loaded first with special priority
- **Dependency Resolution**: Topological sort ensures proper loading order
- **Error Handling**: Core module failures abort startup sequence
- **Phase 1 Only**: Initial loading focuses on service registration

### 4. Individual Module Loading (`core/module_loader.py:339-397`)

**Module Loading Sequence**:
```python
async def load_module(self, module: Dict[str, Any]) -> bool:
    """Load a single module."""
    # Import the module
    module_obj = importlib.import_module(import_path)
    
    # Initialize the module (Phase 1 only - no complex operations)
    if hasattr(module_obj, "initialize"):
        # Verify the initialize method is async
        if not inspect.iscoroutinefunction(module_obj.initialize):
            error_msg = f"Module {module_id} must use 'async def initialize(app_context)'"
            return False
        
        # Call the async initialize method
        await module_obj.initialize(self.app_context)
    
    # Register API routes
    if hasattr(module_obj, "register_routes"):
        module_obj.register_routes(self.app_context.api_router)
    
    # Store the loaded module
    self.modules[module_id] = {
        "manifest": module["manifest"],
        "module": module_obj,
        "path": module["path"]
    }
```

**Module Requirements**:
- **Async Initialize**: All modules must use `async def initialize(app_context)`
- **API Registration**: Optional route registration for web endpoints
- **Service Registration**: Modules register services during Phase 1
- **Hook Registration**: Complex operations deferred to Phase 2 hooks

### 5. FastAPI Integration (`app.py:153-160`)

```python
# Set up API router
app.include_router(app.state.app_context.api_router)

# Override database dependency
app.dependency_overrides[get_db] = app.state.app_context.get_db

# Display any registered warnings before announcing completion
display_warnings(app.state.app_context)
```

**Integration Steps**:
- **Router Inclusion**: Add all module routes to main FastAPI app
- **Dependency Override**: Replace database dependency with context version
- **Warning Display**: Show any startup warnings to developers
- **Error Assessment**: Log failed modules and their impact

### 6. Post-Initialization Hooks (`app.py:162-166`)

```python
# Run post-initialization hooks directly in the main event loop
if hasattr(app.state.app_context, 'post_init_hooks') and app.state.app_context.post_init_hooks:
    logger.info("Running post-initialization hooks...")
    await run_delayed_hooks(app)
```

**Hook Execution Process** (`app.py:35-91`):
```python
async def run_delayed_hooks(app):
    """Run post-initialization hooks after application has fully started."""
    # Sort by priority (lower number = higher priority)
    hooks.sort(key=lambda h: h["priority"])
    
    # Execute hooks respecting dependencies
    for hook in hooks:
        # Check if all dependencies have been executed
        dependencies_met = all(dep in executed_hooks for dep in hook["dependencies"])
        
        if dependencies_met:
            await hook["function"](app.state.app_context)
```

**Hook Features**:
- **Priority-Based**: Lower numbers execute first
- **Dependency Management**: Hooks can depend on other hooks
- **Error Isolation**: Hook failures don't stop other hooks
- **Phase 2 Operations**: Database creation, migrations, complex setup

## AppContext Core Functionality

### 1. Session Management (`core/app_context.py:22-47`)

```python
def __init__(self, config):
    """Initialize the application context with configuration."""
    # Generate unique session identifier for this app instance
    self.session_uuid = str(uuid.uuid4())
    self.session_id = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{self.session_uuid[:8]}"
    self.session_start_time = datetime.now()
    
    # Initialize core components
    self.services = {}
    self.post_init_hooks = {}
    self.startup_warnings = []
    self._shutdown_handlers = []
```

**Session Tracking**:
- **Unique Identifiers**: Each app instance has UUID and formatted session ID
- **Startup Time**: Track application lifetime for monitoring
- **Service Registry**: Central registry for all module services
- **Hook Management**: Post-initialization and shutdown hook storage

### 2. Service Management (`core/app_context.py:191-201`)

```python
def register_service(self, name, service):
    """Register a service for use by other modules."""
    self.logger.info(f"Registering service: {name}")
    self.services[name] = service
    
def get_service(self, name):
    """Get a registered service by name."""
    if name not in self.services:
        self.logger.warning(f"Service '{name}' not found")
        return None
    return self.services[name]
```

**Service Registry Pattern**:
- **Central Discovery**: All services registered in one place
- **Inter-Module Communication**: Modules find services through context
- **Loose Coupling**: Modules don't import each other directly
- **Service Availability**: Graceful handling of missing services

### 3. Database Session Management (`core/app_context.py:183-189`)

```python
async def get_db(self):
    """Database session dependency for FastAPI."""
    db = self.db_session()
    try:
        yield db
    finally:
        await db.close()  # Note the await
```

**Database Features**:
- **Async Sessions**: Full async/await support for database operations
- **Connection Pooling**: Configured for high concurrency
- **Retry Logic**: Built-in retry for SQLite lock contention
- **Multi-Database**: Support for multiple database connections

### 4. Settings Integration (`core/app_context.py:306-505`)

**Enhanced Settings Management**:
```python
async def register_module_settings(self, 
                                 module_id: str, 
                                 default_settings: Dict[str, Any],
                                 validation_schema: Optional[Dict[str, Any]] = None,
                                 ui_metadata: Optional[Dict[str, Any]] = None,
                                 version: Optional[str] = None) -> bool:
```

**Settings Features**:
- **Module-Specific**: Each module can register its own settings
- **Validation Support**: Optional schema validation for settings
- **UI Integration**: Metadata for auto-generating UI controls
- **Version Management**: Support for settings migrations
- **Hierarchical Override**: Environment > client config > module defaults

### 5. Post-Initialization Hook System (`core/app_context.py:214-231`)

```python
def register_post_init_hook(self, name: str, hook: Callable[[Any], Awaitable[None]],
                           priority: int = 100, dependencies: Optional[List[str]] = None):
    """Register a function to be called after all modules are initialized."""
    self.post_init_hooks[name] = {
        "function": hook,
        "priority": priority,
        "dependencies": dependencies or []
    }
```

**Hook System Features**:
- **Deferred Execution**: Complex operations wait until Phase 2
- **Dependency Resolution**: Hooks can depend on other hooks
- **Priority Control**: Order execution by priority levels
- **Error Resilience**: Individual hook failures don't crash startup

## Shutdown Process (`app.py:171-193`)

```python
# Shutdown code
logger.info(f"{settings.APP_NAME} v{settings.APP_VERSION} shutting down")

# First try async shutdown
if hasattr(app.state.app_context, "run_shutdown_handlers"):
    try:
        await app.state.app_context.run_shutdown_handlers()
    except Exception as e:
        # If async shutdown fails, try force shutdown
        app.state.app_context.force_shutdown()

# Always do force shutdown as a final step
app.state.app_context.force_shutdown()
```

**Shutdown Features**:
- **Graceful Shutdown**: Async shutdown handlers for clean resource cleanup
- **Force Shutdown**: Synchronous fallback for emergency situations
- **Session Tracking**: Log session duration and completion
- **Service Cleanup**: Each service can register cleanup handlers

## Error Handling and Monitoring

### 1. Startup Warning System (`app.py:95-127`)

```python
def display_warnings(app_context):
    """Display all registered startup warnings."""
    # Header
    logger.warning("=" * width)
    logger.warning("IMPORTANT SYSTEM MESSAGES".center(width))
    
    # Display each warning with level-specific formatting
    for warning in app_context.startup_warnings:
        level = warning["level"]
        message = warning["message"]
        module = warning["module_id"]
        logger.warning(f"[{prefix}] [{module}] {message}")
```

**Warning Features**:
- **Centralized Display**: All warnings shown in formatted block
- **Level Classification**: Info, warning, critical levels
- **Module Attribution**: Track which module generated each warning
- **Developer Visibility**: Ensure important issues are seen

### 2. Module Loading Error Handling (`app.py:147-152`)

```python
success, failed_modules = await module_loader.load_modules()
if not success:
    if failed_modules:
        logger.error(f"Failed to load the following modules: {', '.join(failed_modules)}")
    logger.error("Application may not function correctly due to module loading failures.")
```

**Error Recovery**:
- **Partial Failure**: App continues even if some modules fail
- **Core Module Protection**: Core module failures abort startup
- **Detailed Logging**: Failed modules listed for debugging
- **Impact Assessment**: Clear indication of functionality impact

### 3. Database Retry Logic (`core/app_context.py:133-181`)

```python
async def execute_with_retry(self, coro, retries=None, retry_delay=None):
    """Execute a coroutine with retry logic for SQLite concurrent access issues."""
    while attempts <= max_retries:
        try:
            return await coro
        except OperationalError as e:
            if "database is locked" in str(e).lower():
                # Calculate exponential backoff with jitter
                delay = min(delay_base * (2 ** (attempts - 1)) * (0.5 + random.random()), 
                           self.retry_delay_max)
                await asyncio.sleep(delay)
```

**Retry Features**:
- **Exponential Backoff**: Increasing delays between retry attempts
- **Jitter**: Random component prevents thundering herd
- **Lock Detection**: Specifically handles SQLite locking issues
- **Configurable**: Retry count and delays can be customized

## API Endpoints and Integration

### 1. System Information (`app.py:240-294`)

**Module Registry Endpoint**:
```python
@app.get("/api/v1/modules/registry")
async def get_module_registry():
    """Get information about all loaded modules."""
    modules = []
    for module_id, module_data in app.state.app_context.module_loader.modules.items():
        # Check if the module has a UI module file
        ui_module_exists = check_ui_module_existence(module_id)
        modules.append({
            "id": module_id,
            "name": module_data["manifest"]["name"],
            "has_ui": ui_module_exists
        })
```

**Health Check Endpoint**:
```python
@app.get("/api/v1/system/health")
async def health_check():
    """Check if the backend is running properly."""
    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "timestamp": datetime.now().isoformat()
    }
```

**API Features**:
- **Module Discovery**: UI can discover available modules
- **Health Monitoring**: Simple health check for process monitoring
- **Configuration Export**: Frontend gets necessary configuration
- **Runtime Information**: Session info and uptime tracking

## Best Practices and Patterns

### 1. Async-First Design

**Requirements**:
- All module initialize methods must be async
- Database operations use async sessions
- Post-init hooks are async
- Full event loop integration

**Benefits**:
- **Non-Blocking**: Startup doesn't block on slow operations
- **Concurrent Operations**: Multiple modules can initialize simultaneously
- **Scalability**: Better resource utilization
- **Modern Patterns**: Follows current Python async best practices

### 2. Two-Phase Initialization

**Phase 1 Benefits**:
- **Fast Startup**: Basic services available quickly
- **Dependency Resolution**: Services available for other modules
- **Error Early Detection**: Basic validation before complex operations

**Phase 2 Benefits**:
- **Complex Operations**: Database creation, migrations, external connections
- **Full Context**: All services available for complex operations
- **Graceful Handling**: Non-critical operations can fail without aborting

### 3. Central Context Pattern

**AppContext Advantages**:
- **Single Source of Truth**: All shared state in one place
- **Service Discovery**: Centralized service registry
- **Configuration Management**: Unified settings access
- **Lifecycle Management**: Consistent startup/shutdown handling

### 4. Modular Architecture

**Module Benefits**:
- **Independent Development**: Modules developed separately
- **Optional Features**: Modules can be disabled if not needed
- **Clean Interfaces**: Modules communicate through well-defined APIs
- **Error Isolation**: Module failures don't affect other modules

## Performance Considerations

### 1. Database Connection Management

**Optimization Features**:
- **Connection Pooling**: 20 connections with 10 overflow
- **Connection Health**: Pre-ping ensures connection validity
- **Connection Recycling**: Prevent stale connection issues
- **Async Operations**: Non-blocking database operations

### 2. Module Loading Optimization

**Efficiency Features**:
- **Dependency Caching**: Avoid recomputing dependencies
- **Parallel Loading**: Independent modules can load simultaneously
- **Early Error Detection**: Fail fast on critical module issues
- **Resource Sharing**: Modules share common services

### 3. Memory Management

**Resource Efficiency**:
- **Service Reuse**: Services shared across modules
- **Lazy Initialization**: Complex objects created only when needed
- **Proper Cleanup**: Shutdown handlers ensure resource cleanup
- **Session Tracking**: Monitor resource usage over time

## Conclusion

The Modular Framework's startup process demonstrates a sophisticated approach to application initialization that balances speed, reliability, and flexibility. The combination of two-phase initialization, async-first design, and central context management provides a robust foundation for complex modular applications.

**Key Strengths**:
- **Robust Error Handling**: Graceful degradation when modules fail
- **Modern Async Patterns**: Full async/await support throughout
- **Modular Architecture**: Clean separation and optional components
- **Performance Optimization**: Efficient resource usage and connection management
- **Developer Experience**: Clear logging, warnings, and error reporting
- **Lifecycle Management**: Proper startup and shutdown sequences

This architecture provides excellent patterns for building scalable, maintainable applications while ensuring that the framework remains reliable and performant under various conditions.
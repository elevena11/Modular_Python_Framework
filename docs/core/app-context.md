# Application Context

The Application Context (`core/app_context.py`) is the heart of the framework, serving as the central service container and dependency injection system.

## Overview

The `AppContext` class manages the application's entire lifecycle, from initialization to shutdown. It provides:

- **Service Container**: Central registry for all services
- **Dependency Injection**: Automatic service resolution
- **Session Management**: Unique session tracking
- **Database Management**: SQLite connection pooling
- **Lifecycle Management**: Post-initialization hooks and shutdown handlers
- **Settings Integration**: Module settings management

## Key Features

### 1. Service Container Pattern

The AppContext implements a service container that manages all framework services:

```python
# Register a service
app_context.register_service("my_module.service", service_instance)

# Get a service
service = app_context.get_service("my_module.service")
```

### 2. Session Management

Each application instance gets a unique session identifier:

```python
session_info = app_context.get_session_info()
# Returns:
# {
#     "session_id": "20250716_202514_97373810",
#     "session_uuid": "uuid4-string",
#     "session_start_time": "2025-07-16T20:25:14.375000",
#     "uptime_seconds": 1234,
#     "uptime_human": "0:20:34"
# }
```

### 3. Database Management

The AppContext manages SQLite connections with automatic pooling and retry logic:

```python
# Database session for FastAPI dependency injection
async def get_db():
    db = app_context.db_session()
    try:
        yield db
    finally:
        await db.close()

# Retry logic for database operations
result = await app_context.execute_with_retry(some_async_operation())
```

### 4. Post-Initialization Hooks

The framework supports two-phase initialization with dependency-aware hooks:

```python
# Register a post-init hook
app_context.register_post_init_hook(
    "module.setup",
    service.initialize,
    priority=100,
    dependencies=["core.database.setup"]
)
```

### 5. Shutdown Handlers

Graceful shutdown with registered cleanup handlers:

```python
# Register shutdown handler
app_context.register_shutdown_handler(cleanup_function)

# Run all shutdown handlers
await app_context.run_shutdown_handlers()
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    AppContext                               │
├─────────────────────────────────────────────────────────────┤
│ Services Registry                                           │
│ ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐ │
│ │ core.database   │ │ core.settings   │ │ core.error      │ │
│ │ .service        │ │ .service        │ │ .service        │ │
│ └─────────────────┘ └─────────────────┘ └─────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│ Database Management                                         │
│ ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐ │
│ │ Connection Pool │ │ Session Factory │ │ Retry Logic     │ │
│ └─────────────────┘ └─────────────────┘ └─────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│ Lifecycle Management                                        │
│ ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐ │
│ │ Post-Init Hooks │ │ Shutdown        │ │ Session         │ │
│ │                 │ │ Handlers        │ │ Tracking        │ │
│ └─────────────────┘ └─────────────────┘ └─────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## Initialization Sequence

### 1. AppContext Creation
```python
app_context = AppContext(config)
app_context.initialize()
```

### 2. Database Setup
- Load database URL from config or use default
- Create database directory if needed
- Set up async SQLite engine with connection pooling
- Create session factory

### 3. Service Registration
Modules register their services during Phase 1:
```python
def initialize(app_context):
    service = MyService(app_context)
    app_context.register_service("my_module.service", service)
```

### 4. Post-Initialization Hooks
After all modules are loaded, hooks run in dependency order:
```python
app_context.register_post_init_hook(
    "module.setup",
    service.complex_initialization,
    dependencies=["core.database.setup"]
)
```

## Database Configuration

### Connection Pool Settings
```python
# Async engine configuration
self.db_engine = create_async_engine(
    async_url,
    pool_size=20,             # Base pool size
    max_overflow=10,          # Additional connections
    pool_timeout=30,          # Connection timeout
    pool_recycle=3600,        # Connection lifetime
    pool_pre_ping=True,       # Health checks
    connect_args={
        "check_same_thread": False  # Multi-thread support
    }
)
```

### Retry Logic
The AppContext provides automatic retry for database operations:
```python
async def execute_with_retry(self, coro, retries=None, retry_delay=None):
    # Exponential backoff with jitter
    # Handles "database is locked" errors
    # Configurable retry count and delay
```

## Service Integration

### Module Service Pattern
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

### Service Registration
```python
# In module's api.py
def initialize(app_context):
    service = ModuleService(app_context)
    app_context.register_service("module.service", service)
    
    # Register complex initialization
    app_context.register_post_init_hook(
        "module.setup",
        service.initialize,
        dependencies=["core.database.setup"]
    )
```

## Settings Integration

The AppContext provides comprehensive settings management:

```python
# Register module settings
await app_context.register_module_settings(
    "my_module",
    default_settings={
        "setting1": "value1",
        "setting2": 42
    },
    validation_schema={
        "setting1": {"type": "str"},
        "setting2": {"type": "int", "min": 0}
    }
)

# Get module settings
settings = await app_context.get_module_settings("my_module")

# Update a setting
await app_context.update_module_setting("my_module", "setting1", "new_value")
```

## Error Handling

The AppContext includes robust error handling:

```python
# Startup warnings
app_context.add_warning("Module configuration issue", "warning", "my_module")

# Database retry logic
try:
    result = await app_context.execute_with_retry(database_operation())
except OperationalError as e:
    # Handle database errors after retries exhausted
    pass
```

## Shutdown Management

### Graceful Shutdown
```python
# Register cleanup handler
async def cleanup():
    # Cleanup resources
    pass

app_context.register_shutdown_handler(cleanup)

# During shutdown
await app_context.run_shutdown_handlers()
```

### Force Shutdown
```python
# When event loop is closing
app_context.force_shutdown()  # Synchronous cleanup
```

## Configuration

The AppContext is configured through the config object:

```python
# Required config attributes
config.DATA_DIR = "data"
config.DATABASE_URL = "sqlite:///data/database/"
config.API_PREFIX = "/api/v1"

# Optional retry configuration
app_context.max_retries = 5
app_context.retry_delay_base = 0.1
app_context.retry_delay_max = 2.0
```

## Best Practices

### 1. Service Registration
- Register services early in Phase 1
- Use descriptive service names
- Include module namespace in name

### 2. Database Operations
- Use the provided session factory
- Implement retry logic for critical operations
- Close sessions properly

### 3. Initialization Hooks
- Use appropriate priorities
- Declare dependencies explicitly
- Handle initialization errors gracefully

### 4. Shutdown Handlers
- Register cleanup handlers for resources
- Handle exceptions in shutdown handlers
- Keep shutdown logic simple and fast

## Common Patterns

### Service Access Pattern
```python
class MyService:
    def __init__(self, app_context):
        self.app_context = app_context
        self.database = None
        
    async def initialize(self):
        self.database = self.app_context.get_service("core.database.service")
        return True
```

### Database Operation Pattern
```python
async def database_operation():
    async with app_context.db_session() as db:
        # Perform database operations
        result = await db.execute(query)
        await db.commit()
        return result
```

### Settings Pattern
```python
# Get settings during initialization
settings = await app_context.get_module_settings("my_module")
timeout = settings.get("timeout", 30)
```

## Related Documentation

- [Configuration System](config-system.md) - Configuration management
- [Module Loader](module-loader.md) - Module loading system
- [Database Module](../modules/database-module.md) - Database management
- [Settings Module](../modules/settings-module.md) - Settings system
- [Two-Phase Initialization](../patterns/two-phase-initialization.md) - Initialization patterns

---

The Application Context is the foundation that enables the framework's modular architecture, providing the services and infrastructure that all modules depend on.
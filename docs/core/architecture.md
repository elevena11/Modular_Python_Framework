# Framework Architecture

The Modular Python Framework is designed around three core systems that provide a solid foundation for building scalable applications.

## Core Systems

### 1. Database System
Each module can have its own SQLite database with automatic lifecycle management:

```python
# Clean database operations with automatic session management
async with app_context.database.integrity_session("module_name", "operation_purpose") as session:
    result = await session.execute(query)
    await session.commit()
```

**Key Features:**
- **Multi-database support** - Each module has its own isolated database
- **Automatic discovery** - Framework finds and initializes databases
- **Session management** - Built-in transaction and lifecycle handling
- **Clean separation** - Modules don't interfere with each other's data

### 2. Settings System
Type-safe configuration using Pydantic v2 with environment variable overrides:

```python
class ModuleSettings(BaseModel):
    api_timeout: int = Field(default=30)
    debug_enabled: bool = Field(default=False)

# Environment override: CORE_MODULE_API_TIMEOUT=60
```

**Key Features:**
- **Type validation** - Pydantic v2 ensures configuration correctness
- **Environment overrides** - Easy deployment configuration
- **Default + user preferences** - Flexible configuration layers
- **Module isolation** - Each module manages its own settings

### 3. Error Handling System
Consistent error handling across all framework operations:

```python
async def some_operation() -> Result:
    try:
        data = await process_something()
        return Result.success(data=data)
    except Exception as e:
        return Result.error(
            code="OPERATION_FAILED",
            message="Processing failed",
            details={"error": str(e)}
        )
```

**Key Features:**
- **Result pattern** - Consistent success/error handling
- **Structured errors** - Standardized error information
- **No exceptions** - Explicit error handling in business logic
- **Debugging support** - Rich error context and logging

## Module Architecture

### Module Structure
```
modules/standard/my_module/
├── api.py              # Module registration and FastAPI routes
├── services.py         # Business logic implementation  
├── settings.py         # Pydantic v2 configuration schema
├── database.py         # Database operations (optional)
├── db_models.py        # SQLAlchemy models (optional)
└── api_schemas.py      # API request/response models (optional)
```

### Module Registration
Modules use decorators for clean registration:

```python
# api.py
@register_service("my_module.service")
@register_api_endpoints("router")
class MyModule(DataIntegrityModule):
    MODULE_ID = "standard.my_module"
    MODULE_VERSION = "1.0.0"
    MODULE_DESCRIPTION = "My application module"
```

## Two-Phase Initialization

The framework initializes in two distinct phases to handle dependencies properly:

### Phase 1: Registration
- **Infrastructure setup** - Create directories, configure logging
- **Service registration** - Register services with the framework
- **Settings registration** - Register Pydantic v2 configuration models
- **No service access** - Services are not yet available

### Phase 2: Complex Initialization  
- **Service dependencies** - Access other framework services
- **Database operations** - Set up tables, initial data
- **External connections** - Connect to APIs, external systems
- **Full framework access** - All services are available

```python
def setup_infrastructure(self):
    # Phase 1: Infrastructure only
    self.logger.info("Setting up module infrastructure")

async def initialize_service(self):
    # Phase 2: Access other services
    settings_service = self.app_context.get_service("core.settings.service")
    await self.setup_database_tables()
```

## Service Discovery

The framework automatically discovers and registers services:

1. **Scan modules** - Find all modules in `modules/core/` and `modules/standard/`
2. **Load decorators** - Process `@register_service` and `@register_api_endpoints`
3. **Build dependency graph** - Determine initialization order
4. **Two-phase initialization** - Register then initialize services
5. **API routing** - Automatically configure FastAPI routes

## Application Lifecycle

```
Startup → Module Discovery → Phase 1 → Phase 2 → Ready
    ↓           ↓              ↓         ↓        ↓
Bootstrap → Load Modules → Register → Initialize → Serve
```

### Startup Process
1. **Bootstrap** - Create essential directories and logging
2. **Module Discovery** - Scan for modules and load decorators
3. **Phase 1** - Infrastructure setup and registration
4. **Phase 2** - Complex initialization with dependencies
5. **API Setup** - Configure FastAPI routes and documentation
6. **Ready** - Application ready to serve requests

## Development Patterns

### Adding New Functionality
1. **Use scaffolding** - `python tools/scaffold_module.py --name my_feature`
2. **Implement services** - Add business logic to `services.py`
3. **Configure settings** - Define configuration in `settings.py`
4. **Add API endpoints** - Create routes in `api.py`
5. **Test compliance** - `python tools/compliance/compliance.py --validate standard.my_feature`

### Disabling Modules
Any module can be temporarily disabled by creating a `.disabled` file in its directory:

```bash
# Disable a standard module
touch modules/standard/my_module/.disabled

# Disable a core module (advanced - may break framework functionality)
touch modules/core/model_manager/.disabled

# Re-enable by removing the file
rm modules/standard/my_module/.disabled
```

**How it works:**
- Framework scans for modules but skips any with `.disabled` files
- Module is completely ignored during initialization
- No services registered, no API endpoints loaded, no database operations
- Useful for troubleshooting, testing, or permanently removing unwanted features

### Database Operations
Always use the integrity session pattern:
```python
async with app_context.database.integrity_session("my_module", "create_user") as session:
    user = User(name="John", email="john@example.com")
    session.add(user)
    await session.commit()
    return user.id
```

### Settings Management
Define typed settings for your module:
```python
class MyModuleSettings(BaseModel):
    model_config = ConfigDict(env_prefix="CORE_MY_MODULE_")
    
    max_connections: int = Field(default=10)
    timeout_seconds: int = Field(default=30)
```

### Error Handling
Use the Result pattern consistently:
```python
result = await some_operation()
if result.success:
    data = result.data
    # Handle success case
else:
    logger.error(f"Operation failed: {result.message}")
    # Handle error case
```

## Framework Benefits

### For Developers
- **Rapid development** - Scaffolding and patterns speed up coding
- **Consistent patterns** - Same approach across all modules
- **Built-in tooling** - Compliance checking, testing, debugging tools
- **Clear separation** - Database, settings, and errors handled cleanly

### For Applications
- **Scalable architecture** - Add modules without affecting others
- **Type safety** - Pydantic v2 ensures configuration correctness
- **Maintainable code** - Clear patterns and error handling
- **Production ready** - Logging, monitoring, and deployment support

The framework handles all the complex infrastructure so you can focus on building your application's unique functionality.
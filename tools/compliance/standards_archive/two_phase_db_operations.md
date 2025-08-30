# Two-Phase DB Operations Standard

**Version: 1.0.0**
**Updated: March 20, 2025**

## Purpose

This standard ensures that modules follow the framework's two-phase initialization pattern with respect to database operations. Database access must not occur during Phase 1 of module initialization. Database operations can be performed any time after Phase 1 is complete.

## Rationale

1. **Dependency Resolution**: Database service may not be fully initialized during Phase 1
2. **Migration Ordering**: Database tables need to be created in the correct order
3. **Deadlock Prevention**: Concurrent database operations during initialization can cause deadlocks
4. **Reliable Startup**: Ensures a predictable and reliable application startup sequence
5. **Error Isolation**: Prevents errors in database operations from affecting core service registration

## Requirements

### Phase 1 Constraints

In the module's `initialize(app_context)` function:
- **NO** direct database operations
- **NO** use of database sessions or connections
- **NO** model operations or queries
- **DO** register services, hooks, and models only

### Phase 2 and Runtime Operations (If Needed)

If a module needs database access, it can use the database:

1. During Phase 2 via a setup hook
2. During normal runtime operation (API handlers, services, etc.)
3. At any other time after Phase 1 is complete

The key requirement is simply to avoid database operations during Phase 1 initialization.

## Implementation Guide

### Phase 1: Registration Only

```python
def initialize(app_context):
    """Phase 1: Register services and hooks."""
    logger.info("Initializing module (Phase 1)")
    
    # Create and register service
    my_service = MyService(app_context)
    app_context.register_service("module.my_service", my_service)
    
    # Register models (if any)
    from .models import MyModel
    app_context.register_models([MyModel])
    
    # If database operations are needed, register for Phase 2
    if needs_database_access:
        app_context.register_module_setup_hook(
            module_id="my.module.id",
            setup_method=setup_module
        )
    
    return True
```

### Phase 2: Database Operations (If Needed)

```python
async def setup_module(app_context):
    """Phase 2: Execute database operations (if needed)."""
    logger.info("Setting up module database (Phase 2)")
    
    # Get database service
    db_service = app_context.get_service("db_service")
    
    # Check if database is initialized
    if db_service and db_service.is_initialized():
        try:
            # Perform database operations
            # ...
            return True
        except Exception as e:
            logger.error(f"Error setting up module database: {str(e)}")
            return False
    else:
        logger.warning("Database not initialized, skipping module setup")
        return False
```

## Common Issues and Solutions

### Common Violations

1. **Database Access in Phase 1**: Attempting to use the database in the initialize function
   - Solution: Move all database operations to a Phase 2 setup method

2. **Missing Setup Hook**: Not registering a setup hook when database operations are needed
   - Solution: Use `app_context.register_module_setup_hook()` to register Phase 2 initialization

### Fixing Violations

To fix Phase 1 database access:

```python
# INCORRECT: Database access in Phase 1
def initialize(app_context):
    db_service = app_context.get_service("db_service")
    async with db_service.session() as session:
        # ... database operations

# CORRECT: Move to Phase 2
def initialize(app_context):
    # Only register a hook if database operations are needed
    app_context.register_module_setup_hook("module.id", setup_module)

async def setup_module(app_context):
    db_service = app_context.get_service("db_service")
    if db_service and db_service.is_initialized():
        async with db_service.session() as session:
            # ... database operations
```

## Validation

The standard primarily checks for anti-patterns:

1. **No Database Access in Phase 1**: The `initialize()` function should not contain database operations
2. **Initializer Check**: Module must have an initialize function to validate

A module passes validation if it doesn't attempt database operations during Phase 1 initialization.

## FAQ

**Q: What if my module doesn't need database access?**
A: If your module doesn't use the database at all, you don't need to implement a Phase 2 setup method. You'll still pass this standard as long as you don't attempt database operations in Phase 1.

**Q: Do I have to use Phase 2 setup hooks for database operations?**
A: No, Phase 2 setup hooks are just one option for database operations. You can also perform database operations during normal runtime operations like API handlers. The only requirement is to avoid database operations during Phase 1.

**Q: When can I use the database after Phase 1?**
A: You can use the database any time after Phase 1 is complete. This includes Phase 2 initialization, API endpoint handlers, service methods, or any other post-initialization code. The only restriction is that database operations must not happen during Phase 1 initialization.

**Q: Can I register models in Phase 1?**
A: Yes, you should register models using `app_context.register_models()` during Phase 1. The actual table creation happens during Phase 2 of the database module's initialization.
# Two-Phase Initialization Pattern

**Version: 1.1.0**

## Purpose

This standard defines the two-phase initialization pattern for modules in the Modular AI Framework. The pattern provides a solution to dependency challenges and ensures that modules initialize in a controlled, predictable manner regardless of load order.

## Rationale

1. **Dependency Management**: Modules depend on each other but can't predict initialization order
2. **Database Operations**: Database tables and records must exist before use but can't be created until all models are registered
3. **Asynchronous Operations**: Complex initialization may require asynchronous operations
4. **Clean Separation**: Registration of services should be separated from their complex initialization
5. **Resource Management**: External resources should be accessed after registration phase to prevent blocking

## Core Design Principles

### 1. Registration Before Use

Modules must register all their components (services, hooks, models) before any module attempts to use them. This allows modules to be discovered regardless of load order.

### 2. Database Operations After Registration

Database tables can only be created after all models are registered, which happens after the registration phase.

### 3. Conditional Phase 2

Not all modules require Phase 2 initialization. Simple modules may complete all their setup in Phase 1.

## Implementation Guide

### Phase 1: Registration Phase

All modules implement Phase 1 in the `initialize` function in api.py:

```python
def initialize(app_context):
    """Phase 1: Register services and hooks."""
    # Create and register service
    my_service = MyService(app_context)
    app_context.register_service("my_service", my_service)
    
    # Register models if any
    from .models import MyModel
    app_context.register_models([MyModel])
    
    # Register settings
    from .module_settings import register_settings
    register_settings(app_context)
    
    # For modules that need Phase 2, register setup hook
    app_context.register_module_setup_hook(
        module_id="module.id",
        setup_method=setup_module
    )
    
    return True
```

**Phase 1 Constraints**:
- No database operations (create_tables, session operations)
- No asynchronous operations (no await)
- No direct access to other modules' internal structures
- No complex initialization of services

### Foundation Services (Phase 1.5)

After all modules complete Phase 1 registration, the framework internally runs special hooks for foundation services:

1. **Database Finalization**: Creates tables and runs migrations
2. **Settings Service**: Loads and initializes all module settings
3. **Other Foundation Services**: Any other critical services

This is handled by the framework, not by normal modules. This phase ensures that database and settings are fully ready before Phase 2 begins.

### Phase 2: Setup Phase

Modules that need Phase 2 implement an async `setup_module` function:

```python
async def setup_module(app_context):
    """Phase 2: Execute complex initialization operations."""
    # Check if database is initialized
    db_service = app_context.get_service("db_service")
    if db_service and db_service.is_initialized():
        try:
            # Perform database operations
            my_service = app_context.get_service("my_service")
            await my_service.initialize_database()
            
            # Access external resources
            await my_service.connect_to_external_service()
            
            # Use settings
            settings = app_context.get_module_settings("my.module.id")
            my_service.configure(settings)
            
            return True
        except Exception as e:
            logger.error(f"Error in Phase 2 initialization: {str(e)}")
            return False
    
    return False
```

**When to Implement Phase 2**:
- When your module needs to create database records
- When initialization requires asynchronous operations
- When initialization depends on settings or other modules' services
- When you need to access external resources during initialization

**When Phase 2 is Optional**:
- For simple utility modules without database operations
- When all initialization can be completed synchronously in Phase 1
- When a module provides only stateless services
- When a module has no dependencies on database or settings

## Implementation Options

### 1. Phase 1 Only (Simple Modules)

For modules that don't need complex initialization:

```python
def initialize(app_context):
    """Only Phase 1 needed for simple modules."""
    # Create and register service
    utility_service = UtilityService()
    app_context.register_service("utility_service", utility_service)
    
    # No Phase 2 registration needed
    return True
```

### 2. Both Phases (Complex Modules)

For modules that need database operations or complex async initialization:

```python
def initialize(app_context):
    """Phase 1: Registration."""
    # Create and register service
    complex_service = ComplexService(app_context)
    app_context.register_service("complex_service", complex_service)
    
    # Register for Phase 2
    app_context.register_module_setup_hook(
        module_id="module.id",
        setup_method=setup_module
    )
    
    return True

async def setup_module(app_context):
    """Phase 2: Complex initialization."""
    db_service = app_context.get_service("db_service")
    if not db_service or not db_service.is_initialized():
        return False
        
    try:
        # Database operations
        await db_service.create_default_records("module_name")
        return True
    except Exception as e:
        logger.error(f"Error in Phase 2: {str(e)}")
        return False
```

## Common Issues and Solutions

### 1. Database Operations in Phase 1

**Problem**:
```python
def initialize(app_context):
    # ERROR: Database operations in Phase 1
    db_service = app_context.get_service("db_service")
    with db_service.session() as session:
        session.add(DefaultRecord())
```

**Solution**:
```python
def initialize(app_context):
    # Register for Phase 2
    app_context.register_module_setup_hook(
        module_id="module.id",
        setup_method=setup_module
    )

async def setup_module(app_context):
    # Correct: Database operations in Phase 2
    db_service = app_context.get_service("db_service")
    if db_service and db_service.is_initialized():
        async with db_service.async_session() as session:
            session.add(DefaultRecord())
            await session.commit()
```

### 2. Accessing Services Without Checking in Phase 2

**Problem**:
```python
async def setup_module(app_context):
    # ERROR: No existence check
    return app_context.get_service("other_service").initialize()
```

**Solution**:
```python
async def setup_module(app_context):
    # Correct: Check if service exists
    other_service = app_context.get_service("other_service")
    if not other_service:
        logger.warning("Other service not available")
        return False
    
    return await other_service.initialize()
```

### 3. Async Operations in Phase 1

**Problem**:
```python
def initialize(app_context):
    # ERROR: Async operations in Phase 1
    import asyncio
    asyncio.run(initialize_async())
```

**Solution**:
```python
def initialize(app_context):
    # Register for Phase 2
    app_context.register_module_setup_hook(
        module_id="module.id",
        setup_method=setup_module
    )

async def setup_module(app_context):
    # Correct: Async operations in Phase 2
    await initialize_async()
```

## Documentation for Intentional Non-Compliance

For modules that intentionally don't implement Phase 2, document this in the Exceptions section of compliance.md:

```markdown
## Exceptions
- Two-Phase Initialization Pattern: This module doesn't require Phase 2 initialization as it has no database operations or complex initialization needs.
```

## Validation

This standard validates:

1. Phase 1 implementation (`initialize` function in api.py)
2. Phase 2 hook registration and implementation (if applicable)
3. Anti-patterns for database or async operations in Phase 1

The validation recognizes that not all modules require Phase 2, but enforces that any database operations must be done in Phase 2, not Phase 1.

## FAQ

**Q: Does every module need to implement Phase 2?**  
A: No. Simple modules that don't require database operations or complex initialization can complete all their setup in Phase 1.

**Q: What about modules that have circular dependencies?**  
A: The two-phase pattern helps solve this. All modules register their services in Phase 1, then use these services in Phase 2, preventing circular initialization issues.

**Q: Can I do simple configurations using settings in Phase 1?**  
A: Yes, if you're only reading settings (not writing them) and not performing complex operations, you can use settings in Phase 1.

**Q: How does the framework know when to start Phase 2?**  
A: The framework waits for all modules to complete Phase 1, then runs special hooks for foundation services (database, settings) before starting Phase 2 module setups.

**Q: What happens if a module's Phase 2 setup fails?**  
A: The framework logs errors but continues with other modules' setups. Your module should implement appropriate error handling and fallbacks.

**Q: Should I perform cleanup operations in Phase 2?**  
A: No, Phase 2 is for initialization. For cleanup, register application shutdown hooks instead.
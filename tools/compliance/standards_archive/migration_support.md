# Migration Support Standard

**Version: 1.0.0**
**Updated: March 20, 2025**

## Purpose

This standard ensures that modules properly support database migrations by registering models with the application context and following migration-compatible patterns. It validates that database models are defined in a way that works with the framework's migration system.

## Rationale

1. **Schema Evolution**: Enables clean database schema updates without data loss
2. **Consistency**: Ensures all modules follow the same approach to model definitions
3. **Central Management**: Allows the core database module to manage migrations
4. **Reliability**: Prevents schema conflicts and inconsistencies
5. **Compatibility**: Ensures models work with SQLite-compatible migrations

## Requirements

For modules that define database models:

1. **Proper Base Class**: Models must inherit from the Base class provided by the database module
2. **Model Registration**: Models must be registered with the application context
3. **No Direct Table Creation**: Models should not create tables directly
4. **Migration Compatibility**: Model definitions should be compatible with Alembic migrations

## Implementation Guide

### Defining Models

Models should inherit from the Base class provided by the database module:

```python
from sqlalchemy import Column, Integer, String
from modules.core.database.models import Base, SQLiteJSON

class MyModel(Base):
    __tablename__ = "my_models"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    metadata = Column(SQLiteJSON, nullable=True, default=dict)
```

### Registering Models

Models should be registered with the application context during Phase 1 initialization:

```python
def initialize(app_context):
    """Initialize the module."""
    # Import models
    from .models import MyModel, AnotherModel
    
    # Register models with the application context
    app_context.register_models([MyModel, AnotherModel])
    
    # Other initialization...
    
    return True
```

### Avoiding Direct Table Creation

**Do not** create tables directly:

```python
# INCORRECT: Creating tables directly
def initialize(app_context):
    Base.metadata.create_all(bind=engine)  # Don't do this
    
# INCORRECT: Creating specific tables
def initialize(app_context):
    MyModel.__table__.create(bind=engine)  # Don't do this
```

Let the database module handle table creation based on registered models.

## Common Issues and Solutions

### Common Violations

1. **Missing Model Registration**: Not registering models with the application context
   - Solution: Add `app_context.register_models([Model1, Model2])` in `initialize()`

2. **Direct Table Creation**: Creating tables directly instead of registering models
   - Solution: Remove direct table creation calls and register models instead

3. **Incorrect Base Class**: Using SQLAlchemy's declarative_base() directly
   - Solution: Import and use `Base` from `modules.core.database.models`

4. **Missing Models File**: No models.py file in a module that needs models
   - Solution: Create a proper models.py file with properly defined models

### Fixing Violations

To fix missing model registration:

```python
# Add to initialize() function
from .models import MyModel, AnotherModel
app_context.register_models([MyModel, AnotherModel])
```

To fix direct table creation:

```python
# BEFORE:
def initialize(app_context):
    engine = app_context.db_engine
    MyModel.__table__.create(bind=engine, checkfirst=True)

# AFTER:
def initialize(app_context):
    from .models import MyModel
    app_context.register_models([MyModel])
    # Database module will handle table creation
```

## Validation

The standard checks for:

1. **Model Definitions**: Proper use of the Base class for model definitions
2. **Model Registration**: Calling register_models with the application context
3. **Anti-patterns**: Direct table creation calls

Note that this standard only applies to modules that define database models. Modules without models automatically pass this standard.

## FAQ

**Q: Does every module need to define models?**
A: No, only modules that need to store data in the database need to define models. This standard only applies to modules that define database models.

**Q: Where should I define database models?**
A: Models should be defined in a `models.py` file in your module, and they should inherit from the Base class provided by the database module.

**Q: Can I use my own Base class?**
A: No, you must use the Base class from `modules.core.database.models` to ensure compatibility with the migration system.

**Q: Why shouldn't I create tables directly?**
A: Direct table creation bypasses the migration system, which can lead to schema inconsistencies, migration errors, and potential data loss during updates.

**Q: When are tables actually created?**
A: Tables are created during Phase 2 of the database module's initialization, after all modules have registered their models.
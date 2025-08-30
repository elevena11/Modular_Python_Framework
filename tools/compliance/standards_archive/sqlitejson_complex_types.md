# SQLiteJSON for Complex Types Standard

**Version: 1.0.0**
**Updated: March 20, 2025**

## Purpose

This standard ensures that modules use the `SQLiteJSON` type decorator for complex data types (dictionaries, lists, JSON objects) in database models. Using `SQLiteJSON` provides proper serialization and deserialization of complex data structures when working with SQLite.

## Rationale

1. **Data Integrity**: Ensures proper serialization/deserialization of complex data types
2. **Query Safety**: Prevents errors when querying or filtering JSON data
3. **Schema Compatibility**: Enables migration compatibility with complex data
4. **Standardized Handling**: Consistent approach across all modules
5. **Performance Optimization**: Reduces overhead in database operations with complex data

## Requirements

When defining SQLAlchemy models with complex data fields:

1. **Use SQLiteJSON**: For any field that will store dictionaries, lists, or JSON data
2. **Proper Import**: Import SQLiteJSON from the core database models module
3. **Default Values**: Set appropriate default values for complex fields (e.g., `default=dict` for dictionaries)
4. **No Raw Text**: Don't use Text or String columns for storing complex data

## Implementation Guide

### Correct Implementation

```python
from sqlalchemy import Column, Integer, String
from modules.core.database.models import Base, SQLiteJSON

class MyModel(Base):
    __tablename__ = "my_models"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    metadata = Column(SQLiteJSON, nullable=True, default=dict)  # Dictionary
    tags = Column(SQLiteJSON, nullable=True, default=list)      # List
    config = Column(SQLiteJSON, nullable=True)                  # Generic JSON
```

### Incorrect Implementation

```python
# INCORRECT: Using Text for JSON data
from sqlalchemy import Column, Integer, String, Text
from modules.core.database.models import Base

class MyModel(Base):
    __tablename__ = "my_models"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    metadata = Column(Text, nullable=True)  # Should use SQLiteJSON
    tags = Column(Text, nullable=True)      # Should use SQLiteJSON
```

### Setting Default Values

Default values should match the expected data type:

```python
# For dictionaries
metadata = Column(SQLiteJSON, nullable=True, default=dict)

# For lists
tags = Column(SQLiteJSON, nullable=True, default=list)

# For nullable fields with no default
config = Column(SQLiteJSON, nullable=True)

# For required fields (not nullable)
required_config = Column(SQLiteJSON, nullable=False, default=lambda: {"version": "1.0.0"})
```

## Common Issues and Solutions

### Common Violations

1. **Using Text for JSON**: Using `Text` or `String` columns for storing JSON data
   - Solution: Replace with `SQLiteJSON` type

2. **Missing Import**: Not importing SQLiteJSON correctly
   - Solution: Import using `from modules.core.database.models import Base, SQLiteJSON`

3. **Incorrect Default**: Missing or inappropriate default values
   - Solution: Use `default=dict` for dictionaries, `default=list` for lists

4. **Manual Serialization**: Manually serializing/deserializing JSON in code
   - Solution: Let SQLiteJSON handle serialization/deserialization automatically

### Fixing Violations

When fixing a `Text` column to use `SQLiteJSON`:

```python
# BEFORE:
metadata = Column(Text, nullable=True)

# AFTER:
from modules.core.database.models import SQLiteJSON
metadata = Column(SQLiteJSON, nullable=True, default=dict)
```

If you need to migrate existing data:

```python
# In a migration script
def upgrade():
    # Update column type to SQLiteJSON (SQLite supports this directly)
    op.alter_column('my_models', 'metadata', 
                    existing_type=sa.Text(), 
                    type_=SQLiteJSON,
                    existing_nullable=True)
    
    # Update any NULL values to empty dictionaries/lists
    op.execute("UPDATE my_models SET metadata = '{}' WHERE metadata IS NULL")
```

## Validation

The standard checks for:

1. **Import Pattern**: Proper import of SQLiteJSON from database models
2. **Usage Pattern**: Use of SQLiteJSON in column definitions
3. **Anti-patterns**: 
   - Using Text/String with dictionary/list defaults
   - Comments indicating JSON storage in Text columns

A module passes validation if it properly imports and uses SQLiteJSON for complex data types.

## FAQ

**Q: What types of data should use SQLiteJSON?**
A: Any field that will store dictionaries, lists, or structured data that would normally be serialized as JSON.

**Q: Does SQLiteJSON have performance implications?**
A: SQLiteJSON adds minimal overhead for serialization/deserialization but provides significant benefits in data integrity and query safety.

**Q: Can I query fields inside a SQLiteJSON column?**
A: Basic querying is supported, but complex querying within JSON data requires custom SQL or additional utilities.

**Q: What about PostgreSQL's JSONB type?**
A: For PostgreSQL databases, a separate JSONType might be used, but our standard focuses on SQLite compatibility.

**Q: Do I need migrations when changing from Text to SQLiteJSON?**
A: Yes, a migration script should be created to change the column type and handle any data conversion.
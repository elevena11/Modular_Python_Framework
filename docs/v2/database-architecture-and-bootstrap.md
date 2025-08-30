# Database Architecture and Bootstrap System

## Overview

The Reality Anchor Hub uses a **multi-database, compile-time schema discovery** system that creates complete databases during bootstrap. This approach ensures all database schemas are discovered, compiled, and created in a single operation before any modules start.

## Bootstrap Database Compilation Process

### Phase 1: Schema Discovery
The bootstrap system automatically scans all modules for `db_models.py` files:

```
modules/
├── core/
│   ├── database/db_models.py      → framework database
│   ├── error_handler/db_models.py → framework database  
│   └── settings/db_models.py      → framework database
└── standard/
    ├── semantic_core/db_models.py → semantic_core database
    └── vector_operations/db_models.py → vector_operations database
```

### Phase 2: Schema Compilation
For each discovered `db_models.py`:
1. Import the module to trigger SQLAlchemy model registration
2. Extract the `DATABASE_NAME` constant
3. Collect all table definitions from the module's base class
4. Group tables by database name

### Phase 3: Database Creation
Create complete databases in single operation:
- **framework.db**: Contains all core module tables (9+ tables)
- **module_name.db**: Contains module-specific tables

## Database Architecture

### Multi-Database Support
Each module can define its own database or share the framework database:

```python
# Framework database (shared)
DATABASE_NAME = "framework"

# Module-specific database (isolated)
DATABASE_NAME = "semantic_core"
```

### Single Source of Truth
- **Original files are authoritative**: No content previews or cached data
- **Database contains metadata only**: Hashes, timestamps, file paths
- **Real-time content access**: Always read from original source files

## Standard db_models.py Pattern

Every module follows the same consistent pattern:

```python
"""
modules/standard/module_name/db_models.py
Database models for the module_name module.
"""

# Database configuration for file-based discovery
DATABASE_NAME = "module_name"  # or "framework" for shared

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean
from core.database import DatabaseBase, SQLiteJSON

# Get database base for this module
ModuleBase = DatabaseBase(DATABASE_NAME)

class MyTable(ModuleBase):
    """Table description."""
    __tablename__ = "my_table"
    __table_args__ = {'extend_existing': True}  # Optional: for table updates
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, index=True)
    data = Column(SQLiteJSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    def __repr__(self):
        return f"<MyTable(id={self.id}, name='{self.name}')>"
```

## Key Requirements

### 1. DATABASE_NAME Constant
**Required for bootstrap discovery:**
```python
DATABASE_NAME = "module_name"  # Must be at module level
```

### 2. Import from core.database
**Centralized database utilities:**
```python
from core.database import DatabaseBase, SQLiteJSON
```

### 3. Use DatabaseBase() Pattern
**Modern pattern (not get_database_base):**
```python
ModuleBase = DatabaseBase(DATABASE_NAME)
```

### 4. Follow Table Conventions
```python
class MyTable(ModuleBase):
    __tablename__ = "table_name"  # Snake case
    __table_args__ = {'extend_existing': True}  # For flexibility
```

## Database Types

### Framework Database (`framework.db`)
**Shared database for core system tables:**
- Module registry (`modules`)
- Settings management (`settings_*`)  
- Error handling (`error_*`)
- Framework metadata

**Usage:**
```python
DATABASE_NAME = "framework"
```

### Module-Specific Databases
**Isolated databases for module data:**
- `semantic_core.db` - Document registry and analysis
- `vector_operations.db` - Vector embeddings and similarity
- `decorator_validation.db` - Validation metadata

**Usage:**
```python
DATABASE_NAME = "module_name"  # Creates module_name.db
```

## Bootstrap Log Example

```
INFO - core.bootstrap - Bootstrap: Compiling database schema...
INFO - core.bootstrap - Bootstrap: Scanning modules for database schemas...
INFO - core.bootstrap - framework: Database created with 9 tables from modules: core.database, core.error_handler, core.settings, core.framework
INFO - core.bootstrap - semantic_core: Database created with 6 tables from modules: standard.semantic_core
INFO - core.bootstrap - vector_operations: Database created with 4 tables from modules: standard.vector_operations
INFO - core.bootstrap - Bootstrap: Created 3 complete databases: framework, semantic_core, vector_operations
INFO - core.bootstrap - Bootstrap: Database compilation complete
```

## Benefits

### 1. Compile-Time Schema Discovery
- All schemas discovered before runtime
- Single database creation operation
- No runtime schema conflicts

### 2. Multi-Database Isolation
- Modules can have isolated databases
- Framework tables stay in core database  
- Clear separation of concerns

### 3. Consistent Patterns
- Every db_models.py follows same structure
- Standardized imports from core.database
- Modern DatabaseBase() pattern throughout

### 4. Bootstrap Reliability
- Complete database creation before any module starts
- All dependencies resolved at bootstrap
- Clean startup with full schema validation

## Migration from Old Patterns

### Old Pattern (Deprecated)
```python
from modules.core.database.db_models import get_database_base
Base = get_database_base(DATABASE_NAME)
```

### New Pattern (Current)
```python
from core.database import DatabaseBase
Base = DatabaseBase(DATABASE_NAME)
```

The bootstrap system automatically handles both patterns during transition, but all new modules should use the modern `DatabaseBase()` pattern.

## Development Workflow

1. **Create db_models.py** with `DATABASE_NAME` constant
2. **Import from core.database** - never from modules/
3. **Use DatabaseBase()** pattern for base class creation
4. **Define tables** inheriting from module base
5. **Bootstrap discovers automatically** - no manual registration needed
6. **Test with fresh database** - `rm data/database/*.db && python app.py`

This architecture provides a robust, scalable foundation for multi-database applications with compile-time schema validation and runtime isolation.
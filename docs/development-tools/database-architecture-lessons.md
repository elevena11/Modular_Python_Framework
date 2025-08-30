# Database Architecture Lessons Learned

## Overview

During the implementation of the Semantic Document Analyzer CLI, we discovered critical insights about this framework's **unique database architecture**. This is NOT a standard database implementation - it has custom patterns that differ significantly from typical SQLAlchemy/ORM approaches.

## Key Discovery: Framework-Specific Database Patterns

### ❌ **What We Initially Assumed (Standard Approach)**
- Direct model imports in service methods
- Standard SQLAlchemy session management
- Per-module database components
- Direct CRUD operations with model classes

### ✅ **What This Framework Actually Uses**

#### 1. **Centralized Database Management**
```python
# ❌ WRONG: Creating module-specific database components
class ModuleDatabaseOperations:
    def __init__(self):
        # Custom database operations
        pass

# ✅ CORRECT: Use centralized core.database
crud_service = self.app_context.get_service("core.database.crud_service")
```

#### 2. **Table-Driven Database Creation**
```python
# ✅ CORRECT: Framework automatically discovers and creates databases
DATABASE_NAME = "module_name"  # Required constant
ModuleBase = get_database_base(DATABASE_NAME)  # Framework utility

class MyTable(ModuleBase):
    __tablename__ = "my_table"
    # Framework handles creation during initialization
```

#### 3. **Model Import Restrictions**
```python
# ❌ WRONG: Importing models in service methods causes conflicts
def service_method(self):
    from .db_models import Document  # Causes "Table already defined" error
    
# ✅ CORRECT: Models are registered during framework initialization
# Don't import models in service methods after initialization
```

#### 4. **Session Factory Pattern**
```python
# ✅ CORRECT: Use framework's session factory
session_factory = self.database_service.get_database_session("database_name")
async with session_factory() as session:
    # Database operations here
```

## Critical Errors We Encountered

### 1. **Table Metadata Conflicts**
```
Error: Table 'documents' is already defined for this MetaData instance. 
Specify 'extend_existing=True' to redefine options and columns on an existing Table object.
```

**Root Cause**: Importing models in service methods after framework initialization
**Solution**: Avoid model imports in service methods; use framework's CRUD service

### 2. **Missing get_model() Method**
```
Error: 'AppContext' object has no attribute 'get_model'
```

**Root Cause**: Assuming standard model registry patterns
**Solution**: Use framework's database utilities instead of direct model access

### 3. **CRUD Service Integration Issues**
```
Error: CRUD service expects model classes but causes conflicts
```

**Root Cause**: Mixing framework CRUD with direct model operations
**Solution**: Use session factory pattern as documented

## Critical Architecture Fix: Infrastructure Separation

### **The Problem We Discovered**
During semantic engineering work, we found a critical architectural inconsistency in database infrastructure usage:

```python
# WRONG: Mixed responsibilities in db_models.py
FrameworkBase = get_database_base("framework")  # Infrastructure call at import time

# WRONG: Inconsistent import patterns
from modules.core.database.database_infrastructure import get_database_base  # Some modules
from modules.core.database.db_models import get_database_base  # Other modules
```

### **The Root Issue**
- **Mixed Responsibilities**: `db_models.py` was both model definitions AND infrastructure re-export hub
- **Import-Time Infrastructure Calls**: `get_database_base()` called during module import
- **Inconsistent Patterns**: Some modules imported from `db_models`, others from `infrastructure`
- **Semantic Confusion**: `database_infrastructure.py` suggested general module usage

### **The Correct Architecture**

#### ✅ **Infrastructure Isolation**
```python
# database_infrastructure.py - ONLY for framework setup
# Should NOT be imported directly by modules
def get_database_base(database_name: str):
    # Pure infrastructure for framework initialization
```

#### ✅ **Single Contact Surface**  
```python
# db_models.py - Single contact surface for modules
from modules.core.database.database_infrastructure import get_database_base, SQLiteJSON

# Lazy loading to avoid import-time infrastructure calls
def get_framework_base():
    global _framework_base
    if _framework_base is None:
        _framework_base = get_database_base("framework")
    return _framework_base
```

#### ✅ **Consistent Module Pattern**
```python
# ALL modules use this pattern:
from modules.core.database.db_models import get_database_base, SQLiteJSON

# NEVER import directly from infrastructure:
# from modules.core.database.database_infrastructure import ...  # WRONG
```

### **Key Lessons**
1. **Infrastructure should be isolated** from module interfaces
2. **Single contact surface** prevents confusion and inconsistency  
3. **Lazy loading** prevents import-time infrastructure execution
4. **Semantic naming** guides correct usage patterns
5. **Consistent patterns** across all modules prevent architectural drift

### **Impact of Fix**
- ✅ No infrastructure execution during module imports
- ✅ Clear architectural boundaries between infrastructure and modules
- ✅ Single contact surface eliminates import confusion
- ✅ Consistent patterns across all modules
- ✅ Proper lazy loading prevents premature initialization

## Framework-Specific Patterns

### 1. **Database Discovery System**
```python
# Framework automatically discovers databases from db_models.py files
DATABASE_NAME = "semantic_core"  # Must be defined
```

### 2. **Multi-Database Architecture**
- **framework.db**: Core framework data
- **module_name.db**: Module-specific data
- **Automatic creation**: Framework handles all database creation

### 3. **Model Registration Process**
```python
# Framework registers models during initialization
# Phase 1: Discovery and registration
# Phase 2: Service initialization
# Don't interfere with this process
```

## Best Practices Learned

### ✅ **DO:**
1. **Read the database documentation first** - this framework is unique
2. **Use core.database.crud_service** for all database operations
3. **Follow session factory pattern** for database access
4. **Let framework handle model registration** during initialization
5. **Use database utilities** provided by framework
6. **Import from db_models.py only** - single contact surface for database infrastructure
7. **Use lazy loading patterns** to avoid import-time infrastructure calls

### ❌ **DON'T:**
1. **Create module-specific database components** - use centralized approach
2. **Import models in service methods** - causes metadata conflicts
3. **Assume standard SQLAlchemy patterns** - this framework is different
4. **Mix CRUD approaches** - stick to framework's patterns
5. **Try to manage database creation manually** - framework handles it
6. **Import directly from database_infrastructure.py** - violates architectural boundaries
7. **Call infrastructure at import time** - use lazy loading instead

## Documentation References

Essential reading before database work:
- `docs/modules/database-module.md` - **READ THIS FIRST**
- Database documentation shows correct patterns
- Don't assume standard ORM approaches work here

## Code Examples

### ✅ **Correct Database Usage**
```python
class ModuleService:
    def __init__(self, app_context):
        self.app_context = app_context
        
    async def initialize(self):
        # Get database service
        self.db_service = self.app_context.get_service("core.database.service")
        
        # Get session factory
        self.session_factory = self.db_service.get_database_session("module_name")
    
    async def some_database_operation(self):
        async with self.session_factory() as session:
            # Database operations using session
            # Don't import models here
            pass
```

### ❌ **Incorrect Database Usage**
```python
# This will cause table metadata conflicts
class ModuleService:
    async def some_database_operation(self):
        from .db_models import Document  # WRONG - causes conflicts
        
        # Custom database operations
        session.add(Document(...))  # WRONG - bypasses framework
```

## Key Takeaways

1. **This framework has a unique database architecture** - don't assume standard patterns
2. **Always read the documentation first** - framework-specific patterns are documented
3. **Use centralized database services** - don't create module-specific database components
4. **Framework handles database creation** - don't interfere with the process
5. **Model imports cause conflicts** - use framework's database utilities instead

## Impact on Development

This discovery changed our entire approach:
- **Before**: Assumed standard SQLAlchemy patterns
- **After**: Follow framework's centralized database architecture
- **Result**: Stable, working database operations

## Conclusion

This framework's database architecture is **intentionally different** from standard approaches. It provides:
- **Centralized management**: All database operations through core.database
- **Automatic discovery**: Framework finds and creates databases
- **Multi-database support**: Each module can have its own database
- **Conflict prevention**: Framework prevents table metadata conflicts
- **Infrastructure isolation**: Clear separation between infrastructure and module interfaces
- **Single contact surface**: Consistent import patterns across all modules

### **Critical Architectural Principles**
1. **Infrastructure isolation** - modules never touch infrastructure directly
2. **Lazy loading** - defer infrastructure calls until actually needed
3. **Consistent patterns** - all modules follow the same import conventions
4. **Semantic clarity** - file names reflect actual purpose and usage boundaries

**Always consult the framework documentation before implementing database operations.**
# Current Database Implementation Pattern

## Overview

This documents the **actual working database pattern** used in the modular framework, based on the successful implementation in `modules/standard/semantic_core`. This is the proven approach that resolves all database conflicts and provides stable operations.

## Working Database Architecture

### 1. **Database Model Definition** (`db_models.py`)

```python
# Database configuration for file-based discovery
DATABASE_NAME = "module_name"  # Required constant for framework discovery

from sqlalchemy import Column, String, Text, DateTime, Boolean, Integer, ForeignKey
from modules.core.database.db_models import get_database_base, SQLiteJSON
from sqlalchemy.sql import func

# Get database base for this module - creates module_name.db
ModuleBase = get_database_base(DATABASE_NAME)

class MyTable(ModuleBase):
    """Table description."""
    __tablename__ = "my_table"
    __table_args__ = {'extend_existing': True}  # Prevents metadata conflicts
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    # Additional columns...
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
```

### 2. **Service Integration Pattern** (`services.py`)

```python
class ModuleService:
    def __init__(self, app_context):
        self.app_context = app_context
        self.database_service = None
        self.initialized = False
        
    async def initialize(self) -> bool:
        """Initialize service with database access."""
        # Get database service
        self.database_service = self.app_context.get_service("core.database.service")
        if not self.database_service:
            return False
        
        self.initialized = True
        return True
    
    def _get_models(self):
        """Get database models for this module.
        
        IMPORTANT: Import models in method to avoid initialization conflicts.
        """
        from .db_models import MyTable, AnotherTable
        return {
            'MyTable': MyTable,
            'AnotherTable': AnotherTable
        }
    
    async def database_operation(self) -> Result:
        """Example database operation using the working pattern."""
        # Check service initialization
        if not self.initialized and not await self.initialize():
            return Result.error(
                code="SERVICE_NOT_INITIALIZED", 
                message="Service not initialized"
            )
        
        try:
            # Get session factory from database service
            session_factory = self.database_service.get_database_session("module_name")
            if not session_factory:
                return Result.error(
                    code="DATABASE_SESSION_ERROR",
                    message="Could not get database session"
                )
            
            async with session_factory() as session:
                from sqlalchemy import select
                
                # Get models - import in method to avoid conflicts
                models = self._get_models()
                MyTable = models['MyTable']
                
                # Perform database operations
                result = await session.execute(select(MyTable))
                items = result.scalars().all()
                
                return Result.success(data=items)
                
        except Exception as e:
            logger.error(f"Database operation failed: {str(e)}")
            return Result.error(
                code="DATABASE_OPERATION_FAILED",
                message="Database operation failed"
            )
```

### 3. **Bulk Operations Pattern** (For Complex Operations)

```python
async def bulk_create_items(self, items_data: list) -> Result:
    """Bulk create items using CRUD service."""
    try:
        session_factory = self.database_service.get_database_session("module_name")
        async with session_factory() as session:
            # Get models
            models = self._get_models()
            MyTable = models['MyTable']
            
            # Get CRUD service for bulk operations
            crud_service = self.app_context.get_service("core.database.crud_service")
            if not crud_service:
                return Result.error(
                    code="CRUD_SERVICE_UNAVAILABLE",
                    message="CRUD service not available"
                )
            
            # Use CRUD service for bulk creation
            bulk_result = await crud_service.bulk_create(session, MyTable, items_data)
            if not bulk_result.success:
                return Result.error(
                    code="BULK_CREATE_FAILED",
                    message="Failed to bulk create items"
                )
            
            return Result.success(data=bulk_result.data)
            
    except Exception as e:
        return Result.error(
            code="BULK_OPERATION_ERROR",
            message=f"Bulk operation failed: {str(e)}"
        )
```

### 4. **Raw SQL Operations Pattern** (For Complex Queries)

```python
async def raw_sql_operation(self) -> Result:
    """Execute raw SQL when needed for complex operations."""
    try:
        # Get database service
        db_service = self.app_context.get_service("core.database.service")
        if not db_service:
            return Result.error(
                code="DATABASE_SERVICE_UNAVAILABLE",
                message="Database service not available"
            )
        
        # Execute raw SQL with named parameters
        result = await db_service.execute_raw_query(
            """SELECT COUNT(*) as count FROM my_table 
               WHERE created_at >= :start_date""",
            database="module_name",  # Database name
            params={
                "start_date": start_date.isoformat()
            }
        )
        
        return Result.success(data=result)
        
    except Exception as e:
        return Result.error(
            code="RAW_SQL_ERROR",
            message=f"Raw SQL operation failed: {str(e)}"
        )
```

## Key Patterns That Work

### ✅ **DO - Working Patterns:**

1. **Import models in `_get_models()` method** - avoids initialization conflicts
2. **Use session factory pattern** - `get_database_session("database_name")`
3. **Check service initialization** before database operations
4. **Use `__table_args__ = {'extend_existing': True}`** in model definitions
5. **Use named parameters (`:param`)** for raw SQL queries
6. **Get database service through app_context** - centralized approach
7. **Use CRUD service for bulk operations** when needed

### ❌ **DON'T - Causes Problems:**

1. **Import models at module level** - causes "Table already defined" errors
2. **Use `?` placeholders with dictionary params** - causes binding errors
3. **Create custom database components** - use centralized services
4. **Skip initialization checks** - causes runtime errors
5. **Mix database operation patterns** - stick to one approach per method

## Database Architecture

```
Framework Database Structure:
├── data/database/framework.db          # Core framework data
├── data/database/semantic_core.db      # semantic_core module data
├── data/database/vector_operations.db  # vector_operations module data
└── data/database/module_name.db        # Your module data
```

### Database Access Layers

```python
# Layer 1: Framework Database Service (core.database.service)
database_service = app_context.get_service("core.database.service")

# Layer 2: Session Factory (per database)
session_factory = database_service.get_database_session("database_name")

# Layer 3: SQLAlchemy Session (per operation)
async with session_factory() as session:
    # Database operations

# Layer 4: CRUD Service (for complex operations)
crud_service = app_context.get_service("core.database.crud_service")

# Layer 5: Raw SQL (for specialized queries)
result = await database_service.execute_raw_query(sql, database="name", params={})
```

## Proven Working Examples

**From semantic_core module** (566 documents, multiple tables, complex operations):
- ✅ Document registry with content_hash primary keys
- ✅ Similarity analysis with 36K+ results storage
- ✅ Bulk document registration operations
- ✅ Complex foreign key relationships
- ✅ Raw SQL for specialized queries

**From vector_operations module** (ChromaDB + database integration):
- ✅ Raw SQL parameter binding with named placeholders
- ✅ Progress tracking across long operations
- ✅ Error handling and status updates

## Common Error Resolutions

### "Table already defined" Error
```python
# ❌ WRONG: Import at module level
from .db_models import Document

# ✅ CORRECT: Import in method
def _get_models(self):
    from .db_models import Document
    return {'Document': Document}
```

### "Incorrect number of bindings" Error
```python
# ❌ WRONG: ? with dictionary
await db_service.execute_raw_query(
    "INSERT INTO table (col1, col2) VALUES (?, ?)",
    params={"col1": "value1", "col2": "value2"}  # Wrong!
)

# ✅ CORRECT: Named parameters
await db_service.execute_raw_query(
    "INSERT INTO table (col1, col2) VALUES (:col1, :col2)",
    params={"col1": "value1", "col2": "value2"}  # Correct!
)
```

## Summary

This pattern has been **battle-tested** with:
- 566 documents processed
- 159K+ pairwise comparisons
- 36K+ similarity results stored
- Multiple complex database tables
- Bulk operations and raw SQL
- No metadata conflicts or binding errors

**Use this semantic_core implementation as the reference for all new modules.**
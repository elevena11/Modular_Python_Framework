# Database Module

The Database Module (`modules/core/database/`) provides comprehensive database management capabilities for the framework. It implements a multi-database architecture with SQLite support, automatic table creation, migration management, and standardized CRUD operations.

## Overview

The Database Module is a core framework component that handles all database operations. It provides:

- **Multi-Database Support**: Multiple SQLite databases for different modules
- **Automatic Discovery**: File-based database discovery and creation
- **Table-Driven Architecture**: Automatic table creation from model definitions
- **Migration Management**: Alembic-based database migrations
- **CRUD Operations**: Standardized create, read, update, delete operations
- **Connection Management**: Async connection pooling and retry logic
- **API Endpoints**: REST API for database management

## Key Features

### 1. Multi-Database Architecture
- **Framework Database**: Core framework data (modules, settings, logs)
- **Module Databases**: Each module can have its own database
- **Automatic Discovery**: Databases discovered from model files
- **Table-Driven Creation**: No manual database setup required

### 2. SQLite Optimization
- **WAL Mode**: Write-Ahead Logging for better concurrency
- **Connection Pooling**: Efficient connection management
- **Pragma Optimization**: Optimized SQLite settings
- **Retry Logic**: Automatic retry for locked databases

### 3. Migration Support
- **Alembic Integration**: Database schema migrations
- **Version Control**: Track database schema changes
- **Automatic Generation**: Generate migrations from model changes
- **Rollback Support**: Downgrade database versions

### 4. CRUD Operations
- **Standardized Interface**: Consistent CRUD operations
- **Pagination Support**: Efficient data retrieval
- **Filtering**: Column-based filtering
- **Sorting**: Multi-column sorting support

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Database Module                          │
├─────────────────────────────────────────────────────────────┤
│ Core Components                                             │
│ ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐ │
│ │ Database        │ │ Database        │ │ CRUD            │ │
│ │ Service         │ │ Operations      │ │ Service         │ │
│ └─────────────────┘ └─────────────────┘ └─────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│ Multi-Database Support                                      │
│ ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐ │
│ │ Framework DB    │ │ Module DB 1     │ │ Module DB N     │ │
│ │ (framework.db)  │ │ (module1.db)    │ │ (moduleN.db)    │ │
│ └─────────────────┘ └─────────────────┘ └─────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│ Database Operations                                         │
│ ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐ │
│ │ Table Creation  │ │ Migration       │ │ Connection      │ │
│ │ & Discovery     │ │ Management      │ │ Pooling         │ │
│ └─────────────────┘ └─────────────────┘ └─────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## Database Discovery System

### 1. File-Based Discovery
The system automatically discovers databases by scanning for `db_models.py` files:

```python
# In any module's db_models.py
DATABASE_NAME = "my_custom_db"

# Get database-specific base
MyBase = get_database_base("my_custom_db")

class MyTable(MyBase):
    __tablename__ = "my_table"
    id = Column(Integer, primary_key=True)
    name = Column(String(100))
```

### 2. Table-Driven Creation
```python
# Framework automatically:
# 1. Discovers DATABASE_NAME declarations
# 2. Creates database files (my_custom_db.db)
# 3. Creates all tables for that database
# 4. Registers database utilities
```

### 3. Multi-Database Pattern
```python
# AI PATTERN: Table-driven multi-database creation
# 1. Tables declare their database: MyBase = get_database_base("db_name")
# 2. Framework automatically discovers all databases
# 3. Database creation is fully automatic
```

## Database Operations

### 1. Database Creation
```python
class DatabaseOperations:
    def create_all_databases_now(self, discovered_databases):
        """Create all discovered databases immediately."""
        for db_name, tables in discovered_databases.items():
            # Create database file
            db_path = self.get_database_path(db_name)
            
            # Create engine and tables
            engine = self.create_database_engine(db_name)
            self.create_tables_for_database(engine, tables)
```

### 2. Connection Management
```python
# Async connection pooling
engine = create_async_engine(
    db_url,
    pool_size=20,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=3600,
    pool_pre_ping=True
)

# Session factory
session_factory = async_sessionmaker(bind=engine)
```

### 3. SQLite Optimization
```python
# Standard SQLite pragmas
SQLITE_PRAGMAS = [
    "PRAGMA journal_mode=WAL",      # Write-Ahead Logging
    "PRAGMA synchronous=NORMAL",    # Balance safety/speed
    "PRAGMA cache_size=10000",      # 10MB cache
    "PRAGMA foreign_keys=ON",       # Enforce constraints
    "PRAGMA busy_timeout=10000"     # 10s lock timeout
]
```

## Module Integration

### 1. Database Utilities
The framework provides utilities for modules to create and manage databases:

```python
# Get database utilities from service
db_utils = self.database_service.get_database_utilities()

# Create database
db_url = db_utils["get_database_url"]("my_module")
db_info = db_utils["create_database_engine"]("my_module", db_url)

# Register database
db_utils["register_database"]("my_module", db_info, "my_module.id")
```

### 2. Model Definition Pattern
```python
# In module's db_models.py
DATABASE_NAME = "my_module"

from modules.core.database.db_models import get_database_base

# Get module-specific base
MyModuleBase = get_database_base("my_module")

class MyTable(MyModuleBase):
    __tablename__ = "my_table"
    id = Column(Integer, primary_key=True)
    name = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)
```

### 3. Service Integration
```python
# In module's services.py
class MyModuleService:
    def __init__(self, app_context):
        self.app_context = app_context
        
    async def initialize(self):
        # Get database service
        self.db_service = self.app_context.get_service("core.database.service")
        
        # Database is already created by framework
        # Get session factory for database operations
        self.session_factory = self.db_service.get_database_session("my_module")
    
    async def some_database_operation(self):
        # Use async context manager for database operations
        async with self.session_factory() as session:
            from .db_models import MyTable
            from sqlalchemy import select
            
            # Query data
            result = await session.execute(select(MyTable))
            items = result.scalars().all()
            
            # Insert data
            new_item = MyTable(name="example")
            session.add(new_item)
            await session.commit()
            
            return items
```

## Migration Management

### 1. Alembic Integration
```python
# Generate migration
result = await service.generate_migration("Add new column to users")

# Run migrations
result = await service.run_migrations("head")

# Downgrade database
result = await service.downgrade_database("previous_revision")
```

### 2. Migration API Endpoints
```python
# Check migration status
GET /api/v1/db/migrations/status

# Generate new migration
POST /api/v1/db/migrations/generate
{
    "message": "Add user preferences table"
}

# Run migrations
POST /api/v1/db/migrations/run
{
    "target": "head"
}
```

## CRUD Operations

### 1. CRUD Service
```python
class CRUDService:
    async def create_record(self, table_name, data):
        """Create a new record in the specified table."""
        
    async def read_records(self, table_name, filters=None):
        """Read records with optional filtering."""
        
    async def update_record(self, table_name, record_id, data):
        """Update an existing record."""
        
    async def delete_record(self, table_name, record_id):
        """Delete a record."""
```

### 2. Pagination Support
```python
# Get paginated data
result = await service.get_table_data(
    table_name="users",
    page=1,
    page_size=50,
    sort_by="created_at",
    sort_desc=True,
    filter_column="status",
    filter_value="active"
)
```

### 3. Table Operations
```python
# List all tables
tables = await service.get_all_tables()

# Get table schema
schema = await service.get_table_schema("users")

# Get table data with pagination
data = await service.get_table_data("users", page=1, page_size=20)
```

## API Endpoints

### 1. Database Status
```python
# Check database status
GET /api/v1/db/status
Response: {
    "status": "connected",
    "engine": "sqlite:///data/database/",
    "initialization": {...},
    "tables": [...],
    "table_count": 10
}

# Check if database is ready
GET /api/v1/db/is-ready
Response: {
    "ready": true,
    "status": "ready"
}
```

### 2. Table Management
```python
# List all tables
GET /api/v1/db/tables
Response: {
    "success": true,
    "tables": ["users", "modules", "settings"]
}

# Get table data
GET /api/v1/db/tables/users?page=1&page_size=20
Response: {
    "success": true,
    "table": "users",
    "page": 1,
    "total_records": 100,
    "records": [...]
}

# Get table schema
GET /api/v1/db/tables/users/schema
Response: {
    "success": true,
    "table": "users",
    "schema_definition": {...}
}
```

## Configuration

### 1. Database Settings
```python
# module_settings.py
DATABASE_MODULE_SETTINGS = {
    "database_url": {
        "type": "str",
        "default": "",
        "description": "Database URL (auto-configured if empty)"
    },
    "max_retries": {
        "type": "int",
        "default": 5,
        "description": "Maximum retry attempts for database operations"
    },
    "connection_timeout": {
        "type": "int",
        "default": 30,
        "description": "Database connection timeout in seconds"
    }
}
```

### 2. Environment Variables
```bash
# Database configuration
DATABASE_URL="sqlite:///custom/path/database/"
DATABASE_MAX_RETRIES=10
DATABASE_CONNECTION_TIMEOUT=60

# SQLite-specific settings
SQLITE_JOURNAL_MODE="WAL"
SQLITE_SYNCHRONOUS="NORMAL"
SQLITE_CACHE_SIZE=10000
```

## Error Handling

### 1. Result Pattern
```python
# All database operations return Result objects
async def create_record(self, table_name, data):
    try:
        # Database operation
        result = await self.perform_operation()
        return Result.success(data=result)
    except Exception as e:
        return Result.error(
            code="CREATE_FAILED",
            message="Failed to create record",
            details={"error": str(e)}
        )
```

### 2. Retry Logic
```python
async def execute_with_retry(self, operation, max_retries=5):
    """Execute database operation with retry logic."""
    for attempt in range(max_retries):
        try:
            return await operation()
        except OperationalError as e:
            if "database is locked" in str(e).lower():
                if attempt < max_retries - 1:
                    await asyncio.sleep(0.1 * (2 ** attempt))
                    continue
            raise
```

### 3. Standardized Error Responses
```python
# API error responses
{
    "error": {
        "code": "TABLE_NOT_FOUND",
        "message": "Table 'users' not found in database",
        "module": "core.database",
        "details": {
            "table_name": "users",
            "available_tables": ["modules", "settings"]
        }
    }
}
```

## Best Practices

### 1. Database Design
- **Use get_database_base()** for module-specific databases
- **Declare DATABASE_NAME** in db_models.py
- **Keep related tables** in the same database
- **Use framework utilities** for database operations

### 2. Model Definition
```python
# ✅ CORRECT: Module-specific database
DATABASE_NAME = "my_module"
MyBase = get_database_base("my_module")

class MyTable(MyBase):
    __tablename__ = "my_table"
    id = Column(Integer, primary_key=True)

# ❌ WRONG: Using framework database
class MyTable(Base):  # Clutters framework database
    __tablename__ = "my_table"
```

### 3. Service Integration
```python
# ✅ CORRECT: Get database service
self.db_service = self.app_context.get_service("core.database.service")
utilities = self.db_service.get_database_utilities()

# ❌ WRONG: Direct database access
import sqlite3
conn = sqlite3.connect("database.db")  # Bypasses framework
```

### 4. Error Handling
```python
# ✅ CORRECT: Use Result pattern
result = await service.create_record(table, data)
if result.success:
    return result.data
else:
    logger.error(f"Failed: {result.error}")

# ❌ WRONG: Direct exception handling
try:
    record = await service.create_record(table, data)
    return record
except Exception as e:
    print(f"Error: {e}")  # Inconsistent error handling
```

## Common Patterns

### 1. Module Database Pattern
```python
# In db_models.py
DATABASE_NAME = "my_module"
MyBase = get_database_base("my_module")

class ModuleData(MyBase):
    __tablename__ = "module_data"
    id = Column(Integer, primary_key=True)
    name = Column(String(100))
    value = Column(SQLiteJSON)
    created_at = Column(DateTime, default=datetime.utcnow)
```

### 2. Service Database Access Pattern
```python
class ModuleService:
    def __init__(self, app_context):
        self.app_context = app_context
        
    async def initialize(self):
        # Get database utilities
        db_service = self.app_context.get_service("core.database.service")
        self.db_utils = db_service.get_database_utilities()
        
        # Database is already created by framework
        self.db_ready = True
```

### 3. CRUD Operations Pattern
```python
class ModuleService:
    async def save_data(self, name, value):
        """Save module data to database."""
        crud_service = self.app_context.get_service("core.database.crud_service")
        
        result = await crud_service.create_record("module_data", {
            "name": name,
            "value": value
        })
        
        return result.success
```

## Performance Considerations

### 1. Connection Pooling
```python
# Async engine with connection pooling
engine = create_async_engine(
    db_url,
    pool_size=20,          # Base pool size
    max_overflow=10,       # Additional connections
    pool_timeout=30,       # Connection timeout
    pool_recycle=3600,     # Connection lifetime
    pool_pre_ping=True     # Health checks
)
```

### 2. Query Optimization
```python
# Use pagination for large datasets
result = await service.get_table_data(
    table_name="large_table",
    page=1,
    page_size=100,  # Reasonable page size
    sort_by="id"
)

# Use filtering to reduce data
result = await service.get_table_data(
    table_name="events",
    filter_column="date",
    filter_value="2025-01-01"
)
```

### 3. Index Usage
```python
# Define indexes in models
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(String(255), index=True)  # Indexed for fast lookups
    created_at = Column(DateTime, index=True)  # Indexed for time-based queries
```

## Related Documentation

- [Application Context](../core/app-context.md) - Service container integration
- [Module Creation Guide](../module-creation-guide-v2.md) - Creating modules with databases
- [Two-Phase Initialization](../patterns/two-phase-initialization.md) - Database initialization patterns
- [Result Pattern](../patterns/result-pattern.md) - Error handling patterns
- [CRUD Operations](../patterns/crud-patterns.md) - Database operation patterns

---

The Database Module provides a comprehensive foundation for data persistence in the framework, with automatic database discovery, multi-database support, and standardized operations that make it easy for modules to work with data while maintaining clean separation and consistency.
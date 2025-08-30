# Bootstrap Database Dependencies Trace

## Purpose
Document and eliminate ALL connections between bootstrap.py and the database module to ensure complete independence.

## Current Bootstrap Flow Analysis

### 1. Bootstrap Entry Point
**File**: `core/bootstrap.py`
**Function**: `run_bootstrap_phase()`

```python
async def run_bootstrap_phase(app_context) -> bool:
    logger.info("Bootstrap: Compiling database schema...")
    
    # Create essential directories
    directories = [
        get_data_path("logs"),
        get_data_path("database"),  # Creates database directory
    ]
    
    # CRITICAL CONNECTION: Calls database compilation
    await _compile_and_create_databases()
```

### 2. Database Compilation Process
**Function**: `_compile_and_create_databases()`

**Line-by-line trace:**

```python
async def _compile_and_create_databases():
    logger.info("Bootstrap: Scanning modules for database schemas...")
    
    # Collect all database schemas by database name
    database_schemas = defaultdict(list)
    
    # PROBLEM: Scans for db_models.py files
    for module_type in ["core", "standard", "extensions"]:
        modules_dir = Path("modules") / module_type
        if not modules_dir.exists():
            continue
            
        for module_path in modules_dir.iterdir():
            if not module_path.is_dir():
                continue
                
            # Skip disabled modules
            if (module_path / ".disabled").exists():
                continue
            
            # CRITICAL CONNECTION: Looks for db_models.py
            db_models_file = module_path / "db_models.py"
            if db_models_file.exists():
                # PROBLEM: Calls schema collection for each db_models.py
                schema_info = await _collect_module_schema(module_type, module_path.name)
                if schema_info:
                    database_name, base_class = schema_info
                    database_schemas[database_name].append({
                        'module': f"{module_type}.{module_path.name}",
                        'base_class': base_class
                    })
```

### 3. Module Schema Collection
**Function**: `_collect_module_schema()`

```python
async def _collect_module_schema(module_type: str, module_name: str):
    try:
        # CRITICAL CONNECTION: Imports db_models.py files
        import_path = f"modules.{module_type}.{module_name}.db_models"
        logger.debug(f"Importing {import_path} for schema compilation")
        
        # PROBLEM: This triggers imports from database module
        db_models_module = importlib.import_module(import_path)
        
        # Check if module defines DATABASE_NAME
        if not hasattr(db_models_module, 'DATABASE_NAME'):
            logger.debug(f"{module_name}: No DATABASE_NAME defined")
            return None
            
        database_name = db_models_module.DATABASE_NAME
        
        # CRITICAL CONNECTION: Searches for base classes
        base_class = _find_database_base(db_models_module, database_name, module_name)
        if not base_class:
            logger.warning(f"{module_name}: No base class found for {database_name}")
            return None
            
        logger.debug(f"{module_name}: Collected schema for {database_name}")
        return database_name, base_class
```

### 4. Database Creation
**Function**: `_create_complete_database()`

```python
def _create_complete_database(database_name: str, schemas: list) -> bool:
    try:
        database_path = get_data_path("database", f"{database_name}.db")
        
        # Skip if database already exists
        if os.path.exists(database_path):
            logger.debug(f"{database_name}: Database already exists, skipping")
            return False
        
        # CRITICAL CONNECTION: Uses SQLAlchemy from imported schemas
        engine = create_engine(f"sqlite:///{database_path}")
        
        # Collect all table definitions for this database
        all_tables = {}
        modules_contributing = []
        
        for schema in schemas:
            base_class = schema['base_class']  # From imported db_models.py
            module_name = schema['module']
            modules_contributing.append(module_name)
            
            # PROBLEM: Uses base_class.metadata from database module imports
            if hasattr(base_class, 'metadata'):
                for table_name, table_obj in base_class.metadata.tables.items():
                    all_tables[table_name] = table_obj
        
        # Create all tables in one operation
        if all_tables:
            # CRITICAL CONNECTION: Uses imported base class metadata
            base_metadata = schemas[0]['base_class'].metadata
            base_metadata.create_all(engine)
```

## Database Module Dependencies Found

### CRITICAL DISCOVERY: ALL db_models.py Files Import from Database Module

**EVERY SINGLE db_models.py file imports from `core.database`:**

1. **core/database/db_models.py**:
   ```python
   from core.database import DatabaseBase, SQLiteJSON
   ```

2. **core/error_handler/db_models.py**:
   ```python
   from core.database import DatabaseBase, SQLiteJSON
   ```

3. **core/scheduler/db_models.py**:
   ```python
   from core.database import DatabaseBase, SQLiteJSON
   ```

4. **core/settings/db_models.py**:
   ```python
   from core.database import DatabaseBase, SQLiteJSON
   ```

5. **core/framework/db_models.py**:
   ```python
   from core.database import DatabaseBase
   ```

6. **core/settings_v2/db_models.py**:
   ```python
   from core.database import DatabaseBase, SQLiteJSON
   ```

7. **standard/semantic_core/db_models.py**:
   ```python
   from core.database import DatabaseBase, SQLiteJSON
   ```

8. **standard/vector_operations/db_models.py**:
   ```python
   from core.database import DatabaseBase, SQLiteJSON
   ```

9. **standard/table_validation/db_models.py**:
   ```python
   from core.database import DatabaseBase
   ```

10. **standard/decorator_validation/db_models.py**:
    ```python
    from core.database import DatabaseBase, SQLiteJSON
    ```

### The Bootstrap -> Database Module Chain

**COMPLETE DEPENDENCY CHAIN:**

1. **bootstrap.py** scans for `db_models.py` files
2. **bootstrap.py** imports each `db_models.py` file via `importlib.import_module()`
3. **Each db_models.py** imports from `core.database` (which is the database module facade)
4. **core.database** imports from `modules.core.database.database_infrastructure`
5. **Bootstrap uses the imported base classes** to create databases

**RESULT**: Bootstrap is completely dependent on the database module!

## SOLUTION: Complete Independence

### Requirements
1. **Bootstrap must NOT import any db_models.py files**
2. **Bootstrap must NOT depend on database module in any way**
3. **db_models.py files can still use database utilities for modules**
4. **Database creation must be handled by the database module itself**

### New Architecture

**BEFORE (Current - BROKEN)**:
```
bootstrap.py 
├── scans for db_models.py files
├── imports each db_models.py
│   └── each imports core.database
│       └── imports modules.core.database.*
├── collects base classes from imports
└── creates databases using base classes
```

**AFTER (Target - INDEPENDENT)**:
```
bootstrap.py 
├── creates essential directories only
└── DOES NOT scan or import any module files

database module (via decorator system)
├── discovers its own databases internally
├── creates databases during its own initialization
└── operates completely independently
```

### Implementation Plan

1. **Remove bootstrap database scanning entirely**
2. **Move database creation to database module Phase 1 initialization**
3. **Let each module handle its own database creation internally**
4. **Bootstrap only creates directory structure**

### Files to Modify

1. **core/bootstrap.py**: Remove all database scanning and creation
2. **modules/core/database/**: Add internal database discovery and creation
3. **Verify all db_models.py**: Can continue using core.database imports

### Verification Steps

1. ✅ **Trace all connections** (DONE)
2. ⏳ **Remove bootstrap database code**
3. ⏳ **Move database creation to database module**
4. ⏳ **Test complete independence**
5. ⏳ **Document final architecture**

## Current Status: DEPENDENCIES IDENTIFIED - READY FOR DISCONNECTION

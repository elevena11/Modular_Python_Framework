# Exact Startup Sequence - RAH Framework

## Overview

This document details the **exact startup sequence** of the RAH framework, including special bootstrap cases, load order dependencies, and critical timing requirements. This is essential for understanding how to improve the database interface without breaking initialization.

## Startup Phase Breakdown

### **Phase 0: Pre-Bootstrap (app.py)**
```
Time: T+0ms
Location: app.py lines 1-33
```

1. **Import Critical Components**
   ```python
   from core.app_context import AppContext
   from core.module_loader import ModuleLoader  
   from core.config import settings
   ```

2. **Logging Setup**
   ```python
   # Creates data/logs/ directory
   # Initializes file + console logging
   logger = logging.getLogger(settings.APP_NAME)
   ```

3. **FastAPI Application Creation**
   ```python
   # AsyncContextManager for startup/shutdown
   ```

---

### **Phase 1: Bootstrap Initialization**
```
Time: T+10ms
Location: app.py startup() function
```

1. **AppContext Creation**
   ```python
   app_context = AppContext(settings)
   app_context.initialize()  # Creates service registry, session management
   ```

2. **ModuleLoader Creation** 
   ```python
   module_loader = ModuleLoader(app_context)
   ```

3. **Session Initialization**
   ```python
   # Generates session_id: YYYYMMDD_HHMMSS_<8-char-hex>
   # Available via app_context.get_session_info()
   ```

---

### **Phase 2: Module Discovery**
```
Time: T+50ms
Location: module_loader.discover_modules()
```

1. **Directory Scanning**
   ```
   modules/core/     -> core modules (database, settings, error_handler, etc.)
   modules/standard/ -> application modules (semantic_core, vector_operations, etc.) 
   modules/extensions/ -> optional extensions
   ```

2. **Manifest Validation**
   ```python
   # For each directory with manifest.json:
   # - Check for .disabled file (skip if exists)
   # - Parse JSON manifest
   # - Validate required fields (id, name, version, dependencies)
   ```

3. **Dependency Resolution**
   ```python
   # Build dependency graph
   # Perform topological sort 
   # Determine load order respecting dependencies
   ```

4. **Special Cases Identified:**
   - **core.database**: Must load FIRST (no dependencies)
   - **core.settings**: Must load AFTER database (depends on database for storage)
   - **core.error_handler**: Can load after database (depends on database for error logging)
   - **All other modules**: Load after core modules

---

### **Phase 3: Module Loading - Phase 1 (Service Registration)**
```
Time: T+100ms
Location: module_loader.load_modules()
```

**CRITICAL: This phase runs in strict dependency order**

#### **3.1: core.database Phase 1 (T+100ms)**
```python
# modules/core/database/api.py initialize()
```

**Special Bootstrap Sequence for Database:**
1. **Create DatabaseService instance**
   ```python
   service_instance = DatabaseService(app_context)
   ```

2. **IMMEDIATE Database Discovery** 
   ```python
   # ⚠️ CRITICAL: This happens in Phase 1, not Phase 2!
   discovered_databases = service_instance.db_operations.discover_databases_from_models()
   # Scans ALL db_models.py files for DATABASE_NAME constants
   # Example output: {"framework": ["modules.core.database", "modules.core.settings", ...]}
   ```

3. **IMMEDIATE Database Creation**
   ```python
   # ⚠️ CRITICAL: Databases created immediately in Phase 1
   success = service_instance.db_operations.create_all_databases_now(discovered_databases)
   # Creates: framework.db, semantic_core.db, vector_operations.db, etc.
   ```

4. **Service Registration**
   ```python
   app_context.register_service("core.database.service", service_instance)
   app_context.register_service("core.database.crud_service", crud_service)
   ```

5. **Make Base Available**
   ```python
   # ⚠️ CRITICAL: Other modules need this during their Phase 1
   Base = get_database_base("framework")
   app_context.db_base = Base
   ```

**Why Database Phase 1 is Special:**
- Creates all databases immediately (not in Phase 2)
- Makes database bases available to other modules during Phase 1
- Other modules can safely import database utilities

#### **3.2: core.settings Phase 1 (T+150ms)**
```python
# Dependencies: ["core.database"] - settings needs database for storage
```

1. **Create SettingsService**
2. **Register service with app_context**
3. **Register database models with framework database**
4. **Register post-init hook for Phase 2**

#### **3.3: Other Core Modules Phase 1 (T+200ms)**
```python
# core.error_handler, core.global, core.model_manager
```

Standard Phase 1 pattern:
- Create service instance
- Register with app_context
- Register database models (if any)
- Register post-init hooks for Phase 2

#### **3.4: Standard Modules Phase 1 (T+300ms)**
```python  
# semantic_core, vector_operations, document_processing, etc.
```

Standard Phase 1 pattern:
- Import models from their db_models.py (databases already created)
- Create service instances
- Register services
- Register post-init hooks

---

### **Phase 4: Module Loading - Phase 2 (Complex Initialization)**
```
Time: T+500ms
Location: run_delayed_hooks() in app.py
```

**Post-initialization hooks run in priority + dependency order:**

#### **Hook Execution Order:**
1. **core.database.setup** (Priority: 10)
   - Minimal Phase 2 setup (databases already created)

2. **database_register_settings** (Priority: 20, Deps: ["core.settings.setup"])
   - Register database settings for UI

3. **core.settings.setup** (Priority: 50)
   - Load and validate all module settings
   - Create settings UI components

4. **core.error_handler.setup** (Priority: 100)
   - Initialize error code registry
   - Load error log files

5. **core.global.setup** (Priority: 100)
   - Initialize global utilities

6. **core.model_manager.setup** (Priority: 150)
   - **⚠️ RESOURCE INTENSIVE**: Load GPU models
   - Create worker pool with 2 GPU workers
   - Load Mixedbread embedding models (1024-dim)

7. **Standard module hooks** (Priority: 200+)
   - semantic_core, vector_operations, etc.
   - Complex business logic initialization

---

### **Phase 5: Application Ready**
```
Time: T+10000ms (model loading is slow)
Location: app.py main()
```

1. **API Server Start**
   ```python
   uvicorn.run("app:app", host=settings.HOST, port=settings.PORT)
   ```

2. **Health Check Endpoints Active**
3. **All Services Available**

---

## Critical Bootstrap Dependencies

### **Database Module Special Cases:**

1. **File-Based Discovery in Phase 1**
   ```python
   # ⚠️ This scanning happens BEFORE other modules load:
   # - Scans modules/*/db_models.py files  
   # - Finds DATABASE_NAME constants
   # - Groups tables by database name
   # - Creates all database files immediately
   ```

2. **Import Safety Pattern**
   ```python
   # ⚠️ Why _get_models() pattern exists:
   def _get_models(self):
       # Import models in method to avoid initialization conflicts
       from .db_models import MyTable
       return {'MyTable': MyTable}
   ```
   
   **Problem it solves:**
   - If models imported at module level during Phase 1
   - Other modules' models not yet discovered by database
   - Creates "chicken and egg" circular dependency

3. **Database Session Pattern**
   ```python
   # Current verbose but necessary pattern:
   session_factory = self.database_service.get_database_session("module_name")
   async with session_factory() as session:
       # operations
   ```
   
   **Why it's verbose:**
   - Database discovery happens per-database
   - Session factories must be retrieved dynamically
   - No direct session access due to multi-database architecture

### **Load Order Requirements:**

1. **MUST be first:** `core.database`
   - Creates all databases
   - Makes utilities available to other modules

2. **MUST be after database:** `core.settings`
   - Needs database for settings storage
   - Other modules need settings service

3. **Can be parallel after settings:** All other core modules
   - `core.error_handler`, `core.global`, `core.model_manager`

4. **Standard modules load last:**
   - All core infrastructure must be ready
   - Can reference any core services safely

### **Timing Constraints:**

- **Database discovery**: Must happen in Phase 1 (not Phase 2)
- **Model loading**: Happens in Phase 2 (takes ~10 seconds)
- **Settings loading**: Must happen after database, before other modules need settings
- **Session generation**: Happens once at startup, persists throughout application lifecycle

---

## Interface Improvement Implications

Based on this startup analysis, any database interface improvements must respect:

1. **Database discovery timing** (Phase 1, before other modules load)
2. **Multi-database architecture** (can't simplify to single session)  
3. **Model import timing** (must be lazy-loaded in methods)
4. **Service registration order** (database service must be available immediately)

The current "verbose" patterns exist for good architectural reasons related to this complex bootstrap sequence.

---

## Recommendations for Interface Improvements

1. **Keep discovery in Phase 1** - don't change this timing
2. **Add convenience methods** - wrapper around session_factory pattern  
3. **Unify import patterns** - but maintain lazy loading
4. **Better error messages** - when bootstrap fails
5. **Document the "why"** - explain why patterns exist

The focus should be on **convenience** and **consistency**, not fundamental architectural changes to the bootstrap sequence.
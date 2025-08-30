# Database Interface Specification

## Overview

This document specifies the unified database interface for the RAH framework. The interface provides convenient access to database operations while preserving the existing multi-database architecture and bootstrap timing requirements.

---

## Design Principles

### **Preserve Bootstrap Constraints**
- Database discovery remains in Phase 1 (T+100ms)
- Multi-database architecture maintained
- Lazy model loading preserved
- Service registration order unchanged

### **Improve Developer Experience**  
- Reduce verbose session access patterns
- Provide consistent interface across modules
- Enable easy database operation testing
- Clear error messages and debugging

### **Enable LLM Automation**
- Self-describing interface with metadata
- Discoverable patterns through introspection
- Consistent naming and conventions
- Well-documented examples

---

## Interface Architecture

### **Core Components**

```
┌─────────────────────────────────────────────────────────┐
│                DatabaseInterface                        │
├─────────────────────────────────────────────────────────┤
│ Convenience Layer                                       │
│ ┌─────────────────┐ ┌─────────────────┐ ┌─────────────┐ │
│ │ Session         │ │ Model           │ │ Utility     │ │
│ │ Management      │ │ Access          │ │ Methods     │ │
│ └─────────────────┘ └─────────────────┘ └─────────────┘ │
├─────────────────────────────────────────────────────────┤
│ Existing Implementation (Preserved)                     │
│ ┌─────────────────┐ ┌─────────────────┐ ┌─────────────┐ │
│ │ DatabaseService │ │ Session         │ │ Database    │ │
│ │ (core.database) │ │ Factories       │ │ Operations  │ │
│ └─────────────────┘ └─────────────────┘ └─────────────┘ │
└─────────────────────────────────────────────────────────┘
```

---

## Interface Specification

### **1. DatabaseInterface Class**

```python
class DatabaseInterface:
    """Unified database interface providing convenient access to framework databases.
    
    This class wraps the existing DatabaseService to provide a cleaner API while
    preserving all bootstrap timing and multi-database architecture requirements.
    """
    
    def __init__(self, app_context: AppContext):
        """Initialize with app context reference."""
        self.app_context = app_context
        self._database_service = None
    
    @property 
    def database_service(self) -> DatabaseService:
        """Lazy load the database service."""
        if self._database_service is None:
            self._database_service = self.app_context.get_service("core.database.service")
            if not self._database_service:
                raise DatabaseInterfaceError("Database service not available")
        return self._database_service
    
    # Session Management
    async def session(self, database_name: str) -> AsyncSessionManager:
        """Get async session manager for database.
        
        Args:
            database_name: Name of database (e.g. "semantic_core", "framework")
            
        Returns:
            Async context manager for database session
            
        Example:
            async with db.session("semantic_core") as session:
                result = await session.execute(select(Document))
        """
        session_factory = self.database_service.get_database_session(database_name)
        if not session_factory:
            raise DatabaseNotFoundError(f"Database '{database_name}' not found")
        return AsyncSessionManager(session_factory)
    
    # Model Access
    def models(self, database_name: str) -> Dict[str, Any]:
        """Get registered models for database.
        
        Args:
            database_name: Name of database
            
        Returns:
            Dictionary mapping model names to model classes
            
        Example:
            models = db.models("semantic_core")
            Document = models["Document"]
        """
        # Access app_context model registry
        return self.app_context.get_database_models(database_name)
    
    def base(self, database_name: str) -> Any:
        """Get SQLAlchemy base for database.
        
        Args:
            database_name: Name of database
            
        Returns:
            SQLAlchemy declarative base for the database
        """
        from modules.core.database.db_models import get_database_base
        return get_database_base(database_name)
    
    # Utility Methods
    async def exists(self, database_name: str) -> bool:
        """Check if database exists and is accessible."""
        try:
            session_factory = self.database_service.get_database_session(database_name)
            return session_factory is not None
        except Exception:
            return False
    
    def list_databases(self) -> List[str]:
        """List all registered databases."""
        return list(self.database_service.get_all_databases().keys())
    
    def get_metadata(self) -> Dict[str, Any]:
        """Get interface metadata for introspection."""
        return {
            "interface_version": "1.0",
            "available_databases": self.list_databases(),
            "features": ["session_management", "model_access", "utilities"],
            "bootstrap_phase": "available_after_phase_1"
        }


class AsyncSessionManager:
    """Async context manager wrapper for database sessions."""
    
    def __init__(self, session_factory):
        self.session_factory = session_factory
        self._session = None
    
    async def __aenter__(self):
        self._session = self.session_factory()
        return await self._session.__aenter__()
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return await self._session.__aexit__(exc_type, exc_val, exc_tb)


# Exception Classes
class DatabaseInterfaceError(Exception):
    """Base exception for database interface errors."""
    pass

class DatabaseNotFoundError(DatabaseInterfaceError):
    """Raised when requested database is not found."""
    pass
```

### **2. AppContext Integration**

```python
# Add to AppContext class:
class AppContext:
    def __init__(self, config):
        # ... existing initialization
        self._database_interface = None
    
    @property
    def database(self) -> DatabaseInterface:
        """Get unified database interface."""
        if self._database_interface is None:
            self._database_interface = DatabaseInterface(self)
        return self._database_interface
    
    # Alias for convenience
    @property
    def db(self) -> DatabaseInterface:
        """Short alias for database interface."""
        return self.database
```

### **3. Import Unification & Auto-Discovery Decorators**

```python
# Create core/database.py - unified import module
"""Unified database interface for RAH framework.

This module provides a single import point for all database functionality,
simplifying imports and providing consistent access patterns.
"""

# Re-export existing utilities
from modules.core.database.db_models import get_database_base, SQLiteJSON

# New unified interface
from .database_interface import DatabaseInterface

# Auto-discovery decorators
from .decorators import register_service, register_database, register_models, requires_modules

# Convenience aliases
DatabaseBase = get_database_base
JSON = SQLiteJSON

# Make available for direct import
__all__ = [
    "DatabaseInterface",
    "DatabaseBase", 
    "get_database_base",  # Backwards compatibility
    "JSON",
    "SQLiteJSON",  # Backwards compatibility
    "register_service",
    "register_database", 
    "register_models",
    "requires_modules"
]
```

```python
# Create core/decorators.py - auto-discovery decorators
"""Auto-discovery decorators for module metadata."""

def register_service(service_name: str):
    """Register a service for auto-discovery."""
    def decorator(cls):
        if not hasattr(cls, '_registered_services'):
            cls._registered_services = []
        cls._registered_services.append(service_name)
        return cls
    return decorator

def register_database(database_name: str):
    """Register a database for auto-discovery.""" 
    def decorator(cls):
        if not hasattr(cls, '_registered_databases'):
            cls._registered_databases = []
        cls._registered_databases.append(database_name)
        return cls
    return decorator

def register_models(model_names: List[str]):
    """Register model names for auto-discovery."""
    def decorator(cls):
        if not hasattr(cls, '_registered_models'):
            cls._registered_models = []
        cls._registered_models.extend(model_names)
        return cls
    return decorator

def requires_modules(*module_names: str):
    """Declare module dependencies for auto-discovery."""
    def decorator(cls):
        cls._required_dependencies = list(module_names)
        return cls
    return decorator
```

---

## Usage Patterns

### **Current vs New Patterns**

#### **Database Session Access**
```python
# OLD: Verbose pattern
session_factory = self.database_service.get_database_session("semantic_core")
async with session_factory() as session:
    result = await session.execute(select(Document))

# NEW: Clean pattern  
async with self.app_context.db.session("semantic_core") as session:
    result = await session.execute(select(Document))

# ALTERNATIVE: Even shorter with property
async with self.db.session("semantic_core") as session:
    result = await session.execute(select(Document))
```

#### **Module Definition Patterns**
```python
# OLD: Separate manifest.json + manual registration
# manifest.json:
# {
#   "id": "semantic_core",
#   "name": "Semantic Core", 
#   "dependencies": ["core.database"]
# }
# 
# api.py:
# class SemanticCoreModule:
#     pass  # Manual registration in initialize()

# NEW: Everything in api.py with auto-discovery
"""
Semantic Core Operations Module
Provides document semantic analysis and similarity operations.
"""

# Module metadata (single source of truth)
MODULE_ID = "semantic_core"
MODULE_NAME = "Semantic Core Operations"
MODULE_VERSION = "1.2.0"
MODULE_AUTHOR = "RAH Framework"
MODULE_DESCRIPTION = __doc__.strip()

# Auto-discovery decorators
@register_service("semantic_core.service")
@register_database("semantic_core")
@register_models(["Document", "DocumentChange"])
@requires_modules(["core.database", "core.settings"])
class SemanticCoreModule(DatabaseEnabledModule):
    pass
```

#### **Import Patterns**
```python
# OLD: Mixed imports
from modules.core.database.db_models import get_database_base, SQLiteJSON
from modules.core.database.database_infrastructure import get_database_base

# NEW: Unified import with decorators
from core.database import DatabaseBase, JSON, register_service, register_database

# Usage 
MyBase = DatabaseBase("my_database")
metadata_col = Column(JSON)
```

#### **Model Access**
```python
# OLD: Manual model management in _get_models()
def _get_models(self):
    from .db_models import Document, DocumentChange
    return {"Document": Document, "DocumentChange": DocumentChange}

# NEW: Auto-discovered models (no manual maintenance)
def get_metadata(self):
    return {
        "models": self._discover_models_from_db_file(),  # Auto-discovered
        "services": getattr(self.__class__, '_registered_services', [])  # From decorators
    }
```

---

## Implementation Strategy

### **Phase 1: Core Interface**
1. **Create DatabaseInterface class** in `core/database_interface.py`
2. **Add to AppContext** as `database` property
3. **Test with existing modules** - verify backwards compatibility

### **Phase 2: Import Unification**  
1. **Create core/database.py** re-export module
2. **Update imports** across framework modules
3. **Verify bootstrap sequence** still works correctly

### **Phase 3: Enhanced Features**
1. **Add model registry** support to AppContext
2. **Implement utility methods** (exists, list_databases)
3. **Add comprehensive error handling**

---

## Bootstrap Compatibility

### **Timing Requirements Preserved**

```
T+100ms: Database Phase 1
├─ DatabaseService creation (unchanged)
├─ Database discovery (unchanged)  
├─ Database creation (unchanged)
└─ Service registration (unchanged)

T+150ms: Settings Phase 1  
├─ DatabaseInterface becomes available
├─ Modules can use app_context.database
└─ Session access works normally

T+300ms: Standard Modules
├─ All database operations work
├─ New convenient patterns available
└─ Old verbose patterns still work
```

### **Multi-Database Support Maintained**

```python
# Each module's database remains separate
semantic_db = app_context.db.session("semantic_core")
vector_db = app_context.db.session("vector_operations") 
framework_db = app_context.db.session("framework")

# Database discovery still scans all db_models.py files
# Table creation still happens per-database
# No architectural changes to bootstrap sequence
```

---

## Error Handling

### **Error Categories**

```python
class DatabaseInterfaceError(Exception):
    """Base exception with structured context."""
    def __init__(self, message: str, context: Dict[str, Any] = None):
        super().__init__(message)
        self.context = context or {}

class DatabaseNotFoundError(DatabaseInterfaceError):
    """Database not registered or not accessible."""
    pass

class SessionCreationError(DatabaseInterfaceError):
    """Cannot create database session."""
    pass

class ModelRegistryError(DatabaseInterfaceError):
    """Issues with model registration or access."""
    pass
```

### **Error Context**

```python
# Provide rich error context for debugging
try:
    async with db.session("nonexistent") as session:
        pass
except DatabaseNotFoundError as e:
    # e.context = {
    #     "requested_database": "nonexistent",
    #     "available_databases": ["framework", "semantic_core"],
    #     "bootstrap_phase": "complete",
    #     "suggestions": ["Check DATABASE_NAME in db_models.py"]
    # }
```

---

## Testing Strategy

### **Unit Tests**
- Test DatabaseInterface methods in isolation
- Mock DatabaseService for controlled testing
- Verify error handling and edge cases

### **Integration Tests**
- Test with actual database services
- Verify session creation and management
- Test model access patterns

### **Bootstrap Tests**
- Ensure interface available after Phase 1
- Test timing dependencies preserved
- Verify backwards compatibility

### **Performance Tests**  
- Benchmark session creation overhead
- Compare old vs new patterns
- Monitor memory usage patterns

---

## Migration Guide

### **For Existing Modules**

```python
# STEP 1: Add convenience property (optional)
class MyModuleService:
    @property
    def db(self):
        return self.app_context.database

# STEP 2: Use new session pattern (gradual)
# async with self.db.session("my_db") as session:
#     # operations

# STEP 3: Update imports (when ready)  
# from core.database import DatabaseBase, JSON

# STEP 4: Use model registry (optional)
# def _get_models(self):
#     return self.db.models("my_database")
```

### **For New Modules**
- Use unified imports from day one
- Utilize convenience session patterns  
- Leverage model registry features
- Follow new error handling patterns

---

## Conclusion

This specification provides a clear path to improved database interfaces while preserving all critical framework architecture. The convenience layer approach ensures compatibility while dramatically improving the developer experience and LLM automation capabilities.
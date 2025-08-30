# Backward Compatibility Tracking - Temporary Migration Aid

## ⚠️ CRITICAL: This is TEMPORARY Compatibility Only

**All items in this document represent technical debt that MUST be removed in Phase 4.**

This document tracks every piece of backward compatibility code added during the framework refactor. Each item must be:
1. **Documented** with deprecation warnings
2. **Usage tracked** to ensure complete migration
3. **Removed entirely** in Phase 4

---

## Compatibility Removal Schedule

| Phase | Old Pattern Status | Action Required |
|-------|-------------------|-----------------|
| **Phase 1-2** | ⚠️ **DEPRECATED** - Warnings logged | Both patterns work, migration encouraged |
| **Phase 3** | 🚨 **LOUD WARNINGS** - Migration assistance | Old patterns work but nag heavily |
| **Phase 4** | ❌ **REMOVED ENTIRELY** - Hard errors | Only new patterns exist |

---

## Database Pattern Compatibility

### 1. Old Verbose Session Access

**DEPRECATED PATTERN:**
```python
# OLD - TO BE REMOVED IN PHASE 4
session_factory = self.database_service.get_database_session("semantic_core")
async with session_factory() as session:
    # operations
```

**NEW PATTERN:**
```python
# NEW - FINAL PATTERN
async with self.app_context.database.integrity_session("semantic_core", purpose="document_analysis") as session:
    # operations with mandatory integrity validation
```

**Compatibility Implementation:**
- **File:** `modules/core/database/services.py`
- **Method:** `DatabaseService.get_database_session()` 
- **Status:** ✅ **IMPLEMENTED** - Deprecation wrapper active
- **Removal Ticket:** #XXX-REMOVE-OLD-DATABASE-PATTERNS
- **Usage Tracking:** ✅ Active - Logs all calls with caller location + Python warnings

**Required Deprecation Code:**
```python
def get_database_session(self, database_name: str):
    """DEPRECATED: Use app_context.database.integrity_session() instead.
    
    This method will be REMOVED in Phase 4.
    """
    import warnings
    import inspect
    
    caller = inspect.getframeinfo(inspect.currentframe().f_back)
    location = f"{caller.filename}:{caller.lineno}"
    
    warnings.warn(
        f"DEPRECATED: get_database_session() called from {location}. "
        f"Use app_context.database.integrity_session() instead. "
        f"This method will be REMOVED in Phase 4.",
        DeprecationWarning,
        stacklevel=2
    )
    
    # Log usage for migration tracking
    self._log_deprecated_usage("get_database_session", location, database_name)
    
    # Forward to new implementation
    return self._compatibility_session_factory(database_name)
```

---

## Import Pattern Compatibility

### 1. Old Database Imports

**DEPRECATED PATTERNS:**
```python
# OLD - TO BE REMOVED IN PHASE 4
from modules.core.database.db_models import get_database_base, SQLiteJSON
from modules.core.database.database_infrastructure import get_database_base, SQLiteJSON
```

**NEW PATTERN:**
```python
# NEW - FINAL PATTERN
from core.database import DatabaseBase, SQLiteJSON
```

**Compatibility Implementation:**
- **Files:** `core/database.py` - Unified interface with deprecation warnings
- **Status:** ✅ **IMPLEMENTED** - Deprecation wrapper active for get_database_base()
- **Removal Ticket:** #XXX-REMOVE-OLD-IMPORTS  
- **Usage Tracking:** ✅ Active - Python warnings + deprecation logging

**Implementation Details:**
- Created `core/database.py` as single import point
- `DatabaseBase()` replaces `get_database_base()` with integrity validation
- All database utilities available: `SQLiteJSON`, `execute_with_retry`
- Backward compatibility via deprecated `get_database_base()` with warnings
- Data integrity validation built into all database utilities

**Required Deprecation Code:**
```python
# In modules/core/database/db_models.py
import warnings
import inspect

def get_database_base(*args, **kwargs):
    """DEPRECATED: Import from core.database instead.
    
    This function will be REMOVED in Phase 4.
    """
    caller = inspect.getframeinfo(inspect.currentframe().f_back)
    location = f"{caller.filename}:{caller.lineno}"
    
    warnings.warn(
        f"DEPRECATED: Importing get_database_base from modules.core.database.db_models at {location}. "
        f"Use 'from core.database import DatabaseBase' instead. "
        f"This import path will be REMOVED in Phase 4.",
        DeprecationWarning,
        stacklevel=2
    )
    
    # Forward to new implementation
    from core.database import DatabaseBase
    return DatabaseBase(*args, **kwargs)
```

---

## Module Pattern Compatibility

### 1. manifest.json Support

**DEPRECATED PATTERN:**
```json
// OLD - TO BE REMOVED IN PHASE 4
{
  "id": "semantic_core",
  "name": "Semantic Core Operations",
  "version": "1.2.0"
}
```

**NEW PATTERN:**
```python
# NEW - FINAL PATTERN in api.py
MODULE_ID = "semantic_core"
MODULE_NAME = "Semantic Core Operations"
MODULE_VERSION = "1.2.0"
```

**Compatibility Implementation:**
- **File:** `core/module_loader.py`
- **Status:** 🔄 **TO BE IMPLEMENTED** - Add manifest.json fallback with warnings
- **Removal Ticket:** #XXX-REMOVE-MANIFEST-SUPPORT
- **Usage Tracking:** Log all manifest.json loads

---

## Error Pattern Compatibility

### 1. Old error_message() if superseded

**Status:** ✅ **NOT NEEDED** - New framework-aware logging enhances rather than replaces error_message()

---

## Migration Tracking Infrastructure

### Usage Logging System

**Required Implementation:**
```python
# core/compatibility_tracker.py
class CompatibilityTracker:
    """Track usage of deprecated patterns for migration assistance."""
    
    def __init__(self):
        self.usage_log = {}
        self.log_file = "data/logs/compatibility_usage.jsonl"
    
    def log_usage(self, pattern_type: str, pattern_name: str, location: str, details: dict = None):
        """Log usage of deprecated pattern."""
        import time
        import json
        
        entry = {
            "timestamp": time.time(),
            "pattern_type": pattern_type,  # "database", "import", "module"
            "pattern_name": pattern_name,  # "get_database_session", "old_import"
            "location": location,          # "file.py:123"
            "details": details or {}
        }
        
        # Append to log file
        with open(self.log_file, 'a') as f:
            f.write(json.dumps(entry) + '\n')
        
        # Track in memory for statistics
        key = f"{pattern_type}.{pattern_name}"
        if key not in self.usage_log:
            self.usage_log[key] = {"count": 0, "locations": set()}
        
        self.usage_log[key]["count"] += 1
        self.usage_log[key]["locations"].add(location)
    
    def get_migration_report(self) -> dict:
        """Generate report of remaining deprecated pattern usage."""
        return {
            "total_patterns": len(self.usage_log),
            "total_usages": sum(data["count"] for data in self.usage_log.values()),
            "by_pattern": {
                pattern: {
                    "count": data["count"],
                    "unique_locations": len(data["locations"]),
                    "locations": list(data["locations"])
                }
                for pattern, data in self.usage_log.items()
            }
        }
```

### Migration Assistance Commands

**Required CLI Tools:**
```bash
# Check for remaining deprecated usage
python tools/migration_check.py --report

# Show migration help for specific pattern
python tools/migration_check.py --help get_database_session

# Generate migration patches
python tools/migration_check.py --auto-migrate database_patterns
```

---

## Phase 4 Removal Checklist

### Database Patterns
- [ ] Delete `DatabaseService.get_database_session()` method
- [ ] Remove compatibility session factory code
- [ ] Update all error messages to reference only new patterns
- [ ] Remove deprecation warning infrastructure

### Import Patterns  
- [ ] Delete `modules/core/database/db_models.py` compatibility exports
- [ ] Delete `modules/core/database/database_infrastructure.py` compatibility exports
- [ ] Remove old import path documentation
- [ ] Force all imports through `core.database` only

### Module Patterns
- [ ] Remove `manifest.json` loading support from `ModuleLoader`
- [ ] Delete manifest.json files from all modules
- [ ] Remove manifest.json documentation
- [ ] Enforce MODULE_* constants as only metadata source

### Infrastructure
- [ ] Delete `CompatibilityTracker` class
- [ ] Remove migration assistance tools
- [ ] Delete this tracking document
- [ ] Update all documentation to show only new patterns
- [ ] Remove deprecation warning systems

### Validation
- [ ] Run full test suite - should pass with only new patterns
- [ ] Verify bootstrap sequence works with only new patterns
- [ ] Confirm no old pattern references remain in codebase
- [ ] Validate all modules use only new patterns

---

## Success Metrics for Phase 4

- **Zero deprecated code**: No backward compatibility remains
- **Zero old documentation**: Only new patterns documented  
- **Zero migration artifacts**: No transition infrastructure remains
- **Single pattern enforcement**: One way to do each operation
- **Clean codebase**: No legacy pattern references anywhere

---

**Remember: Every item in this document represents technical debt that MUST be eliminated. The goal is a clean, single-pattern framework with no legacy baggage.**
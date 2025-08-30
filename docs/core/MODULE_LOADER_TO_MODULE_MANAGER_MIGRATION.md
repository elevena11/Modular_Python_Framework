# Module Loader to Module Manager Migration Guide

**Date**: August 11, 2025  
**Context**: Framework transition from complex module_loader system to clean module_manager  
**Scope**: Critical migration pattern for all modules using module discovery

## Problem Overview

The framework migrated from `module_loader` (complex dictionary-based system) to `module_manager` (clean ModuleInfo dataclass system). This breaks modules that access module metadata using dictionary patterns.

### Key Error Pattern
```python
# OLD PATTERN (BREAKS)
module_data = self.app_context.module_loader.modules[module_id]
manifest = module_data.get("manifest", {})  # AttributeError: 'ModuleInfo' object has no attribute 'get'
version = manifest.get("version")
```

### Root Cause
- **Old system**: `modules[id]` returned dictionaries with `.get()` method
- **New system**: `modules[id]` returns `ModuleInfo` dataclass with direct attributes

## ModuleInfo Structure

The new `ModuleInfo` dataclass (defined in `core/module_manager.py`):

```python
@dataclass
class ModuleInfo:
    id: str                          # Module identifier
    name: str                        # Module display name  
    path: str                        # File system path
    class_obj: type                  # Module class object
    service_name: Optional[str] = None
    dependencies: List[str] = None
    phase2_method: Optional[str] = None
    priority: int = 100
    phase2_priority: int = 100
```

## Migration Pattern

### 1. Update Module Manager References

**BEFORE:**
```python
if not hasattr(self.app_context, 'module_loader'):
    return False
    
for module_id, module_data in self.app_context.module_loader.modules.items():
```

**AFTER:**
```python  
if not hasattr(self.app_context, 'module_manager'):
    return False
    
for module_id, module_info in self.app_context.module_manager.modules.items():
```

### 2. Update Data Access Patterns

**BEFORE (Dictionary Access):**
```python
module_data = self.app_context.module_loader.modules[module_id]
module_instance = module_data.get("module")
manifest = module_data.get("manifest", {})
version = manifest.get("version", "unknown")
```

**AFTER (Attribute Access):**
```python
module_info = self.app_context.module_manager.modules[module_id]
module_class = module_info.class_obj
version = getattr(module_class, "MODULE_VERSION", "unknown")
```

### 3. Version Resolution Pattern

**BEFORE (Manifest-based):**
```python
def get_module_version(self, module_id):
    module_data = self.app_context.module_loader.modules[module_id]
    manifest = module_data.get("manifest", {})
    return manifest.get("version", "unknown")
```

**AFTER (Class-based):**
```python
def get_module_version(self, module_id):
    module_info = self.app_context.module_manager.modules[module_id]
    if hasattr(module_info.class_obj, "MODULE_VERSION"):
        return module_info.class_obj.MODULE_VERSION
    return "unknown"
```

## Real Example: Settings Module Migration

### Problem Location
`modules/core/settings/service_components/core_service.py`

### Specific Fixes Applied

**1. `_resolve_module_version()` method:**
```python
# BEFORE
module_data = self.app_context.module_manager.modules[module_id]
module_instance = module_data.get("module")  # ❌ AttributeError
manifest = module_data.get("manifest", {})   # ❌ AttributeError

# AFTER  
module_info = self.app_context.module_manager.modules[module_id]
if hasattr(module_info.class_obj, "MODULE_VERSION"):  # ✅ Direct access
    version = module_info.class_obj.MODULE_VERSION
```

**2. `_update_all_settings_versions()` method:**
```python
# BEFORE
for module_id, module_data in self.app_context.module_manager.modules.items():
    manifest = module_data.get("manifest", {})  # ❌ AttributeError
    manifest_version = manifest["version"]

# AFTER
for module_id, module_info in self.app_context.module_manager.modules.items():
    if hasattr(module_info.class_obj, "MODULE_VERSION"):  # ✅ Direct access
        manifest_version = module_info.class_obj.MODULE_VERSION
```

## Impact Assessment

### Modules Likely Affected
Any module that:
- Accesses `self.app_context.module_loader.modules`
- Uses `.get()` method on module data  
- Reads manifest information
- Implements cross-module version checking
- Performs module discovery operations

### Search Commands
```bash
# Find modules still using old pattern
rg "module_loader" modules/ --type py
rg "\.get\(\"manifest" modules/ --type py  
rg "\.get\(\"module" modules/ --type py
rg "modules\[.*\]\.get" modules/ --type py
```

## Warning Signs in Logs

**Error Pattern:**
```
AttributeError: 'ModuleInfo' object has no attribute 'get'
```

**Warning Pattern:**
```
MODULE_LOADER_UNAVAILABLE - Cannot update: module_loader not available
```

## Quick Fix Template

For any module showing these errors:

1. **Replace references:**
   - `module_loader` → `module_manager`
   - `module_data` → `module_info`

2. **Update access pattern:**
   - `module_data.get("key")` → `module_info.attribute`
   - `manifest.get("version")` → `module_info.class_obj.MODULE_VERSION`

3. **Test verification:**
   - Check for AttributeError elimination
   - Verify module version resolution works
   - Confirm module registration succeeds

## Migration Success Indicators

✅ **No more MODULE_LOADER_UNAVAILABLE warnings**  
✅ **No more 'ModuleInfo' object has no attribute 'get' errors**  
✅ **Module version resolution working**  
✅ **Module registration completing successfully**  

## Framework Context

This migration is part of the broader framework evolution:
- **Phase 1**: Bootstrap independence (database creation)
- **Phase 2**: Module system cleanup (loader → manager)  
- **Phase 3**: Full decorator-driven automation

The module_manager system provides cleaner, more maintainable module handling with explicit dataclass structures instead of nested dictionaries.
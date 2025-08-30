# Core Module Migration Plan - Decorator Pattern

## Overview
This document tracks the systematic migration of **core modules only** from legacy `initialize()` pattern to the new decorator-based pattern. Standard modules will be migrated as a separate project phase.

## Scope: Core Framework Modules Only
**Total core modules**: 6
**Standard modules**: Deferred to later phase

## Migration Status

### ✅ Completed (1/6 core modules)
- `core.framework` - **MIGRATED** (formerly core.global)

### 🎯 Phase 3A: Database Test Module (Migration Validation)
**Priority: HIGH - Validate migration process with simple test module**

1. `standard.test_table_driven` 
   - Dependencies: None
   - Features: Service only  
   - Complexity: **VERY LOW**
   - Purpose: **Test module for database refactor** - perfect migration candidate
   - Estimated effort: 30 minutes

### 🎯 Phase 3B: Core Infrastructure Modules  
**Priority: CRITICAL - Foundation modules everything depends on**

2. `core.database`
   - Dependencies: None (foundation)
   - Features: Database management, utilities
   - Complexity: **HIGH**
   - Risk: **CRITICAL** - Everything depends on this
   - Estimated effort: 2-3 hours

3. `core.settings`
   - Dependencies: core.database
   - Features: Service, Database, API endpoints
   - Complexity: **MEDIUM** 
   - Risk: **HIGH** - Many modules depend on this
   - Estimated effort: 1-2 hours

4. `core.error_handler`
   - Dependencies: None (self-contained)
   - Features: Service, Database (optional), File logging
   - Complexity: **MEDIUM**
   - Risk: **CRITICAL** - Used everywhere for logging
   - Estimated effort: 1-2 hours

### 🎯 Phase 3C: Supporting Core Modules
**Priority: MEDIUM - Important but not foundation-critical**

5. `core.scheduler`
   - Dependencies: core.database, core.settings
   - Features: Service, Database, API endpoints, Background tasks
   - Complexity: **MEDIUM-HIGH**
   - Estimated effort: 1-2 hours

6. `core.model_manager`
   - Dependencies: TBD
   - Features: Model management
   - Complexity: **MEDIUM**
   - Estimated effort: 1-2 hours

### 📋 Standard Modules - DEFERRED
**These will be migrated in a separate phase after core framework is stable:**
- `standard.crypto_database`
- `standard.document_processing` 
- `standard.semantic_cli`
- `standard.semantic_core`
- `standard.vector_operations`

## Migration Strategy

### Step-by-Step Process
1. **Create backup**: Copy `api.py` to `api_legacy.py`
2. **Add MODULE_* constants**: Extract info from manifest.json
3. **Create module class**: With appropriate decorators
4. **Add legacy compatibility**: Keep old functions during transition
5. **Test thoroughly**: Ensure functionality preserved
6. **Document changes**: Update patch notes
7. **Remove manifest.json**: Only after testing (Phase 4)

### Validation Criteria
Each migrated module must pass:
- ✅ Decorator metadata detection
- ✅ Centralized processing
- ✅ Framework startup integration  
- ✅ Legacy compatibility
- ✅ All original functionality preserved

### Risk Mitigation
- **Start with simplest modules** to validate process
- **Keep legacy compatibility** until all modules migrated
- **Test each module individually** before proceeding
- **Document all changes** for rollback if needed
- **Core modules get extra testing** due to dependency risk

## Current Focus
**Next Target**: `standard.test_table_driven` (database test module, no dependencies)

## Revised Strategy Benefits
- **Focus on core framework** - Get foundation solid first
- **Standard modules deferred** - Application logic can wait
- **Reduced scope** - 6 modules instead of 12
- **Faster to Phase 4** - Core legacy removal achievable sooner

## Notes
- **Core modules**: 6 total (1 completed, 5 remaining)
- **Standard modules**: 6 total (deferred to separate phase)
- **Phase 4 (Legacy Removal)**: Can proceed once 5 core modules migrated
- **Risk reduction**: Focus on framework foundation first
# Implementation Plan: Clean Decorator Architecture

**Status**: Ready to implement  
**Target**: Pure decorator-based module system  
**Priority**: High (blocks Settings V2 and future development)

## Implementation Strategy

### Phase-by-Phase Approach
1. **Validate Template** - Create working example
2. **Core Module Migration** - One module at a time  
3. **Framework Integration** - Ensure end-to-end functionality
4. **Validation** - Test database writes and service availability

## Phase 1: Template Validation

### Goal: Prove the decorator template works end-to-end

**Step 1.1: Create Test Module**
```bash
# Create simple test module using pure decorator pattern
modules/test/decorator_validation/
├── api.py              # Pure decorator implementation
├── services.py         # Service class
└── db_models.py        # Database models (optional)
```

**Success Criteria**:
- ✅ Module loads successfully
- ✅ Services registered and available in Phase 2
- ✅ Database writes work (if applicable)
- ✅ No "service unavailable" errors

**Step 1.2: Template Refinement**
- Fix any issues discovered
- Document working patterns
- Create template generator tool

**Deliverables**:
- Working test module
- Validated decorator template
- Template generation script

---

## Phase 2: Core Module Migration

### Goal: Migrate core modules to pure decorator pattern

**Priority Order**:
1. **core.database** (foundation - other modules depend on it)
2. **core.settings** (configuration system)  
3. **core.error_handler** (logging and error management)
4. **core.framework** (module management)
5. **core.model_manager** (ML model management)

### Step 2.1: core.database Migration

**Current State**:
- ✅ Services registered via decorators
- ❌ Mixed manual/decorator patterns in initialization
- ❌ Phase 1 service access patterns

**Migration Tasks**:
```python
# Target pattern for core.database
@register_service("core.database.service", priority=10)
@register_service("core.database.crud_service", priority=15)  
@auto_service_creation(DatabaseService)
@phase2_operations("setup", priority=20)
class DatabaseModule:
    def __init__(self, app_context):
        """Phase 1: Basic setup only."""
        self.app_context = app_context
        # No complex operations
    
    async def setup(self):
        """Phase 2: Database initialization."""
        # Database already created by bootstrap
        return await self.database_service.initialize()
```

**Success Criteria**:
- ✅ Clean Phase 1/Phase 2 separation
- ✅ Services available when expected
- ✅ Database operations working
- ✅ Other modules can access database services

### Step 2.2: core.settings Migration

**Current Issues**:
- ❌ Phase 1 service access (trying to get database service in `__init__`)
- ❌ Complex initialization timing issues
- ❌ Mixed manual registration patterns

**Migration Tasks**:
```python
# Target pattern for core.settings  
@register_service("core.settings.service", priority=30)
@auto_service_creation(SettingsService)
@requires_services(["core.database.service"])
@phase2_operations("setup", dependencies=["core.database.setup"], priority=50)
class SettingsModule:
    def __init__(self, app_context):
        """Phase 1: Basic setup only."""
        self.app_context = app_context
        self.database_service = None  # Set in Phase 2
    
    async def setup(self):
        """Phase 2: Settings initialization."""
        self.database_service = self.app_context.get_service("core.database.service")
        return await self.settings_service.initialize()
```

**Success Criteria**:
- ✅ Can access database service in Phase 2
- ✅ Settings load and save to database
- ✅ No "database service unavailable" errors
- ✅ Other modules can access settings service

### Step 2.3: Remaining Core Modules

**Apply same pattern to**:
- core.error_handler
- core.framework  
- core.model_manager

**Common Migration Pattern**:
1. Remove manual service registration
2. Add proper decorators
3. Move service access to Phase 2
4. Test service availability

---

## Phase 3: Framework Integration Testing

### Goal: Ensure decorator system works end-to-end

**Step 3.1: Service Registration Validation**
```bash
# Test that all core services are properly registered
python -c "
import asyncio
from core.app_context import AppContext
from core.config import settings

async def test_services():
    app_context = AppContext(settings)
    # ... load modules ...
    
    # Verify all services available
    db_service = app_context.get_service('core.database.service')
    settings_service = app_context.get_service('core.settings.service')
    
    print(f'Database service: {db_service is not None}')
    print(f'Settings service: {settings_service is not None}')

asyncio.run(test_services())
"
```

**Step 3.2: Database Write Testing**
```bash
# Test that modules can write to database
python tools/database_inspection/inspect_sqlite.py --db-path data/database/framework.db --list

# Should show non-zero rows in tables:
# - modules (module registration data)
# - settings_events (settings changes)
# - error_examples (error handler data)
```

**Step 3.3: Clean Startup Validation**
```bash
# Test clean startup with no errors
python app.py

# Should see:
# - No "service unavailable" errors
# - All modules Phase 2 complete
# - Database tables populated
```

**Success Criteria**:
- ✅ All services available when expected
- ✅ Database tables populated with data
- ✅ Clean startup logs (no errors)
- ✅ Modules can interact with each other

---

## Phase 4: Implementation Validation

### Goal: Confirm clean architecture works fully

**Step 4.1: Database Content Verification**
```bash
# Verify data being written to all tables
python tools/database_inspection/inspect_sqlite.py --db-path data/database/framework.db --query "
SELECT 
    name as table_name,
    (SELECT COUNT(*) FROM sqlite_master sm2 WHERE sm2.name = name AND sm2.type = 'table') as row_count
FROM sqlite_master 
WHERE type = 'table' 
    AND name NOT LIKE 'sqlite_%'
ORDER BY name;
"

# Expected: All tables should have > 0 rows
```

**Step 4.2: Service Interaction Testing**
```python
# Test inter-module service usage
async def test_service_interactions():
    # Settings using database service
    settings_service = app_context.get_service("core.settings.service")
    await settings_service.save_setting("test_key", "test_value")
    
    # Error handler using database service  
    error_service = app_context.get_service("core.error_handler.service")
    await error_service.log_error("TEST_ERROR", "Test error message")
    
    # Verify data written to database
    # Check settings_events and error_examples tables
```

**Step 4.3: Performance Validation**
```bash
# Measure startup time with clean architecture
time python -c "
import asyncio
from app import lifespan
from fastapi import FastAPI

async def test_startup():
    app = FastAPI()
    async with lifespan(app):
        print('Startup complete')

asyncio.run(test_startup())
"

# Target: < 5 seconds startup time
```

**Success Criteria**:
- ✅ **Database Integration**: All tables populated, modules writing data
- ✅ **Service Availability**: No "service unavailable" errors anywhere
- ✅ **Performance**: Startup time reasonable (< 5 seconds)
- ✅ **Clean Logs**: No errors, warnings, or issues in logs

---

## Implementation Timeline

### Week 1: Template and Database
- **Day 1-2**: Create and validate decorator template
- **Day 3-5**: Migrate core.database module
- **End of Week**: Database services working properly

### Week 2: Settings and Error Handler  
- **Day 1-3**: Migrate core.settings module
- **Day 4-5**: Migrate core.error_handler module
- **End of Week**: Core configuration and error handling working

### Week 3: Framework Integration
- **Day 1-2**: Migrate remaining core modules
- **Day 3-4**: Framework integration testing
- **Day 5**: Performance and validation testing

### Week 4: Documentation and Cleanup
- **Day 1-2**: Update documentation to match implementation
- **Day 3-4**: Create migration guides and templates
- **Day 5**: Final validation and sign-off

---

## Risk Mitigation

### High Risk: Service Availability
**Risk**: Services still not available when expected
**Mitigation**: 
- Create comprehensive service availability tests
- Implement dependency validation in framework
- Add clear error messages for missing dependencies

### Medium Risk: Database Integration
**Risk**: Database writes still not working after migration
**Mitigation**:
- Test database operations at each migration step
- Validate database service creation and availability
- Create simple database write tests

### Low Risk: Performance Impact
**Risk**: Decorator overhead slows startup
**Mitigation**:
- Benchmark startup time before/after
- Optimize decorator implementation if needed
- Profile startup to identify bottlenecks

---

## Success Definition

### Primary Goals (Must Have)
1. ✅ **No "service unavailable" errors** in any logs
2. ✅ **Database tables populated** with module data
3. ✅ **All services available** when modules expect them
4. ✅ **Clean startup logs** without errors or warnings

### Secondary Goals (Nice to Have)
1. ✅ **Fast startup time** (< 5 seconds)
2. ✅ **Consistent patterns** across all modules
3. ✅ **Easy module development** with templates
4. ✅ **Clear documentation** matching implementation

### Framework Ready Criteria
- **Settings V2 Development**: Framework can support new settings system
- **Module Development**: New modules can be created easily with template
- **Maintenance**: System is maintainable and debuggable
- **Reliability**: System starts consistently without issues

---

This implementation plan provides a clear path to achieve the clean decorator architecture while ensuring each step is validated before proceeding to the next.
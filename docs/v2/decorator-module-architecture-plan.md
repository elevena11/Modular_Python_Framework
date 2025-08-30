# Decorator-Based Module Architecture Plan

**Status**: ✅ IMPLEMENTED (August 2025)  
**Target**: Clean decorator system design  
**Current State**: ✅ PRODUCTION READY - All core modules migrated successfully

## ✅ RESOLVED Problems (August 2025)

### 1. Mixed Architecture Patterns - RESOLVED
- ✅ **Pure decorator system** - All modules use consistent decorator patterns
- ✅ **Clean Phase 1/Phase 2 separation** - No service access in `__init__()`  
- ✅ **Database services available** via @require_services pattern
- ✅ **Database writes working** - All core modules operational

### 2. Timing Issues - RESOLVED
- ✅ **Bootstrap + Module coordination** - Services available when needed
- ✅ **Decorator services available** in Phase 2 as expected
- ✅ **Clear Phase 1/Phase 2 patterns** - @require_services for Phase 2 access

### 3. Architectural Inconsistencies - RESOLVED
- ✅ **All modules use decorators** - 100% decorator coverage for core modules
- ✅ **Consistent service access** - @require_services + get_required_service() pattern
- ✅ **No service availability errors** - Guaranteed service availability in Phase 2

## ✅ IMPLEMENTED Decorator Architecture

### Core Principles

1. **Pure Decorator Pattern**: No manual service registration anywhere
2. **Clear Phase Separation**: Phase 1 = registration, Phase 2 = service access
3. **Predictable Service Availability**: Services available when expected
4. **Self-Contained Modules**: Each module declares what it needs/provides

### Module Structure Template

```python
"""
Standard Decorator-Based Module Template
"""
import logging
from core.decorators import (
    register_service,
    phase2_operations, 
    requires_services,
    auto_service_creation
)

# Module metadata
MODULE_ID = "standard.example_module"
logger = logging.getLogger(MODULE_ID)

# Auto-create and register main service
# Database models discovered automatically from db_models.py (no @register_models needed)
@register_service(f"{MODULE_ID}.service", priority=100)
@auto_service_creation(ExampleService)
@require_services(["core.database.service", "core.settings.service"])
@phase2_operations("setup", dependencies=["core.database.phase2_auto"], priority=150)
class ExampleModule:
    """Example decorator-based module."""
    
    def __init__(self, app_context):
        """Phase 1: Basic setup only - NO service access."""
        self.app_context = app_context
        self.MODULE_ID = MODULE_ID
        self.logger = logger
        
        # Services will be available in Phase 2
        self.database_service = None
        self.settings_service = None
        
        logger.info(f"{MODULE_ID}: Phase 1 registration complete")
    
    async def setup(self):
        """Phase 2: Service access and complex initialization."""
        try:
            # Access required services (guaranteed available by @require_services)
            self.database_service = self.get_required_service("core.database.service")
            self.settings_service = self.get_required_service("core.settings.service")
            
            # Verify services are available
            if not self.database_service or not self.settings_service:
                logger.error(f"{MODULE_ID}: Required services not available")
                return False
            
            # Complex initialization
            await self._initialize_database_operations()
            await self._load_module_settings()
            await self._start_background_tasks()
            
            logger.info(f"{MODULE_ID}: Phase 2 initialization complete")
            return True
            
        except Exception as e:
            logger.error(f"{MODULE_ID}: Phase 2 initialization failed: {str(e)}")
            return False
    
    async def _initialize_database_operations(self):
        """Initialize database-related functionality."""
        # Database guaranteed to exist (created by bootstrap)
        # Database service guaranteed to be available (@requires_services)
        pass
    
    async def _load_module_settings(self):
        """Load module configuration."""
        pass
        
    async def _start_background_tasks(self):
        """Start any background processing."""
        pass

# Service class (created automatically by @auto_service_creation)
class ExampleService:
    """Main service class for this module."""
    
    def __init__(self, app_context):
        self.app_context = app_context
        self.logger = logger
        
    async def do_work(self):
        """Example service method."""
        pass
```

### Decorator System Responsibilities

#### `@register_service(name, priority)`
- **Registers service** with app_context automatically
- **Sets priority** for Phase 2 execution order
- **Creates service instance** and makes it available

#### `@auto_service_creation(ServiceClass)`
- **Automatically creates** service instance from class
- **Handles service lifecycle** (creation, registration, shutdown)
- **Eliminates boilerplate** service creation code

#### `@requires_services([service_list])`
- **Declares service dependencies** explicitly
- **Framework ensures** required services available before Phase 2
- **Fails fast** if dependencies not available

#### `@phase2_operations(method_name, dependencies, priority)`
- **Registers Phase 2 methods** automatically
- **Handles dependency ordering** between modules
- **Manages execution timing** and error handling

#### Database Model Discovery (Automatic)
- **No decorator required** - models discovered from `db_models.py`
- **File-based discovery** scans `DATABASE_NAME` and `__tablename__`
- **Bootstrap creates databases** automatically before modules load
- **Single source of truth** in database model files

### Service Access Pattern

#### Phase 1 (Registration)
```python
def __init__(self, app_context):
    """Phase 1: NO service access allowed."""
    self.app_context = app_context
    # Services set to None - will be available in Phase 2
    self.database_service = None
    self.settings_service = None
```

#### Phase 2 (Service Access)
```python
async def setup(self):
    """Phase 2: Safe service access."""
    # Services guaranteed available by @requires_services
    self.database_service = self.app_context.get_service("core.database.service")
    self.settings_service = self.app_context.get_service("core.settings.service")
    
    # Use services for complex initialization
    await self.database_service.initialize_module_tables()
    config = await self.settings_service.get_module_settings(self.MODULE_ID)
```

## Migration Strategy

### Phase 1: Core Module Conversion
**Target**: Convert core modules to pure decorator pattern

1. **core.database**: 
   - ✅ Already uses decorators for service registration
   - ❌ Needs Phase 1/Phase 2 service access cleanup
   
2. **core.settings**:
   - ❌ Mixed patterns - needs full conversion
   - ❌ Phase 1 service access needs fixing
   
3. **core.error_handler**:
   - ❌ Mixed patterns - needs full conversion
   - ❌ Phase 1 service access needs fixing

### Phase 2: Standard Module Conversion  
**Target**: Update all standard modules to follow decorator template

### Phase 3: Framework Integration
**Target**: Ensure decorator system works end-to-end

1. **Service Registration**: Verify all services available when expected
2. **Phase 2 Execution**: Verify proper dependency ordering
3. **Database Integration**: Verify modules can write to database
4. **Error Handling**: Verify graceful failure modes

## Success Criteria

### 1. Pure Decorator Pattern
- ✅ **No manual service registration** anywhere in codebase
- ✅ **All modules use decorator template**
- ✅ **Consistent service access patterns**

### 2. Working Database Integration
- ✅ **Modules can write to database** (tables have data)
- ✅ **No "service unavailable" errors** in logs
- ✅ **Database services accessible** in Phase 2

### 3. Clean Phase Separation
- ✅ **Phase 1**: Only registration and basic setup
- ✅ **Phase 2**: Service access and complex operations
- ✅ **No service access** in `__init__()` methods

### 4. Dependency Management
- ✅ **Services available when expected**
- ✅ **Proper execution ordering** via dependencies
- ✅ **Clear error messages** when dependencies missing

## Implementation Plan

### Step 1: Design Validation
- [ ] **Review decorator template** with stakeholders
- [ ] **Validate service access patterns** 
- [ ] **Confirm Phase 1/Phase 2 separation** approach

### Step 2: Core Module Migration
- [ ] **core.database**: Complete decorator conversion
- [ ] **core.settings**: Full decorator migration  
- [ ] **core.error_handler**: Full decorator migration
- [ ] **Verify core services work** end-to-end

### Step 3: Framework Testing
- [ ] **Test service registration** timing
- [ ] **Test database service availability**
- [ ] **Test module database writes**
- [ ] **Verify clean startup logs**

### Step 4: Standard Module Migration
- [ ] **Apply decorator template** to standard modules
- [ ] **Test each module** individually
- [ ] **Verify inter-module communication**

### Step 5: Validation and Documentation
- [ ] **End-to-end system test**
- [ ] **Update documentation** to match implementation
- [ ] **Create migration guides** for future modules

## Risk Assessment

### High Risk
- **Service availability timing**: Decorators must ensure services available when expected
- **Database integration**: Core functionality depends on working database services
- **Circular dependencies**: Service access patterns must avoid circular references

### Medium Risk  
- **Migration complexity**: Converting existing modules without breaking functionality
- **Performance impact**: Decorator overhead during startup
- **Error handling**: Maintaining graceful degradation during failures

### Low Risk
- **Documentation updates**: Clear patterns make documentation straightforward
- **Future maintenance**: Consistent patterns easier to maintain
- **Developer experience**: Template-based approach reduces cognitive load

## Next Steps

1. **Review this plan** and get stakeholder buy-in
2. **Validate decorator template** with a simple test module
3. **Start with core.database** complete migration
4. **Test database service availability** end-to-end
5. **Proceed with other core modules** one by one

This plan provides a clear path from the current mixed architecture to a clean, consistent decorator-based system that follows the two-phase initialization pattern properly.
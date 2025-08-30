# FULL DECORATOR SYSTEM PLAN

## CONTEXT & OBJECTIVE

**USER DECISION**: Complete decorator system from scratch - full automation of module boilerplate
**TIMELINE**: 2 days invested, no reverting
**APPROACH**: Ignore old patterns, build clean new system

## WHAT WE'RE LEAVING BEHIND (Never Go Back To)

### Old Manual System Boilerplate (60+ lines per module):
```python
# Global service instance
service_instance = None

async def initialize(app_context):
    global service_instance
    # Manual service creation
    service_instance = MyService(app_context)
    # Manual service registration  
    app_context.register_service(f"{MODULE_ID}.service", service_instance)
    # Manual settings registration
    # Manual hook registration
    # Manual error handling boilerplate...

async def setup_module(app_context):
    # Manual Phase 2 logic
    # Manual settings loading
    # Manual service initialization
    # More manual error handling...

def get_service():
    return service_instance
```

### Half-Way Mixed Patterns (Current Problem):
```python
@register_service(f"{MODULE_ID}.service")  # Decorator
@phase2_setup("initialize") 
class MyModule:
    def __init__(self, app_context):
        self.app_context = app_context           # Still manual
        self.service = MyService(app_context)    # Still manual
        
    async def initialize(self):                  # Still manual
        await self.service.initialize()          # Still manual
```

## TARGET: FULL DECORATOR SYSTEM

### Complete Automation - Zero Manual Boilerplate:
```python
@register_service(f"{MODULE_ID}.service")
@auto_create_service(MyService)
@auto_initialize()
@phase2_setup("setup_complete")
class MyModule:
    MODULE_ID = "standard.my_module"
    # NO MANUAL CODE NEEDED - DECORATORS HANDLE EVERYTHING
```

## IMPLEMENTATION STEPS

### Phase 1: Complete Decorator Set
- [x] `@register_service` - Service registration
- [x] `@auto_create_service` - Automatic service instantiation  
- [x] `@auto_initialize` - Automatic method calling
- [x] `@inject_context` - Automatic context injection
- [x] `@phase2_setup` - Phase 2 automation

### Phase 2: Module Manager Enhancement
- [ ] Update `load_modules()` to handle full automation
- [ ] Implement automatic service creation logic
- [ ] Implement automatic initialization calling
- [ ] Implement automatic context injection

### Phase 3: Update Scaffolding Tool
- [ ] Generate pure declarative modules
- [ ] Use complete decorator set
- [ ] Eliminate all manual boilerplate generation

### Phase 4: Migration & Testing
- [ ] Convert decorator_validation to full decorator pattern
- [ ] Test complete automation works
- [ ] Validate zero manual boilerplate needed

## SUCCESS CRITERIA

**Module developers write:**
```python
@register_service(f"{MODULE_ID}.service")
@auto_create_service(MyService)  
@auto_initialize()
class MyModule:
    MODULE_ID = "standard.my_module"
```

**Framework handles automatically:**
- Service instantiation: `service = MyService(app_context)`
- Context injection: `self.app_context = app_context`
- Service registration: `app_context.register_service()`
- Phase 2 initialization: `await service.initialize()`
- All error handling and logging

## ANTI-PATTERNS TO AVOID

**DO NOT:**
- Question the architectural decision (it's made)
- Implement halfway solutions
- Mix manual and decorator patterns
- Reference old system code for "compatibility"
- Ask "should we go back to manual system?"

**DO:**
- Build complete automation
- Make decorators handle ALL boilerplate
- Keep modules as pure declarations
- Implement from scratch, ignore old patterns

## COLLABORATION PATTERN AWARENESS

**Context Limitation (Claude)**: May drift back to familiar patterns
**Pattern Recognition (User)**: May not notice drift until several steps taken
**Solution**: This plan document to maintain focus

**When Claude starts reverting**: Point to this plan
**When User notices drift**: Reference this document and reset to target

---

**REMEMBER**: We are building a COMPLETE decorator system that eliminates ALL manual boilerplate. No compromises, no halfway solutions.
# Framework Patterns Documentation

This directory contains documentation for the key patterns and practices used throughout the modular framework.

## Framework Patterns Overview

The modular framework is built on several key patterns that ensure consistency, maintainability, and scalability across all modules.

### [Two-Phase Initialization](two-phase-initialization.md)
The framework uses a two-phase initialization pattern to handle complex module dependencies:
- **Phase 1**: Service registration and basic setup
- **Phase 2**: Complex initialization with full dependency access

### [Result Pattern](result-pattern.md)
All operations that can fail return Result objects for consistent error handling:
- Success and error states
- Structured error information
- Chainable operations
- Type-safe error handling

### [Service Registration](service-registration.md)
The framework uses a service container pattern for dependency management:
- Centralized service registry
- Dependency injection
- Service lifecycle management
- Loose coupling between modules

### [Database Patterns](database-patterns.md)
The framework provides multiple database patterns for different use cases:
- **Table-driven pattern**: Simple, automatic database creation
- **Manager pattern**: Complex, manual database operations
- **Hub pattern**: Multi-database coordination

## Pattern Categories

### **Architectural Patterns**
- **Modular Architecture**: Independent, reusable modules
- **Service Container**: Centralized dependency management
- **Plugin System**: Dynamic module loading and unloading

### **Error Handling Patterns**
- **Result Pattern**: Consistent error handling across modules
- **Error Codes**: Standardized error identification
- **Error Logging**: Centralized error tracking and reporting

### **Database Patterns**
- **Database Per Module**: Clean separation of concerns
- **Multi-Database Coordination**: Cross-database operations
- **Schema Management**: Automatic table creation and management

### **Configuration Patterns**
- **Environment-Based Config**: Environment variable support
- **Module Settings**: Per-module configuration management
- **Settings Validation**: Type checking and validation

### **Initialization Patterns**
- **Two-Phase Init**: Dependency-aware initialization
- **Post-Init Hooks**: Delayed initialization support
- **Graceful Shutdown**: Proper resource cleanup

## Pattern Implementation

### Basic Pattern Structure
```python
# Example of Result pattern implementation
from modules.core.error_handler.utils import Result

async def operation() -> Result:
    try:
        # Operation logic
        return Result.success(data=result)
    except Exception as e:
        return Result.error(
            code="OPERATION_FAILED",
            message="Operation description",
            details={"error": str(e)}
        )
```

### Service Registration Pattern
```python
# Example of service registration
def initialize(app_context):
    service = ModuleService(app_context)
    app_context.register_service("module.service", service)
    
    app_context.register_post_init_hook(
        "module.setup",
        service.initialize,
        dependencies=["core.database.setup"]
    )
```

### Database Pattern Selection
```python
# Table-driven pattern (simple)
DATABASE_NAME = "my_module"
Base = get_database_base(DATABASE_NAME)

class MyModel(Base):
    __tablename__ = "my_table"
    __table_args__ = {'extend_existing': True}
    # ... table definition

# Manager pattern (complex)
class DatabaseManager:
    def __init__(self, app_context):
        self.db_service = app_context.get_service("core.database.service")
    
    async def create_tables(self):
        # Manual database setup
        pass
```

## Pattern Guidelines

### When to Use Each Pattern

#### **Table-Driven Pattern**
- ✅ Simple database needs
- ✅ Standard CRUD operations
- ✅ Single database per module
- ❌ Complex cross-database operations

#### **Manager Pattern**
- ✅ Complex database operations
- ✅ Custom initialization logic
- ✅ Cross-database coordination
- ❌ Simple table operations

#### **Hub Pattern**
- ✅ Multi-database coordination
- ✅ Cross-module data operations
- ✅ Complex business logic
- ❌ Simple single-database modules

### Best Practices

1. **Always use Result pattern** for operations that can fail
2. **Follow two-phase initialization** for complex modules
3. **Register services early** in Phase 1
4. **Use dependency injection** instead of direct imports
5. **Implement proper error handling** with error codes
6. **Document all patterns** used in your module
7. **Test pattern implementations** thoroughly

### Anti-Patterns to Avoid

1. **Direct service access** - Use dependency injection
2. **Synchronous operations** - Framework is async-first
3. **Hardcoded paths** - Use path management utilities
4. **Manual database URLs** - Use framework database utilities
5. **Mixed initialization phases** - Keep Phase 1 simple
6. **Circular dependencies** - Design proper dependency graphs

## Pattern Evolution

The framework patterns have evolved through several iterations:

### Version 1.0 (Original)
- Basic module loading
- Simple database patterns
- Manual dependency management

### Version 2.0 (Current)
- Two-phase initialization
- Result pattern standardization
- Multi-database support
- Service container pattern

### Version 3.0 (Future)
- Advanced plugin system
- Dynamic module reconfiguration
- Enhanced error recovery
- Performance optimizations

## Related Documentation

- [Core Framework](../core/README.md) - Framework foundation
- [Core Modules](../modules/README.md) - Framework-provided modules
- [Module Creation Guide](../module-creation-guide-v2.md) - Creating new modules
- [Development Tools](../development-tools/README.md) - Tools and utilities

---

Understanding and following these patterns is essential for creating maintainable, scalable modules that integrate seamlessly with the framework.
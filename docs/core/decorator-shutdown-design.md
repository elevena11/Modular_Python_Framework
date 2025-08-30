# Decorator-Based Shutdown Architecture Design

**Status**: DESIGN PHASE  
**Principle**: Shutdown handling should follow the same declarative pattern as service registration  

## Architecture Philosophy

### **Current v3.0.0 Decorator Pattern**
```python
@register_service("core.database.service", priority=10)
@provides_api_endpoints(router_name="router", prefix="/db") 
@module_health_check(interval=300)
@enforce_data_integrity(strict_mode=True)
class DatabaseModule(DataIntegrityModule):
    # NO manual registration code - decorators handle everything
```

### **Proposed: Extend to Shutdown Handling**
```python
@register_service("core.database.service", priority=10)
@provides_api_endpoints(router_name="router", prefix="/db")
@graceful_shutdown(method="cleanup_resources", timeout=30, priority=10)
@force_shutdown(method="force_cleanup", timeout=5)  
@module_health_check(interval=300)
@enforce_data_integrity(strict_mode=True)
class DatabaseModule(DataIntegrityModule):
    
    # Only cleanup logic - no logging!
    async def cleanup_resources(self):
        """Called during graceful shutdown"""
        await self.close_connections()
        self.stop_background_tasks()
    
    def force_cleanup(self):
        """Called during force shutdown"""
        self.force_close_connections()
```

## Decorator Design

### **1. @graceful_shutdown Decorator**

```python
def graceful_shutdown(method: str = "shutdown", timeout: int = 30, 
                     priority: int = 100, dependencies: List[str] = None):
    """
    Register a method for graceful async shutdown.
    
    Args:
        method: Method name to call for cleanup (default: "shutdown")
        timeout: Max seconds to wait for shutdown (default: 30)  
        priority: Shutdown order priority (lower = earlier, default: 100)
        dependencies: Modules that must shutdown after this one
    
    Example:
        @graceful_shutdown(method="cleanup_resources", timeout=30, priority=10)
        class MyModule(DataIntegrityModule):
            async def cleanup_resources(self):
                # Only cleanup logic here - logging handled automatically
                await self.close_connections()
    """
```

### **2. @force_shutdown Decorator**

```python  
def force_shutdown(method: str = "force_shutdown", timeout: int = 5):
    """
    Register a method for force synchronous shutdown.
    
    Args:
        method: Method name to call for force cleanup (default: "force_shutdown")
        timeout: Max seconds to wait for force shutdown (default: 5)
    
    Example:
        @force_shutdown(method="force_cleanup", timeout=5)  
        class MyModule(DataIntegrityModule):
            def force_cleanup(self):
                # Only cleanup logic here - logging handled automatically
                self.force_close_connections()
    """
```

### **3. @shutdown_dependencies Decorator**

```python
def shutdown_dependencies(*depends_on: str):
    """
    Declare shutdown dependency order.
    
    Args:
        *depends_on: Module IDs that must shutdown AFTER this module
    
    Example:
        @shutdown_dependencies("standard.module1", "standard.module2")
        class CoreModule(DataIntegrityModule):
            # This module shuts down BEFORE module1 and module2
    """
```

## Implementation in Module Processor

### **Enhanced Metadata Storage**

```python
# In _ensure_module_metadata()
cls._decorator_metadata = {
    'services': [],
    'databases': [], 
    'models': [],
    'dependencies': [],
    'api_endpoints': [],
    'health_checks': [],
    
    # NEW: Shutdown configuration
    'shutdown': {
        'graceful': {
            'method': 'shutdown',
            'timeout': 30,
            'priority': 100,
            'dependencies': []
        },
        'force': {
            'method': 'force_shutdown', 
            'timeout': 5
        }
    },
    
    'data_integrity': {...}
}
```

### **Centralized Shutdown Execution**

```python
# In app_context.py
class ApplicationContext:
    
    async def run_shutdown_handlers(self) -> None:
        """Execute decorator-configured shutdown methods with automatic logging"""
        
        # Get all modules with shutdown decorators
        shutdown_modules = self._get_modules_with_shutdown_config()
        
        # Sort by priority and dependencies  
        ordered_modules = self._resolve_shutdown_order(shutdown_modules)
        
        # Execute graceful shutdown with centralized logging
        for module_info in ordered_modules:
            module_name = module_info['module_id']
            shutdown_config = module_info['shutdown']['graceful']
            method_name = shutdown_config['method']  
            timeout = shutdown_config['timeout']
            
            # CENTRALIZED LOGGING - no module duplication!
            self.logger.info(f"{module_name}: Shutting down service gracefully...")
            
            try:
                # Get the actual method from the module instance
                module_instance = self.services[f"{module_name}.service"]
                shutdown_method = getattr(module_instance, method_name)
                
                # Execute with timeout
                await asyncio.wait_for(shutdown_method(), timeout=timeout)
                
                # CENTRALIZED SUCCESS LOGGING
                self.logger.info(f"{module_name}: Service shutdown complete")
                
            except asyncio.TimeoutError:
                self.logger.error(f"{module_name}: Service shutdown timed out after {timeout}s")
            except Exception as e:
                self.logger.error(f"{module_name}: Service shutdown failed - {e}")
```

## Benefits of Decorator Approach

### **1. Consistency with v3.0.0 Architecture** 
- **Same declarative pattern** as service registration
- **Metadata-driven execution** via ModuleProcessor
- **Zero boilerplate code** in modules

### **2. Enhanced Features Beyond Centralized Logging**
- **Configurable timeouts** per module  
- **Priority-based shutdown ordering** (database shuts down last)
- **Dependency resolution** (ensure modules shut down in correct order)
- **Automatic timeout handling** with proper error logging

### **3. Developer Experience**
- **Declarative configuration**: `@graceful_shutdown(timeout=30, priority=10)`  
- **Method name flexibility**: `@graceful_shutdown(method="cleanup_resources")`
- **NO logging code needed**: Focus only on cleanup logic
- **Automatic registration**: Framework handles everything

### **4. Advanced Capabilities** 
- **Shutdown ordering**: Critical modules (database) shutdown after dependent modules
- **Timeout management**: Prevent hanging shutdowns
- **Failure isolation**: One module failure doesn't stop others
- **Metrics collection**: Centralized shutdown timing and success rates

## Migration Path

### **Phase 1: Add Decorators to Core Framework**
```python
# core/decorators.py - add new shutdown decorators
def graceful_shutdown(...)
def force_shutdown(...)
def shutdown_dependencies(...)
```

### **Phase 2: Enhance Module Processor**  
```python  
# core/module_processor.py - read shutdown metadata
# core/app_context.py - execute with centralized logging
```

### **Phase 3: Convert Modules**
```python
# OLD: Manual registration + logging
class DatabaseModule:
    def __init__(self):
        app_context.register_shutdown_handler(self.shutdown)
    
    async def shutdown(self):
        self.logger.info("Shutting down...")  # DUPLICATE!
        await self.cleanup()
        self.logger.info("Shutdown complete")  # DUPLICATE!

# NEW: Declarative + clean
@graceful_shutdown(method="cleanup", priority=10, timeout=30)
class DatabaseModule:
    async def cleanup(self):
        # Only cleanup logic - logging automatic!
        await self.close_connections()
```

## Result: Perfect Architectural Consistency

**All framework features use the same declarative pattern:**

```python
@register_service("module.service", priority=10)       # Service registration
@provides_api_endpoints(router_name="router")          # API endpoints  
@graceful_shutdown(method="cleanup", priority=10)      # Graceful shutdown
@force_shutdown(method="force_cleanup")                # Force shutdown
@module_health_check(interval=300)                     # Health monitoring
@enforce_data_integrity(strict_mode=True)              # Data integrity
class MyModule(DataIntegrityModule):
    # Only business logic - framework handles everything else!
```

This achieves the ultimate **centralized registration** architecture where shutdown handling is as declarative and centralized as every other framework feature.
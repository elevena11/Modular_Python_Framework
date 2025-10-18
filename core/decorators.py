"""
core/decorators.py
Centralized Decorator Infrastructure - Framework Registration System

This module provides the centralized decorator system that eliminates the
"many points of failure" problem in module registration. Instead of every
module duplicating registration logic, decorators provide a single point
of control where all module behavior is managed.

Key Philosophy:
- CENTRALIZED CONTROL: Change registration logic in one place, all modules get the change
- IMPOSSIBLE TO FORGET: Decorators make registration automatic, can't be skipped
- CONSISTENT IMPLEMENTATION: All modules use identical registration logic
- EASY ENHANCEMENT: Add new features (like data integrity validation) centrally
- ELIMINATE BOILERPLATE: No more duplicated initialize() functions

Usage:
    from core.decorators import register_service, register_database, requires_modules
    
    @register_service("my_module.service")
    @register_database("my_module")
    @requires_modules(["core.database", "core.settings"])
    class MyModule(DataIntegrityModule):
        MODULE_ID = "standard.my_module"
        
        # NO manual registration code needed - decorators handle everything!
        pass

Architecture:
- Decorators store metadata on module classes
- ModuleProcessor reads decorator metadata and executes registration
- Single centralized logic for all registration patterns
- Data integrity validation built into all decorators
"""

import logging
import inspect
import warnings
from typing import Dict, Any, List, Optional, Callable, Union, Set
from functools import wraps
from datetime import datetime
from dataclasses import dataclass

from core.logging import get_framework_logger

logger = get_framework_logger(__name__)

# ============================================================================
# SERVICE METHOD DISCOVERY SYSTEM
# ============================================================================

@dataclass
class ServiceParam:
    """Parameter definition for service methods."""
    name: str
    param_type: type
    required: bool = True
    default: Any = None
    description: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "type": self.param_type.__name__,
            "type_module": getattr(self.param_type, '__module__', 'builtins'),
            "required": self.required,
            "default": self.default,
            "description": self.description
        }

@dataclass 
class ServiceReturn:
    """Return type definition for service methods."""
    return_type: type
    description: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "type": self.return_type.__name__,
            "type_module": getattr(self.return_type, '__module__', 'builtins'),
            "description": self.description
        }

@dataclass
class ServiceExample:
    """Usage example for service methods."""
    call: str
    result: str
    description: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "call": self.call,
            "result": self.result,
            "description": self.description
        }

@dataclass
class ServiceMethod:
    """Complete method definition for services."""
    name: str
    description: str
    params: List[ServiceParam]
    returns: ServiceReturn
    examples: Optional[List[ServiceExample]] = None
    is_async: bool = True
    tags: Optional[List[str]] = None  # For categorization
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "description": self.description,
            "params": [param.to_dict() for param in self.params],
            "returns": self.returns.to_dict(),
            "examples": [example.to_dict() for example in (self.examples or [])],
            "is_async": self.is_async,
            "tags": self.tags or []
        }

# ============================================================================
# DECORATOR METADATA STORAGE
# ============================================================================

def _ensure_module_metadata(cls) -> Dict[str, Any]:
    """Ensure module class has metadata storage dictionary."""
    if not hasattr(cls, '_decorator_metadata'):
        cls._decorator_metadata = {
            'services': [],
            'service_methods': {},  # NEW: ServiceMethod definitions by method name
            'databases': [],
            'models': [],
            'dependencies': {
                'modules': [],  # Legacy list format for @requires_modules
                'injection': None,  # New format for @inject_dependencies
            },
            'api_endpoints': [],
            'settings': None,
            'health_checks': [],
            'post_init_hooks': [],
            'initialization': None,  # New format for @initialization_sequence
            'phase2': None,  # New format for @phase2_operations
            'service_creation': None,  # New format for @auto_service_creation
            'data_integrity': {
                'enforced': True,
                'anti_mock_protection': True,
                'hard_failure_mode': True
            },
            'decorator_applied_at': datetime.now().isoformat(),
            'decorator_source': []
        }
    return cls._decorator_metadata

def _add_decorator_source(cls, decorator_name: str, location: str = None) -> None:
    """Track which decorators were applied and where."""
    metadata = _ensure_module_metadata(cls)
    if not location:
        frame = inspect.currentframe().f_back.f_back  # Skip this function and decorator
        location = f"{frame.f_code.co_filename}:{frame.f_lineno}"
    
    metadata['decorator_source'].append({
        'decorator': decorator_name,
        'location': location,
        'timestamp': datetime.now().isoformat()
    })

# ============================================================================
# SERVICE REGISTRATION DECORATORS
# ============================================================================


def register_service(service_name: str, methods: List[ServiceMethod],
                    service_class: Optional[type] = None, priority: int = 100,
                    dependencies: Optional[List[str]] = None):
    """
    Register a service with required method documentation for discovery system.

    Required: Yes (all modules must include this decorator)

    This decorator enforces complete service documentation as infrastructure policy.
    All services must document their public methods for framework discoverability.

    Args:
        service_name: Name to register the service under (e.g., "my_module.service")
        methods: REQUIRED list of ServiceMethod objects documenting all public methods
        service_class: Optional service class (auto-detected from module if not provided)
        priority: Initialization priority (lower number = higher priority)
        dependencies: List of service names this service depends on

    Example:
        @register_service("my_module.service", methods=[
            ServiceMethod("initialize", "Initialize service", [], ServiceReturn(bool, "Success"))
        ], priority=100)
        class MyModule(DataIntegrityModule):
            MODULE_ID = "standard.my_module"
    """
    def decorator(cls):
        metadata = _ensure_module_metadata(cls)
        _add_decorator_source(cls, f"register_service({service_name})")
        
        # Validate and store service methods
        if not methods:
            raise ValueError(
                f"Service '{service_name}' must provide method documentation. "
                f"All services require methods parameter with ServiceMethod objects."
            )
        
        # Store method definitions by name for fast lookup
        for method in methods:
            metadata['service_methods'][method.name] = method
            
        # Data integrity validation for method definitions
        for method in methods:
            # Validate method names
            if not method.name.isidentifier():
                raise ValueError(
                    f"Method name '{method.name}' is not a valid Python identifier. "
                    f"Service method names must follow Python naming conventions."
                )
            
            # Validate parameter names
            for param in method.params:
                if not param.name.isidentifier():
                    raise ValueError(
                        f"Parameter name '{param.name}' in method '{method.name}' "
                        f"is not a valid Python identifier."
                    )
        
        logger.info(f"SERVICE DISCOVERY: Registered {len(methods)} service methods for {cls.__name__}")

        service_info = {
            'name': service_name,
            'class': service_class,  # Will be resolved during processing
            'priority': priority,
            'dependencies': dependencies or [],
            'registered_by': cls.__name__,
            'registration_time': datetime.now().isoformat()
        }
        
        metadata['services'].append(service_info)
        logger.debug(f"Decorator registered service '{service_name}' for {cls.__name__}")
        return cls
    
    return decorator

def register_multiple_services(**service_configs):
    """
    Register multiple services with a single decorator.
    
    Args:
        **service_configs: Dictionary of service_name -> config
        
    Example:
        @register_multiple_services(
            primary_service="my_module.service",
            cache_service={"name": "my_module.cache", "priority": 50}
        )
        class MyModule(DataIntegrityModule):
            pass
    """
    def decorator(cls):
        for service_name, config in service_configs.items():
            if isinstance(config, str):
                # Simple string name
                register_service(config)(cls)
            elif isinstance(config, dict):
                # Full configuration
                name = config.get('name', service_name)
                priority = config.get('priority', 100)
                deps = config.get('dependencies', None)
                register_service(name, None, priority, deps)(cls)
            else:
                raise ValueError(f"Invalid service config for {service_name}: {config}")
        
        return cls
    
    return decorator

# ============================================================================
# DATABASE REGISTRATION DECORATORS
# ============================================================================

def register_database(database_name: Optional[str] = None, auto_create: bool = True,
                     models: Optional[List[str]] = None):
    """
    Register a database requirement with automatic creation and validation.

    Required: Yes (all modules must include this decorator)

    Args:
        database_name: Name of the database to register, or None if module has no database
        auto_create: Whether to automatically create the database
        models: List of model names this database should contain

    Example:
        # Module with database:
        @register_database("my_module", models=["User", "Document"])
        class MyModule(DataIntegrityModule):
            pass

        # Module without database (mandatory decorator with None):
        @register_database(database_name=None)
        class MyModule(DataIntegrityModule):
            pass
    """
    def decorator(cls):
        metadata = _ensure_module_metadata(cls)
        _add_decorator_source(cls, f"register_database({database_name})")

        database_info = {
            'name': database_name,
            'auto_create': auto_create,
            'models': models or [],
            'registered_by': cls.__name__,
            'registration_time': datetime.now().isoformat()
        }
        
        metadata['databases'].append(database_info)
        logger.debug(f"Decorator registered database '{database_name}' for {cls.__name__}")
        return cls
    
    return decorator

def register_models(model_names: List[str], database: str = None):
    """
    Register database models for automatic discovery.
    
    Args:
        model_names: List of model class names
        database: Target database (auto-detected if not provided)
        
    Example:
        @register_models(["User", "Document", "Session"])
        class MyModule(DatabaseEnabledModule):
            pass
    """
    def decorator(cls):
        metadata = _ensure_module_metadata(cls)
        _add_decorator_source(cls, f"register_models({model_names})")
        
        model_info = {
            'names': model_names,
            'database': database,  # Will be resolved during processing
            'registered_by': cls.__name__,
            'registration_time': datetime.now().isoformat()
        }
        
        metadata['models'].append(model_info)
        logger.debug(f"Decorator registered models {model_names} for {cls.__name__}")
        return cls
    
    return decorator

# ============================================================================
# DEPENDENCY MANAGEMENT DECORATORS
# ============================================================================

def requires_modules(module_ids: List[str], optional: bool = False):
    """
    Declare module dependencies for automatic dependency resolution.
    
    Args:
        module_ids: List of required module IDs
        optional: Whether dependencies are optional (won't fail if missing)
        
    Example:
        @requires_modules(["core.database", "core.settings"])
        class MyModule(DataIntegrityModule):
            pass
    """
    def decorator(cls):
        metadata = _ensure_module_metadata(cls)
        _add_decorator_source(cls, f"requires_modules({module_ids})")

        dependency_info = {
            'modules': module_ids,
            'optional': optional,
            'registered_by': cls.__name__,
            'registration_time': datetime.now().isoformat()
        }
        
        metadata['dependencies']['modules'].append(dependency_info)
        logger.debug(f"Decorator registered dependencies {module_ids} for {cls.__name__}")
        return cls
    
    return decorator

def register_api_endpoints(router_name: str = "router"):
    """
    Register API endpoints for automatic route discovery with standardized paths.

    Required: Yes (all modules must include this decorator)

    API paths are automatically generated based on module ID:
    - Core modules: /api/v1/core/{module_name}
    - Standard modules: /api/v1/{module_name}

    Args:
        router_name: Name of the router variable in the module (router can be empty if no API endpoints)

    Example:
        # Module with API routes:
        @register_api_endpoints(router_name="router")
        class MyModule(DataIntegrityModule):
            pass

        # Module without API routes (mandatory decorator with empty router):
        @register_api_endpoints(router_name="router")
        class MyModule(DataIntegrityModule):
            # router = APIRouter() with no routes defined
            pass
    """
    def decorator(cls):
        metadata = _ensure_module_metadata(cls)
        _add_decorator_source(cls, f"register_api_endpoints({router_name})")
        
        endpoint_info = {
            'router_name': router_name,
            'registered_by': cls.__name__,
            'registration_time': datetime.now().isoformat()
        }
        
        metadata['api_endpoints'].append(endpoint_info)
        logger.debug(f"Decorator registered API endpoints for {cls.__name__}")
        return cls
    
    return decorator

# ============================================================================
# DATA INTEGRITY ENFORCEMENT DECORATORS
# ============================================================================

def enforce_data_integrity(strict_mode: bool = True, anti_mock: bool = True):
    """
    Enforce strict data integrity requirements on the module.

    Required: Yes (all modules must include this decorator)

    Args:
        strict_mode: Enable strict data integrity validation
        anti_mock: Enable anti-mock data protection

    Example:
        @enforce_data_integrity(strict_mode=True, anti_mock=True)
        class MyModule(DataIntegrityModule):
            pass
    """
    def decorator(cls):
        metadata = _ensure_module_metadata(cls)
        _add_decorator_source(cls, f"enforce_data_integrity(strict={strict_mode})")
        
        metadata['data_integrity'].update({
            'strict_mode': strict_mode,
            'anti_mock_protection': anti_mock,
            'enforced_by_decorator': True,
            'enforcement_time': datetime.now().isoformat()
        })
        
        logger.debug(f"Decorator enforced data integrity for {cls.__name__}")
        return cls
    
    return decorator

def no_mock_data(enforcement_level: str = "error"):
    """
    Explicitly forbid mock data in the module.
    
    Args:
        enforcement_level: "error", "warning", or "log"
        
    Example:
        @no_mock_data(enforcement_level="error")
        class MyModule(DataIntegrityModule):
            pass
    """
    def decorator(cls):
        metadata = _ensure_module_metadata(cls)
        _add_decorator_source(cls, f"no_mock_data({enforcement_level})")
        
        metadata['data_integrity']['no_mock_data'] = {
            'enabled': True,
            'enforcement_level': enforcement_level,
            'enforced_by_decorator': True
        }
        
        logger.debug(f"Decorator applied no_mock_data protection to {cls.__name__}")
        return cls
    
    return decorator

# ============================================================================
# MODULE HEALTH AND VALIDATION DECORATORS
# ============================================================================

def module_health_check(check_function: Callable = None, interval: int = 300):
    """
    Register a health check function for the module.

    Required: Yes (all modules must include this decorator)

    Args:
        check_function: Function to call for health checks, or None for default health check
        interval: Check interval in seconds

    Example:
        # Module with custom health check:
        @module_health_check(check_function="check_health", interval=60)
        class MyModule(DataIntegrityModule):
            async def check_health(self):
                # Custom health check logic
                return {"healthy": True, "checks": [...]}

        # Module with default health check (mandatory decorator with None):
        @module_health_check(check_function=None)
        class MyModule(DataIntegrityModule):
            # Uses default health check (returns module healthy if running)
            pass
    """
    def decorator(cls):
        metadata = _ensure_module_metadata(cls)
        _add_decorator_source(cls, f"module_health_check(interval={interval})")
        
        health_info = {
            'function': check_function,
            'interval': interval,
            'registered_by': cls.__name__,
            'registration_time': datetime.now().isoformat()
        }
        
        metadata['health_checks'].append(health_info)
        logger.debug(f"Decorator registered health check for {cls.__name__}")
        return cls
    
    return decorator

# ============================================================================
# BACKWARD COMPATIBILITY DECORATORS
# ============================================================================

def legacy_initialize_method(method_name: str = "initialize"):
    """
    DEPRECATED: Mark a module as using legacy initialization patterns.
    
    This decorator is for backward compatibility during migration.
    Will be REMOVED in Phase 4.
    
    Args:
        method_name: Name of the legacy initialization method
    """
    def decorator(cls):
        warnings.warn(
            f"@legacy_initialize_method is DEPRECATED and will be removed in Phase 4. "
            f"Module {cls.__name__} should migrate to decorator-based registration.",
            DeprecationWarning,
            stacklevel=2
        )
        
        metadata = _ensure_module_metadata(cls)
        _add_decorator_source(cls, f"legacy_initialize_method({method_name}) - DEPRECATED")
        
        metadata['legacy_patterns'] = {
            'initialize_method': method_name,
            'deprecated': True,
            'removal_phase': "Phase 4"
        }
        
        logger.warning(f"DEPRECATED: {cls.__name__} uses legacy initialization pattern")
        return cls
    
    return decorator

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def get_module_metadata(cls) -> Dict[str, Any]:
    """Get all decorator metadata for a module class."""
    return getattr(cls, '_decorator_metadata', {})

def has_decorator_metadata(cls) -> bool:
    """Check if a module class has decorator metadata."""
    return hasattr(cls, '_decorator_metadata')

def list_registered_services(cls) -> List[Dict[str, Any]]:
    """Get all services registered via decorators for a module."""
    metadata = get_module_metadata(cls)
    return metadata.get('services', [])

def list_required_databases(cls) -> List[Dict[str, Any]]:
    """Get all databases registered via decorators for a module."""
    metadata = get_module_metadata(cls)
    return metadata.get('databases', [])

def validate_decorator_integrity(cls) -> Dict[str, Any]:
    """
    Validate that decorator metadata meets basic integrity requirements.

    Returns:
        Dictionary with validation results and any violations found
    """
    metadata = get_module_metadata(cls)
    violations = []

    # Check data integrity enforcement
    data_integrity = metadata.get('data_integrity', {})
    if not data_integrity.get('enforced', True):
        violations.append("Data integrity enforcement is disabled")

    return {
        'valid': len(violations) == 0,
        'violations': violations,
        'data_integrity_enforced': data_integrity.get('enforced', True),
        'anti_mock_protection': data_integrity.get('anti_mock_protection', True)
    }

# ============================================================================
# SHUTDOWN MANAGEMENT DECORATORS
# ============================================================================

def graceful_shutdown(method: str = "cleanup_resources", timeout: int = 30,
                     priority: int = 100, dependencies: Optional[List[str]] = None):
    """
    Register a method for graceful async shutdown with centralized logging.

    Required: Yes (all modules must include this decorator)

    This decorator eliminates the need for manual shutdown logging in every
    service. The framework handles all logging automatically, and services
    focus only on their cleanup logic.

    Args:
        method: Method name to call for cleanup (default: "cleanup_resources")
        timeout: Max seconds to wait for shutdown (default: 30)
        priority: Shutdown order priority (lower = earlier, default: 100)
        dependencies: Modules that must shutdown after this one

    Example:
        @graceful_shutdown(method="cleanup_resources", timeout=30)
        class MyModule(DataIntegrityModule):
            async def cleanup_resources(self):
                # Only cleanup logic here - logging handled automatically
                # Add cleanup logic when needed (can be empty for modules with no resources)
                pass
    """
    def decorator(cls):
        metadata = _ensure_module_metadata(cls)
        _add_decorator_source(cls, f"graceful_shutdown({method}, timeout={timeout}, priority={priority})")

        shutdown_info = {
            'method': method,
            'timeout': timeout,
            'priority': priority,
            'dependencies': dependencies or [],
            'registered_by': cls.__name__,
            'registration_time': datetime.now().isoformat()
        }
        
        # Initialize shutdown metadata if not present
        if 'shutdown' not in metadata:
            metadata['shutdown'] = {}
        
        metadata['shutdown']['graceful'] = shutdown_info
        logger.debug(f"Decorator registered graceful shutdown method '{method}' for {cls.__name__}")
        return cls
    
    return decorator

def force_shutdown(method: str = "force_cleanup", timeout: int = 5):
    """
    Register a method for force synchronous shutdown with centralized logging.

    Required: Yes (all modules must include this decorator)

    This decorator handles force shutdown scenarios when graceful shutdown
    fails or times out. Framework provides all logging automatically.

    Args:
        method: Method name to call for force cleanup (default: "force_cleanup")
        timeout: Max seconds to wait for force shutdown (default: 5)

    Example:
        @force_shutdown(method="force_cleanup", timeout=5)
        class MyModule(DataIntegrityModule):
            def force_cleanup(self):
                # Only cleanup logic here - logging handled automatically
                # Add force cleanup logic when needed (can be empty for modules with no resources)
                pass
    """
    def decorator(cls):
        metadata = _ensure_module_metadata(cls)
        _add_decorator_source(cls, f"force_shutdown({method}, timeout={timeout})")

        force_shutdown_info = {
            'method': method,
            'timeout': timeout,
            'registered_by': cls.__name__,
            'registration_time': datetime.now().isoformat()
        }
        
        # Initialize shutdown metadata if not present
        if 'shutdown' not in metadata:
            metadata['shutdown'] = {}
        
        metadata['shutdown']['force'] = force_shutdown_info
        logger.debug(f"Decorator registered force shutdown method '{method}' for {cls.__name__}")
        return cls
    
    return decorator

def shutdown_dependencies(*depends_on: str):
    """
    Declare shutdown dependency order for proper service shutdown sequencing.
    
    Args:
        *depends_on: Module IDs that must shutdown AFTER this module
        
    Example:
        @shutdown_dependencies("standard.module1", "standard.module2")
        class CoreModule(DataIntegrityModule):
            # This module shuts down BEFORE module1 and module2
    """
    def decorator(cls):
        metadata = _ensure_module_metadata(cls)
        _add_decorator_source(cls, f"shutdown_dependencies({', '.join(depends_on)})")

        # Initialize shutdown metadata if not present
        if 'shutdown' not in metadata:
            metadata['shutdown'] = {}
        
        # Add dependencies to graceful shutdown config
        if 'graceful' not in metadata['shutdown']:
            metadata['shutdown']['graceful'] = {
                'method': 'shutdown',
                'timeout': 30,
                'priority': 100,
                'dependencies': [],
                'registered_by': cls.__name__,
                'registration_time': datetime.now().isoformat()
            }
        
        metadata['shutdown']['graceful']['dependencies'].extend(depends_on)
        logger.debug(f"Decorator registered shutdown dependencies {list(depends_on)} for {cls.__name__}")
        return cls
    
    return decorator

# ============================================================================  
# DEPENDENCY INJECTION AND INITIALIZATION DECORATORS
# ============================================================================

def inject_dependencies(*dependency_names: str, optional: List[str] = None):
    """
    Automatic dependency injection decorator.

    Required: Yes (all modules must include this decorator)

    Eliminates the fragile manual app_context passing pattern by automatically
    injecting services into the module constructor. The framework resolves
    dependencies and passes them to __init__().

    Args:
        dependency_names: Names of services to inject (typically at least "app_context")
        optional: List of dependency names that are optional (won't fail if missing)

    Example:
        @inject_dependencies("app_context", "database_service", optional=["settings_service"])
        @register_service("my_module.service")
        class MyModule(DataIntegrityModule):
            def __init__(self, app_context, database_service, settings_service=None):
                # Framework automatically provides these - no manual passing needed!
                self.app_context = app_context
                self.database_service = database_service
                self.settings_service = settings_service
    """
    def decorator(cls):
        _ensure_module_metadata(cls)
        metadata = get_module_metadata(cls)
        
        if 'dependencies' not in metadata:
            metadata['dependencies'] = {'modules': [], 'injection': None}
        elif isinstance(metadata['dependencies'], list):
            # Convert legacy list format to new dict format
            old_deps = metadata['dependencies']
            metadata['dependencies'] = {'modules': old_deps, 'injection': None}
            
        metadata['dependencies']['injection'] = {
            'required': list(dependency_names),
            'optional': optional or [],
            'registered_by': cls.__name__,
            'registration_time': datetime.now().isoformat()
        }
        
        logger.debug(f"Decorator registered dependency injection {list(dependency_names)} for {cls.__name__}")
        return cls
    
    return decorator

def initialization_sequence(*method_names: str, phase: str = "phase1"):
    """
    Automatic method calling sequence decorator.

    Required: Yes (all modules must include this decorator for Phase 1)

    Eliminates manual service.initialize() calls by automatically calling
    specified methods in order during module initialization.

    CRITICAL: All modules MUST use this for Phase 1 with "setup_infrastructure"
    method to register Pydantic settings models.

    Args:
        method_names: Names of methods to call in order (e.g., "setup_infrastructure", "load_config")
        phase: When to call methods ("phase1" or "phase2")

    Example:
        @initialization_sequence("setup_infrastructure", phase="phase1")
        @register_service("my_module.service")
        class MyModule(DataIntegrityModule):
            def setup_infrastructure(self):
                # MANDATORY: Framework calls this automatically in Phase 1
                # Register Pydantic settings model here
                from .settings import MyModuleSettings
                self.app_context.register_pydantic_model(self.MODULE_ID, MyModuleSettings)
    """
    def decorator(cls):
        _ensure_module_metadata(cls)
        metadata = get_module_metadata(cls)
        
        if 'initialization' not in metadata or metadata['initialization'] is None:
            metadata['initialization'] = {'phase1': [], 'phase2': []}
            
        metadata['initialization'][phase].extend([{
            'method': method_name,
            'registered_by': cls.__name__,
            'registration_time': datetime.now().isoformat()
        } for method_name in method_names])
        
        logger.debug(f"Decorator registered {phase} initialization sequence {list(method_names)} for {cls.__name__}")
        return cls
    
    return decorator

def phase2_operations(*method_names: str, dependencies: List[str] = None, priority: int = 100):
    """
    Phase 2 operations automation decorator.

    Required: Yes (all modules must include this decorator)

    Eliminates manual post-init hook registration by automatically scheduling
    methods to run in Phase 2 with proper dependencies and priority.

    Args:
        method_names: Names of methods to call during Phase 2 (use "initialize_phase2" as standard)
        dependencies: List of other modules/services this depends on
        priority: Priority for Phase 2 execution (higher number = later)

    Example:
        @phase2_operations("initialize_phase2", priority=100)
        @register_service("my_module.service")
        class MyModule(DataIntegrityModule):
            async def initialize_phase2(self):
                # Framework calls this automatically in Phase 2
                # All services are available here - can access other services
                settings_service = self.app_context.get_service("core.settings.service")
                return True
    """
    def decorator(cls):
        _ensure_module_metadata(cls)
        metadata = get_module_metadata(cls)
        
        if 'phase2' not in metadata or metadata['phase2'] is None:
            metadata['phase2'] = {}
            
        metadata['phase2']['operations'] = {
            'methods': list(method_names),
            'dependencies': dependencies or [],
            'priority': priority,
            'registered_by': cls.__name__,
            'registration_time': datetime.now().isoformat()
        }
        
        logger.debug(f"Decorator registered Phase 2 operations {list(method_names)} for {cls.__name__}")
        return cls
    
    return decorator

def auto_service_creation(service_class: str = None, constructor_args: Dict[str, Any] = None):
    """
    Automatic service instance creation decorator.

    Required: Yes (all modules must include this decorator)

    Eliminates manual service instance creation by automatically creating
    service instances with injected dependencies.

    Args:
        service_class: Name of service class to create (e.g., "MyModuleService")
        constructor_args: Additional arguments for service constructor

    Example:
        @auto_service_creation(service_class="MyModuleService")
        @inject_dependencies("app_context")
        @register_service("my_module.service")
        class MyModule(DataIntegrityModule):
            # Framework automatically creates MyModuleService(app_context)
            # No manual service_instance = MyModuleService() needed!
            pass
    """
    def decorator(cls):
        _ensure_module_metadata(cls)
        metadata = get_module_metadata(cls)
        
        if 'service_creation' not in metadata or metadata['service_creation'] is None:
            metadata['service_creation'] = {}
            
        metadata['service_creation']['auto'] = {
            'service_class': service_class,
            'constructor_args': constructor_args or {},
            'registered_by': cls.__name__,
            'registration_time': datetime.now().isoformat()
        }
        
        logger.debug(f"Decorator registered automatic service creation for {cls.__name__}")
        return cls
    
    return decorator

# ============================================================================
# SHUTDOWN UTILITY FUNCTIONS
# ============================================================================

def get_shutdown_metadata(cls) -> Dict[str, Any]:
    """Get shutdown configuration metadata for a module class."""
    metadata = get_module_metadata(cls)
    return metadata.get('shutdown', {})

def has_graceful_shutdown(cls) -> bool:
    """Check if a module class has graceful shutdown configured."""
    shutdown_metadata = get_shutdown_metadata(cls)
    return 'graceful' in shutdown_metadata

def has_force_shutdown(cls) -> bool:
    """Check if a module class has force shutdown configured."""
    shutdown_metadata = get_shutdown_metadata(cls)
    return 'force' in shutdown_metadata

def list_shutdown_modules(module_classes: List[type]) -> List[Dict[str, Any]]:
    """
    Get all modules with shutdown configuration, sorted by priority.
    
    Args:
        module_classes: List of module classes to check
        
    Returns:
        List of modules with shutdown metadata, sorted by shutdown priority
    """
    shutdown_modules = []
    
    for cls in module_classes:
        if has_graceful_shutdown(cls):
            module_id = getattr(cls, 'MODULE_ID', cls.__name__)
            shutdown_config = get_shutdown_metadata(cls)
            
            shutdown_modules.append({
                'module_id': module_id,
                'class': cls,
                'shutdown': shutdown_config
            })
    
    # Sort by priority (lower number = higher priority = shutdown earlier)
    shutdown_modules.sort(key=lambda x: x['shutdown']['graceful'].get('priority', 100))
    
    return shutdown_modules

# ============================================================================
# INTER-MODULE SERVICE COMMUNICATION
# ============================================================================

def require_services(service_names: List[str]):
    """
    Declare required services from other modules for inter-module communication.

    Required: Yes (all modules must include this decorator)

    This decorator enables the new inter-module service communication pattern:

    Usage:
        # Module with service dependencies:
        @require_services(["core.database.service", "core.error_handler.service"])
        @phase2_operations("initialize_with_dependencies")
        class MyModule(DataIntegrityModule):
            def initialize_with_dependencies(self):
                # Services guaranteed to be available here
                self.database_service = self.get_required_service("core.database.service")
                self.error_service = self.get_required_service("core.error_handler.service")

        # Module without service dependencies (mandatory decorator with empty list):
        @require_services([])
        class MyModule(DataIntegrityModule):
            pass

    Args:
        service_names: List of service IDs that this module requires (use empty list [] if no dependencies)

    Key Benefits:
        - Explicit dependency declaration
        - Guaranteed service availability in phase2_operations
        - Clear service access pattern
        - LLM-friendly readable code

    Implementation:
        - Stores required service names in decorator metadata
        - Framework ensures services are available before phase2_operations
        - Provides get_required_service() method for clean service access
    """
    def decorator(cls):
        metadata = _ensure_module_metadata(cls)
        _add_decorator_source(cls, f"require_services({service_names})")
        
        # Store required services in metadata
        metadata['required_services'] = service_names
        
        # Add get_required_service method to the class
        def get_required_service(self, service_name: str):
            """Get a required service that was declared via @require_services decorator."""
            if service_name not in service_names:
                raise ValueError(f"Service '{service_name}' not declared in @require_services. "
                               f"Declared services: {service_names}")
            
            service = self.app_context.get_service(service_name)
            if not service:
                raise RuntimeError(f"Required service '{service_name}' not available. "
                                 f"This should not happen if @require_services is used correctly.")
            
            return service
        
        # Add method to class
        cls.get_required_service = get_required_service
        
        logger.debug(f"Module {getattr(cls, 'MODULE_ID', 'Unknown')} requires services: {service_names}")
        return cls
    
    return decorator

# ============================================================================
# MODULE EXPORTS
# ============================================================================

__all__ = [
    # Service method discovery system
    'ServiceParam',
    'ServiceReturn', 
    'ServiceExample',
    'ServiceMethod',
    
    # Service registration
    'register_service',
    'register_multiple_services',
    
    # Database registration
    'register_database', 
    'register_models',
    
    # Dependencies
    'requires_modules',
    'require_services',
    'provides_api_endpoints',
    
    # Data integrity
    'enforce_data_integrity',
    'no_mock_data',
    
    # Health and validation
    'module_health_check',
    
    # Shutdown management
    'graceful_shutdown',
    'force_shutdown', 
    'shutdown_dependencies',
    
    # Complete decorator system (eliminates fragile manual patterns)
    'inject_dependencies',
    'initialization_sequence', 
    'phase2_operations',
    'auto_service_creation',
    
    # Utilities
    'get_module_metadata',
    'has_decorator_metadata',
    'list_registered_services',
    'list_required_databases',
    'validate_decorator_integrity',
    'get_shutdown_metadata',
    'has_graceful_shutdown',
    'has_force_shutdown',
    'list_shutdown_modules',
    
    # Backward compatibility (Phase 4 removal)
    'legacy_initialize_method',
]

# Log module initialization
logger.info("Centralized decorator infrastructure initialized - Module registration system active")
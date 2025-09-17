"""
core/module_manager.py
FULL Decorator Module Management System

Enforces DATA_INTEGRITY_REQUIREMENTS.md - NO mixed patterns allowed.
Only FULL decorator architecture is supported.

Required Patterns:
- @inject_dependencies('app_context') - Mandatory dependency injection
- @register_service() - Service registration
- @phase2_operations() - Phase 2 initialization
- Complete decorator stack from docs/v2/

HARD FAILURE for modules not using FULL decorator patterns.
"""

import os
import sys
import logging
import importlib
import inspect
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from pathlib import Path

from core.module_processor import ModuleProcessor
from core.decorators import get_module_metadata
from core.error_utils import error_message


@dataclass
class ModuleInfo:
    """Simple module information."""
    id: str
    name: str
    path: str
    class_obj: type
    service_name: Optional[str] = None
    dependencies: List[str] = None
    phase2_method: Optional[str] = None
    priority: int = 100
    phase2_priority: int = 100

    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []


class ModuleManager:
    """Simple, clean module management system."""
    
    def __init__(self, app_context):
        self.app_context = app_context
        self.logger = logging.getLogger("core.module_manager")
        self.modules: Dict[str, ModuleInfo] = {}
        self.instances: Dict[str, Any] = {}
        self.processor = ModuleProcessor(app_context)
        
    async def discover_modules(self) -> List[ModuleInfo]:
        """Discover modules in the framework with visibility into failures."""
        modules = []
        expected_modules = []
        discovered_modules = []
        
        # Scan standard module directories
        for module_type in ["core", "standard", "extensions"]:
            modules_dir = Path("modules") / module_type
            if not modules_dir.exists():
                continue
                
            for module_path in modules_dir.iterdir():
                if not module_path.is_dir():
                    continue
                
                # Check if this should be an active module
                api_file = module_path / "api.py"
                if api_file.exists():
                    module_id = f"{module_type}.{module_path.name}"
                    
                    # Skip disabled modules
                    if (module_path / ".disabled").exists():
                        self.logger.info(f"{module_path.name}: Module disabled, skipping")
                        continue
                    
                    # This module is expected to load
                    expected_modules.append(module_id)
                    
                    # Attempt to discover it
                    module_info = await self._extract_module_info(module_path, module_type)
                    if module_info:
                        modules.append(module_info)
                        discovered_modules.append(module_id)
                        self.logger.info(f"{module_info.id}: Module discovered")
        
        # Report modules that failed to load (expected but not discovered)
        failed_modules = set(expected_modules) - set(discovered_modules)
        if failed_modules:
            self.logger.error(error_message(
                module_id="core.module_manager",
                error_type="MODULE_DISCOVERY_FAILED",
                details=f"Failed to load {len(failed_modules)} modules: {sorted(failed_modules)}",
                location="discover_modules()",
                context={"failed_modules": failed_modules, "total_failed": len(failed_modules)}
            ))
            self.logger.error(error_message(
                module_id="core.module_manager",
                error_type="MODULE_DISCOVERY_GUIDANCE",
                details="These modules have api.py files but failed during discovery - check for import errors, decorator issues, or class instantiation problems",
                location="discover_modules()",
                context={"failed_modules": failed_modules}
            ))
        else:
            self.logger.info(f"All {len(expected_modules)} expected modules discovered successfully")
        
        return modules
    
    async def _extract_module_info(self, module_path: Path, module_type: str) -> Optional[ModuleInfo]:
        """Extract module information from api.py."""
        try:
            # Build import path: modules.core.database -> modules.core.database.api
            # Use simple path construction instead of relative_to
            import_path = f"modules.{module_type}.{module_path.name}"
            
            # Import the module
            try:
                module_obj = importlib.import_module(f"{import_path}.api")
            except Exception as e:
                self.logger.error(error_message(
                    module_id="core.module_manager",
                    error_type="MODULE_IMPORT_FAILED",
                    details=f"Module import failed: {str(e)}",
                    location="_try_load_module()",
                    context={"import_path": import_path, "exception_type": type(e).__name__}
                ))
                # Log more detail for common issues
                if "methods" in str(e) and "ServiceMethod" in str(e):
                    self.logger.error(error_message(
                        module_id="core.module_manager",
                        error_type="MODULE_OLD_DECORATOR_PATTERN",
                        details="This module likely uses old @register_service pattern - missing 'methods' parameter",
                        location="_try_load_module()",
                        context={"import_path": import_path}
                    ))
                return None
            
            # Find module class with required attributes
            module_class = None
            for attr_name in dir(module_obj):
                attr = getattr(module_obj, attr_name)
                if (inspect.isclass(attr) and 
                    hasattr(attr, 'MODULE_ID') and 
                    hasattr(attr, '_decorator_metadata')):
                    module_class = attr
                    break
            
            if not module_class:
                self.logger.debug(f"{import_path}: No module class found")
                return None
            
            # Extract metadata
            decorator_meta = getattr(module_class, '_decorator_metadata', {})
            module_id = getattr(module_class, 'MODULE_ID')
            
            # Extract service info from decorator metadata
            services = decorator_meta.get('services', [])
            service_name = services[0]['name'] if services else None
            priority = services[0].get('priority', 100) if services else 100
            
            # Extract Phase 2 method, priority, and dependencies
            phase2_info = decorator_meta.get('phase2', {})
            phase2_method = None
            phase2_priority = 100  # Default Phase 2 priority
            phase2_dependencies = []  # Phase 2 dependencies
            
            if phase2_info and 'operations' in phase2_info:
                operations = phase2_info['operations']
                if 'methods' in operations:
                    phase2_methods = operations['methods']
                    phase2_method = phase2_methods[0] if phase2_methods else None
                # Extract Phase 2 priority
                phase2_priority = operations.get('priority', 100)
                # Extract Phase 2 dependencies 
                phase2_dependencies = operations.get('dependencies', [])
            
            # Use Phase 2 dependencies for dependency resolution
            dependencies = phase2_dependencies
            
            return ModuleInfo(
                id=module_id,
                name=module_path.name,
                path=str(module_path),
                class_obj=module_class,
                service_name=service_name,
                dependencies=dependencies,
                phase2_method=phase2_method,
                priority=priority,
                phase2_priority=phase2_priority
            )
            
        except Exception as e:
            self.logger.error(error_message(
                module_id="core.module_manager",
                error_type="MODULE_INFO_EXTRACTION_FAILED",
                details=f"Module info extraction failed: {str(e)}",
                location="_extract_module_info()",
                context={"module_path": module_path, "exception_type": type(e).__name__}
            ))
            return None
    
    async def load_modules(self, modules: List[ModuleInfo]):
        """Load modules in two phases."""
        self.logger.info("Starting module loading")
        
        # Phase 1: Pure registration only - order doesn't matter
        self.logger.info("Phase 1: Processing modules with decorator system (registration only)")
        for module_info in modules:
            try:
                # Use ModuleProcessor for complete decorator automation
                result = await self.processor.process_module(module_info.class_obj, module_info.id)
                if not result.success:
                    self.logger.error(error_message(
                        module_id="core.module_manager",
                        error_type="MODULE_PROCESSING_FAILED",
                        details=f"Module processing failed: {result.error}",
                        location="process_phase1()",
                        context={"target_module_id": module_info.id, "result_error": result.error}
                    ))
                    continue
                
                # FULL decorator pattern ONLY: Constructor gets app_context via @inject_dependencies
                # If module doesn't use @inject_dependencies, this will fail naturally
                instance = module_info.class_obj()
                self.instances[module_info.id] = instance
                
                # Create service instances based on @auto_service_creation decorator
                service_creation_result = await self.processor.create_auto_services_with_instance(module_info.id, instance)
                if service_creation_result.success:
                    self.logger.info(f"{module_info.id}: Auto services created")
                
                # Execute Phase 1 initialization sequence methods
                phase1_result = await self.processor.execute_phase1_methods(module_info.id, instance)
                if phase1_result.success:
                    self.logger.info(f"{module_info.id}: Phase 1 methods executed")
                
                # NOTE: Service registration handled automatically by decorators
                # No need for post-instance service registration - @register_service does this
                self.logger.debug(f"{module_info.id}: Service registration handled by decorators")
                
                self.modules[module_info.id] = module_info
                self.logger.info(f"{module_info.id}: Phase 1 complete")
                
            except Exception as e:
                self.logger.error(error_message(
                    module_id="core.module_manager",
                    error_type="MODULE_PHASE1_FAILED",
                    details=f"Phase 1 processing failed: {str(e)}",
                    location="process_phase1()",
                    context={"target_module_id": module_info.id, "exception_type": type(e).__name__}
                ))
                continue
        
        # Phase 2: Initialize in Phase 2 priority order and dependency order
        self.logger.info("Phase 2: Running initialization methods")
        initialized = set()
        
        def can_initialize(module_info: ModuleInfo) -> bool:
            """Check if all dependencies are initialized."""
            for dep in module_info.dependencies:
                if dep not in initialized:
                    return False
            return True
        
        # Use only successfully loaded modules from Phase 1
        successfully_loaded_modules = list(self.modules.values())
        
        # Sort by Phase 2 priority for Phase 2 execution (lower numbers = higher priority)
        phase2_sorted_modules = sorted(successfully_loaded_modules, key=lambda m: m.phase2_priority)
        remaining = list(phase2_sorted_modules)
        while remaining:
            progress = False
            for module_info in remaining[:]:  # Copy list to modify during iteration
                if can_initialize(module_info):
                    await self._run_phase2(module_info)
                    # Add both module ID and phase2_auto hook name to initialized set
                    initialized.add(module_info.service_name or module_info.id)
                    initialized.add(f"{module_info.id}.phase2_auto")  # This is what dependencies reference
                    remaining.remove(module_info)
                    progress = True
            
            if not progress and remaining:
                self.logger.error(error_message(
                    module_id="core.module_manager",
                    error_type="CIRCULAR_DEPENDENCY_DETECTED",
                    details="Circular dependency detected in modules",
                    location="process_phase2()",
                    context={"remaining_modules": [m.id for m in remaining], "dependency_count": len(remaining)}
                ))
                break
        
        self.logger.info(f"Module loading complete: {len(initialized)} modules initialized")
    
    async def _run_phase2(self, module_info: ModuleInfo):
        """Run Phase 2 initialization for a module."""
        if not module_info.phase2_method:
            return True
            
        try:
            instance = self.instances[module_info.id]
            method = getattr(instance, module_info.phase2_method)
            
            if inspect.iscoroutinefunction(method):
                result = await method()
            else:
                result = method()
                
            self.logger.info(f"{module_info.id}: Phase 2 complete")
            return result
            
        except Exception as e:
            self.logger.error(error_message(
                module_id="core.module_manager",
                error_type="MODULE_PHASE2_FAILED",
                details=f"Phase 2 processing failed: {str(e)}",
                location="process_phase2()",
                context={"target_module_id": module_info.id, "exception_type": type(e).__name__}
            ))
            return False
    
    # ============================================================================
    # SERVICE METHOD DISCOVERY SYSTEM
    # ============================================================================
    
    def get_available_services(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all registered services with their metadata.
        
        Returns:
            Dictionary mapping service names to service information including methods
        """
        services = {}
        
        for module_id, instance in self.instances.items():
            module_class = instance.__class__
            metadata = getattr(module_class, '_decorator_metadata', {})
            
            # Get service registrations for this module
            for service_info in metadata.get('services', []):
                service_name = service_info['name']
                services[service_name] = {
                    "module_id": module_id,
                    "class_name": module_class.__name__,
                    "priority": service_info.get('priority', 100),
                    "dependencies": service_info.get('dependencies', []),
                    "methods": self.get_service_methods(service_name),
                    "description": getattr(module_class, '__doc__', '').strip() if hasattr(module_class, '__doc__') else ""
                }
        
        return services
    
    def get_service_methods(self, service_name: str) -> Dict[str, Dict[str, Any]]:
        """
        Get detailed method information for a service.
        
        Args:
            service_name: Name of the service to get methods for
            
        Returns:
            Dictionary mapping method names to method information
        """
        # Find the module instance that provides this service
        for module_id, instance in self.instances.items():
            module_class = instance.__class__
            metadata = getattr(module_class, '_decorator_metadata', {})
            
            # Check if this module provides the requested service
            for service_info in metadata.get('services', []):
                if service_info['name'] == service_name:
                    # Return the service methods for this module
                    service_methods = metadata.get('service_methods', {})
                    return {
                        method_name: method.to_dict()
                        for method_name, method in service_methods.items()
                    }
        
        return {}
    
    def get_service_usage_examples(self, service_name: str) -> List[Dict[str, Any]]:
        """
        Get comprehensive usage examples for a service.
        
        Args:
            service_name: Name of the service to get examples for
            
        Returns:
            List of usage examples with full context
        """
        methods = self.get_service_methods(service_name)
        examples = []
        
        for method_name, method_info in methods.items():
            for example in method_info.get("examples", []):
                examples.append({
                    "service": service_name,
                    "method": method_name,
                    "call": example["call"],
                    "result": example["result"],
                    "description": example.get("description", ""),
                    "full_example": f'service = app_context.get_service("{service_name}")\nresult = await service.{example["call"]}'
                })
        
        return examples
    
    def generate_service_documentation(self, service_name: str) -> str:
        """
        Generate comprehensive documentation for a service.
        
        Args:
            service_name: Name of the service to document
            
        Returns:
            Markdown documentation string
        """
        services = self.get_available_services()
        service_info = services.get(service_name)
        
        if not service_info:
            return f"Service '{service_name}' not found."
            
        doc = f"# {service_name}\n\n"
        doc += f"**Module**: {service_info['module_id']}\n"
        doc += f"**Class**: {service_info['class_name']}\n"
        doc += f"**Priority**: {service_info['priority']}\n"
        
        if service_info['dependencies']:
            doc += f"**Dependencies**: {', '.join(service_info['dependencies'])}\n"
            
        doc += f"\n{service_info.get('description', 'No description available.')}\n\n"
        
        methods = service_info.get('methods', {})
        if methods:
            doc += "## Methods\n\n"
            for method_name, method_info in methods.items():
                doc += f"### {method_name}()\n\n"
                doc += f"{method_info.get('description', 'No description available.')}\n\n"
                
                params = method_info.get('params', [])
                if params:
                    doc += "**Parameters:**\n"
                    for param in params:
                        required = "required" if param.get('required', True) else "optional"
                        doc += f"- `{param['name']}` ({param['type']}, {required}): {param.get('description', 'No description')}\n"
                
                returns = method_info.get('returns', {})
                if returns:
                    doc += f"\n**Returns:** {returns.get('type', 'Unknown')} - {returns.get('description', 'No description')}\n\n"
                
                examples = method_info.get('examples', [])
                if examples:
                    doc += "**Examples:**\n"
                    for example in examples:
                        doc += f"```python\n{example.get('call', '')}\n# Result: {example.get('result', '')}\n```\n\n"
        else:
            doc += "## Methods\n\nNo documented methods available. Use @service_methods decorator to add method documentation.\n\n"
        
        return doc
    
    def find_services_by_capability(self, capability: str) -> List[Dict[str, Any]]:
        """
        Find services that provide specific capabilities.
        
        Args:
            capability: Capability to search for (searches descriptions and method names)
            
        Returns:
            List of matching services with match information
        """
        services = self.get_available_services()
        matches = []
        
        for service_name, service_info in services.items():
            # Search in service description
            description = service_info.get('description', '').lower()
            if capability.lower() in description:
                matches.append({
                    "service": service_name,
                    "match_type": "description",
                    "match_text": description,
                    **service_info
                })
            
            # Search in method names and descriptions
            for method_name, method_info in service_info.get('methods', {}).items():
                method_desc = method_info.get('description', '').lower()
                if (capability.lower() in method_name.lower() or 
                    capability.lower() in method_desc):
                    matches.append({
                        "service": service_name, 
                        "method": method_name,
                        "match_type": "method",
                        "match_text": f"{method_name}: {method_desc}",
                        **service_info
                    })
        
        return matches


# Export the complete decorator system from core.decorators
from core.decorators import (
    # Service method discovery system
    ServiceParam,
    ServiceReturn,
    ServiceExample,
    ServiceMethod,
    
    # Service registration
    register_service,
    register_multiple_services,
    register_database,
    register_models,
    requires_modules,
    register_api_endpoints,
    enforce_data_integrity,
    module_health_check,
    inject_dependencies,
    initialization_sequence,
    phase2_operations,
    auto_service_creation,
    graceful_shutdown,
    force_shutdown
)
# Service Method Discovery System Design

## Overview

Design for enhancing the `@register_service` decorator system to provide automatic method signature discovery and documentation, making the framework significantly more LLM-friendly for module creation.

## Current vs Enhanced Pattern

### Current Pattern
```python
@register_service("my_module.service", priority=100)
class MyModule:
    async def process_data(self, data: Dict[str, Any], options: Optional[ProcessingOptions] = None):
        pass

# Usage requires manual knowledge:
service = app_context.get_service("my_module.service")
result = await service.process_data(data={"key": "value"})
```

### Enhanced Pattern  
```python
@register_service("my_module.service", priority=100)
@service_methods([
    ServiceMethod(
        name="process_data",
        description="Process input data with optional configuration",
        params=[
            ServiceParam("data", Dict[str, Any], required=True, 
                        description="Input data dictionary to process"),
            ServiceParam("options", ProcessingOptions, required=False,
                        description="Optional processing configuration")
        ],
        returns=ServiceReturn(ProcessingResult, "Processing result with status and output"),
        examples=[
            ServiceExample(
                call="process_data(data={'text': 'hello'}, options=ProcessingOptions(validate=True))",
                result="ProcessingResult(status='success', output={'processed': 'hello'})"
            )
        ]
    )
])
class MyModule:
    async def process_data(self, data: Dict[str, Any], options: Optional[ProcessingOptions] = None):
        pass
```

## Core Components

### 1. Enhanced Decorator System

```python
# In core/decorators.py

@dataclass
class ServiceParam:
    """Parameter definition for service methods."""
    name: str
    param_type: type
    required: bool = True
    default: Any = None
    description: str = ""
    
@dataclass 
class ServiceReturn:
    """Return type definition for service methods."""
    return_type: type
    description: str = ""
    
@dataclass
class ServiceExample:
    """Usage example for service methods."""
    call: str
    result: str
    description: str = ""
    
@dataclass
class ServiceMethod:
    """Complete method definition for services."""
    name: str
    description: str
    params: List[ServiceParam]
    returns: ServiceReturn
    examples: List[ServiceExample] = None
    is_async: bool = True
    tags: List[str] = None  # For categorization

def service_methods(methods: List[ServiceMethod]):
    """Decorator to register method signatures for a service."""
    def decorator(cls):
        metadata = _ensure_module_metadata(cls)
        metadata['service_methods'] = {method.name: method for method in methods}
        return cls
    return decorator
```

### 2. Module Manager Discovery API

```python
# In core/module_manager.py

class ModuleManager:
    def get_available_services(self) -> Dict[str, Dict[str, Any]]:
        """Get all registered services with their metadata."""
        return {
            service_name: {
                "module_id": service_info.get("module_id"),
                "class_name": service_info.get("class_name"), 
                "priority": service_info.get("priority"),
                "dependencies": service_info.get("dependencies", []),
                "methods": self.get_service_methods(service_name),
                "description": service_info.get("description", "")
            }
            for service_name, service_info in self.registered_services.items()
        }
    
    def get_service_methods(self, service_name: str) -> Dict[str, Dict[str, Any]]:
        """Get detailed method information for a service."""
        service_info = self.registered_services.get(service_name)
        if not service_info:
            return {}
            
        methods = service_info.get("service_methods", {})
        return {
            method_name: {
                "name": method.name,
                "description": method.description,
                "params": [
                    {
                        "name": param.name,
                        "type": param.param_type.__name__,
                        "type_module": param.param_type.__module__,
                        "required": param.required,
                        "default": param.default,
                        "description": param.description
                    }
                    for param in method.params
                ],
                "returns": {
                    "type": method.returns.return_type.__name__,
                    "type_module": method.returns.return_type.__module__,
                    "description": method.returns.description
                },
                "examples": [
                    {
                        "call": example.call,
                        "result": example.result,
                        "description": example.description
                    }
                    for example in (method.examples or [])
                ],
                "is_async": method.is_async,
                "tags": method.tags or []
            }
            for method_name, method in methods.items()
        }
    
    def get_service_usage_examples(self, service_name: str) -> List[Dict[str, Any]]:
        """Get comprehensive usage examples for a service."""
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
        """Generate comprehensive documentation for a service."""
        service_info = self.get_available_services().get(service_name)
        if not service_info:
            return f"Service '{service_name}' not found."
            
        doc = f"# {service_name}\n\n"
        doc += f"**Module**: {service_info['module_id']}\n"
        doc += f"**Priority**: {service_info['priority']}\n"
        
        if service_info['dependencies']:
            doc += f"**Dependencies**: {', '.join(service_info['dependencies'])}\n"
            
        doc += f"\n{service_info.get('description', 'No description available.')}\n\n"
        
        doc += "## Methods\n\n"
        for method_name, method_info in service_info['methods'].items():
            doc += f"### {method_name}()\n\n"
            doc += f"{method_info['description']}\n\n"
            
            doc += "**Parameters:**\n"
            for param in method_info['params']:
                required = "required" if param['required'] else "optional"
                doc += f"- `{param['name']}` ({param['type']}, {required}): {param['description']}\n"
            
            doc += f"\n**Returns:** {method_info['returns']['type']} - {method_info['returns']['description']}\n\n"
            
            if method_info['examples']:
                doc += "**Examples:**\n"
                for example in method_info['examples']:
                    doc += f"```python\n{example['call']}\n# {example['result']}\n```\n\n"
        
        return doc
```

### 3. LLM Integration API

```python
# In core/llm_interface.py (new file)

class LLMServiceInterface:
    """Interface designed specifically for LLM consumption."""
    
    def __init__(self, module_manager: ModuleManager):
        self.module_manager = module_manager
    
    def get_service_catalog(self) -> Dict[str, Any]:
        """Get complete service catalog in LLM-friendly format."""
        services = self.module_manager.get_available_services()
        
        return {
            "framework_version": "3.0.0",
            "total_services": len(services),
            "service_categories": self._categorize_services(services),
            "services": services,
            "common_patterns": self._extract_common_patterns(services),
            "usage_guidelines": self._get_usage_guidelines()
        }
    
    def find_services_by_capability(self, capability: str) -> List[Dict[str, Any]]:
        """Find services that provide specific capabilities."""
        services = self.module_manager.get_available_services()
        matches = []
        
        for service_name, service_info in services.items():
            # Search in service description and method descriptions
            if capability.lower() in service_info.get('description', '').lower():
                matches.append({"service": service_name, "match_type": "description", **service_info})
            
            # Search in method names and descriptions
            for method_name, method_info in service_info.get('methods', {}).items():
                if (capability.lower() in method_name.lower() or 
                    capability.lower() in method_info.get('description', '').lower()):
                    matches.append({
                        "service": service_name, 
                        "method": method_name,
                        "match_type": "method",
                        **service_info
                    })
        
        return matches
    
    def get_implementation_template(self, service_type: str = "standard") -> str:
        """Generate implementation template for new modules."""
        template = '''"""
{module_id}/api.py
Generated template based on framework patterns
"""

from typing import Dict, Any, Optional
from core.decorators import register_service, service_methods, ServiceMethod, ServiceParam, ServiceReturn
from core.module_base import DataIntegrityModule
from core.error_utils import Result

MODULE_ID = "{module_id}"

@register_service(f"{module_id}.service", priority=100)
@service_methods([
    ServiceMethod(
        name="initialize",
        description="Initialize the module service",
        params=[
            ServiceParam("config", Dict[str, Any], required=False, description="Optional configuration")
        ],
        returns=ServiceReturn(bool, "True if initialization successful"),
        examples=[
            ServiceExample("initialize()", "True")
        ]
    ),
    ServiceMethod(
        name="process",
        description="Main processing method",
        params=[
            ServiceParam("data", Dict[str, Any], required=True, description="Input data to process")
        ],
        returns=ServiceReturn(Result, "Processing result"),
        examples=[
            ServiceExample("process({{'key': 'value'}})", "Result.success(data={{'processed': True}})")
        ]
    )
])
class {class_name}(DataIntegrityModule):
    MODULE_ID = "{module_id}"
    
    def __init__(self, app_context):
        super().__init__(app_context)
        self.initialized = False
    
    async def initialize(self, config: Optional[Dict[str, Any]] = None) -> bool:
        """Initialize the service."""
        # Implementation here
        self.initialized = True
        return True
    
    async def process(self, data: Dict[str, Any]) -> Result:
        """Main processing method."""
        if not self.initialized:
            return Result.error("SERVICE_NOT_INITIALIZED", "Service not initialized")
        
        # Implementation here
        return Result.success(data={{"processed": True}})
'''
        return template
```

## Benefits for LLM Development

### 1. **Pattern Discovery**
```python
# LLM can discover patterns across services
patterns = llm_interface.get_service_catalog()["common_patterns"]
# Returns: ["async initialization", "Result pattern returns", "Pydantic configuration", ...]
```

### 2. **Capability Search**
```python
# LLM can find relevant services by functionality
services = llm_interface.find_services_by_capability("validation") 
# Returns services that handle validation with method details
```

### 3. **Template Generation**
```python
# LLM can generate correctly structured modules
template = llm_interface.get_implementation_template("standard")
# Returns properly formatted module with correct patterns
```

### 4. **Interactive Documentation**
```python
# LLM can generate comprehensive docs
docs = module_manager.generate_service_documentation("core.settings.service")
# Returns markdown documentation with examples
```

## Implementation Decision: FORCE BREAKING CHANGE

**DECISION**: Based on framework infrastructure principles from CLAUDE.md, implement this as a **breaking change with NO backwards compatibility**.

### Framework Infrastructure Principles Applied:
- ✅ **Single correct pattern** - Only one way to define services
- ✅ **Clean break** - No backwards compatibility or legacy support  
- ✅ **Enforced correctness** - Make wrong usage impossible
- ✅ **No fallbacks** - Wrong patterns should break immediately

### Implementation Strategy: Break and Fix

**Phase 1: Core Infrastructure (Breaking Change)**
- [ ] Make `@service_methods` decorator REQUIRED for all services
- [ ] Enhance `@register_service` to fail if `@service_methods` missing
- [ ] Create ServiceMethod, ServiceParam, ServiceReturn classes
- [ ] Services without proper documentation fail at startup

**Phase 2: Force Core Module Updates**
- [ ] Convert all 4 core modules to use enhanced decorators immediately
- [ ] No compatibility layer - fix modules or they don't load
- [ ] Update module_manager.py with discovery methods
- [ ] Add LLM-friendly interface layer

**Phase 3: Scaffolding and Quality Gates**
- [ ] Update scaffolding tool to generate only compliant modules
- [ ] Add compliance validation for service documentation
- [ ] Make it impossible to create undocumented services
- [ ] Natural selection: bad modules simply won't load

### Expected Benefits:
1. **Clean Infrastructure**: One correct way to define services
2. **LLM-Ready from Day 1**: All services discoverable and documented  
3. **Natural Quality Gate**: Undocumented modules fail to load
4. **Future-Proof**: No technical debt from compatibility layers

## Usage Example: LLM Creating a Module

```python
# LLM queries available patterns
catalog = llm_interface.get_service_catalog()

# LLM finds similar services for reference
similar = llm_interface.find_services_by_capability("document processing")

# LLM generates new module with correct patterns
template = llm_interface.get_implementation_template("standard")

# Result: Properly structured module following all framework conventions
```

This system would make the framework significantly more accessible to LLMs while maintaining the current decorator-based architecture.
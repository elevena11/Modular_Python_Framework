#!/usr/bin/env python3
"""
tools/scaffold_module.py
Modular Framework module scaffolding tool.

Creates framework-compliant module structures following the comprehensive
module creation guide with mandatory error handling patterns.

Usage:
    python tools/scaffold_module.py
    python tools/scaffold_module.py --name my_module --type standard --features database,api,ui_streamlit
"""

import os
import sys
import json
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional
import datetime

class ModuleScaffolderV2:
    """Generate framework-compliant module structures with error handling patterns."""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        
        # Available features that modules can include
        self.available_features = {
            'database': 'Database operations with Result pattern and error handling',
            'api': 'FastAPI REST endpoints with create_error_response pattern', 
            'ui_streamlit': 'Streamlit UI with proper service communication',
            'settings': 'Framework-compliant settings with validation'
        }
        
        # Module types
        self.module_types = {
            'core': 'Core framework modules (essential functionality)',
            'standard': 'Standard modules (general-purpose features)',
            'extensions': 'Extension modules (specialized functionality)'
        }
    
    def interactive_prompt(self) -> Dict[str, Any]:
        """Interactive prompt to gather module requirements."""
        print("Module Scaffolder V2")
        print("=" * 50)
        print("Creates framework-compliant modules with mandatory error handling")
        
        config = {}
        
        # Module name
        while True:
            name = input("\\nModule name (e.g., 'user_analytics'): ").strip()
            if name and name.replace('_', '').replace('-', '').isalnum():
                config['name'] = name
                break
            print("Please enter a valid module name (letters, numbers, underscore, hyphen)")
        
        # Module type
        print(f"\\nModule type:")
        for key, desc in self.module_types.items():
            print(f"   {key}: {desc}")
        
        while True:
            mod_type = input("Choose type [standard]: ").strip() or 'standard'
            if mod_type in self.module_types:
                config['type'] = mod_type
                break
            print(f"Please choose from: {', '.join(self.module_types.keys())}")
        
        # Description
        config['description'] = input(f"\\nDescription [A {config['name']} module for the Modular Framework]: ").strip() or f"A {config['name']} module for the Modular Framework"
        
        # Features
        print(f"\\nAvailable features:")
        for key, desc in self.available_features.items():
            print(f"   {key}: {desc}")
        
        features_input = input("\\nSelect features (comma-separated) [api]: ").strip() or "api"
        features = [f.strip() for f in features_input.split(',') if f.strip() in self.available_features]
        config['features'] = features
        
        # Dependencies (auto-suggest based on features)
        suggested_deps = []
        if 'database' in features:
            suggested_deps.append('core.database')
        if 'settings' in features:
            suggested_deps.append('core.settings')
            
        deps_default = ','.join(suggested_deps) if suggested_deps else ""
        deps_input = input(f"\\nDependencies [{deps_default}]: ").strip() or deps_default
        config['dependencies'] = [d.strip() for d in deps_input.split(',') if d.strip()] if deps_input else []
        
        # Summary
        print(f"\\nSummary:")
        print(f"   Name: {config['name']}")
        print(f"   Type: {config['type']}")
        print(f"   Module ID: {config['type']}.{config['name']}")
        print(f"   Features: {', '.join(config['features'])}")
        print(f"   Dependencies: {', '.join(config['dependencies'])}")
        
        confirm = input("\\nCreate this module? (y/n) [y]: ").strip().lower() or 'y'
        if confirm != 'y':
            print("Cancelled")
            sys.exit(0)
            
        return config
    
    def create_module_structure(self, config: Dict[str, Any]) -> Path:
        """Create the basic module directory structure."""
        module_path = self.project_root / "modules" / config['type'] / config['name']
        
        if module_path.exists():
            response = input(f"Module directory {module_path} already exists. Overwrite? (y/n): ").strip().lower()
            if response != 'y':
                print("Cancelled")
                sys.exit(0)
        
        # Create directories
        module_path.mkdir(parents=True, exist_ok=True)
        
        # Create UI directory if needed
        if 'ui_streamlit' in config['features']:
            (module_path / "ui").mkdir(exist_ok=True)
            
        # Create tests directory
        tests_path = self.project_root / "tests" / "modules" / config['type'] / config['name']
        tests_path.mkdir(parents=True, exist_ok=True)
        
        print(f"Created directory structure at {module_path}")
        return module_path
    
    def generate_manifest(self, config: Dict[str, Any], module_path: Path):
        """Generate manifest.json with local module ID (framework adds path prefix)."""
        manifest = {
            "id": config['name'],  # Just the module name - framework adds type prefix from path
            "name": config['name'].replace('_', ' ').title(),
            "version": "1.0.0",
            "description": config['description'],
            "dependencies": config['dependencies']  # Only service providers
        }
        
        manifest_path = module_path / "manifest.json"
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f, indent=2)
        
        print(f"Generated {manifest_path}")
    
    def generate_api_py(self, config: Dict[str, Any], module_path: Path):
        """Generate api.py with FULL decorator system pattern."""
        module_id = f"{config['type']}.{config['name']}"
        class_name = config['name'].replace('_', ' ').title().replace(' ', '')
        
        # Generate required decorators based on features
        decorators = self._generate_decorators(config, module_id)
        
        content = f'''"""
modules/{config['type']}/{config['name']}/api.py
{config['name'].replace('_', ' ').title()} Module - FULL decorator-based module.

Generated by Module Scaffolder V3 - FULL Decorator Architecture
"""

from typing import Dict, List, Any, Union, Optional
from core.logging import get_framework_logger
from core.error_utils import error_message
from core.decorators import (
{decorators['imports']}
)
from core.module_base import DataIntegrityModule

from .services import {class_name}Service

# Module metadata
MODULE_ID = "{module_id}"
MODULE_VERSION = "1.0.0"
MODULE_DESCRIPTION = "{config['description']}"
MODULE_DEPENDENCIES = {config['dependencies']}

logger = get_framework_logger(MODULE_ID)

# FULL Decorator-Based Module (v3.0.0 Complete Architecture)
{decorators['decorators']}
class {class_name}Module(DataIntegrityModule):
    """
    {config['name'].replace('_', ' ').title()} Module - FULL Decorator Architecture
    
    Generated with complete decorator system for clean, maintainable code.
    """
    
    # Required module constants
    MODULE_ID = "{module_id}"
    MODULE_VERSION = "1.0.0"
    MODULE_DESCRIPTION = "{config['description']}"
    
    def __init__(self):
        """FULL decorator initialization - NO manual dependencies."""
        super().__init__()
        self.service_instance = None
        self.initialized = False
        
        logger.info(f"{{self.MODULE_ID}} created with FULL decorator system")
    
    async def initialize_phase2(self):
        """Phase 2: Initialize with guaranteed service access."""
        logger.info(f"{{self.MODULE_ID}}: Phase 2 - Initializing with dependencies")
        
        try:
{self._get_service_access_code(config)}
            
            # Initialize service with dependencies
            if self.service_instance:
                success = await self.service_instance.initialize(
{self._get_service_init_params(config)}
                )
                
                if success:
{self._get_phase2_logic(config)}
                    self.initialized = True
                    logger.info(f"{{self.MODULE_ID}}: Phase 2 initialization complete")
                    return True
                else:
                    logger.error(f"{{self.MODULE_ID}}: Service initialization failed")
                    return False
            else:
                logger.error(f"{{self.MODULE_ID}}: Service instance not created")
                return False
                
        except Exception as e:
            logger.error(error_message(
                module_id=self.MODULE_ID,
                error_type="PHASE2_INIT_ERROR",
                details=f"Phase 2 initialization failed: {{str(e)}}",
                location="initialize_phase2()"
            ))
            return False
    
    def get_service(self):
        """Get the service instance."""
        return self.service_instance
    
    async def cleanup_resources(self):
        """Graceful shutdown - cleanup only."""
        if self.service_instance and hasattr(self.service_instance, 'cleanup_resources'):
            await self.service_instance.cleanup_resources()
    
    def force_cleanup(self):
        """Force shutdown - cleanup only."""
        if self.service_instance and hasattr(self.service_instance, 'force_cleanup'):
            self.service_instance.force_cleanup()'''

        # Add API endpoints if api feature is selected
        if 'api' in config['features']:
            content += self._get_decorator_api_endpoints(config, module_id, class_name)

        api_path = module_path / "api.py"
        with open(api_path, 'w') as f:
            f.write(content)
        
        print(f"Generated {api_path}")
    
    def _get_initialization_logic(self, config: Dict[str, Any]) -> str:
        """Generate initialization logic based on enabled features."""
        logic_parts = []
        
        if 'database' in config['features']:
            logic_parts.append("            # Setup database operations")
            logic_parts.append("            await self._setup_database_operations()")
        
        if 'settings' in config['features']:
            logic_parts.append("            # Load module settings")
            logic_parts.append("            await self._load_settings()")
        
        if logic_parts:
            return "\n" + "\n".join(logic_parts)
        return ""
    
    def _get_helper_methods(self, config: Dict[str, Any]) -> str:
        """Generate helper methods based on enabled features."""
        methods = []
        
        if 'database' in config['features']:
            methods.append('''
    
    async def _setup_database_operations(self):
        """Setup database functionality."""
        logger.info(f"{MODULE_ID}: Database operations ready")''')
        
        if 'settings' in config['features']:
            methods.append('''
    
    async def _load_settings(self):
        """Load module settings."""
        logger.info(f"{MODULE_ID}: Settings loaded")''')
        
        return "".join(methods)
    
    def _get_natural_api_endpoints(self, config: Dict[str, Any], module_id: str, class_name: str) -> str:
        """Generate clean API endpoints using natural pattern."""
        return f'''

# FastAPI Routes
from fastapi import APIRouter, HTTPException, Depends, Request
from core.error_handler.utils import Result

router = APIRouter(prefix="/{config['name']}", tags=["{config['name']}"])

def get_module_service():
    """Dependency to get the module service."""
    async def _get_module_service(request: Request):
        return request.app.state.app_context.get_service(f"{module_id}.service")
    return _get_module_service

@router.get("/status")
async def get_status(service = Depends(get_module_service())):
    """Get module status."""
    if not service:
        raise HTTPException(status_code=503, detail="Service unavailable")
    
    return {{"status": "active", "module": "{config['name']}"}}

@router.get("/info")
async def get_info():
    """Get module information."""
    return {{
        "module": "{config['name']}",
        "module_id": "{module_id}",
        "status": "active"
    }}'''
    
    def _generate_decorators(self, config: Dict[str, Any], module_id: str) -> Dict[str, str]:
        """Generate decorator imports and decorators based on features."""
        imports = []
        decorators = []
        
        # Always include basic decorators and service discovery classes
        imports.extend([
            "    register_service,",
            "    ServiceMethod,",
            "    ServiceParam,", 
            "    ServiceReturn,",
            "    ServiceExample,",
            "    auto_service_creation,",
            "    phase2_operations,",
            "    enforce_data_integrity,",
            "    graceful_shutdown,",
            "    force_shutdown,"
        ])
        
        # Add feature-specific decorators
        if 'database' in config['features']:
            imports.append("    require_services,")
        if 'api' in config['features']:
            imports.append("    register_api_endpoints,")
            
        # Build decorator list with enhanced service discovery
        service_methods = self._generate_service_methods(config, module_id)
        decorators.append(f'@register_service("{module_id}.service", methods=[')
        decorators.extend(service_methods)
        decorators.append('], priority=100)')
        
        if 'database' in config['features']:
            decorators.append('@require_services(["core.database.service", "core.database.crud_service"])')
        
        decorators.append('@phase2_operations("initialize_phase2")')
        decorators.append('@auto_service_creation(service_class="' + config['name'].replace('_', ' ').title().replace(' ', '') + 'Service")')
        
        if 'api' in config['features']:
            decorators.append('@register_api_endpoints(router_name="router")')
            
        decorators.extend([
            '@enforce_data_integrity(strict_mode=True, anti_mock=True)',
            '@graceful_shutdown(method="cleanup_resources", timeout=30)',
            '@force_shutdown(method="force_cleanup", timeout=5)'
        ])
        
        return {
            'imports': '\n'.join(imports),
            'decorators': '\n'.join(decorators)
        }
    
    def _generate_service_methods(self, config: Dict[str, Any], module_id: str) -> List[str]:
        """Generate service method documentation for the enhanced decorator."""
        methods = []
        
        # Always include initialize method
        methods.extend([
            "    ServiceMethod(",
            '        name="initialize",',
            '        description="Initialize module service with optional settings",',
            "        params=[",
            '            ServiceParam("settings", "Dict[str, Any]", required=False, ',
            '                        description="Optional pre-loaded settings dictionary")',
            "        ],",
            '        returns=ServiceReturn("Result", "Result indicating initialization success"),',
            "        examples=[",
            '            ServiceExample("initialize()", "Result.success(data={\'initialized\': True})"),',
            '            ServiceExample("initialize(settings={\'key\': \'value\'})", "Result.success(...)")',
            "        ],",
            '        tags=["phase2", "initialization"]',
            "    ),"
        ])
        
        # Add feature-specific methods
        if 'database' in config['features']:
            methods.extend([
                "    ServiceMethod(",
                '        name="get_data",',
                '        description="Retrieve data with database operations",',
                "        params=[",
                '            ServiceParam("filters", "Dict[str, Any]", required=False, ',
                '                        description="Optional filter conditions")',
                "        ],",
                '        returns=ServiceReturn("Result", "Result with retrieved data"),',
                "        examples=[",
                '            ServiceExample("get_data()", "Result.success(data=[{...}, {...}])"),',
                '            ServiceExample("get_data({\'status\': \'active\'})", "Result.success(...)")',
                "        ],",
                '        tags=["database", "query"]',
                "    ),"
            ])
        
        if 'api' in config['features']:
            methods.extend([
                "    ServiceMethod(",
                '        name="process_request",',
                '        description="Process API request with validation",',
                "        params=[",
                '            ServiceParam("request_data", "Dict[str, Any]", required=True, ',
                '                        description="Request data to process")',
                "        ],",
                '        returns=ServiceReturn("Result", "Result with processed response"),',
                "        examples=[",
                '            ServiceExample("process_request({\'action\': \'create\'})", "Result.success(data={\'id\': 123})"),',
                "        ],",
                '        tags=["api", "processing"]',
                "    ),"
            ])
        
        # Add default status method
        methods.extend([
            "    ServiceMethod(",
            '        name="get_status",',
            '        description="Get current service status and health information",',
            "        params=[],",
            '        returns=ServiceReturn("Result", "Result with service status"),',
            "        examples=[",
            '            ServiceExample("get_status()", "Result.success(data={\'status\': \'active\', \'uptime\': 300})"),',
            "        ],",
            '        tags=["status", "monitoring"]',
            "    )"
        ])
        
        return methods
    
    def _get_service_access_code(self, config: Dict[str, Any]) -> str:
        """Generate service access code based on features."""
        if 'database' in config['features']:
            return '''            # Services guaranteed available via @require_services decorator
            database_service = self.get_required_service("core.database.service")
            crud_service = self.get_required_service("core.database.crud_service")'''
        return '''            # No external services required for this module'''
    
    def _get_service_init_params(self, config: Dict[str, Any]) -> str:
        """Generate service initialization parameters."""
        if 'database' in config['features']:
            return '''                    database_service=database_service,
                    crud_service=crud_service'''
        return '''                    # No special parameters needed'''
    
    def _get_phase2_logic(self, config: Dict[str, Any]) -> str:
        """Generate Phase 2 initialization logic."""
        logic_parts = []
        if 'database' in config['features']:
            logic_parts.append('                    # Setup database operations if needed')
        if 'settings' in config['features']:
            logic_parts.append('                    # Load module settings if needed')
        
        if logic_parts:
            return '\n' + '\n'.join(logic_parts)
        return ''
    
    def _get_decorator_api_endpoints(self, config: Dict[str, Any], module_id: str, class_name: str) -> str:
        """Generate clean API endpoints using FULL decorator pattern."""
        return f'''

# FastAPI Routes
from fastapi import APIRouter, HTTPException, Depends, Request
from core.error_utils import create_error_response

router = APIRouter(prefix="/{config['name']}", tags=["{config['name']}"])

def get_module_service():
    \"\"\"Dependency to get the module service.\"\"\"
    async def _get_module_service(request: Request):
        return request.app.state.app_context.get_service("{module_id}.service")
    return _get_module_service

@router.get("/status")
async def get_status(service = Depends(get_module_service())):
    \"\"\"Get module status - Essential for UI service detection.\"\"\"
    try:
        if not service:
            raise HTTPException(
                status_code=503,
                detail=create_error_response(
                    module_id=MODULE_ID,
                    code="SERVICE_UNAVAILABLE",
                    message="Service is not available"
                )
            )
        
        return {{"status": "active", "module": "{config['name']}"}}
        
    except HTTPException:
        raise
        
    except Exception as e:
        logger.error(error_message(
            module_id=MODULE_ID,
            error_type="UNEXPECTED_ERROR",
            details=f"Unexpected error in get_status: {{str(e)}}",
            location="get_status()"
        ))
        
        raise HTTPException(
            status_code=500,
            detail=create_error_response(
                module_id=MODULE_ID,
                code="INTERNAL_ERROR",
                message="An unexpected error occurred"
            )
        )

@router.get("/info")
async def get_info():
    \"\"\"Get module information.\"\"\"
    return {{
        "name": "{config['name']}",
        "version": MODULE_VERSION,
        "description": MODULE_DESCRIPTION
    }}'''
    
    
    def generate_services_py(self, config: Dict[str, Any], module_path: Path):
        """Generate services.py with Result pattern and error handling."""
        module_id = f"{config['type']}.{config['name']}"
        class_name = config['name'].replace('_', ' ').title().replace(' ', '')
        
        content = f'''"""
modules/{config['type']}/{config['name']}/services.py
Core services for the {config['name']} module.

Generated by Module Scaffolder V2
"""

from typing import Dict, Any, Optional
from core.logging import get_framework_logger
from core.error_utils import Result, error_message

# Module identity (must match manifest.json)
MODULE_ID = "{module_id}"
logger = get_framework_logger(MODULE_ID)  # Framework-aware logging

class {class_name}Service:
    """Main service for the {config['name']} module."""
    
    def __init__(self):
        """FULL decorator initialization - NO manual dependencies."""
        self.initialized = False
        self.logger = logger
        
        logger.info(f"{{MODULE_ID}} service created")
    
    @property
    def dependency_service(self):
        """Lazy load dependency service."""
        if self._dependency_service is None:
            # Example: Load settings service if needed
            self._dependency_service = self.app_context.get_service("core.settings.service")
            if not self._dependency_service:
                logger.error(error_message(
                    module_id=MODULE_ID,
                    error_type="DEPENDENCY_UNAVAILABLE",
                    details="Settings service not available",
                    location="dependency_service property"
                ))
        return self._dependency_service
    
    async def initialize(self, database_service=None, crud_service=None) -> bool:
        """Phase 2 initialization - Set up with provided services."""
        if self.initialized:
            return True
        
        logger.info(f"Initializing {{MODULE_ID}} service")
        
        try:
            # Store services if provided
            if database_service:
                self.database_service = database_service
            if crud_service:
                self.crud_service = crud_service
            
            # Perform complex initialization
            # TODO: Add your initialization logic here
            
            self.initialized = True
            logger.info(f"{{MODULE_ID}} service initialized")
            return True
            
        except Exception as e:
            logger.error(error_message(
                module_id=MODULE_ID,
                error_type="INIT_ERROR",
                details=f"Error during initialization: {{str(e)}}",
                location="initialize()"
            ))
            return False
    
    async def example_method(self, data: Dict[str, Any]) -> Result:
        """Example service method with proper Result pattern."""
        # Check initialization
        if not self.initialized and not await self.initialize():
            return Result.error(
                code="SERVICE_NOT_INITIALIZED",
                message=f"{{MODULE_ID}} service not initialized"
            )
        
        try:
            # Validate input
            if not data:
                return Result.error(
                    code="INVALID_INPUT",
                    message="No data provided"
                )
            
            # TODO: Replace with your business logic
            result = {{
                "processed": True,
                "data": data,
                "module": "{config['name']}"
            }}
            
            return Result.success(data=result)
            
        except Exception as e:
            logger.error(error_message(
                module_id=MODULE_ID,
                error_type="PROCESSING_ERROR",
                details=f"Error in example_method: {{str(e)}}",
                location="example_method()"
            ))
            
            return Result.error(
                code="PROCESSING_ERROR",
                message="Failed to process data",
                details={{"error_type": type(e).__name__}}
            )
    
    async def cleanup_resources(self):
        """
        Graceful resource cleanup - logging handled by decorator.
        Called during normal application shutdown via @graceful_shutdown decorator.
        """
        # Cancel background tasks
        # TODO: Add your background task cleanup here
        # for task in self._background_tasks:
        #     task.cancel()
        
        # Close connections
        # TODO: Add your connection cleanup here
        # await self.close_database_connections()
        
        # Save persistent state
        # TODO: Add your state persistence here
        # await self.save_state()
        
        self.initialized = False
    
    def force_cleanup(self):
        """
        Force cleanup of resources - logging handled by decorator.
        Called during emergency shutdown via @force_shutdown decorator.
        """
        # Synchronous cleanup only - ignore errors during force cleanup
        try:
            # TODO: Add your force cleanup logic here
            # self.force_close_connections()
            # self.clear_memory_caches()
            self.initialized = False
        except Exception:
            pass  # Ignore errors during force cleanup'''

        services_path = module_path / "services.py"
        with open(services_path, 'w') as f:
            f.write(content)
        
        print(f"Generated {services_path}")
    
    def generate_api_schemas_py(self, config: Dict[str, Any], module_path: Path):
        """Generate api_schemas.py with Pydantic models (if API feature enabled)."""
        if 'api' not in config['features']:
            return
            
        class_name = config['name'].replace('_', ' ').title().replace(' ', '')
        
        content = f'''"""
modules/{config['type']}/{config['name']}/api_schemas.py
Pydantic schemas for API request/response validation.

Generated by Module Scaffolder V2
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

class {class_name}Request(BaseModel):
    """Request schema for {config['name']} operations."""
    name: str = Field(..., min_length=1, description="Item name")
    description: Optional[str] = Field(None, description="Optional description")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    model_config = {{
        "json_schema_extra": {{
            "example": {{
                "name": "example_item",
                "description": "An example item for the {config['name']} module",
                "metadata": {{"key": "value"}}
            }}
        }}
    }}

class {class_name}Response(BaseModel):
    """Response schema for {config['name']} operations."""
    name: str = Field(..., description="Item name")
    version: str = Field(..., description="Module version")
    description: str = Field(..., description="Module description")
    
    model_config = {{
        "json_schema_extra": {{
            "example": {{
                "name": "{config['name']}",
                "version": "1.0.0",
                "description": "{config['description']}"
            }}
        }}
    }}'''

        schemas_path = module_path / "api_schemas.py"
        with open(schemas_path, 'w') as f:
            f.write(content)
        
        print(f"Generated {schemas_path}")
    
    def generate_database_files(self, config: Dict[str, Any], module_path: Path):
        """Generate database.py and db_models.py with framework patterns."""
        if 'database' not in config['features']:
            return
            
        module_id = f"{config['type']}.{config['name']}"
        class_name = config['name'].replace('_', ' ').title().replace(' ', '')
        
        # Generate db_models.py.template with COMMENTED OUT content
        # This prevents accidental table creation when file is renamed to .py
        models_content = f'''"""
modules/{config['type']}/{config['name']}/db_models.py
SQLAlchemy models for the {config['name']} module.

Generated by Module Scaffolder V3 - FULL Decorator Architecture

IMPORTANT: This template has ALL MODEL DEFINITIONS COMMENTED OUT
to prevent accidental table creation when renamed to .py

TO USE DATABASE:
1. Rename this file to db_models.py (remove .template extension)  
2. Uncomment the model definitions below
3. Customize the models for your specific needs
4. Framework will automatically discover and create tables
"""

# Database configuration for file-based discovery (COMMENTED OUT)
# Uncomment this line when you want to enable database functionality
# DATABASE_NAME = "{config['name']}"

# Imports needed for database models (COMMENTED OUT)  
# Uncomment these imports when enabling database
# from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean
# from core.database import get_database_base, SQLiteJSON
# from sqlalchemy.sql import func

# Database base creation (COMMENTED OUT)
# Uncomment and customize when you need database functionality
# {class_name}Base = get_database_base(DATABASE_NAME)

# Example model definition (COMMENTED OUT)
# Uncomment and customize this model when you need database tables
# class {class_name}Model({class_name}Base):
#     \"\"\"Example model for {config['name']} items.\"\"\"
#     __tablename__ = "{config['name']}_items"
#     __table_args__ = {{'extend_existing': True}}
#     
#     id = Column(Integer, primary_key=True)
#     name = Column(String(100), nullable=False)  
#     description = Column(Text, nullable=True)
#     metadata = Column(SQLiteJSON, nullable=False, default=dict)
#     
#     # Timestamps
#     created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
#     updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
#     
#     # Status
#     is_active = Column(Boolean, default=True, nullable=False)
#     
#     def __repr__(self):
#         return f"<{class_name}Model(id={{self.id}}, name='{{self.name}}')>"

# Add more models here as needed (remember to uncomment first!)'''

        models_path = module_path / "db_models.py.template"
        with open(models_path, 'w') as f:
            f.write(models_content)
        
        # Generate database.py.template with clean, ready-to-use code
        database_content = f'''"""
modules/{config['type']}/{config['name']}/database.py
Database operations for the {config['name']} module.

Generated by Module Scaffolder V3 - FULL Decorator Architecture

TO USE DATABASE:
1. First rename db_models.py.template to db_models.py and uncomment models
2. Then rename this file to database.py (remove .template extension)
3. Customize the database operations for your specific needs
4. Update services.py to use database operations if needed
"""

import logging
import contextlib
from typing import Dict, Any, Optional, AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from core.error_utils import Result, error_message

# Import models when db_models.py is uncommented
# from .db_models import {class_name}Model

MODULE_ID = "{module_id}"
logger = logging.getLogger(f"{{MODULE_ID}}.database")


class {class_name}DatabaseOperations:
    """Database operations for {config['name']} module."""
    
    def __init__(self, app_context):
        self.app_context = app_context
        self.db_service = app_context.get_service("core.database.service")
        self.crud_service = app_context.get_service("core.database.crud_service")
        self.initialized = False
        self.logger = logger
    
    async def initialize(self) -> bool:
        """Initialize database operations."""
        if self.initialized:
            return True
        
        if not self.db_service or not self.db_service.initialized:
            self.logger.warning(error_message(
                module_id=MODULE_ID,
                error_type="DB_SERVICE_UNAVAILABLE",
                details="Database service not available",
                location="initialize()"
            ))
            return False
        
        if not self.crud_service:
            self.logger.warning(error_message(
                module_id=MODULE_ID,
                error_type="CRUD_SERVICE_UNAVAILABLE",
                details="CRUD service not available",
                location="initialize()"
            ))
            return False
        
        self.initialized = True
        self.logger.info("Database operations initialized")
        return True
    
    @contextlib.asynccontextmanager
    async def _db_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Provides async database session."""
        if not self.initialized and not await self.initialize():
            raise RuntimeError("Database operations not initialized")
        
        session_factory = self.db_service.get_database_session("{config['name']}")
        async with session_factory() as session:
            yield session
    
    async def create_item(self, item_data: Dict[str, Any]) -> Result:
        """Create a new item."""
        try:
            async with self._db_session() as session:
                # Uncomment when {class_name}Model is available:
                # new_item = {class_name}Model(**item_data)
                # session.add(new_item)
                # await session.commit()
                # await session.refresh(new_item)
                # return Result.success(data={{"id": new_item.id, "created": True}})
                
                # Placeholder for when models are uncommented
                return Result.success(data={{"message": "Database operations ready - uncomment model usage"}})
                
        except Exception as e:
            return Result.error(
                code="CREATE_ITEM_FAILED",
                message=f"Failed to create item",
                details={{"error": str(e), "item_data": item_data}}
            )
    
    async def get_item(self, item_id: int) -> Result:
        """Retrieve an item by ID."""
        try:
            async with self._db_session() as session:
                # Uncomment when {class_name}Model is available:
                # item = await session.get({class_name}Model, item_id)
                # if item:
                #     return Result.success(data={{"id": item.id, "name": item.name}})
                # else:
                #     return Result.error(code="ITEM_NOT_FOUND", message=f"Item {{item_id}} not found")
                
                # Placeholder for when models are uncommented  
                return Result.success(data={{"message": f"Would retrieve item {{item_id}} - uncomment model usage"}})
                
        except Exception as e:
            return Result.error(
                code="GET_ITEM_FAILED",
                message=f"Failed to get item {{item_id}}",
                details={{"error": str(e), "item_id": item_id}}
            )'''

        database_path = module_path / "database.py.template"
        with open(database_path, 'w') as f:
            f.write(database_content)
        
        print(f"Generated {models_path}")
        print(f"Generated {database_path}")
        print("⚠️  Database files are .template files - rename to .py when needed")
    
    def generate_ui_files(self, config: Dict[str, Any], module_path: Path):
        """Generate UI files with proper service communication patterns."""
        if 'ui_streamlit' not in config['features']:
            return
            
        ui_dir = module_path / "ui"
        module_id = f"{config['type']}.{config['name']}"
        
        # Generate __init__.py
        with open(ui_dir / "__init__.py", 'w') as f:
            f.write('"""UI components for the module."""\n')
        
        # Generate Streamlit UI with proper communication
        streamlit_content = f'''"""
modules/{config['type']}/{config['name']}/ui/ui_streamlit.py
Streamlit UI interface for the {config['name']} module.

Generated by Module Scaffolder V2
"""

import streamlit as st
import requests
import logging
from typing import Dict, Any

logger = logging.getLogger("{module_id}")

def register_components(ui_context):
    """Register UI components with the framework - REQUIRED."""
    ui_context.register_element({{
        "id": "{config['name']}_interface",
        "type": "tab",
        "display_name": "{config['name'].replace('_', ' ').title()}",
        "description": "{config['description']}",
        "render_function": render_ui,
        "order": 90
    }})

def render_ui(app_context) -> Dict[str, Any]:
    """
    Render the Streamlit UI for the {config['name']} module.
    Uses API communication instead of direct service access.
    """
    st.header("{config['name'].replace('_', ' ').title()}")
    st.write("{config['description']}")
    
    # Check service availability via API
    try:
        base_url = getattr(app_context, 'backend_api', {{}}).get('base_url', 'http://127.0.0.1:8000')
        response = requests.get(f"{{base_url}}/api/v1/{config['name']}/status", timeout=5)
        
        if response.status_code != 200:
            st.error("{config['name'].replace('_', ' ').title()} service not available")
            return {{}}
            
        service_status = response.json()
        if service_status.get("status") != "active":
            st.error("{config['name'].replace('_', ' ').title()} service not active")
            return {{}}
        
        st.success("{config['name'].replace('_', ' ').title()} service is available and active")
        
    except requests.exceptions.RequestException as e:
        st.error(f"Cannot connect to {config['name'].replace('_', ' ').title()} service: {{e}}")
        return {{}}
    
    # Status section
    with st.expander("Status", expanded=True):
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("Status", "Active")
        
        with col2:
            st.metric("Module", "{config['name']}")
    
    # TODO: Add your UI components here
    st.subheader("Actions")
    
    if st.button("Test Service"):
        try:
            response = requests.get(f"{{base_url}}/api/v1/{config['name']}/info", timeout=5)
            if response.status_code == 200:
                result = response.json()
                st.success(f"Service test successful: {{result}}")
            else:
                st.error(f"Service test failed: HTTP {{response.status_code}}")
        except Exception as e:
            st.error(f"Service test failed: {{str(e)}}")
    
    return {{
        "module": "{config['name']}",
        "status": "rendered"
    }}'''

        streamlit_path = ui_dir / "ui_streamlit.py"
        with open(streamlit_path, 'w') as f:
            f.write(streamlit_content)
        
        print(f"Generated {streamlit_path}")
    
    def generate_module_settings(self, config: Dict[str, Any], module_path: Path):
        """Generate settings.py with modern Pydantic pattern."""
        if 'settings' not in config['features']:
            return
            
        module_id = f"{config['type']}.{config['name']}"
        class_name = config['name'].replace('_', ' ').title().replace(' ', '') + 'Settings'
        
        content = f'''"""
modules/{config['type']}/{config['name']}/settings.py
Pydantic settings model for {module_id} module.

Generated by Module Scaffolder V3 - Modern Pydantic Pattern
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any
from enum import Enum


class {class_name}(BaseModel):
    """
    Pydantic settings model for {config['name']} module.
    
    All settings with defaults and validation using Pydantic V2 patterns.
    Environment variables can override any setting using the format:
    {module_id.upper().replace('.', '_')}_SETTING_NAME=value
    """
    
    model_config = ConfigDict(
        env_prefix="{module_id.upper().replace('.', '_')}_",
        env_file='.env',
        env_file_encoding='utf-8',
        extra='forbid',  # Prevent extra fields
        validate_default=True,
        str_strip_whitespace=True
    )
    
    # Example settings - customize for your module
    # IMPORTANT: Remove the comments below and add your actual settings
    # These examples are commented out to prevent accidental use in production
    
    # feature_enabled: bool = Field(
    #     default=True,
    #     description="Enable main feature functionality"
    # )
    
    # max_items: int = Field(
    #     default=100,
    #     ge=1,
    #     le=1000,
    #     description="Maximum number of items to process"
    # )
    
    # timeout_seconds: float = Field(
    #     default=30.0,
    #     gt=0.0,
    #     le=300.0,
    #     description="Operation timeout in seconds"
    # )
    
    # debug_mode: bool = Field(
    #     default=False,
    #     description="Enable debug mode for detailed logging"
    # )
    
    # cache_size: int = Field(
    #     default=50,
    #     ge=10,
    #     le=500,
    #     description="Size of internal cache"
    # )
    
    # Add your actual module settings here
    pass  # Remove this line when you add real settings


# Export the settings class for easy import
__all__ = ["{class_name}"]'''

        settings_path = module_path / "settings.py"
        with open(settings_path, 'w') as f:
            f.write(content)
        
        print(f"Generated {settings_path}")
    
    
    def generate_tests(self, config: Dict[str, Any]):
        """Generate comprehensive test structure."""
        tests_path = self.project_root / "tests" / "modules" / config['type'] / config['name']
        module_id = f"{config['type']}.{config['name']}"
        class_name = config['name'].replace('_', ' ').title().replace(' ', '')
        
        # Create test directory structure
        tests_path.mkdir(parents=True, exist_ok=True)
        
        # Generate __init__.py
        with open(tests_path / "__init__.py", 'w') as f:
            f.write(f'"""Tests for the {config["name"]} module."""\n')
        
        # Generate test_service.py with Result pattern testing
        test_content = f'''"""
Test the {config['name']} service functionality.
Generated by Module Scaffolder V2
"""

import pytest
from unittest.mock import Mock, AsyncMock

from modules.{config['type']}.{config['name']}.services import {class_name}Service
from core.error_utils import Result

@pytest.fixture
def mock_app_context():
    """Mock app context for testing"""
    context = Mock()
    context.get_service.return_value = Mock()  # Mock dependency services
    context.get_module_settings = AsyncMock(return_value={{}})
    return context

@pytest.fixture  
def {config['name']}_service(mock_app_context):
    """Create a {config['name']} service instance for testing"""
    return {class_name}Service(mock_app_context)

@pytest.mark.asyncio
async def test_service_initialization({config['name']}_service, mock_app_context):
    """Test service initialization"""
    # Test that service starts uninitialized
    assert not {config['name']}_service.initialized
    
    # Test initialization
    result = await {config['name']}_service.initialize(mock_app_context)
    assert result is True
    assert {config['name']}_service.initialized

@pytest.mark.asyncio
async def test_example_method_success({config['name']}_service, mock_app_context):
    """Test the example service method returns Result object"""
    # Initialize service first
    await {config['name']}_service.initialize(mock_app_context)
    
    # Test the method with valid data
    test_data = {{"test": "data"}}
    result = await {config['name']}_service.example_method(test_data)
    
    # Verify Result object pattern
    assert isinstance(result, Result)
    assert result.success is True
    assert result.data is not None
    assert isinstance(result.data, dict)
    assert result.data["module"] == "{config['name']}"
    assert result.data["processed"] is True

@pytest.mark.asyncio
async def test_example_method_invalid_input({config['name']}_service, mock_app_context):
    """Test example method with invalid input returns error Result"""
    await {config['name']}_service.initialize(mock_app_context)
    
    # Test with empty data
    result = await {config['name']}_service.example_method({{}})
    
    # Verify error Result pattern
    assert isinstance(result, Result)
    assert result.success is False
    assert result.error is not None
    assert isinstance(result.error, dict)
    assert result.error["code"] == "INVALID_INPUT"

@pytest.mark.asyncio
async def test_example_method_service_not_initialized({config['name']}_service):
    """Test that methods return error when service not initialized"""
    # Test without initialization
    result = await {config['name']}_service.example_method({{"test": "data"}})
    
    # Should return error Result
    assert isinstance(result, Result)
    assert result.success is False
    assert result.error["code"] == "SERVICE_NOT_INITIALIZED"

@pytest.mark.asyncio
async def test_service_cleanup_resources({config['name']}_service, mock_app_context):
    """Test service graceful cleanup"""
    # Initialize and then cleanup
    await {config['name']}_service.initialize(mock_app_context)
    assert {config['name']}_service.initialized
    
    await {config['name']}_service.cleanup_resources()
    assert not {config['name']}_service.initialized

def test_service_force_cleanup({config['name']}_service, mock_app_context):
    """Test force cleanup (synchronous)"""
    # Initialize service
    import asyncio
    asyncio.run({config['name']}_service.initialize(mock_app_context))
    assert {config['name']}_service.initialized
    
    # Force cleanup
    {config['name']}_service.force_cleanup()
    assert not {config['name']}_service.initialized'''

        with open(tests_path / "test_service.py", 'w') as f:
            f.write(test_content)
        
        # Generate test_compliance.py
        compliance_test = f'''"""
Compliance tests for the {config['name']} module.
Tests the module against Modular Framework standards.
Generated by Module Scaffolder V2
"""

import pytest
from pathlib import Path
import json
import importlib.util

MODULE_PATH = Path(__file__).parent.parent.parent.parent.parent / "modules" / "{config['type']}" / "{config['name']}"

def test_module_structure():
    """Test that required files exist"""
    # NOTE: manifest.json no longer used in v3.0.0 - replaced by decorators and MODULE_* constants
    # assert (MODULE_PATH / "manifest.json").exists(), "manifest.json missing"  # DISABLED: v3.0.0
    assert (MODULE_PATH / "api.py").exists(), "api.py missing"
    assert (MODULE_PATH / "services.py").exists(), "services.py missing"
    # readme.md is not generated by scaffolder - developer creates after implementation

def test_decorator_metadata():
    """Test v3.0.0 decorator-based metadata compliance"""  
    api_path = MODULE_PATH / "api.py"
    assert api_path.exists()
    
    with open(api_path) as f:
        api_content = f.read()
    
    # Test MODULE_* constants (replace manifest.json)
    assert 'MODULE_ID = "{module_id}"' in api_content, "MODULE_ID constant missing"
    assert 'MODULE_VERSION = "1.0.0"' in api_content, "MODULE_VERSION constant missing"
    assert 'MODULE_DESCRIPTION =' in api_content, "MODULE_DESCRIPTION constant missing"
    
    # Test decorator presence
    assert "@register_service(" in api_content, "Missing @register_service decorator"
    assert "@enforce_data_integrity(" in api_content, "Missing @enforce_data_integrity decorator"

def test_decorator_based_initialization():
    """Test that v3.0.0 decorator-based initialization is implemented"""
    api_path = MODULE_PATH / "api.py"
    assert api_path.exists()
    
    with open(api_path) as f:
        api_content = f.read()
    
    # Check for decorator-based class structure
    assert "class " in api_content and "(DataIntegrityModule):" in api_content, "Missing DataIntegrityModule inheritance"
    
    # Check for Phase 1 method (in class)
    assert "async def initialize(self) -> bool:" in api_content, "Missing Phase 1 initialize method"
    
    # Check for Phase 2 method (in class)  
    assert "async def setup_phase2(self) -> bool:" in api_content, "Missing Phase 2 setup_phase2 method"
    
    # Check for post-init hook registration
    assert "register_post_init_hook" in api_content, "Missing post-init hook registration"

def test_error_handling_compliance():
    """Test that error handling patterns are implemented"""
    api_path = MODULE_PATH / "api.py"
    services_path = MODULE_PATH / "services.py"
    
    # Check API error handling
    with open(api_path) as f:
        api_content = f.read()
    
    assert "from core.error_utils import error_message" in api_content, "Missing error_message import"
    assert "error_message(" in api_content, "Not using error_message utility"
    
    # Check services error handling
    with open(services_path) as f:
        services_content = f.read()
    
    assert "from core.error_utils import Result, error_message" in services_content, "Missing Result/error_message imports"
    assert "Result.success(" in services_content, "Not using Result.success pattern"
    assert "Result.error(" in services_content, "Not using Result.error pattern"

def test_module_id_consistency():
    """Test MODULE_ID constant is defined consistently"""
    api_path = MODULE_PATH / "api.py"
    services_path = MODULE_PATH / "services.py"
    
    with open(api_path) as f:
        api_content = f.read()
    
    assert 'MODULE_ID = "{module_id}"' in api_content, "MODULE_ID not defined correctly in api.py"
    
    with open(services_path) as f:
        services_content = f.read()
    
    assert 'MODULE_ID = "{module_id}"' in services_content, "MODULE_ID not defined correctly in services.py"

{self._get_api_compliance_test(config) if 'api' in config['features'] else ""}

{self._get_ui_compliance_test(config) if 'ui_streamlit' in config['features'] else ""}'''

        with open(tests_path / "test_compliance.py", 'w') as f:
            f.write(compliance_test)
        
        print(f"Generated test files in {tests_path}")
    
    def _get_api_compliance_test(self, config: Dict[str, Any]) -> str:
        """Generate API compliance tests."""
        return f'''
def test_api_error_handling():
    """Test API endpoints use create_error_response pattern"""
    api_path = MODULE_PATH / "api.py"
    
    with open(api_path) as f:
        api_content = f.read()
    
    assert "from core.error_utils import create_error_response" in api_content, "Missing create_error_response import"
    assert "create_error_response(" in api_content, "Not using create_error_response utility"
    assert "register_routes" in api_content, "Missing register_routes function"

def test_required_api_endpoints():
    """Test that required API endpoints exist"""
    api_path = MODULE_PATH / "api.py"
    
    with open(api_path) as f:
        api_content = f.read()
    
    assert "/status" in api_content, "Missing required /status endpoint"
    assert "/info" in api_content, "Missing required /info endpoint"'''
    
    def _get_ui_compliance_test(self, config: Dict[str, Any]) -> str:
        """Generate UI compliance tests."""
        return f'''
def test_ui_registration():
    """Test UI components have proper registration"""
    ui_path = MODULE_PATH / "ui" / "ui_streamlit.py"
    assert ui_path.exists(), "ui_streamlit.py missing"
    
    with open(ui_path) as f:
        ui_content = f.read()
    
    assert "def register_components(ui_context):" in ui_content, "Missing register_components function"
    assert "ui_context.register_element(" in ui_content, "Not registering UI elements"
    assert "def render_ui(app_context):" in ui_content, "Missing render_ui function"'''
    
    def run_non_interactive(self, config):
        """Run scaffolding in non-interactive mode"""
        print(f"Scaffolding Modular Framework Module: {config['name']}")
        print("=" * 60)
        
        # Show configuration
        print(f"Name: {config['name']}")
        print(f"Type: {config['type']}")
        print(f"Module ID: {config['type']}.{config['name']}")
        print(f"Description: {config['description']}")
        print(f"Features: {', '.join(config['features'])}")
        print(f"Dependencies: {', '.join(config['dependencies'])}")
        
        # Create and generate module
        self._scaffold_module(config)
    
    def run(self):
        """Main scaffolding process - interactive mode"""
        config = self.interactive_prompt()
        self._scaffold_module(config)
    
    def _scaffold_module(self, config):
        """Internal method to scaffold module with given config"""
        print(f"\\nCreating framework-compliant module structure...")
        
        # Create module structure
        module_path = self.create_module_structure(config)
        
        # Note: manifest.json generation disabled in v3.0.0 - using decorators instead
        # self.generate_manifest(config, module_path)  # DISABLED: v3.0.0 uses decorators
        self.generate_api_py(config, module_path)
        self.generate_services_py(config, module_path)
        
        if 'api' in config['features']:
            self.generate_api_schemas_py(config, module_path)
        
        if 'database' in config['features']:
            self.generate_database_files(config, module_path)
        
        if 'ui_streamlit' in config['features']:
            self.generate_ui_files(config, module_path)
        
        if 'settings' in config['features']:
            self.generate_module_settings(config, module_path)
        
        self.generate_tests(config)
        
        # NOTE: compliance.md is NOT generated - it should be created by compliance.py
        
        print(f"\\nFramework-compliant module '{config['name']}' scaffolded successfully!")
        print(f"Location: {module_path}")
        
        print(f"\\nDevelopment Workflow:")
        print(f"1. Module scaffolded (DONE)")
        print(f"2. Implement your business logic in services.py")
        print(f"3. Add environment variables if handling sensitive data")
        print(f"4. Run unit tests: pytest tests/modules/{config['type']}/{config['name']}/")
        print(f"")
        print(f"BEFORE TESTING FRAMEWORK INTEGRATION:")
        print(f"5. Run compliance check:")
        print(f"   python tools/compliance/compliance.py validate --module {config['type']}.{config['name']}")
        print(f"6. Fix any compliance issues found")
        print(f"")
        print(f"THEN TEST FRAMEWORK INTEGRATION:")
        print(f"7. Test module loading: python app.py")
        print(f"8. Debug any remaining integration issues")
        
        print(f"\\n" + "="*80)
        print(f"IMPORTANT: Framework Guidelines")
        print(f"="*80)
        print(f"- Use Result pattern: All service methods return Result objects")
        print(f"- Error handling: Import and use error_message utility")
        print(f"- Environment variables: Use os.getenv() for sensitive data")
        print(f"- Settings validation: Use 'bool', 'int', 'float' (not 'boolean', 'integer')")
        print(f"")
        print(f"Complete guide: docs/enhanced-module-creation-workflow.md")
        print(f"="*80)
        
        print(f"\\nMulti-component modules:")
        print(f"   If creating multiple interdependent components, review:")
        print(f"   docs/llm-agent-project/service-registration-circular-dependency-issue.md")
        
        print(f"\\nSuccess Criteria:")
        print(f"   - Compliance for implemented features (use Exceptions section in compliance.md")
        print(f"     to document why features aren't used: 'module does not use database')")
        print(f"   - Module loads without errors")
        print(f"   - All tests pass")
        print(f"   - Environment variables used for sensitive data")
        print(f"   - Create readme.md after module implementation is complete")
    

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Scaffold a new Modular Framework module with compliance")
    parser.add_argument("--name", "-n", help="Module name (e.g., 'user_analytics')")
    parser.add_argument("--type", "-t", choices=['core', 'standard', 'extensions'], default='standard', 
                       help="Module type (default: standard)")
    parser.add_argument("--features", "-f", help="Comma-separated list of features (e.g., 'database,api,ui_streamlit')")
    parser.add_argument("--list-features", action="store_true", help="List available features and exit")
    
    args = parser.parse_args()
    
    scaffolder = ModuleScaffolderV2()
    
    # List features and exit
    if args.list_features:
        print("Available Features:")
        for key, desc in scaffolder.available_features.items():
            print(f"   {key}: {desc}")
        return
    
    # Non-interactive mode
    if args.name:
        # Build config from args
        config = {
            'name': args.name,
            'type': args.type,
            'description': f"A {args.name} module for the Modular Framework",
            'features': args.features.split(',') if args.features else ['api'],
            'dependencies': []
        }
        
        # Auto-suggest dependencies
        if 'database' in config['features']:
            config['dependencies'].append('core.database')
        if 'settings' in config['features']:
            config['dependencies'].append('core.settings')
        
        scaffolder.run_non_interactive(config)
    else:
        # Interactive mode
        scaffolder.run()

if __name__ == "__main__":
    main()
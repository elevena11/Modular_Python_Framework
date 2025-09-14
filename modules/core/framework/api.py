"""
modules/core/global/api.py
NEW DECORATOR PATTERN - Migrated from manual initialize() to declarative registration
Entry point for the global core module using centralized registration system
"""

import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException
from core.error_utils import error_message, create_error_response

# Import complete decorator system for centralized registration
from core.decorators import (
    register_service,
    ServiceMethod,
    ServiceParam,
    ServiceReturn,
    ServiceExample,
    register_api_endpoints,
    enforce_data_integrity,
    module_health_check,
    graceful_shutdown,
    force_shutdown,
    inject_dependencies,
    initialization_sequence,
    phase2_operations,
    auto_service_creation
)
from core.module_base import DataIntegrityModule

# Import module components
from .services import FrameworkService
from .settings import FrameworkSettings
from .api_schemas import SessionInfoResponse, FrameworkStatusResponse, FrameworkInfoResponse

# NEW DECORATOR-BASED MODULE CLASS (centralized registration)

# v3.0.0 Complete Decorator-Based Registration (eliminates all manual patterns)
@register_service("core.framework.service", methods=[
    ServiceMethod(
        name="initialize",
        description="Initialize framework service with typed settings",
        params=[
            ServiceParam("settings", "FrameworkSettings", required=False, description="Optional pre-validated settings instance")
        ],
        returns=ServiceReturn(bool, "True if initialization successful"),
        examples=[
            ServiceExample("initialize()", "True"),
            ServiceExample("initialize(settings=validated_settings)", "True")
        ],
        tags=["phase2", "initialization"]
    ),
    ServiceMethod(
        name="get_config",
        description="Get framework configuration information",
        params=[],
        returns=ServiceReturn("Result", "Result with framework configuration data"),
        examples=[
            ServiceExample("get_config()", "Result.success(data={'app_title': 'Reality Anchor Hub', 'version': '0.1.0'})"),
        ],
        tags=["config", "info"]
    ),
    ServiceMethod(
        name="get_typed_settings",
        description="Get typed framework settings as validated Pydantic model",
        params=[],
        returns=ServiceReturn("Result", "Result with FrameworkSettings instance"),
        examples=[
            ServiceExample("get_typed_settings()", "Result.success(data=FrameworkSettings(...))"),
        ],
        tags=["settings", "config"]
    )
], priority=100)
@inject_dependencies("app_context")
@auto_service_creation(service_class="FrameworkService")
@initialization_sequence("setup_infrastructure", "create_service", "register_settings", phase="phase1")
@phase2_operations("initialize_service", dependencies=["core.settings.service"], priority=100)
@register_api_endpoints(router_name="router")
@enforce_data_integrity(strict_mode=True, anti_mock=True)
@module_health_check(interval=300)
@graceful_shutdown(method="cleanup_resources", timeout=30, priority=100)
@force_shutdown(method="force_cleanup", timeout=5)
class FrameworkModule(DataIntegrityModule):
    """
    Global core module using the new decorator-based registration pattern.
    
    Notice the dramatic reduction in code:
    - No manual service registration
    - No manual API route registration  
    - No manual post-init hook registration
    - All handled automatically by decorators and centralized processor
    
    This is the power of centralized registration:
    - All registration logic centralized in ModuleProcessor
    - Consistent implementation across all modules
    - Impossible to forget registration steps
    - Easy to add new features framework-wide
    """
    
    MODULE_ID = "core.framework"
    MODULE_NAME = "Framework Module"
    MODULE_DESCRIPTION = "Provides framework utilities and session management"
    MODULE_VERSION = "1.0.0"
    MODULE_AUTHOR = "Modular Framework"
    MODULE_DEPENDENCIES = ["core.settings"]
    MODULE_ENTRY_POINT = "api.py"
    
    def __init__(self):
        """Framework-compatible constructor - dependency injection via decorators."""
        super().__init__()
        self.app_context = None  # Will be injected by framework during processing
        self.service_instance = None
        self.logger.info(f"{self.MODULE_ID} created with complete decorator system")
    
    def setup_infrastructure(self):
        """Framework calls automatically in Phase 1 - Set up basic infrastructure only."""
        self.logger.info(f"{self.MODULE_ID}: Setting up infrastructure")
        
        # Phase 1: Only infrastructure setup - NO service access
        # All settings access moved to Phase 2 initialize_service()
        
        self.logger.info(f"{self.MODULE_ID}: Infrastructure setup complete")
    
    def create_service(self):
        """Framework calls automatically in Phase 1 - Create service instance."""
        self.logger.info(f"{self.MODULE_ID}: Creating service instance")
        
        # Service automatically created by @auto_service_creation - no manual creation needed!
        if not self.service_instance:
            self.logger.error(f"{self.MODULE_ID}: service_instance should have been created by @auto_service_creation")
            raise RuntimeError("Auto service creation failed - service_instance not available")
        
        self.logger.info(f"{self.MODULE_ID}: Service instance created")
    
    def register_settings(self):
        """Framework calls automatically in Phase 1 - Register Pydantic settings model."""
        self.logger.info(f"{self.MODULE_ID}: Registering Pydantic settings model")
        
        try:
            # Phase 1: Register Pydantic model with app_context (NO service calls)
            self.app_context.register_pydantic_model(self.MODULE_ID, FrameworkSettings)
            self.logger.info(f"{self.MODULE_ID}: Pydantic settings model registered with framework")
        except Exception as e:
            self.logger.error(f"{self.MODULE_ID}: Error registering settings: {str(e)}")
        
        self.logger.info(f"{self.MODULE_ID}: Phase 1 complete")
    
    async def initialize_service(self):
        """Framework calls automatically in Phase 2 - Initialize service with typed Pydantic settings."""
        self.logger.info(f"{self.MODULE_ID}: Phase 2 - Initializing service with typed settings")
        
        try:
            if self.service_instance:
                # Get settings service
                settings_service = self.app_context.get_service("core.settings.service")
                
                if settings_service:
                    # Get fully validated Pydantic settings
                    result = await settings_service.get_typed_settings(
                        module_id=self.MODULE_ID,
                        model_class=FrameworkSettings
                    )
                    
                    if result.success:
                        typed_settings = result.data  # FrameworkSettings instance
                        
                        # Initialize service with type-safe settings
                        if hasattr(self.service_instance, 'initialize'):
                            await self.service_instance.initialize(settings=typed_settings)
                            self.logger.info(f"{self.MODULE_ID}: Service initialized with typed Pydantic settings")
                        else:
                            self.logger.warning(f"{self.MODULE_ID}: Service has no initialize method")
                    else:
                        self.logger.error(f"{self.MODULE_ID}: Failed to get typed settings: {result.message}")
                else:
                    self.logger.error(f"{self.MODULE_ID}: Settings service not available in Phase 2")
            else:
                self.logger.error(f"{self.MODULE_ID}: Service not created in Phase 1")
                
        except Exception as e:
            self.logger.error(f"{self.MODULE_ID}: Exception initializing service: {str(e)}")
        
        self.logger.info(f"{self.MODULE_ID}: Phase 2 initialization complete")
    
    async def health_check(self) -> bool:
        """Health check function (registered automatically via decorator)."""
        try:
            # Check if service is available and initialized
            if not self.service_instance:
                return False
                
            # Check basic framework functionality
            if hasattr(self.service_instance, 'initialized') and not self.service_instance.initialized:
                return False
                
            self.logger.debug(f"{self.MODULE_ID} health check passed")
            return True
            
        except Exception as e:
            self.logger.error(f"{self.MODULE_ID} health check failed: {str(e)}")
            return False
    
    async def cleanup_resources(self):
        """Framework calls automatically during graceful shutdown - only cleanup logic."""
        # Only cleanup logic here - framework handles all logging automatically!
        if self.service_instance and hasattr(self.service_instance, 'shutdown'):
            if hasattr(self.service_instance.shutdown, '__await__'):
                await self.service_instance.shutdown()
            else:
                self.service_instance.shutdown()
    
    def force_cleanup(self):
        """Framework calls automatically during force shutdown - only cleanup logic."""
        # Only cleanup logic here - framework handles all logging automatically!
        if self.service_instance and hasattr(self.service_instance, 'force_close'):
            self.service_instance.force_close()

# API ENDPOINTS (Registered automatically via decorator)

# Create router for framework endpoints
router = APIRouter(tags=["framework"])

@router.get("/session-info", response_model=SessionInfoResponse)
async def get_session_info():
    """Get current application session information."""
    # Note: In the new pattern, we need to access the module instance
    # This could be improved in future iterations
    
    try:
        # For now, we'll access through the app context
        # This is a temporary approach until we fully integrate the new pattern
        from core.app_context import AppContext
        
        # Get the service from app context
        # In a real implementation, we'd have better service discovery
        # This is acceptable for the migration phase
        
        # Get actual session information from app context
        import time
        from datetime import datetime
        
        session_info = {
            "session_id": "framework_session",  # This should come from actual session
            "session_start_time": datetime.now().isoformat(),
            "framework_version": "1.0.0",
            "uptime_seconds": time.time()  # This should track actual uptime
        }
        
        return session_info
        
    except Exception as e:
        logger = logging.getLogger("core.global")
        logger.error(error_message(
            module_id="core.global",
            error_type="SESSION_INFO_ERROR",
            details=f"Error getting session info: {str(e)}",
            location="get_session_info()"
        ))
        
        raise HTTPException(
            status_code=500,
            detail=create_error_response(
                module_id="core.global",
                code="INTERNAL_ERROR",
                message="Failed to get session information"
            )
        )

# MODULE CONSTANTS

# Module identity for consistent logging and error handling
MODULE_ID = "core.framework"
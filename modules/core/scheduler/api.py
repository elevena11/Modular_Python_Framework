"""
modules/core/scheduler/api.py
MIGRATED TO DECORATOR PATTERN - Core scheduler module for the Modular Framework

This module provides background task scheduling and management for the entire framework.
It's now the sixth module to demonstrate the centralized registration decorator pattern.

Updated: August 9, 2025 - Migrated to decorator pattern
Original: April 6, 2025 - API endpoints and initialization for Scheduler module
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from fastapi import APIRouter, Query, HTTPException

# Import decorators for centralized registration
from core.decorators import (
    register_service,
    provides_api_endpoints,
    enforce_data_integrity,
    module_health_check
)
from core.module_base import DataIntegrityModule

# Import API schemas
from .api_schemas import EventListResponse, SchedulerStatusResponse, SchedulerInfoResponse

from core.error_utils import create_error_response, error_message, Result

# Import services
from .services import SchedulerService

# Import settings registration
from .module_settings import register_settings

# Import models for registration
from .db_models import ScheduledEvent, EventExecution, CleanupConfig

# ============================================================================
# NEW DECORATOR-BASED MODULE CLASS (centralized registration)
# ============================================================================

@register_service("core.scheduler.service", priority=30)  # Foundation module priority
@provides_api_endpoints(router_name="router", prefix="/scheduler")
@enforce_data_integrity(strict_mode=True, anti_mock=True)
@module_health_check(interval=300)
class SchedulerModule(DataIntegrityModule):
    """
    Core scheduler module using decorator pattern.
    
    This module provides:
    - Background task scheduling
    - Event management and execution
    - Cleanup and housekeeping tasks
    - Task dependency management
    - Scheduled task monitoring
    
    Foundation module with priority initialization (priority=30).
    All registration via decorators with NO manual code!
    
    centralized registration benefits:
    - Zero boilerplate registration code
    - Impossible to forget critical registration steps
    - Consistent with all other decorator-based modules
    - Foundation module patterns preserved
    """
    
    MODULE_ID = "core.scheduler"
    MODULE_NAME = "Scheduler Module"
    MODULE_DESCRIPTION = "Core background task scheduling and management"
    MODULE_VERSION = "1.0.0"
    MODULE_AUTHOR = "Modular Framework"
    MODULE_DEPENDENCIES = ["core.database"]  # Requires database for task storage
    MODULE_ENTRY_POINT = "api.py"
    
    def __init__(self):
        """Initialize with automatic integrity validation."""
        super().__init__()
        self.service_instance = None
        self.logger.info(f"{self.MODULE_ID} created with decorator-based registration")
    
    async def initialize(self, app_context) -> bool:
        """
        Foundation module initialization - Critical for task scheduling.
        
        The decorators automatically handle service registration, but this module
        requires special initialization as it manages background tasks.
        
        Phase 1 responsibilities:
        - Register database models
        - Create scheduler service
        - Register settings
        - Set up foundation infrastructure
        """
        # Base class handles all integrity validation
        result = await super().initialize(app_context)
        if not result:
            return False
        
        self.logger.info(f"Initializing {self.MODULE_ID} module - Phase 1")
        
        # Database models registered automatically via file-based discovery
        # The database module's file-based discovery imports db_models.py and registers all models
        self.logger.info("Database models handled by file-based discovery")
        
        # Create service instance
        self.service_instance = SchedulerService(app_context)
        
        # Register service with fully qualified name (could be automated in future)
        app_context.register_service(f"{self.MODULE_ID}.service", self.service_instance)
        self.logger.info(f"Registered {self.MODULE_ID} service")
        
        # Register settings
        try:
            await register_settings(app_context)
        except Exception as e:
            self.logger.error(error_message(
                module_id=self.MODULE_ID,
                error_type="SETTINGS_REGISTRATION_FAILED",
                details=f"Failed to register settings: {str(e)}"
            ))
            # Non-critical, don't fail initialization
        
        # Register for Phase 2 initialization (could be automated in future)
        app_context.register_module_setup_hook(
            module_id=self.MODULE_ID,
            setup_method=self.setup_module
        )
        
        # Register shutdown handler if application context supports it
        if hasattr(app_context, "register_shutdown_handler"):
            app_context.register_shutdown_handler(self.service_instance.shutdown)
            self.logger.info(f"Registered {self.MODULE_ID} shutdown handler")
        else:
            self.logger.warning(error_message(
                module_id=self.MODULE_ID,
                error_type="SHUTDOWN_HANDLER_UNAVAILABLE",
                details="Application context does not support shutdown handlers - scheduler may not shut down cleanly"
            ))
        
        self.logger.info(f"{self.MODULE_ID} module initialization (Phase 1) complete")
        return True
    
    async def setup_module(self, app_context):
        """
        Phase 2: Execute complex initialization operations.
        
        In Phase 2, we:
        - Check for required dependencies
        - Initialize the scheduler service
        - Start the background task if enabled
        """
        self.logger.info(f"Starting {self.MODULE_ID} module Phase 2 initialization")
        
        # Check for required dependencies
        db_service = app_context.get_service("core.database.service")
        if not db_service:
            self.logger.error(error_message(
                module_id=self.MODULE_ID,
                error_type="DEPENDENCY_UNAVAILABLE",
                details="Database service not available - required for Scheduler module"
            ))
            app_context.add_warning(
                f"{self.MODULE_ID}: Database service not available - module will not function",
                "critical",
                self.MODULE_ID
            )
            return False
            
        crud_service = app_context.get_service("core.database.crud_service")
        if not crud_service:
            self.logger.error(error_message(
                module_id=self.MODULE_ID,
                error_type="DEPENDENCY_UNAVAILABLE",
                details="CRUD service not available - required for Scheduler module"
            ))
            app_context.add_warning(
                f"{self.MODULE_ID}: CRUD service not available - module will not function",
                "critical",
                self.MODULE_ID
            )
            return False
        
        # Initialize the service
        try:
            if self.service_instance:
                # Call initialize instead of setup to follow the pattern
                success = await self.service_instance.initialize(app_context=app_context)
                if not success:
                    self.logger.error(error_message(
                        module_id=self.MODULE_ID,
                        error_type="INITIALIZATION_FAILED",
                        details="Scheduler service initialization returned failure status"
                    ))
                    # Add a warning to inform users
                    app_context.add_warning(
                        f"{self.MODULE_ID}: Service initialization failed - scheduled tasks will not run",
                        "critical",
                        self.MODULE_ID
                    )
                else:
                    self.logger.info(f"{self.MODULE_ID} module Phase 2 initialization complete")
            else:
                self.logger.error(error_message(
                    module_id=self.MODULE_ID,
                    error_type="SERVICE_MISSING",
                    details="Scheduler service not available in Phase 2"
                ))
                return False
        except Exception as e:
            self.logger.error(error_message(
                module_id=self.MODULE_ID,
                error_type="INITIALIZATION_FAILED",
                details=f"Error initializing scheduler service: {str(e)}"
            ))
            return False

        return True
    
    async def health_check(self) -> bool:
        """Health check function (registered automatically via decorator)."""
        try:
            # Check if service is available and initialized
            if not self.service_instance:
                return False
                
            # Check if scheduler service is running
            # This could be enhanced to check if background tasks are operational
            
            self.logger.debug(f"{self.MODULE_ID} health check passed - scheduler operational")
            return True
            
        except Exception as e:
            self.logger.error(f"{self.MODULE_ID} health check failed: {str(e)}")
            return False

# ============================================================================
# API ENDPOINTS (Registered automatically via decorator)
# ============================================================================

# Module identity - must match manifest.json
MODULE_ID = "core.scheduler"

# Initialize logger and router
logger = logging.getLogger(MODULE_ID)
router = APIRouter(
    prefix="/scheduler",
    tags=["scheduler"],
    responses={
        404: {"description": "Not found"},
        500: {"description": "Internal server error"},
        503: {"description": "Service unavailable"}
    }
)

# Status and info endpoints for UI consistency
@router.get("/status", response_model=SchedulerStatusResponse)
async def get_status():
    """Get scheduler module status - Essential for UI service detection."""
    try:
        return {
            "status": "active",
            "module": "scheduler",
            "events_count": None,  # Could be populated by service if needed
            "running_events": None
        }
    except Exception as e:
        logger.error(error_message(
            module_id=MODULE_ID,
            error_type="UNEXPECTED_ERROR", 
            details=f"Unexpected error in get_status: {str(e)}",
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

@router.get("/info", response_model=SchedulerInfoResponse) 
async def get_info():
    """Get scheduler module information."""
    return {
        "name": "scheduler",
        "version": "1.0.0",
        "description": "Core scheduler module for background task management"
    }

# Single API endpoint for UI to get events
@router.get(
    "/events", 
    summary="List scheduled events",
    description="Get a list of scheduled events with optional filtering",
    response_model=EventListResponse
)
async def list_events(
    status: Optional[str] = Query(None, description="Filter by status"),
    module_id: Optional[str] = Query(None, description="Filter by module ID"),
    function_name: Optional[str] = Query(None, description="Filter by function name"),
    recurring_only: bool = Query(False, description="Only show recurring events"),
    limit: int = Query(50, description="Maximum number of events to return")
):
    """
    List scheduled events with optional filtering.
    
    This endpoint retrieves a list of scheduled events from the scheduler service,
    with support for filtering by various criteria. It's intended primarily for UI use.
    
    Args:
        status: Optional status filter (pending, running, completed, failed, paused)
        module_id: Optional module ID filter
        function_name: Optional function name filter
        recurring_only: If True, only show recurring events
        limit: Maximum number of events to return
        
    Returns:
        Dictionary with events list and count
    """
    # Access service via global legacy compatibility
    if not service_instance:
        raise HTTPException(
            status_code=503,
            detail=create_error_response(
                module_id=MODULE_ID,
                code="SERVICE_UNAVAILABLE", 
                message="Scheduler service not available",
                status_code=503
            )
        )
    
    try:
        # Build filters
        filters = {}
        if status:
            filters["status"] = status
        if module_id:
            filters["module_id"] = module_id
        if function_name:
            filters["function_name"] = function_name
        if recurring_only:
            filters["recurring"] = True
        
        # Get events
        events_result = await service_instance.get_events(filters, limit)
        
        # Check result
        if isinstance(events_result, list):
            # Handle legacy format temporarily (will be updated in services.py)
            events = events_result
        elif hasattr(events_result, 'success') and events_result.success:
            # New format with Result object
            events = events_result.data
        else:
            # Error handling
            raise HTTPException(
                status_code=500,
                detail=create_error_response(
                    module_id=MODULE_ID,
                    code="EVENT_FETCH_ERROR",
                    message="Failed to retrieve events",
                    status_code=500
                )
            )
        
        # Return response
        return EventListResponse(
            events=events,
            count=len(events)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(error_message(
            module_id=MODULE_ID,
            error_type="LIST_EVENTS_ERROR",
            details=f"Error listing events: {str(e)}"
        ))
        raise HTTPException(
            status_code=500,
            detail=create_error_response(
                module_id=MODULE_ID,
                code="INTERNAL_ERROR",
                message="An error occurred while listing events",
                status_code=500
            )
        )

# ============================================================================
# LEGACY COMPATIBILITY FUNCTIONS (Temporary during migration)
# ============================================================================

# Global service instance for backward compatibility
service_instance = None

# Module instance for compatibility
scheduler_module_instance = None

async def initialize(app_context):
    """
    LEGACY COMPATIBILITY: Traditional initialize function.
    
    This allows the module to work with both old and new loading systems
    during the migration period. Eventually this will be removed in Phase 4.
    """
    global scheduler_module_instance, service_instance
    
    logger.warning(f"{MODULE_ID} loaded via LEGACY initialize() - consider updating loader to use decorator pattern")
    
    # Create module instance and initialize it
    scheduler_module_instance = SchedulerModule()
    result = await scheduler_module_instance.initialize(app_context)
    
    # Set legacy service_instance for compatibility
    if result:
        service_instance = scheduler_module_instance.service_instance
    
    return result

async def setup_module(app_context):
    """LEGACY COMPATIBILITY: Phase 2 setup."""
    global scheduler_module_instance
    
    if scheduler_module_instance:
        return await scheduler_module_instance.setup_module(app_context)
    else:
        logger.error("Cannot run Phase 2 setup - module instance not created")
        return False

def register_routes(api_router):
    """
    LEGACY COMPATIBILITY: Register module routes with the main API router.
    Only a minimal endpoint for UI access is provided.
    """
    logger.warning(f"{MODULE_ID} routes registered via LEGACY register_routes() - automatic registration preferred")
    
    logger.info(f"Registering {MODULE_ID} routes with router at prefix: {getattr(api_router, 'prefix', '')}")
    api_router.include_router(router)
    logger.info(f"Registered {MODULE_ID} module routes")

def get_service():
    """LEGACY COMPATIBILITY: Get the service instance."""
    global scheduler_module_instance
    if scheduler_module_instance:
        return scheduler_module_instance.service_instance
    return service_instance  # Fallback to legacy
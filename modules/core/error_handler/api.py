"""
modules/core/error_handler/api.py
MIGRATED TO DECORATOR PATTERN - Core error handling module for the Modular Framework

This module provides centralized error handling, error registry, and error utilities for the entire framework.
It's now the fifth module to demonstrate the centralized registration decorator pattern.

Updated: August 9, 2025 - Migrated to decorator pattern
Original: April 6, 2025 - Module entry point for Error_Handler
"""

import os
import logging
from typing import Dict, List, Any, Optional

# Import complete decorator system for centralized registration
from core.decorators import (
    register_service,
    ServiceMethod,
    ServiceParam,
    ServiceReturn,
    ServiceExample,
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

# CIRCULAR DEPENDENCY PREVENTION: Do not import from core.error_utils!
# Error_handler processes files created by error_utils - importing would create loops
# Use local Result class and direct logging instead

# Local Result class to avoid circular dependency
class Result:
    """Local Result class to avoid importing from core.error_utils"""
    def __init__(self, success=False, data=None, error=None):
        self.success = success
        self.data = data
        self.error = error or {}
    
    @classmethod
    def success(cls, data=None):
        return cls(success=True, data=data)
    
    @classmethod 
    def error(cls, code, message, details=None):
        return cls(success=False, error={
            "code": code,
            "message": message,
            "details": details or {}
        })

# Import the registry service
from .services import ErrorRegistry
from .settings import ErrorHandlerSettings

# ============================================================================
# NEW DECORATOR-BASED MODULE CLASS (centralized registration)
# ============================================================================

# v3.0.0 Complete Decorator-Based Registration (eliminates all manual patterns)
@register_service("core.error_handler.service", methods=[
    ServiceMethod(
        name="initialize",
        description="Initialize error registry with optional settings",
        params=[
            ServiceParam("app_context", Any, required=False, description="Optional application context"),
            ServiceParam("settings", Dict[str, Any], required=False, description="Optional pre-loaded settings")
        ],
        returns=ServiceReturn(bool, "True if initialization successful"),
        examples=[
            ServiceExample("initialize()", "True"),
            ServiceExample("initialize(settings={'log_processing_interval': 60})", "True")
        ],
        tags=["phase2", "initialization"]
    ),
    ServiceMethod(
        name="process_error_logs",
        description="Process error logs from JSONL files and update registry",
        params=[
            ServiceParam("params", Dict[str, Any], required=False, description="Optional processing parameters")
        ],
        returns=ServiceReturn("Result", "Result with processing statistics"),
        examples=[
            ServiceExample("process_error_logs()", "Result.success(data={'processed': 15, 'new_errors': 3})"),
            ServiceExample("process_error_logs({'force_full_scan': True})", "Result.success(...)")
        ],
        tags=["processing", "logs"]
    ),
    ServiceMethod(
        name="search_errors",
        description="Search for errors by error code or pattern",
        params=[
            ServiceParam("query", str, required=True, description="Search query for error codes"),
            ServiceParam("limit", int, required=False, default=10, description="Maximum number of results"),
            ServiceParam("params", Dict[str, Any], required=False, description="Optional search parameters")
        ],
        returns=ServiceReturn("Result", "Result with matching error codes"),
        examples=[
            ServiceExample("search_errors('DATABASE_ERROR')", "Result.success(data=[{'code': 'DATABASE_ERROR', ...}])"),
            ServiceExample("search_errors('API_', limit=5)", "Result.success(data=[...])")
        ],
        tags=["search", "errors"]
    ),
    ServiceMethod(
        name="get_error_document",
        description="Get detailed documentation for a specific error code",
        params=[
            ServiceParam("error_code", str, required=True, description="Error code to get documentation for"),
            ServiceParam("params", Dict[str, Any], required=False, description="Optional retrieval parameters")
        ],
        returns=ServiceReturn("Result", "Result with error documentation"),
        examples=[
            ServiceExample("get_error_document('DATABASE_CONNECTION_FAILED')", "Result.success(data={'description': '...', 'category': 'database'})"),
        ],
        tags=["documentation", "errors"]
    ),
    ServiceMethod(
        name="get_error_examples",
        description="Get recent examples of a specific error occurrence",
        params=[
            ServiceParam("error_code", str, required=True, description="Error code to get examples for"),
            ServiceParam("limit", int, required=False, default=5, description="Maximum number of examples"),
            ServiceParam("params", Dict[str, Any], required=False, description="Optional retrieval parameters")
        ],
        returns=ServiceReturn("Result", "Result with error examples"),
        examples=[
            ServiceExample("get_error_examples('API_TIMEOUT', limit=3)", "Result.success(data=[{'timestamp': '...', 'context': '...'}, ...])"),
        ],
        tags=["examples", "errors"]
    ),
    ServiceMethod(
        name="update_error_document",
        description="Update documentation for an error code",
        params=[
            ServiceParam("error_code", str, required=True, description="Error code to update"),
            ServiceParam("data", Dict[str, Any], required=True, description="Documentation updates to apply"),
            ServiceParam("params", Dict[str, Any], required=False, description="Optional update parameters")
        ],
        returns=ServiceReturn("Result", "Result indicating update success"),
        examples=[
            ServiceExample("update_error_document('API_ERROR', {'description': 'New description'})", "Result.success(data={'updated': True})"),
        ],
        tags=["update", "documentation"]
    ),
    ServiceMethod(
        name="get_prioritized_errors",
        description="Get errors ranked by priority score for attention",
        params=[
            ServiceParam("limit", int, required=False, default=10, description="Maximum number of errors to return"),
            ServiceParam("params", Dict[str, Any], required=False, description="Optional priority parameters")
        ],
        returns=ServiceReturn("Result", "Result with prioritized error list"),
        examples=[
            ServiceExample("get_prioritized_errors(5)", "Result.success(data=[{'code': 'CRITICAL_ERROR', 'score': 95}, ...])"),
        ],
        tags=["priority", "analysis"]
    ),
    ServiceMethod(
        name="calculate_priority_scores",
        description="Calculate priority scores for all known errors",
        params=[
            ServiceParam("params", Dict[str, Any], required=False, description="Optional calculation parameters")
        ],
        returns=ServiceReturn("Result", "Result with calculation results"),
        examples=[
            ServiceExample("calculate_priority_scores()", "Result.success(data={'calculated': 25, 'updated': 18})"),
        ],
        tags=["priority", "calculation", "analysis"]
    )
], priority=20)  # Foundation module priority
@inject_dependencies("app_context")
@auto_service_creation(service_class="ErrorRegistry")
@initialization_sequence("setup_infrastructure", "create_registry", phase="phase1")
@phase2_operations("initialize_registry", dependencies=["core.settings.service"], priority=30)
@enforce_data_integrity(strict_mode=True, anti_mock=True)
@module_health_check(interval=300)
@graceful_shutdown(method="cleanup_resources", timeout=30, priority=20)
@force_shutdown(method="force_cleanup", timeout=5)
class ErrorHandlerModule(DataIntegrityModule):
    """
    Core error_handler module using decorator pattern.
    
    This module provides:
    - Centralized error handling utilities
    - Error registry and documentation
    - Error code management
    - Direct-import utilities for all modules
    - Error logging and tracking
    
    Foundation module with priority initialization (priority=20).
    Provides utilities via direct import pattern.
    All registration via decorators with NO manual code!
    
    centralized registration benefits:
    - Zero boilerplate registration code
    - Impossible to forget critical registration steps
    - Consistent with all other decorator-based modules
    - Foundation module patterns preserved
    """
    
    MODULE_ID = "core.error_handler"
    MODULE_NAME = "Error_Handler Module"
    MODULE_DESCRIPTION = "Core error handling and error registry"
    MODULE_VERSION = "1.1.0"
    MODULE_AUTHOR = "Modular Framework"
    MODULE_DEPENDENCIES = ["core.settings"]  # Needs settings service for typed configuration
    MODULE_ENTRY_POINT = "api.py"
    
    def __init__(self):
        """Framework-compatible constructor - dependency injection via decorators."""
        super().__init__()
        self.app_context = None  # Will be injected by framework during processing
        self.service_instance = None
        self.logger.info(f"{self.MODULE_ID} created with complete decorator system")
    
    def setup_infrastructure(self):
        """Framework calls automatically in Phase 1 - Set up basic infrastructure."""
        self.logger.info(f"{self.MODULE_ID}: Setting up infrastructure")
        
        # Create error logs directory
        error_logs_dir = os.path.join(self.app_context.config.DATA_DIR, "error_logs")
        os.makedirs(error_logs_dir, exist_ok=True)
        
        self.logger.info(f"{self.MODULE_ID}: Infrastructure setup complete")
    
    def create_registry(self):
        """Framework calls automatically in Phase 1 - Create error registry service."""
        # Service automatically created by @auto_service_creation - no manual creation needed!
        if not self.service_instance:
            self.logger.error(f"{self.MODULE_ID}: service_instance should have been created by @auto_service_creation")
            raise RuntimeError("Auto service creation failed - service_instance not available")
        
        # Use the service created by decorator
        self.error_registry = self.service_instance
        
        # Register Pydantic settings model with app_context (Phase 1)
        try:
            self.app_context.register_pydantic_model(self.MODULE_ID, ErrorHandlerSettings)
            self.logger.info(f"{self.MODULE_ID}: Pydantic settings model registered with framework")
        except Exception as e:
            self.logger.warning(f"{self.MODULE_ID}: Error registering Pydantic model: {e}")
        
        self.logger.info(f"{self.MODULE_ID}: Registry created and Phase 1 complete")
    
    async def initialize_registry(self):
        """Framework calls automatically in Phase 2 - Initialize error registry with settings.
        app_context available via self.app_context (injected by decorators)."""
        self.logger.info(f"{self.MODULE_ID}: Phase 2 - Initializing registry")
        
        # Initialize the registry
        if self.service_instance:
            try:
                # Load typed settings from settings
                settings = None
                try:
                    settings_service = self.app_context.get_service("core.settings.service")
                    if settings_service:
                        result = await settings_service.get_typed_settings(self.MODULE_ID, ErrorHandlerSettings, "settings")
                        if result.success:
                            settings = result.data  # This is a validated ErrorHandlerSettings instance
                            self.logger.info(f"{self.MODULE_ID}: Loaded typed settings from settings")
                        else:
                            self.logger.warning(f"{self.MODULE_ID}: Failed to get typed settings: {result.error}")
                    else:
                        self.logger.warning(f"{self.MODULE_ID}: settings service not available")
                except Exception as e:
                    self.logger.warning(f"{self.MODULE_ID}: Error loading typed settings: {e}")
                
                # Clean Pydantic-only implementation
                if settings is None:
                    self.logger.warning(f"{self.MODULE_ID}: No typed settings available")
                
                # Initialize the registry with settings
                if hasattr(self.service_instance, 'initialize'):
                    import inspect
                    if inspect.iscoroutinefunction(self.service_instance.initialize):
                        # Async initialize
                        initialized = await self.service_instance.initialize(
                            app_context=self.app_context,
                            settings=settings
                        )
                    else:
                        # Sync initialize
                        initialized = self.service_instance.initialize(
                            app_context=self.app_context,
                            settings=settings
                        )
                    
                    if initialized:
                        self.logger.info(f"{self.MODULE_ID}: Registry initialized successfully")
                    else:
                        self.logger.error(f"Error_handler: Failed to initialize error registry")
                else:
                    self.logger.info(f"{self.MODULE_ID}: Registry already initialized")
                    
            except Exception as e:
                # Direct logging instead of error_message() in error_handler to prevent loops
                self.logger.error(f"Error_handler: Exception initializing registry: {str(e)}")
        else:
            self.logger.warning(f"Error_handler: Registry not available - knowledge building features disabled")
        
        self.logger.info(f"{self.MODULE_ID}: Phase 2 initialization complete")
    
    async def health_check(self) -> bool:
        """Health check function (registered automatically via decorator)."""
        try:
            # Check if error registry is available
            if not self.service_instance:
                return False
                
            # Check basic error handling functionality
            test_result = Result.success(data="health_check")
            
            self.logger.debug(f"{self.MODULE_ID} health check passed - error handling operational")
            return True
            
        except Exception as e:
            self.logger.error(f"{self.MODULE_ID} health check failed: {str(e)}")
            return False
    
    async def cleanup_resources(self):
        """Framework calls automatically during graceful shutdown - only cleanup logic."""
        # Only cleanup logic here - framework handles all logging automatically!
        if self.error_registry and hasattr(self.error_registry, 'shutdown'):
            if hasattr(self.error_registry.shutdown, '__await__'):
                await self.error_registry.shutdown()
            else:
                self.error_registry.shutdown()
    
    def force_cleanup(self):
        """Framework calls automatically during force shutdown - only cleanup logic.""" 
        # Only cleanup logic here - framework handles all logging automatically!
        if self.error_registry and hasattr(self.error_registry, 'force_close'):
            self.error_registry.force_close()

# ============================================================================
# MODULE CONSTANTS
# ============================================================================

# Module identity
MODULE_ID = "core.error_handler"
logger = logging.getLogger(MODULE_ID)

# ============================================================================
# HELPER FUNCTIONS FOR MODULES
# ============================================================================

async def search_errors(app_context, query: str, limit: int = 10):
    """
    Search for errors by error code.
    
    Args:
        app_context: Application context
        query: Search query for error code
        limit: Maximum number of results to return
        
    Returns:
        Result object with search results and metadata
    """
    error_registry = app_context.get_service(f"{MODULE_ID}.service")
    if not error_registry or not error_registry.initialized:
        return Result.error(
            code="SERVICE_UNAVAILABLE",
            message="ErrorRegistry service not available"
        )
    
    try:
        # Search for error codes
        search_result = await error_registry.search_errors(query, limit)
        if not search_result.success:
            return search_result
            
        error_codes = search_result.data
        
        # For each error, get examples
        for error in error_codes:
            examples_result = await error_registry.get_error_examples(error["code"], limit=3)
            if examples_result.success:
                error["examples"] = examples_result.data
            else:
                error["examples"] = []
        
        return Result.success(data={
            "query": query,
            "count": len(error_codes),
            "results": error_codes
        })
    except Exception as e:
        # CRITICAL: Do not use # Direct logging instead of error_message() in error_handler to prevent loops
        logger.error(f"Error_handler: Exception searching for errors: {str(e)}")
        return Result.error(
            code="SEARCH_ERROR",
            message=f"Exception searching for errors: {str(e)}"
        )

async def get_error_documentation(app_context, error_code: str):
    """
    Get documentation for an error code.
    
    Args:
        app_context: Application context
        error_code: The error code to get documentation for
        
    Returns:
        Result object with documentation and examples
    """
    error_registry = app_context.get_service(f"{MODULE_ID}.service")
    if not error_registry or not error_registry.initialized:
        return Result.error(
            code="SERVICE_UNAVAILABLE",
            message="ErrorRegistry service not available"
        )
    
    try:
        # Get documentation
        document_result = await error_registry.get_error_document(error_code)
        if not document_result.success:
            return document_result
            
        document = document_result.data
        
        # Get examples
        examples_result = await error_registry.get_error_examples(error_code, limit=5)
        examples = examples_result.data if examples_result.success else []
        
        return Result.success(data={
            "error_code": error_code,
            "document": document,
            "examples": examples
        })
    except Exception as e:
        # CRITICAL: Do not use # Direct logging instead of error_message() in error_handler to prevent loops
        logger.error(f"Error_handler: Exception getting documentation: {str(e)}")
        return Result.error(
            code="DOCUMENTATION_ERROR",
            message=f"Failed to get error documentation: {str(e)}"
        )

async def update_error_documentation(app_context, error_code: str, data: dict):
    """
    Update documentation for an error code.
    
    Args:
        app_context: Application context
        error_code: The error code to update documentation for
        data: Documentation data to update
        
    Returns:
        Result object indicating success or failure
    """
    error_registry = app_context.get_service(f"{MODULE_ID}.service")
    if not error_registry or not error_registry.initialized:
        return Result.error(
            code="SERVICE_UNAVAILABLE",
            message="ErrorRegistry service not available"
        )
    
    try:
        # Update documentation
        result = await error_registry.update_error_document(error_code, data)
        if not result.success:
            return result
        
        return Result.success(data={
            "message": f"Documentation updated for: {error_code}"
        })
    except Exception as e:
        # CRITICAL: Do not use # Direct logging instead of error_message() in error_handler to prevent loops
        logger.error(f"Error_handler: Exception updating documentation: {str(e)}")
        return Result.error(
            code="UPDATE_ERROR",
            message=f"Failed to update error documentation: {str(e)}"
        )
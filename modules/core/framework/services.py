"""
modules/core/framework/services.py
Updated: April 4, 2025
Services for framework module
"""

import logging
from typing import Dict, Any, Optional

from core.error_utils import Result, error_message
from .settings import FrameworkSettings

# Define MODULE_ID constant
MODULE_ID = "core.framework" # This will become core.framework when loaded from modules/core/framework/

# Logger setup
logger = logging.getLogger(MODULE_ID)

class FrameworkService:
    """
    Service for framework concerns.
    Primarily provides access to framework settings and framework-wide utilities.
    """
    
    def __init__(self, app_context):
        """Initialize the framework service."""
        self.app_context = app_context
        self.logger = logger
        self.initialized = False
        self.settings = None  # Typed Pydantic settings

        self.logger.info(f"{MODULE_ID} service instance created (pre-Phase 2)")
    
    async def initialize(self, settings: FrameworkSettings = None) -> bool:
        """
        Phase 2 initialization with typed Pydantic settings.
        
        Args:
            settings: Validated FrameworkSettings instance
            
        Returns:
            bool: True if initialization successful
        """
        if self.initialized:
            return True
            
        self.logger.info(f"Initializing {MODULE_ID} service with typed settings")
        
        try:
            if settings:
                # Store the Pydantic instance for type-safe access
                self.settings = settings

                self.logger.info(f"Framework configured: {settings.app_title} v{settings.app_version} "
                               f"({settings.environment} mode)")
                self.logger.info(f"API available at: {settings.api_base_url}")

                if settings.debug_mode:
                    self.logger.debug(f"Debug mode enabled with {settings.log_level} logging")
            else:
                self.logger.warning(f"{MODULE_ID}: No settings provided, using defaults")
                self.settings = FrameworkSettings()  # Use defaults
            
            # Mark as initialized
            self.initialized = True
            self.logger.info(f"{MODULE_ID} service initialization complete")
            return True
            
        except Exception as e:
            self.logger.error(error_message(
                module_id=MODULE_ID,
                error_type="INIT_ERROR",
                details=f"Error during service initialization: {str(e)}"
            ))
            return False

    def get_typed_settings(self) -> Result:
        """
        Get the current typed Pydantic settings.
        
        Returns:
            Result: Success with FrameworkSettings instance or error
        """
        # Check initialization
        if not self.initialized:
            return Result.error(
                code=f"{MODULE_ID}_SERVICE_NOT_INITIALIZED",
                message=f"{MODULE_ID} service not initialized"
            )
            
        try:
            return Result.success(data=self.settings)
        except Exception as e:
            self.logger.error(error_message(
                module_id=MODULE_ID,
                error_type="TYPED_SETTINGS_ERROR",
                details=f"Error retrieving typed settings: {str(e)}"
            ))
            
            return Result.error(
                code=f"{MODULE_ID}_TYPED_SETTINGS_ERROR",
                message="Failed to retrieve typed settings",
                details={"error": str(e)}
            )
    
    def get_active_modules(self) -> Result:
        """
        Get information about currently active/initialized modules from the module processor.

        Returns:
            Result: Success with active modules data or error
        """
        # Check initialization
        if not self.initialized:
            return Result.error(
                code=f"{MODULE_ID}_SERVICE_NOT_INITIALIZED",
                message=f"{MODULE_ID} service not initialized"
            )

        try:
            # Access the module manager and processor through app_context
            if hasattr(self.app_context, 'module_manager') and self.app_context.module_manager:
                module_manager = self.app_context.module_manager
                if hasattr(module_manager, 'processor') and module_manager.processor:
                    processor = module_manager.processor

                    # Get runtime information from the processor
                    runtime_info = processor.get_all_runtime_info()

                    # Convert processed_modules to a more user-friendly format
                    active_modules = {}
                    for module_id, module_data in processor.processed_modules.items():
                        active_modules[module_id] = {
                            "id": module_id,
                            "name": module_id.replace('.', ' ').title(),
                            "status": "active",  # All processed modules are active
                            "version": module_data.get('module_version', '1.0.0'),
                            "description": module_data.get('module_description', f"Active {module_id} module"),
                            "initialization_time": module_data.get('initialization_time'),
                            "services": list(module_data.get('runtime_info', {}).get('active_services', {}).keys()),
                            "phase1_complete": len(module_data.get('initialization_sequences', {}).get('phase1', [])) > 0,
                            "phase2_complete": 'phase2_operations' in module_data
                        }

                    return Result.success(data={
                        "modules": active_modules,
                        "total_modules": len(active_modules),
                        "system_summary": runtime_info.get('system_summary', {}),
                        "last_updated": runtime_info.get('system_summary', {}).get('last_updated')
                    })
                else:
                    return Result.error(
                        code=f"{MODULE_ID}_PROCESSOR_NOT_AVAILABLE",
                        message="Module processor not available"
                    )
            else:
                return Result.error(
                    code=f"{MODULE_ID}_MODULE_MANAGER_NOT_AVAILABLE",
                    message="Module manager not available"
                )

        except Exception as e:
            self.logger.error(error_message(
                module_id=MODULE_ID,
                error_type="ACTIVE_MODULES_ERROR",
                details=f"Error retrieving active modules: {str(e)}",
                location="get_active_modules()"
            ))

            return Result.error(
                code=f"{MODULE_ID}_ACTIVE_MODULES_ERROR",
                message="Failed to retrieve active modules",
                details={"error": str(e)}
            )

    async def cleanup_resources(self):
        """
        Graceful resource cleanup - logging handled by decorator.
        Called during normal application shutdown via @graceful_shutdown decorator.
        """
        # Framework service cleanup
        self.settings = None
        self.initialized = False
    
    def force_cleanup(self):
        """
        Force cleanup of resources - logging handled by decorator.
        Called during emergency shutdown via @force_shutdown decorator.
        """
        # Force cleanup - clear all state
        try:
            self.settings = None
        except Exception:
            pass
        self.initialized = False

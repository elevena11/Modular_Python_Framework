"""
modules/core/settings/services.py
Updated: April 5, 2025
Main service composition and organization for settings module
"""

import logging
import os
from typing import Dict, Any, Optional, Union

from core.error_utils import error_message, Result

# Import from local directory structure
# Make sure to import these services from their refactored locations
from .service_components.validation_service import ValidationService, ValidationError
from .service_components.env_service import EnvironmentService
from .service_components.core_service import CoreSettingsService
from .storage.file_storage import FileStorageService
from .storage.db_storage import DatabaseStorageService
from .backup.backup_service import BackupService

# Define MODULE_ID matching manifest.json at the top of the file
MODULE_ID = "core.settings"
# Use MODULE_ID directly for the logger name
logger = logging.getLogger(MODULE_ID)

class SettingsService(CoreSettingsService):
    """
    Service for managing module settings with a hierarchical approach:
    1. Environment variables (highest priority)
    2. Client configuration (user overrides)
    3. Settings.json (module defaults)
    
    Features:
    - Settings validation
    - UI metadata for automatic UI generation
    - Settings migration between versions
    - Database-backed backup functionality
    
    This service composes specialized services for validation, storage, etc.
    """
    
    def __init__(self, app_context):
        """
        Initialize the settings service.
        
        This main service delegates to specialized services:
        - EnvironmentService: Handles environment variable integration
        - ValidationService: Validates settings against schemas
        - FileStorageService: Handles file-based storage
        - DatabaseStorageService: Handles database operations
        - BackupService: Manages backups and restoration
        
        Args:
            app_context: Application context
        """
        # Initialize paths
        self.settings_file = os.path.join(app_context.config.DATA_DIR, "settings.json")
        self.client_config_file = os.path.join(app_context.config.DATA_DIR, "client_config.json")
        self.metadata_file = os.path.join(app_context.config.DATA_DIR, "settings_metadata.json")
        
        # Initialize specialized services
        validation_service = ValidationService()
        env_service = EnvironmentService()
        file_storage = FileStorageService(
            self.settings_file, 
            self.client_config_file, 
            self.metadata_file
        )
        # NEW PATTERN: Create database storage service without services first
        # Services will be provided during initialization by parent module
        db_storage = DatabaseStorageService(app_context)
        backup_service = BackupService(app_context, file_storage, db_storage)
        
        # Pass services to the core settings service
        super().__init__(
            app_context=app_context,
            validation_service=validation_service,
            env_service=env_service,
            file_storage=file_storage,
            db_storage=db_storage,
            backup_service=backup_service
        )
        
        logger.info(f"{MODULE_ID} service created (pre-Phase 2)")

    async def cleanup_resources(self):
        """
        Graceful resource cleanup - logging handled by decorator.
        Called during normal application shutdown via @graceful_shutdown decorator.
        """
        # Delegate to core service shutdown logic
        await super().shutdown()
    
    def force_cleanup(self):
        """
        Force cleanup of resources - logging handled by decorator.
        Called during emergency shutdown via @force_shutdown decorator.
        """
        # Force cleanup - clear state immediately
        try:
            # Stop all background tasks if core service has them
            if hasattr(super(), '_background_tasks'):
                for task in super()._background_tasks:
                    if not task.done():
                        task.cancel()
        except Exception:
            pass  # Ignore errors during force cleanup
        
        # Force mark as not initialized
        try:
            if hasattr(super(), 'initialized'):
                super().initialized = False
        except Exception:
            pass

# Re-export ValidationError so it can be caught by API layer
# This maintains backward compatibility with existing code
__all__ = ['SettingsService', 'ValidationError']

"""
modules/core/settings/services/core_service.py
Updated: April 5, 2025
Core settings service implementation following the Hybrid Service Pattern
"""

import copy
import logging
import asyncio
import os
import traceback
from datetime import datetime
from typing import Dict, List, Any, Optional, Union, Callable, Type

from core.error_utils import error_message, Result

from ..utils.error_helpers import handle_operation, handle_result_operation, check_initialization

# Define component identity
MODULE_ID = "core.settings"
COMPONENT_ID = f"{MODULE_ID}.core"
# Use component ID for the logger
logger = logging.getLogger(COMPONENT_ID)

class CoreSettingsService:
    """
    Core service for managing settings with component delegation.
    
    This service coordinates operations between specialized services
    for validation, storage, environment variables, and backups.
    """
    
    def __init__(self, 
                app_context, 
                validation_service, 
                env_service, 
                file_storage, 
                db_storage, 
                backup_service):
        """
        Initialize the core settings service.
        
        Args:
            app_context: Application context
            validation_service: Service for validation
            env_service: Service for environment variables
            file_storage: Service for file-based storage
            db_storage: Service for database storage
            backup_service: Service for backups
        """
        self.app_context = app_context
        self.validation_service = validation_service
        self.env_service = env_service
        self.file_storage = file_storage
        self.db_storage = db_storage
        self.backup_service = backup_service
        
        # Initialize data structures
        self.settings = {}
        self.client_config = {}
        self.metadata = {}
        
        # Set initialized flag using the standard name "initialized"
        self.initialized = False
        
        # Track background tasks for proper shutdown
        self._background_tasks = []
        
        logger.info(f"{COMPONENT_ID} service created (pre-Phase 2)")
    
    async def _ensure_database_ready(self) -> bool:
        """Ensure database service is ready for complex operations."""
        db_service = self.app_context.get_service("core.database.service")
        if not (db_service and db_service.is_initialized()):
            logger.debug("Database service not ready for operations")
            return False
        return True
    
    def _ensure_module_manager_ready(self) -> bool:
        """Ensure module manager has completed discovery."""
        return (hasattr(self.app_context, 'module_manager') and 
                self.app_context.module_manager and 
                getattr(self.app_context.module_manager, 'modules', {}))  # Check if modules are loaded
    
    def _resolve_module_version(self, module_id: str) -> tuple[str, str]:
        """Resolve module version from available sources."""
        # Special case for global settings
        if module_id == "global":
            return "global-settings", "global_type"
        
        if not self._ensure_module_manager_ready():
            return "unknown", "loader_not_ready"
        
        if module_id not in self.app_context.module_manager.modules:
            return "unknown", "module_not_found"
        
        module_info = self.app_context.module_manager.modules[module_id]
        
        # v3.0.0 modules: Check for MODULE_VERSION constant on module class
        if hasattr(module_info.class_obj, "MODULE_VERSION"):
            version = module_info.class_obj.MODULE_VERSION
            if version and isinstance(version, str):
                return version, "module_constant"
        
        # For new module system, we don't have manifest data - return unknown
        return "unknown", "version_missing"

    async def initialize(self, app_context=None, settings=None, database_service=None, crud_service=None):
        """
        Phase 2 initialization - Load settings and set up complex state.
        
        NEW PATTERN: Accept database services from parent module that acquired
        them via @require_services decorator.
        
        Args:
            app_context: Optional application context (if different from constructor)
            settings: Optional pre-loaded settings (unused for this service)
            database_service: Database service from parent module (@require_services)
            crud_service: CRUD service from parent module (@require_services)
            
        Returns:
            bool: True if initialization successful, False otherwise
        """
        # Skip if already initialized
        if self.initialized:
            return True
            
        if app_context:
            self.app_context = app_context
        
        logger.info(f"Initializing {COMPONENT_ID} service")
        
        try:
            # Initialize components first
            await self.validation_service.initialize()
            await self.env_service.initialize()
            await self.file_storage.initialize()
            
            # Load settings from file storage
            settings_result = await self.file_storage.load_settings()
            if settings_result.success:
                self.settings = settings_result.data
            else:
                logger.error(error_message(
                    module_id=COMPONENT_ID,
                    error_type="SETTINGS_LOAD_ERROR",
                    details=f"Failed to load settings: {settings_result.error.get('message', 'Unknown error')}",
                    location="initialize()"
                ))
                # Initialize with error state settings
                self.settings = {"global": {}, "_versions": {"global": "SETTINGS-LOAD-ERROR"}}
            
            # Load client config
            client_config_result = await self.file_storage.load_client_config()
            if client_config_result.success:
                self.client_config = client_config_result.data
            else:
                logger.error(error_message(
                    module_id=COMPONENT_ID,
                    error_type="CLIENT_CONFIG_LOAD_ERROR",
                    details=f"Failed to load client config: {client_config_result.error.get('message', 'Unknown error')}",
                    location="initialize()"
                ))
                self.client_config = {}
            
            # Load metadata
            metadata_result = await self.file_storage.load_metadata()
            if metadata_result.success:
                self.metadata = metadata_result.data
            else:
                logger.error(error_message(
                    module_id=COMPONENT_ID,
                    error_type="METADATA_LOAD_ERROR",
                    details=f"Failed to load metadata: {metadata_result.error.get('message', 'Unknown error')}",
                    location="initialize()"
                ))
                self.metadata = {"validation": {}, "ui": {}, "last_updated": datetime.now().isoformat()}
            
            # NEW PATTERN: Use database services passed from parent module
            if database_service and crud_service:
                logger.info(f"Database services provided by parent module via @require_services pattern")
                await self.db_storage.initialize(database_service=database_service, crud_service=crud_service)
                
                # Initialize backup service if database is available
                if self.backup_service:
                    await self.backup_service.initialize(self.app_context, self)
            else:
                # Fallback to legacy pattern if services not provided
                db_service = self.app_context.get_service("core.database.service")
                logger.info(f"Fallback to legacy database service lookup: found={db_service is not None}, initialized={getattr(db_service, 'initialized', 'NO_ATTR') if db_service else 'N/A'}")
                if db_service and getattr(db_service, 'initialized', False):
                    await self.db_storage.initialize(self.app_context)
                    
                    # Initialize backup service if database is available
                    if self.backup_service:
                        await self.backup_service.initialize(self.app_context, self)
                else:
                    logger.warning(error_message(
                        module_id=COMPONENT_ID,
                        error_type="DB_UNAVAILABLE",
                        details="Database service not available - backup features disabled",
                        location="initialize()"
                    ))
                
            # Update settings versions from manifests
            await self._update_all_settings_versions()
            
            # Set initialized flag BEFORE potentially starting scheduler
            self.initialized = True
            logger.info(f"{COMPONENT_ID} service core initialization complete")

            # Start backup scheduler if enabled (now safe to read settings)
            if self.backup_service:
                try:
                    # Use self.settings directly as it's loaded now
                    if self.settings.get(MODULE_ID, {}).get("auto_backup_enabled", True):
                         # Check if the method exists before calling
                         if hasattr(self.backup_service, '_start_scheduler'):
                            self.backup_service._start_scheduler()
                         else:
                             logger.warning(f"BackupService does not have _start_scheduler method.")
                    else:
                        logger.info("Automatic backups disabled in settings, scheduler not started.")
                except Exception as scheduler_err:
                     logger.error(f"Error starting backup scheduler: {scheduler_err}", exc_info=True)

            logger.info(f"{COMPONENT_ID} service full initialization complete")
            return True
            
        except Exception as e:
            logger.error(error_message(
                module_id=COMPONENT_ID,
                error_type="INIT_ERROR",
                details=f"Error initializing settings service: {str(e)}",
                location="initialize()"
            ))
            logger.error(traceback.format_exc())
            return False
    
    async def shutdown(self):
        """
        Graceful async shutdown when event loop is available.
        
        Returns:
            None
        """
        logger.info(f"{COMPONENT_ID}: Shutting down service gracefully...")
        
        # Cancel background tasks
        for task in self._background_tasks:
            if not task.done():
                task.cancel()
                try:
                    await asyncio.wait_for(asyncio.shield(task), timeout=2.0)
                except (asyncio.TimeoutError, asyncio.CancelledError):
                    pass
        
        # Shutdown components
        if hasattr(self.backup_service, 'shutdown'):
            await self.backup_service.shutdown()
            
        if hasattr(self.db_storage, 'shutdown'):
            await self.db_storage.shutdown()
        
        logger.info(f"{COMPONENT_ID}: Service shutdown complete")
    
    def _create_background_task(self, coroutine, name=None):
        """Create a tracked background task with cleanup handling."""
        task = asyncio.create_task(coroutine, name=name)
        
        # Register cleanup callback
        def _task_done_callback(task):
            # Handle task completion
            if task in self._background_tasks:
                self._background_tasks.remove(task)
        
        task.add_done_callback(_task_done_callback)
        self._background_tasks.append(task)
        return task
    
    async def register_module_settings(self, 
                                     module_id: str, 
                                     default_settings: Dict[str, Any],
                                     validation_schema: Optional[Dict[str, Any]] = None,
                                     ui_metadata: Optional[Dict[str, Any]] = None,
                                     version: Optional[str] = None) -> bool:
        """
        Register default settings for a module using the simplified evolution approach.
        
        Args:
            module_id: Module identifier (e.g., 'core.database')
            default_settings: Dictionary of default settings
            validation_schema: Validation rules for settings
            ui_metadata: UI-specific metadata for settings
            version: Version string for settings schema (optional - uses module's MODULE_VERSION if not provided)
            
        Returns:
            True if settings were registered, False otherwise
        """
        # NOTE: Initialization check removed. Settings registration must happen in Phase 1,
        # before the service is fully initialized in Phase 2.
            
        try:
            # Version handling: explicit parameter takes precedence, otherwise resolve from module data
            if version is not None:
                manifest_version = version
                version_source = "explicit_parameter"
            else:
                # Look up version from module loader (Phase 2 cross-registration)
                manifest_version, version_source = self._resolve_module_version(module_id)
            
            # Always log version resolution for transparency
            logger.debug(f"Using version '{manifest_version}' for {module_id} (source: {version_source})")
            
            # Check for existing settings
            settings_exist = module_id in self.settings
            
            # Check current version if settings exist
            if settings_exist:
                settings_version = self.settings.get("_versions", {}).get(module_id, "0.0.0")
                version_changed = settings_version != manifest_version
                
                if version_changed:
                    logger.info(f"Module {module_id} version changed: {settings_version} -> {manifest_version}")
                    
                    # Create backup before modifying (if database is ready)
                    if await self._ensure_database_ready():
                        await self._backup_settings()
                    else:
                        logger.debug("Skipping backup - database service not ready")
                    
                    # Get current settings
                    current_settings = self.settings.get(module_id, {})
                    
                    # Apply basic settings evolution
                    updated_settings = await self._apply_basic_settings_evolution(
                        module_id, current_settings, default_settings
                    )
                    
                    # Validate updated settings if schema provided
                    if validation_schema:
                        validation_result = await self.validation_service.validate_settings(
                            module_id, updated_settings, validation_schema
                        )
                        if not validation_result.success and validation_result.error.get("errors"):
                            # Get the errors from the validation result
                            errors = validation_result.error.get("errors", {})
                            # Raise ValidationError from the imported service
                            from .validation_service import ValidationError
                            raise ValidationError(module_id, errors)
                    
                    # Update settings
                    self.settings[module_id] = updated_settings
                    
                    # Record setting changes for version update
                    if self.backup_service and self.backup_service.initialized:
                        await self._record_setting_changes(module_id, current_settings, updated_settings, "version_update")
                else:
                    # No version change, just check for missing keys
                    current_settings = self.settings.get(module_id, {})
                    missing_keys = [k for k in default_settings if k not in current_settings]
                    
                    if missing_keys:
                        # Apply basic evolution for missing keys only
                        updated_settings = dict(current_settings)
                        for key in missing_keys:
                            updated_settings[key] = copy.deepcopy(default_settings[key])
                            logger.info(f"Added missing setting '{key}' for module {module_id}")
                        
                        # Validate if schema provided
                        if validation_schema:
                            validation_result = await self.validation_service.validate_settings(
                                module_id, updated_settings, validation_schema
                            )
                            if not validation_result.success and validation_result.error.get("errors"):
                                # Get the errors from the validation result
                                errors = validation_result.error.get("errors", {})
                                # Raise ValidationError from the imported service
                                from .validation_service import ValidationError
                                raise ValidationError(module_id, errors)
                        
                        # Update settings
                        self.settings[module_id] = updated_settings
                        
                        # Record setting changes for missing keys
                        if self.backup_service and self.backup_service.initialized:
                            await self._record_setting_changes(module_id, current_settings, updated_settings, "missing_keys_update")
            else:
                # Settings don't exist yet, create new
                logger.info(f"{module_id} ({manifest_version}): Creating new settings for module")
                
                # Validate new settings if schema provided
                if validation_schema:
                    validation_result = await self.validation_service.validate_settings(
                        module_id, default_settings, validation_schema
                    )
                    if not validation_result.success and validation_result.error.get("errors"):
                        # Get the errors from the validation result
                        errors = validation_result.error.get("errors", {})
                        # Raise ValidationError from the imported service
                        from .validation_service import ValidationError
                        raise ValidationError(module_id, errors)
                
                # Add settings
                self.settings[module_id] = copy.deepcopy(default_settings)
                
                # Record setting creation
                if self.backup_service and self.backup_service.initialized:
                    await self._record_setting_changes(module_id, {}, default_settings, "initial_creation")
            
            # Update version
            if "_versions" not in self.settings:
                self.settings["_versions"] = {}
            self.settings["_versions"][module_id] = manifest_version
            
            # Save settings - proper Result handling
            save_result = await self.file_storage.save_settings(self.settings)
            if not save_result.success:
                logger.error(error_message(
                    module_id=COMPONENT_ID,
                    error_type="SETTINGS_SAVE_ERROR",
                    details=f"Failed to save settings: {save_result.error.get('message', 'Unknown error')}",
                    location="register_module_settings()"
                ))
                return False
            
            # CRITICAL: Create database backup after successful file save
            if self.backup_service and self.backup_service.initialized:
                backup_description = f"Settings registration backup - {module_id} v{manifest_version}"
                backup_result = await self.backup_service.create_backup(self.settings, backup_description)
                if not backup_result.success:
                    logger.warning(error_message(
                        module_id=COMPONENT_ID,
                        error_type="DATABASE_BACKUP_FAILED",
                        details=f"Failed to create database backup during settings registration: {backup_result.error.get('message', 'Unknown error')}",
                        location="register_module_settings()"
                    ))
                    # Continue with registration - database backup failure shouldn't block file-based settings
                else:
                    logger.info(f"Database backup created successfully for {module_id} registration")
            else:
                logger.debug("Backup service not available - settings saved to file only")
            
            # Register validation schema if provided
            if validation_schema:
                if "validation" not in self.metadata:
                    self.metadata["validation"] = {}
                self.metadata["validation"][module_id] = validation_schema
                
                metadata_save_result = await self.file_storage.save_metadata(self.metadata)
                if not metadata_save_result.success:
                    logger.error(error_message(
                        module_id=COMPONENT_ID,
                        error_type="METADATA_SAVE_ERROR",
                        details=f"Failed to save metadata: {metadata_save_result.error.get('message', 'Unknown error')}",
                        location="register_module_settings()"
                    ))
            
            # Register UI metadata if provided
            if ui_metadata:
                if "ui" not in self.metadata:
                    self.metadata["ui"] = {}
                self.metadata["ui"][module_id] = ui_metadata
                
                metadata_save_result = await self.file_storage.save_metadata(self.metadata)
                if not metadata_save_result.success:
                    logger.error(error_message(
                        module_id=COMPONENT_ID,
                        error_type="METADATA_SAVE_ERROR",
                        details=f"Failed to save metadata: {metadata_save_result.error.get('message', 'Unknown error')}",
                        location="register_module_settings()"
                    ))
            
            # Success!
            logger.info(f"{module_id} ({manifest_version}): Successfully registered settings for module")
            return True
            
        except Exception as e:
            # Catch ValidationError separately to re-raise it
            if e.__class__.__name__ == 'ValidationError':
                raise 
            
            logger.error(error_message(
                module_id=COMPONENT_ID,
                error_type="REGISTRATION_ERROR",
                details=f"Error registering settings for module {module_id}: {str(e)}",
                location="register_module_settings()"
            ))
            logger.error(traceback.format_exc())
            return False
    
    async def _record_setting_changes(self, module_id: str, old_settings: Dict[str, Any], 
                                    new_settings: Dict[str, Any], source: str):
        """
        Record setting changes to the database.
        
        Args:
            module_id: Module identifier
            old_settings: Previous settings
            new_settings: New settings
            source: Source of the changes
        """
        # Skip if backup service is disabled or not initialized
        if not self.backup_service or not self.backup_service.initialized:
            return
            
        try:
            # For each setting in new settings
            for key, new_value in new_settings.items():
                old_value = old_settings.get(key)
                
                # Only record if the value has changed
                if old_value != new_value:
                    result = await self.backup_service.record_setting_change(
                        module_id=module_id,
                        setting_key=key,
                        old_value=old_value,
                        new_value=new_value,
                        source=source
                    )
                    if not result.success:
                        logger.warning(error_message(
                            module_id=COMPONENT_ID,
                            error_type="RECORD_CHANGE_ERROR",
                            details=f"Failed to record setting change: {result.error.get('message', 'Unknown error')}",
                            location="_record_setting_changes()"
                        ))
        except Exception as e:
            logger.error(error_message(
                module_id=COMPONENT_ID,
                error_type="RECORD_CHANGES_ERROR",
                details=f"Error recording setting changes: {str(e)}",
                location="_record_setting_changes()"
            ))
    
    async def get_module_settings(self, module_id: str) -> Dict[str, Any]:
        """
        Get settings for a module with overrides applied.
        
        Priority:
        1. Environment variables (MODULE_ID_SETTING_NAME)
        2. Client configuration
        3. Settings.json
        
        Args:
            module_id: Module identifier (e.g., 'core.database')
            
        Returns:
            Dictionary of settings with overrides applied
        """
        # Check initialization
        if not check_initialization(self, COMPONENT_ID, "get_module_settings"):
            return {}
            
        try:
            # Start with the base settings
            if module_id not in self.settings:
                logger.warning(error_message(
                    module_id=COMPONENT_ID,
                    error_type="SETTINGS_NOT_REGISTERED",
                    details=f"Module {module_id} has not registered its settings",
                    location="get_module_settings()"
                ))
                return {}
                
            # Create a copy of the settings to avoid modifying the original
            result = copy.deepcopy(self.settings[module_id])
            
            # Apply client configuration overrides
            if module_id in self.client_config:
                for key, value in self.client_config[module_id].items():
                    result[key] = value
            
            # Apply environment variable overrides
            env_prefix = module_id.replace(".", "_").upper() + "_"
            
            # Get environment variables with this prefix
            env_vars_result = await self.env_service.get_env_vars_by_prefix(env_prefix)
            if env_vars_result.success:
                env_vars = env_vars_result.data
                
                # Apply overrides for each setting
                for key in list(result.keys()):
                    env_var = env_prefix + key.upper()
                    env_value_result = await self.env_service.get_env_var(env_var)
                    
                    if env_value_result.success and env_value_result.data is not None:
                        env_value = env_value_result.data
                        
                        # Convert environment variable to appropriate type
                        original_value = result[key]
                        
                        if isinstance(original_value, bool):
                            result[key] = env_value.lower() in ("true", "1", "yes")
                        elif isinstance(original_value, int):
                            result[key] = int(env_value)
                        elif isinstance(original_value, float):
                            result[key] = float(env_value)
                        else:
                            result[key] = env_value
            
            return result
        except Exception as e:
            logger.error(error_message(
                module_id=COMPONENT_ID,
                error_type="GET_SETTINGS_ERROR",
                details=f"Error retrieving settings for module {module_id}: {str(e)}",
                location="get_module_settings()"
            ))
            logger.error(traceback.format_exc())
            return {}
    
    def _set_nested_value(self, data: Dict[str, Any], key: str, value: Any):
        """
        Set a nested value using dot notation.
        
        Args:
            data: Dictionary to update
            key: Dot-notation key (e.g., "safety.default_safety_level")
            value: Value to set
        """
        keys = key.split('.')
        current = data
        
        # Navigate to the parent of the final key
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]
        
        # Set the final value
        current[keys[-1]] = value
    
    def _get_nested_value(self, data: Dict[str, Any], key: str) -> Any:
        """
        Get a nested value using dot notation.
        
        Args:
            data: Dictionary to search
            key: Dot-notation key (e.g., "safety.default_safety_level")
            
        Returns:
            Value if found, None otherwise
        """
        keys = key.split('.')
        current = data
        
        try:
            for k in keys:
                current = current[k]
            return current
        except (KeyError, TypeError):
            return None
    
    def _remove_nested_value(self, data: Dict[str, Any], key: str) -> bool:
        """
        Remove a nested value using dot notation.
        
        Args:
            data: Dictionary to update
            key: Dot-notation key (e.g., "safety.default_safety_level")
            
        Returns:
            True if value was removed, False if not found
        """
        keys = key.split('.')
        current = data
        
        try:
            # Navigate to the parent of the final key
            for k in keys[:-1]:
                current = current[k]
            
            # Remove the final key if it exists
            if keys[-1] in current:
                del current[keys[-1]]
                
                # Clean up empty parent dictionaries
                self._cleanup_empty_dicts(data, keys[:-1])
                return True
            return False
        except (KeyError, TypeError):
            return False
    
    def _cleanup_empty_dicts(self, data: Dict[str, Any], path: List[str]):
        """
        Clean up empty dictionaries after removing nested values.
        
        Args:
            data: Root dictionary
            path: Path to check for empty dictionaries
        """
        if not path:
            return
            
        current = data
        for k in path[:-1]:
            current = current[k]
        
        # Check if the dictionary is empty and remove it
        last_key = path[-1]
        if last_key in current and isinstance(current[last_key], dict) and not current[last_key]:
            del current[last_key]
            # Recursively clean up parent
            self._cleanup_empty_dicts(data, path[:-1])
    
    def _get_nested_schema(self, schema: Dict[str, Any], key: str) -> Optional[Dict[str, Any]]:
        """
        Get validation schema for a potentially nested setting key.
        
        Args:
            schema: The validation schema dictionary
            key: Setting key, potentially with dot notation (e.g., "safety.default_safety_level")
            
        Returns:
            Schema for the key if found, None otherwise
        """
        # First try direct lookup (for backward compatibility)
        if key in schema:
            return schema[key]
        
        # If not found and key contains dots, try hierarchical lookup
        if '.' in key:
            keys = key.split('.')
            current_schema = schema
            
            # Navigate through the schema hierarchy
            for i, k in enumerate(keys):
                if k in current_schema:
                    if i == len(keys) - 1:
                        # This is the final key, return its schema
                        return current_schema[k]
                    else:
                        # This is an intermediate key, dive into its properties
                        current_item = current_schema[k]
                        if isinstance(current_item, dict) and "properties" in current_item:
                            current_schema = current_item["properties"]
                        else:
                            # No properties found, can't continue
                            return None
                else:
                    # Key not found in current level
                    return None
        
        # Key not found
        return None

    async def update_module_setting(self, 
                                   module_id: str, 
                                   key: str, 
                                   value: Any, 
                                   use_client_config: bool = True,
                                   validate: bool = True,
                                   source: str = "user") -> bool:
        """
        Update a setting value for a module.
        
        Args:
            module_id: Module identifier (e.g., 'core.database')
            key: Setting key
            value: Setting value
            use_client_config: If True, store in client_config.json, otherwise in settings.json
            validate: Whether to validate the setting against schema
            source: Source of the change (for tracking)
            
        Returns:
            True if setting was updated successfully, False otherwise
        """
        # Check initialization
        if not check_initialization(self, COMPONENT_ID, "update_module_setting"):
            return False
            
        try:
            # Log the incoming value for debugging
            logger.debug(f"Updating setting {module_id}.{key} with value: {value} (type: {type(value).__name__})")
            
            # Validate if requested and if a schema exists
            if validate and "validation" in self.metadata and module_id in self.metadata["validation"]:
                schema = self.metadata["validation"][module_id]
                key_schema = self._get_nested_schema(schema, key)
                
                if key_schema:
                    logger.debug(f"Validating {module_id}.{key} with schema: {key_schema}")
                    
                    # Perform validation
                    validation_result = await self.validation_service.validate_setting(key, value, key_schema)
                    if not validation_result.success:
                        logger.error(error_message(
                            module_id=COMPONENT_ID,
                            error_type="VALIDATION_ERROR",
                            details=f"Validation failed for {module_id}.{key}: {validation_result.error.get('message')}",
                            location="update_module_setting()"
                        ))
                        # Raise ValidationError with the errors
                        from .validation_service import ValidationError
                        raise ValidationError(module_id, {key: validation_result.error.get('message')})
            
            # Get the old value for change tracking
            old_value = None
            if use_client_config:
                if module_id in self.client_config:
                    old_value = self._get_nested_value(self.client_config[module_id], key)
            else:
                if module_id in self.settings:
                    old_value = self._get_nested_value(self.settings[module_id], key)
            
            success = False
            
            if use_client_config:
                # Store in client configuration (user overrides)
                if module_id not in self.client_config:
                    self.client_config[module_id] = {}
                
                # Store as flat key (dot notation is literal, not nested path)
                self.client_config[module_id][key] = value
                
                # Save to file storage
                save_result = await self.file_storage.save_client_config(self.client_config)
                if not save_result.success:
                    logger.error(error_message(
                        module_id=COMPONENT_ID,
                        error_type="CLIENT_CONFIG_SAVE_ERROR",
                        details=f"Failed to save client config: {save_result.error.get('message', 'Unknown error')}",
                        location="update_module_setting()"
                    ))
                    return False
                success = True
            else:
                # Store in settings.json (system defaults)
                if module_id not in self.settings:
                    logger.warning(error_message(
                        module_id=COMPONENT_ID,
                        error_type="MODULE_NOT_REGISTERED",
                        details=f"Module {module_id} has not registered its settings",
                        location="update_module_setting()"
                    ))
                    self.settings[module_id] = {}
                
                # Store as flat key (dot notation is literal, not nested path)
                self.settings[module_id][key] = value
                
                # Save to file storage
                save_result = await self.file_storage.save_settings(self.settings)
                if not save_result.success:
                    logger.error(error_message(
                        module_id=COMPONENT_ID,
                        error_type="SETTINGS_SAVE_ERROR",
                        details=f"Failed to save settings: {save_result.error.get('message', 'Unknown error')}",
                        location="update_module_setting()"
                    ))
                    return False
                success = True
            
            # Record the change if it was successful and backup service exists
            if success and old_value != value and self.backup_service and self.backup_service.initialized:
                change_result = await self.backup_service.record_setting_change(
                    module_id=module_id,
                    setting_key=key,
                    old_value=old_value,
                    new_value=value,
                    source=source
                )
                if not change_result.success:
                    logger.warning(error_message(
                        module_id=COMPONENT_ID,
                        error_type="RECORD_CHANGE_ERROR",
                        details=f"Failed to record setting change: {change_result.error.get('message', 'Unknown error')}",
                        location="update_module_setting()"
                    ))
            
            return success
        except Exception as e:
            # Catch ValidationError separately to re-raise it
            if e.__class__.__name__ == 'ValidationError':
                raise
                
            logger.error(error_message(
                module_id=COMPONENT_ID,
                error_type="UPDATE_ERROR",
                details=f"Error updating setting {key} for module {module_id}: {str(e)}",
                location="update_module_setting()"
            ))
            logger.error(traceback.format_exc())
            return False
    
    async def reset_module_setting(self, module_id: str, key: str) -> bool:
        """
        Reset a module setting to its default value by removing any client overrides.
        
        Args:
            module_id: Module identifier (e.g., 'core.database')
            key: Setting key
            
        Returns:
            True if setting was reset successfully, False otherwise
        """
        # Check initialization
        if not check_initialization(self, COMPONENT_ID, "reset_module_setting"):
            return False
            
        try:
            # Get old value for tracking
            old_value = None
            if module_id in self.client_config:
                old_value = self._get_nested_value(self.client_config[module_id], key)
            
            # Get the new (default) value
            new_value = None
            if module_id in self.settings:
                new_value = self._get_nested_value(self.settings[module_id], key)
            
            # Remove from client configuration if it exists
            removed = False
            if module_id in self.client_config:
                removed = self._remove_nested_value(self.client_config[module_id], key)
                
                # Clean up empty module dictionary
                if not self.client_config[module_id]:
                    del self.client_config[module_id]
                
                # Only save if something was actually removed
                if removed:
                    # Save to file storage
                    save_result = await self.file_storage.save_client_config(self.client_config)
                    if not save_result.success:
                        logger.error(error_message(
                            module_id=COMPONENT_ID,
                            error_type="CLIENT_CONFIG_SAVE_ERROR",
                            details=f"Failed to save client config: {save_result.error.get('message', 'Unknown error')}",
                            location="reset_module_setting()"
                        ))
                        return False
                    success = True
                else:
                    success = True  # Nothing to reset
                
                # Record the change if backup service exists
                if success and old_value != new_value and self.backup_service and self.backup_service.initialized:
                    change_result = await self.backup_service.record_setting_change(
                        module_id=module_id,
                        setting_key=key,
                        old_value=old_value,
                        new_value=new_value,
                        source="reset"
                    )
                    if not change_result.success:
                        logger.warning(error_message(
                            module_id=COMPONENT_ID,
                            error_type="RECORD_CHANGE_ERROR",
                            details=f"Failed to record setting change: {change_result.error.get('message', 'Unknown error')}",
                            location="reset_module_setting()"
                        ))
                
                return success
            
            return True  # Nothing to reset
        except Exception as e:
            logger.error(error_message(
                module_id=COMPONENT_ID,
                error_type="RESET_ERROR",
                details=f"Error resetting setting {key} for module {module_id}: {str(e)}",
                location="reset_module_setting()"
            ))
            logger.error(traceback.format_exc())
            return False
    
    async def get_setting(self, module_id: str, key: str) -> Any:
        """
        Get a specific setting value with overrides applied.
        
        Args:
            module_id: Module identifier (e.g., 'core.database')
            key: Setting key
            
        Returns:
            Setting value or None if not found
        """
        # Check initialization
        if not check_initialization(self, COMPONENT_ID, "get_setting"):
            return None
            
        try:
            module_settings = await self.get_module_settings(module_id)
            return module_settings.get(key)
        except Exception as e:
            logger.error(error_message(
                module_id=COMPONENT_ID,
                error_type="GET_SETTING_ERROR",
                details=f"Error retrieving setting {module_id}.{key}: {str(e)}",
                location="get_setting()"
            ))
            logger.error(traceback.format_exc())
            return None
    
    async def get_all_settings(self) -> Dict[str, Any]:
        """
        Get all settings for all modules, enforcing the new settings standard.
        
        Returns:
            Dictionary of all settings
        """
        # Check initialization
        if not check_initialization(self, COMPONENT_ID, "get_all_settings"):
            return {}
            
        logger.info("Getting all settings")
        
        try:
            # Create a deep copy of all settings
            result = copy.deepcopy(self.settings)
            
            # Remove internal tracking keys
            if "_versions" in result:
                del result["_versions"]
            
            # Check for non-compliant settings
            non_compliant_modules = []
            for module_id, settings_value in list(result.items()):
                if not isinstance(settings_value, dict):
                    logger.error(error_message(
                        module_id=COMPONENT_ID,
                        error_type="INVALID_SETTINGS_FORMAT",
                        details=f"Module '{module_id}' has invalid settings format: expected dict, got {type(settings_value).__name__}. "
                                f"This module must be updated to use the new settings standard.",
                        location="get_all_settings()"
                    ))
                    # Remove non-compliant settings
                    del result[module_id]
                    non_compliant_modules.append(module_id)
            
            # Process client config overrides (only apply if properly formatted)
            for module_id, module_settings in self.client_config.items():
                # Skip non-compliant overrides
                if not isinstance(module_settings, dict):
                    logger.error(error_message(
                        module_id=COMPONENT_ID,
                        error_type="INVALID_CLIENT_CONFIG",
                        details=f"Invalid client config for module '{module_id}': expected dict, got {type(module_settings).__name__}. "
                                f"This will be ignored until fixed.",
                        location="get_all_settings()"
                    ))
                    continue
                    
                # Create entry if it doesn't exist
                if module_id not in result:
                    result[module_id] = {}
                    
                # Apply overrides
                for key, value in module_settings.items():
                    result[module_id][key] = value
            
            # Apply environment variable overrides using batch processing
            for module_id in list(result.keys()):
                try:
                    env_prefix = module_id.replace(".", "_").upper() + "_"
                    
                    # Get all environment variables with this prefix
                    env_vars_result = await self.env_service.get_env_vars_by_prefix(env_prefix)
                    
                    if env_vars_result.success:
                        env_vars = env_vars_result.data
                        
                        # Apply overrides
                        for key, env_value in env_vars.items():
                            # Extract the setting key from the environment variable name
                            setting_key = key.replace(env_prefix, "").lower()
                            
                            if setting_key in result[module_id]:
                                # Convert environment variable to appropriate type
                                original_value = result[module_id][setting_key]
                                
                                if isinstance(original_value, bool):
                                    result[module_id][setting_key] = env_value.lower() in ("true", "1", "yes")
                                elif isinstance(original_value, int):
                                    result[module_id][setting_key] = int(env_value)
                                elif isinstance(original_value, float):
                                    result[module_id][setting_key] = float(env_value)
                                else:
                                    result[module_id][setting_key] = env_value
                except Exception as e:
                    logger.warning(error_message(
                        module_id=COMPONENT_ID,
                        error_type="ENV_VAR_PROCESSING_ERROR",
                        details=f"Error processing environment variables for module {module_id}: {str(e)}",
                        location="get_all_settings()"
                    ))
                    # Continue with other modules
            
            # Log a summary
            logger.info(f"Returning {len(result)} module settings")
            if non_compliant_modules:
                logger.warning(error_message(
                    module_id=COMPONENT_ID,
                    error_type="NON_COMPLIANT_MODULES",
                    details=f"Removed {len(non_compliant_modules)} non-compliant modules from settings: {', '.join(non_compliant_modules)}",
                    location="get_all_settings()"
                ))
            
            # Return the result directly
            return result
        except Exception as e:
            logger.error(error_message(
                module_id=COMPONENT_ID,
                error_type="GET_ALL_SETTINGS_ERROR",
                details=f"Error retrieving all settings: {str(e)}",
                location="get_all_settings()"
            ))
            logger.error(traceback.format_exc())
            return {}
    
    # UI Metadata methods
    async def get_ui_metadata(self, module_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get UI metadata for modules.
        
        Args:
            module_id: Optional module identifier to get metadata for specific module
            
        Returns:
            Dictionary of UI metadata
        """
        # Check initialization
        if not check_initialization(self, COMPONENT_ID, "get_ui_metadata"):
            return {}
            
        try:
            if "ui" not in self.metadata:
                return {}
                
            if module_id:
                return copy.deepcopy(self.metadata["ui"].get(module_id, {}))
            else:
                return copy.deepcopy(self.metadata["ui"])
        except Exception as e:
            logger.error(error_message(
                module_id=COMPONENT_ID,
                error_type="GET_UI_METADATA_ERROR",
                details=f"Error retrieving UI metadata: {str(e)}",
                location="get_ui_metadata()"
            ))
            logger.error(traceback.format_exc())
            return {}
            
    async def update_ui_metadata(self, module_id: str, ui_metadata: Dict[str, Any]) -> bool:
        """
        Update UI metadata for a module.
        
        Args:
            module_id: Module identifier
            ui_metadata: UI metadata
            
        Returns:
            True if metadata was updated successfully, False otherwise
        """
        # Check initialization
        if not check_initialization(self, COMPONENT_ID, "update_ui_metadata"):
            return False
            
        try:
            if "ui" not in self.metadata:
                self.metadata["ui"] = {}
            
            self.metadata["ui"][module_id] = ui_metadata
            
            # Save to file storage
            save_result = await self.file_storage.save_metadata(self.metadata)
            if not save_result.success:
                logger.error(error_message(
                    module_id=COMPONENT_ID,
                    error_type="METADATA_SAVE_ERROR",
                    details=f"Failed to save metadata: {save_result.error.get('message', 'Unknown error')}",
                    location="update_ui_metadata()"
                ))
                return False
            return True
        except Exception as e:
            logger.error(error_message(
                module_id=COMPONENT_ID,
                error_type="UPDATE_UI_METADATA_ERROR",
                details=f"Error updating UI metadata for module {module_id}: {str(e)}",
                location="update_ui_metadata()"
            ))
            logger.error(traceback.format_exc())
            return False
            
    async def _apply_basic_settings_evolution(self, module_id: str, old_settings: Dict[str, Any], 
                                           new_defaults: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply basic settings evolution between versions:
        - Keep existing settings with matching names
        - Add new settings with default values
        - Log warnings about removed settings
        
        Args:
            module_id: Module identifier
            old_settings: Existing settings for the module
            new_defaults: New default settings from the module
            
        Returns:
            Updated settings dictionary
        """
        updated_settings = {}
        
        # Add all new default settings
        added_count = 0
        for key, value in new_defaults.items():
            # If the setting exists in old settings, preserve the value
            if key in old_settings:
                updated_settings[key] = old_settings[key]
            else:
                # This is a new setting, use the default value
                updated_settings[key] = copy.deepcopy(value)
                added_count += 1
        
        # Check for settings that exist in old but not in new (removed settings)
        removed_settings = []
        for key in old_settings:
            if key not in new_defaults:
                removed_settings.append(key)
        
        # Log results only if there were changes
        if added_count > 0:
            logger.info(f"Added {added_count} new settings for module {module_id}")
        
        if removed_settings:
            removed_list = ", ".join(removed_settings)
            logger.warning(error_message(
                module_id=COMPONENT_ID,
                error_type="REMOVED_SETTINGS",
                details=f"Module {module_id} has {len(removed_settings)} settings that no longer exist in new version: {removed_list}",
                location="_apply_basic_settings_evolution()"
            ))
        
        return updated_settings

    async def _backup_settings(self, description=None):
        """
        Create a backup of the current settings with timestamp.
        
        Args:
            description: Optional description for this backup
            
        Returns:
            Tuple of (success, backup_path or backup_id)
        """
        try:
            if not self.backup_service or not self.backup_service.initialized:
                # Use file storage for backup
                backup_file_result = await self.file_storage.create_backup_file(
                    self.settings, 
                    description
                )
                
                if not backup_file_result.success:
                    logger.error(error_message(
                        module_id=COMPONENT_ID,
                        error_type="FILE_BACKUP_ERROR",
                        details=f"Failed to create file backup: {backup_file_result.error.get('message', 'Unknown error')}",
                        location="_backup_settings()"
                    ))
                    return False, None
                    
                backup_file = backup_file_result.data.get("path")
                return True, backup_file
            
            # Use backup service
            backup_result = await self.backup_service.create_backup(
                self.settings,
                description
            )
            
            if not backup_result.success:
                logger.error(error_message(
                    module_id=COMPONENT_ID,
                    error_type="BACKUP_ERROR",
                    details=f"Failed to create backup: {backup_result.error.get('message', 'Unknown error')}",
                    location="_backup_settings()"
                ))
                return False, None
                
            backup_id = backup_result.data.get("backup_id")
            return True, backup_id
        except Exception as e:
            logger.error(error_message(
                module_id=COMPONENT_ID,
                error_type="BACKUP_ERROR",
                details=f"Error creating settings backup: {str(e)}",
                location="_backup_settings()"
            ))
            logger.error(traceback.format_exc())
            return False, None

    
    async def _update_all_settings_versions(self):
        """
        Update all settings versions from already-loaded module metadata.
        
        This ensures that the version information in settings._versions 
        matches the actual module versions for all loaded modules.
        """
        try:
            if not hasattr(self.app_context, 'module_manager') or not self.app_context.module_manager:
                logger.warning(error_message(
                    module_id=COMPONENT_ID,
                    error_type="MODULE_MANAGER_UNAVAILABLE",
                    details="Cannot update settings versions: module_manager not available",
                    location="_update_all_settings_versions()"
                ))
                return False
            
            # Initialize _versions if it doesn't exist
            if "_versions" not in self.settings:
                self.settings["_versions"] = {}
                
            changes_made = False
            
            # Iterate through all loaded modules
            for module_id, module_info in self.app_context.module_manager.modules.items():
                # Skip self-referential updates - core.settings manages its own version through registration
                if module_id == "core.settings":
                    continue
                    
                # Get the current version from settings
                current_version = self.settings.get("_versions", {}).get(module_id)
                
                # Get the module version from module class
                # CRITICAL: Only use real versions - never store fake data
                if hasattr(module_info.class_obj, "MODULE_VERSION"):
                    manifest_version = module_info.class_obj.MODULE_VERSION
                    logger.debug(f"Found MODULE_VERSION for {module_id}: {manifest_version}")
                else:
                    manifest_version = "unknown"
                    logger.debug(f"No MODULE_VERSION found for {module_id}, using 'unknown'")
                
                # If versions don't match or current version doesn't exist, update it
                if current_version != manifest_version:
                    logger.info(f"Updating settings version for {module_id}: {current_version} -> {manifest_version}")
                    self.settings["_versions"][module_id] = manifest_version
                    changes_made = True
                    
            # Also check any registered global settings
            if "global" in self.settings and "global" not in self.settings.get("_versions", {}):
                self.settings["_versions"]["global"] = "1.0.0"
                changes_made = True
                
            # Save if changes were made
            if changes_made:
                save_result = await self.file_storage.save_settings(self.settings)
                if not save_result.success:
                    logger.error(error_message(
                        module_id=COMPONENT_ID,
                        error_type="SETTINGS_SAVE_ERROR",
                        details=f"Failed to save settings versions: {save_result.error.get('message', 'Unknown error')}",
                        location="_update_all_settings_versions()"
                    ))
                    return False
                logger.info("Settings versions updated from manifests")
                
            return changes_made
        except Exception as e:
            logger.error(error_message(
                module_id=COMPONENT_ID,
                error_type="UPDATE_VERSIONS_ERROR",
                details=f"Error updating settings versions: {str(e)}",
                location="_update_all_settings_versions()"
            ))
            logger.error(traceback.format_exc())
            return False

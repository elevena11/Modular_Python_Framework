"""
modules/core/settings/services.py
Settings Service - Pydantic-first settings system.

Provides clean, hierarchical settings management with optimal performance
through memory-based resolution and minimal SQL overhead.

Based on architecture documented in: docs/v2/settings_v2.md
"""

import os
import json
from typing import Dict, Any, Optional, Type, List
from datetime import datetime
from pydantic import BaseModel

from core.logging import get_framework_logger
from core.error_utils import error_message, Result

# Import our own settings model
from .settings import SettingsModuleSettings

# Module identity
MODULE_ID = "core.settings"
logger = get_framework_logger(MODULE_ID)

class SettingsService:
    """
    Main service for Settings system.
    
    Core functionality:
    - Pydantic model registration for modules
    - Memory-optimized baseline resolution (defaults + environment) 
    - Single SQL table for user preferences
    - Type-safe settings access via get_typed_settings()
    
    Architecture follows docs/v2/settings_v2.md
    """
    
    def __init__(self, app_context):
        """Sync initialization - NO complex operations."""
        self.app_context = app_context
        self.initialized = False
        self.logger = logger
        
        # Core data structures for clean architecture
        self.registered_models = {}        # module_id -> Pydantic model class
        self.registered_defaults = {}      # module_id -> default dict
        self.resolved_baseline = {}        # module_id -> merged dict (defaults + env)
        
        # Services (set during initialize)
        self.database_service = None
        self.crud_service = None
        self.user_prefs_db = None  # Database operations
        
        # Own settings configuration (will be loaded during Phase 2)
        self.own_settings: Optional[SettingsModuleSettings] = None
        
        # Self-register our own settings model during Phase 1
        self._self_register()
        
        logger.info(f"{MODULE_ID} service created")
    
    def _self_register(self):
        """Phase 1: Register our own settings model - follows the same pattern we enforce."""
        try:
            # Register our own settings model using the same pattern as other modules
            result = self.register_pydantic_model(MODULE_ID, SettingsModuleSettings)
            if result.success:
                logger.info(f"{MODULE_ID}: Successfully self-registered settings model")
            else:
                logger.error(f"{MODULE_ID}: Failed to self-register settings model: {result.message}")
        except Exception as e:
            logger.error(f"{MODULE_ID}: Error during self-registration: {str(e)}")
    
    async def initialize(self, database_service=None, crud_service=None) -> bool:
        """Phase 2 initialization - Set up database access."""
        if self.initialized:
            return True
            
        logger.info(f"Initializing {MODULE_ID} service")
        
        try:
            # Store services passed from module
            self.database_service = database_service
            self.crud_service = crud_service
            
            if not self.database_service:
                logger.error("Database service not provided")
                return False
                
            if not self.crud_service:
                logger.error("CRUD service not provided")
                return False
            
            # Initialize database operations
            from .database import UserPreferencesDatabase
            self.user_prefs_db = UserPreferencesDatabase(database_service, crud_service)
            await self.user_prefs_db.initialize()
            
            # Load our own configuration during Phase 2 (after database is available)
            await self._load_own_settings()
            
            self.initialized = True
            logger.info(f"{MODULE_ID} service initialized")
            return True
            
        except Exception as e:
            logger.error(error_message(
                module_id=MODULE_ID,
                error_type="INIT_ERROR",
                details=f"Error during initialization: {str(e)}",
                location="initialize()"
            ))
            return False
    
    async def _load_own_settings(self):
        """Phase 2: Load our own settings using the system we provide to others."""
        try:
            # Use our own system to get our typed settings with user preferences
            # Use default database name since we haven't loaded config yet
            result = await self.get_typed_settings(
                module_id=MODULE_ID,
                model_class=SettingsModuleSettings,
                database_name="settings"  # Bootstrap with default, will be configurable after this loads
            )
            
            if result.success:
                self.own_settings = result.data
                logger.info(f"{MODULE_ID}: Successfully loaded own configuration")
                if self.own_settings.log_baseline_creation:
                    logger.info(f"{MODULE_ID}: Using database '{self.own_settings.default_database_name}' for preferences")
            else:
                # Fallback to defaults if loading fails
                self.own_settings = SettingsModuleSettings()
                logger.warning(f"{MODULE_ID}: Failed to load settings, using defaults: {result.message}")
                
        except Exception as e:
            # Fallback to defaults on any error
            self.own_settings = SettingsModuleSettings()
            logger.error(f"{MODULE_ID}: Error loading own settings, using defaults: {str(e)}")
    
    def register_pydantic_model(self, module_id: str, model_class: Type[BaseModel]) -> Result:
        """
        Phase 1: Register Pydantic model from module.
        
        Args:
            module_id: Module identifier (e.g., "core.model_manager")
            model_class: Pydantic model class with defaults and validation
            
        Returns:
            Result object with registration information
        """
        try:
            logger.info(f"Registering Pydantic model for {module_id}")
            
            # Store model class for later typed access
            self.registered_models[module_id] = model_class
            
            # Extract defaults from Pydantic model
            model_instance = model_class()
            defaults = model_instance.model_dump()
            self.registered_defaults[module_id] = defaults
            
            logger.info(f"Registered {len(defaults)} default settings for {module_id}")
            
            return Result.success(data={
                "module_id": module_id,
                "settings_count": len(defaults),
                "defaults": defaults
            })
            
        except Exception as e:
            logger.error(error_message(
                module_id=MODULE_ID,
                error_type="MODEL_REGISTRATION_ERROR",
                details=f"Error registering model for {module_id}: {str(e)}",
                location="register_pydantic_model()"
            ))
            
            return Result.error(
                code="MODEL_REGISTRATION_FAILED",
                message=f"Failed to register Pydantic model for {module_id}",
                details={"error": str(e)}
            )
    
    async def create_baseline(self) -> Result:
        """
        Phase 2: Request registered Pydantic models, parse environment variables, and create baseline.
        
        This happens once during Phase 2 initialization.
        
        Returns:
            Result object with baseline creation information
        """
        try:
            # Use configurable logging if available
            if self.own_settings and self.own_settings.log_baseline_creation:
                logger.info("Creating settings baseline (defaults + environment)")
            elif not self.own_settings:
                logger.info("Creating settings baseline (defaults + environment)")
            
            # Step 1: Request all registered Pydantic models from app_context
            registered_models = self.app_context.get_registered_pydantic_models()
            if self.own_settings and self.own_settings.log_baseline_creation:
                logger.info(f"Retrieved {len(registered_models)} registered Pydantic models from framework")
            
            # Step 2: Extract defaults from each Pydantic model
            for module_id, model_class in registered_models.items():
                try:
                    # Create instance to get defaults
                    model_instance = model_class()
                    defaults = model_instance.model_dump()
                    self.registered_defaults[module_id] = defaults
                    self.registered_models[module_id] = model_class
                    if self.own_settings and self.own_settings.log_baseline_creation:
                        logger.info(f"Extracted {len(defaults)} default settings from {module_id}")
                except Exception as e:
                    logger.error(f"Error extracting defaults from {module_id}: {e}")
                    continue
                    
            # Step 3: Parse environment variables once
            env_overrides = self._parse_environment_variables()
            if self.own_settings and self.own_settings.log_environment_parsing:
                logger.info(f"Parsed environment overrides for {len(env_overrides)} modules")
            elif self.own_settings and self.own_settings.log_baseline_creation:
                logger.info(f"Parsed environment overrides for {len(env_overrides)} modules")
            
            # Step 4: Create baseline for each registered module
            for module_id, defaults in self.registered_defaults.items():
                baseline = defaults.copy()
                
                # Override with environment if present
                if module_id in env_overrides:
                    baseline.update(env_overrides[module_id])
                    logger.debug(f"Applied environment overrides to {module_id}")
                
                self.resolved_baseline[module_id] = baseline
            
            logger.info(f"Created baseline for {len(self.resolved_baseline)} modules")
            
            return Result.success(data={
                "modules_count": len(self.resolved_baseline),
                "env_overrides_count": len(env_overrides),
                "registered_models_count": len(registered_models)
            })
            
        except Exception as e:
            logger.error(error_message(
                module_id=MODULE_ID,
                error_type="BASELINE_CREATION_ERROR",
                details=f"Error creating baseline: {str(e)}",
                location="create_baseline()"
            ))
            
            return Result.error(
                code="BASELINE_CREATION_FAILED",
                message="Failed to create settings baseline",
                details={"error": str(e)}
            )
    
    def _parse_environment_variables(self) -> Dict[str, Dict[str, Any]]:
        """
        Parse environment variables into module settings using hybrid approach:
        1. Use Pydantic model env_prefix if available for robust parsing
        2. Fall back to manual parsing for legacy compatibility
        
        Format: CORE_MODEL_MANAGER_GPU_MEMORY_FRACTION=0.9
        Becomes: {"core.model_manager": {"gpu_memory_fraction": 0.9}}
        
        Returns:
            Dictionary of module_id -> setting overrides
        """
        env_overrides = {}
        
        # First, try Pydantic-based environment parsing for registered models
        for module_id, model_class in self.registered_models.items():
            try:
                # Create model instance with env parsing - Pydantic will handle env_prefix automatically
                model_instance = model_class()
                
                # Check if any environment variables were actually used
                # by comparing with defaults
                defaults = model_class().model_dump()
                env_parsed = model_instance.model_dump()
                
                # Find values that differ from defaults (indicating env override)
                env_specific = {}
                for key, value in env_parsed.items():
                    if key in defaults and defaults[key] != value:
                        env_specific[key] = value
                
                if env_specific:
                    env_overrides[module_id] = env_specific
                    logger.debug(f"Pydantic env parsing for {module_id}: {list(env_specific.keys())}")
                    
            except Exception as e:
                logger.debug(f"Pydantic env parsing failed for {module_id}, using fallback: {e}")
                continue
        
        # Fallback: Manual parsing for modules without registered Pydantic models
        # or when Pydantic parsing fails
        for key, value in os.environ.items():
            if not key.startswith(('CORE_', 'STANDARD_', 'EXTENSIONS_')):
                continue
                
            # CORE_MODEL_MANAGER_GPU_MEMORY_FRACTION -> ["core", "model", "manager", "gpu", "memory", "fraction"]
            parts = key.lower().split('_')
            
            if len(parts) >= 3:
                # Build module_id: "core.model_manager"
                if parts[0] in ['core', 'standard', 'extensions']:
                    if len(parts) >= 3:
                        module_id = f"{parts[0]}.{parts[1]}"  # core.model, standard.semantic, etc.
                        setting_key = "_".join(parts[2:])     # gpu_memory_fraction
                    else:
                        continue
                else:
                    continue
                
                # Skip if already handled by Pydantic parsing
                if module_id in env_overrides and setting_key in env_overrides[module_id]:
                    continue
                
                if module_id not in env_overrides:
                    env_overrides[module_id] = {}
                    
                # Parse value with type inference
                env_overrides[module_id][setting_key] = self._parse_env_value(value)
        
        return env_overrides
    
    def _parse_env_value(self, value: str) -> Any:
        """Parse environment variable value with type inference."""
        # Try JSON first for complex types
        try:
            return json.loads(value)
        except (json.JSONDecodeError, ValueError):
            pass
        
        # Try boolean
        if value.lower() in ('true', 'false'):
            return value.lower() == 'true'
        
        # Try numeric
        try:
            if '.' in value:
                return float(value)
            else:
                return int(value)
        except ValueError:
            pass
        
        # Return as string
        return value
    
    async def get_typed_settings(self, module_id: str, model_class: Type[BaseModel], database_name: str) -> Result:
        """
        Runtime: Get validated Pydantic model with resolved settings.
        
        Args:
            module_id: Module identifier
            model_class: Pydantic model class for validation
            database_name: Database to read user preferences from
            
        Returns:
            Result with validated Pydantic model instance
        """
        try:
            # Get baseline (defaults + environment, pre-merged in Phase 2)
            baseline = self.resolved_baseline.get(module_id, {})
            
            # Get user preferences from SQL  
            user_prefs = await self._get_user_preferences(module_id, database_name)
            
            # Merge with priority: baseline + user_prefs
            resolved = {**baseline, **user_prefs}
            
            # Return validated Pydantic model
            validated_model = model_class(**resolved)
            
            return Result.success(data=validated_model)
            
        except Exception as e:
            logger.error(error_message(
                module_id=MODULE_ID,
                error_type="TYPED_SETTINGS_ERROR",
                details=f"Error getting typed settings for {module_id}: {str(e)}",
                location="get_typed_settings()"
            ))
            
            return Result.error(
                code="TYPED_SETTINGS_FAILED",
                message=f"Failed to get typed settings for {module_id}",
                details={"error": str(e)}
            )
    
    async def _get_user_preferences(self, module_id: str, database_name: str) -> Dict[str, Any]:
        """Get user preferences from SQL table."""
        if not self.user_prefs_db:
            return {}
            
        result = await self.user_prefs_db.get_user_preferences(module_id, database_name)
        if result.success:
            return result.data
        else:
            logger.warning(f"Could not get user preferences for {module_id}: {result.message}")
            return {}
    
    def get_configured_database_name(self) -> str:
        """Get the configured database name, with fallback to default."""
        if self.own_settings:
            return self.own_settings.default_database_name
        return "settings"  # Fallback during bootstrap
    
    async def set_user_preference(self, module_id: str, setting_key: str, value: Any, database_name: str) -> Result:
        """Set user preference override."""
        if not self.user_prefs_db:
            return Result.error(
                code="DATABASE_NOT_INITIALIZED",
                message="User preferences database not initialized"
            )
            
        return await self.user_prefs_db.set_user_preference(module_id, setting_key, value, database_name)
    
    async def clear_user_preference(self, module_id: str, setting_key: str, database_name: str) -> Result:
        """Clear user preference override."""
        if not self.user_prefs_db:
            return Result.error(
                code="DATABASE_NOT_INITIALIZED",
                message="User preferences database not initialized"
            )
            
        return await self.user_prefs_db.clear_user_preference(module_id, setting_key, database_name)
    
    async def cleanup_resources(self):
        """Graceful resource cleanup."""
        logger.info("Settings service cleanup complete")
    
    def force_cleanup(self):
        """Force cleanup."""
        self.initialized = False
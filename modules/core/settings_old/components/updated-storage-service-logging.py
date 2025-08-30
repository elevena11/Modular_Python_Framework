"""
modules/core/settings/components/storage_service.py
Updated: April 4, 2025
Handles asynchronous loading and saving of settings files with reduced logging verbosity
"""

import os
import json
import copy
import logging
import aiofiles
from datetime import datetime
from typing import Dict, Any, Tuple, Optional, List, Union

from core.error_utils import error_message, Result

# Define MODULE_ID matching manifest.json at the top of the file
MODULE_ID = "core.settings"
# Use module hierarchy for component logger
logger = logging.getLogger(f"{MODULE_ID}.storage")

class SettingsStorageService:
    """
    Service handling the loading and saving of settings files.
    
    Uses asynchronous file I/O to avoid blocking the event loop
    when reading or writing settings files.
    """
    
    def __init__(self, 
                settings_file: str, 
                client_config_file: str, 
                metadata_file: str):
        """
        Initialize the storage service.
        
        Args:
            settings_file: Path to the main settings file
            client_config_file: Path to client configuration file
            metadata_file: Path to metadata file
        """
        self.settings_file = settings_file
        self.client_config_file = client_config_file
        self.metadata_file = metadata_file
        self.logger = logger
        self.initialized = True  # This service is always initialized upon creation
        
        # Create directories if they don't exist
        os.makedirs(os.path.dirname(settings_file), exist_ok=True)
    
    async def initialize(self, app_context=None, settings=None) -> bool:
        """
        Initialize the storage service.
        
        Args:
            app_context: Optional application context
            settings: Optional pre-loaded settings
            
        Returns:
            True if initialization successful, always True for this service
        """
        return self.initialized
    
    async def load_settings(self) -> Result:
        """
        Load settings from file asynchronously.
        
        Returns:
            Result with dictionary of settings or error
        """
        try:
            if os.path.exists(self.settings_file):
                try:
                    # Changed from INFO to DEBUG to reduce log verbosity
                    self.logger.debug(f"Loading settings from {os.path.relpath(self.settings_file)}")
                    
                    async with aiofiles.open(self.settings_file, 'r') as f:
                        content = await f.read()
                        settings = json.loads(content)
                    
                    # Validate settings format
                    for module_id, content in settings.items():
                        if module_id != "_versions" and not isinstance(content, dict):
                            self.logger.error(error_message(
                                module_id=MODULE_ID,
                                error_type="INVALID_SETTINGS_FORMAT",
                                details=f"Invalid settings format for module '{module_id}': expected dict, got {type(content).__name__}",
                                location="load_settings()"
                            ))
                            settings[module_id] = {}  # Fix invalid format
                    
                    # Changed from INFO to DEBUG to reduce log verbosity
                    self.logger.debug(f"Loaded settings from {os.path.relpath(self.settings_file)}")
                    return Result.success(data=settings)
                except json.JSONDecodeError as e:
                    self.logger.error(error_message(
                        module_id=MODULE_ID,
                        error_type="SETTINGS_PARSE_ERROR",
                        details=f"Error parsing settings file: {str(e)}",
                        location="load_settings()"
                    ))
                    # Return error state settings
                    return Result.success(data={"global": {}, "_versions": {"global": "SETTINGS-PARSE-ERROR"}})
                except Exception as e:
                    self.logger.error(error_message(
                        module_id=MODULE_ID,
                        error_type="SETTINGS_LOAD_ERROR",
                        details=f"Error loading settings: {str(e)}",
                        location="load_settings()"
                    ))
                    return Result.success(data={"global": {}, "_versions": {"global": "SETTINGS-LOAD-ERROR-1.0.0"}})
            else:
                # Create a new settings file with default global settings
                settings = {
                    "global": {},
                    "_versions": {"global": "NEW-SETTINGS-FILE-1.0.0"}
                }
                await self.save_settings(settings)
                return Result.success(data=settings)
        except Exception as e:
            self.logger.error(error_message(
                module_id=MODULE_ID,
                error_type="SETTINGS_LOAD_ERROR",
                details=f"Unexpected error loading settings: {str(e)}",
                location="load_settings()"
            ))
            return Result.error(
                code="SETTINGS_LOAD_ERROR",
                message="Failed to load settings file",
                details={"error": str(e)}
            )
    
    async def save_settings(self, settings: Dict[str, Any]) -> Result:
        """
        Save settings to file asynchronously.
        
        Args:
            settings: Settings to save
            
        Returns:
            Result indicating success or failure
        """
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.settings_file), exist_ok=True)
            
            # Create deep copy to avoid modifying the original
            settings_to_save = copy.deepcopy(settings)
            
            # Write settings to file
            async with aiofiles.open(self.settings_file, 'w') as f:
                await f.write(json.dumps(settings_to_save, indent=2))
            
            # Changed from INFO to DEBUG to reduce log verbosity
            self.logger.debug(f"Saved settings to {os.path.relpath(self.settings_file)}")
            return Result.success(data={"path": os.path.relpath(self.settings_file)})
        except Exception as e:
            self.logger.error(error_message(
                module_id=MODULE_ID,
                error_type="SETTINGS_SAVE_ERROR",
                details=f"Error saving settings: {str(e)}",
                location="save_settings()"
            ))
            return Result.error(
                code="SETTINGS_SAVE_ERROR",
                message="Failed to save settings file",
                details={"error": str(e)}
            )
    
    async def load_client_config(self) -> Result:
        """
        Load client configuration overrides asynchronously.
        
        Returns:
            Result with dictionary of client configuration or error
        """
        try:
            if os.path.exists(self.client_config_file):
                try:
                    async with aiofiles.open(self.client_config_file, 'r') as f:
                        content = await f.read()
                        config = json.loads(content)
                    
                    # Changed from INFO to DEBUG to reduce log verbosity
                    self.logger.debug(f"Loaded client configuration from {os.path.relpath(self.client_config_file)}")
                    return Result.success(data=config)
                except json.JSONDecodeError as e:
                    self.logger.error(error_message(
                        module_id=MODULE_ID,
                        error_type="CLIENT_CONFIG_PARSE_ERROR",
                        details=f"Error parsing client configuration file: {str(e)}",
                        location="load_client_config()"
                    ))
                    return Result.success(data={})
                except Exception as e:
                    self.logger.error(error_message(
                        module_id=MODULE_ID,
                        error_type="CLIENT_CONFIG_LOAD_ERROR",
                        details=f"Error loading client configuration: {str(e)}",
                        location="load_client_config()"
                    ))
                    return Result.success(data={})
            else:
                # Return empty dict if no client config exists
                return Result.success(data={})
        except Exception as e:
            self.logger.error(error_message(
                module_id=MODULE_ID,
                error_type="CLIENT_CONFIG_LOAD_ERROR",
                details=f"Unexpected error loading client configuration: {str(e)}",
                location="load_client_config()"
            ))
            return Result.error(
                code="CLIENT_CONFIG_LOAD_ERROR",
                message="Failed to load client configuration",
                details={"error": str(e)}
            )
    
    async def save_client_config(self, config: Dict[str, Any]) -> Result:
        """
        Save client configuration to file asynchronously.
        
        Args:
            config: Client configuration to save
            
        Returns:
            Result indicating success or failure
        """
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.client_config_file), exist_ok=True)
            
            # Create deep copy to avoid modifying the original
            config_to_save = copy.deepcopy(config)
            
            # Write config to file
            async with aiofiles.open(self.client_config_file, 'w') as f:
                await f.write(json.dumps(config_to_save, indent=2))
            
            # Changed from INFO to DEBUG to reduce log verbosity
            self.logger.debug(f"Saved client configuration to {os.path.relpath(self.client_config_file)}")
            return Result.success(data={"path": os.path.relpath(self.client_config_file)})
        except Exception as e:
            self.logger.error(error_message(
                module_id=MODULE_ID,
                error_type="CLIENT_CONFIG_SAVE_ERROR",
                details=f"Error saving client configuration: {str(e)}",
                location="save_client_config()"
            ))
            return Result.error(
                code="CLIENT_CONFIG_SAVE_ERROR",
                message="Failed to save client configuration",
                details={"error": str(e)}
            )
    
    async def load_metadata(self) -> Result:
        """
        Load settings metadata for validation and UI asynchronously.
        
        Returns:
            Result with dictionary of metadata or error
        """
        try:
            if os.path.exists(self.metadata_file):
                try:
                    async with aiofiles.open(self.metadata_file, 'r') as f:
                        content = await f.read()
                        metadata = json.loads(content)
                    
                    # Changed from INFO to DEBUG to reduce log verbosity
                    self.logger.debug(f"Loaded settings metadata from {os.path.relpath(self.metadata_file)}")
                    return Result.success(data=metadata)
                except json.JSONDecodeError as e:
                    self.logger.error(error_message(
                        module_id=MODULE_ID,
                        error_type="METADATA_PARSE_ERROR",
                        details=f"Error parsing metadata file: {str(e)}",
                        location="load_metadata()"
                    ))
                    return Result.success(data={"validation": {}, "ui": {}, "last_updated": datetime.now().isoformat()})
                except Exception as e:
                    self.logger.error(error_message(
                        module_id=MODULE_ID,
                        error_type="METADATA_LOAD_ERROR",
                        details=f"Error loading settings metadata: {str(e)}",
                        location="load_metadata()"
                    ))
                    return Result.success(data={"validation": {}, "ui": {}, "last_updated": datetime.now().isoformat()})
            else:
                # Create new metadata file
                metadata = {
                    "validation": {},
                    "ui": {},
                    "last_updated": datetime.now().isoformat()
                }
                await self.save_metadata(metadata)
                return Result.success(data=metadata)
        except Exception as e:
            self.logger.error(error_message(
                module_id=MODULE_ID,
                error_type="METADATA_LOAD_ERROR",
                details=f"Unexpected error loading metadata: {str(e)}",
                location="load_metadata()"
            ))
            return Result.error(
                code="METADATA_LOAD_ERROR",
                message="Failed to load metadata",
                details={"error": str(e)}
            )
    
    async def save_metadata(self, metadata: Dict[str, Any]) -> Result:
        """
        Save settings metadata to file asynchronously.
        
        Args:
            metadata: Metadata to save
            
        Returns:
            Result indicating success or failure
        """
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.metadata_file), exist_ok=True)
            
            # Create deep copy to avoid modifying the original
            metadata_to_save = copy.deepcopy(metadata)
            
            # Update timestamp
            metadata_to_save["last_updated"] = datetime.now().isoformat()
            
            # Write metadata to file
            async with aiofiles.open(self.metadata_file, 'w') as f:
                await f.write(json.dumps(metadata_to_save, indent=2))
            
            # Changed from INFO to DEBUG to reduce log verbosity
            self.logger.debug(f"Saved settings metadata to {os.path.relpath(self.metadata_file)}")
            return Result.success(data={"path": os.path.relpath(self.metadata_file)})
        except Exception as e:
            self.logger.error(error_message(
                module_id=MODULE_ID,
                error_type="METADATA_SAVE_ERROR",
                details=f"Error saving settings metadata: {str(e)}",
                location="save_metadata()"
            ))
            return Result.error(
                code="METADATA_SAVE_ERROR",
                message="Failed to save metadata",
                details={"error": str(e)}
            )
    
    # Other methods unchanged...
    
    # The rest of the class implementation remains the same

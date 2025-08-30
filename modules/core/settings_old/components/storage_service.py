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
    
    async def create_backup_file(self, 
                                settings: Dict[str, Any], 
                                description: Optional[str] = None) -> Result:
        """
        Create a backup file of settings.
        
        Args:
            settings: Settings to backup
            description: Optional description for backup
            
        Returns:
            Result with backup path if successful, error if not
        """
        try:
            # Generate timestamp for backup filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_dir = os.path.dirname(self.settings_file)
            backup_file = os.path.join(backup_dir, f"settings_backup_{timestamp}.json")
            
            # Create directory if it doesn't exist
            os.makedirs(backup_dir, exist_ok=True)
            
            # Create deep copy of settings
            settings_to_backup = copy.deepcopy(settings)
            
            # Add backup metadata
            if "_backup_info" not in settings_to_backup:
                settings_to_backup["_backup_info"] = {}
                
            settings_to_backup["_backup_info"] = {
                "created_at": datetime.now().isoformat(),
                "description": description or f"Automatic backup {timestamp}",
                "backup_file": os.path.basename(backup_file)
            }
            
            # Write backup to file
            async with aiofiles.open(backup_file, 'w') as f:
                await f.write(json.dumps(settings_to_backup, indent=2))
            
            self.logger.info(f"Created settings backup: {os.path.relpath(backup_file)}")
            return Result.success(data={"path": os.path.relpath(backup_file)})
        except Exception as e:
            self.logger.error(error_message(
                module_id=MODULE_ID,
                error_type="BACKUP_FILE_ERROR",
                details=f"Failed to create settings backup file: {str(e)}",
                location="create_backup_file()"
            ))
            return Result.error(
                code="BACKUP_FILE_ERROR",
                message="Failed to create settings backup file",
                details={"error": str(e)}
            )
    
    async def list_backup_files(self, limit: int = 10) -> Result:
        """
        List available backup files.
        
        Args:
            limit: Maximum number of backups to return
            
        Returns:
            Result with list of backup information
        """
        try:
            backup_dir = os.path.dirname(self.settings_file)
            backups = []
            
            # List all files in backup directory
            files = []
            try:
                files = [f for f in os.listdir(backup_dir) if f.startswith("settings_backup_") and f.endswith(".json")]
            except FileNotFoundError:
                # Directory doesn't exist yet
                os.makedirs(backup_dir, exist_ok=True)
            
            # Sort by timestamp (newest first)
            files.sort(reverse=True)
            
            # Limit the number of files
            files = files[:limit]
            
            # Get info for each backup file
            for filename in files:
                file_path = os.path.join(backup_dir, filename)
                
                try:
                    # Get file modification time
                    mod_time = os.path.getmtime(file_path)
                    
                    # Try to read description from file
                    description = ""
                    try:
                        async with aiofiles.open(file_path, 'r') as f:
                            content = await f.read(500)  # Read first 500 bytes only
                            # Try to extract description from partial content
                            if "_backup_info" in content:
                                # Very basic parsing, not fully reliable
                                desc_start = content.find('"description"')
                                if desc_start > 0:
                                    desc_start = content.find('"', desc_start + 14)
                                    desc_end = content.find('"', desc_start + 1)
                                    if desc_start > 0 and desc_end > 0:
                                        description = content[desc_start+1:desc_end]
                    except Exception:
                        # Ignore errors in description extraction
                        pass
                        
                    backups.append({
                        "filename": filename,
                        "path": os.path.relpath(file_path),
                        "size": os.path.getsize(file_path),
                        "modified": datetime.fromtimestamp(mod_time).isoformat(),
                        "description": description
                    })
                except Exception as e:
                    self.logger.warning(error_message(
                        module_id=MODULE_ID,
                        error_type="BACKUP_FILE_INFO_ERROR",
                        details=f"Error getting info for backup {filename}: {str(e)}",
                        location="list_backup_files()"
                    ))
            
            return Result.success(data=backups)
        except Exception as e:
            self.logger.error(error_message(
                module_id=MODULE_ID,
                error_type="LIST_BACKUPS_ERROR",
                details=f"Error listing backup files: {str(e)}",
                location="list_backup_files()"
            ))
            return Result.error(
                code="LIST_BACKUPS_ERROR",
                message="Error listing backup files",
                details={"error": str(e)}
            )
    
    async def load_backup_file(self, backup_filename: str) -> Result:
        """
        Load settings from a backup file.
        
        Args:
            backup_filename: Filename of backup to load
            
        Returns:
            Result with settings from backup or error
        """
        try:
            backup_dir = os.path.dirname(self.settings_file)
            backup_path = os.path.join(backup_dir, backup_filename)
            
            if not os.path.exists(backup_path):
                self.logger.error(error_message(
                    module_id=MODULE_ID,
                    error_type="BACKUP_FILE_NOT_FOUND",
                    details=f"Backup file not found: {os.path.relpath(backup_path)}",
                    location="load_backup_file()"
                ))
                return Result.error(
                    code="BACKUP_FILE_NOT_FOUND",
                    message=f"Backup file not found: {backup_filename}",
                    details={"filename": backup_filename}
                )
            
            try:
                # Read backup file
                async with aiofiles.open(backup_path, 'r') as f:
                    content = await f.read()
                    settings = json.loads(content)
                
                # Remove backup metadata if present
                if "_backup_info" in settings:
                    del settings["_backup_info"]
                    
                self.logger.info(f"Loaded settings from backup: {backup_filename}")
                return Result.success(data=settings)
            except json.JSONDecodeError as e:
                self.logger.error(error_message(
                    module_id=MODULE_ID,
                    error_type="BACKUP_PARSE_ERROR",
                    details=f"Error parsing backup file: {str(e)}",
                    location="load_backup_file()"
                ))
                return Result.error(
                    code="BACKUP_PARSE_ERROR",
                    message=f"Error parsing backup file: {str(e)}",
                    details={"filename": backup_filename}
                )
            except Exception as e:
                self.logger.error(error_message(
                    module_id=MODULE_ID,
                    error_type="BACKUP_LOAD_ERROR",
                    details=f"Error loading backup file: {str(e)}",
                    location="load_backup_file()"
                ))
                return Result.error(
                    code="BACKUP_LOAD_ERROR",
                    message=f"Error loading backup file: {str(e)}",
                    details={"filename": backup_filename}
                )
        except Exception as e:
            self.logger.error(error_message(
                module_id=MODULE_ID,
                error_type="BACKUP_LOAD_ERROR",
                details=f"Unexpected error loading backup file: {str(e)}",
                location="load_backup_file()"
            ))
            return Result.error(
                code="BACKUP_LOAD_ERROR",
                message="Error loading backup file",
                details={"error": str(e)}
            )
            
    async def cleanup_old_backups(self, max_backups: int = 5) -> Result:
        """
        Remove old backup files, keeping only the latest ones.
        
        Args:
            max_backups: Maximum number of backups to keep
            
        Returns:
            Result with number of deleted backup files
        """
        try:
            backup_dir = os.path.dirname(self.settings_file)
            deleted_count = 0
            
            # List all backup files
            files = []
            try:
                files = [f for f in os.listdir(backup_dir) if f.startswith("settings_backup_") and f.endswith(".json")]
            except FileNotFoundError:
                # Directory doesn't exist yet
                os.makedirs(backup_dir, exist_ok=True)
                return Result.success(data={"deleted_count": 0})
            
            # Sort by timestamp (oldest first)
            files.sort()
            
            # Calculate how many to delete
            if len(files) <= max_backups:
                return Result.success(data={"deleted_count": 0})
                
            files_to_delete = files[:len(files) - max_backups]
            
            # Delete old backup files
            for filename in files_to_delete:
                file_path = os.path.join(backup_dir, filename)
                try:
                    os.remove(file_path)
                    deleted_count += 1
                    self.logger.debug(f"Deleted old backup file: {filename}")
                except Exception as e:
                    self.logger.warning(error_message(
                        module_id=MODULE_ID,
                        error_type="DELETE_BACKUP_FILE_ERROR",
                        details=f"Error deleting backup file {filename}: {str(e)}",
                        location="cleanup_old_backups()"
                    ))
            
            self.logger.info(f"Cleaned up {deleted_count} old backup files")
            return Result.success(data={"deleted_count": deleted_count})
        except Exception as e:
            self.logger.error(error_message(
                module_id=MODULE_ID,
                error_type="CLEANUP_BACKUPS_ERROR",
                details=f"Error cleaning up old backups: {str(e)}",
                location="cleanup_old_backups()"
            ))
            return Result.error(
                code="CLEANUP_BACKUPS_ERROR",
                message="Error cleaning up old backups",
                details={"error": str(e)}
            )
    
    async def get_file_paths(self) -> Result:
        """
        Get absolute paths to all settings files.
        
        Returns:
            Result with dictionary of file paths
        """
        try:
            paths = {
                "settings_file": os.path.relpath(self.settings_file),
                "client_config_file": os.path.relpath(self.client_config_file),
                "metadata_file": os.path.relpath(self.metadata_file)
            }
            return Result.success(data=paths)
        except Exception as e:
            self.logger.error(error_message(
                module_id=MODULE_ID,
                error_type="GET_FILE_PATHS_ERROR",
                details=f"Error getting file paths: {str(e)}",
                location="get_file_paths()"
            ))
            return Result.error(
                code="GET_FILE_PATHS_ERROR",
                message="Error getting file paths",
                details={"error": str(e)}
            )

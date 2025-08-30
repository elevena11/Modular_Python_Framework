"""
Example module demonstrating the enhanced settings features.
"""

import logging
from typing import Dict, Any

logger = logging.getLogger("modular.example_enhanced")

def initialize(app_context):
    """
    Initialize module with enhanced settings features.
    
    Demonstrates:
    - Settings validation
    - UI metadata
    - Settings migration
    """
    logger.info("Initializing enhanced example module")
    
    # Register a settings migration first (for existing installations)
    if hasattr(app_context, 'register_settings_migration'):
        app_context.register_settings_migration(
            module_id="standard.example_enhanced",
            from_version="1.0.0",
            to_version="2.0.0",
            migration_function=migrate_v1_to_v2
        )
    
    # Register settings with validation schema and UI metadata
    app_context.register_module_settings(
        module_id="standard.example_enhanced",
        default_settings={
            # API Settings
            "api_url": "http://localhost:5000/api",
            "api_key": "",
            "timeout": 30,
            
            # Connection Settings
            "max_connections": 10,
            "retry_limit": 3,
            "connection_timeout": 5,
            
            # Feature Flags
            "enable_feature_x": True,
            "enable_feature_y": False,
            "enable_logging": True,
            
            # User Preferences
            "theme": "light",
            "language": "en",
            "auto_save": True
        },
        validation_schema={
            # API Settings
            "api_url": {
                "type": "string",
                "pattern": "^https?://.*$",
                "description": "URL for the API endpoint"
            },
            "api_key": {
                "type": "string",
                "description": "API key for authentication"
            },
            "timeout": {
                "type": "int",
                "min": 1,
                "max": 3600,
                "description": "Request timeout in seconds"
            },
            
            # Connection Settings
            "max_connections": {
                "type": "int",
                "min": 1,
                "max": 100,
                "description": "Maximum number of concurrent connections"
            },
            "retry_limit": {
                "type": "int",
                "min": 0,
                "max": 10,
                "description": "Maximum number of retry attempts"
            },
            "connection_timeout": {
                "type": "int",
                "min": 1,
                "max": 60,
                "description": "Connection timeout in seconds"
            },
            
            # Feature Flags
            "enable_feature_x": {
                "type": "bool",
                "description": "Enable Feature X"
            },
            "enable_feature_y": {
                "type": "bool",
                "description": "Enable Feature Y"
            },
            "enable_logging": {
                "type": "bool",
                "description": "Enable detailed logging"
            },
            
            # User Preferences
            "theme": {
                "type": "string",
                "enum": ["light", "dark", "system"],
                "description": "UI theme"
            },
            "language": {
                "type": "string",
                "enum": ["en", "es", "fr", "de", "ja", "zh"],
                "description": "Preferred language"
            },
            "auto_save": {
                "type": "bool",
                "description": "Automatically save changes"
            }
        },
        ui_metadata={
            # API Settings
            "api_url": {
                "display_name": "API URL",
                "description": "URL for the API endpoint",
                "input_type": "text",
                "category": "API Configuration",
                "order": 10
            },
            "api_key": {
                "display_name": "API Key",
                "description": "API key for authentication",
                "input_type": "password",
                "category": "API Configuration",
                "order": 20
            },
            "timeout": {
                "display_name": "Request Timeout",
                "description": "Maximum time to wait for API responses (seconds)",
                "input_type": "slider",
                "min": 1,
                "max": 60,
                "step": 1,
                "category": "API Configuration",
                "order": 30
            },
            
            # Connection Settings
            "max_connections": {
                "display_name": "Maximum Connections",
                "description": "Maximum number of concurrent connections",
                "input_type": "number",
                "category": "Connection Settings",
                "order": 10
            },
            "retry_limit": {
                "display_name": "Retry Limit",
                "description": "Maximum number of retry attempts",
                "input_type": "number",
                "category": "Connection Settings",
                "order": 20
            },
            "connection_timeout": {
                "display_name": "Connection Timeout",
                "description": "Time to wait for connection establishment (seconds)",
                "input_type": "number",
                "category": "Connection Settings",
                "order": 30
            },
            
            # Feature Flags
            "enable_feature_x": {
                "display_name": "Enable Feature X",
                "description": "Activates experimental Feature X",
                "input_type": "checkbox",
                "category": "Features",
                "order": 10
            },
            "enable_feature_y": {
                "display_name": "Enable Feature Y",
                "description": "Activates experimental Feature Y",
                "input_type": "checkbox",
                "category": "Features",
                "order": 20
            },
            "enable_logging": {
                "display_name": "Enable Detailed Logging",
                "description": "Records detailed operational logs",
                "input_type": "checkbox",
                "category": "Features",
                "order": 30
            },
            
            # User Preferences
            "theme": {
                "display_name": "UI Theme",
                "description": "Visual theme for the user interface",
                "input_type": "dropdown",
                "options": [
                    {"value": "light", "label": "Light"},
                    {"value": "dark", "label": "Dark"},
                    {"value": "system", "label": "System Default"}
                ],
                "category": "User Preferences",
                "order": 10
            },
            "language": {
                "display_name": "Language",
                "description": "Preferred language for the interface",
                "input_type": "dropdown",
                "options": [
                    {"value": "en", "label": "English"},
                    {"value": "es", "label": "Español"},
                    {"value": "fr", "label": "Français"},
                    {"value": "de", "label": "Deutsch"},
                    {"value": "ja", "label": "日本語"},
                    {"value": "zh", "label": "中文"}
                ],
                "category": "User Preferences",
                "order": 20
            },
            "auto_save": {
                "display_name": "Auto-Save Changes",
                "description": "Automatically save changes without prompting",
                "input_type": "checkbox",
                "category": "User Preferences",
                "order": 30
            }
        },
        version="2.0.0"  # Current settings version
    )
    
    # Create and register the service
    service = EnhancedExampleService(app_context)
    app_context.register_service("example_enhanced_service", service)
    
    # Register for phase 2 setup
    app_context.register_module_setup_hook(
        "standard.example_enhanced", 
        setup_module
    )
    
    logger.info("Enhanced example module initialization complete (Phase 1)")

async def setup_module(app_context):
    """Phase 2 setup for the enhanced example module."""
    logger.info("Starting Phase 2 setup for enhanced example module")
    
    # Get our settings with all overrides applied
    settings = app_context.get_module_settings("standard.example_enhanced")
    
    # Access service and apply settings
    service = app_context.get_service("example_enhanced_service")
    if service:
        await service.configure(settings)
    
    logger.info("Enhanced example module Phase 2 setup complete")

def migrate_v1_to_v2(old_settings):
    """
    Migrate settings from v1.0.0 to v2.0.0.
    
    Changes:
    - Renamed 'api_timeout' to 'timeout'
    - Added new 'connection_timeout' setting
    - Added 'theme' and 'language' settings
    """
    new_settings = old_settings.copy()
    
    # Rename api_timeout to timeout
    if 'api_timeout' in old_settings:
        new_settings['timeout'] = old_settings['api_timeout']
        del new_settings['api_timeout']
    
    # Add new connection_timeout setting
    if 'connection_timeout' not in old_settings:
        new_settings['connection_timeout'] = 5
    
    # Add new user preference settings
    if 'theme' not in old_settings:
        new_settings['theme'] = 'light'
    
    if 'language' not in old_settings:
        new_settings['language'] = 'en'
    
    if 'auto_save' not in old_settings:
        new_settings['auto_save'] = True
    
    return new_settings

class EnhancedExampleService:
    """Example service demonstrating enhanced settings usage."""
    
    def __init__(self, app_context):
        """Initialize with application context."""
        self.app_context = app_context
        self.logger = logger
        self.settings = {}
        self.configured = False
    
    async def configure(self, settings: Dict[str, Any]):
        """Configure the service with settings."""
        self.settings = settings
        
        # Log settings application
        self.logger.info("Configuring service with settings:")
        for category in ["API Configuration", "Connection Settings", "Features"]:
            self.logger.info(f"  {category}:")
            for key, value in settings.items():
                # Use UI metadata to categorize if available
                metadata = self._get_setting_metadata(key)
                if metadata.get("category") == category:
                    self.logger.info(f"    {metadata.get('display_name', key)}: {value}")
        
        self.configured = True
        return True
    
    def _get_setting_metadata(self, key):
        """Get UI metadata for a setting."""
        ui_metadata = self.app_context.get_settings_ui_metadata("standard.example_enhanced")
        return ui_metadata.get(key, {})
    
    async def perform_operation(self, operation_type: str, parameters: Dict[str, Any]):
        """Example method that uses settings."""
        if not self.configured:
            # Get settings on demand if not already configured
            settings = self.app_context.get_module_settings("standard.example_enhanced")
            await self.configure(settings)
        
        # Use appropriate settings based on operation type
        if operation_type == "api_request":
            return await self._perform_api_request(parameters)
        elif operation_type == "data_processing":
            return await self._perform_data_processing(parameters)
        else:
            return {"success": False, "error": f"Unknown operation type: {operation_type}"}
    
    async def _perform_api_request(self, parameters):
        """Perform API request using API settings."""
        # Use API settings
        api_url = self.settings["api_url"]
        api_key = self.settings["api_key"]
        timeout = self.settings["timeout"]
        
        self.logger.info(f"Making API request to {api_url} with timeout {timeout}s")
        
        # In a real implementation, we would use httpx to make the request
        # For this example, we'll just simulate it
        
        # Check if logging is enabled (feature flag)
        if self.settings["enable_logging"]:
            self.logger.info(f"Request parameters: {parameters}")
        
        # Simulate API call
        return {
            "success": True,
            "message": "API request completed",
            "parameters": parameters
        }
    
    async def _perform_data_processing(self, parameters):
        """Perform data processing using appropriate settings."""
        # Use feature flags
        enable_feature_x = self.settings["enable_feature_x"]
        enable_feature_y = self.settings["enable_feature_y"]
        
        self.logger.info(f"Processing data with Feature X: {enable_feature_x}, Feature Y: {enable_feature_y}")
        
        # Use connection settings
        max_connections = self.settings["max_connections"]
        retry_limit = self.settings["retry_limit"]
        
        # Check if logging is enabled (feature flag)
        if self.settings["enable_logging"]:
            self.logger.info(f"Processing parameters: {parameters}")
            self.logger.info(f"Using max connections: {max_connections}, retry limit: {retry_limit}")
        
        # Simulate data processing
        result = {
            "success": True,
            "message": "Data processing completed",
            "features_used": []
        }
        
        if enable_feature_x:
            result["features_used"].append("feature_x")
        
        if enable_feature_y:
            result["features_used"].append("feature_y")
        
        return result

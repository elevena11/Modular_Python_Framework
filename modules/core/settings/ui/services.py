"""
modules/core/settings/ui/services.py
Framework-agnostic services for the new Pydantic-based settings UI.
"""

import logging
import requests
from typing import Dict, List, Any, Optional

logger = logging.getLogger("modules.core.settings.ui.services")

class SettingsUIService:
    """Service class for interacting with the new Pydantic settings API."""
    
    @staticmethod
    def get_system_status(base_url: str) -> Dict[str, Any]:
        """Get the settings system status."""
        try:
            response = requests.get(f"{base_url}/api/v1/settings/status")
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Error getting system status: {response.text}")
                return {"error": f"HTTP {response.status_code}: {response.text}"}
        except Exception as e:
            logger.error(f"Error getting system status: {str(e)}")
            return {"error": str(e)}
    
    @staticmethod
    def get_module_info(base_url: str) -> Dict[str, Any]:
        """Get module information."""
        try:
            response = requests.get(f"{base_url}/api/v1/settings/info")
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Error getting module info: {response.text}")
                return {"error": f"HTTP {response.status_code}: {response.text}"}
        except Exception as e:
            logger.error(f"Error getting module info: {str(e)}")
            return {"error": str(e)}
    
    @staticmethod
    def get_all_settings(base_url: str) -> Dict[str, Any]:
        """Get all settings for all modules."""
        try:
            response = requests.get(f"{base_url}/api/v1/settings/settings")
            if response.status_code == 200:
                data = response.json()
                # Transform the data structure to match what the UI expects
                return data.get("modules", {})
            else:
                logger.error(f"Error getting all settings: {response.text}")
                return {}
        except Exception as e:
            logger.error(f"Error getting all settings: {str(e)}")
            return {}
    
    @staticmethod
    def get_module_settings(base_url: str, module_id: str) -> Dict[str, Any]:
        """Get settings for a specific module."""
        try:
            response = requests.get(f"{base_url}/api/v1/settings/settings/{module_id}")
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Error getting module settings for {module_id}: {response.text}")
                return {"error": f"HTTP {response.status_code}: {response.text}"}
        except Exception as e:
            logger.error(f"Error getting module settings for {module_id}: {str(e)}")
            return {"error": str(e)}
    
    @staticmethod
    def set_user_preference(base_url: str, module_id: str, setting_key: str, value: Any) -> Dict[str, Any]:
        """Set a user preference for a specific setting."""
        try:
            response = requests.put(
                f"{base_url}/api/v1/settings/settings/{module_id}/{setting_key}",
                json={"value": value}
            )
            
            if response.status_code == 200:
                return {"success": True, "message": "Setting updated successfully"}
            else:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                logger.error(f"Error setting user preference for {module_id}.{setting_key}: {error_msg}")
                return {"success": False, "error": error_msg}
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error setting user preference for {module_id}.{setting_key}: {error_msg}")
            return {"success": False, "error": error_msg}
    
    @staticmethod
    def clear_user_preference(base_url: str, module_id: str, setting_key: str) -> Dict[str, Any]:
        """Clear a user preference for a specific setting."""
        try:
            response = requests.delete(f"{base_url}/api/v1/settings/settings/{module_id}/{setting_key}")
            
            if response.status_code == 200:
                return {"success": True, "message": "User preference cleared successfully"}
            else:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                logger.error(f"Error clearing user preference for {module_id}.{setting_key}: {error_msg}")
                return {"success": False, "error": error_msg}
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error clearing user preference for {module_id}.{setting_key}: {error_msg}")
            return {"success": False, "error": error_msg}
    
    @staticmethod
    def format_module_name(module_id: str) -> str:
        """Format module ID into a readable name."""
        parts = module_id.split(".")
        return " ".join(part.capitalize() for part in parts)
    
    @staticmethod
    def format_setting_name(setting_key: str) -> str:
        """Format setting key into a readable name."""
        return setting_key.replace("_", " ").title()
    
    @staticmethod
    def get_setting_type_from_value(value: Any) -> str:
        """Determine the type of a setting value."""
        if isinstance(value, bool):
            return "boolean"
        elif isinstance(value, int):
            return "integer"
        elif isinstance(value, float):
            return "number"
        elif isinstance(value, list):
            return "array"
        elif isinstance(value, dict):
            return "object"
        else:
            return "string"
    
    @staticmethod
    def validate_setting_value(value: Any, setting_schema: Dict[str, Any]) -> tuple[bool, str]:
        """Validate a setting value against its schema."""
        setting_type = setting_schema.get("type", "string")
        enum_values = setting_schema.get("enum", [])
        
        # Check enum values
        if enum_values and value not in enum_values:
            return False, f"Value must be one of: {', '.join(map(str, enum_values))}"
        
        # Basic type checking
        try:
            if setting_type == "boolean" and not isinstance(value, bool):
                bool(value)  # Test if convertible
            elif setting_type == "integer" and not isinstance(value, int):
                int(value)  # Test if convertible
            elif setting_type == "number" and not isinstance(value, (int, float)):
                float(value)  # Test if convertible
        except (ValueError, TypeError):
            return False, f"Value cannot be converted to {setting_type}"
        
        return True, ""
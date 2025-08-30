"""
modules/core/settings/ui/services.py
Framework-agnostic services for the settings UI.
"""

import logging
import requests
from typing import Dict, List, Any, Optional, Tuple

logger = logging.getLogger("modular.core.settings.ui.services")

def load_all_settings(base_url: str) -> Dict[str, Any]:
    """
    Load all settings from the API.
    
    Args:
        base_url: Base URL for the API
        
    Returns:
        Dictionary of all settings or empty dict on error
    """
    try:
        response = requests.get(f"{base_url}/api/v1/settings/")
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"Error loading settings: {response.text}")
            return {}
    except Exception as e:
        logger.error(f"Error loading settings: {str(e)}")
        return {}

def load_settings_metadata(base_url: str) -> Dict[str, Any]:
    """
    Load settings metadata from the API.
    
    Args:
        base_url: Base URL for the API
        
    Returns:
        Dictionary containing UI metadata and validation schemas
    """
    try:
        # This endpoint would need to exist in the backend
        response = requests.get(f"{base_url}/api/v1/settings/metadata")
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"Error loading settings metadata: {response.text}")
            return {"ui": {}, "validation": {}}
    except Exception as e:
        logger.error(f"Error loading settings metadata: {str(e)}")
        return {"ui": {}, "validation": {}}

def update_module_setting(base_url: str, module_id: str, setting_name: str, value: Any) -> Dict[str, Any]:
    """
    Update a specific setting value.
    
    Args:
        base_url: Base URL for the API
        module_id: Module identifier
        setting_name: Setting name
        value: New setting value
        
    Returns:
        Dictionary with success status and message
    """
    try:
        response = requests.put(
            f"{base_url}/api/v1/settings/{module_id}/{setting_name}",
            json={"value": value}
        )
        
        if response.status_code == 200:
            return {"success": True, "message": "Setting updated successfully"}
        else:
            return {"success": False, "message": f"Error: {response.text}"}
    except Exception as e:
        return {"success": False, "message": f"Error: {str(e)}"}

def get_module_name(module_id: str) -> str:
    """
    Get a user-friendly name for a module ID.
    
    Args:
        module_id: Module identifier (e.g., 'core.database')
        
    Returns:
        User-friendly name (e.g., 'Core Database')
    """
    # Convert from "core.database" to "Core Database"
    parts = module_id.split(".")
    return " ".join(part.capitalize() for part in parts)

def get_setting_type(value: Any) -> str:
    """
    Determine the type of a setting value.
    
    Args:
        value: Setting value
        
    Returns:
        Type string: 'bool', 'int', 'float', 'string', etc.
    """
    if isinstance(value, bool):
        return "bool"
    elif isinstance(value, int):
        return "int"
    elif isinstance(value, float):
        return "float"
    elif isinstance(value, list):
        return "list"
    elif isinstance(value, dict):
        return "dict"
    else:
        return "string"

def group_settings_by_category(module_settings: Dict[str, Any], ui_metadata: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """
    Group settings by category using UI metadata.
    
    Args:
        module_settings: Dictionary of module settings
        ui_metadata: UI metadata for the module
        
    Returns:
        Dictionary of settings grouped by category
    """
    categories = {}
    
    for setting_name, setting_value in module_settings.items():
        # Get metadata for this setting
        setting_metadata = ui_metadata.get(setting_name, {})
        
        # Get category, default to "General"
        category = setting_metadata.get("category", "General")
        
        if category not in categories:
            categories[category] = {}
        
        # Combine setting value with its metadata
        combined_info = {
            "value": setting_value,
            "type": get_setting_type(setting_value)
        }
        
        # Debug: Log original setting value
        if setting_name in ["llm.default_provider", "sqlite_journal_mode", "sqlite_synchronous"]:
            logger.info(f"DEBUG {setting_name}: original value={setting_value} (type: {type(setting_value)})")
        
        # Add metadata fields if available
        if setting_metadata:
            for metadata_key, metadata_value in setting_metadata.items():
                if metadata_key not in combined_info:
                    combined_info[metadata_key] = metadata_value
                    
        # Debug: Log final combined info
        if setting_name in ["llm.default_provider", "sqlite_journal_mode", "sqlite_synchronous"]:
            logger.info(f"DEBUG {setting_name}: final value={combined_info.get('value')} (type: {type(combined_info.get('value'))})")
            if "options" in combined_info:
                logger.info(f"DEBUG {setting_name}: has options={len(combined_info['options'])} items")
        
        categories[category][setting_name] = combined_info
    
    return categories

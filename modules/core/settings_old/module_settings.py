"""
modules/core/settings/module_settings.py
Updated: April 4, 2025
Standardized with proper MODULE_ID prefixing and error handling
"""

import logging
import traceback
from typing import Dict, Any

from core.error_utils import error_message, Result

# Define MODULE_ID matching manifest.json at the top of the file
MODULE_ID = "core.settings"
# Use MODULE_ID directly for the logger name
logger = logging.getLogger(MODULE_ID)

# Default settings configuration
DEFAULT_SETTINGS = {
    "auto_backup_enabled": True,
    "backup_frequency_days": 7,
    "backup_retention_count": 5,
    "backup_on_version_change": True
}

# Validation schema
VALIDATION_SCHEMA = {
    "auto_backup_enabled": {
        "type": "bool",
        "description": "Whether to automatically backup settings files periodically"
    },
    "backup_frequency_days": {
        "type": "int",
        "min": 1,
        "max": 90,
        "description": "How often backups should be created (in days)"
    },
    "backup_retention_count": {
        "type": "int",
        "min": 1,
        "max": 50,
        "description": "How many backup files to keep before deleting older ones"
    },
    "backup_on_version_change": {
        "type": "bool",
        "description": "Whether to create a backup when module versions change"
    }
}

# UI metadata
UI_METADATA = {
    "auto_backup_enabled": {
        "display_name": "Enable Automatic Backups",
        "description": "Automatically back up settings files on a schedule",
        "input_type": "checkbox",
        "category": "Backup Management"
    },
    "backup_frequency_days": {
        "display_name": "Backup Frequency (Days)",
        "description": "Number of days between automatic backups",
        "input_type": "number",
        "category": "Backup Management"
    },
    "backup_retention_count": {
        "display_name": "Maximum Backup Files",
        "description": "Number of backup files to retain before removing oldest",
        "input_type": "number",
        "category": "Backup Management"
    },
    "backup_on_version_change": {
        "display_name": "Backup on Version Change",
        "description": "Create a backup when a module's version changes",
        "input_type": "checkbox",
        "category": "Backup Management"
    }
}

async def register_settings(app_context):
    """
    Register module settings with the application context.
    
    Args:
        app_context: Application context
        
    Returns:
        True if registration successful, False otherwise
    """
    try:
        # Register with the application context
        success = await app_context.register_module_settings(
            module_id=MODULE_ID,
            default_settings=DEFAULT_SETTINGS,
            validation_schema=VALIDATION_SCHEMA,
            ui_metadata=UI_METADATA
        )
        
        if success:
            logger.info(f"{MODULE_ID} module settings registered successfully")
        else:
            logger.warning(error_message(
                module_id=MODULE_ID,
                error_type="REGISTRATION_FAILED",
                details="Failed to register settings module settings",
                location="register_settings()"
            ))
            
        return success
        
    except Exception as e:
        logger.error(error_message(
            module_id=MODULE_ID,
            error_type="REGISTRATION_ERROR",
            details=f"Error registering settings module settings: {str(e)}",
            location="register_settings()"
        ))
        logger.error(traceback.format_exc())
        return False

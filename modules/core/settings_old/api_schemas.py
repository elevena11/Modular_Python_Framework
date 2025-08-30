"""
modules/core/settings/api_schemas.py
Updated: April 4, 2025
API schemas for settings module with standardized error handling
"""

import logging
import traceback
from typing import Dict, List, Any, Optional, Union
from pydantic import BaseModel, Field, field_validator, model_validator

from core.error_utils import error_message

# Define MODULE_ID matching manifest.json at the top of the file
MODULE_ID = "core.settings"
# Use MODULE_ID directly for the logger name
logger = logging.getLogger(MODULE_ID)

# Define standardized error codes
ERROR_CODES = {
    # Data access errors
    "SETTING_NOT_FOUND": "Requested setting not found",
    "MODULE_NOT_FOUND": "Module not found or not registered",
    "BACKUP_NOT_FOUND": "Backup not found",
    
    # Validation errors
    "VALIDATION_ERROR": "Validation error in setting data",
    "INVALID_VALUE_TYPE": "Invalid value type for setting",
    "OUT_OF_RANGE": "Value out of allowed range",
    
    # Operation errors
    "UPDATE_FAILED": "Failed to update setting",
    "RESET_FAILED": "Failed to reset setting",
    "BACKUP_FAILED": "Failed to create backup",
    "RESTORE_FAILED": "Failed to restore from backup",
    
    # System errors
    "INTERNAL_ERROR": "Internal server error",
    "DB_ERROR": "Database operation error",
    "FILE_IO_ERROR": "File I/O error"
}

class SettingValueRequest(BaseModel):
    """
    Request model for updating a setting value.
    
    This model is used when updating a setting via the API.
    The value can be of any type (string, number, boolean, list, dictionary).
    """
    value: Any = Field(
        ..., 
        description="Setting value to update (can be string, number, boolean, list, or object)"
    )
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {"value": "example string"},
                {"value": 100},
                {"value": True},
                {"value": ["item1", "item2"]},
                {"value": {"key1": "value1", "key2": "value2"}}
            ]
        }
    }
    
    # Add validation for common error cases to provide better error messages
    @model_validator(mode='after')
    def validate_value_not_none(self):
        """Validate that value is not None."""
        if self.value is None:
            logger.error(error_message(
                module_id=MODULE_ID,
                error_type="VALIDATION_ERROR",
                details="Setting value cannot be None",
                location="SettingValueRequest.validate_value_not_none()"
            ))
            raise ValueError("Setting value cannot be None")
        return self

class SettingValueResponse(BaseModel):
    """
    Response model for a setting value.
    
    This model is returned when retrieving a specific setting via the API.
    The value can be of any type (string, number, boolean, list, dictionary).
    """
    value: Any = Field(
        ..., 
        description="Setting value (can be string, number, boolean, list, or object)"
    )
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {"value": "example string"},
                {"value": 100},
                {"value": True},
                {"value": ["item1", "item2"]},
                {"value": {"key1": "value1", "key2": "value2"}}
            ]
        }
    }

class SuccessResponse(BaseModel):
    """
    Standard success response.
    
    This model is returned for operations that complete successfully.
    It includes a success flag and an optional message with additional details.
    """
    success: bool = Field(
        True, 
        description="Operation success status"
    )
    message: Optional[str] = Field(
        None, 
        description="Success message with additional details"
    )
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {"success": True, "message": "Operation completed successfully"},
                {"success": True, "message": "Setting updated successfully"}
            ]
        }
    }

class ErrorResponse(BaseModel):
    """
    Standard error response.
    
    This model is returned when an operation fails.
    It includes a standardized status, error code, message, and optional details.
    """
    status: str = Field(
        "error", 
        description="Status indicating an error"
    )
    code: str = Field(
        ..., 
        description="Error code identifying the type of error"
    )
    message: str = Field(
        ..., 
        description="Human-readable error message"
    )
    details: Optional[Dict[str, Any]] = Field(
        None, 
        description="Additional error details for debugging"
    )
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "status": "error",
                    "code": "VALIDATION_ERROR",
                    "message": "Invalid setting value",
                    "details": {"field": "timeout", "error": "Value must be a positive integer"}
                },
                {
                    "status": "error",
                    "code": "SETTING_NOT_FOUND",
                    "message": "Setting core.database.pool_size not found"
                }
            ]
        }
    }
    
    @field_validator('code')
    @classmethod
    def validate_error_code(cls, v):
        """Validate that the error code is recognized."""
        if v not in ERROR_CODES:
            logger.warning(error_message(
                module_id=MODULE_ID,
                error_type="UNKNOWN_ERROR_CODE",
                details=f"Unknown error code: {v}",
                location="ErrorResponse.validate_error_code()"
            ))
        return v

class ValidationErrorDetail(BaseModel):
    """
    Validation error details.
    
    This model provides detailed information about validation errors.
    It maps field names to specific error messages.
    """
    errors: Dict[str, str] = Field(
        ..., 
        description="Validation errors by field name"
    )
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "errors": {
                        "timeout": "Value must be a positive integer",
                        "retry_count": "Value must be between 1 and 10"
                    }
                }
            ]
        }
    }

class SettingsMetadataResponse(BaseModel):
    """
    Response model for settings metadata.
    
    This model is returned when requesting metadata about all module settings.
    It includes validation schemas, UI metadata, and a timestamp.
    """
    validation: Dict[str, Dict[str, Any]] = Field(
        ..., 
        description="Validation schemas by module (module_id -> schema)"
    )
    ui: Dict[str, Dict[str, Any]] = Field(
        ..., 
        description="UI metadata by module (module_id -> metadata)"
    )
    last_updated: str = Field(
        ..., 
        description="Last updated timestamp (ISO format)"
    )
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "validation": {
                        "core.settings": {
                            "auto_backup_enabled": {
                                "type": "bool",
                                "description": "Whether to automatically backup settings files periodically"
                            },
                            "backup_frequency_days": {
                                "type": "int",
                                "min": 1,
                                "max": 90,
                                "description": "How often backups should be created (in days)"
                            }
                        }
                    },
                    "ui": {
                        "core.settings": {
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
                            }
                        }
                    },
                    "last_updated": "2025-04-04T12:00:00Z"
                }
            ]
        }
    }

class ModuleSettingsResponse(BaseModel):
    """
    Response model for module settings.
    
    This model represents the settings for a specific module.
    It includes the module identifier and a dictionary of settings.
    """
    module_id: str = Field(
        ..., 
        description="Module identifier (e.g., 'core.database')"
    )
    settings: Dict[str, Any] = Field(
        ..., 
        description="Module settings as key-value pairs"
    )
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "module_id": "core.settings",
                    "settings": {
                        "auto_backup_enabled": True,
                        "backup_frequency_days": 7,
                        "backup_retention_count": 5,
                        "backup_on_version_change": True
                    }
                }
            ]
        }
    }

class BackupResponse(BaseModel):
    """
    Response model for backup operations.
    
    This model represents a settings backup in the system.
    It includes identifying information and metadata about the backup.
    """
    id: int = Field(
        ..., 
        description="Backup ID"
    )
    date_created: str = Field(
        ..., 
        description="Creation date and time (ISO format)"
    )
    version: str = Field(
        ..., 
        description="Settings version information"
    )
    description: Optional[str] = Field(
        None, 
        description="Backup description (user-provided or auto-generated)"
    )
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": 1,
                    "date_created": "2025-04-04T12:00:00Z",
                    "version": "core.settings@1.0.5,core.database@1.0.5",
                    "description": "Manual backup"
                }
            ]
        }
    }

class CreateBackupRequest(BaseModel):
    """
    Request model for creating a backup.
    
    This model is used when requesting a new settings backup.
    It includes an optional description field.
    """
    description: Optional[str] = Field(
        None, 
        description="Optional description for the backup"
    )
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {"description": "Pre-deployment backup"},
                {"description": "Configuration change backup"}
            ]
        }
    }

class CreateBackupResponse(BaseModel):
    """
    Response model for backup creation.
    
    This model is returned when a backup is successfully created.
    It includes success status, backup ID, and a message.
    """
    success: bool = Field(
        True, 
        description="Operation success status"
    )
    backup_id: int = Field(
        ..., 
        description="ID of the created backup"
    )
    message: str = Field(
        "Backup created successfully", 
        description="Success message"
    )
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "success": True,
                    "backup_id": 42,
                    "message": "Backup created successfully"
                }
            ]
        }
    }

class RestoreBackupResponse(BaseModel):
    """
    Response model for backup restoration.
    
    This model is returned when a backup is successfully restored.
    It includes success status and a message.
    """
    success: bool = Field(
        True, 
        description="Operation success status"
    )
    message: str = Field(
        ..., 
        description="Success message with details about the restoration"
    )
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "success": True,
                    "message": "Successfully restored from backup 42"
                }
            ]
        }
    }

# Error logging helpers with standardized formatting
def log_validation_error(schema_name: str, field_name: str, error_msg: str, value: Any = None):
    """
    Log a validation error with detailed context.
    
    Args:
        schema_name: Name of the schema where validation failed
        field_name: Name of the field that failed validation
        error_msg: Error message describing the validation failure
        value: Optional value that failed validation
    """
    # Format the value for logging, handling potentially large objects
    value_str = str(value)
    if len(value_str) > 100:
        value_str = value_str[:97] + "..."
        
    logger.error(error_message(
        module_id=MODULE_ID,
        error_type="SCHEMA_VALIDATION_ERROR",
        details=f"Validation error in {schema_name}.{field_name}: {error_msg}",
        location="log_validation_error()"
    ))
    # Add traceback for debugging in development
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(f"Validation error traceback:\n{traceback.format_stack()}")

def log_schema_error(schema_name: str, error_msg: str, context: Dict[str, Any] = None):
    """
    Log a general schema-related error.
    
    Args:
        schema_name: Name of the schema with the error
        error_msg: Error message describing the issue
        context: Optional dictionary with additional context
    """
    logger.error(error_message(
        module_id=MODULE_ID,
        error_type="SCHEMA_ERROR",
        details=f"Schema error in {schema_name}: {error_msg}",
        location="log_schema_error()"
    ))
    logger.error(traceback.format_exc())

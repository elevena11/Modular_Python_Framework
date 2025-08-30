"""
modules/core/scheduler/functions/register_cleanup.py
Updated: March 30, 2025
Function to register directory for periodic cleanup
"""

import os
from typing import Dict, Any, Optional

FUNCTION_NAME = "scheduler.register_cleanup"
FUNCTION_DESCRIPTION = "Register a directory for periodic cleanup by the Housekeeper"
FUNCTION_PARAMETERS = {
    "directory": {
        "type": "string", 
        "description": "Path to directory containing files to clean", 
        "required": True
    },
    "pattern": {
        "type": "string", 
        "description": "File matching pattern (e.g., '*.log', 'temp_*')", 
        "default": "*"
    },
    "retention_days": {
        "type": "integer", 
        "description": "Maximum age of files to keep in days (None = no limit)", 
        "required": False
    },
    "max_files": {
        "type": "integer", 
        "description": "Maximum number of files to keep (None = no limit)", 
        "required": False
    },
    "max_size_mb": {
        "type": "integer", 
        "description": "Maximum total size in MB (None = no limit)", 
        "required": False
    },
    "description": {
        "type": "string", 
        "description": "Human-readable description of these files", 
        "required": False
    }
}
FUNCTION_CATEGORIES = ["maintenance", "cleanup"]
FUNCTION_TAGS = ["housekeeper", "cleanup", "maintenance"]
FUNCTION_EXAMPLES = [
    {
        "description": "Register log directory with 30-day retention",
        "parameters": {
            "directory": "./logs",
            "pattern": "*.log",
            "retention_days": 30
        }
    },
    {
        "description": "Register temp directory with size limit",
        "parameters": {
            "directory": "./data/temp",
            "max_size_mb": 500,
            "description": "Temporary data files"
        }
    }
]

async def execute(app_context, parameters, trace_info=None):
    """
    Register a directory for periodic cleanup by the Housekeeper.
    
    This function registers a directory to be cleaned up periodically according
    to specified retention policies (age, count, or size-based).
    
    Args:
        app_context: Application context
        parameters: Parameters for the function
        trace_info: Optional trace information
        
    Returns:
        Dict[str, Any]: Result of the operation
    """
    # Get scheduler service
    scheduler_service = app_context.get_service("scheduler_service")
    if not scheduler_service:
        return {
            "success": False,
            "error": {
                "code": "SERVICE_UNAVAILABLE",
                "message": "Scheduler service not available"
            }
        }
    
    try:
        # Extract parameters
        directory = parameters.get("directory")
        pattern = parameters.get("pattern", "*")
        retention_days = parameters.get("retention_days")
        max_files = parameters.get("max_files")
        max_size_mb = parameters.get("max_size_mb")
        description = parameters.get("description")
        
        # Validate directory
        if not os.path.exists(directory):
            return {
                "success": False,
                "error": {
                    "code": "INVALID_DIRECTORY",
                    "message": f"Directory does not exist: {directory}"
                }
            }
        
        if not os.path.isdir(directory):
            return {
                "success": False,
                "error": {
                    "code": "INVALID_DIRECTORY",
                    "message": f"Path is not a directory: {directory}"
                }
            }
        
        # Ensure at least one retention policy is specified
        if retention_days is None and max_files is None and max_size_mb is None:
            # Use default retention days from settings
            settings = await app_context.get_module_settings("core.scheduler")
            retention_days = settings.get("housekeeper_default_retention", 30)
        
        # Determine module_id from calling context if possible
        function_client = app_context.get_service("function_execution_service")
        module_id = None
        if function_client:
            # Try to get the calling module from the function call context
            call_info = getattr(function_client, "current_call_info", {})
            if isinstance(call_info, dict):
                module_id = call_info.get("source_module", "unknown")
        
        # Register with the Housekeeper
        registration_id = await scheduler_service.register_cleanup(
            directory=directory,
            pattern=pattern,
            retention_days=retention_days,
            max_files=max_files,
            max_size_mb=max_size_mb,
            description=description,
            module_id=module_id
        )
        
        # Return success
        return {
            "success": True,
            "registration_id": registration_id,
            "message": f"Directory {directory} registered for cleanup",
            "details": {
                "pattern": pattern,
                "retention_days": retention_days,
                "max_files": max_files,
                "max_size_mb": max_size_mb
            }
        }
    
    except ValueError as e:
        # Handle validation errors
        return {
            "success": False,
            "error": {
                "code": "VALIDATION_ERROR",
                "message": str(e)
            }
        }
    except RuntimeError as e:
        # Handle runtime errors
        return {
            "success": False,
            "error": {
                "code": "RUNTIME_ERROR",
                "message": str(e)
            }
        }
    except Exception as e:
        # Handle unexpected errors
        return {
            "success": False,
            "error": {
                "code": "UNEXPECTED_ERROR",
                "message": f"Unexpected error: {str(e)}"
            }
        }

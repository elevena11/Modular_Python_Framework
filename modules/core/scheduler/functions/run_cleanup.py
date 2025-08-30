"""
modules/core/scheduler/functions/run_cleanup.py
Updated: March 30, 2025
Function to run the housekeeper cleanup
"""

from typing import Dict, Any, Optional

FUNCTION_NAME = "scheduler.run_cleanup"
FUNCTION_DESCRIPTION = "Run the housekeeper cleanup operation manually"
FUNCTION_PARAMETERS = {
    "registration_id": {
        "type": "string", 
        "description": "Optional ID of specific cleanup config to run (all configs if omitted)", 
        "required": False
    },
    "dry_run": {
        "type": "boolean", 
        "description": "If true, only report what would be deleted without actually deleting", 
        "default": False
    }
}
FUNCTION_CATEGORIES = ["maintenance", "cleanup"]
FUNCTION_TAGS = ["housekeeper", "cleanup", "maintenance"]
FUNCTION_EXAMPLES = [
    {
        "description": "Run all cleanup configurations",
        "parameters": {}
    },
    {
        "description": "Run a specific cleanup configuration",
        "parameters": {
            "registration_id": "550e8400-e29b-41d4-a716-446655440000"
        }
    },
    {
        "description": "Run in dry-run mode (no deletion)",
        "parameters": {
            "dry_run": True
        }
    }
]

async def execute(app_context, parameters, trace_info=None):
    """
    Run the housekeeper cleanup operation manually.
    
    This function triggers a cleanup operation using the registered cleanup
    configurations. It can run all configs or a specific one, and supports
    dry-run mode.
    
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
        registration_id = parameters.get("registration_id")
        dry_run = parameters.get("dry_run", False)
        
        # Run the cleanup
        result = await scheduler_service.run_cleanup(registration_id, dry_run)
        
        # If result already has success field, return it directly
        if "success" in result:
            return result
        
        # Otherwise format result
        return {
            "success": True,
            "message": "Cleanup operation completed successfully",
            "details": {
                "dry_run": dry_run,
                "registration_id": registration_id,
                "results": result
            }
        }
    
    except Exception as e:
        # Return error result
        return {
            "success": False,
            "error": {
                "code": "CLEANUP_ERROR",
                "message": f"Error running cleanup: {str(e)}"
            }
        }

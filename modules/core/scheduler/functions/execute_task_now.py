"""
modules/core/scheduler/functions/execute_task_now.py
Updated: March 30, 2025
Function to execute a scheduled task immediately
"""

from typing import Dict, Any, Optional
from datetime import datetime

FUNCTION_NAME = "scheduler.execute_task_now"
FUNCTION_DESCRIPTION = "Execute a scheduled task immediately, regardless of its scheduled time"
FUNCTION_PARAMETERS = {
    "event_id": {
        "type": "string", 
        "description": "ID of the scheduled task to execute", 
        "required": True
    }
}
FUNCTION_CATEGORIES = ["scheduling", "maintenance"]
FUNCTION_TAGS = ["scheduler", "task", "execute", "immediate"]
FUNCTION_EXAMPLES = [
    {
        "description": "Execute a task immediately",
        "parameters": {
            "event_id": "550e8400-e29b-41d4-a716-446655440000"
        }
    }
]

async def execute(app_context, parameters, trace_info=None):
    """
    Execute a scheduled task immediately.
    
    This function runs a scheduled task immediately, regardless of its scheduled
    execution time. For recurring tasks, this is an additional execution that
    doesn't affect the regular schedule.
    
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
        event_id = parameters.get("event_id")
        
        # Check if event exists
        event = await scheduler_service.get_event(event_id)
        if not event:
            return {
                "success": False,
                "error": {
                    "code": "EVENT_NOT_FOUND",
                    "message": f"Task with ID {event_id} not found"
                }
            }
        
        # Check if already running
        if event.get("status") == "running":
            return {
                "success": False,
                "error": {
                    "code": "ALREADY_RUNNING",
                    "message": f"Task '{event.get('name')}' is already running"
                }
            }
        
        # Execute the event
        result = await scheduler_service.execute_event_now(event_id)
        
        # Check result
        if not result.get("success", False):
            error = result.get("error", {})
            return {
                "success": False,
                "error": {
                    "code": error.get("code", "EXECUTION_FAILED"),
                    "message": error.get("message", f"Failed to execute task {event_id}")
                }
            }
        
        # Return success result
        return {
            "success": True,
            "message": f"Task '{event.get('name')}' execution started",
            "details": {
                "event_id": event_id,
                "name": event.get("name"),
                "function_name": event.get("function_name")
            }
        }
    
    except Exception as e:
        # Return error result
        return {
            "success": False,
            "error": {
                "code": "EXECUTION_ERROR",
                "message": f"Error executing task: {str(e)}"
            }
        }

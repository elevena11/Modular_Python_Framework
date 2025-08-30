"""
modules/core/scheduler/functions/cancel_task.py
Updated: March 30, 2025
Function to cancel a scheduled task
"""

from typing import Dict, Any

FUNCTION_NAME = "scheduler.cancel_task"
FUNCTION_DESCRIPTION = "Cancel a scheduled task and prevent it from running"
FUNCTION_PARAMETERS = {
    "event_id": {
        "type": "string", 
        "description": "ID of the scheduled task to cancel", 
        "required": True
    }
}
FUNCTION_CATEGORIES = ["scheduling", "maintenance"]
FUNCTION_TAGS = ["scheduler", "task", "cancel"]
FUNCTION_EXAMPLES = [
    {
        "description": "Cancel a scheduled task",
        "parameters": {
            "event_id": "550e8400-e29b-41d4-a716-446655440000"
        }
    }
]

async def execute(app_context, parameters, trace_info=None):
    """
    Cancel a scheduled task.
    
    This function permanently cancels a scheduled task, preventing it from
    running. This operation cannot be undone.
    
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
        
        # Delete the event
        success = await scheduler_service.delete_event(event_id)
        
        if not success:
            return {
                "success": False,
                "error": {
                    "code": "CANCELLATION_FAILED",
                    "message": f"Failed to cancel task {event_id}"
                }
            }
        
        # Return success result
        return {
            "success": True,
            "message": f"Task '{event.get('name')}' has been canceled",
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
                "code": "CANCELLATION_ERROR",
                "message": f"Error canceling task: {str(e)}"
            }
        }

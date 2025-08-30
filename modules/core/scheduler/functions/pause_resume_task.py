"""
modules/core/scheduler/functions/pause_resume_task.py
Updated: March 30, 2025
Function to pause or resume a scheduled task
"""

from typing import Dict, Any

FUNCTION_NAME = "scheduler.pause_resume_task"
FUNCTION_DESCRIPTION = "Pause or resume a scheduled task"
FUNCTION_PARAMETERS = {
    "event_id": {
        "type": "string", 
        "description": "ID of the scheduled task", 
        "required": True
    },
    "action": {
        "type": "string", 
        "description": "Action to perform: 'pause' or 'resume'", 
        "required": True
    }
}
FUNCTION_CATEGORIES = ["scheduling", "maintenance"]
FUNCTION_TAGS = ["scheduler", "task", "pause", "resume"]
FUNCTION_EXAMPLES = [
    {
        "description": "Pause a scheduled task",
        "parameters": {
            "event_id": "550e8400-e29b-41d4-a716-446655440000",
            "action": "pause"
        }
    },
    {
        "description": "Resume a paused task",
        "parameters": {
            "event_id": "550e8400-e29b-41d4-a716-446655440000",
            "action": "resume"
        }
    }
]

async def execute(app_context, parameters, trace_info=None):
    """
    Pause or resume a scheduled task.
    
    This function pauses or resumes a scheduled task. A paused task will not
    run until it is resumed.
    
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
        action = parameters.get("action")
        
        # Validate action
        if action not in ("pause", "resume"):
            return {
                "success": False,
                "error": {
                    "code": "INVALID_ACTION",
                    "message": "Action must be 'pause' or 'resume'"
                }
            }
        
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
        
        # Check current status
        current_status = event.get("status")
        
        # Pause task
        if action == "pause":
            if current_status == "paused":
                return {
                    "success": False,
                    "error": {
                        "code": "ALREADY_PAUSED",
                        "message": f"Task '{event.get('name')}' is already paused"
                    }
                }
            
            success = await scheduler_service.pause_event(event_id)
            if not success:
                return {
                    "success": False,
                    "error": {
                        "code": "PAUSE_FAILED",
                        "message": f"Failed to pause task {event_id}"
                    }
                }
            
            return {
                "success": True,
                "message": f"Task '{event.get('name')}' has been paused",
                "details": {
                    "event_id": event_id,
                    "name": event.get("name"),
                    "previous_status": current_status,
                    "current_status": "paused"
                }
            }
        
        # Resume task
        else:  # action == "resume"
            if current_status != "paused":
                return {
                    "success": False,
                    "error": {
                        "code": "NOT_PAUSED",
                        "message": f"Task '{event.get('name')}' is not paused (current status: {current_status})"
                    }
                }
            
            success = await scheduler_service.resume_event(event_id)
            if not success:
                return {
                    "success": False,
                    "error": {
                        "code": "RESUME_FAILED",
                        "message": f"Failed to resume task {event_id}"
                    }
                }
            
            return {
                "success": True,
                "message": f"Task '{event.get('name')}' has been resumed",
                "details": {
                    "event_id": event_id,
                    "name": event.get("name"),
                    "previous_status": "paused",
                    "current_status": "pending"
                }
            }
    
    except Exception as e:
        # Return error result
        return {
            "success": False,
            "error": {
                "code": "ACTION_ERROR",
                "message": f"Error performing {action} action: {str(e)}"
            }
        }

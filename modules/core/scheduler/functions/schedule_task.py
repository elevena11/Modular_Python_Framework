"""
modules/core/scheduler/functions/schedule_task.py
Updated: March 30, 2025
Function to schedule a task to run at a specific time
"""

from datetime import datetime
from typing import Dict, Any, Optional

FUNCTION_NAME = "scheduler.schedule_task"
FUNCTION_DESCRIPTION = "Schedule a task to run at a specific time or recurring interval"
FUNCTION_PARAMETERS = {
    "name": {
        "type": "string", 
        "description": "Name of the task", 
        "required": True
    },
    "function_name": {
        "type": "string", 
        "description": "Function to execute", 
        "required": True
    },
    "execution_time": {
        "type": "string", 
        "description": "When to execute (ISO format, e.g. 2025-04-01T12:00:00)", 
        "required": True
    },
    "recurring": {
        "type": "boolean", 
        "description": "Whether this is a recurring task", 
        "default": False
    },
    "interval_type": {
        "type": "string", 
        "description": "For recurring tasks: minutes, hours, days, weeks, months", 
        "required": False
    },
    "interval_value": {
        "type": "integer", 
        "description": "For recurring tasks: number of interval units", 
        "required": False
    },
    "parameters": {
        "type": "object", 
        "description": "Parameters to pass to the function", 
        "default": {}
    },
    "description": {
        "type": "string", 
        "description": "Description of the task", 
        "required": False
    }
}
FUNCTION_CATEGORIES = ["scheduling", "maintenance"]
FUNCTION_TAGS = ["scheduler", "task", "automation"]
FUNCTION_EXAMPLES = [
    {
        "description": "Schedule a one-time task",
        "parameters": {
            "name": "Database backup",
            "function_name": "backup_database",
            "execution_time": "2025-04-01T03:00:00",
            "parameters": {"compress": True}
        }
    },
    {
        "description": "Schedule a recurring task",
        "parameters": {
            "name": "Daily log cleanup",
            "function_name": "cleanup_logs",
            "execution_time": "2025-04-01T00:00:00",
            "recurring": True,
            "interval_type": "days",
            "interval_value": 1
        }
    }
]

async def execute(app_context, parameters, trace_info=None):
    """
    Schedule a task to run at a specific time or recurring interval.
    
    This function calls the scheduler service to create a new scheduled task.
    
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
        name = parameters.get("name")
        function_name = parameters.get("function_name")
        execution_time = parameters.get("execution_time")
        recurring = parameters.get("recurring", False)
        interval_type = parameters.get("interval_type")
        interval_value = parameters.get("interval_value")
        function_params = parameters.get("parameters", {})
        description = parameters.get("description", "")
        
        # Convert execution_time string to datetime
        if isinstance(execution_time, str):
            execution_time = datetime.fromisoformat(execution_time.replace('Z', '+00:00'))
        
        # Validate recurring parameters
        if recurring and (not interval_type or not interval_value):
            return {
                "success": False,
                "error": {
                    "code": "MISSING_PARAMETERS",
                    "message": "Recurring tasks require interval_type and interval_value"
                }
            }
        
        # Validate interval_type
        if recurring and interval_type not in ("minutes", "hours", "days", "weeks", "months"):
            return {
                "success": False,
                "error": {
                    "code": "INVALID_PARAMETER",
                    "message": "interval_type must be one of: minutes, hours, days, weeks, months"
                }
            }
        
        # Determine module_id from calling context if possible
        function_client = app_context.get_service("function_execution_service")
        module_id = "unknown"
        if function_client:
            # Try to get the calling module from the function call context
            call_info = getattr(function_client, "current_call_info", {})
            if isinstance(call_info, dict):
                module_id = call_info.get("source_module", "unknown")
        
        # Schedule the task
        event_id = await scheduler_service.schedule_event(
            name=name,
            description=description,
            function_name=function_name,
            next_execution=execution_time,
            recurring=recurring,
            interval_type=interval_type if recurring else None,
            interval_value=interval_value if recurring else None,
            parameters=function_params,
            module_id=module_id
        )
        
        # Return success result
        return {
            "success": True,
            "event_id": event_id,
            "message": f"Task '{name}' scheduled successfully",
            "details": {
                "execution_time": execution_time.isoformat(),
                "recurring": recurring,
                "function_name": function_name
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
    except Exception as e:
        # Return error result
        return {
            "success": False,
            "error": {
                "code": "SCHEDULING_ERROR",
                "message": f"Error scheduling task: {str(e)}"
            }
        }

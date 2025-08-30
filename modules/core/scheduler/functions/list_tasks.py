"""
modules/core/scheduler/functions/list_tasks.py
Updated: March 30, 2025
Function to list scheduled tasks
"""

from typing import Dict, Any, Optional, List

FUNCTION_NAME = "scheduler.list_tasks"
FUNCTION_DESCRIPTION = "List scheduled tasks with optional filtering"
FUNCTION_PARAMETERS = {
    "status": {
        "type": "string", 
        "description": "Filter by status (pending, running, completed, failed, paused)", 
        "required": False
    },
    "module_id": {
        "type": "string", 
        "description": "Filter by module ID", 
        "required": False
    },
    "function_name": {
        "type": "string", 
        "description": "Filter by function name", 
        "required": False
    },
    "recurring_only": {
        "type": "boolean", 
        "description": "Only show recurring tasks", 
        "default": False
    },
    "limit": {
        "type": "integer", 
        "description": "Maximum number of tasks to return", 
        "default": 50
    }
}
FUNCTION_CATEGORIES = ["scheduling", "maintenance"]
FUNCTION_TAGS = ["scheduler", "task", "list"]
FUNCTION_EXAMPLES = [
    {
        "description": "List all scheduled tasks",
        "parameters": {}
    },
    {
        "description": "List only pending tasks",
        "parameters": {
            "status": "pending"
        }
    },
    {
        "description": "List tasks scheduled by a specific module",
        "parameters": {
            "module_id": "core.database"
        }
    },
    {
        "description": "List recurring tasks",
        "parameters": {
            "recurring_only": True
        }
    }
]

async def execute(app_context, parameters, trace_info=None):
    """
    List scheduled tasks with optional filtering.
    
    This function retrieves a list of scheduled tasks from the scheduler service,
    with support for filtering by various criteria.
    
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
        status = parameters.get("status")
        module_id = parameters.get("module_id")
        function_name = parameters.get("function_name")
        recurring_only = parameters.get("recurring_only", False)
        limit = parameters.get("limit", 50)
        
        # Build filters
        filters = {}
        if status:
            filters["status"] = status
        if module_id:
            filters["module_id"] = module_id
        if function_name:
            filters["function_name"] = function_name
        if recurring_only:
            filters["recurring"] = True
        
        # Get events from scheduler
        events = await scheduler_service.get_events(filters, limit)
        
        # Format the response
        formatted_events = []
        for event in events:
            formatted_event = {
                "id": event.get("id"),
                "name": event.get("name"),
                "description": event.get("description"),
                "module_id": event.get("module_id"),
                "function_name": event.get("function_name"),
                "status": event.get("status"),
                "next_execution": event.get("next_execution").isoformat() if event.get("next_execution") else None,
                "recurring": event.get("recurring", False),
                "interval_type": event.get("interval_type"),
                "interval_value": event.get("interval_value"),
                "execution_count": event.get("execution_count", 0),
                "last_execution": event.get("last_execution").isoformat() if event.get("last_execution") else None,
                "created_at": event.get("created_at").isoformat() if event.get("created_at") else None,
            }
            formatted_events.append(formatted_event)
        
        # Return success result
        return {
            "success": True,
            "events": formatted_events,
            "count": len(formatted_events),
            "filters": {
                "status": status,
                "module_id": module_id,
                "function_name": function_name,
                "recurring_only": recurring_only
            }
        }
    
    except Exception as e:
        # Return error result
        return {
            "success": False,
            "error": {
                "code": "LIST_ERROR",
                "message": f"Error listing tasks: {str(e)}"
            }
        }

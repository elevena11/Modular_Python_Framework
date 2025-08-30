"""
modules/core/scheduler/module_settings.py
Updated: April 6, 2025
Settings for scheduler module with standardized validation schema types
"""

import logging
from core.error_utils import error_message

# Module identity - must match manifest.json
MODULE_ID = "core.scheduler"
logger = logging.getLogger(MODULE_ID)

# Default module settings
DEFAULT_SETTINGS = {
    # Scheduler settings
    "enabled": True,
    "check_interval": 1.0,  # How often to check for due events (seconds)
    "max_concurrent_executions": 10,  # Maximum concurrent event executions
    "execution_timeout": 300,  # Default timeout for event execution (seconds)
    "retry_failed_events": True,  # Whether to retry failed events
    "max_retry_attempts": 3,  # Maximum retry attempts for failed events
    "retry_delay": 300,  # Delay before retrying failed events (seconds)
    "retention_days": 30,  # How long to keep execution history (days)
    "auto_cleanup_enabled": True,  # Whether to automatically clean up old executions
    "cleanup_interval_hours": 24,  # How often to run cleanup (hours)
    "allow_past_events": False,  # Whether to allow scheduling events in the past
    "trace_enabled_by_default": True,  # Whether to enable tracing by default
    
    # Housekeeper settings
    "housekeeper_enabled": True,
    "housekeeper_schedule": "0 3 * * *",  # Daily at 3 AM (cron format)
    "housekeeper_default_retention": 30,  # Default retention period in days
    "housekeeper_dry_run": False,  # Run in dry-run mode (no deletion)
    "housekeeper_read_only": False,  # Run in read-only mode (compatibility only)
    "housekeeper_concurrent_cleanups": 3,  # Max concurrent cleanup operations
    "housekeeper_report_enabled": True,  # Generate reports after cleanup
    "housekeeper_report_directory": ""  # Empty = use default in DATA_DIR
}

# Validation schema for settings - updated to use correct type names
VALIDATION_SCHEMA = {
    "enabled": {
        "type": "bool",
        "description": "Whether the scheduler is enabled"
    },
    "check_interval": {
        "type": "float",
        "min": 0.1,
        "max": 60.0,
        "description": "How often to check for due events (seconds)"
    },
    "max_concurrent_executions": {
        "type": "int",
        "min": 1,
        "max": 100,
        "description": "Maximum concurrent event executions"
    },
    "execution_timeout": {
        "type": "int",
        "min": 1,
        "max": 3600,
        "description": "Default timeout for event execution (seconds)"
    },
    "retry_failed_events": {
        "type": "bool",
        "description": "Whether to retry failed events"
    },
    "max_retry_attempts": {
        "type": "int",
        "min": 0,
        "max": 10,
        "description": "Maximum retry attempts for failed events"
    },
    "retry_delay": {
        "type": "int",
        "min": 1,
        "max": 3600,
        "description": "Delay before retrying failed events (seconds)"
    },
    "retention_days": {
        "type": "int",
        "min": 1,
        "max": 365,
        "description": "How long to keep execution history (days)"
    },
    "auto_cleanup_enabled": {
        "type": "bool",
        "description": "Whether to automatically clean up old executions"
    },
    "cleanup_interval_hours": {
        "type": "int",
        "min": 1,
        "max": 168,
        "description": "How often to run cleanup (hours)"
    },
    "allow_past_events": {
        "type": "bool",
        "description": "Whether to allow scheduling events in the past"
    },
    "trace_enabled_by_default": {
        "type": "bool",
        "description": "Whether to enable tracing by default"
    },
    "housekeeper_enabled": {
        "type": "bool",
        "description": "Whether the housekeeper component is enabled"
    },
    "housekeeper_schedule": {
        "type": "string",
        "description": "Cron expression for housekeeper schedule"
    },
    "housekeeper_default_retention": {
        "type": "int",
        "min": 1,
        "max": 365,
        "description": "Default retention period in days"
    },
    "housekeeper_dry_run": {
        "type": "bool",
        "description": "Run in dry-run mode (no deletion)"
    },
    "housekeeper_read_only": {
        "type": "bool",
        "description": "Run in read-only mode (compatibility only)"
    },
    "housekeeper_concurrent_cleanups": {
        "type": "int",
        "min": 1,
        "max": 10,
        "description": "Max concurrent cleanup operations"
    },
    "housekeeper_report_enabled": {
        "type": "bool",
        "description": "Generate reports after cleanup"
    },
    "housekeeper_report_directory": {
        "type": "string",
        "description": "Directory for cleanup reports (empty = default)"
    }
}

# UI metadata for settings display
UI_METADATA = {
    "enabled": {
        "display_name": "Enable Scheduler",
        "description": "Enable or disable the scheduler functionality",
        "input_type": "toggle",
        "category": "General",
        "order": 10
    },
    "check_interval": {
        "display_name": "Check Interval",
        "description": "How often to check for due events (seconds)",
        "input_type": "number",
        "category": "Performance",
        "order": 20
    },
    "max_concurrent_executions": {
        "display_name": "Max Concurrent Executions",
        "description": "Maximum number of events that can run simultaneously",
        "input_type": "number",
        "category": "Performance",
        "order": 30
    },
    "execution_timeout": {
        "display_name": "Execution Timeout",
        "description": "Default timeout for event execution (seconds)",
        "input_type": "number",
        "category": "Execution",
        "order": 40
    },
    "retry_failed_events": {
        "display_name": "Retry Failed Events",
        "description": "Automatically retry events that fail",
        "input_type": "toggle",
        "category": "Execution",
        "order": 50
    },
    "max_retry_attempts": {
        "display_name": "Max Retry Attempts",
        "description": "Maximum number of retry attempts for failed events",
        "input_type": "number",
        "category": "Execution",
        "order": 60
    },
    "retry_delay": {
        "display_name": "Retry Delay",
        "description": "Delay before retrying failed events (seconds)",
        "input_type": "number",
        "category": "Execution",
        "order": 70
    },
    "retention_days": {
        "display_name": "Retention Period",
        "description": "How long to keep execution history (days)",
        "input_type": "number",
        "category": "Maintenance",
        "order": 80
    },
    "auto_cleanup_enabled": {
        "display_name": "Auto-Cleanup",
        "description": "Automatically clean up old execution records",
        "input_type": "toggle",
        "category": "Maintenance",
        "order": 90
    },
    "cleanup_interval_hours": {
        "display_name": "Cleanup Interval",
        "description": "How often to run cleanup (hours)",
        "input_type": "number",
        "category": "Maintenance",
        "order": 100
    },
    "allow_past_events": {
        "display_name": "Allow Past Events",
        "description": "Allow scheduling events in the past",
        "input_type": "toggle",
        "category": "Scheduling",
        "order": 110
    },
    "trace_enabled_by_default": {
        "display_name": "Enable Tracing",
        "description": "Enable trace logging for events by default",
        "input_type": "toggle",
        "category": "Debugging",
        "order": 120
    },
    "housekeeper_enabled": {
        "display_name": "Enable Housekeeper",
        "description": "Enable the Housekeeper component for centralized cleanup",
        "input_type": "toggle",
        "category": "Housekeeper",
        "order": 130
    },
    "housekeeper_schedule": {
        "display_name": "Housekeeper Schedule",
        "description": "Cron expression for when to run Housekeeper (e.g., '0 3 * * *' for 3 AM daily)",
        "input_type": "text",
        "category": "Housekeeper",
        "order": 140
    },
    "housekeeper_default_retention": {
        "display_name": "Default Retention",
        "description": "Default retention period in days for cleanup tasks",
        "input_type": "number",
        "category": "Housekeeper",
        "order": 150
    },
    "housekeeper_dry_run": {
        "display_name": "Dry Run Mode",
        "description": "Report what would be deleted without actually deleting",
        "input_type": "toggle",
        "category": "Housekeeper",
        "order": 160
    },
    "housekeeper_concurrent_cleanups": {
        "display_name": "Concurrent Cleanups",
        "description": "Maximum number of concurrent cleanup operations",
        "input_type": "number",
        "category": "Housekeeper",
        "order": 170
    },
    "housekeeper_report_enabled": {
        "display_name": "Generate Reports",
        "description": "Generate detailed reports after cleanup operations",
        "input_type": "toggle",
        "category": "Housekeeper",
        "order": 180
    }
}

async def register_settings(app_context):
    """
    Register module settings with the application context.
    
    Args:
        app_context: The application context
        
    Returns:
        bool: Whether registration was successful
    """
    try:
        # Register settings with the application context
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
                error_type="SETTINGS_REGISTRATION_FAILED",
                details=f"Failed to register {MODULE_ID} module settings"
            ))
            
        return success
    except Exception as e:
        logger.error(error_message(
            module_id=MODULE_ID,
            error_type="SETTINGS_REGISTRATION_ERROR",
            details=f"Exception registering {MODULE_ID} module settings: {str(e)}"
        ))
        return False

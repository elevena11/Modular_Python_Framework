"""
Quick fix for modules/core/database/module_settings.py
"""

import logging
from typing import Dict, Any
from core.error_utils import error_message

logger = logging.getLogger("core.database.settings")

# Default settings configuration - FOR UI/DOCUMENTATION ONLY
# These don't affect actual database initialization
DEFAULT_SETTINGS = {
    # Connection settings - READ ONLY (set during install)
    "database_url": "",  # Will be filled from config
    
    # Performance settings - Don't change unless you know what you're doing
    "max_retries": 5,
    "retry_delay_base": 0.1,
    "retry_delay_max": 2.0,
    "pool_size": 20,
    "pool_overflow": 10,
    "pool_timeout": 30,
    "pool_recycle": 3600,
    
    # SQLite settings - Advanced users only
    "sqlite_journal_mode": "WAL",
    "sqlite_synchronous": "NORMAL",
    "sqlite_cache_size": 10000,
    "sqlite_foreign_keys": True,
    "sqlite_busy_timeout": 10000
}

# Validation schema
VALIDATION_SCHEMA = {
    # Connection URL is read-only
    "database_url": {
        "type": "string",
        "description": "Database connection URL (set during installation)"
    },
    "connection_timeout": {
        "type": "int",
        "min": 1,
        "max": 3600,
        "description": "Connection timeout in seconds"
    },
    "max_retries": {
        "type": "int",
        "min": 0,
        "max": 100,
        "description": "Maximum number of retry attempts"
    },
    "retry_delay_base": {
        "type": "float",
        "min": 0.01,
        "max": 10.0,
        "description": "Base delay between retries in seconds"
    },
    "retry_delay_max": {
        "type": "float",
        "min": 0.1,
        "max": 60.0,
        "description": "Maximum delay between retries in seconds"
    },
    "pool_size": {
        "type": "int",
        "min": 1,
        "max": 1000,
        "description": "Connection pool size"
    },
    "pool_overflow": {
        "type": "int",
        "min": 0,
        "max": 1000,
        "description": "Maximum number of connections beyond pool_size"
    },
    "pool_timeout": {
        "type": "int",
        "min": 1,
        "max": 3600,
        "description": "Seconds to wait before timing out on getting a connection"
    },
    "pool_recycle": {
        "type": "int",
        "min": 1,
        "max": 86400,
        "description": "Seconds after which a connection is recycled"
    },
    "sqlite_journal_mode": {
        "type": "string",
        "enum": ["DELETE", "TRUNCATE", "PERSIST", "MEMORY", "WAL", "OFF"],
        "description": "SQLite journal mode"
    },
    "sqlite_synchronous": {
        "type": "string",
        "enum": ["OFF", "NORMAL", "FULL", "EXTRA"],
        "description": "SQLite synchronous setting"
    },
    "sqlite_cache_size": {
        "type": "int",
        "min": 100,
        "max": 1000000,
        "description": "SQLite cache size"
    },
    "sqlite_foreign_keys": {
        "type": "bool",
        "description": "SQLite foreign keys enforcement"
    },
    "sqlite_busy_timeout": {
        "type": "int",
        "min": 100,
        "max": 100000,
        "description": "SQLite busy timeout in ms"
    }
}

# UI metadata
UI_METADATA = {
    # Make database_url display as read-only
    "database_url": {
        "display_name": "Database URL",
        "description": "Database connection URL (set during installation)",
        "input_type": "text",
        "category": "Connection",
        "order": 10,
        "readonly": True
    },
    "connection_timeout": {
        "display_name": "Connection Timeout",
        "description": "Maximum time to wait for a connection (seconds)",
        "input_type": "number",
        "category": "Connection",
        "order": 20
    },
    "max_retries": {
        "display_name": "Maximum Retries",
        "description": "Maximum number of retry attempts for database operations",
        "input_type": "number",
        "category": "Retry Settings",
        "order": 10
    },
    "retry_delay_base": {
        "display_name": "Base Retry Delay",
        "description": "Initial delay between retries (seconds)",
        "input_type": "number",
        "category": "Retry Settings",
        "order": 20
    },
    "retry_delay_max": {
        "display_name": "Maximum Retry Delay",
        "description": "Maximum delay between retries (seconds)",
        "input_type": "number",
        "category": "Retry Settings",
        "order": 30
    },
    "pool_size": {
        "display_name": "Connection Pool Size",
        "description": "Number of connections to keep open",
        "input_type": "number",
        "category": "Connection Pool",
        "order": 10
    },
    "pool_overflow": {
        "display_name": "Pool Overflow",
        "description": "Additional connections beyond pool size",
        "input_type": "number",
        "category": "Connection Pool",
        "order": 20
    },
    "pool_timeout": {
        "display_name": "Pool Timeout",
        "description": "Time to wait for an available connection (seconds)",
        "input_type": "number",
        "category": "Connection Pool",
        "order": 30
    },
    "pool_recycle": {
        "display_name": "Connection Recycle Time",
        "description": "Time before a connection is recycled (seconds)",
        "input_type": "number",
        "category": "Connection Pool",
        "order": 40
    },
    "sqlite_journal_mode": {
        "display_name": "Journal Mode",
        "description": "SQLite journal mode (WAL recommended for concurrency)",
        "input_type": "dropdown",
        "options": [
            {"value": "DELETE", "label": "DELETE"},
            {"value": "TRUNCATE", "label": "TRUNCATE"},
            {"value": "PERSIST", "label": "PERSIST"},
            {"value": "MEMORY", "label": "MEMORY"},
            {"value": "WAL", "label": "WAL (recommended)"},
            {"value": "OFF", "label": "OFF (not recommended)"}
        ],
        "category": "SQLite Settings",
        "order": 10
    },
    "sqlite_synchronous": {
        "display_name": "Synchronous Mode",
        "description": "SQLite synchronous setting (balance of safety and speed)",
        "input_type": "dropdown",
        "options": [
            {"value": "OFF", "label": "OFF (fastest, least safe)"},
            {"value": "NORMAL", "label": "NORMAL (recommended)"},
            {"value": "FULL", "label": "FULL (safer)"},
            {"value": "EXTRA", "label": "EXTRA (safest, slowest)"}
        ],
        "category": "SQLite Settings",
        "order": 20
    },
    "sqlite_cache_size": {
        "display_name": "Cache Size",
        "description": "SQLite cache size (pages)",
        "input_type": "number",
        "category": "SQLite Settings",
        "order": 30
    },
    "sqlite_foreign_keys": {
        "display_name": "Foreign Keys",
        "description": "Enable foreign key constraints",
        "input_type": "checkbox",
        "category": "SQLite Settings",
        "order": 40
    },
    "sqlite_busy_timeout": {
        "display_name": "Busy Timeout",
        "description": "Time to wait on locks (milliseconds)",
        "input_type": "number",
        "category": "SQLite Settings",
        "order": 50
    }
}

async def register_settings(app_context):
    """
    Register database module settings with the application context.
    
    Args:
        app_context: Application context
        
    Returns:
        True if registration successful, False otherwise
    """
    try:
        # Make a copy of default settings
        settings = DEFAULT_SETTINGS.copy()
        
        # Set database_url from configuration
        settings["database_url"] = app_context.config.DATABASE_URL
        
        # Check if settings service is available
        settings_service = app_context.get_service("core.settings.service")
        if not settings_service:
            logger.warning("Settings service not available - cannot register database settings")
            return False
            
        # Register with the application context
        success = await app_context.register_module_settings(
            module_id="core.database",
            default_settings=settings,
            validation_schema=VALIDATION_SCHEMA,
            ui_metadata=UI_METADATA
        )
        
        if success:
            logger.info("core.database: Database module settings registered successfully")
        else:
            logger.warning("core.database: Failed to register database settings")
            
        return success
        
    except Exception as e:
        import traceback
        logger.error(error_message(
            module_id="core.database.settings",
            error_type="SETTINGS_REGISTRATION_ERROR",
            details=f"Error registering database module settings: {str(e)}",
            location="register_settings()",
            context={"traceback": traceback.format_exc()}
        ))
        return False

def get_sqlite_pragmas(settings=None):
    """
    Generate SQLite PRAGMA statements.
    
    Args:
        settings: Optional settings dictionary
        
    Returns:
        List of PRAGMA SQL statements
    """
    # Use defaults if no settings provided
    if settings is None:
        return [
            "PRAGMA journal_mode=WAL",
            "PRAGMA synchronous=NORMAL",
            "PRAGMA cache_size=10000",
            "PRAGMA foreign_keys=ON",
            "PRAGMA busy_timeout=10000"
        ]
    
    # Otherwise use values from settings
    return [
        f"PRAGMA journal_mode={settings['sqlite_journal_mode']}",
        f"PRAGMA synchronous={settings['sqlite_synchronous']}",
        f"PRAGMA cache_size={settings['sqlite_cache_size']}",
        f"PRAGMA foreign_keys={'ON' if settings['sqlite_foreign_keys'] else 'OFF'}",
        f"PRAGMA busy_timeout={settings['sqlite_busy_timeout']}"
    ]

"""
core/database.py
Clean Database Import Facade

This module provides a clean import point for database utilities.
All the actual implementation is in modules/core/database/.

Usage:
    from core.database import DatabaseBase, SQLiteJSON, execute_with_retry
    
    # Create database models
    class MyModel(DatabaseBase("my_database")):
        __tablename__ = "my_table"
        id = Column(Integer, primary_key=True)
        data = Column(SQLiteJSON)
"""

import warnings
import inspect
import logging
from core.logging import get_framework_logger

logger = get_framework_logger(__name__)

def DatabaseBase(database_name: str):
    """
    Create database base class for the specified database.
    
    Args:
        database_name: Name of the database (e.g., "framework", "semantic_core")
        
    Returns:
        SQLAlchemy declarative base for the specified database
    """
    # Import and delegate to the actual implementation
    from modules.core.database.database_infrastructure import get_database_base
    
    logger.debug(f"Creating DatabaseBase for '{database_name}'")
    return get_database_base(database_name)

# Import utilities from the actual database module
def _import_database_utility(name: str):
    """Import database utility from the infrastructure module."""
    try:
        from modules.core.database.database_infrastructure import SQLiteJSON as _SQLiteJSON
        if name == "SQLiteJSON":
            return _SQLiteJSON
        # Add other utilities as needed
    except ImportError as e:
        logger.error(f"Failed to import {name} from database infrastructure: {e}")
        raise

# Initialize utilities
SQLiteJSON = _import_database_utility("SQLiteJSON")

# Simple retry function
def execute_with_retry(operation, max_attempts=3):
    """Simple database operation retry utility."""
    for attempt in range(max_attempts):
        try:
            return operation()
        except Exception as e:
            if attempt == max_attempts - 1:
                raise
            logger.warning(f"Database operation failed (attempt {attempt + 1}/{max_attempts}): {e}")

# Legacy compatibility - DEPRECATED
def get_database_base(database_name: str):
    """DEPRECATED: Use DatabaseBase() instead."""
    warnings.warn(
        f"get_database_base() is DEPRECATED. Use 'DatabaseBase(database_name)' instead.",
        DeprecationWarning,
        stacklevel=2
    )
    return DatabaseBase(database_name)

__all__ = [
    # Primary API
    'DatabaseBase',         # Modern database base class
    'SQLiteJSON',          # SQLite JSON column type  
    'execute_with_retry',  # Database retry utility
    
    # Deprecated (Phase 4 removal)
    'get_database_base',   # DEPRECATED - Use DatabaseBase()
]
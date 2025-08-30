"""
Database Infrastructure for the Modular Framework

CRITICAL: This file provides ONLY database infrastructure for initial setup.
It should NOT be imported directly by modules during normal operations.

Purpose: Database base creation and metadata management during framework initialization.
Usage: Only imported by core.database.db_models.py for re-export to modules.

Semantic Engineering Note: Previously named 'db_models_util' which incorrectly suggested
general utility usage. Renamed to 'database_infrastructure' to reflect actual purpose.
"""

import json
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.types import TypeDecorator

# ============================================================================
# INFRASTRUCTURE UTILITIES
# ============================================================================

# Create a custom SQLite-friendly JSON type
class SQLiteJSON(TypeDecorator):
    """Represents a JSON object as a text-based JSON string in SQLite."""
    impl = Text

    def process_bind_param(self, value, dialect):
        if value is not None:
            value = json.dumps(value)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            try:
                value = json.loads(value)
            except (ValueError, TypeError):
                # Return as-is if it's not valid JSON
                pass
        return value

# ============================================================================
# MULTI-DATABASE SUPPORT - Database-Specific Bases
# ============================================================================

# Global registry to avoid import duplication issues
import sys

# Ensure single global registry across all import contexts
if not hasattr(sys.modules[__name__], '_GLOBAL_DATABASE_BASES'):
    _GLOBAL_DATABASE_BASES = {}
    sys.modules[__name__]._GLOBAL_DATABASE_BASES = _GLOBAL_DATABASE_BASES
else:
    _GLOBAL_DATABASE_BASES = sys.modules[__name__]._GLOBAL_DATABASE_BASES

# Ensure global singleton for framework database base
if "framework" not in _GLOBAL_DATABASE_BASES:
    _GLOBAL_DATABASE_BASES["framework"] = declarative_base()

# Use the global registry
_database_bases = _GLOBAL_DATABASE_BASES


def get_database_base(database_name: str = "framework"):
    """
    Contact surface: Get or create database-specific declarative base.
    Uses app_context as single source of truth to avoid import context issues.
    
    Args:
        database_name: Name of the database (default: "framework")
        
    Returns:
        SQLAlchemy declarative base for the specified database
        
    Examples:
        Framework tables: get_database_base() or get_database_base("framework")
        Custom database: get_database_base("crypto_shared")
    """
    import logging
    logger = logging.getLogger("core.database.database_infrastructure")
    
    # Try to get app_context as single source of truth
    app_context = None
    try:
        import sys
        if 'app' in sys.modules:
            app_module = sys.modules['app']
            if hasattr(app_module, 'get_app_context'):
                app_context = app_module.get_app_context()
    except Exception as e:
        logger.debug(f"Could not get app_context: {e}")
    
    # If we have app_context, use it as the source of truth
    if app_context:
        if not hasattr(app_context, '_database_bases'):
            app_context._database_bases = {"framework": _GLOBAL_DATABASE_BASES["framework"]}
        
        if database_name not in app_context._database_bases:
            app_context._database_bases[database_name] = declarative_base()
            logger.debug(f"Created new database base for '{database_name}' via app_context. Total databases: {list(app_context._database_bases.keys())}")
            
            # Register database requirement
            if database_name != "framework":
                app_context.register_database_requirement(database_name)
                logger.debug(f"Registered database requirement '{database_name}' with app_context")
        else:
            tables_in_metadata = list(app_context._database_bases[database_name].metadata.tables.keys())
            logger.debug(f"Reusing existing database base for '{database_name}' via app_context. Tables in metadata: {tables_in_metadata}")
        
        return app_context._database_bases[database_name]
    
    # Fallback to local registry if app_context not available (during early initialization)
    else:
        if database_name not in _database_bases:
            _database_bases[database_name] = declarative_base()
            logger.debug(f"[FALLBACK] Created database base for '{database_name}'. Total databases: {list(_database_bases.keys())}")
        else:
            logger.debug(f"[FALLBACK] Reusing database base for '{database_name}'")
        
        return _database_bases[database_name]


def get_all_database_names():
    """
    Contact surface: Get all registered database names.
    
    Returns:
        List of database names that have been requested via get_database_base()
    """
    import logging
    logger = logging.getLogger("core.database.database_infrastructure")
    result = list(_database_bases.keys())
    logger.debug(f"get_all_database_names() called - returning: {result}")
    return result


def get_database_metadata(database_name: str = "framework"):
    """
    Contact surface: Get metadata for specific database.
    Uses app_context as single source of truth to avoid import context issues.
    
    Args:
        database_name: Name of the database (default: "framework")
        
    Returns:
        SQLAlchemy metadata object for the specified database
    """
    import logging
    logger = logging.getLogger("core.database.database_infrastructure")
    
    # Try to get app_context as single source of truth
    app_context = None
    try:
        import sys
        if 'app' in sys.modules:
            app_module = sys.modules['app']
            if hasattr(app_module, 'get_app_context'):
                app_context = app_module.get_app_context()
    except Exception as e:
        logger.debug(f"Could not get app_context: {e}")
    
    # If we have app_context, use it as the source of truth
    if app_context:
        if hasattr(app_context, '_database_bases') and database_name in app_context._database_bases:
            base = app_context._database_bases[database_name]
            tables_count = len(base.metadata.tables)
            logger.debug(f"get_database_metadata: Using app_context base for '{database_name}' with {tables_count} tables: {list(base.metadata.tables.keys())}")
            return base.metadata
    
    # Fallback
    base = get_database_base(database_name)
    tables_count = len(base.metadata.tables)
    logger.debug(f"get_database_metadata: Using fallback base for '{database_name}' with {tables_count} tables: {list(base.metadata.tables.keys())}")
    return base.metadata


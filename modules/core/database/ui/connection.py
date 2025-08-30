"""
ui/modules/core/database/connection.py
Synchronous SQLite connection manager for the UI application.
"""

import os
import logging
import sqlite3
import json
from sqlite3 import Connection, Cursor
from contextlib import contextmanager
from typing import Dict, List, Any, Optional, Tuple

from ui.utils.security import redact_connection_url

logger = logging.getLogger("ui.modules.core.database.connection")

# Global connection
_connection = None

class SQLiteJSONEncoder:
    """Helper class to handle JSON encoding for SQLite."""
    
    @staticmethod
    def adapt_json(data):
        """Convert Python object to JSON string for SQLite storage."""
        if data is None:
            return None
        return json.dumps(data)
    
    @staticmethod
    def convert_json(data):
        """Convert SQLite JSON string to Python object."""
        if data is None:
            return None
        try:
            return json.loads(data)
        except:
            return data

def initialize_db_connection(database_url):
    """
    Initialize the database connection for UI.
    
    Args:
        database_url: SQLite connection URL
        
    Returns:
        Connection object if successful, None otherwise
    """
    global _connection
    
    if _connection is not None:
        logger.info("Database connection already initialized")
        return _connection
    
    try:
        # Extract the path from the URL (sqlite:///path/to/db.db)
        if not database_url.startswith("sqlite:///"):
            logger.error(f"Invalid SQLite URL format: {database_url}")
            return None
            
        db_path = database_url[10:]  # Strip 'sqlite:///' prefix
        
        # Check if directory exists
        db_dir = os.path.dirname(db_path)
        if db_dir and not os.path.exists(db_dir):
            logger.info(f"Creating database directory: {db_dir}")
            os.makedirs(db_dir, exist_ok=True)
        
        # Log the database path (safe to log since it's a local file)
        logger.info(f"Connecting to SQLite database at: {db_path}")
        
        # Connect to the database with extended options
        _connection = sqlite3.connect(
            db_path,
            # Important settings for reliability
            timeout=30.0,      # Wait up to 30 seconds for locks to be released
            isolation_level=None,  # Use autocommit mode by default
            check_same_thread=False  # Allow access from multiple threads
        )
        
        # Enable foreign keys
        _connection.execute("PRAGMA foreign_keys=ON")
        
        # Use WAL mode for better concurrency
        _connection.execute("PRAGMA journal_mode=WAL")
        
        # Balance between safety and speed
        _connection.execute("PRAGMA synchronous=NORMAL")
        
        # Register JSON handling for SQLite
        sqlite3.register_adapter(dict, SQLiteJSONEncoder.adapt_json)
        sqlite3.register_adapter(list, SQLiteJSONEncoder.adapt_json)
        sqlite3.register_converter("JSON", SQLiteJSONEncoder.convert_json)
        
        # Configure connection to return dictionaries
        _connection.row_factory = sqlite3.Row
        
        return _connection
        
    except Exception as e:
        logger.error(f"Error initializing database connection: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return None

@contextmanager
def get_db_cursor(transaction=False):
    """
    Get a database cursor with optional transaction management.
    
    Args:
        transaction: Start a transaction if True
        
    Yields:
        Database cursor object
    """
    global _connection
    if _connection is None:
        raise RuntimeError("Database connection not initialized")
    
    if transaction:
        _connection.execute("BEGIN")
    
    cursor = _connection.cursor()
    try:
        yield cursor
        if transaction:
            _connection.execute("COMMIT")
    except Exception as e:
        if transaction:
            _connection.execute("ROLLBACK")
        logger.error(f"Database error: {str(e)}")
        raise
    finally:
        cursor.close()

def execute_query(query, params=None, commit=False):
    """
    Execute a database query and return results.
    
    Args:
        query: SQL query string
        params: Query parameters
        commit: Whether to commit changes
        
    Returns:
        Query results as list of dictionaries
    """
    with get_db_cursor(transaction=commit) as cursor:
        cursor.execute(query, params or {})
        if cursor.description:
            # Convert rows to dictionaries
            columns = [col[0] for col in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
        return None

def get_table_list():
    """
    Get a list of all tables in the database.
    
    Returns:
        List of table names
    """
    query = """
    SELECT name AS table_name 
    FROM sqlite_master 
    WHERE type='table' AND name NOT LIKE 'sqlite_%'
    ORDER BY name
    """
    return execute_query(query)

def get_table_data(table_name, page=1, page_size=50, where=None, params=None, order_by=None):
    """
    Get data from a table with pagination and optional filtering.
    
    Args:
        table_name: Name of the table
        page: Page number (1-based)
        page_size: Number of records per page
        where: WHERE clause (without the 'WHERE' keyword)
        params: Query parameters
        order_by: ORDER BY clause (without the 'ORDER BY' keywords)
        
    Returns:
        Tuple of (data, total_count)
    """
    # Calculate offset
    offset = (page - 1) * page_size
    
    # Prepare parameters
    query_params = params or {}
    
    # Construct base query
    base_query = f"FROM {table_name}"
    if where:
        base_query += f" WHERE {where}"
    
    # Get total count
    count_query = f"SELECT COUNT(*) as total {base_query}"
    count_result = execute_query(count_query, query_params)
    total_count = count_result[0]['total'] if count_result else 0
    
    # Get data with pagination
    data_query = f"SELECT * {base_query}"
    if order_by:
        data_query += f" ORDER BY {order_by}"
    data_query += f" LIMIT ? OFFSET ?"
    
    # Add limit and offset to parameters
    with get_db_cursor() as cursor:
        # Convert params to list for SQLite parameterization
        param_values = list(query_params.values())
        param_values.extend([page_size, offset])
        
        cursor.execute(data_query, param_values)
        
        # Get column names
        columns = [col[0] for col in cursor.description]
        
        # Fetch data and convert to list of dictionaries
        rows = cursor.fetchall()
        data = [dict(zip(columns, row)) for row in rows]
    
    return data, total_count

def get_table_columns(table_name):
    """
    Get information about table columns using PRAGMA.
    
    Args:
        table_name: Name of the table
        
    Returns:
        List of column information dictionaries
    """
    query = f"PRAGMA table_info({table_name})"
    columns = execute_query(query)
    
    # Rename columns to match PostgreSQL naming
    for col in columns:
        if 'pk' in col:
            col['is_primary_key'] = col['pk'] == 1
        if 'notnull' in col:
            col['is_nullable'] = col['notnull'] == 0
    
    return columns

def get_table_schema(table_name):
    """
    Get the schema for a table, including columns and primary keys.
    
    Args:
        table_name: Name of the table
        
    Returns:
        Dict containing table schema information
    """
    # Get column information
    columns = get_table_columns(table_name)
    
    # Extract primary key columns
    primary_keys = [col['name'] for col in columns if col.get('pk', 0) == 1]
    
    # Format columns to match the expected schema format
    formatted_columns = []
    for col in columns:
        formatted_columns.append({
            "name": col['name'],
            "type": col['type'],
            "nullable": col.get('notnull', 1) == 0,
            "primary_key": col.get('pk', 0) == 1
        })
    
    return {
        "columns": formatted_columns,
        "primary_keys": primary_keys
    }

def close_connection():
    """Close the database connection."""
    global _connection
    if _connection is not None:
        _connection.close()
        _connection = None
        logger.info("Database connection closed")

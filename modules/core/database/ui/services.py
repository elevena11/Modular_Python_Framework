"""
modules/core/database/ui/services.py
Service layer for database UI operations with direct SQLite access.
"""

import logging
import json
import sqlite3
import os
from typing import Dict, List, Any, Optional, Tuple

logger = logging.getLogger("modules.core.database.ui.services")

class DatabaseService:
    """Service for database operations in the UI with direct SQLite access."""
    
    @staticmethod
    def get_database_config() -> Dict[str, Any]:
        """Load database configuration from db_config.json."""
        try:
            config_path = os.path.join("data", "db_config.json")
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    return json.load(f)
            else:
                logger.warning("db_config.json not found, using default paths")
                return {"db_path": os.path.join("data", "database")}
        except Exception as e:
            logger.error(f"Error loading db_config.json: {str(e)}")
            return {"db_path": os.path.join("data", "database")}
    
    @staticmethod
    def get_database_path(database_name: str) -> str:
        """Get the full path to a database file."""
        config = DatabaseService.get_database_config()
        db_dir = config.get("db_path", os.path.join("data", "database"))
        return os.path.join(db_dir, f"{database_name}.db")
    
    @staticmethod
    def get_databases() -> List[str]:
        """Get a list of available database names."""
        try:
            config = DatabaseService.get_database_config()
            database_dir = config.get("db_path", os.path.join("data", "database"))
            if not os.path.exists(database_dir):
                return []
            
            databases = []
            for file in os.listdir(database_dir):
                if file.endswith('.db'):
                    db_name = file[:-3]  # Remove .db extension
                    databases.append(db_name)
            
            return sorted(databases)
            
        except Exception as e:
            logger.error(f"Error getting database list: {str(e)}")
            return []
    
    @staticmethod
    def get_tables(database_name: str) -> List[str]:
        """
        Get a list of all tables in a specific database.
        
        Args:
            database_name: Name of the database
            
        Returns:
            List of table names
        """
        try:
            db_path = DatabaseService.get_database_path(database_name)
            if not os.path.exists(db_path):
                logger.warning(f"Database file does not exist: {db_path}")
                return []
            
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
                tables = [row[0] for row in cursor.fetchall()]
                return sorted(tables)
                
        except Exception as e:
            logger.error(f"Error getting table list from database {database_name}: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return []
    
    @staticmethod
    def get_table_data(database_name: str, table_name: str, page=1, page_size=50, filter_column=None, filter_value=None, sort_column=None, sort_desc=False):
        """
        Get data from a table with pagination, filtering, and sorting.
        
        Args:
            database_name: Name of the database
            table_name: Name of the table
            page: Page number (1-based)
            page_size: Number of records per page
            filter_column: Column to filter on
            filter_value: Value to filter for
            sort_column: Column to sort by
            sort_desc: Sort descending if True
            
        Returns:
            Tuple of (data, total_count) where data is a list of dictionaries
        """
        try:
            db_path = DatabaseService.get_database_path(database_name)
            if not os.path.exists(db_path):
                logger.warning(f"Database file does not exist: {db_path}")
                return [], 0
            
            with sqlite3.connect(db_path) as conn:
                conn.row_factory = sqlite3.Row  # Enable dict-like access to rows
                cursor = conn.cursor()
                
                # Build the base query
                base_query = f"SELECT * FROM [{table_name}]"
                count_query = f"SELECT COUNT(*) FROM [{table_name}]"
                params = []
                
                # Add filtering
                where_clause = ""
                if filter_column and filter_value:
                    where_clause = f" WHERE [{filter_column}] LIKE ?"
                    params.append(f"%{filter_value}%")
                    base_query += where_clause
                    count_query += where_clause
                
                # Get total count
                cursor.execute(count_query, params)
                total_count = cursor.fetchone()[0]
                
                # Add sorting
                if sort_column:
                    order_direction = "DESC" if sort_desc else "ASC"
                    base_query += f" ORDER BY [{sort_column}] {order_direction}"
                
                # Add pagination
                offset = (page - 1) * page_size
                base_query += f" LIMIT {page_size} OFFSET {offset}"
                
                # Execute the query
                cursor.execute(base_query, params)
                rows = cursor.fetchall()
                
                # Convert to list of dictionaries
                data = [dict(row) for row in rows]
                
                return data, total_count
                
        except Exception as e:
            logger.error(f"Error getting table data from database {database_name}, table {table_name}: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return [], 0
    
    @staticmethod
    def get_table_schema(database_name: str, table_name: str):
        """
        Get schema information for a table.
        
        Args:
            database_name: Name of the database
            table_name: Name of the table
            
        Returns:
            Dict with table schema information
        """
        try:
            db_path = DatabaseService.get_database_path(database_name)
            if not os.path.exists(db_path):
                logger.warning(f"Database file does not exist: {db_path}")
                return {"columns": [], "primary_keys": []}
            
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                
                # Get column information
                cursor.execute(f"PRAGMA table_info([{table_name}])")
                columns_info = cursor.fetchall()
                
                columns = []
                primary_keys = []
                
                for column_info in columns_info:
                    # SQLite PRAGMA table_info returns: (cid, name, type, notnull, dflt_value, pk)
                    column = {
                        "name": column_info[1],
                        "type": column_info[2],
                        "nullable": not bool(column_info[3]),
                        "primary_key": bool(column_info[5])
                    }
                    columns.append(column)
                    
                    if column["primary_key"]:
                        primary_keys.append(column["name"])
                
                return {
                    "columns": columns,
                    "primary_keys": primary_keys
                }
                
        except Exception as e:
            logger.error(f"Error getting table schema from database {database_name}, table {table_name}: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return {"columns": [], "primary_keys": []}
    
    @staticmethod
    def execute_custom_query(query, params=None, is_write=False):
        """
        Execute a custom SQL query (read-only for security).

        Args:
            query: SQL query string
            params: Query parameters
            is_write: Whether the query modifies data

        Returns:
            Query results or execution status
        """
        try:
            # Block write queries for security
            if is_write:
                logger.warning("Write queries are disabled for security reasons")
                return {"success": False, "error": "Write operations (INSERT, UPDATE, DELETE) are disabled for security reasons in the UI"}

            # Block potentially dangerous commands
            query_upper = query.upper().strip()
            dangerous_commands = ['INSERT', 'UPDATE', 'DELETE', 'DROP', 'CREATE', 'ALTER', 'PRAGMA']
            for cmd in dangerous_commands:
                if query_upper.startswith(cmd):
                    return {"success": False, "error": f"{cmd} operations are not allowed for security reasons"}

            # Only allow SELECT queries from a specific database (use first available)
            databases = DatabaseService.get_databases()
            if not databases:
                return {"success": False, "error": "No databases available"}

            # Default to framework database for queries
            db_path = DatabaseService.get_database_path(databases[0])

            with sqlite3.connect(db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)

                rows = cursor.fetchall()

                # Convert to list of dictionaries
                data = [dict(row) for row in rows]

                return {
                    "success": True,
                    "rows": data,
                    "row_count": len(data),
                    "message": f"Query executed successfully. Returned {len(data)} rows."
                }

        except Exception as e:
            logger.error(f"Error executing custom query: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return {"success": False, "error": str(e)}

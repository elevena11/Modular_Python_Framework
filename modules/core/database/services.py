"""
modules/core/database/services.py
Updated: April 4, 2025
Implemented Hybrid Service Pattern with proper Result object usage and standardized error handling
"""

import logging
import contextlib
from typing import Dict, Any, List, Optional, Union, Tuple

# Import database operations
from .database import DatabaseOperations
from .module_settings import get_sqlite_pragmas

# Import from error handler module
from core.error_utils import Result, error_message

# Module ID for error codes
MODULE_ID = "core.database"

class DatabaseService:
    """
    Primary service for database operations with SQLite.
    Follows the Hybrid Service Pattern with explicit async initialization.
    """
    
    def __init__(self, app_context):
        """
        Initialize basic state - NO complex operations here.
        
        Args:
            app_context: The application context
        """
        self.app_context = app_context
        self.logger = logging.getLogger(MODULE_ID)
        self.initialized = False
        
        # Initialize dependency references (for lazy loading)
        self._db_operations = None
        
        # Initialize state
        self.config = {}
        
        self.logger.info(f"{MODULE_ID} service created (pre-Phase 2)")
    
    @property
    def db_operations(self):
        """Lazy load database operations."""
        if self._db_operations is None:
            self._db_operations = DatabaseOperations(self.app_context)
        return self._db_operations
    
    
    async def initialize(self, app_context=None, settings=None):
        """
        Phase 2 initialization - Load settings and set up complex database state.
        
        Args:
            app_context: Optional application context
            settings: Optional pre-loaded settings
            
        Returns:
            bool: True if initialization successful
        """
        # Skip if already initialized
        if self.initialized:
            return True
        
        self.logger.info(f"Initializing {MODULE_ID} service")
        
        try:
            # Load or use provided settings
            if settings:
                self.config = settings
            else:
                # Load settings from app_context (Removed call to get_module_settings to avoid init dependency)
                context = app_context or self.app_context
                # self.config = await context.get_module_settings(MODULE_ID) # Removed this line
                # If specific settings are needed here, they should be passed via the 'settings' arg
                # or retrieved after the settings service is fully initialized.
            
            # Create all tables
            success = await self.db_operations.create_tables()
            if not success:
                self.logger.error(error_message(
                    module_id=MODULE_ID,
                    error_type="TABLE_CREATION_FAILED",
                    details="Failed to create database tables"
                ))
                return False
            
            # Apply pragmas
            await self.db_operations._set_sqlite_pragmas()
                
            # Mark as initialized
            self.initialized = True
            self.logger.info(f"{MODULE_ID} service initialized")
            return True
            
        except Exception as e:
            self.logger.error(error_message(
                module_id=MODULE_ID,
                error_type="INIT_ERROR",
                details=f"Error during initialization: {str(e)}"
            ))
            import traceback
            self.logger.error(traceback.format_exc())
            return False
    
    async def initialize_all_databases_phase1(self, app_context=None):
        """
        Complete database initialization during Phase 1.
        Creates all engines and tables for all discovered databases.
        
        Args:
            app_context: Optional app context (for hook compatibility)
        
        Returns:
            bool: True if initialization successful
        """
        # Use pre-discovered databases if available, otherwise discover now
        if hasattr(self, '_discovered_databases'):
            self.logger.info("Using pre-discovered databases from Phase 1 synchronous discovery")
            success = await self.db_operations.initialize_all_databases_from_discovery(self._discovered_databases)
        else:
            self.logger.info("No pre-discovered databases found, performing discovery now")
            success = await self.db_operations.initialize_all_databases_phase1()
        
        if success:
            self.initialized = True
            self.logger.info("Database service fully initialized in Phase 1")
        return success
    
    
    async def _initialize_framework_features(self, app_context):
        """Initialize framework-specific features after all databases are ready."""
        # Set SQLite pragmas for framework database
        await self.db_operations._set_sqlite_pragmas()
        
        # Verify framework tables
        await self._verify_tables()
        
        # Mark as initialized
        self.initialized = True
        
        self.logger.info("Framework-specific database features initialized")
    
    async def _verify_tables(self):
        """Verify database tables were created properly."""
        tables = await self.db_operations.get_all_tables()
        
        # Core tables that should always exist
        expected_tables = [
            "modules", "module_settings", "module_logs", 
            "files", "processes", "system_status", "terminal_sessions"
        ]
        
        # Check if all expected tables exist
        missing_tables = [t for t in expected_tables if t not in tables]
        if missing_tables:
            self.logger.warning(f"Missing expected database tables: {', '.join(missing_tables)}")
        else:
            self.logger.info(f"All expected tables verified: {', '.join(expected_tables)}")
            
        # Report all tables found
        self.logger.info(f"All tables in database: {', '.join(tables)}")
    
    def is_initialized(self):
        """Check if database is fully initialized and ready for use."""
        return self.initialized
    
    def get_initialization_status(self):
        """Get detailed status about framework database initialization."""
        try:
            # Use existing method to get available databases
            available_databases = self.get_available_databases()
            
            # Get framework database URL for info
            framework_url = self.get_database_url("framework") if "framework" in available_databases else ""
            
            framework_status = {
                "url": framework_url,
                "available": "framework" in available_databases
            }
            
            return {
                "initialized": self.initialized,
                "framework_database": framework_status,
                "registered_databases_count": len(available_databases),
                "registered_databases": available_databases
            }
            
        except Exception as e:
            self.logger.error(f"Error getting initialization status: {str(e)}")
            return {
                "initialized": self.initialized,
                "framework_database": {},
                "registered_databases_count": 0,
                "registered_databases": []
            }
    
    def get_model_classes(self):
        """
        Get all model classes defined in the database module.
        
        Returns:
            Dictionary of model classes with model names as keys
        """
        from modules.core.database.db_models import (
            Module, DatabaseModuleSetting, ModuleLog, File,
            Process, SystemStatus, TerminalSession
        )
        
        return {
            "Module": Module,
            "DatabaseModuleSetting": DatabaseModuleSetting,
            "ModuleLog": ModuleLog,
            "File": File,
            "Process": Process,
            "SystemStatus": SystemStatus,
            "TerminalSession": TerminalSession
        }
    # Table operations with standardized Result pattern
    
    async def get_all_tables(self, database: str = "framework") -> List[str]:
        """
        Get all tables in the specified database.
        
        Args:
            database: Name of the database (default: "framework")
        
        Returns:
            List of table names or empty list on error
        """
        try:
            # Direct SQLite query to get table names
            import sqlite3
            from core.paths import get_database_path
            
            db_path = get_database_path(f"{database}.db")
            if not db_path.exists():
                self.logger.debug(f"Database file does not exist: {db_path}")
                return []
            
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
                tables = [row[0] for row in cursor.fetchall()]
                return tables
                
        except Exception as e:
            self.logger.error(f"Error getting tables for database {database}: {str(e)}")
            return []
    
    async def get_table_schema(self, table_name: str, database: str = "framework") -> Result:
        """
        Get schema information for a specific table in the specified database.
        
        Args:
            table_name: Name of the table
            database: Name of the database (default: "framework")
            
        Returns:
            Result object with schema information or error details
        """
        
        try:
            # Validate database is initialized
            if not self.initialized:
                self.logger.error(error_message(
                    module_id=MODULE_ID,
                    error_type="NOT_INITIALIZED",
                    details="Database not ready for table schema retrieval"
                ))
                return Result.error(
                    code="NOT_INITIALIZED",
                    message="Database initialization not complete",
                    details={"operation": "get_table_schema"}
                    )
            
            # Check if table exists in specified database
            tables = await self.db_operations.get_all_tables(database)
            if table_name not in tables:
                self.logger.error(error_message(
                    module_id=MODULE_ID,
                    error_type="TABLE_NOT_FOUND",
                    details=f"Table {table_name} not found"
                ))
                return Result.error(
                    code="TABLE_NOT_FOUND",
                    message=f"Table '{table_name}' not found",
                    details={"table": table_name}
                )
            
            # Get schema from operations for specified database
            schema_info = await self.db_operations.get_table_schema(table_name, database)
            if not schema_info:
                return Result.error(
                    code="TABLE_SCHEMA_FAILED",
                    message=f"Failed to retrieve schema for table '{table_name}' in database '{database}'",
                    details={"table": table_name, "database": database}
                )
                
            return Result.success(data=schema_info)
                
        except Exception as e:
            self.logger.error(error_message(
                module_id=MODULE_ID,
                error_type="TABLE_SCHEMA_FAILED",
                details=f"Error retrieving table schema: {str(e)}"
            ))
            import traceback
            self.logger.error(traceback.format_exc())
            
            return Result.error(
                code="TABLE_SCHEMA_FAILED",
                message=f"Error retrieving schema for table '{table_name}': {str(e)}",
                details={"table": table_name, "error_details": str(e)}
            )
    
    async def get_table_data(self, table_name: str, page: int, page_size: int, 
                           database: str = "framework", sort_by: Optional[str] = None, sort_desc: bool = False,
                           filter_column: Optional[str] = None, filter_value: Optional[str] = None) -> Result:
        """
        Get data from a specific table with pagination, sorting, and filtering.
        
        Args:
            table_name: Name of the table
            page: Page number (1-based)
            page_size: Number of records per page
            database: Name of the database (default: "framework")
            sort_by: Column to sort by
            sort_desc: Sort in descending order
            filter_column: Column to filter by
            filter_value: Value to filter for
        
        Returns:
            Result object with data and total count, or error information
        """
        
        try:
            # Validate database is initialized
            if not self.initialized:
                self.logger.error(error_message(
                    module_id=MODULE_ID,
                    error_type="NOT_INITIALIZED",
                    details="Database not ready for table data retrieval"
                ))
                return Result.error(
                    code="NOT_INITIALIZED",
                    message="Database initialization not complete",
                    details={"operation": "get_table_data"})
            
            # Get data from operations for specified database
            data, total = await self.db_operations.get_table_data(
                table_name, page, page_size, sort_by, sort_desc, filter_column, filter_value, database_name=database)
            
            # Check if data was retrieved
            if data is None:
                return Result.error(
                    code="TABLE_DATA_FAILED",
                    message=f"Failed to retrieve data from table '{table_name}'",
                    details={"table": table_name})
                
            # Prepare result data
            result_data = {
                "data": data,
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": (total + page_size - 1) // page_size}
                
            return Result.success(data=result_data)
                
        except Exception as e:
            self.logger.error(error_message(
                module_id=MODULE_ID,
                error_type="TABLE_DATA_FAILED",
                details=f"Error retrieving table data: {str(e)}"
            ))
            import traceback
            self.logger.error(traceback.format_exc())
            
            
            return Result.error(
                code="TABLE_DATA_FAILED",
                message=f"Error retrieving data from table '{table_name}': {str(e)}",
                details={"table": table_name, "error_details": str(e)})
    
    async def execute_with_retry(self, coro):
        """
        Execute a coroutine with retry logic for SQLite concurrent access issues.
        
        Args:
            coro: The coroutine to execute
            
        Returns:
            The result of the coroutine execution
        """
        return await self.db_operations.execute_with_retry(coro)
    
    async def execute_raw_query(self, query_text: str, database: str = "framework", 
                              params: Optional[Dict[str, Any]] = None):
        """
        Execute a raw SQL query on the specified database.
        
        Args:
            query_text: SQL query text
            database: Name of the database (default: "framework")
            params: Optional query parameters
            
        Returns:
            Query result (list of records for SELECT, rowcount for others)
            
        Raises:
            Exception: If query execution fails
        """
        try:
            # Validate database is initialized
            if not self.initialized:
                self.logger.error(error_message(
                    module_id=MODULE_ID,
                    error_type="NOT_INITIALIZED",
                    details="Database not ready for query execution"
                ))
                raise RuntimeError("Database initialization not complete")
            
            # Execute query through operations
            result = await self.db_operations.execute_raw_query(query_text, params, database_name=database)
            return result
            
        except Exception as e:
            self.logger.error(error_message(
                module_id=MODULE_ID,
                error_type="QUERY_EXECUTION_FAILED",
                details=f"Error executing query on database '{database}': {str(e)}"
            ))
            raise
    
    # ============================================================================
    # CONTACT SURFACE - Utilities for Other Modules
    # ============================================================================
    
    def get_database_utilities(self):
        """
        Contact surface: Provide database utilities for other modules to use.
        
        Returns:
            Dict of utility functions that modules can use to manage their own databases
        """
        return self.db_operations.get_database_utilities()
    
    def create_database_engine(self, database_name: str, db_url: str = None):
        """
        Contact surface: Allow modules to create their own database engines.
        
        Args:
            database_name: Name of the database
            db_url: Optional database URL (will be generated if not provided)
            
        Returns:
            Database engine info dict or None on error
        """
        if not db_url:
            db_url = self.db_operations.get_database_url(database_name)
        
        return self.db_operations.create_database_engines(database_name, db_url)
    
    @contextlib.asynccontextmanager
    async def integrity_session(self, database_name: str, purpose: str = "general_operation"):
        """
        Phase 4: Data integrity-enforcing database session context manager.
        
        This replaces get_database_session() with a cleaner interface that:
        - Provides direct context manager access
        - Logs operation purpose for debugging
        - Enforces proper session lifecycle
        - Eliminates session factory pattern complexity
        
        Usage:
            async with app_context.database.integrity_session("database_name", "user_preferences") as session:
                # Database operations with automatic session management
                result = await session.execute(query)
                await session.commit()
        
        Args:
            database_name: Name of the database ("framework", "settings", etc.)
            purpose: Description of the operation for logging/debugging
            
        Yields:
            AsyncSession: Database session with automatic lifecycle management
            
        Raises:
            ValueError: If database not found or not initialized
            RuntimeError: If session creation fails
        """
        # Get the session factory using the established internal pattern
        session_factory = self._get_session_factory_internal(database_name)
        
        self.logger.debug(f"Opening integrity session for {database_name} (purpose: {purpose})")
        
        async with session_factory() as session:
            try:
                yield session
            except Exception as e:
                self.logger.error(f"Error in integrity session for {database_name} ({purpose}): {e}")
                raise
            finally:
                self.logger.debug(f"Closing integrity session for {database_name} (purpose: {purpose})")
    
    def _get_session_factory_internal(self, database_name: str):
        """
        Internal method to get session factory without deprecation warnings.
        
        This is used by integrity_session to access the same logic as get_database_session
        but without triggering deprecation warnings.
        """
        if database_name in self.db_operations.registered_databases:
            db_info = self.db_operations.registered_databases[database_name]["engine_info"]
            if not db_info or "session" not in db_info:
                raise ValueError(f"Database '{database_name}' engine not properly initialized")
            return db_info["session"]
        else:
            available = list(self.db_operations.registered_databases.keys())
            raise ValueError(f"Database '{database_name}' not found. Available databases: {available}")
    
    def get_database_session(self, database_name: str):
        """
        Contact surface: Get session factory for specific database.
        
        **DEPRECATED IN PHASE 4**: This method is deprecated in favor of the 
        integrity_session pattern. Use app_context.database.integrity_session() instead.
        
        This method still works but will issue warnings. It will be removed in a future version.
        
        Migration path:
            OLD: session_factory = db_service.get_database_session("db_name")
                 async with session_factory() as session:
                     # operations
                     
            NEW: async with app_context.database.integrity_session("db_name", "purpose") as session:
                     # operations with integrity validation and purpose logging
        
        Args:
            database_name: Name of the database
            
        Returns:
            Session factory function for the specified database
            
        Raises:
            ValueError: If database not found or not initialized
        """
        # Log deprecation warning for tracking migration progress
        caller_info = self._get_caller_info()
        self.logger.warning(
            f"DEPRECATED: get_database_session('{database_name}') called from {caller_info}. "
            f"Migrate to app_context.database.integrity_session('{database_name}', 'purpose') "
            f"for better logging and session management."
        )
        
        # Continue to work but with deprecation notice
        return self._get_session_factory_internal(database_name)
    
    def _get_caller_info(self) -> str:
        """Get caller information for deprecation logging."""
        try:
            import inspect
            for frame in inspect.stack()[2:]:  # Skip this method and get_database_session
                filename = frame.filename
                if not any(skip in filename for skip in ['/core/', '/database/']):
                    return f"{filename}:{frame.lineno} in {frame.function}()"
            return "unknown_location"
        except Exception:
            return "unknown_location"
    
    def get_available_databases(self):
        """
        Contact surface: Get list of all available databases.
        
        Returns:
            List of database names that modules can access
        """
        try:
            # In Phase 4 architecture, check what databases actually exist on filesystem
            import os
            from core.paths import get_database_path
            
            database_dir = get_database_path()
            if not os.path.exists(database_dir):
                return []
            
            databases = []
            for file in os.listdir(database_dir):
                if file.endswith('.db'):
                    db_name = file[:-3]  # Remove .db extension
                    databases.append(db_name)
            
            return databases
        except Exception as e:
            self.logger.error(f"Error getting available databases: {str(e)}")
            return []
    
    def get_database_url(self, database_name: str) -> str:
        """
        Contact surface: Generate database URL for any database name.
        
        Args:
            database_name: Name of the database
            
        Returns:
            SQLite URL for the database file
        """
        try:
            from core.paths import get_database_path
            db_path = get_database_path(f"{database_name}.db")
            return f"sqlite:///{db_path}"
        except Exception as e:
            self.logger.error(f"Error generating database URL for {database_name}: {str(e)}")
            return f"sqlite:///data/database/{database_name}.db"
    
    async def cleanup_resources(self):
        """
        Graceful resource cleanup - logging handled by decorator.
        Called during normal application shutdown via @graceful_shutdown decorator.
        """
        self.logger.info("***** DATABASE SERVICE CLEANUP_RESOURCES CALLED *****")
        
        # Perform graceful cleanup of all database engines and connections
        # This ensures proper cleanup of WAL/SHM files for all databases
        if self.db_operations:
            self.logger.info("Calling db_operations.cleanup_all_databases()...")
            await self.db_operations.cleanup_all_databases()
        else:
            self.logger.warning("No db_operations available for cleanup")
        
        # Mark service as shutting down
        self.initialized = False
        self.logger.info("***** DATABASE SERVICE CLEANUP_RESOURCES COMPLETE *****")
    
    def force_cleanup(self):
        """
        Force cleanup of resources - logging handled by decorator.
        Called during emergency shutdown via @force_shutdown decorator.
        """
        # Force cleanup of all database engines (synchronously)
        # This ensures cleanup even during emergency shutdown
        if self.db_operations:
            self.db_operations.force_cleanup_all_databases()
        
        # Mark service as shut down
        self.initialized = False
        
    # Legacy methods maintained for backward compatibility during migration
    async def shutdown(self):
        """LEGACY: Use cleanup_resources() instead - will be removed in future version"""
        await self.cleanup_resources()
    
    def force_shutdown(self):
        """LEGACY: Use force_cleanup() instead - will be removed in future version"""
        self.force_cleanup()

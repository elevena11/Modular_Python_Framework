"""
modules/core/database/database.py
Updated: April 4, 2025
Database operations for SQLite with standardized error handling and retry logic
"""

import os
import logging
import asyncio
import random
import json
import sqlite3
from datetime import datetime
import decimal
import uuid
from typing import Optional, List, Dict, Any, Tuple, Union
from sqlalchemy import create_engine, inspect, text, func
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import OperationalError, SQLAlchemyError

from modules.core.database.database_infrastructure import get_database_base, get_database_metadata, get_all_database_names
from .utils import execute_with_retry, ensure_db_directory_exists, redact_connection_url

# Import from core error utilities
from core.error_utils import error_message

# Module ID for error codes
MODULE_ID = "core.database"

class DatabaseOperations:
    """Handles direct database operations for SQLite."""
    
    def __init__(self, app_context):
        """Initialize database operations with multi-database support."""
        self.app_context = app_context
        self.logger = logging.getLogger(MODULE_ID)
        self.initialized = False
        
        # All databases managed uniformly - framework.db is just another database
        self.registered_databases = {}  # All databases (including framework) with their engine info
        
        # Get base database URL template from context
        self.db_url_template = app_context.config.DATABASE_URL
        
        # SQLite-specific settings - these will be loaded from settings in phase 2
        self.max_retries = 5
        self.retry_delay_base = 0.1
        self.retry_delay_max = 2.0
        self.connection_timeout = 30
        self.pool_size = 20
        self.pool_overflow = 10
        self.pool_timeout = 30
        self.pool_recycle = 3600
        
        # Standard SQLite pragmas for all databases
        self.sqlite_pragmas = [
            "PRAGMA journal_mode=WAL",      # Use Write-Ahead Logging for better concurrency
            "PRAGMA synchronous=NORMAL",    # Good balance between safety and speed
            "PRAGMA cache_size=10000",      # Larger cache (about 10MB)
            "PRAGMA foreign_keys=ON",       # Enforce foreign key constraints
            "PRAGMA busy_timeout=10000"     # Wait up to 10s on locks
        ]
    
    # discover_databases_from_models() - REMOVED - duplicate of bootstrap functionality
    # Bootstrap now handles all database discovery and creation independently
    
    # create_all_databases_now() - REMOVED - duplicate of bootstrap functionality
    # Bootstrap now handles all database creation independently
    
    async def _create_all_databases_async(self, discovered_databases):
        """
        Async implementation of database creation.
        
        Args:
            discovered_databases: Dict of {database_name: [table_names]}
            
        Returns:
            bool: True if successful
        """
        try:
            # 1. Compile schemas for all databases
            self.logger.info("Compiling schemas for all databases...")
            for database_name in discovered_databases.keys():
                success = await self._compile_schema_for_database(database_name, discovered_databases)
                if not success:
                    self.logger.error(f"Failed to compile schema for {database_name}")
                    return False
            
            # 2. Create database engines and tables
            self.logger.info("Creating database engines and tables...")
            for database_name, table_names in discovered_databases.items():
                # Create engine
                db_url = self.get_database_url(database_name)
                db_info = self.create_database_engines(database_name, db_url)
                if not db_info:
                    self.logger.error(f"Failed to create engine for {database_name}")
                    return False
                
                # Store engine info uniformly for all databases
                self.registered_databases[database_name] = {
                    "engine_info": db_info,
                    "table_names": table_names
                }
                
                # Set up app_context references for framework database (backward compatibility)
                if database_name == "framework":
                    self.app_context.db_engine = db_info["engine"]
                    self.app_context.db_session = db_info["session"]
                    self.app_context.db_sync_engine = db_info["sync_engine"]
                
                
                # Create tables
                success = await self.create_tables_for_database(database_name)
                if not success:
                    self.logger.error(f"Failed to create tables for {database_name}")
                    return False
                
                self.logger.info(f"Database '{database_name}' created with {len(table_names)} tables")
            
            # 3. Set SQLite pragmas
            await self._set_sqlite_pragmas()
            
            self.logger.info(f"All {len(discovered_databases)} databases created successfully!")
            return True
            
        except Exception as e:
            self.logger.error(f"Error creating databases: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return False
    
    async def _compile_all_schemas_once(self):
        """
        Compile schemas for all discovered databases ONCE at startup.
        
        This prevents repeated schema compilation during database creation.
        """
        try:
            # Get all discovered databases
            discovered_databases = self._discover_databases_from_files()
            
            # Compile schema for each database once
            for database_name in discovered_databases.keys():
                self.logger.info(f"Pre-compiling schema for database '{database_name}'")
                success = await self._compile_schema_for_database(database_name)
                if not success:
                    self.logger.error(f"Failed to pre-compile schema for database '{database_name}'")
                    return False
            
            self.logger.info(f"Successfully pre-compiled schemas for {len(discovered_databases)} databases")
            return True
            
        except Exception as e:
            self.logger.error(f"Error in schema pre-compilation: {e}")
            return False
    
    async def _compile_schema_for_database(self, database_name: str, discovered_databases: dict = None):
        """
        Compile unified schema for a database by using already-discovered modules.
        
        This uses the results from the initial discovery phase to prevent
        disabled modules from being imported during schema compilation.
        
        Args:
            database_name: Name of the database to compile schema for
            discovered_databases: Dict of {database_name: [module_paths]} from discovery phase
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            import os
            import re
            import ast
            
            compiled_modules = []
            imported_modules = set()  # Track already imported modules to prevent duplicates
            
            # AI GUIDANCE: Use discovered_databases from initial discovery phase instead of re-scanning
            # This prevents disabled modules from being imported during schema compilation
            if discovered_databases is None:
                self.logger.error("No discovered databases provided to schema compilation")
                return False
            
            # Get modules that target this database from the discovery results
            if database_name not in discovered_databases:
                self.logger.info(f"No modules found for database '{database_name}' in discovery results")
                return True
            
            # Get module paths from discovery results instead of scanning filesystem again
            module_info_list = discovered_databases.get(database_name, [])
            
            # Process each module found in the discovery phase
            for module_info in module_info_list:
                # module_info contains the import path from discovery
                import_path = module_info
                
                # Skip core.database.db_models to avoid circular imports  
                if import_path == "modules.core.database.db_models":
                    self.logger.info(f"Skipping schema compilation of {import_path} (core database tables already registered)")
                    compiled_modules.append(f"{import_path} (skipped - circular)")
                    continue
                
                # Skip if already imported to prevent SQLAlchemy conflicts
                if import_path in imported_modules:
                    self.logger.info(f"Skipping schema compilation of {import_path} (already imported)")
                    compiled_modules.append(f"{import_path} (skipped - duplicate)")
                    continue
                
                self.logger.info(f"Schema compilation: Importing {import_path} for database {database_name}")
                
                try:
                    # Read the db_models.py file to extract table classes
                    # Convert import path to file path
                    module_parts = import_path.split('.')
                    if len(module_parts) >= 3:  # modules.type.name.db_models
                        from core.paths import find_framework_root
                        framework_root = find_framework_root()
                        db_models_path = os.path.join(framework_root, *module_parts[:-1], "db_models.py")
                        
                        if os.path.exists(db_models_path):
                            # Read file to extract table class definitions
                            with open(db_models_path, 'r') as f:
                                content = f.read()
                            
                            # Extract table class definitions from the file
                            table_classes = self._extract_table_classes_from_content(content)
                            
                            if table_classes:
                                # Import the module to register tables with SQLAlchemy
                                try:
                                    import importlib
                                    module = importlib.import_module(import_path)
                                    imported_modules.add(import_path)  # Track this import
                                    
                                    # Verify the tables are registered by accessing them
                                    registered_tables = []
                                    for class_name in table_classes:
                                        if hasattr(module, class_name):
                                            table_obj = getattr(module, class_name)
                                            if hasattr(table_obj, '__tablename__') and hasattr(table_obj, '__table__'):
                                                registered_tables.append(table_obj.__tablename__)
                                                # Access __table__ to ensure registration
                                                _ = table_obj.__table__
                                    
                                    self.logger.info(f"Schema compiled from {import_path}: {len(registered_tables)} tables ({registered_tables})")
                                    compiled_modules.append(import_path)
                                    
                                except Exception as import_error:
                                    self.logger.warning(f"Failed to import {import_path} after schema compilation: {import_error}")
                            else:
                                self.logger.info(f"No table classes found in {import_path}")
                        else:
                            self.logger.warning(f"db_models.py not found for {import_path}: {db_models_path}")
                    else:
                        self.logger.warning(f"Invalid import path format: {import_path}")
                        
                except Exception as e:
                    self.logger.warning(f"Error compiling schema from {import_path}: {e}")
            
            if compiled_modules:
                self.logger.info(f"Successfully compiled schema from {len(compiled_modules)} modules for database '{database_name}': {compiled_modules}")
            else:
                self.logger.warning(f"No modules found targeting database '{database_name}'")
                
            return True
            
        except Exception as e:
            self.logger.error(f"Error compiling schema for database '{database_name}': {e}")
            return False
    
    def _extract_table_classes_from_content(self, content: str) -> List[str]:
        """
        Extract SQLAlchemy table class names from Python file content.
        
        Args:
            content: Python file content as string
            
        Returns:
            List of table class names
        """
        try:
            import ast
            import re
            
            table_classes = []
            base_variable_names = set()
            
            # Parse the Python file
            tree = ast.parse(content)
            
            # First pass: Find variables assigned from get_database_base() calls
            for node in ast.walk(tree):
                if isinstance(node, ast.Assign):
                    # Check if this is an assignment like: SomeBase = get_database_base("db_name")
                    if (isinstance(node.value, ast.Call) and 
                        isinstance(node.value.func, ast.Name) and 
                        node.value.func.id == "get_database_base"):
                        # Extract the variable name being assigned to
                        for target in node.targets:
                            if isinstance(target, ast.Name):
                                base_variable_names.add(target.id)
            
            # Second pass: Find table classes
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    # Check if this class likely defines a table
                    has_tablename = False
                    inherits_from_base = False
                    
                    # Check for __tablename__ attribute
                    for item in node.body:
                        if isinstance(item, ast.Assign):
                            for target in item.targets:
                                if isinstance(target, ast.Name) and target.id == "__tablename__":
                                    has_tablename = True
                                    break
                    
                    # Check if inherits from Base or similar
                    for base in node.bases:
                        if isinstance(base, ast.Name):
                            if base.id in ["Base", "FrameworkBase"]:
                                inherits_from_base = True
                            elif base.id in base_variable_names:
                                # Inherits from a variable that was assigned from get_database_base()
                                inherits_from_base = True
                        elif isinstance(base, ast.Call) and isinstance(base.func, ast.Name) and base.func.id == "get_database_base":
                            inherits_from_base = True
                    
                    # If it has __tablename__ and inherits from Base, it's likely a table class
                    if has_tablename and inherits_from_base:
                        table_classes.append(node.name)
            
            return table_classes
            
        except Exception as e:
            self.logger.warning(f"Error extracting table classes from content: {e}")
            # Fallback to regex-based extraction
            return self._extract_table_classes_regex(content)
    
    def _extract_table_classes_regex(self, content: str) -> List[str]:
        """
        Fallback regex-based extraction of table class names.
        
        Args:
            content: Python file content as string
            
        Returns:
            List of table class names
        """
        try:
            import re
            
            table_classes = []
            
            # Find class definitions that likely define tables
            class_pattern = r'class\s+(\w+)\s*\([^)]*(?:Base|FrameworkBase|get_database_base)[^)]*\):'
            class_matches = re.findall(class_pattern, content)
            
            for class_name in class_matches:
                # Check if this class has __tablename__
                tablename_pattern = rf'class\s+{class_name}.*?__tablename__\s*='
                if re.search(tablename_pattern, content, re.DOTALL):
                    table_classes.append(class_name)
            
            return table_classes
            
        except Exception as e:
            self.logger.warning(f"Error in regex-based table class extraction: {e}")
            return []

    async def _force_import_module_models(self, database_name: str):
        """
        Force import ALL modules' db_models.py that target the specified database.
        
        Args:
            database_name: Name of the database to import models for
        """
        try:
            import os
            import importlib
            
            imported_modules = []
            
            # Find ALL modules that target this database by scanning for DATABASE_NAME
            from core.paths import find_framework_root
            
            # Get the current project's root directory dynamically
            try:
                framework_root = find_framework_root()
                modules_dirs = [
                    os.path.join(framework_root, "modules", "core"),
                    os.path.join(framework_root, "modules", "standard"), 
                    os.path.join(framework_root, "modules", "extensions")
                ]
            except ValueError:
                # If framework root can't be determined, fail gracefully
                self.logger.error("Could not determine framework root directory - cannot discover modules")
                return False
            
            for modules_dir in modules_dirs:
                if not os.path.exists(modules_dir):
                    continue
                    
                for module_name in os.listdir(modules_dir):
                    module_path = os.path.join(modules_dir, module_name)
                    if not os.path.isdir(module_path):
                        continue
                    
                    # Skip disabled modules
                    disabled_file = os.path.join(module_path, ".disabled")
                    if os.path.exists(disabled_file):
                        continue
                        
                    db_models_path = os.path.join(module_path, "db_models.py")
                    if not os.path.exists(db_models_path):
                        continue
                    
                    try:
                        # Read file to check DATABASE_NAME
                        with open(db_models_path, 'r') as f:
                            content = f.read()
                        
                        import re
                        # Use separate patterns for double and single quotes
                        db_match = re.search(r'DATABASE_NAME\s*=\s*"([^"]+)"', content)
                        if not db_match:
                            db_match = re.search(r"DATABASE_NAME\s*=\s*'([^']+)'", content)
                        if db_match and db_match.group(1) == database_name:
                            # Found a module that targets this database - force import to register tables
                            module_path_part = os.path.basename(modules_dir)  # "core", "standard", "extensions"
                            import_path = f"modules.{module_path_part}.{module_name}.db_models"
                            
                            # Skip importing core.database.db_models to avoid circular imports  
                            if import_path == "modules.core.database.db_models":
                                self.logger.info(f"Skipping force import of {import_path} to avoid circular import (tables already registered)")
                                imported_modules.append(f"{import_path} (skipped - circular)")
                                continue
                            
                            self.logger.info(f"Force importing {import_path} to register tables")
                            
                            try:
                                # Import the module to trigger table registration
                                module = importlib.import_module(import_path)
                                self.logger.info(f"Successfully imported {import_path}")
                                
                                # Force access to all classes in the module to ensure table registration
                                if hasattr(module, '__dict__'):
                                    table_classes = []
                                    for name, obj in module.__dict__.items():
                                        if (hasattr(obj, '__tablename__') and 
                                            hasattr(obj, '__table__') and
                                            hasattr(obj, 'metadata')):
                                            table_classes.append(name)
                                            # Access the __table__ attribute to ensure registration
                                            _ = obj.__table__
                                    
                                    if table_classes:
                                        self.logger.info(f"Registered {len(table_classes)} table classes from {import_path}: {table_classes}")
                                    else:
                                        self.logger.info(f"No table classes found in {import_path}")
                                
                                imported_modules.append(import_path)
                                
                            except Exception as e:
                                # Try reloading if already imported
                                try:
                                    module = importlib.import_module(import_path)
                                    importlib.reload(module)
                                    self.logger.info(f"Successfully reloaded {import_path}")
                                    
                                    # Force access to all classes in the reloaded module
                                    if hasattr(module, '__dict__'):
                                        table_classes = []
                                        for name, obj in module.__dict__.items():
                                            if (hasattr(obj, '__tablename__') and 
                                                hasattr(obj, '__table__') and
                                                hasattr(obj, 'metadata')):
                                                table_classes.append(name)
                                                # Access the __table__ attribute to ensure registration
                                                _ = obj.__table__
                                        
                                        if table_classes:
                                            self.logger.info(f"Registered {len(table_classes)} table classes from reloaded {import_path}: {table_classes}")
                                    
                                    imported_modules.append(import_path)
                                except Exception as reload_error:
                                    self.logger.warning(f"Failed to import/reload {import_path}: {e}, {reload_error}")
                    
                    except Exception as e:
                        self.logger.warning(f"Error checking {db_models_path}: {e}")
            
            if imported_modules:
                self.logger.info(f"Successfully imported {len(imported_modules)} modules for database '{database_name}': {imported_modules}")
            else:
                self.logger.warning(f"No modules found targeting database '{database_name}'")
            
        except Exception as e:
            self.logger.error(f"Error force importing models for database '{database_name}': {e}")

    async def _set_sqlite_pragmas_all_databases(self):
        """
        Set SQLite pragmas for all initialized databases.
        """
        try:
            # Set pragmas for framework database
            if "framework" in self.registered_databases:
                self.logger.info("Phase 1: Setting SQLite pragmas for framework database")
                async with self.registered_databases["framework"]["engine_info"]["engine"].begin() as conn:
                    for pragma in self.sqlite_pragmas:
                        await conn.execute(text(pragma))
                self.logger.info("Phase 1: Framework database pragmas set")
            
            # Set pragmas for all registered databases
            for database_name, db_data in self.registered_databases.items():
                db_info = db_data["engine_info"]
                self.logger.info(f"Phase 1: Setting SQLite pragmas for database '{database_name}'")
                async with db_info["engine"].begin() as conn:
                    for pragma in self.sqlite_pragmas:
                        await conn.execute(text(pragma))
                self.logger.info(f"Phase 1: Pragmas set for database '{database_name}'")
            
            self.logger.info("Phase 1: SQLite pragmas set for all databases")
            
        except Exception as e:
            self.logger.error(f"Phase 1: Error setting SQLite pragmas: {e}")
            raise
    
    def _get_database_base_safe(self, db_name: str = "framework"):
        """
        Safely get database base without causing multiple imports.
        
        AI WARNING: Do not use __import__ in utilities - causes multiple imports
        This method uses cached import to prevent SQLAlchemy conflicts.
        """
        # Import only once at class level
        if not hasattr(self, '_db_models_module'):
            import modules.core.database.db_models as db_models
            self._db_models_module = db_models
        
        return self._db_models_module.get_database_base(db_name)
    
    def register_module_database(self, database_name: str, engine_info: dict, module_id: str = None):
        """
        Contact surface: Allow modules to register their databases for utility access.
        This is optional - modules can manage their databases completely independently.
        
        Args:
            database_name: Name of the database
            engine_info: Database engine information
            module_id: Optional module ID for tracking
        """
        self.registered_databases[database_name] = {
            "engine_info": engine_info,
            "module_id": module_id,
            "registered_at": self.app_context.get_timestamp() if hasattr(self.app_context, 'get_timestamp') else None
        }
        self.logger.info(f"Registered database '{database_name}' from module '{module_id or 'unknown'}'")
    
    def get_database_utilities(self):
        """
        Contact surface: Provide database utilities for other modules.
        
        Returns:
            Dict of utility functions that modules can use
        """
        return {
            "create_database_engine": self.create_database_engines,
            "get_database_url": self.get_database_url,
            "sqlite_pragmas": self.sqlite_pragmas,
            "execute_with_retry": self.execute_with_retry,
            "register_database": self.register_module_database,
            
            # New multi-database utilities
            "get_database_base": self._get_database_base_safe,
            "get_all_databases": lambda: list(self.registered_databases.keys()),
            "get_database_engine": lambda db_name: self.registered_databases.get(db_name, {}).get("engine_info"),
            # "discover_databases" - REMOVED - handled by bootstrap
        }
    
    async def cleanup_all_databases(self):
        """
        Cleanup all database engines and close connections.
        This ensures proper cleanup of WAL/SHM files for all databases.
        """
        self.logger.info("***** STARTING DATABASE CLEANUP *****")
        self.logger.info(f"Found {len(self.registered_databases)} databases to clean up")
        
        for database_name in self.registered_databases.keys():
            self.logger.info(f"Will clean up database: {database_name}")
        
        cleanup_count = 0
        for database_name, db_data in self.registered_databases.items():
            try:
                self.logger.info(f"Cleaning up database: {database_name}")
                db_info = db_data["engine_info"]
                
                # Dispose of async engine
                if "engine" in db_info and db_info["engine"]:
                    await db_info["engine"].dispose()
                    self.logger.info(f"DISPOSED async engine for database: {database_name}")
                
                # Dispose of sync engine
                if "sync_engine" in db_info and db_info["sync_engine"]:
                    db_info["sync_engine"].dispose()
                    self.logger.info(f"DISPOSED sync engine for database: {database_name}")
                
                cleanup_count += 1
                
            except Exception as e:
                self.logger.error(f"ERROR cleaning up database {database_name}: {e}")
                import traceback
                self.logger.error(traceback.format_exc())
        
        # Clear the registry after cleanup
        self.registered_databases.clear()
        
        self.logger.info(f"***** DATABASE CLEANUP COMPLETE. Cleaned up {cleanup_count} databases *****")
    
    def force_cleanup_all_databases(self):
        """
        Force cleanup of all database engines synchronously.
        Used during emergency shutdown when async cleanup is not possible.
        """
        self.logger.info("Starting force cleanup of all database engines...")
        
        cleanup_count = 0
        for database_name, db_data in self.registered_databases.items():
            try:
                db_info = db_data["engine_info"]
                
                # Force dispose of sync engine (async engines can't be disposed synchronously)
                if "sync_engine" in db_info and db_info["sync_engine"]:
                    db_info["sync_engine"].dispose()
                    self.logger.debug(f"Force disposed sync engine for database: {database_name}")
                
                cleanup_count += 1
                
            except Exception as e:
                self.logger.error(f"Error during force cleanup of database {database_name}: {e}")
        
        # Clear the registry after cleanup
        self.registered_databases.clear()
        
        self.logger.info(f"Force database cleanup complete. Cleaned up {cleanup_count} databases.")

    def get_database_url(self, database_name: str) -> str:
        """
        Generate database URL for a specific database.
        
        Args:
            database_name: Name of the database
            
        Returns:
            SQLite URL for the database file
        """
        # Extract directory from template URL
        if self.db_url_template.startswith("sqlite:///"):
            base_path = self.db_url_template[10:]  # Remove 'sqlite:///' prefix
            # Directory-only URL format: sqlite:///path/to/database/
            db_dir = base_path.rstrip('/')
            return f"sqlite:///{db_dir}/{database_name}.db"
        else:
            # Fallback for non-SQLite URLs (though we only support SQLite)
            return f"{self.db_url_template}_{database_name}"
    
    def _ensure_db_directory_exists(self, db_url: str):
        """Ensure the directory for the SQLite database exists."""
        if db_url.startswith("sqlite:///"):
            # Extract the file path part
            db_path = db_url[10:]
            # Get the directory
            db_dir = os.path.dirname(db_path)
            if db_dir and not os.path.exists(db_dir):
                try:
                    os.makedirs(db_dir, exist_ok=True)
                    # Use normalized relative path for logging
                    log_path = db_dir
                    # Remove any absolute path components for logging
                    if "\\" in log_path:
                        parts = log_path.split("\\")
                        # Get just the database-related part of the path
                        if len(parts) > 2:
                            log_path = "\\".join(parts[-2:])
                    self.logger.info(f"Created database directory: {log_path}")
                except Exception as e:
                    self.logger.error(error_message(
                        error_type="DIRECTORY_CREATE_FAILED",
                        details=f"Failed to create database directory: {str(e)}",
                        module_id=MODULE_ID
                    ))
                    return False
            return True
        return True
    
    
    def create_database_engines(self, database_name: str, db_url: str):
        """
        Create async and sync engines for a specific database.
        
        Args:
            database_name: Name of the database
            db_url: SQLite URL for the database
            
        Returns:
            Dict with engine, session, sync_engine, sync_session
        """
        try:
            # Ensure database directory exists
            if not self._ensure_db_directory_exists(db_url):
                return None
            
            # Create sync engine
            sync_engine = create_engine(
                db_url,
                connect_args={
                    "check_same_thread": False,
                    "timeout": self.connection_timeout
                },
                pool_pre_ping=True,
                pool_recycle=self.pool_recycle,
                echo=False
            )
            
            # Set pragmas for sync engine
            with sync_engine.connect() as conn:
                for pragma in self.sqlite_pragmas:
                    conn.execute(text(pragma))
            
            # Create sync session factory
            sync_session = sessionmaker(bind=sync_engine)
            
            # Create async engine
            async_url = db_url.replace('sqlite:///', 'sqlite+aiosqlite:///')
            async_engine = create_async_engine(
                async_url,
                echo=False,
                future=True,
                pool_size=self.pool_size,
                max_overflow=self.pool_overflow,
                pool_timeout=self.pool_timeout,
                pool_recycle=self.pool_recycle,
                pool_pre_ping=True,
                connect_args={
                    "check_same_thread": False
                }
            )
            
            # Create async session factory
            async_session = async_sessionmaker(
                bind=async_engine,
                expire_on_commit=False,
                class_=AsyncSession
            )
            
            return {
                "engine": async_engine,
                "session": async_session,
                "sync_engine": sync_engine,
                "sync_session": sync_session,
                "url": db_url
            }
            
        except Exception as e:
            self.logger.error(f"Error creating engines for database {database_name}: {str(e)}")
            return None
    
    async def initialize_all_databases_from_discovery(self, discovered_databases):
        """
        Initialize all databases using pre-discovered database information.
        
        Args:
            discovered_databases: Dict of {database_name: [table_names]}
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.logger.info("Phase 1: Complete database initialization starting...")
            self.logger.info(f"Phase 1: Using pre-discovered {len(discovered_databases)} databases")
            
            # Pre-compile schemas for all databases ONCE at startup
            self.logger.info("Phase 1: Pre-compiling schemas for all databases...")
            schema_success = await self._compile_all_schemas_once()
            if not schema_success:
                self.logger.error("Phase 1: Failed to pre-compile schemas")
                return False
            self.logger.info("Phase 1: Schema pre-compilation completed")
            
            # Create engines for all pre-discovered databases immediately
            for database_name, table_names in discovered_databases.items():
                self.logger.info(f"Phase 1: Creating engine for database '{database_name}'")
                
                db_url = self.get_database_url(database_name)
                db_info = self.create_database_engines(database_name, db_url)
                
                if not db_info:
                    self.logger.error(f"Phase 1: Failed to create engine for database: {database_name}")
                    return False
                
                # Store engine info uniformly for all databases
                self.registered_databases[database_name] = {
                    "engine_info": db_info,
                    "table_names": []  # Will be populated as tables are created
                }
                
                # Set up app_context references for framework database (backward compatibility)
                if database_name == "framework":
                    self.app_context.db_engine = db_info["engine"]
                    self.app_context.db_session = db_info["session"]
                    self.app_context.db_sync_engine = db_info["sync_engine"]
                    self.app_context.db_sync_session = db_info["sync_session"]
                
                self.logger.info(f"Phase 1: Engine created for database '{database_name}'")
            
            # Create all tables immediately
            for database_name in discovered_databases.keys():
                self.logger.info(f"Phase 1: Creating tables for database '{database_name}'")
                success = await self.create_tables_for_database(database_name)
                if success:
                    self.logger.info(f"Phase 1: Tables created for database '{database_name}'")
                else:
                    self.logger.warning(f"Phase 1: Table creation failed for database '{database_name}'")
            
            # Set SQLite pragmas for all databases
            await self._set_sqlite_pragmas_all_databases()
            
            database_count = len(discovered_databases)
            self.logger.info(f"Phase 1: All {database_count} pre-discovered databases fully initialized and ready!")
            return True
            
        except Exception as e:
            self.logger.error(error_message(
                error_type="PHASE1_INITIALIZATION_FAILED",
                details=f"Error in Phase 1 database initialization from discovery: {str(e)}",
                module_id=MODULE_ID
            ))
            import traceback
            self.logger.error(traceback.format_exc())
            return False

    async def initialize_all_databases_phase1(self):
        """
        Complete database initialization during Phase 1 module loading.
        
        Discovers all databases via file scanning and creates engines + tables immediately.
        No legacy code, no fallbacks - single initialization path.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.logger.info("Phase 1: Complete database initialization starting...")
            
            # 1. Discovery of databases that bootstrap created
            # Bootstrap has already created the database files, now we need to register them
            all_database_names = get_all_database_names()
            self.logger.info(f"Phase 1: Found {len(all_database_names)} databases from bootstrap: {all_database_names}")
            
            # Convert to the format expected by initialize_all_databases_from_discovery
            database_tables = {}
            for db_name in all_database_names:
                # Get table names from metadata
                try:
                    metadata = get_database_metadata(db_name)
                    table_names = list(metadata.tables.keys())
                    database_tables[db_name] = table_names
                    self.logger.info(f"Phase 1: Database '{db_name}' has tables: {table_names}")
                except Exception as e:
                    self.logger.warning(f"Phase 1: Could not get metadata for '{db_name}': {e}")
                    database_tables[db_name] = []
            
            database_count = len(database_tables)
            self.logger.info(f"Phase 1: Discovered {database_count} databases to initialize")
            
            # Use the new method with discovered databases
            return await self.initialize_all_databases_from_discovery(database_tables)
            
        except Exception as e:
            self.logger.error(error_message(
                error_type="PHASE1_INITIALIZATION_FAILED",
                details=f"Error in Phase 1 complete database initialization: {str(e)}",
                module_id=MODULE_ID
            ))
            import traceback
            self.logger.error(traceback.format_exc())
            return False
    
    async def create_tables_for_database(self, database_name: str):
        """
        Create all tables for a specific database.
        
        Args:
            database_name: Name of the database to create tables for
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Get the appropriate database engine
            db_info = None
            if database_name == "framework":
                if "framework" not in self.registered_databases:
                    self.logger.error(f"Framework database not prepared")
                    return False
                db_info = self.framework_database
            elif database_name in self.registered_databases:
                db_info = self.registered_databases[database_name]["engine_info"]
            else:
                self.logger.error(f"Database '{database_name}' not prepared")
                return False
            
            # Schema compilation already done at startup - skip here
            
            # Get metadata for this specific database
            from modules.core.database.database_infrastructure import get_database_metadata
            metadata = get_database_metadata(database_name)
            
            self.logger.info(f"Debug: Database '{database_name}' metadata has {len(metadata.tables)} tables: {list(metadata.tables.keys())}")
            
            if not metadata.tables:
                self.logger.info(f"No tables defined for database '{database_name}'")
                return True
            
            # Create all tables for this database
            async with db_info["engine"].begin() as conn:
                await conn.run_sync(lambda conn: metadata.create_all(conn, checkfirst=True))
            
            table_count = len(metadata.tables)
            table_names = list(metadata.tables.keys())
            self.logger.info(f"Created {table_count} tables for database '{database_name}': {', '.join(table_names)}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create tables for database '{database_name}': {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return False
    
    async def create_tables(self):
        """
        Legacy method: Create database tables for framework database only.
        Other modules are responsible for creating their own tables.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Only create tables for framework database
            if "framework" not in self.registered_databases:
                self.logger.error("Framework database engine not prepared")
                return False
                
            self.logger.info("Creating tables for framework database")
            
            # Models are registered during Phase 1 by each module
            self.logger.info("Using models registered during Phase 1 initialization")
            
            # Get the framework database metadata
            database_metadata = get_database_metadata()
            
            # Check for registered models for framework database
            if hasattr(self.app_context, 'registered_models') and self.app_context.registered_models:
                if "framework" in self.app_context.registered_models:
                    framework_models = self.app_context.registered_models["framework"]
                    self.logger.info(f"Found {len(framework_models)} registered models for framework database")
                    
                    # Log details about each registered model
                    for model in framework_models:
                        model_name = model.__name__
                        table_name = getattr(model, '__tablename__', 'unknown')
                        self.logger.info(f"Registered framework model: {model_name}, table: {table_name}")
                else:
                    self.logger.info("No models registered for framework database")
            else:
                self.logger.info("No registered_models found in app_context")
            
            # Debug: Log what models are actually discovered
            self.logger.info(f"Framework metadata contains {len(database_metadata.tables)} tables before create_all")
            
            # Log what tables will be created
            table_names = list(database_metadata.tables.keys())
            if table_names:
                self.logger.info(f"Framework tables to create: {', '.join(table_names)}")
            else:
                self.logger.info("No framework tables defined")
                return True
            
            # Create tables using the framework database engine
            async with self.registered_databases["framework"]["engine_info"]["engine"].begin() as conn:
                # Create tables from main metadata
                await execute_with_retry(
                    conn.run_sync(database_metadata.create_all)
                )
                
                # Create tables for registered models that aren't in main metadata
                if hasattr(self.app_context, 'registered_models') and self.app_context.registered_models:
                    if "framework" in self.app_context.registered_models:
                        framework_models = self.app_context.registered_models["framework"]
                        for model in framework_models:
                            if hasattr(model, '__table__'):
                                table_name = model.__tablename__
                                if table_name not in database_metadata.tables:
                                    self.logger.info(f"Creating table for registered model: {model.__name__}")
                                    await execute_with_retry(
                                        conn.run_sync(lambda conn, m=model: m.__table__.create(conn, checkfirst=True))
                                    )
            
            # Verify tables were created using Phase 4 pattern (reuses existing method)
            actual_tables = await self.get_all_tables("framework")
            self.logger.info(f"Framework tables created: {', '.join(actual_tables)}")
            
            self.logger.info("Framework database tables created successfully")
            return True
                    
        except Exception as e:
            self.logger.error(error_message(
                error_type="TABLE_CREATION_FAILED",
                details=f"Error creating framework database tables: {str(e)}",
                module_id=MODULE_ID
            ))
            import traceback
            self.logger.error(traceback.format_exc())
            return False
    
    async def execute_with_retry(self, coro, retries=None, retry_delay=None):
        """
        Execute a coroutine with retry logic for SQLite concurrent access issues.
        
        Args:
            coro: The coroutine to execute
            retries: Number of retries (uses self.max_retries if None)
            retry_delay: Base delay between retries (uses self.retry_delay_base if None)
            
        Returns:
            The result of the coroutine execution
            
        Raises:
            The last encountered exception if all retries fail
        """
        # Use class properties for defaults
        actual_retries = self.max_retries if retries is None else retries
        actual_delay = self.retry_delay_base if retry_delay is None else retry_delay
        
        # Call the utils function with the appropriate parameters
        return await execute_with_retry(
            coro, 
            max_retries=actual_retries, 
            base_delay=actual_delay,
            max_delay=self.retry_delay_max
        )
    
    async def _set_sqlite_pragmas(self):
        """Set SQLite pragmas for framework database."""
        if "framework" not in self.registered_databases:
            self.logger.warning("No framework database to set pragmas for")
            return
            
        self.logger.info("Setting SQLite pragmas for framework database")
        
        # Set pragmas for framework database
        async with self.registered_databases["framework"]["engine_info"]["engine"].begin() as conn:
            for pragma in self.sqlite_pragmas:
                await conn.execute(text(pragma))
        
        self.logger.info("SQLite pragmas set for framework database")
    
    async def get_all_tables(self, database_name: str = "framework") -> List[str]:
        """
        Get all tables in the specified database.
        Supports framework database and registered databases.
        
        Args:
            database_name: Name of the database (default: "framework")
        
        Returns:
            List of table names or empty list on error
        """
        try:
            # Get the appropriate database engine
            db_info = None
            if database_name == "framework":
                if "framework" not in self.registered_databases:
                    self.logger.error("Framework database not initialized")
                    return []
                db_info = self.framework_database
            elif database_name in self.registered_databases:
                db_info = self.registered_databases[database_name]["engine_info"]
            else:
                self.logger.error(f"Database '{database_name}' not found")
                return []
            
            # Use Phase 4 integrity_session pattern for session-level operations
            async with self.app_context.database.integrity_session(database_name, "get_all_tables") as session:
                # For SQLite, we can use this query to get all tables
                query = text("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name NOT LIKE 'sqlite_%'
                    ORDER BY name
                """)
                result = await session.execute(query)
                tables = [row[0] for row in result]
                return tables
        except Exception as e:
            self.logger.error(error_message(
                error_type="QUERY_FAILED",
                details=f"Error getting tables from {database_name} database: {str(e)}",
                module_id=MODULE_ID
            ))
            import traceback
            self.logger.error(traceback.format_exc())
            return []
    
    async def get_table_schema(self, table_name: str, database_name: str = "framework") -> Dict[str, Any]:
        """
        Get schema information for a specific table in the specified database.
        
        Args:
            table_name: Name of the table
            database_name: Name of the database (default: "framework")
            
        Returns:
            Dict with schema information or empty dict on error
        """
        try:
            # Get the appropriate database engine
            db_info = None
            if database_name == "framework":
                if "framework" not in self.registered_databases:
                    self.logger.error(error_message(
                        error_type="DATABASE_NOT_INITIALIZED",
                        details="Framework database not initialized",
                        module_id=MODULE_ID
                    ))
                    return {}
                db_info = self.framework_database
            elif database_name in self.registered_databases:
                db_info = self.registered_databases[database_name]["engine_info"]
            else:
                self.logger.error(error_message(
                    error_type="DATABASE_NOT_FOUND",
                    details=f"Database {database_name} not found",
                    module_id=MODULE_ID
                ))
                return {}
            
            # Check if table exists
            tables = await self.get_all_tables(database_name)
            if table_name not in tables:
                self.logger.error(error_message(
                    error_type="TABLE_NOT_FOUND",
                    details=f"Table {table_name} not found in {database_name} database",
                    module_id=MODULE_ID
                ))
                return {}
            
            # Use Phase 4 integrity_session pattern for session-level operations
            async with self.app_context.database.integrity_session(database_name, f"get_table_schema_{table_name}") as session:
                # For SQLite, get column information using PRAGMA
                columns_query = text(f"PRAGMA table_info({table_name})")
                columns_result = await session.execute(columns_query)
                
                # Process column information
                columns = []
                primary_keys = []
                
                for row in columns_result:
                    col_info = {
                        "name": row[1],  # column name
                        "type": row[2],  # data type
                        "nullable": row[3] == 0,  # notnull is 1 if NOT NULL
                        "primary_key": row[5] == 1  # pk is 1 for primary key
                    }
                    columns.append(col_info)
                    
                    if col_info["primary_key"]:
                        primary_keys.append(col_info["name"])
                
                schema_info = {
                    "columns": columns,
                    "primary_keys": primary_keys,
                    "database": database_name
                }
                
                return schema_info
                
        except Exception as e:
            self.logger.error(error_message(
                error_type="TABLE_SCHEMA_FAILED",
                details=f"Error retrieving table schema from framework database: {str(e)}",
                module_id=MODULE_ID
            ))
            import traceback
            self.logger.error(traceback.format_exc())
            return {}
    
    async def get_table_data(self, table_name: str, page: int, page_size: int, 
                            sort_by: Optional[str] = None, sort_desc: bool = False,
                            filter_column: Optional[str] = None, filter_value: Optional[str] = None,
                            database_name: str = "framework") -> Tuple[List[Dict[str, Any]], int]:
        """
        Get data from a specific table with pagination, sorting, and filtering.
        
        Args:
            table_name: Name of the table
            page: Page number (1-based)
            page_size: Number of records per page
            sort_by: Column to sort by
            sort_desc: Sort in descending order
            filter_column: Column to filter by
            filter_value: Value to filter for
            database_name: Name of the database (defaults to framework)
        
        Returns:
            Tuple of (list of records, total count) or ([], 0) on error
        """
        try:
            # Check if database exists
            if database_name == "framework":
                if "framework" not in self.registered_databases:
                    self.logger.error(error_message(
                        error_type="DATABASE_NOT_FOUND",
                        details=f"Framework database not initialized",
                        module_id=MODULE_ID
                    ))
                    return [], 0
            elif database_name not in self.registered_databases:
                self.logger.error(error_message(
                    error_type="DATABASE_NOT_FOUND",
                    details=f"Database {database_name} not found",
                    module_id=MODULE_ID
                ))
                return [], 0
            
            # Validate table name
            tables = await self.get_all_tables(database_name)
            if table_name not in tables:
                self.logger.error(error_message(
                    error_type="TABLE_NOT_FOUND",
                    details=f"Table {table_name} not found in {database_name}",
                    module_id=MODULE_ID
                ))
                return [], 0
            
            # Validate page parameters
            if page < 1:
                page = 1
            if page_size < 1:
                page_size = 50
            
            # Get the database engine
            if database_name == "framework":
                db_info = self.framework_database
            else:
                db_info = self.registered_databases[database_name]["engine_info"]
            
            # Use Phase 4 integrity_session pattern for session-level operations
            async with self.app_context.database.integrity_session(database_name, f"get_table_data_{table_name}") as session:
                # Build base query for data
                base_query = f"FROM {table_name}"
                params = {}
                
                # Add filter condition if provided
                if filter_column and filter_value is not None:
                    base_query += f" WHERE {filter_column} LIKE :filter_value"
                    params["filter_value"] = f"%{filter_value}%"
                
                # Get total count
                count_query = text(f"SELECT COUNT(*) {base_query}")
                count_result = await session.execute(count_query, params)
                total = count_result.scalar() or 0
                
                # Build data query with pagination and sorting
                data_query = f"SELECT * {base_query}"
                
                # Add sorting
                if sort_by:
                    data_query += f" ORDER BY {sort_by} {'DESC' if sort_desc else 'ASC'}"
                
                # Add pagination
                data_query += " LIMIT :limit OFFSET :offset"
                params["limit"] = page_size
                params["offset"] = (page - 1) * page_size
                
                # Execute data query
                result = await session.execute(text(data_query), params)
                rows = result.mappings().all()
                
                # Convert rows to dictionaries with proper JSON handling
                data = []
                for row in rows:
                    # Process row data
                    processed_row = {}
                    for key, value in row.items():
                        # Handle special data types
                        if value is None:
                            processed_row[key] = None
                        elif isinstance(value, (datetime, decimal.Decimal, uuid.UUID)):
                            processed_row[key] = str(value)
                        else:
                            processed_row[key] = value
                    data.append(processed_row)
                
                return data, total
                
        except Exception as e:
            self.logger.error(error_message(
                error_type="TABLE_DATA_FAILED",
                details=f"Error retrieving table data: {str(e)}",
                module_id=MODULE_ID
            ))
            import traceback
            self.logger.error(traceback.format_exc())
            return [], 0
        
    async def execute_raw_query(self, query_text: str, params: Optional[Dict[str, Any]] = None, database_name: str = "framework") -> Union[List[Dict[str, Any]], int]:
        """
        Execute a raw SQL query.
        
        Args:
            query_text: SQL query text
            params: Optional query parameters
            database_name: Name of the database (defaults to framework)
            
        Returns:
            List of records for SELECT queries, or number of affected rows for others
        """
        try:
            # Check if database exists
            if database_name == "framework":
                if "framework" not in self.registered_databases:
                    self.logger.error(error_message(
                        error_type="DATABASE_NOT_FOUND",
                        details=f"Framework database not initialized",
                        module_id=MODULE_ID
                    ))
                    raise ValueError(f"Framework database not initialized")
            elif database_name not in self.registered_databases:
                self.logger.error(error_message(
                    error_type="DATABASE_NOT_FOUND",
                    details=f"Database {database_name} not found",
                    module_id=MODULE_ID
                ))
                raise ValueError(f"Database '{database_name}' not found")
            
            # Get the database engine
            if database_name == "framework":
                db_info = self.framework_database
            else:
                db_info = self.registered_databases[database_name]["engine_info"]
            
            # Use begin() for transaction management to ensure writes are committed
            async with db_info["engine"].begin() as conn:
                result = await conn.execute(text(query_text), params or {})
                
                # If this is a SELECT query, return results
                if result.returns_rows:
                    rows = result.mappings().all()
                    return [dict(row) for row in rows]
                
                # Otherwise return rowcount
                return result.rowcount
                
        except Exception as e:
            self.logger.error(error_message(
                error_type="QUERY_EXECUTION_FAILED",
                details=f"Error executing raw query on {database_name}: {str(e)}",
                module_id=MODULE_ID
            ))
            import traceback
            self.logger.error(traceback.format_exc())
            raise
    
    def _import_schema_for_database(self, database_name):
        """Import all db_models.py files for a specific database to register SQLAlchemy models."""
        import os
        import importlib
        from core.paths import find_framework_root
        
        # Get the current project's root directory dynamically
        try:
            framework_root = find_framework_root()
            modules_dirs = [
                os.path.join(framework_root, "modules", "core"),
                os.path.join(framework_root, "modules", "standard"), 
                os.path.join(framework_root, "modules", "extensions")
            ]
        except ValueError:
            # If framework root can't be determined, fail gracefully
            self.logger.error("Could not determine framework root directory - cannot import schemas")
            return
        
        for modules_dir in modules_dirs:
            if not os.path.exists(modules_dir):
                continue
                
            for module_name in os.listdir(modules_dir):
                module_path = os.path.join(modules_dir, module_name)
                if not os.path.isdir(module_path):
                    continue
                
                db_models_path = os.path.join(module_path, "db_models.py")
                if not os.path.exists(db_models_path):
                    continue
                
                try:
                    # Read file to check DATABASE_NAME
                    with open(db_models_path, 'r') as f:
                        content = f.read()
                    
                    # Check if this module targets our database
                    import re
                    # Use separate patterns for double and single quotes
                    db_match = re.search(r'DATABASE_NAME\s*=\s*"([^"]+)"', content)
                    if not db_match:
                        db_match = re.search(r"DATABASE_NAME\s*=\s*'([^']+)'", content)
                    if db_match and db_match.group(1) == database_name:
                        # Import the module to register its models
                        module_path_part = os.path.basename(modules_dir)
                        import_path = f"modules.{module_path_part}.{module_name}.db_models"
                        
                        # Skip core.database to avoid circular imports
                        if import_path == "modules.core.database.db_models":
                            continue
                        
                        importlib.import_module(import_path)
                        self.logger.info(f"Imported schema from {import_path}")
                        
                except Exception as e:
                    self.logger.warning(f"Failed to import schema from {db_models_path}: {e}")
    
    def _create_tables_sync(self, database_name, db_info):
        """Create tables synchronously using the sync engine."""
        try:
            # Get metadata for this database
            from modules.core.database.database_infrastructure import get_database_metadata
            metadata = get_database_metadata(database_name)
            
            # Create all tables with better error handling for indexes
            from sqlalchemy import inspect
            
            # Get the inspector to check existing tables and indexes
            inspector = inspect(db_info["sync_engine"])
            existing_tables = inspector.get_table_names()
            
            # Create tables one by one to handle index conflicts gracefully
            tables_created = []
            tables_existed = []
            
            for table_name, table in metadata.tables.items():
                if table_name in existing_tables:
                    tables_existed.append(table_name)
                else:
                    try:
                        # Create the table
                        table.create(db_info["sync_engine"], checkfirst=True)
                        tables_created.append(table_name)
                    except Exception as table_error:
                        # If it's an index error, handle it gracefully
                        if "index" in str(table_error) and "already exists" in str(table_error):
                            # Table was created but index already exists - this is fine
                            tables_created.append(table_name)
                        else:
                            raise table_error
            
            # Log results professionally
            total_tables = len(metadata.tables)
            if tables_created:
                self.logger.info(f"Database '{database_name}' created with {len(tables_created)} tables")
            elif tables_existed:
                self.logger.info(f"Database '{database_name}' verified with {total_tables} existing tables")
            else:
                self.logger.info(f"Database '{database_name}' ready with {total_tables} tables")
            
        except Exception as e:
            self.logger.error(f"Failed to create tables for {database_name}: {e}")
            raise
    
    def _set_sqlite_pragmas_sync(self):
        """Set SQLite pragmas synchronously."""
        try:
            from sqlalchemy import text
            
            # Set pragmas for framework database
            if "framework" in self.registered_databases:
                engine = self.registered_databases["framework"]["engine_info"]["sync_engine"]
                with engine.connect() as conn:
                    for pragma in self.sqlite_pragmas:
                        conn.execute(text(pragma))
                self.logger.info("SQLite pragmas set for framework database")
            
            # Set pragmas for other databases
            for database_name, db_data in self.registered_databases.items():
                engine = db_data["engine_info"]["sync_engine"]
                with engine.connect() as conn:
                    for pragma in self.sqlite_pragmas:
                        conn.execute(text(pragma))
                self.logger.info(f"SQLite pragmas set for database '{database_name}'")
                
        except Exception as e:
            self.logger.error(f"Failed to set SQLite pragmas: {e}")
            raise

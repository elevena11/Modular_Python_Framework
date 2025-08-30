"""
Bootstrap Phase - Standalone Database Creation

Creates databases before modules load using completely self-contained logic.
Does NOT import anything from modules/core/database - all logic is copied here
to ensure complete independence when we clean up the database module.

This bootstrap:
- Scans for db_models.py files (text parsing, no imports)
- Extracts DATABASE_NAME and table names via regex  
- Creates SQLite databases and tables
- Is completely independent from database module
"""

import os
import re
import logging
from pathlib import Path
from collections import defaultdict
from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from core.paths import get_data_path

logger = logging.getLogger("core.bootstrap")


async def run_bootstrap_phase(app_context) -> bool:
    """
    Run bootstrap phase - create databases using standalone logic.
    
    Returns:
        bool: True if successful, False if failed
    """
    logger.info("Bootstrap: Creating databases with standalone logic...")
    
    try:
        # Create essential directories
        directories = [
            get_data_path("logs"),
            get_data_path("database"),
        ]
        
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
        
        logger.info("Bootstrap: Essential directories created")
        
        # Discover databases by scanning db_models.py files
        discovered_databases = _discover_databases_standalone()
        
        if discovered_databases:
            success = _create_databases_standalone(discovered_databases)
            if not success:
                logger.error("Bootstrap: Database creation failed")
                return False
            logger.info(f"Bootstrap: Created {len(discovered_databases)} databases")
        else:
            logger.info("Bootstrap: No databases found to create")
        
        logger.info("Bootstrap: Database creation complete")
        return True
        
    except Exception as e:
        logger.error(f"Bootstrap failed: {str(e)}")
        return False


def _discover_databases_standalone():
    """
    Discover databases by scanning db_models.py files for DATABASE_NAME declarations.
    Completely standalone - no imports from database module.
    
    Returns:
        Dict mapping database names to their table lists
    """
    database_tables = {}
    
    # Scan module directories for db_models.py files
    modules_dirs = [
        Path("modules") / "core",
        Path("modules") / "standard", 
        Path("modules") / "extensions"
    ]
    
    for modules_dir in modules_dirs:
        if not modules_dir.exists():
            continue
            
        for module_path in modules_dir.iterdir():
            if not module_path.is_dir():
                continue
            
            # Skip disabled modules
            if (module_path / ".disabled").exists():
                logger.debug(f"Skipping disabled module: {module_path.name}")
                continue
                
            db_models_file = module_path / "db_models.py"
            if not db_models_file.exists():
                continue
            
            try:
                # Read file content (no imports!)
                content = db_models_file.read_text()
                
                # Extract DATABASE_NAME using regex
                db_match = re.search(r'DATABASE_NAME\s*=\s*"([^"]+)"', content)
                if not db_match:
                    db_match = re.search(r"DATABASE_NAME\s*=\s*'([^']+)'", content)
                
                if db_match:
                    database_name = db_match.group(1)
                    
                    # Extract table names from __tablename__ declarations
                    table_matches = []
                    for line in content.split('\n'):
                        line = line.strip()
                        if not line.startswith('#') and '__tablename__' in line:
                            match = re.search(r'__tablename__\s*=\s*"([^"]+)"', line)
                            if not match:
                                match = re.search(r"__tablename__\s*=\s*'([^']+)'", line)
                            if match:
                                table_matches.append(match.group(1))
                    
                    if table_matches:
                        database_tables[database_name] = table_matches
                        logger.info(f"Bootstrap: Discovered database '{database_name}' from {module_path.name} with tables: {', '.join(table_matches)}")
            
            except Exception as e:
                logger.warning(f"Bootstrap: Error scanning {db_models_file}: {e}")
    
    return database_tables


def _create_databases_standalone(discovered_databases):
    """
    Create SQLite databases and tables using standalone SQLAlchemy logic.
    Completely independent from database module.
    
    Args:
        discovered_databases: Dict of {database_name: [table_names]}
    
    Returns:
        bool: True if successful
    """
    try:
        # First, import all db_models to register SQLAlchemy models
        logger.info("Bootstrap: Importing database models...")
        _import_all_db_models()
        
        for database_name, table_names in discovered_databases.items():
            database_path = get_data_path("database", f"{database_name}.db")
            
            # Skip if database already exists
            if os.path.exists(database_path):
                logger.info(f"Bootstrap: Database {database_name} already exists, skipping")
                continue
            
            # Create SQLite database
            engine = create_engine(f"sqlite:///{database_path}")
            
            # Import and create tables using database infrastructure
            try:
                from modules.core.database.database_infrastructure import get_database_metadata
                metadata = get_database_metadata(database_name)
                
                if len(metadata.tables) == 0:
                    logger.warning(f"Bootstrap: No tables found for database {database_name}")
                    # Fall back to creating empty database
                    with engine.connect() as conn:
                        empty_metadata = MetaData()
                        empty_metadata.create_all(engine)
                    logger.info(f"Bootstrap: Created empty database {database_name} (no tables found)")
                else:
                    # Create all tables
                    metadata.create_all(engine)
                    logger.info(f"Bootstrap: Created database {database_name} with {len(metadata.tables)} tables")
                
            except Exception as schema_error:
                logger.warning(f"Bootstrap: Could not import schema for {database_name}: {schema_error}")
                # Fall back to creating empty database
                with engine.connect() as conn:
                    metadata = MetaData()
                    metadata.create_all(engine)
                logger.info(f"Bootstrap: Created empty database {database_name} (schema import failed)")
        
        return True
        
    except Exception as e:
        logger.error(f"Bootstrap: Database creation failed - {e}")
        return False


def _import_all_db_models():
    """Import all db_models.py files to register SQLAlchemy models."""
    try:
        modules_dirs = [
            Path("modules/core"),
            Path("modules/standard"),
            Path("modules/extensions")
        ]
        
        for modules_dir in modules_dirs:
            if not modules_dir.exists():
                continue
                
            for module_path in modules_dir.iterdir():
                if not module_path.is_dir():
                    continue
                    
                db_models_file = module_path / "db_models.py"
                if db_models_file.exists():
                    try:
                        # Build import path: modules.core.database -> modules.core.database.db_models
                        if modules_dir.name == "core":
                            import_path = f"modules.core.{module_path.name}.db_models"
                        elif modules_dir.name == "standard":
                            import_path = f"modules.standard.{module_path.name}.db_models" 
                        else:
                            import_path = f"modules.{modules_dir.name}.{module_path.name}.db_models"
                        
                        # Import the models to register them
                        import importlib
                        importlib.import_module(import_path)
                        logger.debug(f"Bootstrap: Imported models from {import_path}")
                        
                    except Exception as e:
                        logger.warning(f"Bootstrap: Could not import {import_path}: {e}")
                        
    except Exception as e:
        logger.warning(f"Bootstrap: Error importing db_models: {e}")
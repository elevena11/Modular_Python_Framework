#!/usr/bin/env python3
"""
setup_db.py
Updated: March 30, 2025
Improved SQLite database setup script with robust path handling and migration support
"""

import os
import json
import sys
import logging
import shutil
import platform
import argparse
import subprocess
import traceback
from pathlib import Path
from datetime import datetime

# Find project root - should work whether script is run from root or elsewhere
def find_project_root():
    """Find the project root directory."""
    # Start with the directory containing this script
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # If script is in project root, current_dir is already the project root
    if os.path.exists(os.path.join(current_dir, "modules")):
        return current_dir
        
    # Navigate up the directory tree looking for project root markers
    while current_dir and not os.path.exists(os.path.join(current_dir, "modules")):
        parent_dir = os.path.dirname(current_dir)
        if parent_dir == current_dir:  # Reached filesystem root
            break
        current_dir = parent_dir
    
    if not os.path.exists(os.path.join(current_dir, "modules")):
        # If we still can't find it, try the current working directory
        current_dir = os.getcwd()
        if not os.path.exists(os.path.join(current_dir, "modules")):
            raise ValueError("Could not locate project root directory containing 'modules' folder")
    
    return current_dir

# Find the project root
PROJECT_ROOT = find_project_root()

# Ensure project root is in Python path for module imports
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Configure logging
log_dir = os.path.join(PROJECT_ROOT, "data", "logs")
os.makedirs(log_dir, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(log_dir, "setup_db.log"), mode='a')
    ]
)
logger = logging.getLogger("modular.setup_db")

def setup_db_config(force_reset=False):
    """
    Interactive setup for SQLite database configuration.
    
    Args:
        force_reset: Whether to force reset the database if it exists
    
    Returns:
        True if successful, False otherwise
    """
    print("=" * 70)
    print("        Modular AI Framework - SQLite Database Setup")
    print("=" * 70)
    print(f"\nProject root directory: {PROJECT_ROOT}")
    print("\nThis script will configure a SQLite database for the Modular AI Framework.")
    
    try:
        # Set up the data directory for SQLite - use absolute paths
        data_dir = os.path.abspath(os.path.join(PROJECT_ROOT, "data"))
        os.makedirs(data_dir, exist_ok=True)
        
        # Set up logs directory
        logs_dir = os.path.join(data_dir, "logs")
        os.makedirs(logs_dir, exist_ok=True)
        
        # Set up database directory
        db_dir = os.path.join(data_dir, "database")
        os.makedirs(db_dir, exist_ok=True)
        
        logger.info(f"Database directory created: {db_dir}")
        print(f"\nDatabase directory: {db_dir}")
        
        # Use directory-only database URL for multi-database architecture
        print(f"\nUsing directory-based database configuration: {db_dir}")
        print("Individual database files will be created as needed (framework.db, etc.)")
        
        # Check if any database files exist in the directory
        db_files = [f for f in os.listdir(db_dir) if f.endswith('.db')] if os.path.exists(db_dir) else []
        db_exists = len(db_files) > 0
        
        # Handle force reset
        if db_exists and force_reset:
            print(f"\nForce reset requested, removing {len(db_files)} existing database files...")
            for db_file in db_files:
                db_path = os.path.join(db_dir, db_file)
                _cleanup_database_files(db_path)
            db_exists = False
        elif db_exists:
            print(f"\nFound {len(db_files)} existing database files: {', '.join(db_files)}")
            confirm = input("Would you like to reset all databases? [y/N]: ").lower()
            if confirm == 'y':
                print("Removing existing database files...")
                for db_file in db_files:
                    db_path = os.path.join(db_dir, db_file)
                    _cleanup_database_files(db_path)
                db_exists = False
        
        # Create the database URL with directory-only format for multi-database architecture
        # Always use forward slashes in database URL regardless of platform
        db_url_path = db_dir.replace('\\', '/')
        db_url = f"sqlite:///{db_url_path}/"
        
        # Save to configuration file
        config_path = os.path.join(data_dir, "db_config.json")
        with open(config_path, 'w') as f:
            json.dump({
                "database_url": db_url,
                "database_type": "sqlite",
                "created_at": datetime.now().isoformat(),
                "platform": platform.system(),
                "db_path": db_dir
            }, f, indent=2)
        
        logger.info(f"Configuration saved to {config_path}")
        print(f"\nConfiguration saved to {config_path}")
        
        if not db_exists:
            print(f"Database directory is ready: {db_dir}")
            print("Database files will be created automatically when the application starts.")
        else:
            print(f"Using existing database files in: {db_dir}")
        
        # Make sure environment variable DATA_DIR is set properly for migrations
        if "DATA_DIR" not in os.environ:
            os.environ["DATA_DIR"] = data_dir
        
        # Update environment variable for modules
        if PROJECT_ROOT not in sys.path:
            sys.path.insert(0, PROJECT_ROOT)
        
        print("\nDatabase configuration complete!")
        print("\nNext steps:")
        print("1. Start the application:")
        print("   python app.py")
        print("2. Database tables will be created automatically on first startup")
        print("3. Each module manages its own database schema independently")
            
        print("\nTo start with a completely fresh database later, run:")
        print(f"   python setup_db.py --reset")
        print("\nThe application will also recreate necessary database tables on startup if they don't exist.")
        print("=" * 70)
        
        return True
    except Exception as e:
        logger.error(f"Error during database setup: {str(e)}")
        logger.error(traceback.format_exc())
        print(f"\nError during setup: {str(e)}")
        print("See logs for more details.")
        return False

def _cleanup_database_files(db_path):
    """
    Clean up database files including WAL and SHM files.
    
    Args:
        db_path: Path to the main database file
    """
    # Remove the main database file
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
            logger.info(f"Removed database file: {db_path}")
        except Exception as e:
            logger.warning(f"Could not remove database file: {str(e)}")
    
    # Remove WAL file if it exists
    wal_path = f"{db_path}-wal"
    if os.path.exists(wal_path):
        try:
            os.remove(wal_path)
            logger.info(f"Removed WAL file: {wal_path}")
        except Exception as e:
            logger.warning(f"Could not remove WAL file: {str(e)}")
    
    # Remove SHM file if it exists
    shm_path = f"{db_path}-shm"
    if os.path.exists(shm_path):
        try:
            os.remove(shm_path)
            logger.info(f"Removed SHM file: {shm_path}")
        except Exception as e:
            logger.warning(f"Could not remove SHM file: {str(e)}")

# Migration functions removed - no longer needed with multi-database architecture
# Each module now manages its own database schema independently

def main():
    """Main function."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Set up SQLite database for Modular AI Framework')
    parser.add_argument('--reset', action='store_true', help='Force reset all databases if they exist')
    
    args = parser.parse_args()
    
    # Check for confirmation before reset
    if args.reset:
        print("WARNING: This will DELETE ALL DATA in your databases!")
        confirm = input("Type 'yes' to confirm database reset: ")
        
        if confirm.lower() != 'yes':
            print("Database reset cancelled.")
            return False
    
    return setup_db_config(force_reset=args.reset)

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\nSetup canceled by user.")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error during setup: {str(e)}")
        logger.error(traceback.format_exc())
        print(f"\nUnexpected error during setup: {str(e)}")
        print("See logs for more details.")
        sys.exit(1)

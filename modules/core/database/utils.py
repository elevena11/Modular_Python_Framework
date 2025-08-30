"""
modules/core/database/utils.py
Utility functions for the database module.
Updated for SQLite compatibility.
"""

import os
import json
import logging
import random
import asyncio
from typing import Optional, Any, Dict, Callable, Awaitable
from sqlalchemy.exc import OperationalError

def redact_connection_url(url):
    """
    Redact sensitive information from database connection URL.
    
    Args:
        url: Database connection URL
        
    Returns:
        Redacted URL with username, password removed but keeping server info
    """
    if not url:
        return "<empty url>"
        
    try:
        # Handle SQLite URL
        if url.startswith("sqlite:///"):
            # Just return the SQLite connection with path
            return url
            
        # For other database types (e.g., PostgreSQL)
        if "://" in url:
            protocol, rest = url.split("://", 1)
            
            # Handle URL with authentication
            if "@" in rest:
                # Remove everything before the @ symbol (username:password)
                _, server_part = rest.split("@", 1)
                
                # Keep server, port and database name
                return f"{protocol}://*****@{server_part}"
            else:
                # URL without authentication
                return f"{protocol}://{rest}"
        return url
    except Exception:
        # If parsing fails, return a generic message
        return "<database connection>"

def safe_log_connection(url, logger):
    """
    Safely log a database connection URL without sensitive information.
    
    Args:
        url: Database connection URL
        logger: Logger instance
    """
    safe_url = redact_connection_url(url)
    logger.info(f"Database connection URL: {safe_url}")

def get_db_path_from_url(url):
    """
    Extract the database file path from a SQLite connection URL.
    
    Args:
        url: SQLite connection URL
        
    Returns:
        Path to the SQLite database file or None if not a SQLite URL
    """
    if url.startswith("sqlite:///"):
        # Extract the file path part
        return url[10:]
    return None

def get_db_dir_from_url(url):
    """
    Extract the database directory from a SQLite connection URL.
    
    Args:
        url: SQLite connection URL
        
    Returns:
        Directory containing the SQLite database file or None if not a SQLite URL
    """
    path = get_db_path_from_url(url)
    if path:
        return os.path.dirname(path)
    return None

def ensure_db_directory_exists(url):
    """
    Ensure the directory for the SQLite database exists.
    
    Args:
        url: SQLite connection URL
        
    Returns:
        True if directory exists or was created, False on error
    """
    try:
        db_dir = get_db_dir_from_url(url)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
            return True
        return True
    except Exception:
        return False

async def execute_with_retry(coro, max_retries=5, base_delay=0.1, max_delay=2.0):
    """
    Execute a coroutine with retry logic for SQLite concurrent access issues.
    
    Args:
        coro: The coroutine to execute
        max_retries: Maximum number of retry attempts
        base_delay: Base delay between retries in seconds
        max_delay: Maximum delay between retries in seconds
        
    Returns:
        The result of the coroutine execution
        
    Raises:
        The last encountered exception if all retries fail
    """
    logger = logging.getLogger("modular.database.utils")
    
    attempts = 0
    last_error = None
    
    while attempts <= max_retries:
        try:
            return await coro
        except OperationalError as e:
            # Check if this is a database locked error
            if "database is locked" in str(e).lower():
                attempts += 1
                if attempts > max_retries:
                    logger.error(f"Max retries exceeded ({max_retries}) for database operation")
                    raise
                
                # Calculate exponential backoff with jitter
                delay = min(base_delay * (2 ** (attempts - 1)) * (0.5 + random.random()), max_delay)
                
                logger.warning(f"Database locked, retrying in {delay:.2f}s (attempt {attempts}/{max_retries})")
                await asyncio.sleep(delay)
                last_error = e
            else:
                # Re-raise if it's not a locking issue
                raise
        except Exception as e:
            # Re-raise other exceptions immediately
            raise
    
    # We shouldn't get here, but just in case
    if last_error:
        raise last_error

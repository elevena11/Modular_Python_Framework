"""
core/paths.py
Framework path management utilities for consistent data directory access.
"""

import os
import sys
from pathlib import Path
from typing import Union

def find_framework_root() -> Path:
    """
    Find the framework root directory by looking for the 'modules' folder.
    
    This function works whether called from:
    - Framework root directory
    - Any subdirectory within the framework
    - Module files at any depth
    
    Returns:
        Path object pointing to the framework root directory
        
    Raises:
        ValueError: If framework root cannot be located
    """
    # Start with the directory containing this file (core/paths.py)
    current_dir = Path(__file__).parent.parent.absolute()
    
    # If we're already at root and modules exists, return it
    if (current_dir / "modules").exists():
        return current_dir
        
    # Navigate up the directory tree looking for 'modules' folder
    search_dir = current_dir
    while search_dir.parent != search_dir:  # While not at filesystem root
        if (search_dir / "modules").exists():
            return search_dir
        search_dir = search_dir.parent
    
    # If we still can't find it, try the current working directory
    cwd = Path.cwd()
    if (cwd / "modules").exists():
        return cwd
        
    # Last resort: check if we're running from within the framework structure
    # Look for framework markers in parent directories
    for parent in Path(__file__).parents:
        if (parent / "modules").exists() and (parent / "core").exists():
            return parent
    
    raise ValueError(
        "Could not locate framework root directory. "
        "Expected to find a 'modules' directory in the framework root."
    )

# Global framework root - calculated once at import
FRAMEWORK_ROOT = find_framework_root()

def get_framework_root() -> Path:
    """Get the framework root directory as a Path object."""
    return FRAMEWORK_ROOT

def get_data_path(*path_parts: Union[str, Path]) -> Path:
    """
    Get a path within the framework's data directory.
    
    Args:
        *path_parts: Path components to join with the data directory
        
    Returns:
        Path object pointing to the requested location in data/
        
    Examples:
        get_data_path("logs", "app.log") -> /framework/data/logs/app.log
        get_data_path("llm_memory", "chromadb") -> /framework/data/llm_memory/chromadb
    """
    return FRAMEWORK_ROOT / "data" / Path(*path_parts)

def get_module_data_path(module_name: str, *path_parts: Union[str, Path]) -> Path:
    """
    Get a path within a module's data directory.
    
    Args:
        module_name: Name of the module (e.g., "llm_memory_processing")
        *path_parts: Additional path components
        
    Returns:
        Path object pointing to the module's data directory
        
    Examples:
        get_module_data_path("llm_memory_processing", "database.db")
        -> /framework/data/llm_memory_processing/database.db
    """
    return get_data_path(module_name, *path_parts)

def ensure_data_path(*path_parts: Union[str, Path]) -> Path:
    """
    Ensure a data directory path exists, creating it if necessary.
    
    Args:
        *path_parts: Path components to join with the data directory
        
    Returns:
        Path object pointing to the created directory
    """
    path = get_data_path(*path_parts)
    path.mkdir(parents=True, exist_ok=True)
    return path

def ensure_module_data_path(module_name: str, *path_parts: Union[str, Path]) -> Path:
    """
    Ensure a module data directory path exists, creating it if necessary.
    
    Args:
        module_name: Name of the module
        *path_parts: Additional path components
        
    Returns:
        Path object pointing to the created directory
    """
    path = get_module_data_path(module_name, *path_parts)
    path.mkdir(parents=True, exist_ok=True)
    return path

# Convenience functions for common paths
def get_logs_path(*path_parts: Union[str, Path]) -> Path:
    """Get a path within the logs directory."""
    return get_data_path("logs", *path_parts)

def get_database_path(*path_parts: Union[str, Path]) -> Path:
    """Get a path within the database directory.""" 
    return get_data_path("database", *path_parts)

def get_memory_path(*path_parts: Union[str, Path]) -> Path:
    """Get a path within the llm_memory directory."""
    return get_data_path("llm_memory", *path_parts)

def ensure_logs_path(*path_parts: Union[str, Path]) -> Path:
    """Ensure a logs directory path exists."""
    return ensure_data_path("logs", *path_parts)

def ensure_memory_path(*path_parts: Union[str, Path]) -> Path:
    """Ensure a memory directory path exists."""
    return ensure_data_path("llm_memory", *path_parts)

# Export commonly used paths as constants
DATA_ROOT = get_data_path()
LOGS_ROOT = get_logs_path()
DATABASE_ROOT = get_database_path()
MEMORY_ROOT = get_memory_path()
"""
ui/utils/formatting.py
Formatting utility functions for UI display.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List

logger = logging.getLogger("ui.utils.formatting")

def format_timestamp(timestamp, format_str="%Y-%m-%d %H:%M:%S"):
    """
    Format a timestamp for display.
    
    Args:
        timestamp: Timestamp (datetime, string, or unix timestamp)
        format_str: Format string for output
        
    Returns:
        Formatted timestamp string
    """
    if not timestamp:
        return ""
        
    try:
        # Handle different timestamp types
        if isinstance(timestamp, datetime):
            dt = timestamp
        elif isinstance(timestamp, (int, float)):
            dt = datetime.fromtimestamp(timestamp)
        elif isinstance(timestamp, str):
            # Try parsing ISO format
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        else:
            return str(timestamp)
            
        return dt.strftime(format_str)
    except Exception as e:
        logger.warning(f"Error formatting timestamp {timestamp}: {str(e)}")
        return str(timestamp)

def format_file_size(size_bytes):
    """
    Format file size in human-readable format.
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        Human-readable size string
    """
    if not isinstance(size_bytes, (int, float)):
        return str(size_bytes)
        
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024 or unit == 'TB':
            if unit == 'B':
                return f"{size_bytes} {unit}"
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024
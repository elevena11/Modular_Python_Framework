"""
modules/core/scheduler/utils.py
Updated: April 6, 2025
Utility functions and classes for the scheduler module
"""

from typing import Dict, Any, Optional
from datetime import datetime, timedelta

# Note: We don't need to define MODULE_ID here since this file only contains helpers
# and doesn't do any logging or error handling that requires the ID

def parse_cron_expression(cron_expression: str) -> datetime:
    """
    Parse a cron expression and return the next execution time.
    
    Args:
        cron_expression: Cron-style expression (e.g., "0 0 * * *" for daily at midnight)
        
    Returns:
        datetime: Next execution time
    """
    # This is a simplified implementation
    # In a production environment, you would use a full cron parser library
    
    parts = cron_expression.split()
    if len(parts) != 5:
        raise ValueError("Invalid cron expression format")
    
    # For now, just return a simple approximation
    # In a real implementation, this would be much more sophisticated
    
    # Minute (0-59)
    minute = 0 if parts[0] == "*" else int(parts[0])
    
    # Hour (0-23)
    hour = 0 if parts[1] == "*" else int(parts[1])
    
    # Get current time as starting point
    now = datetime.now()
    
    # Create a target time for today
    target = datetime(
        now.year, 
        now.month, 
        now.day, 
        hour, 
        minute, 
        0
    )
    
    # If target time is in the past, add one day
    if target <= now:
        target += timedelta(days=1)
    
    return target

def calculate_next_execution(
    base_time: datetime,
    interval_type: str,
    interval_value: int
) -> datetime:
    """
    Calculate the next execution time based on interval.
    
    Args:
        base_time: Base time to calculate from
        interval_type: Type of interval (minutes, hours, days, weeks, months)
        interval_value: Number of interval units
        
    Returns:
        datetime: Next execution time
    """
    if interval_type == "minutes":
        return base_time + timedelta(minutes=interval_value)
    elif interval_type == "hours":
        return base_time + timedelta(hours=interval_value)
    elif interval_type == "days":
        return base_time + timedelta(days=interval_value)
    elif interval_type == "weeks":
        return base_time + timedelta(weeks=interval_value)
    elif interval_type == "months":
        # Approximate months as 30 days for simplicity
        return base_time + timedelta(days=30 * interval_value)
    else:
        # Default to hours if unknown interval type
        return base_time + timedelta(hours=interval_value)

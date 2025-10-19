"""
core/error_utils.py
Created: August 9, 2025

Pure error handling utilities with zero dependencies.
File-based error logging with no circular dependencies.

This module provides immediate error handling, logging, and response generation
without requiring any framework services or module imports.

Architecture:
- Zero imports from framework modules
- Direct JSONL file logging
- Standard library only
- High performance, low overhead
- Works even if other services are down
"""

import os
import json
import time
import logging
import inspect
from datetime import datetime
from typing import Dict, Any, Optional, Union
from fastapi import HTTPException

# Constants - using environment variables for paths
DATA_DIR = os.getenv("DATA_DIR", "./data")
ERROR_LOGS_DIR = os.path.join(DATA_DIR, "error_logs")

# Create error logs directory (self-contained module responsibility)
os.makedirs(ERROR_LOGS_DIR, exist_ok=True)

class Result:
    """
    Standard result object for all service operations.
    
    Usage:
        # Success case - ALWAYS use the 'data=' keyword argument
        return Result.success(data={"user_id": 123})
        
        # Error case
        return Result.error(code="USER_NOT_FOUND", message="User not found")
        
    Important:
        - Always use the 'data=' keyword when calling Result.success()
        - Never return raw dictionaries from service methods
        - Always check result.success before accessing result.data
    """
    
    def __init__(self, success=False, data=None, error=None):
        """
        Initialize a result object.
        
        Args:
            success (bool): Whether the operation was successful
            data (Any): Data to return in case of success
            error (Dict): Error information in case of failure
        """
        self.success = success
        self.data = data
        self.error = error or {}
    
    @classmethod
    def success(cls, data=None):
        """
        Create a success result with data.
        
        Args:
            data: The data to include in the successful result
                Must be passed as named parameter 'data='
        
        Returns:
            A Result object with success=True and the provided data
        
        Raises:
            TypeError: If data is passed as a positional argument or is a Result object
        """
        # If data is a Result object, it's likely a programming error
        if isinstance(data, cls):
            frame = inspect.currentframe().f_back
            caller = inspect.getframeinfo(frame).function
            caller_filename = inspect.getframeinfo(frame).filename
            line_number = inspect.getframeinfo(frame).lineno
            
            error_msg = (
                f"Result.success() in '{caller}' at {caller_filename}:{line_number} was passed a Result object. "
                f"Did you mean to return the Result directly instead of wrapping it again?"
            )
            
            raise TypeError(error_msg)
            
        return cls(success=True, data=data)
    
    @classmethod
    def error(cls, code, message, details=None):
        """
        Create an error result.
        
        Args:
            code (str): Error code - should be base code without prefix
            message (str): Human-readable error message
            details (Dict, optional): Additional error details
            
        Returns:
            A Result object with success=False and the provided error information
        """
        error_info = {
            "code": code,
            "message": message
        }
        
        if details:
            error_info["details"] = details

        return cls(success=False, error=error_info)

    @property
    def code(self):
        """
        Get error code (for errors) or None (for success).

        Provides intuitive access: result.code instead of result.error.get("code")

        Returns:
            str: Error code if this is an error result, None if success
        """
        return self.error.get("code") if not self.success else None

    @property
    def message(self):
        """
        Get error message (for errors) or None (for success).

        Provides intuitive access: result.message instead of result.error.get("message")

        Returns:
            str: Error message if this is an error result, None if success
        """
        return self.error.get("message") if not self.success else None

    @property
    def details(self):
        """
        Get error details (for errors) or None (for success).

        Provides intuitive access: result.details instead of result.error.get("details")

        Returns:
            Any: Error details if this is an error result, None if success
        """
        return self.error.get("details") if not self.success else None

    def __str__(self):
        """String representation of the Result."""
        if self.success:
            return f"Result(success=True, data={self.data})"
        else:
            return f"Result(success=False, error={self.error})"
            
    def __repr__(self):
        """Debug representation of the Result."""
        return self.__str__()

def create_error_response(module_id: str, code: str, message: str, details: Any = None, status_code: int = 400) -> HTTPException:
    """
    Create a standardized HTTP error response.

    Args:
        module_id (str): The dot-separated module identifier (e.g., "core.database").
        code (str): The base error code (e.g., "CONNECTION_FAILED").
        message (str): Human-readable error message.
        details (Any, optional): Optional additional details. Defaults to None.
        status_code (int, optional): HTTP status code. Defaults to 400.

    Returns:
        FastAPI HTTPException with standardized error format
    """
    # Create the underscore-formatted code for the response body
    module_prefix_underscores = module_id.replace('.', '_')
    error_code_response = f"{module_prefix_underscores}_{code}"

    # Log the error using the explicit module_id and base code
    _log_error_to_jsonl(module_id=module_id, code=code, message=message, details=details)

    # Create error response detail
    error_response = {
        "status": "error",
        "code": error_code_response,
        "message": message
    }

    # Add details if provided
    if details is not None:
        error_response["details"] = details

    # Create and return HTTPException
    return HTTPException(
        status_code=status_code,
        detail=error_response
    )

def error_message(module_id: str, error_type: str, details: str, location: str = None, context: Optional[Dict[str, Any]] = None) -> str:
    """
    Create a standardized error message and log it to error logs.

    Args:
        module_id (str): The dot-separated module identifier (e.g., "core.database").
        error_type (str): The base error type (e.g., "CONNECTION_FAILED").
        details (str): Error details.
        location (str, optional): Location in code (auto-detected if None). Defaults to None.
        context (Dict[str, Any], optional): Additional structured context for the error. Defaults to None.

    Returns:
        Formatted error message: "module_id_base_code - DETAILS in LOCATION [context_key=value, ...]"
    """
    # Auto-detect location if not provided
    if location is None:
        location = _detect_calling_location()

    # Create the underscore-formatted code for the return message
    module_prefix_underscores = module_id.replace('.', '_')
    error_code_full = f"{module_prefix_underscores}_{error_type}"

    # Log the error using the explicit module_id and base error_type
    _log_error_to_jsonl(
        module_id=module_id,
        code=error_type,
        message=details,
        location=location,
        context=context
    )

    # Build the formatted message
    message = f"{error_code_full} - {details} in {location}"

    # Append context if provided
    if context:
        context_str = ", ".join(f"{k}={v}" for k, v in context.items())
        message += f" [{context_str}]"

    return message

def _log_error_to_jsonl(module_id: str, code: str, message: str, details: Any = None, location: str = None, context: Optional[Dict[str, Any]] = None) -> None:
    """
    Log an error directly to JSONL file.

    Args:
        module_id (str): The dot-separated module identifier (e.g., "core.database").
        code (str): The base error code (e.g., "CONNECTION_FAILED").
        message (str): Error message.
        details (Any, optional): Error details. Defaults to None.
        location (str, optional): Location in code where the error occurred (auto-detected if None).
        context (Dict[str, Any], optional): Additional structured context for the error. Defaults to None.
    """
    try:
        # Get session ID from environment or generate basic one
        session_id = os.getenv("SESSION_ID", f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_unknown")

        # Get log file path with current date
        date_str = datetime.now().strftime("%Y%m%d")
        log_file = os.path.join(ERROR_LOGS_DIR, f"{date_str}-error.jsonl")

        # Get caller information if location not provided
        if location is None:
            location = _detect_calling_location()

        # Create error entry - matching documented JSONL format
        timestamp = datetime.now().isoformat() + "Z"
        error_entry = {
            "timestamp": timestamp,
            "module_id": module_id,
            "error_type": code,
            "details": message,
            "location": location,
            "session_id": session_id
        }

        # Add structured context if provided (industry standard pattern)
        if context is not None:
            error_entry["context"] = context

        # Add additional details if provided
        if details is not None:
            if isinstance(details, Exception):
                error_entry["exception_details"] = {
                    "type": details.__class__.__name__,
                    "message": str(details)
                }
            elif isinstance(details, dict):
                error_entry["additional_details"] = details
            else:
                error_entry["additional_details"] = {"value": str(details)}

        # Write to log file - atomic append operation
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(error_entry) + "\n")

    except Exception as e:
        # Fallback to stderr if file logging fails
        print(f"ERROR: Failed to log error to JSONL: {e}", flush=True)
        print(f"Original error: {module_id}.{code} - {message}", flush=True)

def _detect_calling_location() -> str:
    """
    Detect the location where the error is being logged from.
    
    Returns:
        Location string (e.g., "database.py:143" or "function_name()")
    """
    # Get the call stack
    stack = inspect.stack()
    
    # Find the first frame that's not in this file
    for frame in stack[1:]:  # Skip the current function
        # Check if it's not in this file
        if frame.filename != __file__:
            # Get the filename without path
            filename = os.path.basename(frame.filename)
            
            # Try to get function name
            function_name = frame.function
            
            # Return with line number if available
            if frame.lineno:
                return f"{filename}:{frame.lineno}"
            elif function_name:
                return f"{function_name}()"
            else:
                return filename
    
    # Fallback if detection fails
    return "unknown_location"
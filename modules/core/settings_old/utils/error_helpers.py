"""
modules/core/settings/utils/error_helpers.py
Updated: April 5, 2025
Shared error handling utilities for settings module
"""

import logging
import traceback
from typing import Callable, TypeVar, Any, Dict, Optional, Awaitable

from core.error_utils import error_message, Result

# Type variable for generic functions
T = TypeVar('T')

# Define MODULE_ID for use in error messages
MODULE_ID = "core.settings"
logger = logging.getLogger(MODULE_ID)

async def handle_operation(
    operation: Callable[[], Awaitable[T]],
    module_id: str,
    error_type: str,
    details_prefix: str,
    location: str,
    default_value: Optional[T] = None
) -> T:
    """
    Execute an operation with standardized error handling.
    
    Args:
        operation: Async function to execute
        module_id: Module or component identifier
        error_type: Base error type
        details_prefix: Prefix for error details
        location: Code location for error message
        default_value: Default value to return on error
        
    Returns:
        Result of operation or default_value on error
    """
    try:
        return await operation()
    except Exception as e:
        logger.error(error_message(
            module_id=module_id,
            error_type=error_type,
            details=f"{details_prefix}: {str(e)}",
            location=location
        ))
        logger.error(traceback.format_exc())
        return default_value

async def handle_result_operation(
    operation: Callable[[], Awaitable[Any]],
    module_id: str,
    error_type: str,
    error_message_text: str,
    location: str,
    details: Optional[Dict[str, Any]] = None
) -> Result:
    """
    Execute an operation and return a Result object.
    
    Args:
        operation: Async function to execute
        module_id: Module or component identifier
        error_type: Base error type
        error_message_text: Human-readable error message
        location: Code location for error message
        details: Additional details for error
        
    Returns:
        Result.success with operation result or Result.error on failure
    """
    try:
        result = await operation()
        return Result.success(data=result)
    except Exception as e:
        logger.error(error_message(
            module_id=module_id,
            error_type=error_type,
            details=f"{error_message_text}: {str(e)}",
            location=location
        ))
        logger.error(traceback.format_exc())
        
        error_details = details or {}
        error_details["error"] = str(e)
        
        return Result.error(
            code=error_type,
            message=error_message_text,
            details=error_details
        )

def check_initialization(service, module_id: str, operation: str) -> bool:
    """
    Check if a service is initialized.
    
    Args:
        service: Service to check
        module_id: Module or component identifier
        operation: Operation being performed
        
    Returns:
        True if initialized, False otherwise
    """
    if not hasattr(service, 'initialized') or not service.initialized:
        logger.error(error_message(
            module_id=module_id,
            error_type="SERVICE_NOT_INITIALIZED",
            details=f"Cannot perform {operation} - service not initialized",
            location=operation
        ))
        return False
    return True

def log_operation_result(success: bool, module_id: str, operation: str, 
                         success_msg: str, error_type: str = None, 
                         error_msg: str = None) -> None:
    """
    Log the result of an operation.
    
    Args:
        success: Whether the operation succeeded
        module_id: Module or component identifier
        operation: Operation being performed
        success_msg: Message to log on success
        error_type: Base error type for error
        error_msg: Message to log on error
    """
    if success:
        logger.info(success_msg)
    else:
        logger.error(error_message(
            module_id=module_id,
            error_type=error_type or "OPERATION_FAILED",
            details=error_msg or f"Failed to perform {operation}",
            location=operation
        ))

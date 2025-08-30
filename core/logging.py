"""
core/logging.py
Framework-aware logging system for automatic LLM adoption

This module provides framework-aware logging that automatically captures
standard logging patterns and feeds them into framework error tracking.
LLMs can use standard logging and it will "just work" with our system.
"""

import logging
import inspect
import functools
from typing import Optional, Dict, Any
from core.error_utils import Result, error_message, _log_error_to_jsonl


class FrameworkLogger:
    """
    Framework-aware logger that automatically feeds framework error tracking.
    
    This logger acts as a transparent proxy that:
    1. Provides standard logging interface (logger.info, logger.error, etc.)
    2. Automatically extracts module context from caller
    3. Routes errors to framework error tracking system
    4. Makes framework patterns look like standard Python logging
    
    Usage (looks completely standard to LLMs):
        logger = get_framework_logger(__name__)
        logger.error("Something went wrong")  # Automatically tracked by framework
    """
    
    def __init__(self, name: str, original_logger: logging.Logger = None):
        self.name = name
        self.original_logger = original_logger or logging.getLogger(name)
        
        # Extract module_id from logger name if possible
        self.module_id = self._extract_module_id(name)
    
    def _extract_module_id(self, name: str) -> str:
        """Extract framework module_id from logger name."""
        # Handle common patterns:
        # modules.core.database -> core.database
        # modules.standard.semantic_core -> standard.semantic_core
        if name.startswith('modules.'):
            return name.replace('modules.', '', 1)
        
        # Handle direct module imports:
        # core.database, standard.semantic_core
        if '.' in name and any(name.startswith(prefix) for prefix in ['core.', 'standard.', 'custom.']):
            return name
            
        # Handle file-based names:
        # services, api, utils -> try to infer from call stack
        return self._infer_module_from_stack()
    
    def _infer_module_from_stack(self) -> str:
        """Infer module_id from the call stack."""
        try:
            # Look through call stack for module indicators
            for frame_info in inspect.stack()[2:]:  # Skip this method and caller
                filename = frame_info.filename
                
                # Look for modules/ directory structure
                if '/modules/' in filename:
                    # Extract from path: .../modules/core/database/services.py -> core.database
                    parts = filename.split('/modules/')[-1].split('/')
                    if len(parts) >= 3:  # ['core', 'database', 'services.py']
                        return f"{parts[0]}.{parts[1]}"
                
                # Look for module indicators in path
                if any(indicator in filename for indicator in ['core/', 'standard/', 'custom/']):
                    # Try to extract module path
                    for prefix in ['core/', 'standard/', 'custom/']:
                        if prefix in filename:
                            path_after_prefix = filename.split(prefix)[-1]
                            module_part = path_after_prefix.split('/')[0]
                            return f"{prefix.rstrip('/')}.{module_part}"
            
            # Fallback to logger name
            return self.name
            
        except Exception:
            # If inference fails, use logger name
            return self.name
    
    def _get_caller_location(self) -> str:
        """Get the location of the actual caller (not this logger)."""
        try:
            # Skip framework logger methods to find real caller
            for frame_info in inspect.stack()[2:]:
                filename = frame_info.filename
                
                # Skip internal logging and framework files
                if any(skip in filename for skip in ['/logging.py', '/core/logging.py', 'python/lib']):
                    continue
                
                # Found the real caller
                import os
                return f"{os.path.basename(filename)}:{frame_info.lineno}"
                
        except Exception:
            return "unknown_location"
        
        return "unknown_location"
    
    def error(self, message: str, *args, **kwargs):
        """Error logging with automatic framework tracking."""
        # Format message if args provided
        if args:
            try:
                formatted_message = message % args
            except (TypeError, ValueError):
                formatted_message = f"{message} {args}"
        else:
            formatted_message = message
        
        # Get caller location
        location = self._get_caller_location()
        
        # Extract error details from kwargs
        details = kwargs.pop('extra', {}) if 'extra' in kwargs else {}
        if 'exc_info' in kwargs and kwargs['exc_info']:
            # If exception info provided, extract it
            import sys
            if kwargs['exc_info'] is True:
                exc_info = sys.exc_info()
            else:
                exc_info = kwargs['exc_info']
            
            if exc_info and exc_info[1]:
                details['exception'] = {
                    'type': exc_info[0].__name__ if exc_info[0] else 'Unknown',
                    'message': str(exc_info[1])
                }
        
        # Feed to framework error tracking
        try:
            # Generate error type from message (simple heuristic)
            error_type = self._generate_error_type(formatted_message)
            
            # Use framework error tracking
            _log_error_to_jsonl(
                module_id=self.module_id,
                code=error_type,
                message=formatted_message,
                details=details if details else None,
                location=location
            )
        except Exception as e:
            # If framework tracking fails, don't break logging
            self.original_logger.warning(f"Framework error tracking failed: {e}")
        
        # Always call original logger
        self.original_logger.error(formatted_message, **kwargs)
    
    def warning(self, message: str, *args, **kwargs):
        """Warning logging with framework tracking for significant warnings."""
        # Format message
        if args:
            try:
                formatted_message = message % args
            except (TypeError, ValueError):
                formatted_message = f"{message} {args}"
        else:
            formatted_message = message
        
        # Only track warnings that look like errors or significant issues
        if self._should_track_warning(formatted_message):
            location = self._get_caller_location()
            details = kwargs.pop('extra', {}) if 'extra' in kwargs else {}
            
            try:
                error_type = self._generate_error_type(formatted_message, prefix="WARNING")
                _log_error_to_jsonl(
                    module_id=self.module_id,
                    code=error_type,
                    message=formatted_message,
                    details=details if details else None,
                    location=location
                )
            except Exception:
                pass  # Don't break logging if tracking fails
        
        # Always call original logger
        self.original_logger.warning(formatted_message, **kwargs)
    
    def info(self, message: str, *args, **kwargs):
        """Info logging (standard behavior, no framework tracking)."""
        if args:
            try:
                formatted_message = message % args
            except (TypeError, ValueError):
                formatted_message = f"{message} {args}"
        else:
            formatted_message = message
        
        self.original_logger.info(formatted_message, **kwargs)
    
    def debug(self, message: str, *args, **kwargs):
        """Debug logging (standard behavior, no framework tracking)."""
        if args:
            try:
                formatted_message = message % args
            except (TypeError, ValueError):
                formatted_message = f"{message} {args}"
        else:
            formatted_message = message
        
        self.original_logger.debug(formatted_message, **kwargs)
    
    def critical(self, message: str, *args, **kwargs):
        """Critical logging with automatic framework tracking."""
        # Same as error but with CRITICAL prefix
        if args:
            try:
                formatted_message = message % args
            except (TypeError, ValueError):
                formatted_message = f"{message} {args}"
        else:
            formatted_message = message
        
        location = self._get_caller_location()
        details = kwargs.pop('extra', {}) if 'extra' in kwargs else {}
        
        try:
            error_type = self._generate_error_type(formatted_message, prefix="CRITICAL")
            _log_error_to_jsonl(
                module_id=self.module_id,
                code=error_type,
                message=formatted_message,
                details=details if details else None,
                location=location
            )
        except Exception:
            pass
        
        self.original_logger.critical(formatted_message, **kwargs)
    
    def _generate_error_type(self, message: str, prefix: str = None) -> str:
        """Generate error type from message using simple heuristics."""
        # Convert message to uppercase and extract key words
        upper_msg = message.upper()
        
        # Common error patterns
        if 'CONNECT' in upper_msg or 'CONNECTION' in upper_msg:
            error_type = 'CONNECTION_ERROR'
        elif 'DATABASE' in upper_msg or 'DB' in upper_msg:
            error_type = 'DATABASE_ERROR'
        elif 'FILE' in upper_msg and ('NOT FOUND' in upper_msg or 'MISSING' in upper_msg):
            error_type = 'FILE_NOT_FOUND'
        elif 'PERMISSION' in upper_msg or 'ACCESS' in upper_msg:
            error_type = 'ACCESS_ERROR'
        elif 'TIMEOUT' in upper_msg:
            error_type = 'TIMEOUT_ERROR'
        elif 'INVALID' in upper_msg:
            error_type = 'INVALID_INPUT'
        elif 'FAILED' in upper_msg:
            error_type = 'OPERATION_FAILED'
        else:
            # Generic error type
            words = upper_msg.replace('[^A-Z0-9 ]', '').split()[:3]  # First 3 significant words
            error_type = '_'.join(word for word in words if len(word) > 2)[:50]  # Limit length
            
            if not error_type:
                error_type = 'GENERAL_ERROR'
        
        # Add prefix if provided
        if prefix:
            error_type = f"{prefix}_{error_type}"
        
        return error_type
    
    def _should_track_warning(self, message: str) -> bool:
        """Determine if a warning should be tracked by framework."""
        upper_msg = message.upper()
        
        # Track warnings that indicate potential problems
        track_patterns = [
            'FAILED', 'ERROR', 'TIMEOUT', 'CONNECTION', 'DATABASE',
            'MISSING', 'NOT FOUND', 'INVALID', 'DEPRECATED',
            'SECURITY', 'PERMISSION', 'ACCESS'
        ]
        
        return any(pattern in upper_msg for pattern in track_patterns)
    
    # Delegate all other logging methods to original logger
    def __getattr__(self, name):
        """Delegate any other methods to the original logger."""
        return getattr(self.original_logger, name)


def get_framework_logger(name: str) -> FrameworkLogger:
    """
    Get a framework-aware logger instance.
    
    This function provides the standard interface that LLMs expect:
    
    Usage:
        logger = get_framework_logger(__name__)
        logger.error("Something went wrong")  # Automatically tracked
        logger.info("Processing data...")     # Standard logging
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        FrameworkLogger instance that provides standard interface + framework integration
    """
    return FrameworkLogger(name)


def patch_stdlib_logging():
    """
    Monkey-patch standard library logging to use framework tracking.
    
    This makes ALL logging in the application framework-aware without
    requiring code changes. LLMs can use standard patterns and they
    will automatically work with framework tracking.
    
    Call this early in application startup.
    """
    # Store original getLogger
    original_getLogger = logging.getLogger
    
    def framework_aware_getLogger(name=None):
        """Replacement getLogger that returns framework-aware loggers."""
        # Get the original logger
        original_logger = original_getLogger(name)
        
        # Wrap with framework logger for application modules
        if name and (name.startswith('modules.') or 
                    any(name.startswith(prefix) for prefix in ['core.', 'standard.', 'custom.'])):
            return FrameworkLogger(name, original_logger)
        
        # Return original logger for system/library modules
        return original_logger
    
    # Replace the function
    logging.getLogger = framework_aware_getLogger


def unpatch_stdlib_logging():
    """
    Remove monkey-patch from standard library logging.
    
    Useful for testing or if patching causes issues.
    """
    # Restore original function if we have it
    if hasattr(logging, '_original_getLogger'):
        logging.getLogger = logging._original_getLogger
        delattr(logging, '_original_getLogger')


# Framework integration helper
def setup_framework_logging():
    """
    Setup framework-aware logging system.
    
    Call this during application initialization to enable automatic
    framework error tracking for all logging.
    """
    # Store original before patching
    if not hasattr(logging, '_original_getLogger'):
        logging._original_getLogger = logging.getLogger
    
    # Apply monkey-patch
    patch_stdlib_logging()
    
    # Log that framework logging is active
    logger = get_framework_logger('core.logging')
    logger.info("Framework-aware logging system activated")
"""
ui/utils/security.py
Security-related utility functions.
"""

import logging

logger = logging.getLogger("ui.utils.security")

def redact_connection_url(url):
    """
    Redact sensitive information from connection URLs.
    
    Args:
        url: Connection URL (database, API, etc.)
        
    Returns:
        Redacted URL with username and password removed
    """
    if not url:
        return "<empty url>"
        
    try:
        # Parse the URL
        if "://" in url:
            protocol, rest = url.split("://", 1)
            
            # Handle URL with authentication
            if "@" in rest:
                # Remove everything before the @ symbol (username:password)
                auth_part, server_part = rest.split("@", 1)
                
                # Replace credentials with asterisks
                return f"{protocol}://***:***@{server_part}"
            else:
                # URL without authentication
                return url
        return url
    except Exception as e:
        logger.error(f"Error redacting URL: {str(e)}")
        # If parsing fails, return a generic message
        return "<connection string>"

def safe_log_connection(url, logger_instance=None):
    """
    Safely log a connection URL without exposing credentials.
    
    Args:
        url: Connection URL
        logger_instance: Optional logger instance
    """
    safe_url = redact_connection_url(url)
    message = f"Connection: {safe_url}"
    
    if logger_instance:
        logger_instance.info(message)
    else:
        logger.info(message)

def mask_sensitive_data(data, fields_to_mask=None):
    """
    Mask sensitive fields in data structures.
    
    Args:
        data: Dictionary or similar structure containing data
        fields_to_mask: List of field names to mask
        
    Returns:
        Copy of data with sensitive fields masked
    """
    if not data or not fields_to_mask:
        return data
        
    if not isinstance(data, dict):
        return data
        
    # Create a copy to avoid modifying the original
    masked_data = data.copy()
    
    # Default fields to mask if none provided
    default_fields = ['password', 'api_key', 'secret', 'token', 'credentials']
    fields = fields_to_mask or default_fields
    
    # Mask specified fields
    for field in fields:
        if field in masked_data and masked_data[field]:
            masked_data[field] = '********'
    
    return masked_data
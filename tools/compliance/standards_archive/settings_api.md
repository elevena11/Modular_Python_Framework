# Settings API v2 Standard

**Version: 2.0.1**
**Updated: March 19, 2025**

## Purpose

This standard defines how modules should implement, register, and access settings in the Modular AI Framework. It ensures consistent settings management across all modules, enabling centralized configuration, validation, and UI-driven settings management.

## Rationale

1. **Centralized Management**: Enables all module settings to be managed through a single interface
2. **Type Safety**: Ensures settings are validated before use, preventing runtime errors
3. **Self-Documentation**: UI metadata provides built-in documentation for each setting
4. **Consistency**: Creates a uniform experience for developers implementing settings
5. **Version Tracking**: Provides automatic migration and compatibility between versions

## Requirements

### Essential Components
- **module_settings.py file**: Contains all settings-related definitions
- **DEFAULT_SETTINGS dictionary**: Default values for all module settings
- **VALIDATION_SCHEMA dictionary**: Type and constraint definitions for each setting
- **UI_METADATA dictionary**: Display information for the centralized settings UI
- **register_settings function**: Registers settings with the application context
- **Version tracking via manifest.json**: No explicit version parameter in settings registration

## Implementation Guide

### 1. Create module_settings.py

```python
"""
modules/[type]/[module_name]/module_settings.py
Configuration settings for the module.
"""

import logging
from typing import Dict, Any

logger = logging.getLogger("modular.[module_name].settings")

# Default settings configuration
DEFAULT_SETTINGS = {
    "feature_enabled": True,
    "timeout": 30,
    "max_retries": 3
}

# Validation schema
VALIDATION_SCHEMA = {
    "feature_enabled": {
        "type": "bool",
        "description": "Enable the feature"
    },
    "timeout": {
        "type": "int",
        "min": 1,
        "max": 300,
        "description": "Timeout in seconds"
    },
    "max_retries": {
        "type": "int",
        "min": 0,
        "max": 10,
        "description": "Maximum number of retry attempts"
    }
}

# UI metadata
UI_METADATA = {
    "feature_enabled": {
        "display_name": "Enable Feature",
        "description": "Whether to enable this feature",
        "input_type": "checkbox",
        "category": "General"
    },
    "timeout": {
        "display_name": "Timeout",
        "description": "Maximum time to wait for operations (seconds)",
        "input_type": "number",
        "category": "Performance"
    },
    "max_retries": {
        "display_name": "Maximum Retries",
        "description": "Number of times to retry failed operations",
        "input_type": "number",
        "category": "Reliability"
    }
}

def register_settings(app_context):
    """
    Register module settings with the application context.
    
    Args:
        app_context: Application context
        
    Returns:
        True if registration successful, False otherwise
    """
    try:
        # Register with the application context
        success = app_context.register_module_settings(
            module_id="[type].[module_name]",
            default_settings=DEFAULT_SETTINGS,
            validation_schema=VALIDATION_SCHEMA,
            ui_metadata=UI_METADATA
        )
        
        if success:
            logger.info("Module settings registered successfully")
        else:
            logger.warning("Failed to register module settings")
            
        return success
        
    except Exception as e:
        logger.error(f"Error registering module settings: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False
```

### 2. Register Settings in Phase 1 Initialization

```python
def initialize(app_context):
    """Initialize the module."""
    logger.info("Initializing module")
    
    # Check if settings service exists
    settings_service = app_context.get_service("settings_service")
    if not settings_service:
        logger.warning("Settings service not available, using default settings")
    else:
        # Register module settings
        from .module_settings import register_settings
        register_settings(app_context)
    
    # Create and register service
    my_service = MyService(app_context)
    app_context.register_service("module_id.service_name", my_service)
    
    logger.info("Module initialized")
    return True
```

### 3. Access Settings in Services

```python
def _load_settings(self):
    """Load settings from the app_context."""
    try:
        # Get settings using the app_context method
        settings = self.app_context.get_module_settings("[type].[module_name]")
        
        if settings:
            self.feature_enabled = settings.get("feature_enabled", self.feature_enabled)
            self.timeout = settings.get("timeout", self.timeout)
            self.max_retries = settings.get("max_retries", self.max_retries)
            
            self.logger.info(f"Loaded settings: feature_enabled={self.feature_enabled}, timeout={self.timeout}")
        else:
            self.logger.warning("No settings found, using defaults")
    except Exception as e:
        self.logger.error(f"Error loading settings: {str(e)}")
        # Continue with defaults
```

## Validation Schema Types

The validation schema supports these data types:

```python
# Types
"type": "string"  # Text values
"type": "int"     # Integer values
"type": "float"   # Floating point values
"type": "bool"    # Boolean values
"type": "list"    # List of values
"type": "dict"    # Dictionary/object

# Constraints (examples)
# For numeric types:
"min": 0           # Minimum value
"max": 100         # Maximum value

# For strings:
"min_length": 1    # Minimum length
"max_length": 256  # Maximum length
"pattern": "^[a-z]"  # Regular expression pattern

# For lists:
"min_items": 1     # Minimum number of items
"max_items": 10    # Maximum number of items

# For enums (any type):
"enum": ["value1", "value2", "value3"]  # Allowed values
```

## UI Metadata Options

The UI metadata supports these configuration options:

```python
# Input Types
"input_type": "text"      # Text input
"input_type": "password"  # Password input
"input_type": "number"    # Numeric input
"input_type": "checkbox"  # Boolean checkbox
"input_type": "dropdown"  # Dropdown selection
"input_type": "radio"     # Radio button selection
"input_type": "slider"    # Slider for numeric range
"input_type": "textarea"  # Multi-line text input
"input_type": "code"      # Code editor
"input_type": "color"     # Color picker
"input_type": "datetime"  # Date/time selector
"input_type": "file"      # File upload

# For dropdown/radio:
"options": [
    {"value": "option1", "label": "Option 1"},
    {"value": "option2", "label": "Option 2"},
]

# For slider:
"min": 0          # Minimum value
"max": 100        # Maximum value
"step": 5         # Step size

# For organization:
"category": "General"     # Group settings by category
"order": 10               # Control display order
"conditions": {           # Conditional display
    "feature_enabled": true
}
```

## Common Issues and Solutions

### Common Issues

1. **Missing UI Metadata**: Settings present in DEFAULT_SETTINGS but not in UI_METADATA
2. **Validation Mismatch**: Validation schema doesn't match default values
3. **Explicit Version Parameter**: Using the deprecated version parameter
4. **Old MODULE_SETTINGS Pattern**: Using deprecated MODULE_SETTINGS dictionary pattern
5. **Missing Registration Call**: No call to register_module_settings in initialization

### Solutions

1. **Complete UI Metadata**: Ensure every setting has UI metadata for the settings UI
2. **Validate Types**: Ensure validation schema matches your default values
3. **Use Manifest Version**: Remove any explicit version parameter and rely on manifest.json version
4. **Use New Pattern**: Follow the current pattern with separate dictionaries
5. **Register in Phase 1**: Call register_settings during module initialization

## Validation

This standard validates:
- Existence of module_settings.py file
- Presence of DEFAULT_SETTINGS dictionary
- Presence of VALIDATION_SCHEMA dictionary
- Presence of UI_METADATA dictionary
- Registration call in initialization
- Absence of explicit version parameter
- Absence of old MODULE_SETTINGS pattern

## FAQ

**Q: When should I access settings in my module?**
A: During initialization you should only register settings. Access them when your service or components are created, not during app startup.

**Q: How do I handle settings that depend on other modules?**
A: Register default settings in Phase 1, but access them during Phase 2 initialization when all other modules are guaranteed to be registered.

**Q: Can I programmatically update settings?**
A: Yes, use `app_context.update_module_setting(module_id, key, value)` to update settings programmatically.

**Q: How do I handle settings that don't make sense in the UI?**
A: Include them in DEFAULT_SETTINGS and VALIDATION_SCHEMA, but you can omit them from UI_METADATA if they shouldn't be user-configurable.

**Q: What happens when my manifest version changes?**
A: The system will detect the version change and apply basic evolution to keep existing values for matching keys.

**Q: How can I make a setting depend on another setting?**
A: Use the "conditions" property in UI_METADATA to show/hide settings based on others.
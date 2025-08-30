# Module Settings Developer Guide

## Overview

This guide explains how to implement the settings pattern in your modules. It covers registering settings, validation, UI metadata, and versioning.

## Recommended File Structure

For better organization and maintainability, implement settings in a dedicated file:

```
modules/[type]/[module_name]/
  ├── api.py              # API endpoints for the module
  ├── services.py         # Core services and business logic
  ├── manifest.json       # Module definition and metadata
  ├── module_settings.py  # Settings definitions and registration
  ├── models.py           # (Optional) Database models
  └── ...
```

## Basic Implementation

### Step 1: Create module_settings.py

```python
"""
Settings definitions for your module.
"""

# Default settings
DEFAULT_SETTINGS = {
    "setting_1": "default_value",
    "setting_2": 100,
    # More settings...
}

# Validation schema (optional but recommended)
VALIDATION_SCHEMA = {
    "setting_1": {
        "type": "string",
        "description": "Description of setting_1"
    },
    "setting_2": {
        "type": "int",
        "min": 0,
        "max": 1000,
        "description": "Description of setting_2"
    },
    # More validation rules...
}

# UI metadata (optional but recommended)
UI_METADATA = {
    "setting_1": {
        "display_name": "Setting One",
        "description": "User-friendly description",
        "input_type": "text",
        "category": "General",
        "order": 10
    },
    "setting_2": {
        "display_name": "Setting Two",
        "description": "User-friendly description",
        "input_type": "number",
        "category": "Performance",
        "order": 20
    },
    # More UI metadata...
}

def register_settings(app_context):
    """Register module settings with the app context."""
    return app_context.register_module_settings(
        module_id="module.id",
        default_settings=DEFAULT_SETTINGS,
        validation_schema=VALIDATION_SCHEMA,
        ui_metadata=UI_METADATA
        # No version parameter - pulled automatically from manifest.json
    )
```

### Step 2: Register settings in api.py

```python
def initialize(app_context):
    # Register module settings
    from .module_settings import register_settings
    register_settings(app_context)
    
    # Get settings with all overrides applied
    settings = app_context.get_module_settings("module.id")
    
    # Rest of initialization with settings...
```

### Step 3: Use settings in your code

```python
def process_request(self, data):
    # Get settings with all overrides applied
    settings = self.app_context.get_module_settings("core.my_module")
    
    # Use settings directly - they're guaranteed to exist
    api_url = settings["api_url"]
    max_retries = settings["max_retries"]
    
    # Process with settings...
```

## Versioning and Manifest.json

The settings system now uses your module's `manifest.json` version as the source of truth:

```json
{
  "id": "my_module",
  "name": "My Module",
  "version": "1.0.4",  // This is used for settings version
  "description": "..."
}
```

When you update your module:

1. Always update the version in manifest.json
2. The settings system will automatically detect the new version
3. Existing settings will be preserved while new settings are added

## Validation Schema Reference

### Common Fields

- `type`: Data type (`string`, `int`, `float`, `bool`, `list`, `dict`)
- `description`: Description of the setting
- Type-specific validation rules

### String Validation

```python
"setting_name": {
    "type": "string",
    "min_length": 1,           # Minimum string length
    "max_length": 100,         # Maximum string length
    "pattern": "^[a-zA-Z0-9]+$", # Regex pattern
    "enum": ["option1", "option2"] # Allowed values
}
```

### Numeric Validation

```python
"setting_name": {
    "type": "int",  # or "float"
    "min": 0,       # Minimum value
    "max": 100      # Maximum value
}
```

### Boolean Validation

```python
"setting_name": {
    "type": "bool"  # True or False
}
```

### List Validation

```python
"setting_name": {
    "type": "list",
    "min_items": 1,     # Minimum items
    "max_items": 10,    # Maximum items
    "items": {          # Schema for list items
        "type": "string",
        "min_length": 1
    }
}
```

## UI Metadata Reference

### Common Fields

- `display_name`: User-friendly name for the setting
- `description`: Help text explaining the setting
- `category`: Grouping category for organizing settings
- `order`: Display order within category (lower numbers first)
- `input_type`: Type of control to display

### Input Types and Specific Fields

#### Text Input

```python
"setting_name": {
    "input_type": "text",
    "placeholder": "Enter value..."  # Placeholder text
}
```

#### Number Input

```python
"setting_name": {
    "input_type": "number",
    "min": 0,          # Minimum value
    "max": 100,        # Maximum value
    "step": 1          # Increment step
}
```

#### Slider

```python
"setting_name": {
    "input_type": "slider",
    "min": 0,          # Minimum value
    "max": 100,        # Maximum value
    "step": 1          # Increment step
}
```

#### Checkbox

```python
"setting_name": {
    "input_type": "checkbox"
}
```

#### Dropdown

```python
"setting_name": {
    "input_type": "dropdown",
    "options": [
        {"value": "option1", "label": "Option 1"},
        {"value": "option2", "label": "Option 2"}
    ]
}
```

## Settings Evolution

When your module's settings schema changes, follow these guidelines:

### Adding New Settings

Simply add the new settings to your DEFAULT_SETTINGS dictionary. The system will automatically add them to existing configurations.

```python
# Before
DEFAULT_SETTINGS = {
    "timeout": 30
}

# After
DEFAULT_SETTINGS = {
    "timeout": 30,
    "retry_count": 3  # New setting
}
```

### Removing Settings

Remove settings from your DEFAULT_SETTINGS dictionary. They'll remain in existing configurations but won't be used.

### Renaming Settings

If you need to rename a setting, add both the old and new names to the validation schema with the same type, then gradually phase out the old name in a future version.

### Changing Types

Avoid changing the type of existing settings. If needed, create a new setting with the new type and keep the old one for backward compatibility.

## Best Practices

1. **Use Descriptive Names**: Settings should be self-explanatory
2. **Add Validation**: Validate all settings to prevent misconfigurations
3. **Provide UI Metadata**: Help users understand and configure your module
4. **Keep Default Values Sensible**: Choose safe default values
5. **Group Related Settings**: Use categories to organize settings
6. **Document Each Setting**: Add descriptions for all settings
7. **Update Manifest Version**: Always update your manifest.json version when changing settings
8. **Avoid Complex Migrations**: Keep settings evolution simple when possible

## Core API Methods

### Registering Settings

```python
app_context.register_module_settings(
    module_id="module.id",
    default_settings={
        "setting_key": "default_value",
        # More settings...
    },
    validation_schema=VALIDATION_SCHEMA,  # Optional
    ui_metadata=UI_METADATA  # Optional
)
```

### Getting Settings

```python
settings = app_context.get_module_settings("module.id")
```

### Updating Settings

```python
# Update in client config (user override)
app_context.update_module_setting(
    module_id="module.id",
    key="setting_key",
    value="new_value",
    use_client_config=True  # Default
)

# Update in settings.json (change default)
app_context.update_module_setting(
    module_id="module.id",
    key="setting_key",
    value="new_value",
    use_client_config=False
)
```

### Resetting Settings

```python
app_context.reset_module_setting("module.id", "setting_key")
```

## Removed Features

### Migration System

The previous complex migration system has been removed for simplicity. The settings system now:

- Preserves existing settings when a module is updated
- Adds new settings with default values
- Uses manifest.json for version tracking
- Logs warnings about potentially incompatible settings during downgrades

### Explicit Version Parameters

Do not use explicit version parameters in your settings registration:

```python
# DON'T DO THIS
app_context.register_module_settings(
    module_id="module.id",
    default_settings=DEFAULT_SETTINGS,
    version="1.0.0"  # Don't include this!
)
```

Instead, update your manifest.json version.

## Future Plans

Future enhancements to the settings system may include:

- Simple field renaming support
- Type conversion for compatible changes
- User-friendly migration warnings
- Settings backup and restore

For now, focus on keeping your settings evolution straightforward and making small, incremental changes between versions.

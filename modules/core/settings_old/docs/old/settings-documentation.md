# Module Settings Registration Pattern

## Overview

The Modular AI Framework provides a standardized approach to module settings management that simplifies configuration handling. This pattern allows modules to register their default settings during initialization, ensuring settings are discoverable, centralized, and automatically documented.

## Why Use This Pattern?

- **Self-Documenting**: The settings.json file becomes a complete reference of all available settings
- **Simplified Code**: No need for constant null checks or fallbacks throughout your code
- **Hierarchical Overrides**: Clear precedence of environment variables → client overrides → defaults
- **Automatic UI Integration**: Registered settings can be automatically exposed in the UI
- **Centralized Management**: All settings are stored in consistent locations

## How It Works

### Settings Hierarchy (Highest to Lowest Priority)

1. **Environment Variables**: `MODULE_ID_SETTING_NAME` format (e.g., `CORE_DATABASE_PORT=5432`)
2. **Client Config**: User-specific overrides in `data/client_config.json`
3. **Settings File**: Module-registered defaults in `data/settings.json`

## Recommended File Structure

For better organization and maintainability, settings should be defined in a dedicated file:

```
modules/[type]/[module_name]/
  ├── api.py              # API endpoints for the module
  ├── services.py         # Core services and business logic
  ├── manifest.json       # Module definition and metadata
  ├── module_settings.py  # Settings definitions and registration
  ├── models.py           # (Optional) Database models
  └── ...
```

### Example `module_settings.py`

```python
"""
Settings definitions for the module.
Centralizes all settings-related code in one place.
"""

# Default settings
DEFAULT_SETTINGS = {
    "setting_1": "default_value",
    "setting_2": 100,
    # More settings...
}

# Validation schema
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

# UI metadata
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

# Settings version for migration tracking
SETTINGS_VERSION = "1.0.0"

def register_settings(app_context):
    """Register module settings with the app context."""
    return app_context.register_module_settings(
        module_id="module.id",
        default_settings=DEFAULT_SETTINGS,
        validation_schema=VALIDATION_SCHEMA,
        ui_metadata=UI_METADATA,
        version=SETTINGS_VERSION
    )
```

### Using in `api.py`

```python
def initialize(app_context):
    # Register module settings
    from .module_settings import register_settings
    register_settings(app_context)
    
    # Get settings with all overrides applied
    settings = app_context.get_module_settings("module.id")
    
    # Rest of initialization with settings...
```

## Benefits of Dedicated Settings Files

1. **Improved Maintainability**: All settings in one place makes them easier to find and update
2. **Better Separation of Concerns**: Keeps configuration separate from implementation
3. **Easier Discoverability**: Developers can quickly understand available settings
4. **Simplified Updating**: Version management and migrations in one location
5. **Consistent Pattern**: Creates a uniform approach across all modules

### Implementation Pattern

During module initialization (Phase 1), each module should register its default settings:

```python
def initialize(app_context):
    # Register default settings using the dedicated file
    from .module_settings import register_settings
    register_settings(app_context)
    
    # Rest of initialization...
```

Then, when settings are needed, they can be accessed without null checks:

```python
def process_request(self, data):
    # Get settings with all overrides applied
    settings = self.app_context.get_module_settings("core.my_module")
    
    # Use settings directly - they're guaranteed to exist
    api_url = settings["api_url"]
    max_retries = settings["max_retries"]
    
    # Process with settings...
```

## Core Methods

### Registering Settings

```python
app_context.register_module_settings(
    module_id="module.id",
    default_settings={
        "setting_key": "default_value",
        # More settings...
    }
)
```

- If the module settings don't exist in `settings.json`, they will be added
- If some settings exist but others are missing, only missing settings will be added
- Existing settings are preserved to maintain user customizations

### Getting Settings

```python
settings = app_context.get_module_settings("module.id")
```

Returns a dictionary with all settings for the module, with overrides applied according to the hierarchy.

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

Removes any override in client config, reverting to the default value.

## Best Practices

1. **Use Dedicated Settings Files**: Create a module_settings.py for all settings-related code
2. **Register Early**: Always register settings during Phase 1 initialization
3. **Be Comprehensive**: Include all possible settings with sensible defaults
4. **Use Descriptive Names**: Settings should be self-explanatory
5. **Type Consistency**: Maintain consistent types for settings (string, int, bool, etc.)
6. **Documentation**: Document each setting's purpose and accepted values
7. **Validation**: Add validation for all settings to prevent misconfigurations
8. **Categorization**: Group related settings with categories in UI metadata

## Environment Variable Overrides

Environment variables can override any setting using the format:

```
MODULE_ID_SETTING_NAME=value
```

For example, to override the `port` setting in the `core.database` module:

```
CORE_DATABASE_PORT=5432
```

Type conversion is automatically handled based on the default value's type.

## UI Integration

Registered settings can be automatically exposed in the UI for easy configuration. The UI can use the settings service to retrieve and update settings.

Module developers don't need to create custom UI components for settings - they can be automatically generated based on registered settings.
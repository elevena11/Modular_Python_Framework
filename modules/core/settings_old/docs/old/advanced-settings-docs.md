# Advanced Settings Management

The Modular AI Framework provides a sophisticated settings management system that extends beyond basic storage and retrieval. This document covers the advanced features of the settings system including validation, UI metadata, and settings migration.

## Core Features

### 1. Settings Validation

Ensures settings conform to expected types, ranges, and patterns, preventing configuration errors that could cause runtime issues.

### 2. UI Metadata

Provides additional information for automatically generating UI controls, creating a rich, intuitive settings interface.

### 3. Settings Migration

Handles changes to settings schemas between versions, ensuring smooth upgrades without breaking existing configurations.

## Using Advanced Settings Features

### Basic Registration with All Features

```python
app_context.register_module_settings(
    module_id="module.id",
    default_settings={
        "api_url": "http://localhost:3000",
        "max_retries": 3,
        "theme": "light"
    },
    validation_schema={
        "api_url": {
            "type": "string",
            "pattern": "^https?://.*$"
        },
        "max_retries": {
            "type": "int",
            "min": 0,
            "max": 10
        },
        "theme": {
            "type": "string",
            "enum": ["light", "dark", "system"]
        }
    },
    ui_metadata={
        "api_url": {
            "display_name": "API URL",
            "input_type": "text",
            "category": "API Settings"
        },
        "max_retries": {
            "display_name": "Maximum Retries",
            "input_type": "slider",
            "category": "API Settings"
        },
        "theme": {
            "display_name": "UI Theme",
            "input_type": "dropdown",
            "options": [
                {"value": "light", "label": "Light"},
                {"value": "dark", "label": "Dark"},
                {"value": "system", "label": "System Default"}
            ],
            "category": "Appearance"
        }
    },
    version="1.0.0"
)
```

### Handling Settings Migrations

```python
# Register migration function
app_context.register_settings_migration(
    module_id="module.id",
    from_version="1.0.0",
    to_version="2.0.0",
    migration_function=lambda old_settings: {
        # Transform old settings to new format
        **old_settings,
        "new_setting": "default_value"
    }
)

# Later, register with the new version
app_context.register_module_settings(
    module_id="module.id",
    default_settings={
        # Updated settings structure...
    },
    version="2.0.0"  # New version
)
```

## Validation Schema Reference

### Common Fields

These fields apply to all types:

- `type`: Data type (`string`, `int`, `float`, `bool`, `list`, `dict`)
- `description`: Description of the setting (for documentation)

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

### Dict Validation

```python
"setting_name": {
    "type": "dict",
    "properties": {     # Schema for dict properties
        "key1": {
            "type": "string"
        },
        "key2": {
            "type": "int"
        }
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

#### Password Input

```python
"setting_name": {
    "input_type": "password",
    "placeholder": "Enter password..."
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

#### Radio Buttons

```python
"setting_name": {
    "input_type": "radio",
    "options": [
        {"value": "option1", "label": "Option 1"},
        {"value": "option2", "label": "Option 2"}
    ]
}
```

#### Text Area

```python
"setting_name": {
    "input_type": "textarea",
    "rows": 5,         # Number of visible rows
    "placeholder": "Enter text..."
}
```

#### Color Picker

```python
"setting_name": {
    "input_type": "color",
    "default": "#ffffff"
}
```

## Settings Migration Guide

### When to Use Migrations

Use migrations when:
- Renaming settings keys
- Changing data types
- Splitting or combining settings
- Adding or removing settings
- Changing default values

### Migration Function Requirements

A migration function:
- Takes the old settings dictionary as input
- Returns a new dictionary with the transformed settings
- Handles missing keys gracefully
- Preserves values not affected by the migration

### Example Migration Scenarios

#### Renaming a Setting

```python
def migrate_v1_to_v2(old_settings):
    new_settings = old_settings.copy()
    
    # Rename 'api_timeout' to 'timeout'
    if 'api_timeout' in old_settings:
        new_settings['timeout'] = old_settings['api_timeout']
        del new_settings['api_timeout']
    
    return new_settings
```

#### Changing Data Types

```python
def migrate_v1_to_v2(old_settings):
    new_settings = old_settings.copy()
    
    # Convert string representation to boolean
    if 'enable_feature' in old_settings:
        if isinstance(old_settings['enable_feature'], str):
            new_settings['enable_feature'] = old_settings['enable_feature'].lower() in ['true', 'yes', '1']
    
    return new_settings
```

#### Splitting a Setting

```python
def migrate_v1_to_v2(old_settings):
    new_settings = old_settings.copy()
    
    # Split 'server_address' into 'host' and 'port'
    if 'server_address' in old_settings:
        try:
            parts = old_settings['server_address'].split(':')
            new_settings['host'] = parts[0]
            new_settings['port'] = int(parts[1]) if len(parts) > 1 else 80
            del new_settings['server_address']
        except Exception:
            # Fallback to defaults if parsing fails
            new_settings['host'] = 'localhost'
            new_settings['port'] = 80
    
    return new_settings
```

## Best Practices

### 1. Validation

- Provide validation for all settings, especially those with format requirements
- Use appropriate type constraints to catch errors early
- Include descriptive error messages
- Test validation with both valid and invalid values

### 2. UI Metadata

- Group related settings with categories
- Use appropriate input types for the data
- Provide helpful descriptions
- Set logical ordering within categories
- Use consistent naming conventions

### 3. Migrations

- Always increment version numbers when changing settings structure
- Write migration functions for each version transition
- Test migrations with real-world configuration data
- Handle missing or invalid settings gracefully
- Document all schema changes

### 4. General

- Keep settings focused on configuration, not state
- Use descriptive setting names
- Document the purpose of each setting
- Provide sensible defaults
- Consider making complex features optional via feature flags

## Implementation Details

The advanced settings system is implemented with:

1. A `SettingsService` class that handles storage, retrieval, validation, and migration
2. Extensions to `AppContext` that expose these features to modules
3. Storage in three files:
   - `settings.json`: Default settings values
   - `client_config.json`: User overrides
   - `settings_metadata.json`: Validation schemas and UI metadata

## Caveats and Limitations

- Validation happens at registration and update time, not at runtime
- Complex validation logic may require custom validator functions
- UI metadata only works with supported input types
- Migrations run sequentially by version number
- No support for partial migration rollbacks

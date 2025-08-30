# Settings Versioning System

## Overview

The Modular AI Framework settings system now includes robust version handling that integrates with the module versioning system. This guide explains how settings versioning works and best practices for implementing it in your modules.

## Key Features

- **Automatic Version Detection**: Settings version is now automatically derived from your module's `manifest.json` version
- **Upgrade Path**: When a module is upgraded, settings are automatically migrated using registered migrations
- **Downgrade Path**: When a module is downgraded, settings are preserved or migrated based on available migrations
- **Versioned Settings Schema**: Each module's settings schema is tracked with its corresponding version

## How It Works

### Registration

When a module registers its settings:

```python
app_context.register_module_settings(
    module_id="core.database",
    default_settings={...},
    validation_schema={...},
    ui_metadata={...}
    # Version is no longer needed - pulled from manifest.json
)
```

The system will:

1. Read the module's version from `manifest.json`
2. Compare it to the stored settings version for that module
3. Apply migrations if needed
4. Update the settings with any new keys from the current version
5. Save the new version number with the settings

### Versioning Logic

The settings system handles various versioning scenarios:

#### 1. New Module Installation
- Settings are registered with the current module version
- Default values are stored in settings.json

#### 2. Module Upgrade (e.g., v1.0.0 → v1.1.0)
- Checks for registered migrations from old to new version
- Applies migrations if available
- Adds any new settings with default values
- Updates settings version to new module version

#### 3. Module Downgrade (e.g., v1.1.0 → v1.0.0)
- Checks for registered downgrade migrations
- If available, applies downgrade migrations
- If not available, preserves settings but logs a warning
- Updates settings version to current module version

## Migration Registration

To handle version transitions, register migration functions:

```python
app_context.register_settings_migration(
    module_id="core.database",
    from_version="1.0.0",
    to_version="1.1.0",
    migration_function=lambda old_settings: {
        # Transform old settings to new format
        **old_settings,
        "new_setting": "default_value"
    }
)
```

## Best Practices

### 1. Keep Manifest Version Updated

Always update your module's version in `manifest.json` when changing settings:

```json
{
  "id": "database",
  "name": "Database Module",
  "version": "1.1.0",  // Increment this!
  ...
}
```

### 2. Register Migrations

When changing settings structure, register migrations between versions:

```python
def initialize(app_context):
    # Register migrations before registering settings
    app_context.register_settings_migration(
        module_id="my.module",
        from_version="1.0.0",
        to_version="1.1.0",
        migration_function=upgrade_v1_to_v11
    )
    
    # Also register reverse migrations when possible
    app_context.register_settings_migration(
        module_id="my.module",
        from_version="1.1.0",
        to_version="1.0.0",
        migration_function=downgrade_v11_to_v1
    )
    
    # Then register settings (uses current manifest version)
    app_context.register_module_settings(
        module_id="my.module",
        default_settings=MY_SETTINGS
    )
```

### 3. Create Clean Migration Functions

Write migration functions that:

- Don't modify the input dictionary (create a new one)
- Handle missing keys gracefully
- Preserve unaffected settings
- Document the changes they make

```python
def upgrade_v1_to_v11(old_settings):
    """
    Upgrade settings from v1.0.0 to v1.1.0.
    
    Changes:
    - Renamed 'timeout_ms' to 'timeout' (converted to seconds)
    - Added new 'retry_policy' setting
    """
    new_settings = old_settings.copy()
    
    # Handle renamed/transformed setting
    if 'timeout_ms' in old_settings:
        new_settings['timeout'] = old_settings['timeout_ms'] / 1000
        del new_settings['timeout_ms']
    
    # Add new settings
    if 'retry_policy' not in new_settings:
        new_settings['retry_policy'] = 'exponential'
    
    return new_settings
```

### 4. Test Both Upgrade and Downgrade Paths

Create unit tests that verify:
- Settings upgrade correctly from previous versions
- Settings downgrade correctly when available
- Migration functions handle edge cases properly

## Examples

### Example 1: Simple Settings Evolution

Module v1.0.0:
```python
DEFAULT_SETTINGS = {
    "api_url": "http://localhost:8000",
    "timeout": 30
}
```

Module v1.1.0:
```python
DEFAULT_SETTINGS = {
    "api_url": "http://localhost:8000",
    "timeout": 30,
    "max_retries": 3  # New setting
}

def initialize(app_context):
    # No migration needed for simple addition
    app_context.register_module_settings(
        module_id="my.module",
        default_settings=DEFAULT_SETTINGS
    )
```

### Example 2: Complex Settings Evolution

Module v1.0.0:
```python
DEFAULT_SETTINGS = {
    "connection_string": "sqlite:///data.db",
    "pool_size": 5
}
```

Module v2.0.0:
```python
DEFAULT_SETTINGS = {
    "database": {  # Restructured settings
        "url": "sqlite:///data.db",
        "pool": {
            "size": 5,
            "timeout": 30
        }
    }
}

def initialize(app_context):
    # Register upgrade migration
    app_context.register_settings_migration(
        module_id="my.module",
        from_version="1.0.0",
        to_version="2.0.0",
        migration_function=upgrade_v1_to_v2
    )
    
    # Register downgrade migration
    app_context.register_settings_migration(
        module_id="my.module",
        from_version="2.0.0",
        to_version="1.0.0",
        migration_function=downgrade_v2_to_v1
    )
    
    # Register settings
    app_context.register_module_settings(
        module_id="my.module",
        default_settings=DEFAULT_SETTINGS
    )

def upgrade_v1_to_v2(old_settings):
    """Transform flat settings to nested structure."""
    return {
        "database": {
            "url": old_settings.get("connection_string", "sqlite:///data.db"),
            "pool": {
                "size": old_settings.get("pool_size", 5),
                "timeout": 30  # New setting with default
            }
        }
    }

def downgrade_v2_to_v1(new_settings):
    """Transform nested settings back to flat structure."""
    db = new_settings.get("database", {})
    pool = db.get("pool", {})
    
    return {
        "connection_string": db.get("url", "sqlite:///data.db"),
        "pool_size": pool.get("size", 5)
    }
```

## Troubleshooting

### Settings Not Migrating

If settings aren't migrating properly:

1. Check that module versions are correctly incremented in `manifest.json`
2. Verify migration functions are registered *before* calling `register_module_settings`
3. Confirm migration functions handle all required transformations
4. Check logs for errors during migration

### Handling Missing Migrations

If downgrade migrations are missing:

1. Settings will be preserved as-is but with the older version number
2. A warning will be logged to alert users of potential compatibility issues
3. New settings that didn't exist in the older version will remain but may not be used

## API Reference

### `register_module_settings`

```python
app_context.register_module_settings(
    module_id: str,               # Module identifier
    default_settings: Dict,       # Default settings values
    validation_schema: Dict = None, # Optional validation rules
    ui_metadata: Dict = None,     # Optional UI display metadata
    version: str = None           # Optional explicit version (uses manifest.json if None)
)
```

### `register_settings_migration`

```python
app_context.register_settings_migration(
    module_id: str,               # Module identifier
    from_version: str,            # Source version
    to_version: str,              # Target version
    migration_function: Callable  # Function to transform settings
)
```

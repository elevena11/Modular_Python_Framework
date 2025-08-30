# Settings Module

**Version: 1.1.0**  
**Updated: April 5, 2025**

## Overview

The Settings module provides centralized configuration management for the framework. It handles loading, saving, validating, and tracking changes to configuration settings across all modules.

## Key Features

- **Hierarchical Settings**: Environment variables > Client config > Default settings
- **Validation**: Type checking and constraint validation for settings
- **Backup & Restoration**: Automated backups with restoration capability
- **Change Tracking**: History of setting changes for auditing
- **UI Metadata**: Support for automatic UI controls generation

## Module Structure

The settings module follows a modular architecture with clear separation of concerns:

```
modules/core/settings/
├── api.py                  # API endpoints and initialization
├── services.py             # Main service composition and organization
├── api_schemas.py          # API request/response schemas
├── module_settings.py      # Module's own settings
├── services/               # Core service components
│   ├── core_service.py     # Main settings operations
│   ├── validation_service.py # Validation logic
│   └── env_service.py      # Environment variable handling
├── storage/                # Storage implementations
│   ├── file_storage.py     # File-based operations
│   └── db_storage.py       # Database operations
├── backup/                 # Backup components
│   └── backup_service.py   # Backup management
├── models/                 # Database models
│   └── db_models.py        # Database models
└── utils/                  # Shared utilities
    └── error_helpers.py    # Error handling utilities
```

## Usage

### Getting Settings

```python
# Get all settings for a module
settings = await app_context.get_module_settings("module.id")

# Get a specific setting with overrides applied
value = await settings_service.get_setting("module.id", "setting_name")
```

### Updating Settings

```python
# Update a setting (client config by default)
result = await settings_service.update_module_setting(
    "module.id", "setting_name", "new_value"
)

# Reset a setting to default value
result = await settings_service.reset_module_setting(
    "module.id", "setting_name"
)
```

### Module Registration

```python
# Register a module's settings
success = await settings_service.register_module_settings(
    module_id="my.module",
    default_settings={
        "setting1": "default_value",
        "setting2": 42
    },
    validation_schema={
        "setting1": {"type": "string", "min_length": 3},
        "setting2": {"type": "int", "min": 0, "max": 100}
    },
    ui_metadata={
        "setting1": {
            "display_name": "Setting One",
            "description": "Description for setting one",
            "input_type": "text"
        }
    }
)
```

### Backup and Restore

```python
# Create a backup
result = await settings_service.backup_service.create_backup(
    settings_data,
    description="Manual backup"
)

# Restore from backup
result = await settings_service.backup_service.restore_backup(
    backup_id=42
)
```

## Settings Hierarchy

Settings are resolved with the following priority:

1. **Environment Variables**: `MODULE_ID_SETTING_NAME`
2. **Client Configuration**: User-specific overrides
3. **Default Settings**: Module-defined defaults

## API Endpoints

- `GET /settings/` - Get all settings
- `GET /settings/metadata` - Get validation and UI metadata
- `GET /settings/{module_id}/{setting_name}` - Get specific setting
- `PUT /settings/{module_id}/{setting_name}` - Update setting

## Environment Variables

- `CORE_SETTINGS_AUTO_BACKUP_ENABLED`: Enable/disable automatic backups
- `CORE_SETTINGS_BACKUP_FREQUENCY_DAYS`: Days between backups
- `CORE_SETTINGS_BACKUP_RETENTION_COUNT`: Number of backups to keep

## Dependencies

- `core.database`: For storing backups and change history
- `core.trace_logger`: For tracing operations
- `core.error_handler`: For standardized error handling

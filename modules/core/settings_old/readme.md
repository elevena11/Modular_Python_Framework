# Settings Module

**Version: 1.0.5**  
**Updated: March 23, 2025**

## 📋 RECOMMENDED: Flat Structure with Dot Notation

**The Streamlit UI works best with flat structure using dot notation.**

✅ **RECOMMENDED**: `"database.host": "localhost"`  
⚠️ **PROBLEMATIC**: `"database": {"host": "localhost"}` (may cause UI issues)

**📖 See [SETTINGS_STRUCTURE_GUIDE.md](./SETTINGS_STRUCTURE_GUIDE.md) for complete documentation and historical context.**

## Overview

The Settings Module is a core foundation module that provides centralized settings management for all modules in the Modular AI Framework. It implements a hierarchical approach to configuration with validation, UI metadata, and migration support.

## Features

- **Hierarchical Settings**: Prioritizes environment variables, client configuration, and defaults
- **Settings Validation**: Enforces type safety and constraints with comprehensive validation
- **UI Metadata**: Provides context for settings UI generation
- **Version Tracking**: Manages settings evolution across module versions
- **Backup System**: Database-backed settings backups with scheduling and restoration
- **Asynchronous Operations**: Non-blocking file and database operations
- **TTL-based Caching**: Efficient environment variable caching

## Architecture

The Settings Module uses a component-based architecture with specialized services:

### Core Components

- **SettingsService**: Main service that composes and coordinates specialized services
- **ValidationService**: Handles validation of settings against schemas
- **StorageService**: Manages async file I/O for settings and configuration
- **EnvCacheService**: Provides TTL-based caching for environment variables
- **BackupService**: Manages database-backed settings backups

The module follows the framework's two-phase initialization pattern:

1. **Phase 1**: Registers the settings service and models with the application context
2. **Phase 2**: Bootstraps the settings service and initializes backup scheduling

## Files

- **`services.py`**: Main settings service that coordinates specialized components
- **`api.py`**: FastAPI endpoints for settings management
- **`database.py`**: Database operations for backups and history
- **`api_schemas.py`**: Pydantic models for API request/response validation
- **`db_models.py`**: SQLAlchemy models for database storage
- **`module_settings.py`**: Settings for the settings module itself (self-similar architecture)
- **`components/`**: Specialized component services
- **`ui/`**: UI components for settings management

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/settings` | GET | Get all settings |
| `/settings/metadata` | GET | Get metadata for UI generation |
| `/settings/{module_id}/{setting_name}` | GET | Get a specific setting |
| `/settings/{module_id}/{setting_name}` | PUT | Update a setting |
| `/settings/backup` | POST | Create a settings backup |
| `/settings/backups` | GET | List available backups |
| `/settings/restore/{backup_id}` | POST | Restore settings from a backup |
| `/settings/test` | GET | Test if settings module is working |
| `/settings/debug` | GET | Get debug information |

## Settings Management

The module manages settings in three layers:

1. **Environment Variables**: Highest priority, override everything
2. **Client Configuration**: User overrides stored in client_config.json
3. **Default Settings**: Defined by each module

## Usage

### Registering Module Settings

```python
def register_settings(app_context):
    success = app_context.register_module_settings(
        module_id="your.module.id",
        default_settings=DEFAULT_SETTINGS,
        validation_schema=VALIDATION_SCHEMA,
        ui_metadata=UI_METADATA
    )
    return success
```

### Accessing Settings

```python
# In async context
settings = await app_context.get_module_settings("your.module.id")
feature_enabled = settings.get("feature_enabled", False)

# In sync context (compatibility wrapper)
settings = app_context.get_module_settings("your.module.id")
feature_enabled = settings.get("feature_enabled", False)
```

### Updating Settings

```python
# In async context
success = await app_context.update_module_setting(
    module_id="your.module.id",
    key="setting_name",
    value=new_value
)

# In sync context (compatibility wrapper)
success = app_context.update_module_setting(
    module_id="your.module.id",
    key="setting_name",
    value=new_value
)
```

### Creating Backups

```python
# Create a manual backup
backup_id = await settings_service.create_backup(
    description="Pre-deployment backup"
)
```

### Restoring from Backups

```python
# Restore from a backup
success = await settings_service.restore_backup(backup_id)
```

## Backup Features

The module provides comprehensive backup capabilities:

- **Automatic Backups**: Scheduled backups with configurable frequency
- **Manual Backups**: On-demand backups through API
- **Version Backups**: Automatic backups when module versions change
- **Backup Rotation**: Automatic cleanup of old backups
- **Backup History**: Tracking of all backup operations
- **Settings History**: Change history for individual settings

## Best Practices

1. Always define a validation schema for your settings
2. Provide helpful UI metadata for better user experience
3. Use reasonable defaults for all settings
4. Keep settings simple and focused on configuration
5. Organize settings in logical categories for the UI
6. Use await with settings operations in async contexts
7. Set up automatic backups for critical settings

## Implementation Details

- **Async File I/O**: Uses aiofiles for non-blocking file operations
- **TTL-based Caching**: Environment variables are cached with configurable TTL
- **Database Integration**: Uses SQLAlchemy models and execute_with_retry pattern
- **Validation**: Comprehensive validation with type conversion where appropriate
- **Performance Optimization**: Yield points in long operations to prevent blocking

# Settings Module Analysis - Configuration Management

## Overview

The core.settings module provides hierarchical configuration management with environment variable overrides, validation, and automatic UI generation support.

**Location**: `modules/core/settings/`

## Architecture

### Service Composition Pattern
The settings module uses a composition pattern with specialized services:

- **CoreSettingsService**: Main orchestrator 
- **ValidationService**: Schema validation
- **EnvironmentService**: Environment variable handling
- **FileStorageService**: JSON file operations
- **DatabaseStorageService**: Database backup operations
- **BackupService**: Automatic backup management

### Configuration Hierarchy
Settings are resolved in priority order:

1. **Environment Variables** (highest priority)
   - Format: `{MODULE_ID}_{SETTING_NAME}` (uppercase)
   - Example: `CORE_DATABASE_AUTO_BACKUP_ENABLED=true`

2. **Client Configuration** (user overrides)
   - File: `data/client_config.json`
   - User-specific customizations

3. **Settings.json** (module defaults, lowest priority)
   - File: `data/settings.json`
   - Module-registered default settings

## Module Integration Pattern

### 1. Settings Registration (Phase 1)
```python
# In module's initialize() function
async def initialize(app_context):
    # Define default settings
    default_settings = {
        "api_rate_limit": 60,
        "retry_attempts": 3,
        "data_retention_days": 30,
        "enable_feature": True
    }
    
    # Optional validation schema
    validation_schema = {
        "api_rate_limit": {"type": "integer", "minimum": 1, "maximum": 1000},
        "retry_attempts": {"type": "integer", "minimum": 1, "maximum": 10},
        "data_retention_days": {"type": "integer", "minimum": 1},
        "enable_feature": {"type": "boolean"}
    }
    
    # Optional UI metadata for Streamlit dashboard
    ui_metadata = {
        "api_rate_limit": {
            "label": "API Rate Limit (requests/minute)",
            "description": "Maximum API requests per minute",
            "widget": "slider",
            "min": 1,
            "max": 1000
        },
        "enable_feature": {
            "label": "Enable Feature",
            "description": "Enable or disable this feature"
        }
    }
    
    # Register settings (happens in Phase 1, before settings service fully initialized)
    await app_context.register_module_settings(
        "standard.example_module",
        default_settings,
        validation_schema,
        ui_metadata
    )
```

### 2. Settings Access (Phase 2 and Runtime)
```python
# In module's Phase 2 initialization or runtime
async def setup_module():
    # Get settings with all overrides applied
    settings = await app_context.get_module_settings("standard.example_module")
    
    # Use settings
    rate_limit = settings.get("api_rate_limit", 60)
    retry_attempts = settings.get("retry_attempts", 3)
    retention_days = settings.get("data_retention_days", 30)
    feature_enabled = settings.get("enable_feature", True)
```

### 3. Runtime Settings Updates
```python
# Update a setting programmatically
await app_context.update_module_setting(
    "standard.example_module",
    "api_rate_limit", 
    120,
    use_client_config=True  # Store in client_config.json
)

# Reset to default
await app_context.reset_module_setting(
    "standard.example_module",
    "api_rate_limit"
)
```

## Environment Variable Override Pattern

### Example Module Settings
```bash
# Override example_module settings
export STANDARD_EXAMPLE_MODULE_API_RATE_LIMIT=120
export STANDARD_EXAMPLE_MODULE_ENABLE_FEATURE=false

# Override another_module settings  
export STANDARD_ANOTHER_MODULE_THRESHOLD=0.8
export STANDARD_ANOTHER_MODULE_INTERVAL=300

# Override core module settings
export CORE_DATABASE_AUTO_BACKUP_ENABLED=true
```

### Environment Variable Conversion
- **Boolean**: `"true"`, `"1"`, `"yes"` → `True`
- **Integer**: `"120"` → `120`  
- **Float**: `"0.75"` → `0.75`
- **String**: Used as-is

## File Structure

### 1. Settings Files
```
data/
├── settings.json          # All module default settings
├── client_config.json     # User override settings  
├── settings_metadata.json # Validation schemas and UI metadata
└── settings_backups/      # Automatic backups
```

### 2. Settings.json Structure
```json
{
  "standard.example_module": {
    "api_rate_limit": 60,
    "retry_attempts": 3,
    "data_retention_days": 30,
    "enable_feature": true
  },
  "standard.another_module": {
    "threshold": 0.7,
    "interval": 300,
    "max_events_per_hour": 10
  },
  "_versions": {
    "standard.example_module": "1.0.0",
    "standard.another_module": "1.0.0"
  }
}
```

### 3. Client Config Override Example
```json
{
  "standard.example_module": {
    "api_rate_limit": 120,
    "enable_feature": false
  }
}
```

## Advanced Features

### 1. Settings Validation
- JSON Schema validation on registration and updates
- Type checking and constraint validation
- Automatic error reporting for invalid settings

### 2. Settings Evolution
- Version tracking via manifest.json
- Automatic migration between settings schema versions
- Missing key detection and auto-addition

### 3. Backup System
- Automatic periodic backups to database
- Settings change tracking and audit trail
- Restoration capabilities

### 4. UI Integration
- Automatic Streamlit UI generation from metadata
- Widget type specification (slider, checkbox, text)
- Help text and validation messages

## Service Access Pattern

### Getting Settings Service
```python
# Access the settings service
settings_service = app_context.get_service("core.settings.service")

# Direct method calls (if service available)
settings = await settings_service.get_module_settings("module_id")

# Via app_context convenience methods (recommended)
settings = await app_context.get_module_settings("module_id")
```


## Key Benefits

### For Framework
- ✅ Centralized configuration management
- ✅ Environment-based deployment configuration
- ✅ Automatic validation and error handling
- ✅ UI generation capabilities

### For Application Modules
- ✅ Easy configuration without hardcoding
- ✅ Environment variable override for production
- ✅ User customization through client config
- ✅ Automatic backup and versioning

This settings system provides robust, hierarchical configuration management for any application built on the framework.
# Settings Module

The Settings Module (`modules/core/settings/`) provides centralized configuration management for the framework and all modules. It implements a hierarchical settings system with environment variable support, validation, UI metadata, and backup functionality.

## Overview

The Settings Module is a core framework component that manages all application configuration. It provides:

- **Hierarchical Configuration**: Environment variables → Client config → Default settings
- **Validation System**: Schema-based validation with type checking
- **UI Metadata**: Automatic UI generation for settings management
- **Backup & Restoration**: Database-backed settings backups
- **Environment Integration**: Environment variable override support
- **Module Integration**: Seamless integration with all framework modules

## Key Features

### 1. Hierarchical Settings Resolution
- **Environment Variables**: Highest priority (e.g., `CORE_DATABASE_MAX_RETRIES=10`)
- **Client Configuration**: User overrides stored in `client_config.json`
- **Default Settings**: Module defaults stored in `settings.json`
- **Automatic Merging**: Intelligent merging of all configuration sources

### 2. Validation System
- **Schema-Based**: JSON schema validation for all settings
- **Type Checking**: Automatic type conversion and validation
- **Error Handling**: Detailed validation error messages
- **Optional Validation**: Can be disabled for performance

### 3. UI Metadata
- **Automatic UI Generation**: Metadata for creating settings interfaces
- **Field Descriptions**: Human-readable descriptions for each setting
- **Input Types**: Specify appropriate input types (text, number, boolean, etc.)
- **Validation Rules**: Client-side validation rules

### 4. Backup & Restoration
- **Database-Backed**: Settings backups stored in database
- **Version Tracking**: Track settings changes over time
- **Restore Points**: Restore to any previous configuration
- **Automatic Backups**: Configurable automatic backup schedules

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Settings Module                          │
├─────────────────────────────────────────────────────────────┤
│ Settings Resolution (Hierarchical)                         │
│ ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐ │
│ │ Environment     │ │ Client Config   │ │ Default         │ │
│ │ Variables       │ │ (client_config  │ │ Settings        │ │
│ │ (highest)       │ │ .json)          │ │ (settings.json) │ │
│ └─────────────────┘ └─────────────────┘ └─────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│ Core Services                                               │
│ ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐ │
│ │ Core Settings   │ │ Validation      │ │ Environment     │ │
│ │ Service         │ │ Service         │ │ Service         │ │
│ └─────────────────┘ └─────────────────┘ └─────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│ Storage Services                                            │
│ ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐ │
│ │ File Storage    │ │ Database        │ │ Backup          │ │
│ │ Service         │ │ Storage         │ │ Service         │ │
│ └─────────────────┘ └─────────────────┘ └─────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## Settings Resolution Process

### 1. Hierarchical Resolution
```python
# Settings resolution order (highest to lowest priority)
1. Environment Variables: CORE_DATABASE_MAX_RETRIES=10
2. Client Configuration: client_config.json
3. Module Defaults: settings.json
4. Schema Defaults: From validation schema
```

### 2. Environment Variable Format
```python
# Format: MODULE_SETTING_NAME=value
CORE_DATABASE_MAX_RETRIES=10
CORE_SETTINGS_BACKUP_ENABLED=true
STANDARD_MY_MODULE_TIMEOUT=30

# Converted to:
{
    "core.database": {"max_retries": 10},
    "core.settings": {"backup_enabled": true},
    "standard.my_module": {"timeout": 30}
}
```

### 3. Settings Merging
```python
# Final settings = env_vars + client_config + defaults
def resolve_settings(module_id):
    defaults = load_default_settings(module_id)
    client_overrides = load_client_config(module_id)
    env_overrides = load_env_variables(module_id)
    
    # Merge with priority: env > client > defaults
    return merge_settings(defaults, client_overrides, env_overrides)
```

## Module Settings Registration

### 1. Module Settings Schema
```python
# In module's module_settings.py
MODULE_SETTINGS = {
    "setting_name": {
        "type": "int",
        "default": 30,
        "description": "Timeout in seconds",
        "validation": {"min": 1, "max": 300},
        "ui_metadata": {
            "label": "Timeout",
            "input_type": "number",
            "category": "Performance"
        }
    }
}

async def register_settings(app_context):
    await app_context.register_module_settings(
        "my_module",
        MODULE_SETTINGS
    )
```

### 2. Settings Registration Process
```python
# During module initialization
async def initialize(app_context):
    # Register module settings
    from .module_settings import register_settings
    await register_settings(app_context)
    
    # Settings are now available
    settings = await app_context.get_module_settings("my_module")
```

### 3. Settings Usage in Modules
```python
class MyModuleService:
    async def initialize(self):
        # Get module settings
        settings = await self.app_context.get_module_settings("my_module")
        
        # Use settings
        self.timeout = settings.get("timeout", 30)
        self.max_retries = settings.get("max_retries", 3)
```

## Validation System

### 1. Schema Definition
```python
# Validation schema for settings
VALIDATION_SCHEMA = {
    "timeout": {
        "type": "int",
        "min": 1,
        "max": 300,
        "required": True
    },
    "enabled": {
        "type": "bool",
        "default": True
    },
    "levels": {
        "type": "list",
        "items": {"type": "str"},
        "allowed": ["DEBUG", "INFO", "WARNING", "ERROR"]
    }
}
```

### 2. Validation Process
```python
class ValidationService:
    async def validate_setting(self, module_id, key, value, schema):
        """Validate a single setting value."""
        try:
            # Type validation
            validated_value = self.validate_type(value, schema["type"])
            
            # Range validation
            if "min" in schema and validated_value < schema["min"]:
                raise ValidationError(f"Value {value} below minimum {schema['min']}")
            
            # Custom validation
            if "validator" in schema:
                schema["validator"](validated_value)
            
            return Result.success(data=validated_value)
        except Exception as e:
            return Result.error(
                code="VALIDATION_ERROR",
                message=f"Validation failed: {str(e)}"
            )
```

### 3. Type Conversion
```python
# Automatic type conversion
def convert_value(value, target_type):
    if target_type == "int":
        return int(value)
    elif target_type == "bool":
        return str(value).lower() in ("true", "1", "yes", "on")
    elif target_type == "float":
        return float(value)
    elif target_type == "list":
        return value.split(",") if isinstance(value, str) else value
    return value
```

## Storage Services

### 1. File Storage
```python
class FileStorageService:
    async def save_settings(self, settings_data):
        """Save settings to settings.json file."""
        
    async def load_settings(self):
        """Load settings from settings.json file."""
        
    async def save_client_config(self, client_config):
        """Save client overrides to client_config.json."""
        
    async def load_client_config(self):
        """Load client overrides from client_config.json."""
```

### 2. Database Storage
```python
class DatabaseStorageService:
    async def save_settings_backup(self, settings_data, description=None):
        """Save settings backup to database."""
        
    async def load_settings_backup(self, backup_id):
        """Load settings from a specific backup."""
        
    async def list_backups(self):
        """List all available backups."""
```

### 3. Backup Service
```python
class BackupService:
    async def create_backup(self, description=None):
        """Create a new settings backup."""
        
    async def restore_backup(self, backup_id):
        """Restore settings from a backup."""
        
    async def schedule_automatic_backup(self, interval_hours=24):
        """Schedule automatic backups."""
```

## API Endpoints

### 1. Settings Management
```python
# Get all settings
GET /api/v1/settings
Response: {
    "success": true,
    "settings": {
        "core.database": {"max_retries": 5},
        "core.settings": {"backup_enabled": true}
    }
}

# Get module settings
GET /api/v1/settings/core.database
Response: {
    "success": true,
    "module_id": "core.database",
    "settings": {"max_retries": 5, "timeout": 30}
}

# Update setting
PUT /api/v1/settings/core.database/max_retries
Request: {"value": 10}
Response: {"success": true}
```

### 2. Backup Management
```python
# Create backup
POST /api/v1/settings/backups
Request: {"description": "Before update"}
Response: {
    "success": true,
    "backup_id": 123,
    "created_at": "2025-07-16T10:30:00Z"
}

# List backups
GET /api/v1/settings/backups
Response: {
    "success": true,
    "backups": [
        {
            "id": 123,
            "created_at": "2025-07-16T10:30:00Z",
            "description": "Before update"
        }
    ]
}

# Restore backup
POST /api/v1/settings/backups/123/restore
Response: {"success": true}
```

### 3. Validation
```python
# Validate setting
POST /api/v1/settings/core.database/max_retries/validate
Request: {"value": 10}
Response: {
    "success": true,
    "valid": true,
    "converted_value": 10
}

# Get validation metadata
GET /api/v1/settings/core.database/metadata
Response: {
    "success": true,
    "metadata": {
        "max_retries": {
            "type": "int",
            "min": 1,
            "max": 100,
            "description": "Maximum retry attempts"
        }
    }
}
```

## Environment Integration

### 1. Environment Variable Loading
```python
class EnvironmentService:
    def load_environment_overrides(self):
        """Load settings from environment variables."""
        overrides = {}
        
        for key, value in os.environ.items():
            if self.is_settings_variable(key):
                module_id, setting_name = self.parse_env_key(key)
                overrides.setdefault(module_id, {})[setting_name] = value
        
        return overrides
    
    def is_settings_variable(self, key):
        """Check if environment variable is a settings override."""
        # Format: MODULE_SETTING_NAME
        return "_" in key and key.isupper()
```

### 2. Environment Variable Format
```bash
# Framework core modules
CORE_DATABASE_MAX_RETRIES=10
CORE_SETTINGS_BACKUP_ENABLED=true

# Standard modules
STANDARD_MY_MODULE_TIMEOUT=30
STANDARD_MY_MODULE_ENABLED=false

# Extensions
EXTENSIONS_PLUGIN_NAME_SETTING=value
```

## Database Models

### 1. Settings Backup Model
```python
class SettingsBackup(FrameworkBase):
    __tablename__ = "settings_backups"
    
    id = Column(Integer, primary_key=True)
    date_created = Column(DateTime, default=func.now())
    version = Column(String(50), nullable=False)
    settings_data = Column(SQLiteJSON, nullable=False)
    description = Column(Text, nullable=True)
```

### 2. Settings Event Model
```python
class SettingsEvent(FrameworkBase):
    __tablename__ = "settings_events"
    
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=func.now())
    module_id = Column(String(100), nullable=False)
    setting_key = Column(String(100), nullable=False)
    old_value = Column(SQLiteJSON, nullable=True)
    new_value = Column(SQLiteJSON, nullable=True)
    source = Column(String(50), nullable=False)  # 'api', 'env', 'backup'
```

## Configuration Examples

### 1. Module Settings Definition
```python
# module_settings.py
MODULE_SETTINGS = {
    "timeout": {
        "type": "int",
        "default": 30,
        "description": "Request timeout in seconds",
        "validation": {"min": 1, "max": 300},
        "ui_metadata": {
            "label": "Timeout",
            "input_type": "number",
            "category": "Performance",
            "help_text": "Maximum time to wait for requests"
        }
    },
    "enabled": {
        "type": "bool",
        "default": True,
        "description": "Enable the module",
        "ui_metadata": {
            "label": "Enable Module",
            "input_type": "checkbox",
            "category": "General"
        }
    },
    "log_level": {
        "type": "str",
        "default": "INFO",
        "description": "Logging level",
        "validation": {
            "allowed": ["DEBUG", "INFO", "WARNING", "ERROR"]
        },
        "ui_metadata": {
            "label": "Log Level",
            "input_type": "select",
            "options": ["DEBUG", "INFO", "WARNING", "ERROR"],
            "category": "Logging"
        }
    }
}
```

### 2. Settings File Structure
```json
// settings.json
{
    "core.database": {
        "max_retries": 5,
        "timeout": 30,
        "pool_size": 20
    },
    "core.settings": {
        "backup_enabled": true,
        "backup_interval": 24,
        "validation_enabled": true
    },
    "standard.my_module": {
        "timeout": 30,
        "enabled": true,
        "log_level": "INFO"
    }
}
```

### 3. Client Configuration
```json
// client_config.json (user overrides)
{
    "core.database": {
        "max_retries": 10  // Override default value
    },
    "standard.my_module": {
        "timeout": 60,     // Override default value
        "log_level": "DEBUG"
    }
}
```

## Best Practices

### 1. Settings Definition
```python
# ✅ CORRECT: Complete settings definition
MODULE_SETTINGS = {
    "timeout": {
        "type": "int",
        "default": 30,
        "description": "Clear description",
        "validation": {"min": 1, "max": 300},
        "ui_metadata": {
            "label": "Timeout",
            "input_type": "number",
            "category": "Performance"
        }
    }
}

# ❌ WRONG: Incomplete definition
MODULE_SETTINGS = {
    "timeout": 30  # Missing type, description, validation
}
```

### 2. Settings Access
```python
# ✅ CORRECT: Async settings access
settings = await app_context.get_module_settings("my_module")
timeout = settings.get("timeout", 30)

# ❌ WRONG: Direct file access
import json
with open("settings.json", "r") as f:
    settings = json.load(f)
```

### 3. Environment Variables
```python
# ✅ CORRECT: Standard format
CORE_DATABASE_MAX_RETRIES=10
STANDARD_MY_MODULE_TIMEOUT=30

# ❌ WRONG: Non-standard format
database_max_retries=10
MY_MODULE_TIMEOUT=30
```

### 4. Validation
```python
# ✅ CORRECT: Comprehensive validation
"validation": {
    "min": 1,
    "max": 300,
    "required": True,
    "validator": lambda x: x % 5 == 0  # Custom validation
}

# ❌ WRONG: No validation
"validation": {}  # Missing validation rules
```

## Error Handling

### 1. Validation Errors
```python
class ValidationError(Exception):
    def __init__(self, message, field=None, value=None):
        self.message = message
        self.field = field
        self.value = value
        super().__init__(message)

# Usage
try:
    await settings_service.update_setting("module", "key", "invalid_value")
except ValidationError as e:
    print(f"Validation failed for {e.field}: {e.message}")
```

### 2. Storage Errors
```python
# File storage errors
result = await file_storage.save_settings(settings)
if not result.success:
    logger.error(f"Failed to save settings: {result.error['message']}")

# Database errors
result = await db_storage.create_backup(settings)
if not result.success:
    logger.error(f"Backup failed: {result.error['message']}")
```

## Performance Considerations

### 1. Settings Caching
```python
class SettingsService:
    def __init__(self):
        self._settings_cache = {}
        self._cache_timestamp = None
        
    async def get_module_settings(self, module_id):
        # Check cache first
        if self._is_cache_valid():
            return self._settings_cache.get(module_id, {})
        
        # Reload from storage
        await self._reload_settings()
        return self._settings_cache.get(module_id, {})
```

### 2. Lazy Loading
```python
# Load settings on demand
async def get_module_settings(self, module_id):
    if module_id not in self._loaded_modules:
        await self._load_module_settings(module_id)
    
    return self._resolve_settings(module_id)
```

## Related Documentation

- [Application Context](../core/app-context.md) - Settings integration with app context
- [Configuration System](../core/config-system.md) - Framework configuration
- [Database Module](database-module.md) - Settings storage in database
- [Module Creation Guide](../module-creation-guide-v2.md) - Adding settings to modules
- [Two-Phase Initialization](../patterns/two-phase-initialization.md) - Settings initialization

---

The Settings Module provides a comprehensive configuration management system that enables flexible, hierarchical settings with validation, UI integration, and backup capabilities, making it easy for modules to manage their configuration while maintaining consistency across the framework.
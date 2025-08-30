# Settings V2: Decorator-Based Architecture Design

**Status**: DESIGN PHASE - Ready for Implementation  
**Target**: Replace complex core.settings with clean decorator-based system  
**Philosophy**: Simple, declarative, follows centralized registration principles

## Problem Statement

The current `core.settings` module is overly complex with:
- 6+ service classes requiring manual composition
- Complex inheritance hierarchies 
- Multiple storage abstractions
- Scattered file path management
- Service composition patterns that fight the v3.0.0 architecture

**Result**: Hundreds of lines of complex code for what should be a simple system.

## Core Requirements

When stripped of complexity, the settings system has one simple job:

1. **Module declares defaults** → `@define_settings({"key": {"default": "value"}})`
2. **Framework stores in database** → Automatic during module loading  
3. **User can override via UI/API** → Stored as user preferences
4. **Module asks for value** → `self.settings.key` → Framework returns final value

## Settings Value Priority Hierarchy

**Priority Order (highest to lowest):**
1. **User-set value** (via UI/API) - Highest priority, explicit user intent
2. **Environment variable** (.env file) - Deployment/environment configuration
3. **Module default** (from decorator) - Developer-defined sensible defaults

## Data Flow Architecture

```
Module Defaults → Database → User Overrides → Environment Check → Final Value → Module Access
     ↓              ↓            ↓                ↓              ↓            ↓
@define_settings  SQL table   User changes    .env check    Computed   self.settings.key
```

### Value Resolution Logic

```python
def get_setting_value(module_id: str, key: str):
    # 1. Check user-set value first (highest priority)
    if user_value := get_user_override(module_id, key):
        return user_value
    
    # 2. Check environment variable (.env file)
    if env_var := get_env_var(module_id, key):
        return env_var
        
    # 3. Return module default (lowest priority)
    return get_default_value(module_id, key)
```

## Database Schema

**Simple two-table design:**

```sql
-- Default values declared by modules via @define_settings
CREATE TABLE module_defaults (
    module_id TEXT NOT NULL,
    key TEXT NOT NULL,
    default_value TEXT NOT NULL,  -- JSON encoded value
    value_type TEXT NOT NULL,     -- string, integer, boolean, float, list, dict
    description TEXT,             -- Human-readable description
    env_var TEXT,                 -- Optional environment variable name
    constraints TEXT,             -- JSON: {"min": 1, "max": 100, "choices": [...]}
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (module_id, key)
);

-- User overrides of default values
CREATE TABLE user_overrides (
    module_id TEXT NOT NULL,
    key TEXT NOT NULL,
    user_value TEXT NOT NULL,     -- JSON encoded value
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    changed_by TEXT DEFAULT 'user',  -- 'user', 'api', 'admin', etc.
    PRIMARY KEY (module_id, key),
    FOREIGN KEY (module_id, key) REFERENCES module_defaults(module_id, key)
);
```

## Decorator Design

### `@define_settings()` Decorator

**Single decorator that handles all settings configuration:**

```python
@define_settings({
    "setting_name": {
        "default": "default_value",
        "type": "string",               # string, integer, boolean, float, list, dict
        "description": "Human description",
        "env_var": "ENV_VAR_NAME",     # Optional environment variable
        "constraints": {               # Optional validation constraints
            "min": 1,                  # For numbers
            "max": 100,                # For numbers  
            "choices": ["a", "b", "c"], # For enums
            "pattern": "^[a-z]+$"       # For string regex
        }
    }
})
class MyModule(DataIntegrityModule):
    # Settings automatically available as self.settings
```

### Supported Types and Constraints (LLM-Friendly)

**Type Flexibility - Multiple Accepted Formats:**
- **Strings**: `"string"`, `"str"`, `"text"` → All resolve to `string`
- **Integers**: `"integer"`, `"int"`, `"number"` → All resolve to `integer`  
- **Booleans**: `"boolean"`, `"bool"`, `"flag"` → All resolve to `boolean`
- **Floats**: `"float"`, `"decimal"`, `"real"` → All resolve to `float`
- **Lists**: `"list"`, `"array"`, `"sequence"` → All resolve to `list`
- **Objects**: `"dict"`, `"object"`, `"map"` → All resolve to `dict`

**Smart Type Detection:**
- If type is omitted, auto-detect from default value
- Invalid types default to `string` with warning
- Graceful handling of malformed JSON in decorator

**Constraints (optional):**
- `min`/`max` or `minimum`/`maximum` - Numeric ranges
- `choices` or `options` or `enum` - Enumerated options  
- `pattern` or `regex` - String regex validation
- `required` or `mandatory` - Cannot be None/empty

**Nested Settings Support:**
- Use dot notation: `"database.host"`, `"api.retry.max_attempts"`
- Automatic nested object creation
- Deep merge for complex configurations

## Usage Examples

### Simple Settings (LLM-Friendly Examples)

```python
@define_settings({
    "debug_mode": {
        "default": False,
        "type": "bool",  # Also accepts "boolean", "flag"
        "description": "Enable debug logging",
        "env_var": "DEBUG"
    },
    "api_timeout": {
        "default": 30,
        "type": "int",  # Also accepts "integer", "number"  
        "description": "API timeout in seconds",
        "min": 1, "max": 300  # Also accepts "minimum"/"maximum"
    },
    # Type auto-detection from default value
    "service_name": {
        "default": "my-service",  # Auto-detected as string
        "description": "Service identifier"
    }
})
class MyModule(DataIntegrityModule):
    
    def make_request(self):
        timeout = self.settings.api_timeout  # Could be: user_override OR env_var OR 30
        debug = self.settings.debug_mode     # Could be: user_override OR DEBUG env var OR False
        name = self.settings.service_name    # Auto-detected string type
```

### Complex Settings with Nested Support

```python
@define_settings({
    # Nested settings with dot notation
    "database.host": {
        "default": "localhost",
        "type": "str",  # Flexible type naming
        "description": "Database host"
    },
    "database.port": {
        "default": 5432,
        "type": "int",
        "min": 1, "max": 65535
    },
    "database.ssl": {
        "default": True,
        "type": "bool"
    },
    
    # List settings
    "allowed_origins": {
        "default": ["http://localhost:3000"],
        "type": "array",  # Alternative to "list"
        "description": "CORS allowed origins"
    },
    
    # Enum with multiple choice formats
    "log_level": {
        "default": "INFO",
        "type": "string", 
        "description": "Logging level",
        "env_var": "LOG_LEVEL",
        "choices": ["DEBUG", "INFO", "WARNING", "ERROR"]  # or "options" or "enum"
    }
})
class WebModule(DataIntegrityModule):
    
    def setup_database(self):
        # Access nested settings naturally
        host = self.settings.database.host     # Auto-created nested object
        port = self.settings.database.port
        ssl = self.settings.database.ssl
        
    def setup_cors(self):
        origins = self.settings.allowed_origins
        for origin in origins:
            self.add_cors_origin(origin)
```

### Error-Tolerant Usage Examples

```python
# LLM might write inconsistent JSON - Settings V2 handles gracefully:

@define_settings({
    "retry_count": {
        "default": 3,
        # Missing type - auto-detected as integer from default
        "description": "Number of retries"
    },
    "timeout": {
        "default": "30",  # String default
        "type": "integer",  # But specified as int - auto-converts
        "description": "Timeout in seconds"
    },
    "enabled": {
        "default": True,
        "type": "boolean",  # LLM used "boolean" instead of "bool" - works fine
        "description": "Feature enabled"
    }
})
class RobustModule(DataIntegrityModule):
    pass
```

## Implementation Architecture

### Core Components

1. **Settings Decorator** (`@define_settings`) - Declarative settings definition with LLM-friendly parsing
2. **Settings Processor** - Registers settings during module loading with type normalization
3. **Settings Storage** - Database operations for defaults and overrides
4. **Settings Access** - `self.settings.key` property access with nested object support
5. **Settings Validation** - Robust validation engine with error tolerance
6. **Settings Versioning** - Module version tracking and migration support  
7. **Settings UI Generator** - Automatic UI generation from schema definitions
8. **Settings API** - REST endpoints for UI integration

### Module Integration

**Automatic Integration with Module Loading:**
```python
# ModuleProcessor automatically handles settings registration
INFO - core.module_processor - my_module: Registered 5 settings definitions
INFO - core.module_processor - my_module: Settings available via self.settings
```

**Zero Boilerplate Access:**
```python
class MyService:
    def __init__(self, module_context):
        self.settings = module_context.settings  # Automatically injected
    
    def do_work(self):
        batch_size = self.settings.batch_size  # Direct access, no service lookup
```

## API Design

**REST endpoints for settings management:**

```
GET    /api/v1/settings/                    # List all modules and their settings
GET    /api/v1/settings/{module_id}         # Get settings for specific module
PUT    /api/v1/settings/{module_id}/{key}   # Update specific setting value
DELETE /api/v1/settings/{module_id}/{key}   # Reset setting to default
GET    /api/v1/settings/{module_id}/schema  # Get setting definitions and constraints
```

## Advanced Features

### 🛡️ Settings Validation Engine

**LLM-Friendly Type System:**
```python
# Type aliases and normalization
TYPE_ALIASES = {
    # String variants
    "string": "string", "str": "string", "text": "string",
    # Integer variants  
    "integer": "integer", "int": "integer", "number": "integer",
    # Boolean variants
    "boolean": "boolean", "bool": "boolean", "flag": "boolean",
    # Float variants
    "float": "float", "decimal": "float", "real": "float",
    # List variants
    "list": "list", "array": "list", "sequence": "list",
    # Dict variants
    "dict": "dict", "object": "dict", "map": "dict"
}
```

**Auto-Type Detection:**
```python
def detect_type_from_default(value):
    """Automatically detect type from default value when type is missing."""
    if isinstance(value, bool): return "boolean"
    if isinstance(value, int): return "integer" 
    if isinstance(value, float): return "float"
    if isinstance(value, list): return "list"
    if isinstance(value, dict): return "dict"
    return "string"  # Safe default
```

**Graceful Type Conversion & Soft Warnings:**
```python
@define_settings({
    "timeout": {
        "default": "30",        # String default
        "type": "int",          # Soft warning: "Converting 'int' → 'integer'"
        "description": "API timeout"
    },
    "retry_count": {
        "default": 3,
        "type": "invalid_type",  # Soft warning: "Unknown type, using auto-detected 'integer'"
        "description": "Number of retries"
    },
    "debug_flag": {
        "default": True,
        # Missing type - Soft warning: "Auto-detected type 'boolean' from default"
        "description": "Enable debug mode"
    }
})

# Logs generated (all INFO level with "fix when convenient" hints):
# INFO - settings_v2 - my_module: Type alias 'int' → 'integer' for setting 'timeout' (consider updating to 'integer')
# INFO - settings_v2 - my_module: Invalid type 'invalid_type' for 'retry_count', auto-detected 'integer' from default (fix type when convenient)
# INFO - settings_v2 - my_module: Auto-detected type 'boolean' for setting 'debug_flag' (consider adding explicit type)
# INFO - settings_v2 - my_module: All 3 settings registered successfully
```

### 🏗️ Nested Settings Support

**Dot Notation Processing:**
```python
# Input: "database.connection.host" 
# Creates: {"database": {"connection": {"host": "localhost"}}}

def create_nested_structure(settings_dict):
    result = {}
    for key, config in settings_dict.items():
        if '.' in key:
            parts = key.split('.')
            current = result
            for part in parts[:-1]:
                if part not in current:
                    current[part] = {}
                current = current[part]
            current[parts[-1]] = config
        else:
            result[key] = config
    return result
```

**Natural Access Patterns:**
```python
# Access nested settings as objects
config = self.settings.database.connection.host
# Or traditional bracket notation  
config = self.settings["database.connection.host"]
```

### 📦 Settings Versioning System

**Module Version Tracking:**
```sql
-- Enhanced database schema with versioning
CREATE TABLE module_settings_versions (
    module_id TEXT NOT NULL,
    version TEXT NOT NULL,
    settings_schema TEXT NOT NULL,  -- JSON schema
    migration_script TEXT,          -- Optional migration logic
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (module_id, version)
);
```

**Version Migration Support:**
```python
@define_settings({
    "new_setting": {
        "default": "default_value",
        "type": "string",
        "version_added": "1.2.0"  # Track when setting was added
    },
    "deprecated_setting": {
        "default": "old_value", 
        "type": "string",
        "deprecated": "1.3.0",     # Mark as deprecated
        "replacement": "new_setting"  # Suggest replacement
    }
}, version="1.3.0")  # Module version
class VersionedModule(DataIntegrityModule):
    pass
```

### 🎨 Automatic UI Generation

**Schema-Driven UI Components:**
```python
def generate_ui_component(setting_key, setting_config):
    """Generate appropriate UI component based on setting type and constraints."""
    
    if setting_config["type"] == "boolean":
        return {"component": "checkbox", "label": setting_config["description"]}
    
    elif setting_config["type"] == "string":
        if "choices" in setting_config:
            return {"component": "select", "options": setting_config["choices"]}
        elif "pattern" in setting_config:
            return {"component": "text_input", "validation": setting_config["pattern"]}
        else:
            return {"component": "text_input"}
    
    elif setting_config["type"] in ["integer", "float"]:
        return {
            "component": "number_input",
            "min": setting_config.get("min"),
            "max": setting_config.get("max")
        }
```

**Automatic Category Organization:**
```python
# Nested settings automatically create UI categories
# "database.host" and "database.port" → "Database" category
# "api.timeout" and "api.retries" → "API" category
```

### 🔄 Soft Warning Philosophy

**All type conversions, normalizations, and auto-corrections generate INFO-level logs, never errors:**

```python
# Logging approach for maximum LLM friendliness
class SettingsProcessor:
    def process_setting(self, key, config):
        # Type alias conversion
        if config.get("type") in ["str", "int", "bool"]:
            standard = self.normalize_type(config["type"])
            logger.info(f"Type alias '{config['type']}' → '{standard}' for {key} (consider updating to '{standard}')")
        
        # Auto-type detection  
        if "type" not in config:
            detected = self.detect_type_from_default(config["default"])
            logger.info(f"Auto-detected type '{detected}' for setting '{key}' (consider adding explicit type)")
            
        # Invalid type recovery
        if config.get("type") not in VALID_TYPES:
            detected = self.detect_type_from_default(config["default"])
            logger.info(f"Unknown type '{config['type']}' for '{key}', using '{detected}' (fix type when convenient)")
            
        # Never log.warning() or log.error() for these cases
        # LLM can scan INFO logs when convenient, system keeps running
```

**Benefits of Soft Warning Approach:**
- **No False Alarms**: INFO logs don't suggest actual problems
- **Gentle Nudging**: "fix when convenient" hints encourage gradual improvement
- **LLM Scan Friendly**: Easy to filter and review type conversions
- **Development Flow**: LLM works iteratively without emergency stops
- **Operational Clarity**: Real errors stand out from normal conversions
- **Non-Blocking Awareness**: LLM knows about conversions but isn't forced to fix them

## Benefits of V2 Architecture

### Developer Experience
- **Zero Boilerplate**: `self.settings.key` instead of service composition
- **Declarative**: Settings defined right with the module using decorators
- **LLM-Friendly**: Flexible type naming, auto-detection, graceful error handling
- **IntelliSense**: IDE can autocomplete setting names and types
- **Nested Access**: Natural object notation for complex configurations

### LLM & AI Integration
- **Soft Warnings Only**: All type conversions logged as INFO, never as errors
- **Error Tolerance**: Handles "str" vs "string", "int" vs "integer" automatically
- **Type Flexibility**: Multiple accepted formats for same type
- **Auto-Recovery**: Missing types detected from defaults, invalid types default safely
- **JSON Resilience**: Graceful handling of malformed decorator JSON
- **Non-Blocking**: System always continues running, LLM can fix issues later

### Framework Consistency  
- **Same Pattern**: Uses decorators like all other v3.0.0 features
- **centralized registration**: Settings follow same architectural principles
- **Automatic Registration**: Framework handles everything automatically
- **Version Management**: Built-in versioning and migration support

### Operational Benefits
- **Simple Storage**: Clean database schema with versioning
- **Predictable Priority**: Clear hierarchy (user → env → default)  
- **Environment Integration**: Seamless .env file support
- **Auto-Generated UI**: Automatic settings interface from schema
- **Robust Validation**: Type conversion, constraint checking, nested support

## Migration Strategy

### Parallel Implementation Approach

1. **Phase 1**: Implement `core.settings_v2` alongside existing system
2. **Phase 2**: Convert core modules to use v2 system one by one
3. **Phase 3**: Migrate all standard modules to v2
4. **Phase 4**: Remove legacy `core.settings` module entirely

### Backward Compatibility

**During Migration Period:**
- Both systems run simultaneously
- Modules can use either system
- No disruption to existing functionality
- Clear migration guide for each module

## Code Comparison

### Current System (Complex)
```python
# Settings definition
from .module_settings import register_settings, DEFAULT_SETTINGS, VALIDATION_SCHEMA

# Manual registration in initialize()
await register_settings(app_context, self.MODULE_ID, DEFAULT_SETTINGS, VALIDATION_SCHEMA)

# Complex service composition in services.py  
validation_service = ValidationService()
env_service = EnvironmentService()
file_storage = FileStorageService(self.settings_file, self.client_config_file, self.metadata_file)
db_storage = DatabaseStorageService(app_context)
backup_service = BackupService(app_context, file_storage, db_storage)

super().__init__(
    app_context=app_context,
    validation_service=validation_service,
    env_service=env_service,
    file_storage=file_storage,
    db_storage=db_storage,
    backup_service=backup_service
)

# Usage requires service lookup
settings_service = app_context.get_service("core.settings.service")
value = await settings_service.get_setting("my_module", "some_key")
```

### New System (Simple)
```python
# Everything in one decorator
@define_settings({
    "some_key": {
        "default": "default_value",
        "type": "string",
        "env_var": "MY_MODULE_KEY",
        "description": "Some configuration setting"
    }
})
class MyModule(DataIntegrityModule):
    
    def some_method(self):
        value = self.settings.some_key  # That's it!
```

**Lines of Code Comparison:**
- **Current System**: ~500+ lines across multiple files and services
- **New System**: ~50 lines total for same functionality
- **Reduction**: ~90% less code for same features

## Implementation Plan

### Step 1: Core Infrastructure
- Create `modules/core/settings_v2/` directory structure
- Implement `@define_settings` decorator
- Create database tables and models
- Build settings processor for ModuleProcessor integration

### Step 2: Access Layer
- Implement `self.settings.key` property access
- Build value resolution logic (user → env → default)
- Add type validation and constraint checking
- Create settings context injection for modules

### Step 3: API Layer  
- Build REST API endpoints for settings management
- Add settings schema endpoints for UI generation
- Implement bulk operations (import/export)
- Add audit logging for setting changes

### Step 4: Testing & Documentation
- Comprehensive test suite for all functionality
- Migration guide for existing modules  
- API documentation and examples
- Performance benchmarks vs current system

## Success Criteria

**Technical Metrics:**
- [ ] 90%+ reduction in settings-related code
- [ ] Sub-millisecond setting access time
- [ ] Zero manual service composition required
- [ ] 100% type validation coverage

**Developer Experience:**
- [ ] Single decorator defines all settings
- [ ] `self.settings.key` access pattern works
- [ ] Automatic environment variable override
- [ ] IntelliSense support for setting names

**System Integration:**
- [ ] Seamless ModuleProcessor integration
- [ ] Clean database schema with no service layers
- [ ] REST API for external setting management
- [ ] Backward compatibility during migration

This architecture represents a fundamental simplification that brings settings in line with the v3.0.0 centralized registration philosophy, eliminating complexity while providing more functionality through clean, declarative design.
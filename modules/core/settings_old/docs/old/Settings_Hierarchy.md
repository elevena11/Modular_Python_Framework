## Settings Hierarchy (Highest to Lowest Priority)

1. **Environment Variables**
   - Format: `MODULE_ID_SETTING_NAME` (e.g., `CORE_DATABASE_CONNECTION_TIMEOUT=60`)
   - Highest priority, overrides everything else
   - Useful for deployment-specific configurations

2. **Client Configuration**
   - Stored in `data/client_config.json`
   - User-specific overrides set through the UI
   - Second highest priority

3. **Settings File**
   - Stored in `data/settings.json`
   - Contains module-registered defaults
   - Lowest priority

## Registration and Storage

When a module registers settings:
```python
app_context.register_module_settings(
    module_id="core.database",
    default_settings={...},
    validation_schema={...},
    ui_metadata={...},
    version="1.0.0"
)
```

This does several things:
- Adds settings to `settings.json` if they don't exist
- Registers validation schema in `settings_metadata.json`
- Registers UI metadata in `settings_metadata.json`
- Sets up version tracking for migrations

## Retrieval and Overrides

When a module needs its settings:
```python
settings = app_context.get_module_settings("core.database")
```

The settings service:
1. Starts with defaults from `settings.json`
2. Applies overrides from `client_config.json`
3. Applies environment variable overrides
4. Returns the final combined settings

## Advanced Features

The system supports:
- **Validation**: Schema-based validation (type checking, min/max values, etc.)
- **UI Metadata**: Information for auto-generating UI controls
- **Migrations**: Version-based migrations when settings structure changes

This approach separates default values from user preferences, allows for deployment customization, and provides validation to prevent misconfigurations.
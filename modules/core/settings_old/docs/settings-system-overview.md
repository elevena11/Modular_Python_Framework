# Settings System Overview

## What Are Settings?

The Settings System in the Modular AI Framework provides a centralized way to store, retrieve, and manage configuration values for all modules. It handles everything from basic storage to validation, UI generation, and version management.

## Settings Hierarchy

Settings are processed in the following priority order (highest to lowest):

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

This hierarchy ensures deployment configurations take precedence over user preferences, which take precedence over defaults.

## How Settings Are Stored

The settings system uses multiple files:

1. **settings.json** - Contains all default settings registered by modules
   ```json
   {
     "core.database": {
       "connection_timeout": 30,
       "max_connections": 5
     },
     "standard.ai_agent": {
       "max_tokens": 500
     },
     "_versions": {
       "core.database": "1.0.4",
       "standard.ai_agent": "1.0.3"
     }
   }
   ```

2. **client_config.json** - Contains user-specific overrides
   ```json
   {
     "core.database": {
       "max_connections": 10
     }
   }
   ```

3. **settings_metadata.json** - Contains validation rules and UI information
   ```json
   {
     "validation": {
       "core.database": {
         "connection_timeout": {
           "type": "int",
           "min": 1,
           "max": 120
         }
       }
     },
     "ui": {
       "core.database": {
         "connection_timeout": {
           "display_name": "Connection Timeout",
           "input_type": "slider"
         }
       }
     }
   }
   ```

## Viewing and Updating Settings

### Through the UI

The Settings tab in the UI provides a user-friendly interface for viewing and updating settings. Changes made here are stored in `client_config.json` and take effect immediately for most settings.

![Settings UI Example](https://placekitten.com/800/400)

### Using Environment Variables

For deployment-specific or sensitive settings, use environment variables:

```bash
# Linux/macOS
export CORE_DATABASE_CONNECTION_TIMEOUT=60

# Windows
set CORE_DATABASE_CONNECTION_TIMEOUT=60
```

Environment variables are automatically converted to the appropriate type based on the setting's defined type.

## Version Management

The settings system tracks the version of each module's settings schema. When a module is updated:

1. The system detects the version change by comparing the manifest.json version with the stored settings version
2. Settings are automatically updated with any new fields from the latest version
3. Existing settings values are preserved

This ensures your settings stay up-to-date with module updates while preserving your customizations.

## Troubleshooting

### Settings Not Being Applied

If settings don't seem to be applied correctly:

1. **Check Priority**: Environment variables override everything else
2. **Verify Location**: Make sure you're updating the correct setting
3. **Check Types**: Settings are strongly typed and require correct formats
4. **UI Refresh**: Some settings changes may require a UI refresh

### Common Issues

- **Type Mismatches**: Environment variables are strings by default and must be convertible to the expected type
- **Module ID Format**: Module IDs must be in the format `type.name` (e.g., `core.database`)
- **Permission Issues**: Ensure the application has write access to the data directory

### Viewing Current Settings

To see the current effective settings (with all overrides applied):

1. Go to the "Settings" tab in the UI
2. Navigate to the specific module
3. Each setting will show its current value
4. A small indicator shows when a value has been overridden

## Next Steps

- Explore the Settings tab to see available configuration options
- Try overriding a setting using an environment variable
- Review module-specific documentation for details on individual settings

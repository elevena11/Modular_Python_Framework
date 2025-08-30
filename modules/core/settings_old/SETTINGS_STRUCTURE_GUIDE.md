# Settings Structure Guide

## Overview

The VeritasForma Framework settings system uses **flat structure with dot notation** for hierarchical settings. This document outlines the recommended structure and explains why this approach is used.

## 📋 RECOMMENDED: Flat Structure with Dot Notation

**Note**: While the framework core can handle nested structures, the Streamlit UI implementation works best with flat dot notation keys. This guide reflects the current best practices for the Streamlit-based UI.

### ✅ CORRECT: Flat Structure with Dot Notation

```python
# modules/your_module/module_settings.py
DEFAULT_SETTINGS = {
    "enabled": True,
    
    # Hierarchical settings use dot notation
    "database.host": "localhost",
    "database.port": 5432,
    "database.username": "user",
    
    "cache.redis.host": "localhost",
    "cache.redis.port": 6379,
    "cache.redis.timeout": 30,
    
    "api.rate_limit": 100,
    "api.timeout": 30
}

VALIDATION_SCHEMA = {
    "enabled": {
        "type": "bool",
        "required": False
    },
    "database.host": {
        "type": "string",
        "required": False
    },
    "database.port": {
        "type": "int",
        "required": False,
        "min": 1,
        "max": 65535
    }
    # ... more validation rules
}

UI_METADATA = {
    "enabled": {
        "display_name": "Enable Module",
        "description": "Enable or disable this module",
        "type": "checkbox",
        "category": "General"
    },
    "database.host": {
        "display_name": "Database Host",
        "description": "Database server hostname",
        "type": "text",
        "category": "Database"
    },
    "api.rate_limit": {
        "display_name": "API Rate Limit",
        "description": "Maximum requests per minute",
        "type": "select",
        "options": [
            {"value": "50", "label": "50 requests/min"},
            {"value": "100", "label": "100 requests/min"},
            {"value": "200", "label": "200 requests/min"}
        ],
        "category": "API"
    }
}
```

### ⚠️ PROBLEMATIC: Nested Structure (Streamlit UI Issues)

```python
# AVOID: Nested dictionaries can cause Streamlit UI display issues
DEFAULT_SETTINGS = {
    "enabled": True,
    
    # PROBLEMATIC: Nested dictionaries may not display correctly in Streamlit
    "database": {
        "host": "localhost",
        "port": 5432,
        "username": "user"
    },
    
    # PROBLEMATIC: Deeply nested structures can cause UI corruption
    "cache": {
        "redis": {
            "host": "localhost",
            "port": 6379,
            "timeout": 30
        }
    }
}
```

## Data File Structure Requirements

### Settings Files Must Use Flat Structure

**✅ CORRECT data/settings.json:**
```json
{
  "your.module": {
    "enabled": true,
    "database.host": "localhost",
    "database.port": 5432,
    "cache.redis.host": "localhost",
    "cache.redis.port": 6379
  }
}
```

**❌ WRONG data/settings.json:**
```json
{
  "your.module": {
    "enabled": true,
    "database": {
      "host": "localhost",
      "port": 5432
    },
    "cache": {
      "redis": {
        "host": "localhost",
        "port": 6379
      }
    }
  }
}
```

## Historical Issues (Now Resolved)

### Previous Streamlit UI Problems

Before the fix, nested structures caused these issues:

1. **UI Displayed Dictionary Strings**: Settings showed as `"{'host': 'localhost', 'port': 5432}"` instead of individual fields
2. **Save/Reload Corruption**: Settings would corrupt on save due to `_set_nested_value` converting dot notation to nested structures
3. **Validation Failures**: `"'bool' object is not iterable"` errors during validation
4. **Dropdown Issues**: Dropdowns showed `"{'value': 'option', 'label': 'Label'}"` instead of proper options

### Root Cause (Fixed)

The issue was in the settings save logic where `_set_nested_value` was converting flat keys like `"llm.default_provider"` into nested structures like `{"llm": {"default_provider": "value"}}`. This has been fixed by treating dot notation as literal keys rather than nested paths.

## Fixing Corrupted Settings

### 1. Identify Corrupted Files

Check these files for nested structures:
- `data/settings.json`
- `data/client_config.json` 
- `data/settings_metadata.json`

### 2. Flatten Nested Structures

Convert nested structures to dot notation:

**Before (Corrupted):**
```json
{
  "module.id": {
    "config": {
      "sub_setting": "value"
    }
  }
}
```

**After (Fixed):**
```json
{
  "module.id": {
    "config.sub_setting": "value"
  }
}
```

### 3. Update Module Settings

Ensure your module's `DEFAULT_SETTINGS`, `VALIDATION_SCHEMA`, and `UI_METADATA` all use flat dot notation.

## Best Practices

### 1. Use Descriptive Dot Notation

```python
# Good: Clear hierarchy
"llm.providers.openai.api_key": "sk-..."
"llm.providers.openai.timeout": 30
"llm.providers.anthropic.api_key": "..."

# Avoid: Too flat, loses context
"openai_api_key": "sk-..."
"openai_timeout": 30
"anthropic_api_key": "..."
```

### 2. Group Related Settings by Category

```python
UI_METADATA = {
    "llm.providers.openai.api_key": {
        "category": "OpenAI Provider"  # Groups related settings
    },
    "llm.providers.openai.timeout": {
        "category": "OpenAI Provider"
    },
    "llm.providers.anthropic.api_key": {
        "category": "Anthropic Provider"
    }
}
```

### 3. Consistent Naming Conventions

- Use lowercase with underscores: `max_retry_attempts`
- Use dot notation for hierarchy: `provider.openai.api_key`
- Be descriptive: `request_timeout_seconds` not `timeout`

### 4. Validation Schema Alignment

Ensure validation schema keys exactly match setting keys:

```python
DEFAULT_SETTINGS = {
    "api.rate_limit": 100
}

VALIDATION_SCHEMA = {
    "api.rate_limit": {  # Must match exactly
        "type": "int",
        "min": 1,
        "max": 1000
    }
}
```

## Migration Guide

### Converting Existing Nested Settings

1. **Backup** existing settings files
2. **Identify** all nested structures in your module settings
3. **Flatten** using dot notation
4. **Update** validation schemas and UI metadata
5. **Test** thoroughly in development

### Example Migration

**Before:**
```python
DEFAULT_SETTINGS = {
    "database": {
        "connection": {
            "host": "localhost",
            "port": 5432
        },
        "pool": {
            "min_size": 5,
            "max_size": 20
        }
    }
}
```

**After:**
```python
DEFAULT_SETTINGS = {
    "database.connection.host": "localhost",
    "database.connection.port": 5432,
    "database.pool.min_size": 5,
    "database.pool.max_size": 20
}
```

## Troubleshooting

### Common Issues and Solutions

1. **"Dictionary corruption detected"**
   - **Cause**: Nested structures in settings files
   - **Solution**: Flatten all nested structures to dot notation

2. **"Unknown type str in validation schema"**
   - **Cause**: Validation schema uses `"str"` instead of `"string"`
   - **Solution**: Use `"string"`, `"int"`, `"bool"`, `"float"` for types

3. **Settings not saving properly**
   - **Cause**: Mismatch between flat and nested structures
   - **Solution**: Ensure all files use consistent flat structure

4. **UI showing weird strings**
   - **Cause**: Nested objects being serialized as strings
   - **Solution**: Check client_config.json for nested structures

### Debug Tools

The UI includes corruption detection that will:
- Show error messages for corrupted values
- Attempt automatic fixes where possible
- Display problematic settings as disabled text areas

## Framework Integration

### How the Settings System Works

1. **Registration**: Modules register settings (flat structure recommended)
2. **Storage**: Settings stored in JSON files with flat dot notation keys
3. **Validation**: Each setting validated individually against schema
4. **UI Generation**: Streamlit UI components created for each flat setting
5. **Updates**: Individual settings updated via API with literal key storage

### Why Flat Structure is Recommended

- **Streamlit UI Compatibility**: Current UI implementation works best with flat keys
- **Validation Simplicity**: Each setting validated independently
- **API Consistency**: REST endpoints work with individual setting keys
- **Type Safety**: Individual settings have specific types and constraints
- **Persistence Consistency**: Saves and loads maintain flat structure

### Technical Notes

- **Framework Core**: Can technically handle both flat and nested structures
- **UI Layer**: Streamlit implementation optimized for flat dot notation
- **Historical Context**: Previous Gradio UI worked with nested structures, but Gradio is no longer used
- **Save Logic**: Uses literal key storage instead of nested path conversion

## Conclusion

**Best Practice**: Use flat structures with dot notation like `"category.subcategory.setting"` for optimal compatibility with the current Streamlit-based UI system.

This approach ensures your module settings integrate seamlessly with the framework and provide a consistent user experience.
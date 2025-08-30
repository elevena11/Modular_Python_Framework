# VeritasForma Framework Settings Structure Standard

**ENFORCED STANDARD**: All modules MUST use flat settings structure. Nested objects are FORBIDDEN in module settings.

## ❌ FORBIDDEN: Nested Settings Structure

```python
# DO NOT USE - Causes raw JSON display in UI
DEFAULT_SETTINGS = {
    "device_management": {
        "auto_detect": True,
        "prefer_gpu": True,
        "force_cpu": False
    },
    "sharing": {
        "enabled": True,
        "max_shared_models": 5,
        "unload_after_seconds": 1800
    }
}
```

**Problems with nested structure:**
- Displays as ugly raw JSON: `{'enabled': True, 'max_shared_models': 5}`
- No individual control over settings
- Poor user experience
- Harder to validate and document

## ✅ REQUIRED: Flat Settings Structure

```python
# CORRECT - Use flat structure with dot notation
DEFAULT_SETTINGS = {
    "device_preference": "auto",  # Simple dropdown
    "gpu_memory_fraction": 0.8,   # Number input
    "allow_gpu_growth": True,     # Checkbox
    
    "sharing.enabled": True,
    "sharing.max_shared_models": 5,
    "sharing.unload_after_seconds": 1800,
    
    "cache.enabled": True,
    "cache.max_size": 10000,
    "cache.ttl_seconds": 3600
}
```

**Benefits of flat structure:**
- Clean UI with individual labeled inputs
- Easy dropdowns, checkboxes, and number inputs
- Better user experience
- Easier validation and documentation
- Follows existing successful patterns

## UI Metadata Requirements

Each flat setting MUST have proper UI metadata:

```python
UI_METADATA = {
    "device_preference": {
        "display_name": "Device Preference",
        "description": "Choose device for model loading",
        "type": "select",  # Creates dropdown
        "options": [
            {"value": "auto", "label": "Auto-detect (Recommended)"},
            {"value": "gpu", "label": "Force GPU"},
            {"value": "cpu", "label": "Force CPU"}
        ],
        "category": "Hardware"
    },
    "sharing.enabled": {
        "display_name": "Enable Model Sharing",
        "description": "Allow models to be shared between modules",
        "type": "checkbox",  # Creates checkbox
        "category": "Performance"
    },
    "sharing.max_shared_models": {
        "display_name": "Max Shared Models",
        "description": "Maximum number of models to keep loaded",
        "type": "number",  # Creates number input
        "category": "Performance"
    }
}
```

## Validation Schema Requirements

Each flat setting MUST have validation:

```python
VALIDATION_SCHEMA = {
    "device_preference": {
        "type": "string",
        "enum": ["auto", "gpu", "cpu"],
        "required": True
    },
    "sharing.enabled": {
        "type": "bool",
        "required": True
    },
    "sharing.max_shared_models": {
        "type": "int",
        "required": True,
        "min": 1,
        "max": 20
    }
}
```

## Code Access Patterns

Access flattened settings directly:

```python
# CORRECT - Direct access
device_pref = self.config.get("device_preference", "auto")
sharing_enabled = self.config.get("sharing.enabled", True)
max_models = self.config.get("sharing.max_shared_models", 5)

# WRONG - Don't use nested access
sharing_config = self.config.get("sharing", {})
enabled = sharing_config.get("enabled", True)  # Don't do this!
```

## Supported Input Types

Use these UI input types only:

- **`"type": "select"`** - Dropdown with options
- **`"type": "checkbox"`** - Boolean checkbox
- **`"type": "text"`** - Text input
- **`"type": "password"`** - Password input
- **`"type": "number"`** - Number input
- **`"type": "readonly"`** - Read-only display

## Categories for Organization

Group related settings with categories:

```python
"category": "General"      # Enable/disable, basic settings
"category": "Performance"  # Cache, timeouts, limits
"category": "Hardware"     # GPU, CPU, device settings
"category": "Security"     # Passwords, tokens, safety
"category": "Debugging"    # Logging, monitoring
```

## Real Examples from Framework

### ✅ Good Examples (Follow These)

**From `llm_agent` module:**
```python
"safety.default_safety_level": "chat_only",
"llm.default_provider": "ollama",
"chat.max_conversations_per_user": 50
```

**From `database` module:**
```python
"sqlite_journal_mode": "WAL",
"sqlite_synchronous": "NORMAL",
"max_retries": 5
```

### ❌ Bad Examples (Fix These)

**Old nested structures that cause problems:**
```python
# These show as raw JSON - convert to flat!
"models": {"embedding": {...}, "t5": {...}},
"sharing": {"enabled": True, "max": 5},
"cache": {"enabled": True, "size": 1000}
```

## Migration Guide

To convert existing nested settings:

1. **Flatten the structure** using dot notation
2. **Update DEFAULT_SETTINGS** to use flat keys
3. **Update UI_METADATA** for each flat setting
4. **Update VALIDATION_SCHEMA** for each flat setting
5. **Update service code** to access flat config keys
6. **Test UI** to ensure proper display

## Enforcement

- **Code Reviews**: All settings must be flat
- **Compliance Tool**: Run `python tools/compliance/compliance.py` to check
- **Documentation**: This standard is mandatory for all modules
- **UI Testing**: Verify no raw JSON appears in settings interface

## Benefits Summary

Flat settings provide:
- **Clean UI** with proper input controls
- **Better UX** with labeled, organized settings
- **Easier maintenance** and validation
- **Consistent patterns** across all modules
- **No raw JSON display** issues

This standard ensures a professional, maintainable settings system across the entire VeritasForma Framework.
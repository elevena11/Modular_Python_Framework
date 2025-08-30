# Streamlit Dropdown Implementation Guide

This guide explains how to properly implement dropdown menus in VeritasForma Framework settings to avoid displaying raw JSON strings in the UI.

## Problem: Raw JSON Display
❌ **Wrong**: Settings showing as raw JSON strings like `[{"value": "option1", "label": "Option 1"}]`  
✅ **Correct**: Settings showing as clean dropdown menus with user-friendly labels

## Dropdown Implementation Patterns

### Pattern 1: Using `type: "select"` (Recommended)

```python
# In module_settings.py UI_METADATA
"setting_name": {
    "display_name": "User-Friendly Name",
    "description": "Helpful description for users",
    "type": "select",
    "options": [
        {"value": "internal_value", "label": "Display Label"},
        {"value": "another_value", "label": "Another Label"}
    ],
    "category": "Category Name"
}
```

### Pattern 2: Using `input_type: "dropdown"`

```python
# Alternative syntax (also works)
"setting_name": {
    "display_name": "User-Friendly Name", 
    "description": "Helpful description",
    "input_type": "dropdown",
    "options": [
        {"value": "stored_value", "label": "User Sees This"},
        {"value": "another_stored", "label": "User Sees This Too"}
    ],
    "category": "Category Name",
    "order": 10  # Controls display order
}
```

## Real Examples from Framework

### LLM Provider Selection (from llm_agent)
```python
"llm.default_provider": {
    "display_name": "Default LLM Provider",
    "description": "Default provider for LLM requests",
    "type": "select",
    "options": [
        {"value": "ollama", "label": "Ollama (Local)"},
        {"value": "openai", "label": "OpenAI"},
        {"value": "anthropic", "label": "Anthropic"},
        {"value": "huggingface", "label": "HuggingFace"}
    ],
    "category": "LLM"
}
```

### Database Journal Mode (from core.database)
```python
"sqlite_journal_mode": {
    "display_name": "Journal Mode",
    "description": "SQLite journal mode (WAL recommended for concurrency)",
    "input_type": "dropdown",
    "options": [
        {"value": "DELETE", "label": "DELETE"},
        {"value": "TRUNCATE", "label": "TRUNCATE"},
        {"value": "PERSIST", "label": "PERSIST"},
        {"value": "MEMORY", "label": "MEMORY"},
        {"value": "WAL", "label": "WAL (recommended)"},
        {"value": "OFF", "label": "OFF (not recommended)"}
    ],
    "category": "SQLite Settings",
    "order": 10
}
```

### Safety Level Selection (from llm_agent)
```python
"safety.default_safety_level": {
    "display_name": "Default Safety Level",
    "description": "Default safety level for new sessions",
    "type": "select",
    "options": [
        {"value": "chat_only", "label": "Chat Only"},
        {"value": "chat_and_execute", "label": "Chat and Execute"},
        {"value": "autonomous", "label": "Autonomous"},
        {"value": "emergency_stop", "label": "Emergency Stop"}
    ],
    "category": "Safety"
}
```

## How It Works in Streamlit

The framework automatically detects dropdown configurations and renders them using `st.selectbox`:

```python
# Framework automatically converts to:
selected_value = st.selectbox(
    "Default LLM Provider",
    options=["ollama", "openai", "anthropic", "huggingface"],
    format_func=lambda x: {
        "ollama": "Ollama (Local)",
        "openai": "OpenAI", 
        "anthropic": "Anthropic",
        "huggingface": "HuggingFace"
    }[x],
    index=default_index
)
```

## Value vs Label Handling

- **`value`**: Stored in database and used by code (e.g., `"ollama"`)
- **`label`**: Displayed to users (e.g., `"Ollama (Local)"`)
- **Storage**: Only the `value` is saved to settings.json
- **Display**: Only the `label` is shown to users

## Alternative: Enum-Based Dropdowns

You can also define dropdowns through validation schema:

```python
# In VALIDATION_SCHEMA
"setting_name": {
    "type": "string",
    "enum": ["option1", "option2", "option3"],
    "required": True
}

# In UI_METADATA (minimal)
"setting_name": {
    "display_name": "Setting Name",
    "description": "Choose an option",
    "category": "Category"
}
```

## Common Mistakes to Avoid

❌ **Don't use `"type": "text"`** for dropdowns  
❌ **Don't store entire option objects** in default settings  
❌ **Don't use complex nested structures** without proper UI metadata  
❌ **Don't forget to include `options` array**

✅ **Do use `"type": "select"` or `"input_type": "dropdown"`**  
✅ **Do store only the `value` in default settings**  
✅ **Do provide clear `label` descriptions**  
✅ **Do organize with `category` and `order`**

## Fixing Existing Raw JSON Issues

If you have settings showing as raw JSON:

1. **Check UI_METADATA**: Ensure proper `type: "select"` or `input_type: "dropdown"`
2. **Check DEFAULT_SETTINGS**: Store only the `value`, not the full option object
3. **Check options format**: Use `[{"value": "...", "label": "..."}]` format
4. **Test in UI**: Verify dropdown appears instead of text input

## Categories and Organization

Group related dropdowns using categories:

```python
"category": "Database"      # Groups with other DB settings
"category": "Performance"   # Groups with other performance settings  
"category": "Security"      # Groups with other security settings
"order": 10                 # Controls order within category
```

This ensures clean, organized settings interfaces that are user-friendly and maintainable.
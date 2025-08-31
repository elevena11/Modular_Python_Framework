# Streamlit UI Implementation Guide for Modular AI Framework

## Overview

This guide provides instructions and best practices for implementing Streamlit UI components in the Modular AI Framework. It compiles lessons learned and solutions to common issues when developing `ui_streamlit.py` files.

## Table of Contents

1. [Basic Structure](#basic-structure)
2. [Framework Detection](#framework-detection)
3. [Streamlit State Management](#streamlit-state-management)
4. [Widget Requirements](#widget-requirements)
5. [Common Patterns](#common-patterns)
6. [Type Consistency](#type-consistency)
7. [Migration Notes](#migration-notes)
8. [Troubleshooting](#troubleshooting)

## Basic Structure

Each module's Streamlit UI implementation should follow this structure:

```python
"""
modules/[type]/[module_name]/ui/ui_streamlit.py
Streamlit implementation of the UI for [module_name].
"""

import logging
import streamlit as st
from typing import Dict, List, Any

# Import framework-agnostic services
from .services import your_service_functions

logger = logging.getLogger("modular.[type].[module_name].ui.streamlit")

def register_components(ui_context):
    """
    Register UI components for the module.
    This function is called by the module loader.
    """
    logger.info(f"Registering {module_name} UI components with Streamlit")
    
    # Register UI elements
    ui_context.register_element({
        "type": "tab",
        "id": "my_module_tab",
        "display_name": "My Module Tab",
        "description": "Description of this tab's functionality",
        "priority": 10,  # Lower numbers appear first
        "render_function": render_my_tab
    })
    
    logger.info(f"{module_name} UI components registered")

def render_my_tab(ui_context):
    """
    Render the main tab content.
    This function is called when the tab is selected.
    """
    # Get services or API clients
    api_client = ui_context.get_service("api_client")
    
    # Create UI elements
    st.title("My Module")
    st.write("This is a module UI implemented in Streamlit")
    
    # Create input widgets, processing logic, and output displays
    # ...
```

## Framework Detection

The module loader will:

1. First check for `ui/__init__.py` with framework detection
2. If not found, look for specific `ui/ui_streamlit.py` implementation

If using the framework detection approach in `__init__.py`:

```python
def register_components(ui_context):
    """
    Register UI components with framework detection.
    """
    # Detect which framework is active based on available modules
    is_streamlit = 'streamlit' in sys.modules and hasattr(sys.modules['streamlit'], 'title')
    
    # Register components for the appropriate framework
    if is_streamlit:
        from . import ui_streamlit
        ui_streamlit.register_components(ui_context)
    else:
        # Framework not available - log warning
        logger.warning("Streamlit framework not detected")
```

## Streamlit State Management

### Session State

Streamlit uses a session state object to persist data across reruns:

```python
# Initialize state if needed
if 'key' not in st.session_state:
    st.session_state.key = initial_value

# Access state
current_value = st.session_state.key

# Update state
st.session_state.key = new_value
```

### Triggering Reruns

When state changes require a UI refresh:

```python
# Update state and trigger rerun
if new_selection != st.session_state.current_selection:
    st.session_state.current_selection = new_selection
    st.rerun()  # Note: not st.experimental_rerun()
```

## Widget Requirements

### Unique Keys

**IMPORTANT**: All Streamlit widgets must have unique keys:

```python
# BAD: No keys - may cause "StreamlitDuplicateElementId" errors
value = st.text_input("Label", value="default")

# GOOD: Unique keys prevent duplicate ID errors
value = st.text_input("Label", value="default", key="module_label_text")
```

Create keys that combine module ID, setting name, and widget type:

```python
key = f"{module_id}_{setting_name}_{widget_type}"
value = st.text_input("Setting", value="default", key=key)
```

### Type Consistency

All numeric arguments must be of the same type:

```python
# BAD: Mixed types (int and float) will cause errors
st.number_input("Value", value=1.0, min_value=0, max_value=10, step=0.1)

# GOOD: Consistent types
st.number_input("Value", value=1.0, min_value=0.0, max_value=10.0, step=0.1)
```

Always convert numeric parameters to the same type:

```python
# For integers
min_val = int(min_val) if min_val is not None else None
max_val = int(max_val) if max_val is not None else None
value = int(value) if value is not None else 0

# For floats
min_val = float(min_val) if min_val is not None else None
max_val = float(max_val) if max_val is not None else None
value = float(value) if value is not None else 0.0
```

## Common Patterns

### Layout Components

Streamlit uses different layout components than Gradio:

```python
# Columns
col1, col2 = st.columns(2)  # Two equal columns
with col1:
    st.write("Content for left column")
with col2:
    st.write("Content for right column")

# Tabs
tab1, tab2 = st.tabs(["First Tab", "Second Tab"])
with tab1:
    st.write("Content for first tab")
with tab2:
    st.write("Content for second tab")

# Expandable sections
with st.expander("Click to expand"):
    st.write("Hidden content here")
```

### Data Display

```python
# Display data frames
st.dataframe(df)  # Interactive dataframe

# Display JSON
st.json(data)

# Display code
st.code(code_string, language="python")

# Display metrics
st.metric(label="Temperature", value=32, delta=2)
```

### Status Messages

```python
# Status messages
st.success("Operation successful")
st.info("Information message")
st.warning("Warning message")
st.error("Error message")
```

## Type Consistency

Streamlit is more strict about type consistency than Gradio:

1. **Numeric Inputs**: All numeric parameters (value, min_value, max_value, step) must be the same type
2. **List Items**: All items in a list should be the same type for display components
3. **Date/Time**: Use proper datetime objects, not strings, for date inputs

Example of handling different setting types:

```python
# Boolean setting
if setting_type == "bool":
    value = st.checkbox(
        label, 
        value=bool_value,
        key=f"{module_id}_{setting_name}_bool"
    )

# Integer setting
elif setting_type == "int":
    # Ensure all values are integers
    min_val = int(min_val) if min_val is not None else None
    max_val = int(max_val) if max_val is not None else None
    int_value = int(value) if value is not None else 0
    
    value = st.number_input(
        label,
        value=int_value,
        min_value=min_val,
        max_value=max_val,
        step=1,
        key=f"{module_id}_{setting_name}_int"
    )

# Float setting
elif setting_type == "float":
    # Ensure all values are floats
    min_val = float(min_val) if min_val is not None else None
    max_val = float(max_val) if max_val is not None else None
    float_value = float(value) if value is not None else 0.0
    
    value = st.number_input(
        label,
        value=float_value,
        min_value=min_val,
        max_value=max_val,
        step=0.1,
        format="%.2f",
        key=f"{module_id}_{setting_name}_float"
    )
```

## Migration Notes

When implementing Streamlit UI components, consider these framework-specific characteristics:

### Key Streamlit Features
- **Automatic Reactivity**: UI automatically updates when widgets change
- **Session State**: Persistent data storage across reruns
- **Type Safety**: Strict type consistency for numeric inputs
- **Layout System**: Column-based layouts with `st.columns()`
- **Built-in Components**: Rich set of data display components

### Framework Considerations
- All widgets require unique keys to prevent duplicate element errors
- Numeric inputs must have consistent types (all int or all float)
- State management uses `st.session_state` dictionary
- UI updates automatically trigger reruns
- Layout is handled through context managers and column structures

## Troubleshooting

### Common Errors and Solutions

#### StreamlitDuplicateElementId

**Error**: `streamlit.errors.StreamlitDuplicateElementId`

**Solution**: Add unique keys to all input widgets:

```python
st.text_input("Label", value="default", key="unique_key")
```

#### StreamlitMixedNumericTypesError

**Error**: `streamlit.errors.StreamlitMixedNumericTypesError`

**Solution**: Ensure all numeric arguments are the same type:

```python
# Convert all to float
min_val = float(min_val) if min_val is not None else None
max_val = float(max_val) if max_val is not None else None
value = float(value) if value is not None else 0.0

st.number_input(..., value=value, min_value=min_val, max_value=max_val)
```

#### Missing ScriptRunContext

**Error**: `Thread 'MainThread': missing ScriptRunContext!`

**Solution**: Don't directly manipulate Streamlit components outside the main execution flow. Move the code into a proper Streamlit app or use the launcher approach.

#### State Lost Between Reruns

**Problem**: Widget values reset on page refresh

**Solution**: Use session state to persist values:

```python
if 'my_value' not in st.session_state:
    st.session_state.my_value = default_value

# Use the value from session state
st.text_input("Input", value=st.session_state.my_value, key="my_input")
```

### Debugging Tips

1. Use `st.write()` for quick debugging output
2. Add explicit logging statements
3. When handling complex data, use `st.json()` to visualize it
4. For widget issues, try simplifying by creating widgets with minimal parameters first
5. Check for type consistency in all numeric inputs

## Best Practices

1. **Always use unique keys** for all Streamlit widgets
2. **Maintain type consistency** for all numeric inputs
3. **Use session state** for persisting data between reruns
4. **Follow standard layout patterns** for consistent UIs
5. **Use appropriate string representations** for complex data types
6. **Handle None values gracefully** with sensible defaults
7. **Use expanders** for sections that might get long
8. **Prefer columns** over complex nested layouts
9. **Provide clear error messages** using st.error()
10. **Use st.rerun() carefully** to avoid infinite loops

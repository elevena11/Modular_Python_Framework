# UI Streamlit Implementation Standard

**Version: 1.0.0**
**Updated: March 20, 2025**

## Purpose

This standard ensures that modules in the Modular AI Framework provide a Streamlit UI implementation to support the multi-framework UI architecture. It validates that each module with UI components offers an implementation for the Streamlit framework, enabling users to choose their preferred UI experience.

## Rationale

1. **Framework Flexibility**: Streamlit offers an alternative UI experience with different strengths
2. **User Choice**: Supporting multiple frameworks allows users to select their preferred interface
3. **Implementation Discoverability**: The UI module loader must be able to locate Streamlit implementations
4. **Framework Predictability**: Module UIs must follow a consistent pattern for dynamic loading
5. **Feature Parity**: Modules should strive to offer equivalent functionality across frameworks

## Requirements

Each module that provides UI components should include:

- `ui/ui_streamlit.py` - A Streamlit-specific implementation file

This file must exist in the module's `ui` directory and follow the standard registration pattern.

## Implementation Guide

### Basic Implementation

Create a `ui/ui_streamlit.py` file with the following structure:

```python
def register_components(ui_context):
    """Register UI components for the module."""
    ui_context.register_element({
        "type": "tab",
        "id": "my_component",
        "display_name": "My Component",
        "description": "Description of my component",
        "priority": 10,
        "render_function": render_my_component
    })
    
def render_my_component(ui_context):
    """Render the component UI using Streamlit."""
    import streamlit as st
    
    st.title("My Component")
    # Implementation details...
```

### Required Function Signatures

- `register_components(ui_context)`: Entry point for registering UI elements
- Element render function that accepts `ui_context` parameter

### Element Registration Format

```python
ui_context.register_element({
    "type": "tab",  # Element type (tab, panel, widget, etc.)
    "id": "unique_id",  # Unique identifier for this element
    "display_name": "Human-Readable Name",  # User-facing name
    "description": "Description of functionality",  # User-facing description
    "priority": 10,  # Display order (lower numbers first)
    "render_function": function_reference  # Function to render the element
})
```

## Common Issues and Solutions

### Common Violations

1. **Missing Streamlit File**: No `ui/ui_streamlit.py` file in the module
   - Solution: Add a Streamlit implementation in `ui/ui_streamlit.py`

2. **Incorrect Registration Pattern**: Not using the `register_element` method
   - Solution: Update to use the standard registration format shown above

3. **Framework-Specific Code Issues**: Using Gradio components in Streamlit implementation
   - Solution: Use appropriate Streamlit components and patterns

### Fixing Violations

To add a missing Streamlit implementation:

1. Create a `ui` directory in your module if it doesn't exist
2. Create a `ui_streamlit.py` file with the required components
3. Implement the `register_components` function
4. Create render functions for your UI components

## Validation

The standard performs two checks:

1. **File Existence**: Verifies that `ui/ui_streamlit.py` exists in the module
2. **Registration Pattern**: Checks that the file contains:
   - A `register_components(ui_context)` function
   - Calls to `ui_context.register_element()` with appropriate parameters
   - Required keys in the registration dictionary ("type", "id", "display_name", "render_function")

A module passes validation if the file exists and contains the correct registration pattern.

## FAQ

**Q: Is Streamlit support required for all modules?**
A: Streamlit support is encouraged but not mandatory. Modules should prioritize implementing Gradio UI first, then add Streamlit support when possible.

**Q: How do Streamlit and Gradio implementations differ?**
A: While registration is similar, the actual UI rendering is different due to the fundamentally different APIs and patterns of the two frameworks.

**Q: Can I share code between Gradio and Streamlit implementations?**
A: Business logic can often be shared, but UI rendering code should be framework-specific. Consider creating a shared services.py file in the UI directory for common logic.

**Q: How does my Streamlit implementation get used?**
A: When a user launches the application with Streamlit as the selected framework, the UI module loader will discover and use your `ui_streamlit.py` implementation.

**Q: Are there guidelines for consistent UI between frameworks?**
A: Yes - while implementation details differ, strive to maintain visual and functional consistency between frameworks. Elements should have the same names, ordering, and general behavior.
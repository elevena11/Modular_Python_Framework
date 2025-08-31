# UI Configuration System

version: 2.0.0
updated: 09/03/2025

## Overview

The UI Configuration System allows users to customize which UI elements are visible in the application interface. This provides a cleaner, more focused user experience by hiding elements that aren't relevant to the user's current needs, while allowing modules to register multiple UI components.

## Design Principles

1. **Modularity**: Modules can register multiple UI elements, not just a single tab
2. **Flexibility**: Clear separation between element identifiers and display names
3. **Precision**: Fine-grained control over individual UI elements
4. **Core Protection**: Essential system elements cannot be disabled
5. **Persistence**: Configuration settings are saved between application restarts
6. **Single Source of Truth**: Protected elements are defined in one central location

## Key Concepts

### UI Elements

UI elements are the building blocks of the user interface. Each element has:
- A unique identifier (`id`)
- A module it belongs to (`module_id`)
- A type (e.g., "tab", "panel", "widget")
- A display name shown to users
- A description of its functionality
- A priority/order value for positioning
- A render function to create the actual UI component

### Element Registry

The Element Registry is a centralized repository of all UI elements in the system. It:
- Maintains a list of all registered elements
- Organizes elements by module and type
- Provides lookup and filtering capabilities
- Handles element validation during registration

### Protected Elements

Some UI elements are considered essential and cannot be disabled:

```python
# Single source of truth for protected elements
PROTECTED_ELEMENTS = [
    "core.ui_config.config_panel",  # UI Configuration tab
    "core.system.home",             # Home tab
    "core.database.database_viewer", # Database Viewer
    "core.settings.settings_manager", # Settings Manager
    "standard.llm_instruction.instruction_handler" # LLM Instruction Handler
]
```

Protected elements do not appear in the configuration interface as they must remain enabled.

## Element Registration

Modules register their UI elements using a standardized API:

```python
def register_ui_components(ui_context):
    """Register UI components for the module."""
    # Register a tab element
    ui_context.register_element({
        "type": "tab",
        "id": "database_viewer",
        "display_name": "Database Viewer",
        "description": "View and manage database tables",
        "priority": 10,
        "render_function": render_database_viewer
    })
    
    # Register another element from the same module
    ui_context.register_element({
        "type": "tab",
        "id": "query_tool",
        "display_name": "SQL Query Tool",
        "description": "Execute custom SQL queries",
        "priority": 20,
        "render_function": render_query_tool
    })
```

### Element IDs

Each UI element has a unique ID consisting of:
- The module ID (e.g., "core.database")
- The element ID (e.g., "database_viewer")

Combined into a full ID: "core.database.database_viewer"

This provides a clear and unique identifier for each UI element in the system.

## Configuration Storage

UI configuration is stored in a JSON file with the following structure:

```json
{
  "ui_elements": {
    "core.database.database_viewer": {
      "visible": true,
      "order": 5
    },
    "core.database.query_tool": {
      "visible": false,
      "order": 6
    },
    "core.file_manager.file_browser": {
      "visible": true,
      "order": 10
    }
  },
  "version": "2.0.0",
  "last_updated": "2025-03-09T21:50:25.023361"
}
```

## Two-Phase Initialization

The UI Configuration module follows the framework's two-phase initialization pattern:

### Phase 1
- Loads the basic configuration file
- Sets up the element registry
- Registers services and APIs
- Sets up protected elements list

### Phase 2
- Discovers all modules with UI components
- Registers UI elements from these modules
- Updates the configuration with any newly discovered elements
- Sets default visibility for new elements (visible by default)

## Implementation Details

## Component Implementation Guidelines

When implementing UI components for the Modular AI Framework, consider these best practices:

### Data Handling

1. **Complex Data Objects**: When working with complex data like JSON objects:
   - Use Streamlit's session state to persist data across reruns
   - Use `st.json()` for displaying JSON objects with proper formatting
   - Convert complex objects to appropriate display formats

2. **Streamlit Component Features**:
   - DataFrame components handle complex nested objects well with `st.dataframe()`
   - Use interactive widgets for user input and selection
   - Leverage built-in data visualization capabilities

3. **State Management**:
   - Store data in `st.session_state` for persistence across reruns
   - Use unique keys for all interactive widgets
   - Handle state updates with `st.rerun()` when necessary

### User Experience Patterns

1. **Master-Detail Pattern**:
   - For complex data tables, implement a master-detail pattern
   - Show simplified data in the main view using `st.dataframe()` with selection
   - Provide detailed information in expandable sections or separate columns
   - Use Streamlit's built-in selection capabilities for interactive data exploration

2. **Error Handling**:
   - Implement robust error handling in all UI components
   - Provide clear error messages to users
   - Log errors with sufficient detail for debugging

### Core Module: `core.ui_config`

The UI configuration system is implemented as a core module with:

- **Element Registry**: Centralized registry of all UI elements
- **API endpoints**: For programmatic configuration management
- **Service layer**: For loading/saving configuration
- **UI component**: For the configuration interface
- **Configuration storage**: For persistence
- **Centralized protected elements list**: For consistency

### Configuration Process

1. During application startup, the UI configuration is loaded from the configuration file
2. If no configuration file exists, a default configuration is created with all elements visible
3. During Phase 2, all modules with UI components register their elements
4. When the UI is rendered, elements respect their visibility settings in the configuration
5. Changes made in the UI Configuration tab are persisted to the configuration file
6. Element visibility changes require an application restart to take effect

### UI Implementation

The UI Configuration tab displays:
- A list of all configurable (non-protected) UI elements
- Toggles for turning elements on/off
- Clear descriptions of what each element does
- Grouping by module for easier management
- A save button to persist changes

## API Endpoints

The module provides these API endpoints:

- `GET /api/v1/ui-config` - Get the complete configuration
- `POST /api/v1/ui-config` - Update the complete configuration
- `GET /api/v1/ui-config/elements` - Get all registered UI elements
- `GET /api/v1/ui-config/elements/{full_id}` - Get a specific element's details
- `PUT /api/v1/ui-config/elements/{full_id}/visibility` - Update an element's visibility
- `GET /api/v1/ui-config/protected-elements` - Get the list of protected elements

## Usage Examples

### Registering UI Elements

```python
def register_ui_components(ui_context):
    """Register UI components for the file manager module."""
    ui_context.register_element({
        "type": "tab",
        "id": "file_browser",
        "display_name": "File Browser",
        "description": "Browse and manage files in the system",
        "priority": 10,
        "render_function": render_file_browser
    })
```

### Checking Element Visibility

```python
def check_element_visibility(ui_context, element_id):
    """Check if an element should be visible."""
    # Get the configuration service
    config_service = ui_context.backend_api.get_service("ui_config_service")
    
    # Check if this element is visible
    return config_service.is_element_visible(element_id)
```

### Rendering UI Based on Configuration

```python
def compose_ui(ui_context):
    """Build the UI based on registered elements and configuration."""
    elements = ui_context.get_registered_elements()
    
    # Filter to tabs and check visibility
    visible_tabs = []
    for element in elements:
        if element["type"] == "tab":
            is_visible = ui_context.is_element_visible(element["full_id"])
            if is_visible:
                visible_tabs.append(element)
    
    # Sort tabs by order
    visible_tabs.sort(key=lambda t: t.get("order", t.get("priority", 100)))
    
    # Render tabs
    tab_names = [tab["display_name"] for tab in visible_tabs]
    selected_tab = st.tabs(tab_names)
    for i, tab in enumerate(visible_tabs):
        with selected_tab[i]:
            tab["render_function"](ui_context)
```

## Future Enhancements

Planned future enhancements include:
- Element grouping and categorization
- Drag-and-drop reordering of elements
- Per-user configurations
- Role-based element visibility
- UI theming and styling configuration
- Conditional visibility based on system state

## Migration from Previous Version

For modules using the old tab-based configuration:

1. Update your `register_ui_components` function to use the new element registration API
2. Use element IDs instead of tab names for identification
3. Provide display names separately from IDs
4. Add descriptions to help users understand your UI elements
5. Consider breaking complex tabs into multiple elements for better user control

If you previously had:
```python
def register_ui_components(ui_context):
    # Old tab-based registration
    pass
```

Update to:
```python
def register_ui_components(ui_context):
    ui_context.register_element({
        "type": "tab",
        "id": "database_viewer",
        "display_name": "Database Viewer",
        "description": "View and manage database tables",
        "priority": 10,
        "render_function": render_database_viewer
    })
    
    def render_database_viewer(ui_context):
        st.title("Database Viewer")
        # Streamlit UI code...
```

The system includes backward compatibility for modules not yet updated to the new API.

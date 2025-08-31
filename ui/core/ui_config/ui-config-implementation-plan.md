# UI Configuration Module Implementation Plan - Revised

## Module Structure

```
modules/core/ui_config/
  ├── api.py              # API endpoints for config management 
  ├── services.py         # Services for loading/saving config
  ├── manifest.json       # Module definition
  ├── ui.py               # UI configuration tab implementation
  └── registry.py         # UI element registry management
```

## Core Files and Functionality

### manifest.json
```json
{
  "id": "ui_config",
  "name": "UI Configuration",
  "version": "1.0.0",
  "description": "Configuration management for UI components and tabs",
  "author": "Modular Framework",
  "dependencies": ["core.database"],
  "entry_point": "api.py"
}
```

### services.py
The `services.py` file provides:
- Single source of truth for protected elements
- UI element registry management
- Configuration loading/saving
- Validation logic
- Module discovery in Phase 2

Key classes:
- `UIConfigService`: Main service for managing UI configuration
- `UIElementRegistry`: Registry for UI elements from various modules

### registry.py
The `registry.py` file provides:
- Data structures for UI element registration
- Methods for registering, retrieving, and managing UI elements
- Validation for element registration
- Helper methods for UI composition

### api.py
The `api.py` file provides:
- Phase 1 & 2 initialization
- API endpoints for configuration management
- Element registration endpoints
- Dependency injection for the service
- Error handling

Key API endpoints:
- `GET /api/v1/ui-config` - Get the current configuration
- `POST /api/v1/ui-config` - Update the configuration
- `GET /api/v1/ui-config/elements` - Get all registered UI elements
- `PUT /api/v1/ui-config/elements/{element_id}/visibility` - Update an element's visibility
- `GET /api/v1/ui-config/protected-elements` - Get list of protected elements

### ui.py
The `ui.py` file provides:
- UI component for the configuration tab
- Imports the protected elements list from services.py
- Uses API calls to interact with the backend
- Handles Streamlit implementation requirements

## Data Structures

### UI Element Registry Entry
```json
{
  "module_id": "core.database",
  "type": "tab",
  "id": "database_viewer",
  "display_name": "Database Viewer",
  "description": "View and manage database content",
  "priority": 10,
  "render_function": "function_reference"
}
```

### UI Configuration JSON
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
    }
  },
  "version": "1.0.0",
  "last_updated": "2025-03-09T21:50:25.023361"
}
```

## Implementation Pattern

### UI Element Registry

The `UIElementRegistry` handles:
- Registration of UI elements from modules
- Tracking element metadata (type, display name, etc.)
- Organizing elements by module ID for easy lookup
- Providing validation for element registration

```python
class UIElementRegistry:
    """Registry for UI elements from various modules."""
    
    def __init__(self):
        """Initialize an empty registry."""
        self.elements = {}  # Module ID -> List of elements
        
    def register_element(self, module_id: str, element_data: dict) -> str:
        """Register a UI element from a module."""
        if module_id not in self.elements:
            self.elements[module_id] = []
            
        # Validate required fields
        required_fields = ["id", "type", "display_name"]
        for field in required_fields:
            if field not in element_data:
                raise ValueError(f"Missing required field '{field}' in element data")
                
        # Create a full element ID
        element_id = f"{module_id}.{element_data['id']}"
        
        # Add to registry
        self.elements[module_id].append({
            "module_id": module_id,
            "full_id": element_id,
            **element_data
        })
        
        return element_id
```

### Configuration Service

The `UIConfigService` handles:
- Loading configuration from a JSON file
- Saving configuration changes
- Providing default configuration
- Validating configuration data
- Determining which elements are protected
- Discovering modules with UI components

```python
class UIConfigService:
    """Service for managing UI configuration."""
    
    def __init__(self, app_context):
        """Initialize the UI configuration service."""
        self.app_context = app_context
        self.config_file = os.path.join(app_context.config.DATA_DIR, "ui_config.json")
        self.protected_elements = PROTECTED_ELEMENTS
        self.element_registry = UIElementRegistry()
        self.config = self._load_config()
    
    def is_element_visible(self, element_id: str) -> bool:
        """Check if a UI element is visible."""
        # Protected elements are always visible
        if element_id in self.protected_elements:
            return True
        
        # Check in configuration
        if element_id in self.config["ui_elements"]:
            return self.config["ui_elements"][element_id].get("visible", True)
        
        # Default to visible
        return True
```

### Two-Phase Initialization

The module follows the framework's two-phase initialization:

**Phase 1:**
```python
def initialize(app_context):
    global ui_config_service
    
    logger.info("Initializing UI Configuration module (Phase 1)")
    
    # Create and register configuration service
    ui_config_service = UIConfigService(app_context)
    app_context.register_service("ui_config_service", ui_config_service)
    
    # Register for Phase 2 initialization
    app_context.register_module_setup_hook(
        "core.ui_config",
        setup_module
    )
```

**Phase 2:**
```python
async def setup_module(app_context):
    logger.info("Starting UI Configuration module Phase 2 initialization")
    
    # Get the configuration service
    config_service = app_context.get_service("ui_config_service")
    
    # Discover modules with UI components
    await config_service.discover_ui_modules()
```

### UI Composition

The UI composition logic in `gradio_ui.py` is updated to:
- Get all registered UI elements from the registry
- Check element visibility based on configuration
- Sort elements by order/priority
- Render visible elements using their render functions

```python
def compose_ui(ui_context):
    """Build the UI based on registered elements and configuration."""
    elements = ui_context.get_registered_elements()
    
    # Filter to just tab elements and check visibility
    tabs = []
    for element in elements:
        if element["type"] == "tab":
            element_id = element["full_id"]
            is_protected = element_id in PROTECTED_ELEMENTS
            is_visible = is_protected or ui_context.is_element_visible(element_id)
            
            if is_visible:
                tabs.append(element)
    
    # Sort tabs by order/priority
    tabs.sort(key=lambda t: ui_context.get_element_order(t["full_id"], t.get("priority", 100)))
    
    # Render tabs
    tab_names = [tab["display_name"] for tab in tabs]
    selected_tabs = st.tabs(tab_names)
    for i, tab in enumerate(tabs):
        with selected_tabs[i]:
            tab["render_function"](ui_context)
```

## Integration with Streamlit UI

The Streamlit UI implementation is modified to:
- Get registered UI elements during startup
- Check element visibility using the configuration service
- Render elements in the specified order
- Support module-specific render functions
- Default to visible for any configuration errors

## Element Registration API

Modules register their UI elements using this API:

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
    
    # Define the render function
    def render_database_viewer(ui_context):
        st.title("Database Viewer")
        st.write("Database viewer content here")
        # Rest of the Streamlit UI code...
```

## Testing Strategy

1. **Unit Tests**
   - Test element registration
   - Test configuration loading/saving
   - Test visibility determination
   - Test protected element detection

2. **Integration Tests**
   - Test UI element discovery
   - Test configuration application to UI
   - Test persistence between restarts

3. **User Testing**
   - Verify UI is intuitive
   - Confirm changes persist correctly
   - Check error handling

4. **Component Interaction Tests**
   - Test complex data handling in components
   - Verify proper display of nested data structures
   - Test selection and detail viewing mechanisms
   - Check error handling for edge cases

## Migration Strategy

To transition from the old tab-based system to the new element-based system:

1. Create a database of existing modules and their tab names
2. Create migration functions to convert old-style configurations
3. Add backward compatibility for modules not yet updated to the new API
4. Provide clear documentation and examples for module developers

## Implementation Guidelines

- Follow framework's module pattern
- Use proper logging throughout
- Ensure proper error handling at all levels
- Practice defensive programming
- Keep code DRY and modular
- Document all classes and public methods
- Follow Phase 1 & 2 initialization pattern strictly
- Use API-based approach for UI/backend communication
- Consider Streamlit framework requirements and best practices
- Use Streamlit's built-in data display capabilities for complex data structures
- Implement proper state management with session state
- Test with various data types including complex nested structures
- Follow Streamlit's unique key requirements for all interactive widgets

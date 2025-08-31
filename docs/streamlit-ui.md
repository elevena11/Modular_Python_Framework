# Streamlit UI System

The framework includes a complete Streamlit-based web interface that provides an intuitive way to interact with your modules through a browser-based dashboard.

## Quick Start

### Running the UI
```bash
# Start the Streamlit interface
python run_ui.py

# Or directly with streamlit
streamlit run ui/streamlit_app.py

# Specify port (default: 8501)
python run_ui.py --port 8502
```

The UI will be available at `http://localhost:8501` by default.

### Available Interfaces
```bash
# Streamlit interface (default)
python run_ui.py --ui streamlit

# Additional UI frameworks can be configured
python run_ui.py --ui gradio    # If implemented
python run_ui.py --ui flask     # If implemented
```

---

## UI Architecture

### Core Components

**`run_ui.py`** - Main UI Entry Point
- **Purpose**: Configurable UI launcher with framework detection
- **Features**: Command-line argument parsing, UI framework selection, logging setup
- **Usage**: Primary way to start the UI system

**`ui/streamlit_app.py`** - Streamlit Application
- **Purpose**: Streamlit-specific application entry point  
- **Features**: Module loading, page routing, session management
- **Integration**: Connects to backend services via app context

**`ui/core/`** - UI Framework Infrastructure
- `config.py` - UI configuration management
- `app_context.py` - UI application context and service integration
- `module_loader.py` - Dynamic UI module loading
- `ui_loader.py` - Framework-agnostic UI loading system

### UI Integration Pattern

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   run_ui.py     │───▶│  streamlit_app  │───▶│  Module UIs     │
│  (Entry Point)  │    │   (Framework)   │    │ (Feature Pages) │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  UI Config      │    │  UI App Context │    │  Backend API    │
│  (Settings)     │    │  (Services)     │    │  (app.py)       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

---

## Creating Module UIs

### UI File Structure

When using the scaffolding tool with `ui_streamlit` feature:

```
modules/standard/my_module/
├── api.py              # Backend API endpoints
├── services.py         # Business logic
├── ui.py              # Streamlit UI implementation
└── ui_schemas.py       # UI-specific data schemas (optional)
```

### Basic UI Implementation

```python
# modules/standard/my_module/ui.py
"""
Streamlit UI implementation for my_module.
"""

import streamlit as st
import logging
from typing import Dict, List, Any

logger = logging.getLogger("modular.standard.my_module.ui.streamlit")

def register_components(ui_context):
    """
    Register UI components with the framework.
    Called automatically by the UI module loader.
    """
    logger.info("Registering my_module UI components")
    
    # Register a main tab
    ui_context.register_element({
        "type": "tab",
        "id": "my_module_tab",
        "display_name": "My Module",
        "description": "Main interface for my module functionality",
        "priority": 10,
        "render_function": render_main_tab
    })
    
    # Register a sidebar component (optional)
    ui_context.register_element({
        "type": "sidebar",
        "id": "my_module_sidebar",
        "display_name": "Quick Actions",
        "priority": 20,
        "render_function": render_sidebar
    })

def render_main_tab(ui_context):
    """Render the main tab content."""
    st.header("My Module Interface")
    
    # Connect to backend service
    try:
        service = ui_context.get_service("my_module.service")
        
        # Example: Display module status
        with st.expander("Module Status", expanded=True):
            if st.button("Check Status"):
                result = service.get_status()
                if result.success:
                    st.success(f"Status: {result.data}")
                else:
                    st.error(f"Error: {result.error['message']}")
        
        # Example: User input form
        with st.form("module_action_form"):
            st.subheader("Perform Action")
            
            user_input = st.text_input("Enter data:")
            action_type = st.selectbox("Action", ["create", "update", "delete"])
            
            if st.form_submit_button("Execute"):
                if user_input:
                    result = service.perform_action(action_type, user_input)
                    if result.success:
                        st.success("Action completed successfully!")
                        st.json(result.data)
                    else:
                        st.error(f"Action failed: {result.error['message']}")
                else:
                    st.warning("Please enter some data")
    
    except Exception as e:
        st.error(f"Failed to connect to service: {str(e)}")

def render_sidebar(ui_context):
    """Render sidebar components."""
    st.sidebar.subheader("My Module")
    
    if st.sidebar.button("Quick Action"):
        st.sidebar.success("Quick action performed!")
    
    # Display module statistics
    try:
        service = ui_context.get_service("my_module.service") 
        stats = service.get_statistics()
        if stats.success:
            st.sidebar.metric("Total Items", stats.data.get("count", 0))
    except:
        st.sidebar.warning("Stats unavailable")
```

### Advanced UI Patterns

#### State Management
```python
def render_main_tab(ui_context):
    # Initialize session state
    if "my_module_data" not in st.session_state:
        st.session_state.my_module_data = {}
    
    # Use session state for persistence
    if st.button("Load Data"):
        service = ui_context.get_service("my_module.service")
        result = service.get_data()
        if result.success:
            st.session_state.my_module_data = result.data
            st.rerun()  # Refresh the UI
```

#### Real-time Updates
```python
def render_main_tab(ui_context):
    # Auto-refresh every 30 seconds
    import time
    
    placeholder = st.empty()
    
    if st.checkbox("Auto-refresh", value=False):
        while True:
            with placeholder.container():
                service = ui_context.get_service("my_module.service")
                result = service.get_live_data()
                if result.success:
                    st.json(result.data)
                    st.caption(f"Last updated: {time.strftime('%H:%M:%S')}")
            
            time.sleep(30)
```

#### Error Handling
```python
def render_main_tab(ui_context):
    try:
        service = ui_context.get_service("my_module.service")
        
        # Service operations with error handling
        result = service.some_operation()
        
        if result.success:
            st.success("Operation successful")
            st.json(result.data)
        else:
            # Display structured error information
            st.error("Operation failed")
            with st.expander("Error Details"):
                st.code(result.error.get('code', 'UNKNOWN_ERROR'))
                st.write(result.error.get('message', 'No error message'))
                if 'details' in result.error:
                    st.json(result.error['details'])
    
    except Exception as e:
        st.error(f"UI Error: {str(e)}")
        logger.exception("UI rendering error")
```

---

## UI Framework Integration

### Service Integration

The UI system integrates with backend services through the UI app context:

```python
def render_main_tab(ui_context):
    # Get backend services
    my_service = ui_context.get_service("my_module.service")
    settings_service = ui_context.get_service("core.settings.service")
    database_service = ui_context.get_service("core.database.service")
    
    # All services return Result objects
    result = my_service.some_operation()
    if result.success:
        # Handle success
        data = result.data
    else:
        # Handle error
        error_info = result.error
```

### Configuration Access

```python
def render_main_tab(ui_context):
    # Access framework configuration
    config = ui_context.config
    
    st.write(f"App Name: {config.APP_NAME}")
    st.write(f"Debug Mode: {config.DEBUG}")
    
    # Access module settings
    settings_service = ui_context.get_service("core.settings.service")
    settings = settings_service.get_typed_settings("my_module", MyModuleSettings)
    
    if settings.success:
        st.json(settings.data.dict())
```

---

## UI Development Guidelines

### Best Practices

**Structure and Organization**
- Use the `register_components()` pattern for all UI elements
- Separate rendering functions for different UI areas
- Keep UI logic separate from business logic
- Use type hints for better code maintainability

**User Experience**
- Provide clear feedback for all user actions
- Use loading indicators for long operations
- Display meaningful error messages
- Implement proper form validation

**Integration**
- Always use the UI app context to access services
- Handle Result objects properly (check `.success` first)
- Log UI errors appropriately
- Test UI components with backend services

**Performance**
- Use `st.cache_data` for expensive computations
- Implement pagination for large datasets
- Avoid unnecessary re-renders with session state
- Use `st.empty()` and `st.rerun()` for dynamic updates

### Common Patterns

**Form Handling**
```python
with st.form("user_input_form"):
    name = st.text_input("Name")
    email = st.text_input("Email")
    
    if st.form_submit_button("Submit"):
        if name and email:
            service = ui_context.get_service("user.service")
            result = service.create_user(name, email)
            
            if result.success:
                st.success("User created successfully!")
            else:
                st.error(f"Failed: {result.error['message']}")
```

**Data Display**
```python
# Tables with actions
service = ui_context.get_service("data.service")
result = service.get_all_items()

if result.success:
    items = result.data
    
    for item in items:
        col1, col2, col3 = st.columns([3, 1, 1])
        
        with col1:
            st.write(item['name'])
        with col2:
            if st.button("Edit", key=f"edit_{item['id']}"):
                # Handle edit
                pass
        with col3:
            if st.button("Delete", key=f"delete_{item['id']}"):
                # Handle delete
                pass
```

---

## Security Considerations

### Default Security Posture

**IMPORTANT**: The framework is configured for security by default:

```bash
# .env configuration (SECURE - localhost only)
HOST=127.0.0.1      # Only accessible from local machine
PORT=8000           # Backend API port  
STREAMLIT_PORT=8501 # UI port
```

**Why This Matters:**
- ✅ **Safe**: Only accessible from the same machine where it's running
- ❌ **Dangerous**: `HOST=0.0.0.0` would expose to entire network
- 🔒 **Best Practice**: Keep localhost-only unless you specifically need network access

### Network Access Warnings

**Never use `HOST=0.0.0.0` unless you understand the risks:**

```bash
# DANGEROUS - Do not use in .env unless you need network access
HOST=0.0.0.0        # Exposes framework to entire network
```

**Risks of network exposure:**
- Anyone on your network can access the framework
- No built-in authentication or access controls
- Potential access to sensitive data and operations
- Could expose database contents and system operations

### Production Deployment

**For Production Use:**
1. **Keep localhost-only** for development and personal use
2. **Add authentication** if network access is needed
3. **Use reverse proxy** (nginx) with SSL/TLS
4. **Implement access controls** at the infrastructure level
5. **Monitor access logs** regularly

**Production Configuration Example:**
```bash
# Production .env (still localhost - use reverse proxy for external access)
HOST=127.0.0.1
PORT=8000
DEBUG=false
LOG_LEVEL=INFO
```

## Deployment and Configuration

### Production Considerations

**Security**
- Framework runs on localhost (127.0.0.1) by default for security
- Network access requires explicit configuration and security measures
- No built-in authentication system - implement via framework modules if needed

**Performance**
- Streamlit apps can be resource-intensive
- Consider using `st.cache_data` for expensive operations
- Monitor memory usage with large datasets

**Logging**
- UI actions are logged to `data/logs/ui.log` and `data/logs/ui_streamlit.log`
- Configure log levels appropriately for production

### Configuration Options

```python
# In your environment or configuration
STREAMLIT_PORT=8501
STREAMLIT_HOST=127.0.0.1
UI_DEBUG=true
```

The Streamlit UI system provides a complete web interface for your framework applications, with automatic module discovery, service integration, and professional UI patterns built-in.
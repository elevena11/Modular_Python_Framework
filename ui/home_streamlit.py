"""
ui/home_streamlit.py
Streamlit implementation of the home tab.
"""

import streamlit as st
import logging

logger = logging.getLogger("ui.home_streamlit")

def render_home(ui_context):
    """Render the Home tab content using Streamlit."""
    # Get the API client for backend info
    api_client = ui_context.get_service("api_client")
    
    # Get app information
    app_title = ui_context.config.get("app_title", "Modular AI Framework")
    app_version = api_client.config.get("app_version", "Unknown")
    
    # Get modules information
    modules = api_client.get_modules()
    
    # Header
    st.title(f"Welcome to {app_title}")
    st.markdown(f"**Version:** {app_version}")
    st.markdown("This is a modular application framework. Modules can be added to extend functionality.")
    
    # Available Modules section
    st.header("Available Modules")
    st.write(f"{len(modules)} modules are loaded:")
    
    # Create columns for module categories
    col1, col2 = st.columns(2)
    
    # Core Modules
    with col1:
        st.subheader("Core Modules")
        core_modules = [m for m in modules if m["id"].startswith("core.")]
        if core_modules:
            for m in core_modules:
                st.markdown(f"- **{m['name']}** (`{m['id']}`) - {m['description']}")
        else:
            st.markdown("*No core modules found*")
        
        # Extension Modules (in same column)
        st.subheader("Extension Modules")
        ext_modules = [m for m in modules if m["id"].startswith("extensions.")]
        if ext_modules:
            for m in ext_modules:
                st.markdown(f"- **{m['name']}** (`{m['id']}`) - {m['description']}")
        else:
            st.markdown("*No extension modules found*")
    
    # Standard Modules
    with col2:
        st.subheader("Standard Modules")
        std_modules = [m for m in modules if m["id"].startswith("standard.")]
        if std_modules:
            for m in std_modules:
                st.markdown(f"- **{m['name']}** (`{m['id']}`) - {m['description']}")
        else:
            st.markdown("*No standard modules found*")
        
        # Other Modules (in same column)
        st.subheader("Other Modules")
        other_modules = [m for m in modules if not (
            m["id"].startswith("core.") or 
            m["id"].startswith("standard.") or 
            m["id"].startswith("extensions.")
        )]
        if other_modules:
            for m in other_modules:
                st.markdown(f"- **{m['name']}** (`{m['id']}`) - {m['description']}")
        else:
            st.markdown("*No other modules found*")
    
    # System Status section
    st.header("System Status")
    st.markdown("Current status information about the application:")
    
    try:
        health_status = "Connected" if api_client.check_connection() else "Disconnected"
        status_color = "green" if health_status == "Connected" else "red"
        
        st.markdown(f"- **Backend API**: :{status_color}[{health_status}]")
        st.markdown(f"- **API Documentation**: [{api_client.base_url}/docs]({api_client.base_url}/docs)")
    except Exception as e:
        st.error(f"Error getting system status: {str(e)}")

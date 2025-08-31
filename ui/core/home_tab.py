"""
ui/core/home_tab.py
Home tab for the UI application - shows welcome message and system information.
"""

import streamlit as st
import logging

logger = logging.getLogger("ui.core.home_tab")

def render_home_tab(ui_context):
    """Render the Home tab content."""
    # Get the API client for backend info
    api_client = ui_context.get_service("api_client")
    
    # Get app information
    app_title = ui_context.config.get("app_title", "Modular AI Framework")
    app_version = api_client.config.get("app_version", "Unknown")
    
    # Get modules information
    modules = api_client.get_modules()
    
    st.markdown(f"""
    # Welcome to {app_title}
    
    **Version:** {app_version}
    
    This is a modular application framework. Modules can be added to extend functionality.
    
    ## Available Modules
    
    {len(modules)} modules are loaded:
    """)
    
    # Show modules in a more organized way
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Core Modules")
        core_modules = [m for m in modules if m["id"].startswith("core.")]
        if core_modules:
            modules_list = "\n".join([f"- **{m['name']}** (`{m['id']}`) - {m['description']}" for m in core_modules])
            st.markdown(modules_list)
        else:
            st.markdown("*No core modules found*")
        
        st.markdown("### Extension Modules")
        ext_modules = [m for m in modules if m["id"].startswith("extensions.")]
        if ext_modules:
            modules_list = "\n".join([f"- **{m['name']}** (`{m['id']}`) - {m['description']}" for m in ext_modules])
            st.markdown(modules_list)
        else:
            st.markdown("*No extension modules found*")
    
    with col2:
        st.markdown("### Standard Modules")
        std_modules = [m for m in modules if m["id"].startswith("standard.")]
        if std_modules:
            modules_list = "\n".join([f"- **{m['name']}** (`{m['id']}`) - {m['description']}" for m in std_modules])
            st.markdown(modules_list)
        else:
            st.markdown("*No standard modules found*")
        
        st.markdown("### Other Modules")
        other_modules = [m for m in modules if not (
            m["id"].startswith("core.") or 
            m["id"].startswith("standard.") or 
            m["id"].startswith("extensions.")
        )]
        if other_modules:
            modules_list = "\n".join([f"- **{m['name']}** (`{m['id']}`) - {m['description']}" for m in other_modules])
            st.markdown(modules_list)
        else:
            st.markdown("*No other modules found*")
    
    # System status section
    st.markdown("""
    ## System Status
    
    Current status information about the application:
    """)
    
    try:
        health_status = "Connected" if api_client.check_connection() else "Disconnected"
        status_color = "green" if health_status == "Connected" else "red"
        
        st.markdown(f"""
        - **Backend API**: :{status_color}[{health_status}]
        - **API URL**: {api_client.base_url}
        """)
    except Exception as e:
        st.error(f"Error getting system status: {str(e)}")
"""
ui/streamlit_app.py
Entry point script for Streamlit UI.
"""

import os
import sys
import logging
import streamlit as st

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import app context and configuration
from ui.core.config import UIConfig
from ui.core.app_context import UIAppContext
from ui.core.module_loader import UIModuleLoader
from ui.home_streamlit import render_home

# Set up logging - use same format as run_ui.py
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(name)s - %(message)s',
    handlers=[
        logging.FileHandler("data/logs/ui_streamlit.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("ui.streamlit_app")

# Initialize app context
config = UIConfig()
config.set("default_ui", "streamlit")
app_context = UIAppContext(config)

# Load UI modules
module_loader = UIModuleLoader(app_context)
module_loader.load_modules()

# Initialize Streamlit app state
if 'initialized' not in st.session_state:
    st.session_state.initialized = True
    st.session_state.app_context = app_context
    st.session_state.current_tab = "Home"
    
    # Get visible tabs
    app_context.ui_config_service.config.update_with_registered_elements()
    st.session_state.visible_tabs = app_context.ui_config_service.get_visible_elements("tab")

# Set page config
st.set_page_config(
    page_title=app_context.config.get("app_title", "Modular AI Framework"),
    layout="wide"
)

# Title removed - using sidebar navigation instead

# Create tab navigation in sidebar
tab_options = ["Home"] + [tab.get("display_name") for tab in st.session_state.visible_tabs]
tab_options.append("UI Configuration")  # Add the config tab at the end

# Debug information in sidebar
with st.sidebar.expander("🔍 Debug Info"):
    st.write(f"Visible tabs count: {len(st.session_state.visible_tabs)}")
    st.write("Registered tabs:")
    for tab in st.session_state.visible_tabs:
        st.write(f"- {tab.get('display_name')} ({tab.get('full_id')})")

selected_tab = st.sidebar.selectbox("Select Tab", tab_options, index=tab_options.index(st.session_state.current_tab))

# Update current tab in session state if changed
if selected_tab != st.session_state.current_tab:
    st.session_state.current_tab = selected_tab
    st.rerun()  # Using the non-experimental function

# Display appropriate tab content
if selected_tab == "Home":
    # Render home tab
    render_home(app_context)
elif selected_tab == "UI Configuration":
    # Import and render UI config tab (Streamlit version)
    from ui.core.ui_config.ui_streamlit import render_config_panel
    render_config_panel(app_context)
else:
    # Find and render the selected module tab
    for tab in st.session_state.visible_tabs:
        if tab.get("display_name") == selected_tab:
            render_fn = tab.get("render_function")
            if render_fn:
                render_fn(app_context)
            else:
                st.warning(f"No render function for tab {tab.get('full_id')}")
            break

# Display framework info in footer
st.sidebar.markdown("---")
# Framework info removed for cleaner UI

"""
ui/core/ui_config/ui_streamlit.py
Streamlit UI component for managing UI element configuration.
"""

import streamlit as st
import logging

logger = logging.getLogger("ui.core.ui_config.ui_streamlit")

def render_config_panel(ui_context):
    """Render the UI configuration panel for Streamlit."""
    st.header("🎛️ UI Configuration")
    
    st.markdown("""
    Configure which UI elements are visible in the user interface.

    **Note:** Changes take effect after restarting the application.
    """)
    
    # Get services
    ui_config_service = ui_context.get_service("ui_config_service")
    
    if not ui_config_service:
        st.error("UI Configuration service not available")
        return
    
    # Get all registered elements - no protection system
    configurable_elements = ui_context.get_all_elements()
    
    if not configurable_elements:
        st.info("No configurable elements found.")
        return
    
    # Group elements by module
    elements_by_module = {}
    for element in configurable_elements:
        module_id = element.get("module_id", "unknown")
        if module_id not in elements_by_module:
            elements_by_module[module_id] = []
        
        # Add visibility info from config
        element_id = element.get("full_id")
        element["visible"] = ui_config_service.config.is_element_visible(element_id)
        
        elements_by_module[module_id].append(element)
    
    # Initialize session state for toggles if not exists
    if 'ui_config_changes' not in st.session_state:
        st.session_state.ui_config_changes = {}
    
    # Create element visibility controls
    st.subheader("Element Visibility Configuration")
    
    changes_made = False
    
    # Create a section for each module
    for module_id, elements in elements_by_module.items():
        st.markdown(f"### Module: `{module_id}`")
        
        # Create a toggle for each element in this module
        for element in elements:
            element_id = element.get("full_id")
            display_name = element.get("display_name", element_id)
            description = element.get("description", "")
            current_visibility = element.get("visible", True)
            
            # Use session state to track changes
            key = f"toggle_{element_id}"
            if key not in st.session_state:
                st.session_state[key] = current_visibility
            
            # Create the toggle with description
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.markdown(f"**{display_name}**")
                if description:
                    st.caption(description)
            
            with col2:
                new_value = st.toggle(
                    "Visible",
                    value=st.session_state[key],
                    key=key,
                    help=f"Toggle visibility for {display_name}"
                )
                
                # Track if this element's visibility changed
                if new_value != current_visibility:
                    st.session_state.ui_config_changes[element_id] = new_value
                    changes_made = True
                elif element_id in st.session_state.ui_config_changes:
                    # If value returned to original, remove from changes
                    if new_value == current_visibility:
                        del st.session_state.ui_config_changes[element_id]
        
        st.markdown("---")
    
    # Save configuration section
    st.subheader("Save Configuration")
    
    if st.session_state.ui_config_changes:
        st.info(f"You have {len(st.session_state.ui_config_changes)} unsaved changes.")
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            if st.button("💾 Save Changes", type="primary"):
                try:
                    # Update the configuration
                    for element_id, visible in st.session_state.ui_config_changes.items():
                        ui_config_service.config.set_element_visibility(element_id, visible)
                    
                    # Clear changes
                    st.session_state.ui_config_changes = {}
                    
                    st.success("Configuration saved successfully! Restart the application for changes to take effect.")
                    st.rerun()
                    
                except Exception as e:
                    logger.error(f"Error saving configuration: {str(e)}")
                    st.error(f"Error saving configuration: {str(e)}")
        
        with col2:
            if st.button("↩️ Reset Changes"):
                # Reset all toggles to original values
                for element_id in st.session_state.ui_config_changes:
                    # Find original value
                    for module_elements in elements_by_module.values():
                        for element in module_elements:
                            if element.get("full_id") == element_id:
                                key = f"toggle_{element_id}"
                                st.session_state[key] = element.get("visible", True)
                                break
                
                # Clear changes
                st.session_state.ui_config_changes = {}
                st.info("Changes reset to original values.")
                st.rerun()
    else:
        st.success("No unsaved changes.")
    
    # Help section
    with st.expander("ℹ️ Help & Information"):
        st.markdown("""
        **How to use:**
        1. Use the toggles above to show/hide UI elements
        2. Click "Save Changes" to persist your configuration
        3. Restart the application to see the changes take effect

        **Module Information:**
        - Each module can contribute multiple UI elements (tabs, buttons, etc.)
        - Disabling an element will hide it from the interface
        - The UI Configuration tab itself cannot be hidden to ensure you can always restore elements
        """)
        
        # Show current configuration summary
        st.markdown("**Current Element Status:**")
        status_data = []
        for module_id, elements in elements_by_module.items():
            for element in elements:
                element_id = element.get("full_id")
                current_status = "Visible" if st.session_state.get(f"toggle_{element_id}", element.get("visible", True)) else "Hidden"
                status_data.append({
                    "Module": module_id,
                    "Element": element.get("display_name", element_id),
                    "Status": current_status
                })
        
        if status_data:
            import pandas as pd
            df = pd.DataFrame(status_data)
            st.dataframe(df, width='stretch')
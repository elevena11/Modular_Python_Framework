"""
ui/core/ui_config/ui.py
UI component for managing UI element configuration.
"""

import streamlit as st
import logging

logger = logging.getLogger("ui.core.ui_config.ui")

def render_config_panel(ui_context):
    """Render the UI configuration panel."""
    # Get services
    ui_config_service = ui_context.get_service("ui_config_service")
    
    st.markdown("""
    # UI Configuration
    
    Configure which UI elements are visible in the user interface. 
    Protected elements are always enabled and not shown here.
    
    Changes take effect after restarting the application.
    """)
    
    # Get all registered elements
    all_elements = ui_context.get_all_elements()
    
    # Filter out protected elements
    from ui.core.ui_config.constants import PROTECTED_ELEMENTS
    configurable_elements = [e for e in all_elements if e.get("full_id") not in PROTECTED_ELEMENTS]
    
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
    
    if not configurable_elements:
        st.markdown("No configurable elements found.")
    else:
        # Create a section for each module
        for module_id, elements in elements_by_module.items():
            with st.expander(f"Module: {module_id}", expanded=True):
                # Create a toggle for each element in this module
                for element in elements:
                    element_id = element.get("full_id")
                    display_name = element.get("display_name", element_id)
                    description = element.get("description", "")
                    is_visible = element.get("visible", True)
                    
                    # Create a checkbox for each element
                    new_visibility = st.checkbox(
                        label=display_name,
                        value=is_visible,
                        help=description,
                        key=f"visibility_{element_id}"
                    )
                    
                    # Update configuration if changed
                    if new_visibility != is_visible:
                        ui_config_service.config.set_element_visibility(element_id, new_visibility)
    
    # Save button
    if st.button("Save Configuration"):
        try:
            st.success("Configuration saved successfully. Restart the application for changes to take effect.")
        except Exception as e:
            logger.error(f"Error saving configuration: {str(e)}")
            st.error(f"Error: {str(e)}")
    
    # Help text with the protected elements
    protected_elements_str = ", ".join([e.split(".")[-1] for e in PROTECTED_ELEMENTS])
    st.info(f"""
    **Note:** Changes take effect after restarting the application.
    
    Protected elements ({protected_elements_str}) are always enabled and not shown here.
    """)
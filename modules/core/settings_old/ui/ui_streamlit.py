"""
modules/core/settings/ui/ui_streamlit.py
Streamlit UI implementation for the settings module with type consistency fixes.
"""

import logging
import streamlit as st
import requests
from typing import Dict, List, Any, Optional, Tuple

from .services import (
    load_all_settings, 
    load_settings_metadata,
    update_module_setting,
    get_module_name,
    group_settings_by_category
)

logger = logging.getLogger("modular.core.settings.ui.streamlit")

def register_components(ui_context):
    """Register UI components for the settings module."""
    logger.info("Registering Settings UI components with Streamlit")
    
    # Register the Settings tab using the new element registration pattern
    ui_context.register_element({
        "type": "tab",
        "id": "settings_manager",
        "display_name": "Settings",
        "description": "Configure application settings and connection parameters",
        "priority": 15,
        "render_function": render_settings_ui
    })
    
    logger.info("Settings UI components registered")

def render_settings_ui(ui_context):
    """Render the Settings UI components using Streamlit."""
    # Get the client config from backend API
    client_config = ui_context.backend_api.config
    base_url = ui_context.backend_api.base_url
    
    # Client Configuration section
    st.header("Client Configuration")
    st.write("These settings are stored on your machine and control how the UI connects to the backend.")
    
    # API URL input
    api_url = st.text_input(
        "API Base URL",
        value=client_config.get("api_base_url"),
        help="URL for the backend API server (requires UI restart)"
    )
    
    # Save client config button
    if st.button("Save Client Configuration"):
        if not api_url:
            st.error("API URL cannot be empty")
        else:
            try:
                client_config.set("api_base_url", api_url)
                st.success("Client configuration saved. Restart the UI for changes to take effect.")
            except Exception as e:
                st.error(f"Error saving client configuration: {str(e)}")
    
    # Server Settings section
    st.header("Server Settings")
    if st.button("Refresh Server Settings"):
        st.info("Settings refreshed. Reload the page to see updated settings.")
    
    # Load all settings and metadata
    all_settings = load_all_settings(base_url)
    all_metadata = load_settings_metadata(base_url)
    
    # Extract UI metadata
    ui_metadata = all_metadata.get("ui", {})
    
    if not all_settings:
        st.warning("Unable to load settings. Make sure the application is running.")
    else:
        # Group settings by module
        for module_id, module_settings in all_settings.items():
            # Skip modules with no settings
            if not module_settings:
                continue
            
            # Get module name and UI metadata
            module_name = get_module_name(module_id)
            module_ui_metadata = ui_metadata.get(module_id, {})
            
            # Create expander for each module
            with st.expander(module_name):
                st.subheader(f"{module_name} Settings")
                
                # Track setting values for saving
                setting_values = {}
                
                # Group settings by category
                settings_by_category = group_settings_by_category(module_settings, module_ui_metadata)
                
                # Create settings components for each category
                for category, category_settings in settings_by_category.items():
                    st.markdown(f"### {category}")
                    
                    # Create components for each setting
                    for setting_name, setting_info in category_settings.items():
                        # Extract setting properties (handle both flat and nested structures like Gradio)
                        label = setting_name.replace("_", " ").title()
                        
                        # Handle different setting info structures like Gradio does
                        if isinstance(setting_info, dict) and "value" in setting_info:
                            # Regular case: setting_info has a value key
                            value = setting_info["value"]
                            description = setting_info.get("description", "")
                            setting_type = setting_info.get("type", "string")
                        elif isinstance(setting_info, dict) and "type" in setting_info and "default" in setting_info:
                            # Raw settings definition (happens in Global settings)
                            value = setting_info.get("default", "")
                            description = setting_info.get("description", "")
                            setting_type = setting_info.get("type", "string")
                        else:
                            # Direct value case
                            value = setting_info
                            description = ""
                            # Determine type from value
                            if isinstance(value, bool):
                                setting_type = "bool"
                            elif isinstance(value, int):
                                setting_type = "int"
                            elif isinstance(value, float):
                                setting_type = "float"
                            elif isinstance(value, list):
                                setting_type = "list"
                            else:
                                setting_type = "string"
                        
                        # CRITICAL FIX: Check if value is a corrupted string representation of a dictionary
                        if isinstance(value, str) and value.startswith("{'value':") and "'label':" in value:
                            st.error(f"CORRUPTED VALUE DETECTED for {setting_name}: {value}")
                            # Try to extract the actual value from the string representation
                            try:
                                import ast
                                dict_value = ast.literal_eval(value)
                                if isinstance(dict_value, dict) and "value" in dict_value:
                                    value = dict_value["value"]
                                    st.success(f"FIXED: Extracted value '{value}' from corrupted data")
                                else:
                                    st.error(f"Could not extract value from corrupted data: {value}")
                            except Exception as e:
                                st.error(f"Failed to parse corrupted value: {e}")
                                # Keep the original corrupted value for now
                        
                        # Check for dropdown options like Gradio does
                        has_options = False
                        options = []
                        
                        if isinstance(setting_info, dict):
                            # First try "enum" for validation schema options
                            if "enum" in setting_info:
                                has_options = True
                                options = setting_info["enum"]
                            # Then check UI metadata options
                            elif "options" in setting_info:
                                has_options = True
                                options = setting_info["options"]
                        
                        is_select_type = setting_type in ["select", "dropdown"] or has_options
                        
                        # Full label with description
                        full_label = f"{label}" + (f" - {description}" if description else "")
                        
                        # Create appropriate component based on type
                        if setting_type == "bool":
                            setting_values[setting_name] = st.checkbox(
                                full_label, 
                                value=value,
                                key=f"{module_id}_{setting_name}_checkbox"
                            )
                        elif setting_type == "int":
                            # Ensure all numeric values are integers for consistency
                            min_val = setting_info.get("min")
                            max_val = setting_info.get("max")
                            step_val = 1
                            
                            # Convert to int if needed
                            if min_val is not None:
                                min_val = int(min_val)
                            if max_val is not None:
                                max_val = int(max_val)
                            
                            # Make sure value is an integer
                            int_value = int(value) if value is not None else 0
                            
                            setting_values[setting_name] = st.number_input(
                                full_label,
                                value=int_value,
                                step=step_val,
                                min_value=min_val,
                                max_value=max_val,
                                key=f"{module_id}_{setting_name}_int"
                            )
                        elif setting_type == "float":
                            # Ensure all numeric values are floats for consistency
                            min_val = setting_info.get("min")
                            max_val = setting_info.get("max")
                            step_val = 0.1
                            
                            # Convert to float if needed
                            if min_val is not None:
                                min_val = float(min_val)
                            if max_val is not None:
                                max_val = float(max_val)
                            
                            # Make sure value is a float
                            float_value = float(value) if value is not None else 0.0
                            
                            setting_values[setting_name] = st.number_input(
                                full_label,
                                value=float_value,
                                step=step_val,
                                min_value=min_val,
                                max_value=max_val,
                                format="%.2f",
                                key=f"{module_id}_{setting_name}_float"
                            )
                        elif is_select_type:
                            
                            # Handle options that are dictionaries with value/label
                            if options and isinstance(options[0], dict):
                                option_values = [opt["value"] for opt in options]
                                option_labels = [opt["label"] for opt in options]
                                
                                # Ensure current value is in option_values to prevent index errors
                                if value in option_values:
                                    default_index = option_values.index(value)
                                else:
                                    st.warning(f"Current value '{value}' for {setting_name} is not in available options. Using first option.")
                                    default_index = 0
                                
                                selected_value = st.selectbox(
                                    full_label,
                                    options=option_values,
                                    format_func=lambda x: option_labels[option_values.index(x)] if x in option_values else x,
                                    index=default_index,
                                    key=f"{module_id}_{setting_name}_select"
                                )
                                
                                # CRITICAL FIX: Ensure we only save the string value, never the full dict
                                if isinstance(selected_value, dict):
                                    # If somehow a dict was returned, extract the value
                                    if "value" in selected_value:
                                        setting_values[setting_name] = selected_value["value"]
                                        st.error(f"WARNING: Dictionary detected for {setting_name}, extracting value: {selected_value['value']}")
                                    else:
                                        # Fall back to string representation
                                        setting_values[setting_name] = str(selected_value)
                                        st.error(f"WARNING: Invalid dictionary for {setting_name}, using string: {str(selected_value)}")
                                else:
                                    # Normal case: selected_value should be a string
                                    setting_values[setting_name] = selected_value
                            else:
                                # Handle simple string options
                                default_index = options.index(value) if value in options else 0
                                setting_values[setting_name] = st.selectbox(
                                    full_label,
                                    options=options,
                                    index=default_index,
                                    key=f"{module_id}_{setting_name}_select"
                                )
                        elif setting_type == "list":
                            # Convert list to multiline string for editing
                            list_value = value or []
                            if isinstance(list_value, list):
                                text_value = "\n".join(str(item) for item in list_value)
                            else:
                                text_value = str(list_value)
                                
                            input_value = st.text_area(
                                full_label,
                                value=text_value,
                                height=150,
                                key=f"{module_id}_{setting_name}_list"
                            )
                            
                            # Parse back to list
                            setting_values[setting_name] = [line.strip() for line in input_value.split("\n") if line.strip()]
                        elif isinstance(value, (dict, list)):
                            # Handle complex objects - likely missing UI metadata
                            if isinstance(value, dict) and len(value) > 0:
                                st.warning(f"⚠️ **{setting_name}**: Complex object without UI metadata")
                                st.caption("This setting needs proper UI metadata for user editing. See docs/development-tools/settings-structure-standard.md")
                                with st.expander(f"View {setting_name} raw data (read-only)", expanded=False):
                                    st.json(value)
                            elif isinstance(value, list) and len(value) > 0:
                                st.warning(f"⚠️ **{setting_name}**: List without UI metadata")
                                st.caption("This setting needs proper UI metadata for user editing.")
                                with st.expander(f"View {setting_name} raw data (read-only)", expanded=False):
                                    st.json(value)
                            else:
                                st.info(f"🔧 **{setting_name}**: Empty complex setting")
                            # Don't include in setting_values to prevent accidental modification
                        else:  # Default to text input for simple values
                            setting_values[setting_name] = st.text_input(
                                full_label,
                                value=str(value) if value is not None else "",
                                key=f"{module_id}_{setting_name}_text"
                            )
                
                # Save button for this module
                if st.button(
                    f"Save {module_name} Settings", 
                    key=f"{module_id}_save_button"
                ):
                    results = []
                    for setting_name, value in setting_values.items():
                        try:
                            response = update_module_setting(base_url, module_id, setting_name, value)
                            if response.get("success"):
                                results.append(f"[SUCCESS] {setting_name}")
                            else:
                                results.append(f"[ERROR] {setting_name}: {response.get('message', 'Unknown error')}")
                        except Exception as e:
                            results.append(f"[ERROR] {setting_name}: {str(e)}")
                    
                    # Show results
                    if all(r.startswith("[SUCCESS]") for r in results):
                        st.success("All settings updated successfully")
                    else:
                        # Filter to just the errors
                        errors = [r for r in results if r.startswith("[ERROR]")]
                        st.error("Some settings failed to update:\n" + "\n".join(errors))

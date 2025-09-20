"""
modules/core/settings/ui/ui_streamlit.py
Streamlit UI implementation for the new Pydantic-based settings system.
"""

import logging
import streamlit as st
import requests
import json
from typing import Dict, List, Any, Optional
from datetime import datetime

from .services import SettingsUIService

logger = logging.getLogger("modules.core.settings.ui.streamlit")

def register_components(ui_context):
    """Register UI components for the settings module."""
    logger.info("Registering Settings UI components with Streamlit")
    
    # Register the Settings tab
    ui_context.register_element({
        "type": "tab",
        "id": "settings_manager",
        "display_name": "Settings",
        "description": "Configure application settings and user preferences",
        "priority": 15,
        "render_function": render_settings_ui
    })
    
    logger.info("Settings UI components registered")

def render_settings_ui(ui_context):
    """Render the Settings UI using Streamlit - mimics old settings UI behavior."""
    st.header("⚙️ Framework Settings")
    st.markdown("Configure framework settings. Changes are saved to user preferences and override baseline values.")
    
    # Get API client
    api_client = ui_context.get_service("api_client")
    if not api_client:
        st.error("API client not available")
        return
    
    base_url = api_client.base_url
    
    # Add refresh button
    if st.button("Refresh Settings"):
        st.info("Settings refreshed. Reload the page to see updated settings.")
    
    # Load all settings like the old UI
    render_all_module_settings(base_url)

def render_all_module_settings(base_url: str):
    """Render all module settings in expandable sections like the old UI."""
    
    # Load all settings from API
    try:
        all_settings_response = requests.get(f"{base_url}/api/v1/core/settings/settings")
        if all_settings_response.status_code != 200:
            st.error(f"Failed to load settings: {all_settings_response.status_code}")
            return
        
        data = all_settings_response.json()
        all_settings = data.get("modules", {})
        
        if not all_settings:
            st.warning("No settings found. Make sure the application is running.")
            return
        
        st.info(f"Found {data.get('total_modules', 0)} modules with {data.get('total_user_overrides', 0)} user overrides")
        
        # Group settings by module like the old UI
        for module_id, module_data in all_settings.items():
            current_settings = module_data.get("settings", {})
            baseline_count = module_data.get("baseline_count", 0)
            user_overrides_count = module_data.get("user_overrides_count", 0)
            
            # Skip modules with no settings
            if not current_settings:
                continue
            
            # Get module name
            module_name = format_module_name(module_id)
            
            # Create expander for each module like the old UI
            with st.expander(f"{module_name} ({baseline_count} baseline, {user_overrides_count} overrides)", expanded=False):
                st.subheader(f"{module_name} Settings")
                
                # Track setting values for saving
                setting_values = {}
                
                # Group settings by category (simplified for now)
                settings_by_category = group_settings_by_category(current_settings)
                
                # Create settings components for each category
                for category, category_settings in settings_by_category.items():
                    if category != "General":
                        st.markdown(f"### {category}")
                    
                    # Create components for each setting
                    for setting_name, setting_value in category_settings.items():
                        # Create input component and track value
                        new_value = create_setting_input_component(
                            module_id, setting_name, setting_value
                        )
                        setting_values[setting_name] = new_value
                
                # Save button for this module
                if st.button(f"Save {module_name} Settings", key=f"{module_id}_save_button"):
                    save_module_settings(base_url, module_id, setting_values, current_settings)
    
    except Exception as e:
        st.error(f"Error loading settings: {e}")

def group_settings_by_category(settings: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """Group settings by category. For now, put everything in General."""
    return {"General": settings}

def create_setting_input_component(module_id: str, setting_name: str, current_value: Any) -> Any:
    """Create appropriate Streamlit input component for a setting."""
    # Format label
    label = setting_name.replace("_", " ").title()
    key = f"{module_id}_{setting_name}"
    
    # Determine type and create appropriate input
    if isinstance(current_value, bool):
        return st.checkbox(
            label,
            value=current_value,
            key=f"{key}_checkbox"
        )
    elif isinstance(current_value, int):
        return st.number_input(
            label,
            value=current_value,
            step=1,
            key=f"{key}_int"
        )
    elif isinstance(current_value, float):
        return st.number_input(
            label,
            value=current_value,
            step=0.1,
            format="%.3f",
            key=f"{key}_float"
        )
    elif isinstance(current_value, list):
        # Convert list to multiline string for editing
        text_value = "\n".join(str(item) for item in current_value)
        input_value = st.text_area(
            label,
            value=text_value,
            height=100,
            key=f"{key}_list"
        )
        # Parse back to list
        return [line.strip() for line in input_value.split("\n") if line.strip()]
    elif isinstance(current_value, dict):
        # Show dict as read-only for now
        st.markdown(f"**{label}** (complex object - read only):")
        st.json(current_value)
        return current_value
    else:
        # Default to text input
        return st.text_input(
            label,
            value=str(current_value) if current_value is not None else "",
            key=f"{key}_text"
        )

def save_module_settings(base_url: str, module_id: str, setting_values: Dict[str, Any], original_settings: Dict[str, Any]):
    """Save changed settings to user preferences."""
    results = []
    changes_made = 0
    
    for setting_name, new_value in setting_values.items():
        original_value = original_settings.get(setting_name)
        
        # Only save if value actually changed
        if new_value != original_value:
            try:
                result = SettingsUIService.set_user_preference(base_url, module_id, setting_name, new_value)
                if result.get("success"):
                    results.append(f"✅ {setting_name}: {original_value} → {new_value}")
                    changes_made += 1
                else:
                    results.append(f"❌ {setting_name}: {result.get('error', 'Unknown error')}")
            except Exception as e:
                results.append(f"❌ {setting_name}: {str(e)}")
    
    # Show results
    if changes_made == 0:
        st.info("No changes detected.")
    elif all(r.startswith("✅") for r in results):
        st.success(f"Successfully saved {changes_made} setting(s):")
        for result in results:
            st.write(result)
        st.info("Settings saved to user preferences. Refresh to see updated values.")
    else:
        st.warning("Some settings failed to save:")
        for result in results:
            st.write(result)





def format_module_name(module_id: str) -> str:
    """Format module ID into a readable name."""
    parts = module_id.split(".")
    return " ".join(part.capitalize() for part in parts)

def format_setting_name(setting_key: str) -> str:
    """Format setting key into a readable name."""
    return setting_key.replace("_", " ").title()
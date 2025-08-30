"""
Settings module UI using the new element registration pattern.
Updated for Gradio 5.20.0.
"""

import logging
import gradio as gr
import requests

logger = logging.getLogger("modular.core.settings")

def register_components(ui_context):
    """Register UI components for the settings module."""
    logger.info("Registering Settings UI components")
    
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
    """Render the Settings UI components."""
    # Get the client config from backend API
    client_config = ui_context.backend_api.config
    base_url = ui_context.backend_api.base_url
    
    with gr.Column():
        # Add client configuration accordion
        with gr.Accordion("Client Configuration", open=False):
            gr.Markdown("## Local Connection Settings")
            gr.Markdown("These settings are stored on your machine and control how the UI connects to the backend.")
            
            # API URL input
            api_url_input = gr.Textbox(
                label="API Base URL",
                value=client_config.get("api_base_url"),
                info="URL for the backend API server (requires UI restart)",
            )
            
            # Save button for client config
            save_client_config_btn = gr.Button("Save Client Configuration")
            client_config_status = gr.Textbox(label="Status", interactive=False)
            
            # Save client config handler
            def save_client_config(api_url):
                if not api_url:
                    return "API URL cannot be empty"
                
                try:
                    client_config.set("api_base_url", api_url)
                    return "Client configuration saved. Restart the UI for changes to take effect."
                except Exception as e:
                    return f"Error saving client configuration: {str(e)}"
            
            save_client_config_btn.click(
                fn=save_client_config,
                inputs=[api_url_input],
                outputs=[client_config_status]
            )
        
        # Add a refresh button for server settings
        refresh_btn = gr.Button("Refresh Server Settings")
        status_output = gr.Textbox(label="Status", interactive=False)
        
        # Load all settings
        all_settings = load_all_settings(ui_context.backend_api)
        
        if not all_settings:
            gr.Markdown("# Settings\n\nUnable to load settings. Make sure the application is running.")
        else:
            # Group settings by module using accordions
            for module_id, module_settings in all_settings.items():
                # Skip modules with no settings
                if not module_settings:
                    continue
                
                # Get module name
                module_name = get_module_name(module_id)
                
                # Create accordion for each module
                with gr.Accordion(module_name, open=False):
                    gr.Markdown(f"## {module_name} Settings")
                    
                    # Create a list to hold components for this module
                    module_components = []
                    module_setting_names = []
                    
                    # Group settings by category
                    settings_by_category = group_settings_by_category(module_settings)
                    
                    # Create settings components for each category
                    for category, category_settings in settings_by_category.items():
                        gr.Markdown(f"### {category}")
                        
                        # Create components for each setting
                        for setting_name, setting_info in category_settings.items():
                            # Create appropriate component based on type
                            component = create_setting_component(
                                module_id,
                                setting_name,
                                setting_info
                            )
                            module_components.append(component)
                            module_setting_names.append(setting_name)
                    
                    # Add a save button for this module
                    save_btn = gr.Button(f"Save {module_name} Settings")
                    
                    # Create a closure to capture module_id and setting_names
                    def create_save_fn(mod_id, setting_names):
                        def save_settings(*values):
                            return update_module_settings(ui_context.backend_api, mod_id, setting_names, values)
                        return save_settings
                    
                    # Register event handler
                    save_btn.click(
                        fn=create_save_fn(module_id, module_setting_names),
                        inputs=module_components,
                        outputs=status_output
                    )
            
            def refresh_settings():
                """Simply returns a message - UI refresh requires page reload."""
                return "Settings refreshed. Reload the page to see updated settings."
            
            refresh_btn.click(
                fn=refresh_settings,
                inputs=[],
                outputs=status_output
            )

def load_all_settings(backend_api=None):
    """Load all settings from the API."""
    try:
        # Get base URL from backend_api if available, otherwise use default
        base_url = backend_api.base_url if backend_api else "http://localhost:8000"
        
        response = requests.get(f"{base_url}/api/v1/settings/")
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"Error loading settings: {response.text}")
            return {}
    except Exception as e:
        logger.error(f"Error loading settings: {str(e)}")
        return {}

def get_module_name(module_id):
    """Get a friendly name for a module ID."""
    # Convert from "core.database" to "Core Database"
    parts = module_id.split(".")
    return " ".join(part.capitalize() for part in parts)

def group_settings_by_category(module_settings):
    """Group settings by category."""
    categories = {}
    
    for setting_name, setting_info in module_settings.items():
        # Get category, default to "General"
        category = setting_info.get("category", "General")
        
        if category not in categories:
            categories[category] = {}
            
        categories[category][setting_name] = setting_info
    
    return categories

def create_setting_component(module_id, setting_name, setting_info):
    """Create a Gradio component for a setting based on its type."""
    label = setting_name.replace("_", " ").title()
    description = setting_info.get("description", "")
    value = setting_info.get("value", setting_info.get("default", ""))
    setting_type = setting_info.get("type", "string")
    
    # Add the description as a label suffix
    full_label = f"{label}" + (f" - {description}" if description else "")
    
    if setting_type == "boolean":
        return gr.Checkbox(
            label=full_label,
            value=value
        )
    elif setting_type == "integer":
        return gr.Number(
            label=full_label,
            value=value,
            precision=0,
            minimum=setting_info.get("min"),
            maximum=setting_info.get("max")
        )
    elif setting_type == "float":
        return gr.Number(
            label=full_label,
            value=value,
            minimum=setting_info.get("min"),
            maximum=setting_info.get("max")
        )
    elif setting_type == "string" and "options" in setting_info:
        return gr.Dropdown(
            label=full_label,
            value=value,
            choices=setting_info["options"]
        )
    else:  # Default to textbox
        return gr.Textbox(
            label=full_label,
            value=value
        )

def update_module_settings(backend_api, module_id, setting_names, values):
    """Update settings for a module."""
    results = []
    
    # Get base URL
    base_url = backend_api.base_url if backend_api else "http://localhost:8000"
    
    for i, setting_name in enumerate(setting_names):
        # Get the value for this setting
        value = values[i]
        
        # Update the setting
        try:
            response = requests.put(
                f"{base_url}/api/v1/settings/{module_id}/{setting_name}",
                json={"value": value}
            )
            
            if response.status_code == 200:
                results.append(f"✅ {setting_name}")
            else:
                results.append(f"❌ {setting_name}: {response.text}")
        except Exception as e:
            results.append(f"❌ {setting_name}: {str(e)}")
    
    # Format the result message
    if all(r.startswith("✅") for r in results):
        return f"All settings updated successfully"
    else:
        # Filter to just the errors
        errors = [r for r in results if r.startswith("❌")]
        return f"Some settings failed to update:\n" + "\n".join(errors)
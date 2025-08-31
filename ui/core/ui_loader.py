"""
ui/core/ui_loader.py
Dynamic loader for UI frameworks.
"""

import logging
import importlib
from typing import Dict, Any, Optional

logger = logging.getLogger("ui.ui_loader")

# Supported UI frameworks
SUPPORTED_FRAMEWORKS = ["streamlit"]

def load_ui_framework(framework_name: str = "streamlit"):
    """
    Load the specified UI framework.
    
    Args:
        framework_name: Name of the UI framework to load (default: "streamlit")
        
    Returns:
        The UI framework module if found, None otherwise
    """
    # Map short codes to full names
    framework_map = {
        "st": "streamlit",
        "streamlit": "streamlit"
    }
    
    # Normalize framework name
    short_name = framework_name.lower()
    if short_name in framework_map:
        framework_name = framework_map[short_name]
    else:
        logger.warning(f"Unsupported UI framework: {framework_name}, defaulting to streamlit")
        framework_name = "streamlit"
    
    # Validate the framework is supported
    if framework_name not in SUPPORTED_FRAMEWORKS:
        logger.warning(f"Unsupported UI framework: {framework_name}. Defaulting to streamlit.")
        framework_name = "streamlit"
    
    try:
        # Try to import the appropriate UI module
        # For example, if framework_name is "streamlit", import "ui.ui_streamlit"
        module_path = f"ui.ui_{framework_name}"
        ui_module = importlib.import_module(module_path)
        logger.info(f"Successfully loaded UI framework: {framework_name}")
        return ui_module
    except ImportError as e:
        logger.error(f"Failed to load UI framework '{framework_name}': {str(e)}")
        return None

def get_framework_from_config(ui_config: Dict[str, Any]) -> str:
    """
    Get the UI framework name from configuration.
    
    Args:
        ui_config: UI configuration dictionary
        
    Returns:
        Framework name (defaults to "streamlit")
    """
    # Get the framework name from config, default to "streamlit"
    return ui_config.get("default_ui", "streamlit")

def load_ui_for_module(module_name: str, framework_name: str = "streamlit") -> Optional[Any]:
    """
    Load the UI implementation for a specific module.
    
    Args:
        module_name: Name of the module (e.g., "core.trace_logger")
        framework_name: Name of the UI framework (default: "streamlit")
        
    Returns:
        The module's UI implementation if found, None otherwise
    """
    # Convert module name to import path
    # e.g., "core.trace_logger" -> "modules.core.trace_logger.ui.ui_streamlit"
    module_parts = module_name.split(".")
    
    if len(module_parts) < 2:
        logger.error(f"Invalid module name format: {module_name}")
        return None
    
    try:
        # Construct import path
        import_path = f"modules.{module_parts[0]}.{module_parts[1]}.ui.ui_{framework_name}"
        
        # Try to import the module
        ui_module = importlib.import_module(import_path)
        logger.info(f"Loaded UI for module {module_name} using framework {framework_name}")
        return ui_module
    except ImportError as e:
        logger.warning(f"Failed to load UI for module {module_name} using framework {framework_name}: {str(e)}")
        return None

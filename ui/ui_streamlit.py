"""
ui/ui_streamlit.py
Streamlit implementation of the UI framework.
"""

import logging
import subprocess
import os
import sys
from typing import Dict, List, Any

logger = logging.getLogger("ui.ui_streamlit")

def build_and_launch_ui(app_context):
    """
    Build and launch the Streamlit UI.
    
    Args:
        app_context: The application context
    """
    logger.info("Preparing to launch Streamlit UI")
    
    # Get configuration
    app_title = app_context.config.get("app_title", "Modular AI Framework")
    
    # Path to streamlit app script
    streamlit_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "streamlit_app.py")
    
    # Check if the script exists
    if not os.path.exists(streamlit_script):
        logger.error(f"Streamlit app script not found: {streamlit_script}")
        print(f"ERROR: Streamlit app script not found: {streamlit_script}")
        return
    
    # Check if streamlit command is available
    try:
        # First try to run the app using the streamlit command
        cmd = [sys.executable, "-m", "streamlit", "run", streamlit_script]
        logger.info(f"Launching Streamlit with command: {' '.join(cmd)}")
        
        # Print instructions to the user
        print(f"\n{'=' * 80}")
        print(f"Launching {app_title} with Streamlit")
        print(f"{'=' * 80}")
        print("\nIf the browser doesn't open automatically, you can access the UI at:")
        print("http://localhost:8501\n")
        print("To manually launch the Streamlit UI, run this command:")
        print(f"streamlit run {streamlit_script}")
        print(f"{'=' * 80}\n")
        
        # Launch the process
        process = subprocess.Popen(cmd)
        
        # Wait for the process to complete
        process.wait()
        
    except Exception as e:
        logger.error(f"Error launching Streamlit: {str(e)}")
        print(f"ERROR: Failed to launch Streamlit UI: {str(e)}")
        print("\nTo manually launch the Streamlit UI, run this command:")
        print(f"streamlit run {streamlit_script}")

def register_component(ui_context, element_data):
    """
    Register a UI component.
    
    Args:
        ui_context: The UI context
        element_data: Component metadata
    
    Returns:
        True if registration was successful, False otherwise
    """
    return ui_context.register_element(element_data)

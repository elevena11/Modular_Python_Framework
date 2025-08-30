# run_ui.py - UI application entry point
import os
import sys
import logging
import argparse

# Add the current directory to the path so imports work correctly
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ui.core.config import UIConfig
from ui.core.app_context import UIAppContext
from ui.core.module_loader import UIModuleLoader
from ui.core.ui_loader import load_ui_framework, get_framework_from_config

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(name)s - %(message)s',
    handlers=[
        logging.FileHandler("data/logs/ui.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("ui_app")

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Run the Modular AI Framework UI")
    parser.add_argument('--ui', '-u', dest='ui_framework', 
                      choices=['gradio', 'streamlit'], 
                      help='Specify the UI framework to use (default: from config)')
    return parser.parse_args()

def main():
    """Main entry point for the UI application."""
    try:
        logger.info("Starting UI application")
        
        # Parse command line arguments
        args = parse_args()
        
        # Initialize configuration
        config = UIConfig()
        
        # Determine which UI framework to use
        ui_framework = args.ui_framework if args.ui_framework else get_framework_from_config(config.config)
        logger.info(f"Using UI framework: {ui_framework}")
        
        # Update the config with the selected framework to ensure it's used consistently
        if ui_framework != config.get("default_ui"):
            config.set("default_ui", ui_framework)
            logger.info(f"Updated default UI framework in config to: {ui_framework}")
        
        # Load the UI framework
        ui_module = load_ui_framework(ui_framework)
        if not ui_module:
            logger.error(f"Failed to load UI framework: {ui_framework}")
            return
        
        # Create application context
        app_context = UIAppContext(config)
        
        # Load UI modules
        module_loader = UIModuleLoader(app_context)
        module_loader.load_modules()
        
        # Build and launch UI using the loaded framework
        if hasattr(ui_module, 'build_and_launch_ui'):
            ui_module.build_and_launch_ui(app_context)
        else:
            logger.error(f"UI framework module {ui_framework} does not have build_and_launch_ui function")
            logger.info("Falling back to app_context.build_and_launch_ui()")
            app_context.build_and_launch_ui()
            
    except KeyboardInterrupt:
        print("\n  Stopping...")
        logger.info("UI application stopped by user (Ctrl+C)")
    except Exception as e:
        logger.error(f"UI application failed: {e}")
        raise
    finally:
        logger.info("UI application stopped")

if __name__ == "__main__":
    main()

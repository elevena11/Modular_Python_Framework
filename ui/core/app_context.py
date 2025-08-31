"""
ui/core/app_context.py
Application context for the UI application.
"""

import logging
import importlib
from typing import Dict, List, Any, Optional

# Import the UI config service
from ui.core.ui_config import UIConfigService
from ui.core.ui_loader import load_ui_framework, get_framework_from_config

logger = logging.getLogger("ui.core.app_context")

class UIAppContext:
    """Context for the UI application."""
    
    def __init__(self, config):
        """Initialize with configuration."""
        self.config = config
        self.logger = logging.getLogger("ui.app_context")
        self.services = {}
        self.current_module_id = None
        
        # Initialize services
        self._initialize_services()
    
    def _initialize_services(self):
        """Initialize required services."""
        # Initialize UI config service first (always needed)
        try:
            self.ui_config_service = UIConfigService(self)
            self.register_service("ui_config_service", self.ui_config_service)
            self.logger.info("UI configuration service initialized")
        except Exception as e:
            self.logger.error(f"Error initializing UI config service: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
        
        # Initialize database connection
        try:
            from modules.core.database.ui.connection import initialize_db_connection
            self.db_connection = initialize_db_connection(self.config.get("database_url"))
            self.logger.info("Database connection initialized")
        except Exception as e:
            self.logger.warning(f"Database connection failed: {str(e)}")
            self.db_connection = None
            
        # Initialize API client
        try:
            from ui.services.api_client import APIClient
            api_client = APIClient(self.config.get("api_base_url"))
            self.register_service("api_client", api_client)
            self.logger.info("API client initialized")
        except Exception as e:
            self.logger.error(f"Error initializing API client: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
    
    @property
    def backend_api(self):
        """Compatibility property for old UI components."""
        return self.get_service("api_client")
    
    def register_service(self, name: str, service):
        """Register a service for use by modules."""
        self.services[name] = service
        return True
    
    def get_service(self, name: str):
        """Get a registered service."""
        return self.services.get(name)
    
    def register_element(self, element_data: Dict[str, Any]):
        """Register a UI element."""
        return self.ui_config_service.register_element(element_data)
    
    def get_element(self, full_id: str):
        """Get an element by its full ID."""
        return self.ui_config_service.registry.get_element(full_id)
        
    def get_elements_by_type(self, element_type: str):
        """Get all elements of a specific type."""
        return self.ui_config_service.registry.get_elements_by_type(element_type)
    
    def get_all_elements(self):
        """Get all registered elements."""
        return self.ui_config_service.registry.get_all_elements()
    
    def build_and_launch_ui(self):
        """Build and launch the UI using the configured framework."""
        # Get the UI framework from configuration
        framework_name = get_framework_from_config(self.config.config)
        self.logger.info(f"Building UI using framework: {framework_name}")
        
        # Load the UI framework
        ui_framework = load_ui_framework(framework_name)
        
        if ui_framework and hasattr(ui_framework, 'build_and_launch_ui'):
            # Use the framework's build_and_launch_ui function
            ui_framework.build_and_launch_ui(self)
        else:
            # Fallback to the legacy implementation
            self.logger.warning(f"UI framework {framework_name} not available. Using legacy UI implementation.")
            self._legacy_build_and_launch_ui()
    
    def _legacy_build_and_launch_ui(self):
        """Legacy implementation removed - Gradio support has been removed from this project."""
        self.logger.error("Legacy Gradio UI implementation is no longer available. Please use Streamlit framework.")
        raise NotImplementedError("Gradio support has been removed. Use Streamlit framework instead.")
